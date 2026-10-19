"""Prospective price-only ratio study. Future baseline avoids stale-price returns.

Records both the current rule and a majority-vote challenger; nothing promotes
a strategy automatically or supplies calibrated probabilities/options returns.
"""
import hashlib,math
from datetime import datetime,timezone,timedelta
from data.models import stamp,finite
from data.premarket_spy import verified,URL
from core.sessions import ET,market_session
from research.basic_trend import analyze
VERSION='spy-ratio-forward-v1'
def tick(store,raw,now=None):
    now=now or datetime.now(timezone.utc)
    try:
        if raw.get('source')!=URL or raw.get('symbol')!='SPY' or raw.get('status')!='RESEARCH_DATA_RECEIVED' or raw.get('use')!='DELAY_UNVERIFIED_RESEARCH_ONLY' or not verified(raw):return
        if not 0<=(now-stamp(raw['fetched_at'])).total_seconds()<=600:return
        rows={};last=None
        for b in raw['bars']:
            ts=b['timestamp']
            if type(ts) is not int or (last is not None and ts<=last):return
            last=ts
            if ts+300>min(now.timestamp(),stamp(raw['fetched_at']).timestamp()):continue
            if ts%300 or not all(finite(b.get(k)) for k in ('open','high','low','close','volume')) or not 0<b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] or b['volume']<0:return
            rows[ts]=b
    except (KeyError,TypeError,ValueError,OverflowError):return
    for item in store.events('ratio_study',10000):
        start=item['baseline_bar'];target=item['target_bar'];key='ratio_result:'+item['id'];old=store.get(key)
        if old:
            if old['status']=='OBSERVED' and start in rows and target in rows and (rows[start]['close']!=old['baseline_close'] or rows[target]['close']!=old['target_close']):
                store.put('ratio_revision:'+item['id'],{'status':'SOURCE_REVISION_REJECTED','observed_at':now.isoformat(),'sha256':raw['sha256']})
                store.audit('ratio-revision-'+item['id'],'ratio_source_revision','worker',{'version':VERSION,'sha256':raw['sha256']})
            continue
        if target+300>now.timestamp() or any(t not in rows for t in range(start,target+1,300)):continue
        base=rows[start]['close'];end=rows[target]['close'];ret=(end/base-1)*100
        direction='UP' if ret>0 else 'DOWN' if ret<0 else 'FLAT'
        result={'status':'OBSERVED','version':VERSION,'observed_at':now.isoformat(),'baseline_close':base,'target_close':end,'return_pct':ret,'outcome_direction':direction,'active_correct':None if item['active_direction']=='MIXED' or direction=='FLAT' else item['active_direction']==direction,'challenger_correct':None if item['challenger_direction']=='MIXED' or direction=='FLAT' else item['challenger_direction']==direction,'sha256':raw['sha256'],'meaning':'UNDERLYING_PRICE_ONLY_NOT_OPTION_WIN_RATE'}
        store.put(key,result);store.audit('ratio-outcome-'+item['id'],'prospective_ratio_outcome','worker',{'version':VERSION,'outcome':direction})
    r=analyze(raw,now)
    if r['direction']=='UNAVAILABLE':return
    # The entry baseline is a completed bar strictly AFTER the reading was made.
    start=(int(now.timestamp())//300+1)*300;target=start+900
    local=datetime.fromtimestamp(target+300,timezone.utc).astimezone(ET);session=market_session(now)
    close=570 if r['scope']=='PREMARKET' else session['close_minute']
    if local.date().isoformat()!=session['date'] or local.hour*60+local.minute>close:return
    prior=store.get('ratio_last',{})
    if prior and (start<=prior['target'] or stamp(r['as_of'])<=stamp(prior['as_of'])):return
    identity=hashlib.sha256((VERSION+r['as_of']+str(start)).encode()).hexdigest()[:32]
    record={'id':identity,'version':VERSION,'issued_at':now.isoformat(),'as_of':r['as_of'],'phase':r['scope'],'source_sha256':raw['sha256'],'baseline_bar':start,'target_bar':target,'active_direction':r['direction'],'challenger_direction':r['support']['lean'],'support':r['support'],'scope':'PROSPECTIVE_UNDERLYING_ONLY','action':'RESEARCH_ONLY'}
    if store.event(identity,'ratio_study',record):store.audit('ratio-issued-'+identity,'prospective_ratio_observation','worker',{'version':VERSION,'active':r['direction'],'challenger':r['support']['lean']})
    store.put('ratio_last',{'target':target,'as_of':r['as_of']})
def summary(store):
    items=store.events('ratio_study',10000);observed=[];pending=0;revisions=0
    for item in items:
        result=store.get('ratio_result:'+item['id'])
        if store.get('ratio_revision:'+item['id']):revisions+=1;continue
        if result and result['status']=='OBSERVED':observed.append((item,result))
        elif not result:pending+=1
    active=[r['active_correct'] for _,r in observed if r['active_correct'] is not None];challenger=[r['challenger_correct'] for _,r in observed if r['challenger_correct'] is not None]
    paired=[r for _,r in observed if r['active_correct'] is not None and r['challenger_correct'] is not None]
    wins=sum(not r['active_correct'] and r['challenger_correct'] for r in paired);losses=sum(r['active_correct'] and not r['challenger_correct'] for r in paired);n=wins+losses
    p=sum(math.comb(n,k) for k in range(wins,n+1))/2**n if n else 1.0
    review=len(paired)>=60 and wins>losses and p<.01
    groups={}
    for item,result in observed:
        label=item['phase']+'|'+str(item['support']['up_pct']);group=groups.setdefault(label,{'observations':0,'up':0,'down':0,'flat':0})
        group['observations']+=1;group[result['outcome_direction'].lower()]+=1
    return {'version':VERSION,'observations':len(items),'resolved':len(observed),'pending':pending,'revision_rejections':revisions,'active_trials':len(active),'active_correct':sum(active),'active_hit_pct':sum(active)/len(active)*100 if active else None,'challenger_trials':len(challenger),'challenger_correct':sum(challenger),'challenger_hit_pct':sum(challenger)/len(challenger)*100 if challenger else None,'paired_trials':len(paired),'challenger_only_wins':wins,'active_only_wins':losses,'paired_one_sided_p':p,'improvement_state':'CHALLENGER_READY_FOR_REVIEW' if review else 'COLLECTING_EVIDENCE','grouped_outcomes':groups,'automatic_promotion':False,'calibrated_probability':None,'limitations':'Public delayed/unverified prices; non-overlapping future paths; small samples are preliminary. Price-direction matches are not options profits. Hypothesis review is not validated prediction probability.'}
def text_for(s):
    lines=['TREND LEARNING: '+str(s['resolved'])+' completed observations; '+str(s['pending'])+' awaiting future prices.']
    if s['active_trials']:lines.append('Current-rule direction matches: %d/%d (%.1f%% of measured trials).'%(s['active_correct'],s['active_trials'],s['active_hit_pct']))
    if s['challenger_trials']:lines.append('Majority-vote challenger matches: %d/%d (%.1f%%).'%(s['challenger_correct'],s['challenger_trials'],s['challenger_hit_pct']))
    lines+=['These are observed underlying-price results, not chances of profit.','Improvement review: '+s['improvement_state']+'. Small samples remain preliminary.']
    return '\n'.join(lines)
