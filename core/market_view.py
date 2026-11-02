"""One versioned, deterministic product snapshot. No model grants entry permission."""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone,timedelta
import hashlib,json
from core.sessions import ET,market_session
from core.directional_research import view,VERSION as TREND_VERSION
from data.models import finite,stamp

VERSION='market-view-v2-free-underlying'
SCENARIO_VERSION='h60-vwap-condition-v3-free'
DESCRIPTIVE_MAX_BAR_AGE_SECONDS=120

@dataclass(frozen=True)
class PriceView:
    value:float|None
    kind:str
    source_at:str|None
    received_at:str|None
    provider:str
    quote_eligible:bool

@dataclass(frozen=True)
class TrendView:
    state:str
    as_of:str|None
    observation_window_minutes:int
    rule_version:str
    reason:str
    descriptive_only:bool

@dataclass(frozen=True)
class OutlookView:
    horizon:str
    bias:str
    target_at:str|None
    reference:float|None
    invalidation:float|None
    basis:str
    reason:str|None
    rule_version:str=SCENARIO_VERSION

@dataclass(frozen=True)
class EntryView:
    state:str
    reason:str
    underlying_eligible:bool
    calendar_eligible:bool
    option_eligible:bool

@dataclass(frozen=True)
class PremarketView:
    opening_hour_lean:str
    session_lean:str
    current_premarket:bool
    reference:float|None
    high:float|None
    low:float|None
    source_at:str|None
    quality:str
    reference_kind:str

@dataclass(frozen=True)
class RecapView:
    day:str
    alerted:int
    confirmed:int
    closed:int
    open:int
    unresolved:int
    cancelled:int
    silent_observations:int
    carried_in:int=0
    administratively_closed_unresolved:int=0
    option_performance:str='UNAVAILABLE_WITHOUT_GENUINE_QUOTES'

@dataclass(frozen=True)
class MarketView:
    schema_version:str
    snapshot_id:str
    generated_at:str
    session:str
    price:PriceView
    trend:TrendView
    outlooks:dict[str,OutlookView]
    entry:EntryView
    primary_plan:dict|None
    option_data:str
    evidence:dict
    premarket:dict|None=None
    recap:dict|None=None
    live_signal_ready:bool=False
    order_execution_enabled:bool=False

def premarket_view(report,now):
    levels=report.get('levels') or {};source=report.get('as_of_bar') or report.get('as_of');quality=report.get('quality','DATA UNAVAILABLE');px=levels.get('last')
    try:current=stamp(source).astimezone(ET).date()==now.astimezone(ET).date() and 0<=(now-stamp(source)).total_seconds()<=900
    except (ValueError,TypeError):current=False
    usable=current and finite(px) and quality in ('IEX_RESEARCH_ONLY','PUBLIC_RESEARCH_ONLY','SIMULATED')
    lean={'BULLISH':'UP','BEARISH':'DOWN','UP':'UP','DOWN':'DOWN'}.get(report.get('bias'),'UNCLEAR') if usable else 'UNCLEAR'
    return asdict(PremarketView(lean,'UNCLEAR',current,px if finite(px) else None,levels.get('high') if finite(levels.get('high')) else None,levels.get('low') if finite(levels.get('low')) else None,source,quality,'CURRENT_PREMARKET_BAR_RESEARCH' if usable else 'PRIOR_CLOSE_PROJECTION_OR_UNAVAILABLE'))

