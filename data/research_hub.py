"""Independent bar research with explicit failover, quality and provenance."""
import json,hashlib
from datetime import datetime,timezone
from core.storage import ROOT
from data.secondary_spy import refresh
from data.massive_research import MassiveResearchProvider,SOURCE
from research.source_consensus import daily_context,compare_intraday
MASSIVE=MassiveResearchProvider()
def enrich(primary,analyze,now=None,provider=None):
    now=now or datetime.now(timezone.utc);provider=provider or MASSIVE
    daily=daily_context(refresh(now),now)
    datum=provider.get_bars();secondary=None
    if datum.payload.get('bars'):
        body=json.dumps(datum.payload['raw_response'],sort_keys=True).encode();digest=hashlib.sha256(body).hexdigest()
        cache=ROOT/'data/secondary_cache';cache.mkdir(parents=True,exist_ok=True);(cache/(digest+'.json')).write_bytes(body)
        secondary=analyze({'status':'RESEARCH_DATA_RECEIVED','source':SOURCE,'fetched_at':datum.received_timestamp,'bars':datum.payload['bars']},now);secondary['sha256']=digest
    comparison=compare_intraday(primary,secondary or {},now)
    selected=primary;selected_provider='Yahoo';failover='NONE'
    from monitoring.research_alerts import observe
    from core.sessions import market_session
    session=market_session(now)
    if observe(primary,session,now)['quality']=='UNAVAILABLE' and secondary and observe(secondary,session,now)['quality']=='PUBLIC_RESEARCH_ONLY':
        selected=secondary;selected_provider='Massive';failover='EXPLICIT_PUBLIC_RESEARCH_FALLBACK'
    selected['multi_source']={'version':1,'selected_provider':selected_provider,'failover':failover,'intraday_comparison':comparison,'daily':daily,'providers':{'yahoo':{'status':primary.get('data_status'),'source':primary.get('source'),'fetched_at':primary.get('source_fetched_at'),'delay':'UNVERIFIED'},'massive':{**provider.health(),'result_quality':datum.quality,'reason':datum.reason,'source':SOURCE},'stooq':{'status':daily['status'],'source':'https://stooq.com/q/d/l/?s=spy.us&i=d','horizon':'DAILY'},'tradingview':{'status':'NO_GENERAL_DATA_API','use':'HUMAN_CHART_REFERENCE_ONLY'}}}
    target=ROOT/'research/multi_source_latest.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(selected['multi_source'],indent=2),encoding='utf-8');temp.replace(target)
    return selected
