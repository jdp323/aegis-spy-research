"""Read-only retrospective comparison; never a sealed test or option backtest."""
import argparse,json,sqlite3,hashlib
from collections import defaultdict,Counter
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core.sessions import ET,market_session
from features.indicators import normalize
from strategies.published_baselines import compare,VERSION
from core.research_horizons import deadline

def replay(rows,now,dividends=None):
    bars=normalize(rows,now=now);days=defaultdict(list)
    for b in bars:days[datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date().isoformat()].append(b)
    prior=[];previous=None;counts=Counter();outcomes=[];excluded=Counter()
    for day,daybars in sorted(days.items()):
        session=market_session(datetime.fromisoformat(day).replace(hour=10,tzinfo=ET));expected=session['close_minute']-570
        if len(daybars)!=expected or any(b['timestamp']-a['timestamp']!=60 for a,b in zip(daybars,daybars[1:])):
            excluded['incomplete_session']+=1;continue
        for n in sorted(set(range(30,len(daybars),30))|({361} if len(daybars)>361 else set())):
            observed=daybars[:n];issue=datetime.fromtimestamp(observed[-1]['timestamp']+60,timezone.utc)
            result=compare(observed,prior,previous,(dividends or {}).get(day))
            for name,r in result.items():
                if not isinstance(r,dict):continue
                counts[name+':'+r['status']]+=1
                if r.get('side') not in (-1,1):continue
                for h in ('H60','H120','SESSION'):
                    end=deadline(issue,h)
                    if end is None:excluded[name+':'+h+':insufficient_time']+=1;continue
                    # Conservative one-minute response delay. Subminute scenarios
                    # cannot be evaluated from minute OHLCV and are not invented.
                    entry=next((b for b in daybars if b['timestamp']==issue.timestamp()+60),None)
                    exit_=next((b for b in daybars if b['timestamp']==end.timestamp()-60),None)
                    net=None if not entry or not exit_ else (exit_['close']-entry['open'])*r['side']-.03
                    outcomes.append(dict(day=day,strategy=name,horizon=h,net_usd_per_share=net,delay_seconds=60,option_pnl=None))
        prior.append(daybars);previous=daybars[-1]['close']
    by=defaultdict(list)
    for o in outcomes:by[o['strategy']+':'+o['horizon']].append(o['net_usd_per_share'])
    return dict(version=VERSION,population='RETROSPECTIVE_UNDERLYING_TIME_EXIT_ADAPTATION',
        source_rows=len(rows),normalized_rows=len(bars),sessions=len(days),complete_sessions=len(prior),
        decisions=dict(counts),exclusions=dict(excluded),
        results={k:dict(observations=len(v),resolved=sum(x is not None for x in v),net_usd_per_share=sum(x for x in v if x is not None)) for k,v in by.items()},
        limits=['No stop/target fill or portfolio profitability claim; time-exit diagnostic only.',
            'Concretum exact decision unavailable without explicit dividends and prior same-clock history.',
            'VIX-filtered first-last unavailable without contemporaneous VIX.',
            '0/15-second human delays unavailable from minute bars.',
            'No untouched final period, genuine option BBO or sufficient independent days.'],strategy_qualified=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    source=Path(a.database).resolve();db=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=2)
    try:
        raw=db.execute('SELECT payload FROM state WHERE key=?',('research_stream_bars:SPY:iex',)).fetchone()
        rows=json.loads(raw[0]) if raw else []
    finally:db.close()
    result=replay(rows,datetime.now(timezone.utc));result['source_rows_sha256']=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
