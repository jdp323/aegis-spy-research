"""Option-value research estimates from fresh real quotes; signed vendor theta in USD/day."""
from datetime import datetime,timezone,timedelta
import math
from core.signals import option_quote_valid
from core.sessions import ET,market_session
from data.models import finite,stamp
VERSION='greek-local-v1'
def mismatch(quotes,config,now):
    from core.signals import quote_valid
    values=[q['payload']['mid'] for q in quotes if quote_valid(q,now) and q.get('feed_quality')!='SIMULATED']
    if len(values)<2:return False
    lo,hi=min(values),max(values);t=config.get('price_mismatch_tolerance',{})
    return hi-lo>t.get('usd',.5) or (hi-lo)/lo*100>t.get('percent',.1)
def sanity(c,now,config,simulation=False):
    reasons=[];q=c.get('quote',{})
    if not option_quote_valid(q,now) and not (simulation and q.get('feed_quality')=='SIMULATED'):reasons.append('OPTION_QUOTE_NOT_FRESH_VERIFIED')
    bid,ask=c.get('bid'),c.get('ask')
    if not finite(bid) or not finite(ask) or not 0<bid<=ask:reasons.append('BID_ASK_INVALID')
    else:
        mid=c.get('mid',(bid+ask)/2)
        if not finite(mid) or not bid<=mid<=ask:reasons.append('MID_OUTSIDE_SPREAD')
        if (ask-bid)/mid>config.get('max_option_spread_pct',.10):reasons.append('SPREAD_ABOVE_LIMIT')
        if config.get('premium_cap_mode','reject')=='reject' and ask*100>config.get('options_risk',{}).get('max_trade_premium_usd',500):reasons.append('PREMIUM_ABOVE_CAP')
    if any(not finite(c.get(k)) for k in ('delta','gamma','theta','vega','iv')):reasons.append('GREEKS_UNAVAILABLE')
    else:
        if not (0<c['delta']<=1 if c.get('type')=='C' else -1<=c['delta']<0):reasons.append('DELTA_IMPLAUSIBLE')
        if c['gamma']<0 or c['theta']>0 or c['vega']<0 or c['iv']<=0:reasons.append('GREEK_SIGN_INVALID')
    try:
        from options.ledger import contract
        spec=contract(c['symbol'])
        if float(spec['strike'])!=float(c['strike']) or spec['type']!=c['type'] or spec['expiry']!=c['expiry']:reasons.append('CONTRACT_TERMS_MISMATCH')
    except (ValueError,KeyError,TypeError):reasons.append('CONTRACT_TERMS_UNAVAILABLE')
    return sorted(set(reasons))
def estimated_bid(c,delta_spy,days):
    """Local Taylor expansion, fixed IV; never a live quote or guaranteed exit."""
    if not all(finite(c.get(k)) for k in ('bid','delta','gamma','theta')) or not finite(days) or days<0:raise ValueError('ESTIMATE_INPUT_UNAVAILABLE')
    return max(0,c['bid']+c['delta']*delta_spy+.5*c['gamma']*delta_spy**2+c['theta']*days)
def horizon(s,c,now,config,news=None):
    local=now.astimezone(ET);minute=local.hour*60+local.minute;session=market_session(now);dte=(datetime.fromisoformat(c['expiry']).date()-local.date()).days
    if dte<1:raise ValueError('ZERO_DTE_DISABLED')
    h=config.get('horizons',{});close=session['close_minute']-h.get('intraday_exit_minutes_before_close',30)
    if s.get('setup_type')=='TREND_CONTINUATION' and h.get('swing_enabled',False) and 2<=dte<=7 and s.get('multi_timeframe_alignment',{}).get('daily')==('BULL' if s['direction']=='CALL' else 'BEAR'):
        end=now+timedelta(days=min(h.get('swing_days',3),dte-1))
        if not news or not news.get('coverage_complete') or stamp(news['coverage_through'])<end:raise ValueError('SWING_CALENDAR_COVERAGE_UNAVAILABLE')
        if any(e.get('risk')=='HIGH' and now<=stamp(e['time_utc'])<=end for e in news.get('events',[])):raise ValueError('SWING_EVENT_WINDOW')
        return 'SWING',end,'swing — review by '+end.astimezone(ET).strftime('%a %H:%M ET')+'; overnight gaps can exceed the stop'
    if minute<630 and s.get('setup_type')=='OPENING_RANGE_BREAKOUT' and minute<close:
        end=datetime.combine(local.date(),datetime.min.time(),ET)+timedelta(minutes=close)
        return 'INTRADAY',end.astimezone(timezone.utc),'intraday — review exit by '+end.strftime('%H:%M ET')
    minutes=min(h.get('scalp_minutes',60),close-minute)
    if minutes<=0:raise ValueError('OUTSIDE_PLAN_TIME_WINDOW')
    end=now+timedelta(minutes=minutes);return 'SCALP',end,'scalp — review exit by '+end.astimezone(ET).strftime('%H:%M ET')
