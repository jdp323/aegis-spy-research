"""Shared, bounded public-chart refresh; separate from the 09:15 reservation."""
import json,hashlib,os,time,urllib.request,urllib.error
from contextlib import contextmanager
from datetime import datetime,timezone
from core.storage import ROOT
from data.models import stamp
from data.public_spy import parse_chart
from data.premarket_spy import URL,save
COMMAND_CACHE_SECONDS=30
FAILURE_COOLDOWN_SECONDS=60
def load():
    try:
        value=json.loads((ROOT/'research/basic_trend_raw.json').read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}

@contextmanager
def refresh_lock(wait_seconds=2):
    """OS advisory lock releases on process death; never steal a live lock."""
    path=ROOT/'runtime/trend_refresh.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0,os.SEEK_END)
        if handle.tell()==0:handle.write(b'0');handle.flush()
        locked=False;deadline=time.monotonic()+wait_seconds
        while True:
            try:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                locked=True;break
            except OSError:
                if time.monotonic()>=deadline:break
                time.sleep(.05)
        try:yield locked
        finally:
            if locked:
                handle.seek(0)
                if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

def refresh(now=None,max_age_seconds=300):
    now=now or datetime.now(timezone.utc)
    if not 0<=max_age_seconds<=300:raise ValueError('Invalid cache age')
    with refresh_lock() as locked:
        old=load()
        if not locked:return {**old,'refresh_mode':'REFRESH_IN_PROGRESS'}
        try:
            age=(now-stamp(old['fetched_at'])).total_seconds()
            limit=max_age_seconds if old.get('status')=='RESEARCH_DATA_RECEIVED' else FAILURE_COOLDOWN_SECONDS
            if 0<=age<limit:
                return {**old,'refresh_mode':'RECENT_CACHE' if old.get('status')=='RESEARCH_DATA_RECEIVED' else 'FAILURE_COOLDOWN'}
        except (KeyError,ValueError,TypeError):pass
        target=ROOT/'research/basic_trend_raw.json'
        out={'source':URL,'symbol':'SPY','fetched_at':now.isoformat(),'status':'FETCH_RESERVED','use':'DELAY_UNVERIFIED_RESEARCH_ONLY','bars':[]}
        save(target,out) # reserve attempt before networking, including a killed child
        try:
            req=urllib.request.Request(URL,headers={'User-Agent':'AEGIS-public-trend-research/1.1'})
            with urllib.request.urlopen(req,timeout=8) as r:body=r.read(8_000_001)
            if len(body)>8_000_000:raise ValueError('Oversized response')
            rows=parse_chart(body);digest=hashlib.sha256(body).hexdigest()
            cache=ROOT/'data/premarket_cache';cache.mkdir(parents=True,exist_ok=True)
            (cache/(digest+'.json')).write_bytes(body)
            out.update(status='RESEARCH_DATA_RECEIVED',bars=rows,sha256=digest,fetched_at=datetime.now(timezone.utc).isoformat())
        except urllib.error.HTTPError as e:out.update(status='UNAVAILABLE',reason='HTTP_'+str(e.code))
        except Exception:out.update(status='UNAVAILABLE',reason='SOURCE_OR_SCHEMA_UNAVAILABLE')
        save(target,out)
        return {**out,'refresh_mode':'FRESH_FETCH' if out['status']=='RESEARCH_DATA_RECEIVED' else 'FETCH_FAILED'}
