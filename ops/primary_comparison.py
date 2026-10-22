"""Frozen chronological underlying comparison. Never option qualification."""
import argparse,json,sqlite3,hashlib,statistics,random,math
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
from core.sessions import ET,market_session
from features.indicators import normalize,resample,calculate,from_normalized
from strategies.concretum import complete,session_replay
from strategies.idea_setups import detect
from core.research_horizons import deadline
from ops.alert_audit import path_outcome
VERSION='primary-comparison-frozen-v3-source-pairing'

def summarize(trades):
 vals=[t['net_per_share'] for t in trades];by=defaultdict(float)
 for t in trades:by[t['day']]+=t['net_per_share']
 days=sorted(by);total=sum(vals);equity=0;peak=0;dd=0
 for t in trades:equity+=t['net_per_share'];peak=max(peak,equity);dd=max(dd,peak-equity)
 rng=random.Random(22026);boot=[sum(by[rng.choice(days)] for _ in days)/len(days) for _ in range(1000)] if len(days)>=2 else [];boot.sort()
 return {'trades':len(vals),'independent_active_days':len(days),'net_per_share_sum':total,'mean_per_share':statistics.mean(vals) if vals else None,'profit_factor':sum(x for x in vals if x>0)/-sum(x for x in vals if x<0) if any(x<0 for x in vals) else None,'max_drawdown_per_share':dd,'day_block_mean_ci95':[boot[24],boot[974]] if boot else None,'familywise_uncertainty':'No qualification: 27 registered variants plus prior project trials; CI descriptive, not corrected selection evidence.','by_day':dict(by)}