def build(s,now=None,config=None,news=None,simulation=False):
    now=now or datetime.now(timezone.utc);config=config or {};c=s.get('option_contract')
    if not c:raise ValueError('OPTION_CONTRACT_UNAVAILABLE')
    reasons=sanity(c,now,config,simulation)
    if reasons:raise ValueError(','.join(reasons))
    h,end,hold=horizon(s,c,now,config,news);days=(end-now).total_seconds()/86400
    if any(not finite(s.get(k)) for k in ('spy_price','invalidation','t1','t2')):raise ValueError('SPY_LEVELS_UNAVAILABLE')
    limit=(c['bid']+c['ask'])/2;buf=config.get('buy_limit_buffer',{});max_price=c['ask']+min(buf.get('usd',.1),c['ask']*buf.get('percent',4)/100)
    stop=estimated_bid(c,s['invalidation']-s['spy_price'],days);t1=estimated_bid(c,s['t1']-s['spy_price'],days);t2=estimated_bid(c,s['t2']-s['spy_price'],days)
    loss=(limit-stop)*100+1.3
    if loss<=0 or t2<=limit:raise ValueError('ESTIMATED_RISK_REWARD_INVALID')
    return {'horizon':h,'max_hold_until':end.isoformat(),'hold_text':hold,'limit':round(limit,2),'max_price':round(max_price,2),'t1_bid':round(t1,2),'t2_bid':round(t2,2),'stop_bid':round(stop,2),'cost':round(limit*100+.65,2),'loss_at_stop':round(loss,2),'estimated_reward_risk':((t2-limit)*100-1.3)/loss,'warnings':['PREMIUM_ABOVE_CAP (informational; paper entry limits unchanged)'] if c['ask']*100>config.get('options_risk',{}).get('max_trade_premium_usd',500) else [],'estimate':True,'estimate_method':VERSION,'theta_convention':'signed USD per calendar day; +theta*days','vega_effect_assumed':0,'limitations':'Fixed IV local approximation; real bid depends on IV, spread and path.'}
def exit_conditions(plan,s,underlying,option,now):
    """Dual price triggers; stale option data never creates an option-dollar exit."""
    from core.signals import quote_valid
    px=underlying.get('payload',{}).get('mid') if quote_valid(underlying,now) else None
    bid=option.get('payload',{}).get('bid') if option_quote_valid(option,now) else None
    sign=1 if s.get('direction')=='CALL' else -1;out=[]
    if bid is None:out.append('DATA_WARNING_OPTION_UNAVAILABLE_SPY_LEVELS_ONLY')
    if px is not None and (px-s['invalidation'])*sign<=0 or bid is not None and bid<=plan['stop_bid']:out.append('STOP_REVIEW')
    for key in ('t1','t2'):
        if px is not None and (px-s[key])*sign>=0 or bid is not None and bid>=plan[key+'_bid']:out.append(key.upper()+'_REVIEW')
    if stamp(plan['max_hold_until'])<=now:out.append('TIME_STOP_REVIEW')
    return {'conditions':out,'spy':px,'option_bid':bid,'text':'EXIT REVIEW — SPY '+(f'{px:.2f}' if px is not None else 'UNAVAILABLE')+' / option bid '+(f'{bid:.2f}' if bid is not None else 'UNAVAILABLE')+'\n'+', '.join(out)+'\nManual review only; no order placed.'}
