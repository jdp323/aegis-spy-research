"""Versioned research signals. Scores cannot override hard rejections."""
from dataclasses import dataclass,field,asdict
from datetime import datetime,timezone,timedelta
import hashlib,json
def tier(score):
    if score is None:return 'NO TRADE'
    return 'A+' if score>=90 else 'A' if score>=85 else 'B' if score>=75 else 'C' if score>=65 else 'NO TRADE'
@dataclass
class Signal:
    signal_id:str
    timestamp:str
    market_timestamp:str|None
    data_provider:str
    strategy_version:str='spy-setups-paper-v2'
    scoring_version:str='evidence-rubric-v3'
    schema_version:int=3
    horizon:str="UNAVAILABLE"
    option_plan:dict|None=None
    paper_eligible:bool=False
    paper_blockers:list=field(default_factory=list)
    live_signal_ready:bool=False
    paper_mode:str='OPTIONS_REAL_QUOTES'
    feed_quality:str='UNAVAILABLE'
    direction:str='UNAVAILABLE'
    setup_type:str='UNAVAILABLE'
    market_regime:str='UNSAFE'
    score:float|None=None
    score_components:dict=field(default_factory=dict)
    tier:str='NO TRADE'
    spy_price:float|None=None
    vwap:float|None=None
    multi_timeframe_alignment:dict=field(default_factory=dict)
    entry_condition:str='UNAVAILABLE'
    underlying_entry_range:list=field(default_factory=list)
    invalidation:float|None=None
    stop_concept:str='Underlying thesis invalidation; not a guaranteed option loss cap'
    t1:float|None=None
    t2:float|None=None
    risk_reward:float|None=None
    option_contract:dict|None=None
    option_entry_range:list=field(default_factory=list)
    max_holding_minutes:int=60
    news_status:str='UNAVAILABLE'
    volatility_status:str='UNAVAILABLE'
    signal_expiry:str|None=None
    hard_rejection:bool=True
    rejection_reasons:list=field(default_factory=list)
    explanation:list=field(default_factory=list)
    validated_strategy:bool=False
    actionable:bool=False
    status:str='REJECTED'
    def dict(self):return asdict(self)
