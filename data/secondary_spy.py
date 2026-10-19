"""Independent daily source for research; not a real-time failover."""
import csv,io,json,hashlib,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
from math import isfinite
ROOT=Path(__file__).resolve().parents[1]
URL='https://stooq.com/q/d/l/?s=spy.us&i=d'
def parse_daily(body,now):
    rows=[]
    for b in csv.DictReader(io.StringIO(body.decode('utf-8-sig'))):
        day=datetime.strptime(b['Date'],'%Y-%m-%d').date()
        if day>now.date():raise ValueError('Future date')
        o,h,l,c,v=[float(b[k]) for k in ['Open','High','Low','Close','Volume']]
        if not all(isfinite(x) for x in [o,h,l,c,v]) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0:raise ValueError('Invalid row')
        rows.append({'date':day.isoformat(),'open':o,'high':h,'low':l,'close':c,'volume':v})
    if len(rows)<20 or any(a['date']>=b['date'] for a,b in zip(rows,rows[1:])):raise ValueError('Missing/unsorted data')
    return rows
def collect(now=None,fetch=None):
    now=now or datetime.now(timezone.utc);out={'provider':'Stooq','source':URL,'fetched_at':now.isoformat(),'use':'DAILY_RESEARCH_ONLY','adjustments':'UNVERIFIED','action':'NO TRADE','rows':[]}
    try:
        if fetch:body=fetch()
        else:
            from data.public_https import download
            body,out['transport']=download(URL)
        if len(body)>8_000_000:raise ValueError('Response too large')
        rows=parse_daily(body,now)
        digest=hashlib.sha256(body).hexdigest();cache=ROOT/'data/public_cache';cache.mkdir(parents=True,exist_ok=True);(cache/(digest+'.csv')).write_bytes(body)
        out.update(status='DAILY_HISTORY_RECEIVED',sha256=digest,total_rows=len(rows),rows=rows[-260:])
    except urllib.error.HTTPError as e:out.update(status='SECONDARY_SOURCE_UNAVAILABLE',reason='HTTP_'+str(e.code),note='No fallback data fabricated; provider denial preserved.')
    except (ValueError,KeyError,UnicodeError):out.update(status='SECONDARY_SOURCE_UNAVAILABLE',reason='SCHEMA_INVALID',note='No fallback data fabricated; invalid response preserved as unavailable.')
    except Exception:out.update(status='SECONDARY_SOURCE_UNAVAILABLE',reason='NETWORK_OR_STORAGE_UNAVAILABLE',note='No fallback data fabricated; failure preserved.')
    target=ROOT/'research/secondary_spy_latest.json';target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(out,indent=2),encoding='utf-8');temp.replace(target)
    return out
def refresh(now=None,fetch=None):
    """One attempt per ET date, including failures and interrupted requests."""
    from core.sessions import ET
    from data.models import stamp
    now=now or datetime.now(timezone.utc);target=ROOT/'research/secondary_spy_latest.json'
    try:
        old=json.loads(target.read_text(encoding='utf-8'))
        if stamp(old['fetched_at']).astimezone(ET).date()==now.astimezone(ET).date():return old
    except (OSError,ValueError,KeyError,TypeError):pass
    target.parent.mkdir(parents=True,exist_ok=True)
    reservation={'provider':'Stooq','source':URL,'fetched_at':now.isoformat(),'status':'SECONDARY_ATTEMPT_RESERVED','rows':[],'use':'DAILY_RESEARCH_ONLY','action':'NO TRADE'}
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(reservation),encoding='utf-8');temp.replace(target)
    return collect(now,fetch)
if __name__=='__main__':
    r=collect();print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('Latest:',r['rows'][-1:] )
