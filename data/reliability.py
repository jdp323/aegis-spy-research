"""Secret-free append-only reliability telemetry. Active views retain 30 days.

Older rows are retained as archive evidence, never deleted. No provider payloads,
URLs, exception messages, authentication frames or recipient identifiers allowed.
"""
import json, sqlite3, time
from datetime import datetime, timezone, timedelta
from core.sessions import ET, market_session
from data.models import stamp

FIELDS = {'reason','close_code','attempt','backoff_seconds','latency_ms','count',
          'payload_type','duration_seconds','wall_gap_seconds','monotonic_gap_seconds',
          'clock_jump_seconds','source_age_seconds','receipt_age_seconds','source_receipt_skew_seconds',
          'predicate','provider','snapshot_id','source','feed_quality','recorded','confirmed','state'}
def active(now):
    local=now.astimezone(ET); noon=local.replace(hour=12,minute=0,second=0,microsecond=0)
    session=market_session(noon)
    return session['active'] and 560<=local.hour*60+local.minute<session['close_minute']

class Events:
    def __init__(self,path):
        path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,timeout=15)
        self.db.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS stream_events(id INTEGER PRIMARY KEY,at TEXT NOT NULL,feed TEXT NOT NULL,event TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS stream_events_time ON stream_events(at);
        CREATE VIEW IF NOT EXISTS active_stream_events AS SELECT * FROM stream_events WHERE julianday(at)>=julianday('now','-30 days');
        CREATE TRIGGER IF NOT EXISTS stream_events_no_delete BEFORE DELETE ON stream_events BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS stream_events_no_update BEFORE UPDATE ON stream_events BEGIN SELECT RAISE(ABORT,'append only'); END;''')
    def add(self,event,feed,now=None,**fields):
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:raise ValueError('AWARE_TIME_REQUIRED')
        if feed not in ('iex','sip','opra','worker','supervisor'):raise ValueError('INVALID_EVENT_FEED')
        if event not in {'CONNECT','AUTHENTICATED','SUBSCRIBED','FIRST_MARKET_MESSAGE','MINUTE_MESSAGES','DISCONNECT','RECONNECT','PERMISSION_ERROR','CLOCK_REJECTION','PROCESS_PAUSED','WATCHDOG_RECONNECT','WATCHDOG_RESTART','BACKFILL','BACKFILL_FAILED','DATA_REJECTION','PREOPEN_CHECK'}:raise ValueError('INVALID_EVENT')
        if set(fields)-FIELDS:raise ValueError('EVENT_FIELD_FORBIDDEN')
        # Free-form errors are forbidden; codes are short, restricted diagnostics.
        for k,v in fields.items():
            if isinstance(v,str) and (len(v)>160 or any(c in v for c in ('\n','\r','/','\\','@'))):raise ValueError('UNSAFE_EVENT_VALUE')
        with self.db:self.db.execute('INSERT INTO stream_events(at,feed,event,payload) VALUES(?,?,?,?)',(now.astimezone(timezone.utc).isoformat(),feed,event,json.dumps(fields,allow_nan=False)))
    def close(self):self.db.close()

class PauseProbe:
    def __init__(self):self.last=None
    def check(self,now,mono=None):
        mono=time.monotonic() if mono is None else mono
        if now.tzinfo is None:raise ValueError('AWARE_TIME_REQUIRED')
        old=self.last;self.last=(now,mono)
        if old is None:return None
        wall=(now-old[0]).total_seconds();elapsed=mono-old[1]
        if max(wall,elapsed,abs(wall-elapsed))>60 and (active(now) or active(old[0])):
            return {'duration_seconds':max(wall,elapsed,abs(wall-elapsed)),'wall_gap_seconds':wall,'monotonic_gap_seconds':elapsed,'clock_jump_seconds':wall-elapsed,'reason':'CLOCK_JUMP' if abs(wall-elapsed)>60 else 'SCHEDULING_GAP'}
        return None

def watchdog_age(last,now,started):
    try:return (now-stamp(last['received_timestamp'])).total_seconds()
    except (KeyError,TypeError,ValueError):return (now-started).total_seconds()

def connection_watchdog_age(last,now,started):
    """New sockets get their own90s window; global outage age stays separate."""
    baseline=started
    try:
        receipt=stamp(last['received_timestamp'])
        if started<=receipt<=now:baseline=receipt
    except (KeyError,TypeError,ValueError):pass
    return (now-baseline).total_seconds()

def quote_diagnostics(q,now,provider=None,budget=5):
    """Signed times; same strict receipt/freshness predicates as quote_valid."""
    from core.signals import quote_valid
    d={'provider':q.get('provider','UNAVAILABLE'),'source_age_seconds':None,'receipt_age_seconds':None,'source_receipt_skew_seconds':None,'predicate':None}
    try:
        source=stamp(q['source_timestamp']);receipt=stamp(q['received_timestamp'])
        d.update(source_age_seconds=(now-source).total_seconds(),receipt_age_seconds=(now-receipt).total_seconds(),source_receipt_skew_seconds=(source-receipt).total_seconds())
        skew=q.get('accepted_future_skew_seconds',0)
        # Datum advertises the accepted budget under this existing field.
        skew=q.get('accepted_skew_budget_seconds',skew)
        if provider and q.get('provider')!=provider:d['predicate']='PROVIDER_MISMATCH'
        elif d['receipt_age_seconds']<0:d['predicate']='RECEIPT_AFTER_CLOCK'
        elif d['source_age_seconds'] < -skew:d['predicate']='SOURCE_AFTER_CLOCK'
        elif d['source_receipt_skew_seconds']>skew:d['predicate']='SOURCE_RECEIPT_SKEW'
        elif d['source_age_seconds']>budget:d['predicate']='SOURCE_TOO_OLD'
        elif d['receipt_age_seconds']>budget:d['predicate']='RECEIPT_TOO_OLD'
        elif not quote_valid(q,now,budget):d['predicate']='QUALITY_ENTITLEMENT_OR_BID_ASK_INVALID'
    except (KeyError,TypeError,ValueError):d['predicate']='QUOTE_TIMESTAMP_UNAVAILABLE'
    return d

def describe(d):
    names={'PROVIDER_MISMATCH':'provider mismatch','RECEIPT_AFTER_CLOCK':'receipt time after evaluation clock','SOURCE_AFTER_CLOCK':'source time after evaluation clock','SOURCE_RECEIPT_SKEW':'source/receipt skew exceeds accepted tolerance','SOURCE_TOO_OLD':'source age exceeds 5 s','RECEIPT_TOO_OLD':'receipt age exceeds 5 s','QUALITY_ENTITLEMENT_OR_BID_ASK_INVALID':'quality, entitlement or bid/ask invalid','QUOTE_TIMESTAMP_UNAVAILABLE':'quote timestamp unavailable'}
    f=lambda x:'UNAVAILABLE' if x is None else f'{x:+.3f} s'
    return 'Quote rejected: '+names.get(d['predicate'],str(d['predicate']))+'; source age '+f(d['source_age_seconds'])+', receipt age '+f(d['receipt_age_seconds'])+', skew '+f(d['source_receipt_skew_seconds'])+'; '+d['provider']