def build(features,regime,selection,quote,news,session,risk,now=None,config=None):
    config=config or {}
    now=now or datetime.now(timezone.utc);f=features.get('5m',{});opening=features.get('opening_range');px=(quote.get('payload') or {}).get('mid')
    from strategies.spy_setups import VERSION
    identity=[quote.get('source_timestamp'),session['date'],f.get('timestamp'),VERSION,'evidence-rubric-v3']
    sid=hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    s=Signal(sid,now.isoformat(),quote.get('source_timestamp'),quote.get('provider','UNAVAILABLE'));s.signal_expiry=(now+timedelta(seconds=config.get('signal_expiry_seconds',600))).isoformat();s.spy_price=px;s.vwap=f.get('vwap_approx');s.market_regime=regime['regime'];s.news_status=news['risk'];s.volatility_status=regime['regime'];s.option_contract=selection.get('best_contract');s.feed_quality='SIP' if quote.get('provider') in ('alpaca','alpaca-sip') else 'UNAVAILABLE'
    reasons=[]
    clock=config.get('clock_health') or {}
    if clock.get('state')=='MEASURED' and abs(clock.get('offset_seconds',0))>config.get('max_future_skew_seconds',2):reasons.append('CLOCK_OFFSET_BEYOND_TOLERANCE')
    if config.get('require_chain_sanity',False):reasons.extend(selection.get('chain_sanity_reasons') or ([] if selection.get('chain_sanity_reasons')==[] else ['CHAIN_NEIGHBORS_UNAVAILABLE']))
    if quote.get('quality')!='DATA_OK' or quote.get('entitlement')!='REALTIME' or s.feed_quality!='SIP' or not quote_valid(quote,now,5):reasons.append('UNDERLYING_DATA_NOT_VERIFIED')
    bar_time=features.get('1m',{}).get('timestamp')
    if bar_time is None or not 60<=now.timestamp()-bar_time<=180:reasons.append('BAR_HISTORY_STALE_OR_UNAVAILABLE')
    if not session['active']:reasons.append('OUTSIDE_STRATEGY_SESSION')
    if news['quality']!='DATA_OK' or news['risk'] not in ('NORMAL','MODERATE'):reasons.append('NEWS_UNAVAILABLE_OR_BLACKOUT')
    if regime['regime'] in ('UNSAFE','ABNORMAL','CHOPPY','NEUTRAL'):reasons.append('REGIME_UNSUITABLE')
    from strategies.spy_setups import detect,VERSION
    setup=detect(features,px);s.strategy_version=VERSION
    if setup['sign'] and f.get('atr14'):
        sign=setup['sign'];s.direction='CALL' if sign==1 else 'PUT';s.setup_type=setup['setup_type'];s.entry_condition='Completed-bar setup with volume, structure and higher-frame confirmation';s.underlying_entry_range=[px-.1*f['atr14'],px+.1*f['atr14']];s.invalidation=setup['invalidation'];distance=(px-s.invalidation)*sign
        if distance>0:s.t1=px+sign*distance*1.5;s.t2=px+sign*distance*2;s.risk_reward=2
        else:reasons.append('INVALID_SETUP_RISK_DISTANCE')
        reasons.extend(setup['reasons'])
    else:reasons.extend(setup['reasons'] or ['SETUP_INPUTS_UNAVAILABLE'])
    s.multi_timeframe_alignment={k:features.get(k,{}).get('trend','UNAVAILABLE') for k in ('1m','5m','15m','30m','1h','daily')}
    aligned='BULL' if s.direction=='CALL' else 'BEAR'
    if any(v=='UNAVAILABLE' for v in s.multi_timeframe_alignment.values()):reasons.append('MULTI_TIMEFRAME_HISTORY_INCOMPLETE')
    elif any(v!=aligned for v in s.multi_timeframe_alignment.values()):reasons.append('MULTI_TIMEFRAME_NOT_ALIGNED')
    if not s.option_contract:reasons.append('NO_ELIGIBLE_OPTION_CONTRACT')
    elif s.option_contract['type']!=('C' if s.direction=='CALL' else 'P'):reasons.append('CONTRACT_DIRECTION_MISMATCH')
    else:
        s.option_entry_range=[s.option_contract['bid'],s.option_contract['ask']]
        if not option_quote_valid(s.option_contract.get('quote',{}),now):reasons.append('OPTION_QUOTE_NOT_VERIFIED')
        from data.models import stamp,finite
        try:
            age=(now-stamp(s.option_contract['greeks_timestamp'])).total_seconds()
            if not 0<=age<=60 or any(not finite(s.option_contract.get(k)) for k in ('delta','gamma','theta','vega','iv')) or s.option_contract['iv']<=0:raise ValueError()
        except (KeyError,ValueError,TypeError):reasons.append('OPTION_GREEKS_NOT_FRESH_VERIFIED')
        if any(not finite(s.option_contract.get(k)) or s.option_contract[k]<100 for k in ('volume','oi')):reasons.append('OPTION_LIQUIDITY_NOT_VERIFIED')
    if not risk.get('ready'):reasons.extend(risk.get('reasons') or ['RISK_LIMITS_NOT_CONFIGURED'])
    # A missing score component stays unavailable, not zero or an invented confidence.
    components=[f.get('structure') not in (None,'UNAVAILABLE'),f.get('trend') not in (None,'UNAVAILABLE'),f.get('rvol_same_slot') is not None,s.vwap is not None,f.get('macd') is not None,s.option_contract is not None,news['quality']=='DATA_OK',s.risk_reward is not None]
    if all(components):
        values=[20 if f['structure'] in ('HH_HL','LH_LL') else 0,15 if f['trend']==aligned else 0,10 if f['rvol_same_slot']>=1.2 else 0,15 if px and s.vwap and (px-s.vwap)*(1 if s.direction=='CALL' else -1)>0 else 0,10 if f['macd']['histogram']*(1 if s.direction=='CALL' else -1)>0 else 0,10,10 if news['risk']=='NORMAL' else 0,10 if s.risk_reward>=1.5 else 0]
        s.score_components=dict(zip(('structure','trend','rvol','vwap','macd','contract','news','risk_reward'),values));s.score=sum(values)
    s.tier=tier(s.score)
    if s.score is None or s.score<75:reasons.append('SCORE_UNAVAILABLE_OR_BELOW_THRESHOLD')
    if s.option_contract:
        from options.trade_plan import build as plan_build,sanity
        extra=sanity(s.option_contract,now,config);reasons.extend(extra)
        if not extra and s.direction in ('CALL','PUT') and all(v is not None for v in (s.spy_price,s.t1,s.t2,s.invalidation)):
            try:
                s.option_plan=plan_build(s.dict(),now,config,news);s.horizon=s.option_plan['horizon'];s.max_holding_minutes=max(1,int((__import__('data.models',fromlist=['stamp']).stamp(s.option_plan['max_hold_until'])-now).total_seconds()/60))
            except ValueError as error:reasons.append(str(error))
    # No config boolean can claim a strategy is validated. Promotion requires a separate evidence review.
    finalize(s,reasons,config)
    s.signal_id=hashlib.sha256(json.dumps([sid,s.strategy_version,s.scoring_version,s.setup_type,s.rejection_reasons,s.score,risk.get('limits')],sort_keys=True).encode()).hexdigest()[:24]
    return s
