"""Frozen chronological underlying-only diagnostics, never live/option evidence.

Run against a separately frozen market-only export. The manifest is exclusively
written before any outcome computation. All reviewed dates remain development.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import random
import statistics

from core.sessions import ET, market_session
from features.indicators import normalize, from_normalized
from strategies.free_candidates import evaluate_shadow, RULES, RULE_HASH, VERSION
from strategies.idea_setups import detect as incumbent, VERSION as INCUMBENT_VERSION

STUDY_VERSION = 'free-spy-shadow-study-v1.1-no-sample'
POLICIES = ('INCUMBENT', 'ORB_5M', 'PULLBACK_5M_15M', 'FIXED_10_30_H60_LONG', 'FIXED_10_30_H60_SHORT')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def requested_sessions(start, end):
    first=datetime.fromisoformat(start).date();last=datetime.fromisoformat(end).date()
    if last < first:raise ValueError('INVALID_REQUESTED_WINDOW')
    result=[];day=first
    while day<=last:
        clock=datetime.combine(day,datetime.min.time(),ET).replace(hour=10)
        if market_session(clock).get('active'):result.append(day.isoformat())
        day+=timedelta(days=1)
    return result


def freeze_manifest(raw, start, end, availability_mode, config, now):
    if availability_mode not in ('RECORDED_RECEIPT','RETROSPECTIVE_CLOSE_ONLY'):
        raise ValueError('EXPLICIT_AVAILABILITY_MODE_REQUIRED')
    source=Path(__file__).resolve().parents[1]/'strategies/idea_setups.py'
    return {'study_version':STUDY_VERSION,'frozen_at':now.isoformat(),'rule_version':VERSION,
        'rule_hash':RULE_HASH,'incumbent_version':INCUMBENT_VERSION,
        'incumbent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'dataset_content_sha256':digest(raw),'requested_start':start,'requested_end':end,
        'requested_sessions':requested_sessions(start,end),'feed':'IEX','provider':'alpaca-iex',
        'availability_mode':availability_mode,'incumbent_config_sha256':digest(config),
        'reviewed_through':'2026-11-01','partition_rule':'All dates through2026-11-01 DEVELOPMENT_ONLY_ALREADY_REVIEWED; later sessions PROSPECTIVE_PENDING_REVIEW. No historical holdout is claimed untouched.',
        'decision_clock':'Completed5m ends,09:50 onward; same genuine minute prefix for all3strategy policies.',
        'one_primary_policy':'Each registered cell has at most1open plan and10minute same-direction cooldown; fixed arbitration and no overlapping exposure within cell.',
        'delays_seconds':RULES['study_delays_seconds'],'roundtrip_costs_per_share':RULES['study_roundtrip_cost_per_share_usd'],
        'trial_count':31,'prior_project_trials':'Additional prior trials retained; not a fresh isolated selection exercise.',
        'execution_proxy':'First available minute OPEN at or after issue+delay;15/30s both round up to same minute. No intraminute price or executable BBO evidence. Stop-first ambiguity and adverse gap fill.',
        'outcome_rules':'Stop orTarget2 ends plan; Target1 observation only. Deadline uses exact completed minute close. Missing any required post-entry minute makes outcome unresolved; no win/loss imputation.',
        'option_performance':'NOT_MEASURED','promote_winner':False,'broadcast':False,'live_ready':False}


def outcome(bars, idea, start, deadline, cost):
    """Conservative completed-minute path; gaps and missing outcomes stay visible."""
    by={int(b['timestamp']):b for b in bars};entrybar=by.get(start)
    if entrybar is None:return {'status':'MISSING_ENTRY','net_per_share':None}
    sign=1 if idea['direction']=='CALL' else -1;entry=entrybar['open']
    if (entry-idea['do_not_chase'])*sign>0:return {'status':'ENTRY_LIMIT_REFUSED','net_per_share':None}
    if (entry-idea['invalidation'])*sign<=0:return {'status':'INVALIDATED_BEFORE_ENTRY','net_per_share':None}
    target1=False
    for ts in range(start,int(deadline.timestamp()),60):
        bar=by.get(ts)
        if bar is None:return {'status':'UNRESOLVED_MISSING_MINUTE','net_per_share':None,'entry_at':start,'entry_price':entry,'missing_at':ts,'target1_observed':target1}
        stop=bar['low']<=idea['invalidation'] if sign==1 else bar['high']>=idea['invalidation']
        hit=bar['high']>=idea['t2'] if sign==1 else bar['low']<=idea['t2']
        t1=bar['high']>=idea['t1'] if sign==1 else bar['low']<=idea['t1'];target1=target1 or t1
        if stop:
            px=min(bar['open'],idea['invalidation']) if sign==1 else max(bar['open'],idea['invalidation'])
            status='AMBIGUOUS_STOP_TARGET_STOP_FIRST' if hit else 'INVALIDATION'
        elif hit:px=idea['t2'];status='TARGET2'
        else:continue
        return {'status':status,'entry_at':start,'exit_at':ts+60,'entry_price':entry,'exit_price':px,
            'net_per_share':(px-entry)*sign-cost,'target1_observed':target1,'cost_per_share':cost}
    final=by.get(int(deadline.timestamp())-60)
    if final is None:return {'status':'UNRESOLVED_DEADLINE_PRICE','net_per_share':None,'entry_at':start,'entry_price':entry,'target1_observed':target1}
    return {'status':'H60_DEADLINE','entry_at':start,'exit_at':int(deadline.timestamp()),'entry_price':entry,'exit_price':final['close'],
        'net_per_share':(final['close']-entry)*sign-cost,'target1_observed':target1,'cost_per_share':cost}


def summarize(trades, days):
    closed=[r for r in trades if r.get('net_per_share') is not None]
    totals={day:0.0 for day in days};bydir={}
    for row in closed:totals[row['day']]+=row['net_per_share']
    for direction in ('CALL','PUT'):
        values=[r['net_per_share'] for r in closed if r['direction']==direction]
        bydir[direction]={'closed':len(values),'net_per_share_sum':sum(values),'mean_per_share':statistics.mean(values) if values else None}
    equity=peak=drawdown=0.0
    for row in sorted(closed,key=lambda r:(r['entry_at'],r['signal_id'])):
        equity+=row['net_per_share'];peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
    rng=random.Random(20261101);keys=sorted(totals)
    boot=sorted(sum(totals[rng.choice(keys)] for _ in keys)/len(keys) for _ in range(1000)) if len(keys)>=2 and len(closed)>=2 else []
    return {'plans':len(trades),'closed':len(closed),'unresolved_or_refused':len(trades)-len(closed),
        'net_per_share_sum':sum(r['net_per_share'] for r in closed) if closed else None,
        'net_expectancy_per_closed':statistics.mean(r['net_per_share'] for r in closed) if closed else None,
        'max_drawdown_per_share':drawdown if closed else None,'requested_independent_sessions':len(days),
        'active_sessions':len({r['day'] for r in trades}),'closed_active_sessions':len({r['day'] for r in closed}),
        'day_block_mean_ci95':[boot[24],boot[974]] if boot else None,
        'direction_strata':bydir,'status_counts':dict(Counter(r['status'] for r in trades)),
        'turnover_entries':len([r for r in trades if 'entry_at' in r]),
        'uncertainty_limit':'Descriptive retrospective day-block interval; not multiple-trial corrected, calibrated, option-level or independent holdout qualification.'}


def run(raw, manifest, config):
    if digest(raw)!=manifest['dataset_content_sha256'] or manifest['rule_hash']!=RULE_HASH:
        raise ValueError('FROZEN_INPUT_OR_RULE_MISMATCH')
    feed=manifest['feed'];provider=manifest['provider'];mode=manifest['availability_mode']
    # Preserve original receipt fields alongside normalized prices.
    normalized=normalize(raw,now=datetime.now(timezone.utc));metadata={}
    for row in raw:
        ts=int(datetime.fromisoformat(row['t'].replace('Z','+00:00')).timestamp()) if 't' in row else int(row['timestamp'])
        metadata[ts]={k:row[k] for k in ('provider','feed_quality','source','recorded_at','available_at') if k in row}
    groups=defaultdict(list)
    for bar in normalized:
        day=datetime.fromtimestamp(bar['timestamp'],timezone.utc).astimezone(ET).date().isoformat()
        groups[day].append(dict(bar,**metadata.get(int(bar['timestamp']),{})))
    audit=[];detections=Counter();candidate_rows=defaultdict(list);alltrades={};partition={}
    for day in manifest['requested_sessions']:
        today=groups.get(day,[]);clock=datetime.fromisoformat(day).replace(hour=10,tzinfo=ET)
        session=market_session(clock);expected=session['close_minute']-570
        missing_receipt=sum(not (b.get('recorded_at') or b.get('available_at')) for b in today)
        audit.append({'day':day,'expected_minutes':expected,'recorded_minutes':len(today),'missing_minutes':expected-len(today),
            'receipt_missing_minutes':missing_receipt,'complete':len(today)==expected,'partition':'DEVELOPMENT_ONLY_ALREADY_REVIEWED' if day<=manifest['reviewed_through'] else 'PROSPECTIVE_PENDING_REVIEW'})
        partition[day]=audit[-1]['partition']
        if mode=='RECORDED_RECEIPT' and missing_receipt:
            detections['NO_DECISION_TIME_RECEIPTS:'+day]+=1;continue
        for index in range(19,len(today)):
            last=today[index];issue=datetime.fromtimestamp(last['timestamp']+60,timezone.utc)
            if (issue.astimezone(ET).minute%5):continue
            prefix=today[:index+1]
            result=evaluate_shadow(prefix,issue,feed=feed,provider=provider,availability_mode=mode)
            detections[result.get('reason') or 'CANDIDATE_CONFIRMATION']+=1
            for idea in result['candidates']:candidate_rows[day].append(dict(idea,policy=idea['setup_type']))
            # Same exact genuine prefix requirement applies to incumbent too.
            if result.get('reason') in ('GENUINE_SESSION_PREFIX_GAP','COMPLETED_BAR_AGE','OUTSIDE_REGULAR_SESSION'):
                continue
            try:
                fs=from_normalized(prefix,[],issue);px=last['close'];q={'provider':provider,'payload':{'mid':px},'source_timestamp':issue.isoformat()}
                choices=incumbent(fs,prefix,q,issue,config,len(prefix)<31 and issue.astimezone(ET).hour*60+issue.astimezone(ET).minute<=600)
                # Existing loop order is the frozen incumbent conflict arbitration.
                for order,idea in enumerate(choices):candidate_rows[day].append(dict(idea,policy='INCUMBENT',_order=order))
            except (ValueError,TypeError,KeyError):detections['INCUMBENT_FEATURES_UNAVAILABLE']+=1
        for policy,sign in [('FIXED_10_30_H60_LONG',1),('FIXED_10_30_H60_SHORT',-1)]:
            issue=clock.replace(hour=10,minute=30).astimezone(timezone.utc);reference=next((b['close'] for b in today if b['timestamp']==issue.timestamp()-60),None)
            if reference is None:continue
            # Baselines have no stop/target threshold; H60 only. Very distant
            # positive bounds avoid a nominal stop being mistaken for a real risk policy.
            candidate_rows[day].append({'signal_id':digest([policy,day])[:24],'policy':policy,'direction':'CALL' if sign==1 else 'PUT',
                'timestamp':issue.isoformat(),'signal_expiry':(issue+timedelta(seconds=60)).isoformat(),'max_hold_until':(issue+timedelta(minutes=60)).isoformat(),
                'do_not_chase':reference+sign*reference,'invalidation':.000001 if sign==1 else reference*1000,
                't1':reference*1000 if sign==1 else .000001,'t2':reference*1000 if sign==1 else .000001})
    for policy in POLICIES:
        for delay in RULES['study_delays_seconds']:
            for cost in RULES['study_roundtrip_cost_per_share_usd']:
                key=f'{policy}:delay{delay}:cost{cost:.2f}';trades=[]
                for day in manifest['requested_sessions']:
                    occupied=0;cooldown={};seen=set();today=groups.get(day,[])
                    choices=sorted((r for r in candidate_rows[day] if r['policy']==policy),key=lambda r:(r['timestamp'],r.get('_order',0),r['signal_id']))
                    for idea in choices:
                        if idea['signal_id'] in seen:continue
                        seen.add(idea['signal_id']);issue=datetime.fromisoformat(idea['timestamp']);expiry=datetime.fromisoformat(idea['signal_expiry']);deadline=datetime.fromisoformat(idea['max_hold_until'])
                        if issue.timestamp()<occupied or issue.timestamp()<cooldown.get(idea['direction'],0):continue
                        start=math.ceil((issue.timestamp()+delay)/60)*60
                        if start>=expiry.timestamp() or start>=deadline.timestamp():
                            trades.append({'signal_id':idea['signal_id'],'day':day,'direction':idea['direction'],'status':'ENTRY_EXPIRED_AFTER_DELAY','net_per_share':None});continue
                        result=outcome(today,idea,start,deadline,cost)
                        trades.append(dict(result,signal_id=idea['signal_id'],day=day,direction=idea['direction'],partition=partition[day]))
                        if 'entry_at' in result:
                            occupied=result.get('exit_at',deadline.timestamp());cooldown[idea['direction']]=issue.timestamp()+RULES['cooldown_minutes']*60
                alltrades[key]=trades
    return {'manifest':manifest,'coverage':audit,'detection_counts':dict(detections),
        'results':{key:summarize(trades,manifest['requested_sessions']) for key,trades in alltrades.items()},
        'no_trade_baseline':{'net_per_share':0,'turnover':0,'trial_count':1},
        'trades':alltrades,'option_performance':'NOT_MEASURED','winner':'NOT_SELECTED',
        'strategy_validated':False,'live_ready':False,
        'limits':['Historical receipt times absent from supplied current-state bars; CLOSE_ONLY is an explicit retrospective idealized availability diagnostic, not live evidence.',
            'Incumbent arithmetic is unchanged but only same-session minute-derived features supplied; historical native/daily context and actual production eligibility are not reconstructed.',
            'Missing requested dates/minutes are retained in coverage; conditional proxy results suffer data selection bias.',
            'Entry expiry is strict: minute-open rounding can make all15/30/60second paths expire for a60second window. No favorable fill is invented.',
            'No calibrated forecast, executable underlying BBO, option contract return or profitability/readiness selection follows from this diagnostic.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bars-export',required=True);parser.add_argument('--start',required=True);parser.add_argument('--end',required=True)
    parser.add_argument('--availability-mode',required=True,choices=('RECORDED_RECEIPT','RETROSPECTIVE_CLOSE_ONLY'));parser.add_argument('--output',required=True);args=parser.parse_args()
    path=Path(args.bars_export)
    if path.stat().st_size>64*1024*1024:raise ValueError('INPUT_SIZE_LIMIT')
    source=json.loads(path.read_text());raw=source['bars']
    if source.get('feed')!='IEX' or source.get('provider')!='alpaca-iex':raise ValueError('EXPLICIT_MATCHING_IEX_EXPORT_REQUIRED')
    root=Path(__file__).resolve().parents[1];config=json.loads((root/'config/upgrade.json').read_text());output=Path(args.output)
    manifest=freeze_manifest(raw,args.start,args.end,args.availability_mode,config,datetime.now(timezone.utc));manifest['export_file_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    with output.with_suffix('.manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
    result=run(raw,manifest,config)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'coverage':result['coverage'],'results':result['results'],'winner':result['winner'],'option_performance':result['option_performance']}))


if __name__=='__main__':main()
