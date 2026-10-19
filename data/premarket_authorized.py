"""Prefer actual same-day authorized IEX prices, never retag public data."""
import json,hashlib
from datetime import datetime,timezone,timedelta
from core.storage import ROOT
from core.sessions import ET
from data.backfill import history
from data.models import stamp

def collect(day,now,provider=None):
    from data.providers import AlpacaProvider
    provider=provider or AlpacaProvider();start=now.astimezone(ET).replace(hour=4,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    end=min(now.replace(second=0,microsecond=0)-timedelta(minutes=2),now.astimezone(ET).replace(hour=9,minute=15,second=0,microsecond=0).astimezone(timezone.utc)-timedelta(minutes=1))
    if provider.health()['status']=='FEED_NOT_CONFIGURED':return None
    try:
        raw=history(provider,start,end,'iex');groups={}
        for r in raw:
            t=int(stamp(r['t']).timestamp());groups.setdefault(t//300*300,[]).append(r)
        bars=[]
        for ts,rs in sorted(groups.items()):
            if len(rs)!=5 or [int(stamp(r['t']).timestamp()) for r in rs]!=list(range(ts,ts+300,60)):continue
            bars.append({'timestamp':ts,'open':rs[0]['o'],'high':max(r['h'] for r in rs),'low':min(r['l'] for r in rs),'close':rs[-1]['c'],'volume':sum(r['v'] for r in rs)})
        if len(bars)<6:return None
        body=json.dumps({'feed':'IEX','provider':'alpaca-iex','bars':bars},sort_keys=True,allow_nan=False).encode();digest=hashlib.sha256(body).hexdigest();folder=ROOT/'data/premarket_authorized_cache';folder.mkdir(exist_ok=True)
        (folder/(digest+'.json')).write_bytes(body)
        return {'session_date':day,'source':'https://data.alpaca.markets/v2/stocks/SPY/bars','symbol':'SPY','fetched_at':datetime.now(timezone.utc).isoformat(),'status':'RESEARCH_DATA_RECEIVED','use':'IEX_AUTHORIZED_PRICE_RESEARCH_ONLY','feed_quality':'IEX','bars':bars,'sha256':digest}
    except (OSError,ValueError,KeyError,RuntimeError,TypeError):return None
def verified(raw):
    try:
        digest=raw['sha256']
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):return False
        body=(ROOT/'data/premarket_authorized_cache'/(digest+'.json')).read_bytes();d=json.loads(body)
        return hashlib.sha256(body).hexdigest()==digest and d['feed']=='IEX' and d['provider']=='alpaca-iex' and d['bars']==raw['bars']
    except (OSError,ValueError,KeyError,TypeError):return False
