"""One scheduled public premarket-chart attempt per ET session; never a live feed."""
import json,hashlib,urllib.request,urllib.error
from datetime import datetime,timezone
from core.storage import ROOT
from data.public_spy import parse_chart
URL='https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=5m&range=5d&includePrePost=true'
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,allow_nan=False),encoding='utf-8');temp.replace(path)
def collect_once(day,now=None):
    path=ROOT/'research/premarket'/ (day+'.json')
    if path.exists():
        try:return json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):return {'status':'UNAVAILABLE'}
    now=now or datetime.now(timezone.utc)
    result={'session_date':day,'source':URL,'symbol':'SPY','fetched_at':now.isoformat(),'status':'FETCH_IN_PROGRESS','use':'DELAY_UNVERIFIED_RESEARCH_ONLY','bars':[]}
    # Reserve before networking: a crash or denied request must not trigger probing.
    save(path,result)
    try:
        req=urllib.request.Request(URL,headers={'User-Agent':'AEGIS-local-premarket-research/1.0'})
        with urllib.request.urlopen(req,timeout=15) as response:body=response.read(8_000_001)
        if len(body)>8_000_000:raise ValueError('Oversized chart')
        rows=parse_chart(body);digest=hashlib.sha256(body).hexdigest()
        cache=ROOT/'data/premarket_cache';cache.mkdir(parents=True,exist_ok=True);(cache/(digest+'.json')).write_bytes(body)
        result.update(status='RESEARCH_DATA_RECEIVED',bars=rows,sha256=digest,fetched_at=datetime.now(timezone.utc).isoformat())
    except urllib.error.HTTPError as error:result.update(status='UNAVAILABLE',http_status=error.code)
    except Exception:result['status']='UNAVAILABLE'
    save(path,result);return result
def verified(raw):
    try:
        digest=raw['sha256']
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):return False
        body=(ROOT/'data/premarket_cache'/(digest+'.json')).read_bytes()
        return hashlib.sha256(body).hexdigest()==digest and parse_chart(body)==raw['bars']
    except (KeyError,ValueError,TypeError,OSError):return False
