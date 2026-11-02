"""Bounded state-only diagnostic view: no replay, provider or private ledger scan."""
import json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from core.storage import ROOT
from core.sessions import market_session

VERSION='state-only-dashboard-v1'
KEYS=('features','regime','selection','news','worker_health','quote:SPY',
      'research_quote:SPY:iex','stream:iex','stream:sip','stream:opra',
      'fast_path_health','market_view','receipt_observer_health','ntp_clock')

def snapshot(root=ROOT,clock=None):
    root=Path(root);values={};error=None
    try:
        db=sqlite3.connect((root/'runtime/aegis.sqlite').resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)
        try:
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
            for key in KEYS:
                row=db.execute('SELECT payload FROM state WHERE key=?',(key,)).fetchone()
                values[key]=json.loads(row[0]) if row else None
            db.rollback()
        finally:db.close()
    except (sqlite3.Error,OSError,ValueError) as e:error=type(e).__name__
    now=(clock or (lambda:datetime.now(timezone.utc)))()
    if now.tzinfo is None:raise ValueError('AWARE_TIME_REQUIRED')
    system={'worker':values.get('worker_health'),'monitor':values.get('fast_path_health'),
            'delivery_observation':values.get('receipt_observer_health'),
            'database':'QUERY_ONLY_OK' if error is None else 'UNAVAILABLE','error_type':error}
    for name,path in (('services','services.json'),('telegram','telegram_health.json'),('dispatcher','dispatcher_health.json')):
        try:system[name]=json.loads((root/'runtime'/path).read_text(encoding='utf-8'))
        except (OSError,ValueError):system[name]={'state':'UNAVAILABLE'}
    return {'generated_at':now.isoformat(),'session':market_session(now),
      'underlying':values.get('quote:SPY') or {'quality':'DATA_INCOMPLETE','payload':{}},'research_underlying':values.get('research_quote:SPY:iex') or {'quality':'DATA_INCOMPLETE','payload':{}},
      'features':values.get('features') or {},'regime':values.get('regime') or {},
      'selection':values.get('selection') or {},'news':values.get('news') or {},
      'streams':{f:values.get('stream:'+f) or {} for f in ('iex','sip','opra')},
      'system':system,'ntp_clock':values.get('ntp_clock'),'market_view':values.get('market_view'),
      'signals':[],'positions':None,'positions_view':'NOT_READ_BY_BOUNDED_DIAGNOSTIC; use private /mypositions; no closure inferred',
      'options_readiness':{'mode':'RESEARCH_ONLY','gates':{'LIVE_SIGNAL_READY':False}},
      'today_verdict':'NO TRADE — diagnostic state; /trend recomputes current gates.',
      'today_next_event':'See /news and /details; optional coverage may be unavailable',
      'action':'NO TRADE','live_signal_enabled':False,'live_execution_enabled':False,
      'order_execution_enabled':False,'LIVE_SIGNAL_READY':False,
      'diagnostic_source':VERSION,'study_summaries':'Outside HTTP refresh; use /details or retained research reports',
      'clock_meaning':'generated_at is composition time; every underlying source/receipt and saved evidence clock is preserved'}
