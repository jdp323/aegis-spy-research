"""Optional official FRED dates; untimed HIGH releases block the entire ET day."""
import json,re,os,tempfile,urllib.request,urllib.parse
from datetime import datetime,timezone,timedelta
from pathlib import Path
from core.storage import ROOT
from core.sessions import ET
from monitoring.vault import transform
from core.runtime_paths import private_directory
PATH=private_directory()/'fred.dpapi'
NOTICE='This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.'
TERMS='https://fred.stlouisfed.org/docs/api/terms_of_use.html'
def save(key,path=PATH):
    if not isinstance(key,str) or not re.fullmatch('[a-z0-9]{32}',key):raise ValueError('INVALID_FRED_KEY')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=transform(json.dumps({'fred_api_key':key}).encode())
    with tempfile.NamedTemporaryFile('wb',dir=path.parent,delete=False) as f:f.write(raw);tmp=f.name
    os.replace(tmp,path)
def request(url):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args):return None
    with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url,headers={'User-Agent':'AEGIS/5 (personal economic-calendar research)'}),timeout=8) as r:
        raw=r.read(1000001)
    if len(raw)>1000000:raise ValueError('OVERSIZED_FRED_RESPONSE')
    return json.loads(raw)
def collect(now,transport=request,key=None,path=PATH):
    from news.calendar_updater import category,event,HIGH
    if key is None:
        if not Path(path).exists():return [],{'status':'FRED_NOT_CONFIGURED','notice':NOTICE}
        try:key=json.loads(transform(Path(path).read_bytes(),True))['fred_api_key']
        except Exception:return [],{'status':'FRED_ENCRYPTED_CONFIG_UNREADABLE'}
    if not re.fullmatch('[a-z0-9]{32}',key):return [],{'status':'FRED_INVALID_CONFIGURATION'}
    try:
        base='https://api.stlouisfed.org/fred/releases/dates';query=urllib.parse.urlencode({'api_key':key,'file_type':'json','include_release_dates_with_no_data':'true','realtime_start':now.astimezone(ET).date().isoformat(),'realtime_end':(now+timedelta(days=90)).date().isoformat(),'limit':1000,'order_by':'release_date','sort_order':'asc'})
        data=transport(base+'?'+query);rows=[]
        if data.get('count',0)>1000:raise ValueError('FRED_PAGINATION_INCOMPLETE')
        for r in data['release_dates']:
            name=r['release_name'];kind=category(name)
            if kind not in HIGH:continue
            start=datetime.fromisoformat(r['date']).replace(tzinfo=ET);end=start+timedelta(days=1)
            e=event(name+' (FRED release date; time unknown)',kind,start,base,now.isoformat())
            e.update(time_source='DATE_ONLY',all_day=True,blackout_start_utc=start.astimezone(timezone.utc).isoformat(),blackout_end_utc=end.astimezone(timezone.utc).isoformat(),decision_time='UNAVAILABLE')
            rows.append(e)
        return rows,{'status':'PARSED_DATE_ONLY_SUPPLEMENT','count':len(rows),'source_url':base,'fetched_at':now.isoformat(),'notice':NOTICE,'limitation':'Dates lack release times. Conservative all-day HIGH supplement; does not replace required issuer coverage.'}
    except Exception as error:return [],{'status':'FAILED','error_type':type(error).__name__,'notice':NOTICE}
