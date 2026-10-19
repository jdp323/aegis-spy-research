"""Append-only scheduled-status evidence, separate from Telegram acceptance."""
import sqlite3,json
from datetime import timezone

def record(path,event_id,now,ctx,news):
    from core.isolation import assert_real
    assert_real(ctx)
    if now.tzinfo is None:raise ValueError('AWARE_TIME_REQUIRED')
    bar=ctx.get('bar_research') or {};frames={k:ctx.get('features',{}).get(k,{}).get('trend','UNAVAILABLE') for k in ('1m','5m','15m','30m','1h','daily')}
    d={'event_id':event_id,'at':now.astimezone(timezone.utc).isoformat(),'status':'VALID_UNDERLYING' if not ctx.get('reason') else 'DESCRIPTIVE_ONLY' if not bar.get('reason') else 'UNAVAILABLE',
       'predicate':ctx.get('failed_predicate'),'feed_quality':ctx.get('feed_quality','UNAVAILABLE'),'frames':frames,
       'heartbeat_age_seconds':ctx.get('heartbeat_age_seconds'),'bar_end_age_seconds':ctx.get('bar_end_age_seconds'),
       'quote_diagnostics':ctx.get('diagnostics',[]),'calendar_quality':news.get('quality','UNAVAILABLE'),
       'horizons':{k:v.get('bias','UNAVAILABLE') for k,v in ctx.get('horizons',{}).items()},
       'delivery_meaning':'Scheduled analysis composed; not Telegram acceptance or phone delivery.'}
    path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path,timeout=.5)
    try:
        db.executescript('''CREATE TABLE IF NOT EXISTS trend_status_events(event_id TEXT PRIMARY KEY,at TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS trend_status_no_update BEFORE UPDATE ON trend_status_events BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS trend_status_no_delete BEFORE DELETE ON trend_status_events BEGIN SELECT RAISE(ABORT,'append only'); END;''')
        with db:db.execute('INSERT OR IGNORE INTO trend_status_events VALUES(?,?,?)',(event_id,d['at'],json.dumps(d,allow_nan=False)))
    finally:db.close()
    return d
