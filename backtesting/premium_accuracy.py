"""Descriptive estimate errors, never auto-retunes a strategy."""
import json,statistics,math
from pathlib import Path
from core.storage import Store
from core.isolation import assert_real
class Accuracy:
 def __init__(self,path):
  self.store=Store(path);self.db=self.store.db
  self.db.execute('CREATE TABLE IF NOT EXISTS premium_estimates(id TEXT PRIMARY KEY,payload TEXT NOT NULL)');self.db.commit()
  for operation in ('UPDATE','DELETE'):
   self.db.execute("CREATE TRIGGER IF NOT EXISTS premium_estimates_no_"+operation.lower()+" BEFORE "+operation+" ON premium_estimates BEGIN SELECT RAISE(ABORT,'APPEND_ONLY_ESTIMATE_HISTORY'); END")
  self.db.commit()
 def close(self):self.store.close()
 def observe(self,position,underlying,option,now):
  from core.signals import quote_valid,option_quote_valid
  assert_real(position);assert_real(underlying);assert_real(option)
  if not quote_valid(underlying,now) or not option_quote_valid(option,now):return 0
  s=position['signal'];plan=s.get('option_plan')
  if not plan:return 0
  px=underlying['payload']['mid'];bid=option['payload']['bid'];sign=1 if s['direction']=='CALL' else -1;c=s['option_contract'];count=0
  for level,key in [('t1','t1_bid'),('t2','t2_bid'),('invalidation','stop_bid')]:
   hit=(px-s[level])*sign>=0 if level!='invalidation' else (px-s[level])*sign<=0
   if not hit:continue
   import datetime
   from core.sessions import ET
   dte=(datetime.datetime.fromisoformat(c['expiry']).date()-now.astimezone(ET).date()).days
   value={'signal_id':s['signal_id'],'level':level,'estimate':plan[key],'observed_bid':bid,'error':bid-plan[key],'observed_at':now.isoformat(),'dte':dte,'delta':c['delta'],'iv':c['iv'],'horizon':plan['horizon'],'feed_quality':option.get('feed_quality','OPRA'),'limitations':'First sampled threshold crossing, not an exact tick at the target.'}
   with self.db:count+=self.db.execute('INSERT OR IGNORE INTO premium_estimates VALUES(?,?)',(s['signal_id']+':'+level,json.dumps(value))).rowcount
  return count
 def report(self):
  rows=[json.loads(r[0]) for r in self.db.execute('SELECT payload FROM premium_estimates')]
  def stats(values):
   xs=[r['error'] for r in values];n=len(xs)
   return {'n':n,'mean_error':statistics.mean(xs) if xs else None,'sample_stdev':statistics.stdev(xs) if n>=2 else None,'review_bias':n>=20 and abs(statistics.mean(xs))>.1,'validated':False}
  dimensions={'horizon':lambda r:r['horizon'],'dte':lambda r:'0-1' if r['dte']<=1 else '2-7' if r['dte']<=7 else '8+','delta':lambda r:'low' if abs(r['delta'])<.35 else 'preferred' if abs(r['delta'])<=.65 else 'high','iv':lambda r:'under .20' if r['iv']<.2 else '.20-.40' if r['iv']<=.4 else 'over .40'}
  return {'overall':stats(rows),'groups':{k:{v:stats([r for r in rows if fn(r)==v]) for v in sorted({fn(r) for r in rows})} for k,fn in dimensions.items()},'horizon_comparison':'Insufficient data; no automatic promotion.','limitations':'Sampled executable bid error; fixed-IV estimates; no strategy validation.'}
