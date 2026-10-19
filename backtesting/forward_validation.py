"""Append every evaluation and later underlying outcome; no option-return inference."""
import hashlib,json,math
from datetime import datetime,timezone,timedelta
from core.storage import Store,encode
from data.models import stamp,finite
from features.indicators import normalize
from core.sessions import ET
class ForwardValidation:
 def __init__(self,path):
  self.store=Store(path);self.db=self.store.db;self.db.executescript('''CREATE TABLE IF NOT EXISTS forward_evaluations(id TEXT PRIMARY KEY,signal_id TEXT NOT NULL,timestamp TEXT NOT NULL,payload TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS forward_reason_counts(minute TEXT,reason TEXT,version TEXT,evaluations INTEGER,PRIMARY KEY(minute,reason,version));
   CREATE VIEW IF NOT EXISTS active_forward_reason_counts AS SELECT * FROM forward_reason_counts WHERE julianday(minute)>=julianday('now','-14 days');
   CREATE TABLE IF NOT EXISTS forward_outcomes(id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,payload TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS forward_exclusions(evaluation_id TEXT PRIMARY KEY,reason TEXT NOT NULL,at TEXT NOT NULL);
  CREATE TRIGGER IF NOT EXISTS forward_exclusion_no_delete BEFORE DELETE ON forward_exclusions BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE TRIGGER IF NOT EXISTS forward_exclusion_no_update BEFORE UPDATE ON forward_exclusions BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE INDEX IF NOT EXISTS forward_outcomes_evaluation ON forward_outcomes(evaluation_id);
  CREATE TRIGGER IF NOT EXISTS forward_eval_no_delete BEFORE DELETE ON forward_evaluations BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE TRIGGER IF NOT EXISTS forward_eval_no_update BEFORE UPDATE ON forward_evaluations BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE TRIGGER IF NOT EXISTS forward_outcome_no_delete BEFORE DELETE ON forward_outcomes BEGIN SELECT RAISE(ABORT,'append only'); END;
  CREATE TRIGGER IF NOT EXISTS forward_outcome_no_update BEFORE UPDATE ON forward_outcomes BEGIN SELECT RAISE(ABORT,'append only'); END;''')
 def close(self):self.store.close()
 def record(self,s):
  s=s.dict() if hasattr(s,'dict') else s;id=hashlib.sha256((s['signal_id']+s['timestamp']).encode()).hexdigest()
  if s.get('direction') not in ('CALL','PUT') or not all(finite(s.get(k)) and s[k]>0 for k in ('spy_price','invalidation','t2')):
   from core.isolation import assert_real
   assert_real(s);minute=stamp(s['timestamp']).replace(second=0,microsecond=0).astimezone(timezone.utc).isoformat()
   with self.db:
    for reason in sorted(set(s.get('paper_blockers') or s.get('rejection_reasons') or ['MODELED_LEVELS_UNAVAILABLE'])):
     self.db.execute('INSERT INTO forward_reason_counts VALUES(?,?,?,1) ON CONFLICT(minute,reason,version) DO UPDATE SET evaluations=evaluations+1',(minute,reason,s.get('strategy_version','UNAVAILABLE')))
   return None
  payload={**s,'evidence_kind':'UNDERLYING_EVALUATION_NOT_OPTION_RETURN','gate_results':{'paper_eligible':s.get('paper_eligible',False),'paper_blockers':s.get('paper_blockers',s.get('rejection_reasons',[]))},'theoretical_entry':s.get('spy_price'),'theoretical_stop':s.get('invalidation'),'theoretical_t1':s.get('t1'),'theoretical_t2':s.get('t2')}
  with self.db:self.db.execute('INSERT OR IGNORE INTO forward_evaluations VALUES(?,?,?,?)',(id,s['signal_id'],s['timestamp'],encode(payload)))
  return id
 def observe(self,rows,now,feed_quality):
  if feed_quality not in ('IEX','SIP'):return 0
  bars=normalize(rows,now=now);written=0
  # Bound per cycle; terminal outcomes free capacity. Missing levels stay unresolved.
  pending=self.db.execute('SELECT id,payload FROM forward_evaluations WHERE id NOT IN (SELECT evaluation_id FROM forward_outcomes) AND id NOT IN (SELECT evaluation_id FROM forward_exclusions) ORDER BY timestamp LIMIT 500').fetchall()
  for id,payload in pending:
   s=json.loads(payload);entry=s.get('theoretical_entry');stop=s.get('theoretical_stop');target=s.get('theoretical_t2');sign=1 if s['direction']=='CALL' else -1 if s['direction']=='PUT' else 0
   if not sign or entry is None or stop is None or target is None:
    with self.db:self.db.execute('INSERT OR IGNORE INTO forward_outcomes VALUES(?,?,?)',(id+'-missing',id,encode({'outcome':'UNAVAILABLE','reason':'Original evaluation lacks modeled direction/entry/stop/target; no result fabricated','option_pnl':None})))
    continue
   if s.get('feed_quality')!=feed_quality:continue
   opened=stamp(s['timestamp']);horizon=opened+timedelta(minutes=s.get('max_holding_minutes',60))
   observed=[b for b in bars if opened<=datetime.fromtimestamp(b['timestamp'],timezone.utc)<horizon and datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==opened.astimezone(ET).date()];mfe=mae=0;outcome=None;end=None
   if observed and (observed[0]['timestamp']!=math.ceil(opened.timestamp()/60)*60 or any(observed[i]['timestamp']-observed[i-1]['timestamp']!=60 for i in range(1,len(observed)))):
    if now>=horizon:
     with self.db:self.db.execute('INSERT OR IGNORE INTO forward_outcomes VALUES(?,?,?)',(id+'-gap',id,encode({'outcome':'UNAVAILABLE','reason':'Non-contiguous outcome bars; no result inferred','option_pnl':None})))
    continue
   for b in observed:
    end=datetime.fromtimestamp(b['timestamp'],timezone.utc)+timedelta(minutes=1);mfe=max(mfe,(b['high']-entry) if sign==1 else entry-b['low']);mae=min(mae,(b['low']-entry) if sign==1 else entry-b['high'])
    if (b['low']<=stop if sign==1 else b['high']>=stop):outcome='STOP_FIRST';break
    if (b['high']>=target if sign==1 else b['low']<=target):outcome='T2';break
    if end-stamp(s['timestamp'])>=timedelta(minutes=s.get('max_holding_minutes',60)):outcome='TIME_HORIZON';break
   if outcome:
    with self.db:written+=self.db.execute('INSERT OR IGNORE INTO forward_outcomes VALUES(?,?,?)',(id+'-outcome',id,encode({'outcome':outcome,'mfe_usd_per_share':mfe,'mae_usd_per_share':mae,'observed_through':end.isoformat(),'feed_quality':feed_quality,'sample_dependence':'Repeated evaluations share bars; not independent trades','option_pnl':None}))).rowcount
  return written
