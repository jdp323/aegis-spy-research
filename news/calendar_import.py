"""Owner-imported official schedules; content hashes and explicit download provenance."""
import csv,io,json,hashlib
from pathlib import Path
from datetime import timezone
from data.models import stamp
from news.engine import source_valid
def load(folder,now):
    from news.calendar_updater import parse_official_ics,category,event
    groups={};failures=[]
    for p in sorted(Path(folder).glob('*')):
        if p.suffix.lower() not in ('.ics','.csv'):continue
        try:
            if p.is_symlink() or p.stat().st_size>3000000:raise ValueError('INVALID_IMPORT_FILE')
            side=json.loads(p.with_suffix(p.suffix+'.provenance.json').read_text(encoding='utf-8'));url=side['source_url'];downloaded=stamp(side['downloaded_at']).astimezone(timezone.utc);body=p.read_bytes();digest=hashlib.sha256(body).hexdigest()
            if not source_valid(url) or digest!=str(side['sha256']).lower() or not 0<=(now-downloaded).total_seconds()<=7*86400:raise ValueError('UNVERIFIED_OR_STALE_IMPORT')
            if p.suffix.lower()=='.ics':rows,_=parse_official_ics(body,url,downloaded)
            else:
                rows=[]
                for r in csv.DictReader(io.StringIO(body.decode('utf-8-sig'))):
                    if set(r)!=set(('name','time_et','source_url')) or r['source_url']!=url:raise ValueError('INVALID_CSV_SCHEMA')
                    kind=category(r['name']);t=stamp(r['time_et'])
                    from core.sessions import ET
                    if t.utcoffset()!=t.astimezone(ET).utcoffset() or t.replace(tzinfo=None)!=t.astimezone(ET).replace(tzinfo=None):raise ValueError('CSV_TIME_NOT_VALID_ET')
                    if kind:rows.append(event(r['name'],kind,t,url,downloaded.isoformat()))
            if not rows:raise ValueError('EMPTY_IMPORT')
            host=__import__('urllib.parse',fromlist=['urlparse']).urlparse(url).hostname
            key='bls' if host=='www.bls.gov' else 'fed' if host=='www.federalreserve.gov' else 'bea' if host in ('www.bea.gov','apps.bea.gov') else 'optional_import'
            info=groups.setdefault(key,{'events':[],'files':[],'fetched_at':downloaded.isoformat()})
            info['events']+=rows;info['files'].append({'name':p.name,'sha256':digest,'source_url':url,'downloaded_at':downloaded.isoformat(),'provenance':'Owner-supplied browser download; hash verifies file integrity, not independent network retrieval.'})
            info['fetched_at']=min(info['fetched_at'],downloaded.isoformat())
        except (OSError,ValueError,KeyError,TypeError):failures.append({'file':p.name,'status':'REJECTED_IMPORT'})
    return groups,failures
