"""Prospective underlying-only observations. Not options returns or live signals.

Fixed, versioned rules; no automatic promotion or parameter changes. Predictions
are created only on newly observed bars. Future outcomes cannot influence them.
"""
import json,hashlib,math
from datetime import datetime,timezone,timedelta
from core.storage import ROOT
from data.models import stamp
from monitoring.research_alerts import observe

VERSION='spy-5m-structure-forward-v1'
def verified_cache(raw):
    try:
        body=(ROOT/'data/public_cache'/(raw['sha256']+'.json')).read_bytes()
        from data.public_spy import parse_chart
        return hashlib.sha256(body).hexdigest()==raw['sha256'] and parse_chart(body)==raw['bars']
    except (OSError,KeyError,ValueError,TypeError):return False
def rows_from_disk():
    try:return json.loads((ROOT/'research/public_spy_latest.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def tick(store,snapshot,raw,session,now=None):
    now=now or datetime.now(timezone.utc)
    observation=observe(snapshot,session,now)
    if observation['quality']!='PUBLIC_RESEARCH_ONLY':return
    try:
        if raw['source']!=snapshot['source'] or raw['symbol']!='SPY' or raw['status']!='RESEARCH_DATA_RECEIVED' or raw['fetched_at']!=snapshot['source_fetched_at']:return
        rows=raw['bars'];digest=raw['sha256']
        if len(digest)!=64 or any(x not in '0123456789abcdef' for x in digest):return
        if not verified_cache(raw):return
        series={}
        for r in rows:
            ts=r['timestamp'];vals=[r[k] for k in ('open','high','low','close','volume')]
            if type(ts) is not int:return
            # Public charts can append a non-aligned current-price point. It is
            # not a completed5m bar and must never invalidate valid history.
            if ts+300>min(now.timestamp(),stamp(raw['fetched_at']).timestamp()):continue
            if ts%300 or any(type(v) not in (int,float) or not math.isfinite(v) for v in vals):return
            if not 0<r['low']<=min(r['open'],r['close'])<=max(r['open'],r['close'])<=r['high'] or r['volume']<=0:continue
            if ts in series:return
            series[ts]=r
        anchor=int(observation['bar'].timestamp());l=observation['levels']
        if anchor not in series or series[anchor]['close']!=l['last_close']:return
    except (KeyError,ValueError,TypeError,OverflowError):return
    # Settle prior observations only with the exact future bar and complete path.
    # A gap, revision or missing target stays unresolved; never interpolate it.
    for item in store.events('forward_study',10000):
        if store.get('forward_result:'+item['id']):continue
        end=item['target_bar_start'];start=item['anchor_bar_start']
        if end+300>now.timestamp():continue
        if any(ts not in series for ts in range(start,end+1,300)):continue
        if series[start]['close']!=item['anchor_close']:
            store.put('forward_result:'+item['id'],{'status':'SOURCE_REVISION_REJECTED','version':VERSION});continue
        price=series[end]['close'];change=(price/item['anchor_close']-1)*10000
        correct=None if item['direction']=='ABSTAIN' or change==0 else (change>0)==(item['direction']=='UP')
        result={'status':'OBSERVED','version':VERSION,'observed_at':now.isoformat(),'target_bar_start':end,'underlying_return_bps':change,'direction_correct':correct,'outcome_source_sha256':digest,'use':'UNDERLYING_RESEARCH_ONLY_NOT_OPTIONS_PNL'}
        store.put('forward_result:'+item['id'],result)
    if not session['active']:return
    last=store.get('forward_last',{})
    # Require the next anchor to follow the previous outcome bar. Merely spacing
    # issue times30minutes apart would still overlap delayed-price paths.
    prior_target=last.get('target',(int(last.get('issued_at',0))//300)*300+1800)
    if last and (anchor<=last['anchor'] or anchor<prior_target or now.timestamp()-last['issued_at']<1800):return
    direction='UP' if observation['trend']=='UPWARD 5m STRUCTURE' else 'DOWN' if observation['trend']=='DOWNWARD 5m STRUCTURE' else 'ABSTAIN'
    target=(int(now.timestamp())//300)*300+1800
    close=session['close_minute']
    from core.sessions import ET
    target_et=datetime.fromtimestamp(target+300,timezone.utc).astimezone(ET)
    if target_et.date().isoformat()!=session['date'] or target_et.hour*60+target_et.minute>close:return
    identity=hashlib.sha256((VERSION+str(anchor)+str(target)).encode()).hexdigest()[:32]
    record={'id':identity,'version':VERSION,'issued_at':now.isoformat(),'anchor_bar_start':anchor,'anchor_close':l['last_close'],'target_bar_start':target,'direction':direction,'trend':observation['trend'],'source_sha256':digest,'source_fetched_at':raw['fetched_at'],'option_prices':'UNAVAILABLE','scope':'PROSPECTIVE_UNDERLYING_ONLY','action':'NO TRADE'}
    if store.event(identity,'forward_study',record):store.audit('forward-'+identity,'prospective_research','worker',{'version':VERSION,'direction':direction,'action':'NO TRADE'})
    store.put('forward_last',{'anchor':anchor,'issued_at':now.timestamp(),'target':target})

def summary(store):
    items=store.events('forward_study',10000);results=[store.get('forward_result:'+x['id']) for x in items]
    observed=[x for x in results if x and x['status']=='OBSERVED'];directions=[x for x in observed if x['direction_correct'] is not None]
    return {'version':VERSION,'observations':len(items),'resolved':len(observed),'pending':sum(x is None for x in results),'revision_rejections':sum(bool(x and x['status']=='SOURCE_REVISION_REJECTED') for x in results),'abstentions':sum(x['direction']=='ABSTAIN' for x in items),'directional_trials':len(directions),'directional_accuracy':sum(x['direction_correct'] for x in directions)/len(directions) if directions else None,'limitations':'Delayed/unverified public5m bars. Underlying direction only; no option fills, costs or P&L. Small samples do not validate a strategy. No automatic live promotion.','action':'NO TRADE'}
