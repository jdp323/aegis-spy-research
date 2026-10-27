"""Retrospective descriptive-rule diagnostic; no quote/entry/option claim."""
import json,argparse,hashlib
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import defaultdict,Counter
from features.indicators import normalize,calculate
from core.directional_research import view,VERSION
from core.sessions import ET,market_session

def run(raw):
    groups=defaultdict(list)
    for b in normalize(raw,now=datetime.now(timezone.utc)):groups[datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date().isoformat()].append(b)
    counts=Counter();outcomes=defaultdict(Counter);changed=Counter();complete_days=0
    for day,bars in sorted(groups.items()):
        opening=datetime.fromisoformat(day).replace(hour=9,minute=30,tzinfo=ET);session=market_session(opening.replace(hour=12));close=opening.replace(hour=session['close_minute']//60,minute=session['close_minute']%60);by={b['timestamp']:b for b in bars}
        if len(bars)!=session['close_minute']-570 or bars[0]['timestamp']!=opening.timestamp() or any(b['timestamp']-a['timestamp']!=60 for a,b in zip(bars,bars[1:])):
            counts['INCOMPLETE_SESSION_EXCLUDED']+=1;continue
        complete_days+=1
        for minute in range(585,session['close_minute']-14,15):
            now=opening.replace(hour=minute//60,minute=minute%60);prefix=[b for b in bars if b['timestamp']+60<=now.timestamp()];f=calculate(prefix)
            ctx={'early':len(prefix)<31,'reason':None,'bar_research':{'quality':'COMPLETED_BAR_RESEARCH_ONLY','reason':None,'bars':prefix,'features':{'1m':f},'feed_quality':'SIP_HISTORICAL'}}
            r=view(ctx,now);px=r['price'];tail=prefix[-16:];vwap=f.get('vwap_approx');change=tail[-1]['close']-tail[0]['close'];old='DATA UNAVAILABLE' if px is None else 'UP' if px>vwap and change>0 else 'DOWN' if px<vwap and change<0 else 'SIDEWAYS';new=r['trend']
            for version,bias in [('v1',old),('v2',new)]:counts[version+':'+bias]+=1
            if old!=new:changed[old+'->'+new]+=1
            for h,end in [('H60',now+timedelta(minutes=60)),('H120',now+timedelta(minutes=120)),('SESSION',close)]:
                for version,bias in [('v1',old),('v2',new)]:
                    c=outcomes[version+':'+h];c['issued']+=1
                    if end>close or bias not in ('UP','DOWN'):c['abstain']+=1;continue
                    b=by.get(end.timestamp()-60)
                    if not b:c['missing']+=1;continue
                    actual='UP' if b['close']>px else 'DOWN' if b['close']<px else 'SIDEWAYS';c['resolved']+=1;c['correct']+=actual==bias
    return {'version':VERSION,'source_sha256':hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest(),'population':'ALL_REVIEWED_DATES_DEVELOPMENT_ONLY; historical download, not contemporaneous quote evidence','complete_sessions':complete_days,'counts':dict(counts),'changed_classifications':dict(changed),'horizons':{k:dict(v) for k,v in outcomes.items()},'reference':'completed minute close at issue; exact future minute close; no BBO or notification fill','selection':'No parameter tuning or rule winner selected; no untouched evaluation','option_performance':'UNAVAILABLE','strategy_validated':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bars-export',required=True);p.add_argument('--output',required=True);a=p.parse_args();source=Path(a.bars_export)
    if source.stat().st_size>64*1024*1024:raise ValueError('EXPORT_TOO_LARGE')
    data=json.loads(source.read_text())
    if data.get('capture_mode')!='HISTORICAL_DOWNLOAD':raise ValueError('CAPTURE_LABEL_REQUIRED')
    r=run(data['bars']);Path(a.output).write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
