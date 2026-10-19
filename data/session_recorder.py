"""Additive tagged minute-bar/chain history. Indicative IV observations never grant readiness."""
import hashlib,json,sqlite3
from datetime import datetime,timezone,timedelta
from core.storage import Store,encode
from core.sessions import ET,market_session
from data.models import stamp,finite
from features.indicators import normalize
from options.ledger import contract
class Recorder:
 def __init__(self,path):
  self.store=Store(path);self.db=self.store.db
  self.db.executescript('''CREATE TABLE IF NOT EXISTS session_bars(id TEXT PRIMARY KEY,provider TEXT NOT NULL,feed_quality TEXT NOT NULL,source_timestamp TEXT NOT NULL,recorded_at TEXT NOT NULL,payload TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS option_snapshots(id TEXT PRIMARY KEY,provider TEXT NOT NULL,feed_quality TEXT NOT NULL,source_timestamp TEXT,recorded_at TEXT NOT NULL,payload TEXT NOT NULL);
  CREATE INDEX IF NOT EXISTS session_bars_time ON session_bars(source_timestamp);
  CREATE TRIGGER IF NOT EXISTS session_bars_no_delete BEFORE DELETE ON session_bars BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE TRIGGER IF NOT EXISTS session_bars_no_update BEFORE UPDATE ON session_bars BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE TRIGGER IF NOT EXISTS snapshots_no_delete BEFORE DELETE ON option_snapshots BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE TRIGGER IF NOT EXISTS snapshots_no_update BEFORE UPDATE ON option_snapshots BEGIN SELECT RAISE(ABORT,'append only'); END;''')
 def close(self):self.store.close()
 def bars(self,rows,feed,now):
  from core.isolation import assert_real
  assert_real(rows)
  if feed not in ('SIP','IEX'):raise ValueError('UNVERIFIED_BAR_FEED')
  normalized=normalize(rows,now=now);count=0;originals={stamp(r['t']).timestamp():r for r in rows}
  with self.db:
   for b in normalized:
    source=datetime.fromtimestamp(b['timestamp'],timezone.utc).isoformat();original=originals.get(b['timestamp'],{});payload=encode({**b,'source':original.get('source','STREAM'),'provider':'alpaca-'+feed.lower(),'feed_quality':feed});id=hashlib.sha256((feed+source+payload).encode()).hexdigest()
    count+=self.db.execute('INSERT OR IGNORE INTO session_bars VALUES(?,?,?,?,?,?)',(id,'alpaca-'+feed.lower(),feed,source,now.isoformat(),payload)).rowcount
  return count
 def chain(self,datum,spot,now):
  from core.isolation import assert_real
  assert_real(datum)
  feed=datum.get('feed_quality','OPRA' if datum.get('provider')=='alpaca' and datum.get('entitlement')=='REALTIME' and datum.get('quality')=='DATA_OK' else 'UNAVAILABLE')
  if feed not in ('OPRA','INDICATIVE') or not finite(spot) or spot<=0:return 0
  items=[]
  for symbol,raw in datum.get('payload',{}).get('contracts',{}).items():
   try:
    spec=contract(symbol);t=stamp(raw['latestQuote']['t']);dte=(datetime.fromisoformat(spec['expiry']).date()-now.astimezone(ET).date()).days
    if not 0<=dte<=30 or abs(float(spec['strike'])-spot)>spot*.05 or t>now or t.astimezone(ET).date()!=now.astimezone(ET).date():continue
    if feed=='OPRA' and raw.get('feed_quality')!='OPRA':continue
    items.append((spec,raw,t))
   except (KeyError,ValueError,TypeError):continue
  expiries=sorted({s['expiry'] for s,r,t in items})[:3];count=0
  with self.db:
   for spec,raw,t in items:
    if spec['expiry'] not in expiries:continue
    payload=encode({'contract':spec,'snapshot':raw,'iv_timestamp':raw.get('greeksTimestamp'),'iv_timestamp_verified':bool(raw.get('greeksTimestamp'))});id=hashlib.sha256((feed+spec['symbol']+t.isoformat()+payload).encode()).hexdigest()
    count+=self.db.execute('INSERT OR IGNORE INTO option_snapshots VALUES(?,?,?,?,?,?)',(id,datum.get('provider','UNAVAILABLE'),feed,t.astimezone(timezone.utc).isoformat(),now.isoformat(),payload)).rowcount
  return count
 def iv_history(self):
  days=set();series={}
  for row in self.db.execute('SELECT source_timestamp,payload,feed_quality FROM option_snapshots ORDER BY source_timestamp'):
   d=json.loads(row[1]);raw=d['snapshot'];iv=raw.get('impliedVolatility')
   observed=stamp(row[0]);regular=datetime.combine(observed.astimezone(ET).date(),datetime.min.time(),ET)+timedelta(hours=12)
   if not market_session(regular)['active']:continue
   if finite(iv) and iv>0:days.add(observed.astimezone(ET).date().isoformat())
   try:
    observed=stamp(row[0]);iv_at=stamp(raw['greeksTimestamp']);spec=d['contract'];delta=raw['greeks']['delta'];dte=(datetime.fromisoformat(spec['expiry']).date()-observed.astimezone(ET).date()).days
    if not finite(iv) or iv<=0 or not finite(delta) or spec['type']!='C' or not 20<=dte<=30 or not .45<=delta<=.55 or not 0<=(observed-iv_at).total_seconds()<=300:continue
    # Compare only the same tagged near-ATM call maturity bucket. Never combine feeds.
    day=observed.astimezone(ET).date().isoformat();key=(row[2],day);rank=(abs(delta-.5),abs(dte-25),-observed.timestamp())
    if key not in series or rank<series[key][0]:series[key]=(rank,iv)
   except (KeyError,ValueError,TypeError):continue
  metrics={}
  for feed in ('OPRA','INDICATIVE'):
   values=[(day,value[1]) for (quality,day),value in series.items() if quality==feed];values.sort();ivs=[value for day,value in values];ready=len(ivs)>=60
   metrics[feed]={'comparable_days':len(ivs),'enabled':ready,'iv_rank':100*(ivs[-1]-min(ivs))/(max(ivs)-min(ivs)) if ready and max(ivs)>min(ivs) else None,'basis':'20–30 DTE calls, delta .45–.55, timestamped IV within five minutes of quote; same feed only','live_readiness':False}
  return {'observed_trading_days':len(days),'iv_rank_history_ready':len(days)>=60,'iv_rank_enabled':any(m['enabled'] for m in metrics.values()),'series':metrics,'reason':'Research IV rank enables only after 60 comparable timestamped days. Indicative/OPRA remain separate and never grant readiness.'}
def tick(store,now,root=None):
 from core.storage import ROOT
 r=Recorder((root or ROOT)/'runtime/history.sqlite')
 try:
  for feed,key in [('SIP','stream_bars:SPY'),('IEX','research_stream_bars:SPY:iex')]:
   try:r.bars(store.get(key,[]) or [],feed,now)
   except (ValueError,KeyError,TypeError):store.put('recorder_rejection:'+feed,{'at':now.isoformat(),'reason':'INVALID_BAR_BATCH'})
  quote=store.get('quote:SPY') or store.get('research_quote:SPY:iex') or {};spot=quote.get('payload',{}).get('mid')
  for key in ('chain','chain:indicative'):r.chain(store.get(key,{}) or {},spot,now)
  store.put('recorder_health',{'at':now.isoformat(),'state':'RUNNING','iv_history':r.iv_history()})
 finally:r.close()
