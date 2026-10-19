import json,time,os
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from data.public_spy import collect
ROOT=Path(__file__).resolve().parents[1];ET=ZoneInfo('America/New_York')
from core.exchange_calendar import HOLIDAYS,EARLY,YEARS
def session(now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(ET);day=now.date().isoformat();minute=now.hour*60+now.minute
    if now.year not in YEARS:return 'CALENDAR_REFRESH_REQUIRED',21600
    if now.weekday()>4 or day in HOLIDAYS:return 'CLOSED',21600
    end=780 if day in EARLY else 960
    if 570<=minute<end:return 'REGULAR_SESSION',300
    return ('PREMARKET',300) if 240<=minute<570 else ('AFTER_HOURS',7200)
def analyze(data,now=None):
    now=now or datetime.now(timezone.utc)
    groups={}
    for b in data.get('bars',[]):
        t=datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET);day=t.date().isoformat();end=780 if day in EARLY else 960
        if t.year not in YEARS or t.weekday()>4 or day in HOLIDAYS or not 570<=t.hour*60+t.minute<end or b['timestamp']+300>now.timestamp() or b['volume']<=0:continue
        groups.setdefault(day,[]).append(b)
    status,interval=session(now)
    out={'generated_at':now.isoformat(),'market':status,'poll_seconds':interval,'action':'NO TRADE','signal_ready':False,'data_status':data['status'],'source':data['source'],'source_fetched_at':data['fetched_at'],'data_use':'DELAYED_OR_UNVERIFIED_RESEARCH_ONLY','option_quotes':'UNAVAILABLE','reason':'No verified current option quotes or validated option strategy. Public chart levels are research only.','levels':None}
    if groups:
        from features.spy_patterns import describe
        out['patterns']=describe([b for group in groups.values() for b in group],now)
        days=sorted(groups);bars=groups[days[-1]];volume=sum(b['volume'] for b in bars)
        out['levels']={'session_date':days[-1],'last_completed_bar_at':datetime.fromtimestamp(bars[-1]['timestamp'],timezone.utc).isoformat(),'last_close':bars[-1]['close'],'high':max(b['high'] for b in bars),'low':min(b['low'] for b in bars),'open':bars[0]['open'],'bar_based_vwap_approx':sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in bars)/volume,'bar_count':len(bars),'currency':'USD'}
        if len(days)>1:
            prev=groups[days[-2]];out['levels']['prior_session']={'date':days[-2],'high':max(b['high'] for b in prev),'low':min(b['low'] for b in prev),'close':prev[-1]['close']}
    return out
def once():
    result=analyze(collect())
    from research.closing_estimate import refresh
    refresh()
    from data.research_hub import enrich
    result=enrich(result,analyze)
    from data.trend_spy import refresh as refresh_trend
    from research.basic_trend import analyze as analyze_trend
    result['basic_trend']=analyze_trend(refresh_trend())
    target=ROOT/'research/spy_research_latest.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2),encoding='utf-8');temp.replace(target);return result
def run():
    lock=ROOT/'monitoring/research_worker.lock'
    with lock.open('x') as f:json.dump({'pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat()},f)
    try:
        while not (ROOT/'runtime/shutdown.request').exists():
            result=once();print(json.dumps({'status':result['data_status'],'market':result['market'],'next_poll_seconds':result['poll_seconds']}),flush=True)
            # Short waits allow prompt shutdown; cadence is public research, not a price alarm.
            for tick in range(result['poll_seconds']):
                time.sleep(1)
                if (ROOT/'runtime/shutdown.request').exists():break
                if tick%15==0 and session()[0]!=result['market']:break
    finally:lock.unlink(missing_ok=True)
def current():
    p=ROOT/'research/spy_research_latest.json'
    if not p.exists():return {'action':'NO TRADE','reason':'No research snapshot yet','levels':None,'live_execution_enabled':False}
    result=json.loads(p.read_text());result['snapshot_age_seconds']=(datetime.now(timezone.utc)-datetime.fromisoformat(result['generated_at'])).total_seconds();result['current_session']=session()[0];result['live_execution_enabled']=False;return result
if __name__=='__main__':
    import sys
    if '--loop' in sys.argv:run()
    else:print(json.dumps(once(),indent=2))
