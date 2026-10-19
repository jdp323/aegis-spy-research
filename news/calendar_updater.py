"""Official-only ingestion. Untimed dates are unresolved, never assumed at 14:00."""
import hashlib,html,json,re,os,tempfile,urllib.request
from pathlib import Path
from datetime import datetime,timezone
from core.sessions import ET
from data.models import stamp
from news.engine import source_valid,validate,NewsProvider
SOURCES={'fed':'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm','bls':'https://www.bls.gov/schedule/{year}/home.htm','bea':'https://www.bea.gov/news/schedule'}
HIGH={'FOMC','CPI','JOBS','PCE','GDP'}
def plain(text):return ' '.join(html.unescape(re.sub('<[^>]*>',' ',text)).split())
def category(name):
    for kind,words in [('CPI',['consumer price index']),('JOBS',['employment situation']),('PPI',['producer price index']),('PCE',['personal income and outlays']),('GDP',['gross domestic product','gdp (']),('FOMC_MINUTES',['fomc minutes','minutes of the federal open market']),('FOMC',['fomc rate decision']),('RETAIL_SALES',['retail sales','retail and food services']),('JOBLESS_CLAIMS',['jobless claims','unemployment insurance weekly claims']),('FED_SPEAKER',['scheduled speech','chair speech','governor speech']),('TREASURY',['quarterly refunding','treasury refunding'])]:
        if any(w in name.lower() for w in words):return kind
def event(name,kind,local,url,fetched):
    if local.tzinfo is None or not source_valid(url):raise ValueError('INVALID_SOURCE_OR_TIME')
    local=local.astimezone(ET);utc=local.astimezone(timezone.utc).isoformat()
    return {'event_id':hashlib.sha256((url+name+utc).encode()).hexdigest()[:24],'name':name,'type':kind,'kind':kind,'time_et':local.isoformat(),'time_utc':utc,'time':utc,'risk':'HIGH' if kind in HIGH else 'MODERATE','blackout_before_minutes':30,'blackout_after_minutes':60 if kind=='FOMC' else 15,'source_url':url,'fetched_at':fetched,'verified_at':fetched}
def parse_bea(body,url,now):
    text=body.decode('utf-8');year=re.search(r'Year\s+(\d{4})',text)
    if not year:raise ValueError('BEA_YEAR_MISSING')
    rows=[]
    for row in re.findall(r'<tr[^>]*scheduled-releases-type-press[^>]*>(.*?)</tr>',text,re.S):
        title=re.search(r'<td[^>]*release-title[^>]*>(.*?)</td>',row,re.S);date=re.search(r'release-date[^>]*>([^<]+)',row);clock=re.search(r'<small[^>]*>([^<]+)</small>',row)
        if not title:continue
        name=plain(title[1]);kind=category(name)
        if not kind:continue
        if not date or not clock:raise ValueError('BEA_EVENT_TIME_MISSING')
        local=datetime.strptime(plain(date[1])+' '+year[1]+' '+plain(clock[1]),'%B %d %Y %I:%M %p').replace(tzinfo=ET)
        rows.append(event(name,kind,local,url,now.isoformat()))
    if not rows:raise ValueError('BEA_EMPTY')
    return rows,[]
