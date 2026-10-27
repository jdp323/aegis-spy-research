"""Stdlib-only shadow protocol. Model output is never genuine market data."""
import hashlib,json,math,sqlite3
from datetime import datetime,timedelta,timezone
from pathlib import Path
from core.sessions import ET,market_session
from data.models import finite,stamp

VERSION='kronos-mini-shadow-v1'
MODEL='NeoQuasar/Kronos-mini'
MODEL_REVISION='f4e68697d9d5aed55cef5c96aabc3376bcad9f81'
TOKENIZER='NeoQuasar/Kronos-Tokenizer-2k'
TOKENIZER_REVISION='26966d0035065a0cae0ebad7af8ece35bc1fb51c'
CODE_REVISION='67b630e67f6a18c9e9be918d9b4337c960db1e9a'
SEEDS=(1729,1730,1731)
FEATURES=('open','high','low','close','volume','amount')

def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def future_starts(cutoff,now,horizon):
    """5m bar START convention; never extend across a session boundary."""
    cutoff=stamp(cutoff) if isinstance(cutoff,str) else cutoff
    session=market_session(now)
    if session['quality']!='DATA_OK' or not session['active']:raise ValueError('VERIFIED_ACTIVE_SESSION_REQUIRED')
    if cutoff.timestamp()%300 or cutoff>now or (now-cutoff).total_seconds()>=300:raise ValueError('CURRENT_COMPLETED_5M_CUTOFF_REQUIRED')
    local=cutoff.astimezone(ET);close=local.replace(hour=session['close_minute']//60,minute=session['close_minute']%60,second=0,microsecond=0)
    if local.date()!=now.astimezone(ET).date() or local.hour*60+local.minute<570:raise ValueError('CURRENT_REGULAR_SESSION_REQUIRED')
    count={'H60':12,'H120':24,'SESSION':int((close-cutoff).total_seconds()//300)}.get(horizon)
    if count is None or count<=0 or cutoff+timedelta(minutes=5*count)>close:raise ValueError('FULL_HORIZON_UNAVAILABLE')
    return [(cutoff+timedelta(minutes=5*i)).astimezone(timezone.utc).isoformat() for i in range(count)]

def prepare(rows,feed,now,horizon='H60'):
    if feed not in ('IEX','SIP'):raise ValueError('EXPLICIT_FEED_REQUIRED')
    if not 78<=len(rows)<=512:raise ValueError('78_TO_512_GENUINE_BARS_REQUIRED')
    clean=[];last=None
    for b in rows:
        t=stamp(b['start_at']);s=market_session(t);end=t+timedelta(minutes=5)
        if b.get('symbol')!='SPY' or b.get('feed_quality')!=feed or b.get('origin') not in ('STREAM','REST_BACKFILL','PROVIDER_NATIVE_AGGREGATE'):raise ValueError('GENUINE_SOURCE_PROVENANCE_REQUIRED')
        if t.timestamp()%300 or not s['active'] or end.astimezone(ET).hour*60+end.astimezone(ET).minute>s['close_minute'] or end>now:raise ValueError('PARTIAL_OR_OUTSIDE_SESSION')
        if last and t<=last:raise ValueError('DUPLICATE_OR_OUT_OF_ORDER')
        if last and t.astimezone(ET).date()==last.astimezone(ET).date() and t-last!=timedelta(minutes=5):raise ValueError('MISSING_5M_INPUT')
        if not b.get('received_at') or not end<=stamp(b['received_at'])<=now:raise ValueError('INPUT_AVAILABILITY_UNVERIFIED')
        v=[b.get(k) for k in FEATURES[:5]]
        if not all(finite(x) for x in v) or not 0<b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] or b['volume']<0:raise ValueError('INVALID_OHLCV')
        row={k:b[k] for k in FEATURES[:5]};row['amount']=b['volume']*sum(b[k] for k in FEATURES[:4])/4
        clean.append(dict(row,start_at=t.astimezone(timezone.utc).isoformat(),model_feature_only=True));last=t
    cutoff=last+timedelta(minutes=5);future=future_starts(cutoff,now,horizon)
    request={'version':VERSION,'symbol':'SPY','feed':feed,'created_at':now.isoformat(),'input_cutoff':cutoff.isoformat(),'input_sha256':sha(rows),'input_rows':clean,'input_provenance':rows,'future_starts':future,'horizon':horizon,'target_at':(stamp(future[-1])+timedelta(minutes=5)).isoformat(),'model':MODEL,'model_revision':MODEL_REVISION,'tokenizer':TOKENIZER,'tokenizer_revision':TOKENIZER_REVISION,'code_revision':CODE_REVISION,'seeds':list(SEEDS),'temperature':1.,'top_p':.9,'top_k':0,'sample_count_per_call':1,'raw_path_count':3,'device':'cpu','threads':1,'transform':'actual volume; derived amount=volume*OHLCmean, model feature only v1','capture_population':'PROSPECTIVE_SHADOW_NOT_ENTRY_PERMISSION','calibrated':False}
    # Restart/read-observation times cannot create another identical trial.
    # Genuine changed OHLCV is a new input revision; original remains immutable.
    request['id']=sha({k:request[k] for k in ('version','feed','input_cutoff','input_rows','future_starts','horizon','model_revision','tokenizer_revision','code_revision','seeds','temperature','top_p','top_k')})
    return request

def validate_result(request,result,completed):
    if result.get('request_id')!=request['id']:raise ValueError('REQUEST_BINDING_MISMATCH')
    paths=result.get('paths')
    if not isinstance(paths,list) or len(paths)!=3:raise ValueError('THREE_RAW_PATHS_REQUIRED')
    for seed,path in zip(SEEDS,paths):
        if path.get('seed')!=seed or len(path.get('bars',[]))!=len(request['future_starts']):raise ValueError('PATH_DIMENSION_OR_SEED')
        for t,b in zip(request['future_starts'],path['bars']):
            if b.get('start_at')!=t or not all(finite(b.get(k)) for k in FEATURES):raise ValueError('NONFINITE_OR_TIMESTAMP_OUTPUT')
            if not 0<b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] or b['volume']<0 or b['amount']<0:raise ValueError('INCONSISTENT_MODEL_OHLCV')
    if completed<stamp(request['created_at']) or completed>=stamp(request['future_starts'][0])+timedelta(minutes=5):raise ValueError('FORECAST_AVAILABLE_TOO_LATE')
    return {**result,'version':VERSION,'completed_at':completed.isoformat(),'available_at':completed.isoformat(),'input_cutoff':request['input_cutoff'],'input_sha256':request['input_sha256'],'horizon':request['horizon'],'target_at':request['target_at'],'model_generated':True,'entry_eligible':False,'option_profitability':'UNAVAILABLE'}

class ShadowLog:
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=.25)
        self.db.executescript("""PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS shadow(id TEXT PRIMARY KEY,kind TEXT,payload TEXT,created TEXT);
        CREATE TRIGGER IF NOT EXISTS shadow_no_update BEFORE UPDATE ON shadow BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS shadow_no_delete BEFORE DELETE ON shadow BEGIN SELECT RAISE(ABORT,'append only'); END;""")
    def append(self,ident,kind,value,now):
        with self.db:cur=self.db.execute('INSERT OR IGNORE INTO shadow VALUES(?,?,?,?)',(ident,kind,json.dumps(value,allow_nan=False),now.isoformat()))
        return cur.rowcount==1
    def close(self):self.db.close()