def quote_valid(q,now,max_age=5):
    from data.models import stamp,finite
    try:
        source=stamp(q['source_timestamp']);received=stamp(q['received_timestamp']);p=q['payload'];budget=q.get('accepted_future_skew_seconds',0)
        if type(budget) not in (int,float) or not 0<=budget<=5 or q.get('feed_quality') in ('SIMULATED','INDICATIVE','DELAYED'):return False
        return q['quality']=='DATA_OK' and q['entitlement']=='REALTIME' and q.get('data_type')=='quote' and all(finite(p[k]) for k in ('bid','ask')) and 0<p['bid']<=p['ask'] and -budget<=(now-source).total_seconds()<=max_age and 0<=(now-received).total_seconds()<=max_age and (source-received).total_seconds()<=budget
    except (KeyError,ValueError,TypeError):return False
def option_quote_valid(q,now):
    if q.get('provider')=='questrade':return q.get('feed_quality')=='OPRA_L1_QUESTRADE' and q.get('source_timestamp_verified') is True and quote_valid(q,now,10)
    return q.get('provider') in ('alpaca-opra','alpaca') and q.get('feed_quality', 'OPRA' if q.get('provider')=='alpaca-opra' else None)=='OPRA' and quote_valid(q,now,15)
def finalize(s,reasons,config):
    if s.feed_quality=='SIMULATED' or s.option_contract and s.option_contract.get('quote',{}).get('feed_quality')=='SIMULATED':reasons=list(reasons)+['SIMULATED_DATA_FORBIDDEN']
    s.paper_blockers=sorted(set(reasons))
    if not config.get('allow_unvalidated_paper_trading',False):s.paper_blockers.append('STRATEGY_PROSPECTIVE_VALIDATION_MISSING')
    s.paper_eligible=not s.paper_blockers
    s.rejection_reasons=sorted(set(reasons+['STRATEGY_PROSPECTIVE_VALIDATION_MISSING']))
    s.hard_rejection=True;s.actionable=False;s.live_signal_ready=False;s.validated_strategy=False;s.status='PAPER_ELIGIBLE' if s.paper_eligible else 'REJECTED'
    s.explanation=list(dict.fromkeys(s.explanation+['Uncalibrated research score, not probability of profit.','Paper only; strategy not validated. No order execution capability.']))