def run(raw,dividends=None,dividend_basis='UNAVAILABLE',frozen=None):
 bars=normalize(raw,now=datetime.now(timezone.utc));groups=defaultdict(list)
 for b in bars:groups[datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date().isoformat()].append(b)
 days=sorted(groups);valid=[d for d in days if complete(groups[d])];n=len(valid);a=int(n*.6);b=int(n*.8)
 partitions={'development':valid[:a],'validation_retrospective':valid[a:b],'evaluation_retrospective':valid[b:]}
 for name in partitions:partitions[name]=[d for d in partitions[name] if d!='2026-10-21']
 if '2026-10-21' in valid:partitions['development'].append('2026-10-21')
 if frozen is not None:
  partitions=frozen['partitions']
  if set(partitions)!={'development','validation_retrospective','evaluation_retrospective'}:raise ValueError('FROZEN_PARTITIONS_INVALID')
  declared=[d for values in partitions.values() for d in values]
  if len(declared)!=len(set(declared)) or any(d not in groups for d in declared) or any('2026-10-21' in values for k,values in partitions.items() if k!='development'):raise ValueError('FROZEN_PARTITIONS_INVALID')
 split={d:k for k,v in partitions.items() for d in v};prior=[];alltrades=defaultdict(list);missing=Counter();counts=Counter()
 manifest={'version':VERSION,'source_sha256':hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest(),'partitions':partitions,'oct21':'DEVELOPMENT_ONLY_ALREADY_REVIEWED','cut_rule':'60/20/20 full chronological sessions; overnight flat; no outcome crosses session/split boundary','decision_clock':'30-minute matched-cadence diagnostic; current 10-second production is different','trials':27,'delays_seconds':[15,30,60],'horizons':['H60','H120','SESSION'],'dividend_basis':dividend_basis,'frozen_parent_manifest_sha256':hashlib.sha256(json.dumps(frozen,sort_keys=True).encode()).hexdigest() if frozen else None,'costs':'Concretum .0035 commission + .001 slippage each side; current underlying .03 roundtrip sensitivity; not option costs','criteria':'No production promotion. Require untouched later sessions, broader coverage and genuine option evaluation.'}
 for day in days:
  today=groups[day]
  if day not in valid or day not in split:prior.append(today);continue
  previous=prior[-1][-1]['close'] if prior else None;div=(dividends or {}).get(day)
  label='development' if day=='2026-10-21' else split[day]
  for stop in ('OPPOSITE_BAND','CURRENT_BAND_VWAP'):
   for h,mins in [('H60',60),('H120',120),('SESSION',None)]:
    for delay in (15,30,60):
     key='CONCRETUM:'+stop+':'+h+':'+str(delay);r=session_replay(today,prior,previous,div,delay,stop,mins)
     counts[key+':'+r['status']]+=1
     if r['status']=='UNAVAILABLE':missing[r['reason']]+=1
     for t in r['trades']:alltrades[key+':'+label].append(dict(t,day=day))
  # Existing deterministic setup code, frozen 30m comparison clock. Recomputes
  # only completed prefixes and independent horizon populations; one open plan.
  preceding=[x for d in prior[-14:] for x in d]
  daily=[dict(timestamp=d[0]['timestamp'],open=d[0]['open'],high=max(x['high'] for x in d),low=min(x['low'] for x in d),close=d[-1]['close'],volume=sum(x['volume'] for x in d)) for d in prior]
  occupied={};registered=set()
  for m in range(30,len(today),30):
   observed=today[:m];issue=datetime.fromtimestamp(observed[-1]['timestamp']+60,timezone.utc);fs=from_normalized(preceding+observed,daily,issue);px=observed[-1]['close'];q={'provider':'alpaca-iex','payload':{'mid':px},'source_timestamp':issue.isoformat()}
   choices=detect(fs,observed,q,issue,{},False)
   for h in ('H60','H120','SESSION'):
    end=deadline(issue,h)
    if not end:continue
    for delay in (15,30,60):
     key='CURRENT:'+h+':'+str(delay)
     if occupied.get(key,0)>issue.timestamp():continue
     for idea in choices:
      if (key,idea['signal_id']) in registered:continue
      start=math.ceil((issue.timestamp()+delay)/60)*60;entry=next((x for x in today if x['timestamp']==start),None)
      if not entry or start>=end.timestamp():continue
      sign=1 if idea['direction']=='CALL' else -1
      if (entry['open']-idea['do_not_chase'])*sign>0 or (entry['open']-idea['invalidation'])*sign<=0:continue
      outcome=path_outcome([x for x in today if x['timestamp']>=start],entry['open'],idea['invalidation'],idea['t2'],sign,end)
      exitat=datetime.fromisoformat(outcome['bar_end']).timestamp() if outcome['bar_end'] else end.timestamp();exitbar=next((x for x in today if x['timestamp']==exitat-60),None)
      if outcome['result']=='AMBIGUOUS_STOP_TARGET':missing['current_same_bar_ambiguous_stop_first']+=1
      exitprice=idea['invalidation'] if outcome['result'] in ('INVALIDATION','AMBIGUOUS_STOP_TARGET') else idea['t2'] if outcome['result']=='TARGET' else exitbar['close'] if exitbar else None
      if exitprice is None:missing['current_missing_exit']+=1;continue
      alltrades[key+':'+label].append({'day':day,'entry_at':start,'exit_at':exitat,'side':sign,'setup':idea['setup_type'],'net_per_share':(exitprice-entry['open'])*sign-.03});occupied[key]=exitat;registered.add((key,idea['signal_id']));break
  prior.append(today)
 return {'manifest':manifest,'coverage':{'raw_rows':len(raw),'regular_rows':len(bars),'sessions':n,'incomplete_excluded':[d for d in days if d not in valid]},'availability':dict(counts),'exclusions':dict(missing),'results':{k:summarize(v) for k,v in alltrades.items()},'option_performance':'UNAVAILABLE','qualified':False,'limits':['Input provenance is declared separately; no replication of the published full-span returns.','Historical bars downloaded later do not prove contemporaneous availability.','Current H120/SESSION are registered adaptations, not validated extensions.','15/30s round up to next available minute-open proxy, no executable BBO.','Dividends unavailable unless explicitly supplied; scheduled-dividend sensitivity is not verified corporate-action completeness.','All reported intervals are descriptive; no trial winner or automatic promotion.']}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);sources=p.add_mutually_exclusive_group(required=True);sources.add_argument('--database');sources.add_argument('--bars-export');p.add_argument('--output',required=True);p.add_argument('--dividends');p.add_argument('--frozen-manifest');a=p.parse_args()
 if a.database:
  db=sqlite3.connect(Path(a.database).resolve().as_uri()+'?mode=ro',uri=True);v=db.execute("select payload from state where key='research_stream_bars:SPY:iex'").fetchone();db.close();raw=json.loads(v[0]) if v else []
 else:
  source=Path(a.bars_export)
  if source.stat().st_size>64*1024*1024:raise ValueError('HISTORICAL_EXPORT_TOO_LARGE')
  data=json.loads(source.read_text());raw=data['bars']
  if data.get('capture_mode')!='HISTORICAL_DOWNLOAD':raise ValueError('HISTORICAL_CAPTURE_LABEL_REQUIRED')
 d=json.loads(Path(a.dividends).read_text()) if a.dividends else {};r=run(raw,d.get('dividends'),d.get('basis','UNAVAILABLE'),json.loads(Path(a.frozen_manifest).read_text()) if a.frozen_manifest else None);Path(a.output).write_text(json.dumps(r,indent=2));print(json.dumps({'coverage':r['coverage'],'results':r['results'],'exclusions':r['exclusions']},indent=2))