def recap_view(rows,now,closures=()):
    day=now.astimezone(ET).date();today=[r for r in rows if stamp(r['timestamp']).astimezone(ET).date()==day];alerted=[r for r in today if r.get('alerted')]
    closed=sum(r.get('status')=='CLOSED' for r in alerted);open_=sum(r.get('status') in ('OPEN','PENDING') and r.get('coverage_status')!='UNRESOLVED_GAP' for r in alerted)
    unresolved=sum(r.get('coverage_status')=='UNRESOLVED_GAP' or r.get('status') not in ('CLOSED','OPEN','PENDING','EXPIRED','EXPIRED_NO_ENTRY','CANCELLED') for r in alerted)
    cancelled=sum(r.get('status') in ('EXPIRED','EXPIRED_NO_ENTRY','CANCELLED') for r in alerted)
    retired={r['signal_id'] for r in closures};retired_today={r['signal_id'] for r in closures if stamp(r['at']).astimezone(ET).date()==day}
    admin=sum(r['signal_id'] in retired and r.get('status') in ('OPEN','PENDING') for r in alerted)
    carried=[r for r in rows if r.get('alerted') and stamp(r['timestamp']).astimezone(ET).date()<day and (r.get('status') in ('OPEN','PENDING') and r['signal_id'] not in retired or r['signal_id'] in retired_today or r.get('closed_at') and stamp(r['closed_at']).astimezone(ET).date()==day)]
    open_-=sum(r['signal_id'] in retired and r.get('status') in ('OPEN','PENDING') and r.get('coverage_status')!='UNRESOLVED_GAP' for r in alerted)
    unresolved=sum(r.get('coverage_status')=='UNRESOLVED_GAP' or r['signal_id'] in retired and r.get('status') in ('OPEN','PENDING') or r.get('status') not in ('CLOSED','OPEN','PENDING','EXPIRED','EXPIRED_NO_ENTRY','CANCELLED') for r in alerted)
    return asdict(RecapView(day.isoformat(),len(alerted),sum(bool(r.get('opened_at')) for r in alerted),closed,open_,unresolved,cancelled,len(today)-len(alerted),len(carried),admin))

def plan_view(plan,now,monitoring_available=False):
    from core.primary_plan import state,public_state,administrative_end
    primary={k:plan.get(k) for k in ('signal_id','direction','horizon_id','horizon','strategy_version','timestamp','confirmation_at','confirmation_bar_start','confirmation_timeframe','decision_at','market_timestamp','quote_received_at','entry_condition','planned_holding_minutes','entry_mode','trigger_level','trigger','reference_midpoint','entry','modeled_entry_fill','invalidation','t1','t2','do_not_chase','signal_expiry','max_hold_until','coverage_status','last_observed_bar')}
    primary.update(state=state(plan,now),public_state=public_state(plan,now,monitoring_available),administrative_end=administrative_end(plan).isoformat(),monitoring_available=monitoring_available,meaning='RESEARCH_PLAN; no personal fill or sale inferred')
    return primary

def observed_research(ctx,now):
    """Bound the descriptive path independently, never override entry predicates.

    The incumbent VWAP/change rule is preserved. The adapter additionally checks
    the exact 15-minute endpoints, genuine constituents and current RTH session.
    Provider arrival/availability remains separate from candle close time.
    """
    result=view(ctx,now);bar=ctx.get('bar_research') or {}
    rows=bar.get('bars',[]) if not bar.get('reason') else ctx.get('bars',[]) if ctx.get('early') and not ctx.get('reason') else []
    reason=None
    if len(rows)<16:reason='exact 15-minute completed-price endpoints unavailable'
    else:
        tail=rows[-16:]
        for row in tail:
            try:
                at=datetime.fromtimestamp(row['timestamp'],timezone.utc)
                if at.astimezone(ET).date()!=now.astimezone(ET).date() or not market_session(at)['active']:reason='completed bars are outside the current regular session';break
                if row.get('synthetic') or row.get('continuity_only') or row.get('confirmed_empty') or row.get('quality') in ('SYNTHETIC','CONTINUITY_ONLY'):
                    reason='genuine completed bars required; continuity slots are not prices';break
                if row.get('available_at') and stamp(row['available_at'])>now:reason='completed bar was not available at evaluation';break
            except (KeyError,ValueError,TypeError,OverflowError):reason='invalid completed-bar timestamp';break
        if not reason and not 0<=now.timestamp()-tail[-1]['timestamp']-60<=DESCRIPTIVE_MAX_BAR_AGE_SECONDS:reason='completed bar older than 120 seconds or unfinished'
    if reason:
        result=dict(result,trend='DATA UNAVAILABLE',price=None,as_of=None,reason=reason,invalidation=None,outlooks={})
    return result

def plain_reason(text):
    text=str(text or '')
    if text.startswith(('BUY CALL','BUY PUT')):return 'underlying watch; option gates separate'
    for needle,label in (('data not fresh','fresh price unavailable'),('quote','fresh price unavailable'),('SOURCE','fresh price unavailable'),('RECEIPT','fresh price unavailable'),('CLOCK','clock verification failed'),('HEARTBEAT','feed heartbeat unavailable'),('STREAM','feed disconnected'),('BAR_','completed minutes missing'),('history','completed minutes missing'),('COOL','research pause active'),('research pause','research pause active'),('DIRECTION_COOLDOWN','similar plan recently alerted'),('PRIMARY_PLAN','one primary plan already active'),('calendar','event calendar unavailable'),('blackout','major event blackout')):
        if needle in text:return label
    return text.removeprefix('NO TRADE — ').replace('_',' ').lower()[:90] or 'confirmation missing'

