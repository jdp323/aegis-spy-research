"""Public Yahoo chart research. Never an executable options feed."""
import json,urllib.request,urllib.error,hashlib,math
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
URL='https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=5m&range=5d&includePrePost=false'

def parse_chart(body):
    doc=json.loads(body);r=doc['chart']['result'][0]
    if r['meta']['symbol']!='SPY':raise ValueError('Wrong symbol')
    quotes=r['indicators']['quote'][0];rows=[]
    for i,t in enumerate(r.get('timestamp',[])):
        values=[quotes[k][i] for k in ['open','high','low','close','volume']]
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in values):continue
        o,h,l,c,v=values
        if not 0<l<=min(o,c)<=max(o,c)<=h or v<0:continue
        rows.append({'timestamp':t,'open':o,'high':h,'low':l,'close':c,'volume':v})
    if not rows or any(a['timestamp']>=b['timestamp'] for a,b in zip(rows,rows[1:])):raise ValueError('Missing or unordered bars')
    return rows

def collect():
    now=datetime.now(timezone.utc);result={'fetched_at':now.isoformat(),'source':URL,'symbol':'SPY','use':'DELAYED_OR_UNVERIFIED_RESEARCH_ONLY','action':'NO TRADE','options_quotes':None}
    try:
        req=urllib.request.Request(URL,headers={'User-Agent':'AEGIS-local-research/1.0'})
        with urllib.request.urlopen(req,timeout=15) as response:body=response.read(8_000_000)
        rows=parse_chart(body)
        cache=ROOT/'data/public_cache';cache.mkdir(exist_ok=True)
        digest=hashlib.sha256(body).hexdigest();(cache/(digest+'.json')).write_bytes(body)
        result.update(status='RESEARCH_DATA_RECEIVED',bars=rows,sha256=digest,last_bar_at=datetime.fromtimestamp(rows[-1]['timestamp'],timezone.utc).isoformat(),note='Public chart data may be delayed/revised. Last bar may be incomplete. This is not a verified live option quote.')
    except urllib.error.HTTPError as e:result.update(status='PUBLIC_SOURCE_UNAVAILABLE',http_status=e.code,bars=[],note='No authentication bypass or repeated endpoint probing attempted.')
    except Exception:result.update(status='PUBLIC_SOURCE_UNAVAILABLE',bars=[],note='Network or schema failure; no prices inferred.')
    path=ROOT/'research/public_spy_latest.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2),encoding='utf-8');tmp.replace(path)
    return result

if __name__=='__main__':
    result=collect();print(json.dumps({k:v for k,v in result.items() if k!='bars'},indent=2));print('Bars:',len(result.get('bars',[])))