def parse_bls(body,url,now):
    text=body.decode('utf-8');rows=[]
    # Recorded official-page reader text is supported without creating dates from memory.
    if 'Source: open(' in text and url in text[:500]:
        for line in text.splitlines():
            match=re.match(r'L\d+: (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (\w+ \d{1,2}, \d{4}) (\d{1,2}:\d{2} [AP]M) (.+)',line)
            if not match:continue
            name=match[3];kind=category(name)
            if kind:rows.append(event(name,kind,datetime.strptime(match[1]+' '+match[2],'%B %d, %Y %I:%M %p').replace(tzinfo=ET),url,now.isoformat()))
        if not rows:raise ValueError('OFFICIAL_READER_EMPTY')
        return rows,[]
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>',text,re.S):
        cells=[plain(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',row,re.S)];name=' '.join(cells);kind=category(name)
        if not kind:continue
        date=re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',name);clock=re.search(r'(\d{1,2}:\d{2})\s*([APap][Mm])',name)
        if not date or not clock:raise ValueError('BLS_EVENT_TIME_MISSING')
        local=datetime.strptime(' '.join(date.groups())+' '+clock[1]+' '+clock[2].upper(),'%B %d %Y %I:%M %p').replace(tzinfo=ET)
        rows.append(event(name,kind,local,url,now.isoformat()))
    if not rows:raise ValueError('BLS_EMPTY_OR_FORMAT_CHANGED')
    return rows,[]
def parse_fed(body,url,now,date_only=False):
    text=body.decode('utf-8');unresolved=[]
    for year,section in re.findall(r'(\d{4}) FOMC Meetings(.*?)(?=\d{4} FOMC Meetings|\Z)',text,re.S):
        for month,days in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)',section,re.S):
            nums=re.findall(r'\d+',days)
            try:date=datetime.strptime(month+' '+nums[-1]+' '+year,'%B %d %Y').date()
            except (ValueError,IndexError):continue
            if date>=now.astimezone(ET).date():
                start=datetime.strptime(month+' '+nums[0]+' '+year,'%B %d %Y').date()
                unresolved.append({'type':'FOMC','date':date.isoformat(),'meeting_start':start.isoformat(),'source_url':url,'reason':'Published meeting date lacks a decision time. Coverage stops before the first meeting day, rather than inventing a decision time.'})
    if not unresolved:raise ValueError('FOMC_FUTURE_COVERAGE_MISSING')
    if date_only:
        from datetime import timedelta
        rows=[]
        for item in unresolved:
            start=datetime.fromisoformat(item['date']).replace(tzinfo=ET)
            if start.year!=now.astimezone(ET).year:continue
            end=datetime.combine(start.date()+timedelta(days=1),datetime.min.time(),ET)
            row=event('FOMC statement day (official date; time unknown)','FOMC',start,url,now.isoformat())
            row.update(time_source='DATE_ONLY',all_day=True,blackout_start_utc=start.astimezone(timezone.utc).isoformat(),blackout_end_utc=end.astimezone(timezone.utc).isoformat(),decision_time='UNAVAILABLE')
            rows.append(row)
        return rows,[]
    return [],unresolved
def parse_official_ics(body,url,now):
    """Optional official schedules must publish a timed UTC or New York event."""
    if not source_valid(url):raise ValueError('UNOFFICIAL_SOURCE')
    text=body.decode('utf-8').replace('\r\n','\n');text=re.sub(r'\n[ \t]','',text)
    if 'BEGIN:VCALENDAR' not in text:raise ValueError('INVALID_OFFICIAL_CALENDAR')
    events=[]
    for block in re.findall(r'BEGIN:VEVENT\n(.*?)\nEND:VEVENT',text,re.S):
        summary=re.search(r'^SUMMARY:(.+)$',block,re.M)
        if not summary:continue
        name=summary[1].replace('\\,',',');kind=category(name)
        if not kind:continue
        match=re.search(r'^DTSTART(?P<params>[^:]*):(?P<value>[^\n]+)$',block,re.M)
        if not match:raise ValueError('OFFICIAL_EVENT_TIME_MISSING')
        value=match['value'];params=match['params']
        if value.endswith('Z') and not params:
            local=datetime.strptime(value,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        elif params==';TZID=America/New_York':
            naive=datetime.strptime(value,'%Y%m%dT%H%M%S');local=naive.replace(tzinfo=ET)
            if local.utcoffset()!=local.replace(fold=1).utcoffset() or local.astimezone(timezone.utc).astimezone(ET).replace(tzinfo=None)!=naive:raise ValueError('AMBIGUOUS_OR_NONEXISTENT_EVENT_TIME')
        else:raise ValueError('UNVERIFIED_EVENT_TIMEZONE')
        events.append(event(name,kind,local,url,now.isoformat()))
    if not events:raise ValueError('OFFICIAL_SCHEDULE_EMPTY')
    return events,[]
def fetch(url):
    if not source_valid(url):raise ValueError('UNOFFICIAL_SOURCE')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AEGIS/1.0 (personal use; official calendar research)'}),timeout=10) as r:
        if not source_valid(r.url):raise ValueError('UNOFFICIAL_REDIRECT')
        body=r.read(3000001)
    if len(body)>3000000:raise ValueError('OVERSIZED_SOURCE')
    return body
def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as f:json.dump(data,f,indent=2);tmp=f.name
    os.replace(tmp,path)
def update(root,now=None,transport=fetch):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('AWARE_CLOCK_REQUIRED')
    root=Path(root);events=[];unresolved=[];statuses={}
    for key,url in SOURCES.items():
        url=url.format(year=now.astimezone(ET).year)
        try:
            try:body=transport(url)
            except Exception as error:
                if key!='bls' or getattr(error,'code',None)!=403:raise
                url='https://www.bls.gov/schedule/news_release/bls.ics';body=transport(url)
            parser=parse_official_ics if url.endswith('.ics') else globals()['parse_'+key]
            rows,missing=parser(body,url,now,date_only=True) if key=='fed' else parser(body,url,now)
            events+=rows;unresolved+=missing;statuses[key]={'status':'PARSED','source_url':url,'fetched_at':now.isoformat(),'sha256':hashlib.sha256(body).hexdigest(),'events':len(rows)}
        except Exception as e:statuses[key]={'status':'FAILED','source_url':url,'error_type':type(e).__name__,'http_status':getattr(e,'code',None),'fetched_at':now.isoformat()}
    try:configuration=json.loads((root/'config/upgrade.json').read_text(encoding='utf-8'))
    except FileNotFoundError:configuration={}
    for index,url in enumerate(configuration.get('calendar_official_extra_sources',[])):
        key='optional_'+str(index)
        try:
            body=transport(url);rows,missing=parse_official_ics(body,url,now);events+=rows
            statuses[key]={'status':'PARSED','source_url':url,'fetched_at':now.isoformat(),'sha256':hashlib.sha256(body).hexdigest(),'events':len(rows)}
        except Exception as e:statuses[key]={'status':'FAILED','source_url':url,'error_type':type(e).__name__,'http_status':getattr(e,'code',None),'fetched_at':now.isoformat()}
    from news.calendar_import import load as import_load
    imports,import_failures=import_load(root/'config/calendar_import',now)
    statuses['imports']={'status':'INSPECTED','failures':import_failures}
    for key,info in imports.items():
        if key not in SOURCES or statuses[key]['status']!='PARSED':
            events+=info['events'];statuses[key]={'status':'PARSED','source_url':info['files'][0]['source_url'],'fetched_at':info['fetched_at'],'events':len(info['events']),'import_files':info['files']}
    from news.fred_calendar import collect as fred_collect
    fred_rows,fred_status=fred_collect(now);events+=fred_rows;statuses['fred']=fred_status
    events=list({e['event_id']:e for e in events}.values())
    for item in events:
        overrides=configuration.get('calendar_event_overrides',{}).get(item['event_id'],{})
        for field in ('blackout_before_minutes','blackout_after_minutes'):
            if field in overrides:item[field]=overrides[field]
    future=[e for e in events if stamp(e['time_utc'])>=now];kinds={e['type'] for e in future}
    required=HIGH-{'FOMC'} if unresolved else HIGH
    complete=required<=kinds and all(statuses[k]['status']=='PARSED' for k in SOURCES)
    through=min(max(stamp(e['time_utc']) for e in future if e['type']==k) for k in required) if complete else max((stamp(e['time_utc']) for e in future),default=now)
    if complete and unresolved:
        # A coverage boundary is not an event timestamp. No event at midnight is invented.
        boundary=datetime.fromisoformat(min(e['meeting_start'] for e in unresolved)).replace(tzinfo=ET).astimezone(timezone.utc)
        from datetime import timedelta
        through=min(through,boundary-timedelta(seconds=1))
        if through<=now:complete=False
    if complete:
        from datetime import timedelta
        end_day=through.astimezone(ET).date()
        through=(datetime.combine(end_day+timedelta(days=1),datetime.min.time(),ET)-timedelta(seconds=1)).astimezone(timezone.utc)
    verified=min([now.isoformat()]+[x['fetched_at'] for x in statuses.values() if x.get('status')=='PARSED' and x.get('fetched_at')])
    result={'schema_version':4,'source_url':SOURCES['fed'],'fetched_at':now.isoformat(),'verified_at':verified,'coverage_from':now.isoformat(),'coverage_through':through.isoformat(),'coverage_complete':complete,'events':events,'source_status':statuses,'unresolved':unresolved,'optional_categories':'Only explicitly timed entries; absent categories are unknown.'}
    target=root/'config/news_calendar.json';atomic(root/'research/calendar_attempts'/('attempt_'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.json'),result)
    if complete and future:validate(result);atomic(target,result);result['published']=True
    else:result['published']=False
    return result
def maintenance(store,config,now=None,transport=fetch,root=None):
    from core.storage import ROOT
    root=Path(root or ROOT)
    now=now or datetime.now(timezone.utc);state=store.get('calendar_updater',{})
    if state and (now-stamp(state['attempted_at'])).total_seconds()<86400:return
    result=update(root,now,transport);store.put('calendar_updater',{'attempted_at':now.isoformat(),'published':result['published'],'source_status':result['source_status']})
if __name__=='__main__':
    from core.storage import ROOT
    d=update(ROOT);print(json.dumps({k:d[k] for k in ('published','coverage_complete','coverage_through','source_status')}))