def earlier_session_baseline(history,issue,reference,horizon_minutes,*,feed):
    """Past complete-session same-clock returns only; descriptive distribution."""
    target=issue+timedelta(minutes=horizon_minutes);values=[]
    for day,rows in sorted(history.items()):
        if day>=issue.astimezone(ET).date().isoformat():continue
        if not rows or any(b.get('feed_quality')!=feed for b in rows):continue
        d=stamp(rows[0]['start_at']).astimezone(ET);s=market_session(d.replace(hour=10,minute=0))
        if not s['active'] or len(rows)!=(s['close_minute']-570)//5 or (d.hour,d.minute)!=(9,30):continue
        if any(stamp(b['start_at'])-stamp(a['start_at'])!=timedelta(minutes=5) for a,b in zip(rows,rows[1:])):continue
        # Full/early populations cannot be pooled.
        if s['close_minute']!=market_session(issue)['close_minute']:continue
        a=next((b for b in rows if stamp(b['start_at']).astimezone(ET).strftime('%H:%M')==issue.astimezone(ET).strftime('%H:%M')),None)
        z=next((b for b in rows if (stamp(b['start_at'])+timedelta(minutes=5)).astimezone(ET).strftime('%H:%M')==target.astimezone(ET).strftime('%H:%M')),None)
        if a and z and a['open']>0:values.append(z['close']/a['open']-1)
    return {'count_sessions':len(values),'returns':values,'mean_price':reference*(1+sum(values)/len(values)) if values else None,'no_change_price':reference,'probability':None}