def h60_scenario(ctx,now,research):
    """Separate frozen hypothesis: completed 5m and 15m moves plus VWAP.

    This does not reuse the current-trend label. Missing complete frames abstain;
    disagreement is MIXED. It has no calibrated forecast or profitability claim.
    """
    from features.indicators import resample
    bar=ctx.get('bar_research') or {};rows=bar.get('bars') or []
    out={'bias':'ABSTAIN','target_at':None,'invalidation':None,'reason':'complete five-/fifteen-minute scenario evidence unavailable'}
    if research.get('trend')=='DATA UNAVAILABLE' or bar.get('reason'):return out
    five=resample(rows,5);fifteen=resample(rows,15)
    vwap=(bar.get('features') or {}).get('1m',{}).get('vwap_approx')
    if len(five)<2 or len(fifteen)<2 or not finite(vwap) or vwap<=0:return out
    d5=five[-1]['close']-five[-2]['close'];d15=fifteen[-1]['close']-fifteen[-2]['close'];last=rows[-1]['close']
    bias='UP' if d5>0 and d15>0 and last>vwap else 'DOWN' if d5<0 and d15<0 and last<vwap else 'SIDEWAYS' if d5==0 and d15==0 else 'MIXED'
    session=market_session(now);close=now.astimezone(ET).replace(hour=session['close_minute']//60,minute=session['close_minute']%60,second=0,microsecond=0)
    target=now+timedelta(minutes=60)
    if not session['active'] or target>close:return dict(out,reason='full next hour does not fit verified regular session')
    return {'bias':bias,'target_at':target.isoformat(),'invalidation':vwap,'reason':None,'delta_5m':d5,'delta_15m':d15}

def build(ctx,news,now,config=None,plan=None,entry_reason=None):
    """Pure constructor shared by scheduled/on-demand/dashboard representations.

    A completed-bar price is explicitly distinct from a fresh quote. Option
    absence never deletes a descriptive trend. Missing price inputs abstain.
    """
    if now.tzinfo is None:raise ValueError('AWARE_TIME_REQUIRED')
    config=config or {};research=observed_research(ctx,now);session=market_session(now)
    from core.signals import quote_valid
    q=ctx.get('quote') or {};fresh=quote_valid(q,now,5)
    payload=q.get('payload') or {};mid=payload.get('mid')
    fresh=bool(fresh and finite(mid) and mid>0)
    source=q.get('source_timestamp') if fresh else research.get('as_of')
    received=q.get('received_timestamp') if fresh else None
    px=mid if fresh else research.get('price')
    provider=ctx.get('feed_quality','UNAVAILABLE') if fresh else research.get('provider','UNAVAILABLE')
    price=PriceView(px if finite(px) else None,'FRESH_QUOTE_REFERENCE' if fresh else 'COMPLETED_BAR_CLOSE' if finite(px) else 'UNAVAILABLE',source,received,provider,fresh)
    state=research.get('trend','UNAVAILABLE')
    if state=='DATA UNAVAILABLE':state='UNAVAILABLE'
    trend=TrendView(state,research.get('as_of'),research.get('window_minutes',0),TREND_VERSION,research.get('reason') or 'usable completed-price evidence',not fresh or bool(ctx.get('reason')))
    underlying=bool(session['active'] and not ctx.get('reason') and fresh)
    calendar=bool(news.get('quality')=='DATA_OK' and news.get('risk') in ('NORMAL','MODERATE'))
    why='market closed' if not session['active'] else plain_reason(ctx.get('reason') or 'fresh price unavailable') if not underlying else 'event calendar unavailable' if news.get('quality')!='DATA_OK' else 'major event blackout' if not calendar else plain_reason(entry_reason)
    primary=None
    if plan:
        primary=plan_view(plan,now,underlying)
        why='one primary plan already active' if underlying else why
    entry_state='WAIT'
    if underlying and calendar and not plan and entry_reason and str(entry_reason).startswith('setup confirmed'):entry_state='WATCH'
    from options.research_contract import current_reference
    option=current_reference(plan,now,config) if plan else None
    option_data='UNAVAILABLE — separate real option gates required'
    if option:
        c,p=option;option_data='VERIFIED_QUOTE_REFERENCE_ONLY; strategy remains unvalidated'
        primary['option_reference']={'symbol':c['symbol'],'expiry':c['expiry'],'strike':c['strike'],'right':c['type'],'bid':c['bid'],'ask':c['ask'],'source_at':c['quote']['source_timestamp'],'provider':c['quote']['provider'],'premium_at_risk':p['limit']*100,'multiplier':100,'personal_fill':False}
    entry=EntryView(entry_state,why,underlying,calendar,bool(option and underlying and calendar))
    outlooks={};scenario=h60_scenario(ctx,now,research)
    for h in ('H60','H120','SESSION'):
        o=scenario if h=='H60' else {}
        available=bool(h=='H60' and underlying and o.get('target_at') and o.get('bias') in ('UP','DOWN','MIXED','SIDEWAYS'))
        missing='separate horizon scenario not issued by this version' if h!='H60' else 'fresh underlying unavailable' if not underlying else o.get('reason') or 'insufficient session time or evidence'
        outlooks[h]=OutlookView(h,o.get('bias') if available else 'ABSTAIN',o.get('target_at') if available else None,mid if available else None,o.get('invalidation') if available else None,'Conditional H60 hypothesis while the measured VWAP invalidation holds; not calibrated',None if available else missing)
    evidence={'underlying_reason':ctx.get('reason'),'quote_diagnostics':ctx.get('diagnostics',[]),'heartbeat_age_seconds':ctx.get('heartbeat_age_seconds'),'bar_end_age_seconds':ctx.get('bar_end_age_seconds'),'descriptive_bar_age_limit_seconds':DESCRIPTIVE_MAX_BAR_AGE_SECONDS,'descriptive_minimum_endpoint_bars':16,'confirmed_empty_continuity_slots':ctx.get('synthetic_continuity_minutes',0),'early_limited':bool(ctx.get('early')),'trend_components':research.get('components',{}),'calendar_quality':news.get('quality'),'calendar_risk':news.get('risk'),'options_separate':True,'source_population':ctx.get('feed_quality','UNAVAILABLE')}
    ident={'schema':VERSION,'at':now.isoformat(),'price':asdict(price),'trend':asdict(trend),'entry':asdict(entry),'plan':primary,'outlooks':{k:asdict(v) for k,v in outlooks.items()}}
    digest=hashlib.sha256(json.dumps(ident,sort_keys=True,allow_nan=False,default=str).encode()).hexdigest()[:24]
    premarket=premarket_view(ctx.get('premarket_report') or {},now);recap=ctx.get('recap')
    ident.update(premarket=premarket,recap=recap);digest=hashlib.sha256(json.dumps(ident,sort_keys=True,allow_nan=False,default=str).encode()).hexdigest()[:24]
    return asdict(MarketView(VERSION,digest,now.astimezone(timezone.utc).isoformat(),session['state'],price,trend,outlooks,entry,primary,option_data,evidence,premarket,recap))

def details(snapshot):
    s=snapshot;lines=['AEGIS VIEW '+s['schema_version']+' · '+s['snapshot_id'],'Generated: '+s['generated_at'],'Current trend: '+s['trend']['state']+' · '+s['trend']['rule_version'],s['trend']['reason']]
    for h,o in s['outlooks'].items():lines.append(h+': '+o['bias']+' · '+o['rule_version']+' · target '+str(o['target_at'] or 'unavailable')+' · '+str(o['reason'] or o['basis']))
    lines+=['Observed rule: close versus same-feed session VWAP and exact15m change; UP/DOWN require agreement. SIDEWAYS requires span<=2ATR, |change|<=0.25ATR, |close-VWAP|<=0.5ATR; other disagreement=MIXED.', 'Descriptive bounds: current-session genuine contiguous completed endpoints; bar end age 0..120 seconds. Entry quote/receipt/heartbeat/calendar/risk gates are independent.']
    lines+=['Entry: '+s['entry']['state']+' — '+s['entry']['reason'],'Primary: '+(s['primary_plan']['signal_id']+' '+s['primary_plan']['state'] if s.get('primary_plan') else 'none'),s['option_data'],'Indicators, hypotheses and entries are separate. No calibrated odds; no order execution.']
    return '\n'.join(lines)

def observe(store,news,now,config=None,rows=()):
    from core.idea_service import context
    from core.primary_plan import current
    ctx=context(store,now)
    return build(ctx,news,now,config,current(store,rows,now))
