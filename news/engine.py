"""Verified official economic-calendar coverage and explicit event risk windows."""
import json
from pathlib import Path
from datetime import datetime,timezone
from data.models import stamp
from core.sessions import ET
from urllib.parse import urlparse
KINDS={'FOMC','CPI','PCE','JOBS','UNEMPLOYMENT','GDP','PPI','RETAIL_SALES','JOBLESS_CLAIMS','FOMC_MINUTES','FED_SPEAKER','TREASURY','ECONOMIC_RELEASE','GEOPOLITICAL'}
OFFICIAL={'www.federalreserve.gov','www.bls.gov','www.bea.gov','apps.bea.gov','www.census.gov','www.dol.gov','www.treasury.gov','home.treasury.gov','api.stlouisfed.org','fred.stlouisfed.org'}
def source_valid(url):
    p=urlparse(url);return p.scheme=='https' and p.hostname in OFFICIAL and not p.username and not p.password and p.port in (None,443)
def validate(d):
    if not source_valid(d['source_url']):raise ValueError('UNVERIFIED_CALENDAR_SOURCE')
    stamp(d['verified_at']);start=stamp(d['coverage_from']);end=stamp(d['coverage_through'])
    if start>=end or type(d['coverage_complete']) is not bool:raise ValueError('INVALID_COVERAGE')
    ids=set()
    for e in d['events']:
        if e['event_id'] in ids:raise ValueError('DUPLICATE_EVENT')
        ids.add(e['event_id'])
        if e['type'] not in KINDS or e['risk'] not in ('HIGH','MODERATE') or not source_valid(e['source_url']):raise ValueError('INVALID_EVENT')
        t=stamp(e['time_utc']);local=stamp(e['time_et'])
        if t!=local or local.isoformat()!=t.astimezone(ET).isoformat():raise ValueError('INVALID_ET_CONVERSION')
        if e.get('time_source')=='DATE_ONLY':
            start=stamp(e['blackout_start_utc']);end=stamp(e['blackout_end_utc'])
            if not e.get('all_day') or e['risk']!='HIGH' or start!=t or not 0<(end-start).total_seconds()<=90000 or start.astimezone(ET).time()!=datetime.min.time() or end.astimezone(ET).time()!=datetime.min.time():raise ValueError('INVALID_DATE_ONLY_WINDOW')
        for key in ('blackout_before_minutes','blackout_after_minutes'):
            if type(e[key]) is not int or not 0<=e[key]<=240:raise ValueError('INVALID_WINDOW')
    return d
class NewsProvider:
    def __init__(self,path):self.path=Path(path)
    def snapshot(self,now=None):
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:raise ValueError('AWARE_CLOCK_REQUIRED')
        out={'quality':'DATA_INCOMPLETE','risk':'UNAVAILABLE','events':[],'coverage_through':None,'stale':True,'reason':'NEWS_DATA_UNAVAILABLE: no complete fresh official calendar'}
        try:
            d=validate(json.loads(self.path.read_text(encoding='utf-8')));age=(now-stamp(d['verified_at'])).total_seconds()
            stale=not d['coverage_complete'] or not 0<=age<=7*86400 or not stamp(d['coverage_from'])<=now<=stamp(d['coverage_through'])
            out.update(verified_at=d['verified_at'],coverage_through=d['coverage_through'],coverage_complete=d['coverage_complete'],stale=stale,source=d['source_url'],source_status=d.get('source_status',{}),date_only_event_count=sum(e.get('time_source')=='DATE_ONLY' for e in d['events']))
            if stale or not d['coverage_complete']:return out
            events=[]
            for e in d['events']:
                delta=(stamp(e['time_utc'])-now).total_seconds();inside=-60*e['blackout_after_minutes']<=delta<=60*e['blackout_before_minutes']
                if e.get('time_source')=='DATE_ONLY':inside=stamp(e['blackout_start_utc'])<=now<stamp(e['blackout_end_utc'])
                events.append({**e,'kind':e['type'],'time':e['time_utc'],'seconds_until':delta,'blackout':inside and e['risk']=='HIGH','caution':inside and e['risk']=='MODERATE'})
            risk='HIGH' if any(e['blackout'] for e in events) else 'MODERATE' if any(e['caution'] for e in events) else 'NORMAL'
            return {**out,'quality':'DATA_OK','risk':risk,'events':events,'reason':None,'note':'Published official coverage; unexpected news remains possible.'}
        except (ValueError,KeyError,TypeError,OSError):return out
