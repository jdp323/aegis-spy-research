"""Frozen forecast scoring, never an option-profitability or promotion gate."""
from collections import Counter,defaultdict
from datetime import timedelta
import statistics,random
from data.models import stamp,finite
from core.sessions import ET
from research.shadow_forecast import sha

VERSION='shadow-comparison-v1'

def evaluate(requests,results,observations,now):
    rows=[]
    for request in requests:
        outcome=results.get(request['id']) or {};validated=outcome.get('validated');row={'id':request['id'],'horizon':request['horizon'],'feed':request['feed'],'day':stamp(request['created_at']).astimezone(ET).date().isoformat(),'target_at':request['target_at'],'option_performance':'UNAVAILABLE'}
        if stamp(request['target_at'])>now:row['status']='PENDING'
        elif not validated:row.update(status=outcome.get('status','MISSING_MODEL_RESULT'))
        else:
            expected=request['future_starts'];by={b['start_at']:b for b in observations if b.get('feed_quality')==request['feed'] and b.get('symbol')=='SPY' and stamp(b['start_at'])+timedelta(minutes=5)<=now}
            actual=[by.get(t) for t in expected]
            if any(b is None for b in actual):row['status']='MISSING_OUTCOME'
            elif not all(finite(b.get('close')) and b['close']>0 for b in actual):row['status']='INVALID_OUTCOME'
            else:
                paths=validated['paths'];predicted=[statistics.mean(p['bars'][n]['close'] for p in paths) for n in range(len(actual))];reference=request['input_rows'][-1]['close'];target=actual[-1]['close']
                point=predicted[-1];bias='UP' if point>reference else 'DOWN' if point<reference else 'SIDEWAYS';direction='UP' if target>reference else 'DOWN' if target<reference else 'SIDEWAYS'
                row.update(status='RESOLVED',model_mae=statistics.mean(abs(p-b['close']) for p,b in zip(predicted,actual)),no_change_mae=statistics.mean(abs(reference-b['close']) for b in actual),target_absolute_error=abs(point-target),direction_correct=direction==bias,actual=direction,predicted=bias,available_at=validated['available_at'],outcome_sha256=sha(actual),existing_rule_price_error=None,existing_rule_reason='directional hypothesis has no point-price forecast; no fabricated point estimate',path_envelope_coverage=statistics.mean(min(p['bars'][n]['low'] for p in paths)<=b['low']<=b['high']<=max(p['bars'][n]['high'] for p in paths) for n,b in enumerate(actual)),range_label='three raw scenario envelope; not calibrated interval',earlier_session_mae=None)
                baselines=request.get('baselines') or {};tod=baselines.get('time_of_day') or {};mean=tod.get('mean_price');rule=baselines.get('deterministic_direction')
                row.update(earlier_session_target_error=abs(mean-target) if finite(mean) else None,earlier_session_count=tod.get('count_sessions',0),deterministic_direction_correct=(rule==direction) if rule in ('UP','DOWN') else None,deterministic_abstention=rule not in ('UP','DOWN'))
        rows.append(row)
    groups={}
    for key in sorted({(r['feed'],r['horizon']) for r in rows}):
        cohort=[r for r in rows if (r['feed'],r['horizon'])==key];valid=[r for r in cohort if r['status']=='RESOLVED'];days=defaultdict(list)
        for r in valid:days[r['day']].append(r['model_mae']-r['no_change_mae'])
        daily=[statistics.mean(v) for _,v in sorted(days.items())];rng=random.Random(1729);boot=sorted(statistics.mean(rng.choice(daily) for _ in daily) for _ in range(2000)) if len(daily)>1 else []
        groups[':'.join(key)]={'issued':len(cohort),'statuses':dict(Counter(r['status'] for r in cohort)),'independent_sessions':len(days),'correct':sum(r['direction_correct'] for r in valid),'resolved':len(valid),'paired_daily_mae_difference':statistics.mean(daily) if daily else None,'day_block_ci95':[boot[49],boot[1949]] if boot else None,'qualified':False,'reason':'No automatic promotion; prior dates consumed; checkpoint overlap unknown; genuine option evidence unavailable. All three horizons and previous trials retained.'}
    return {'version':VERSION,'rows':rows,'groups':groups,'trial_registry':'one pinned model × three horizons; 3 fixed seeds are paths, not strategy search','future_holdout':'first untouched sessions after frozen deployment; prior viewed dates DEVELOPMENT_ONLY','option_performance':'UNAVAILABLE','strategy_validated':False}
