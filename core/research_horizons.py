"""Completed-bar descriptive context and independently versioned horizon studies.

No function in this module grants live/option eligibility. Genuine historical
bars are historical observations even if downloaded now. No synthetic slots enter
indicators or outcomes. Legacy scalp families are preserved by idea_service.
"""
import hashlib,json,statistics
from datetime import datetime,timezone,timedelta
from core.sessions import ET,market_session
from data.models import stamp,finite
from features.indicators import normalize,multi_timeframe,calculate,resample

VERSION='spy-horizon-comparison-v2'
RULES={'H60':{'minutes':60,'frames':('15m','5m'),'atr_frame':'15m'},
       'H120':{'minutes':120,'frames':('30m','1h'),'atr_frame':'30m'},
       'SESSION':{'minutes':None,'frames':('1h','daily'),'atr_frame':'1h'}}

def deadline(now,horizon):
    if now.tzinfo is None:raise ValueError('AWARE_TIME_REQUIRED')
    rule=RULES[horizon];session=market_session(now)
    close=now.astimezone(ET).replace(hour=session['close_minute']//60,minute=session['close_minute']%60,second=0,microsecond=0)-timedelta(minutes=5)
    if not session['active']:return None
    planned=now+timedelta(minutes=rule['minutes']) if rule['minutes'] else close
    if planned>close or (close-now).total_seconds()<30*60 or planned<=now:return None
    return planned.astimezone(timezone.utc)

def from_snapshot(snapshot,now,simulation=False):
    """Quote-independent view: same-session, genuine contiguous completed bars."""
    out={'quality':'UNAVAILABLE','reason':'NO_COMPLETED_CURRENT_SESSION_BARS','features':{},'bars':[],'rows':[], 'provider':'UNAVAILABLE','feed_quality':'UNAVAILABLE','entry_eligible':False}
    if not market_session(now)['active']:out['reason']='OUTSIDE_REGULAR_SESSION';return out
    choices=[]
    for feed,key in (('SIP','stream_bars:SPY'),('IEX','research_stream_bars:SPY:iex')):
        raw=snapshot.get(key) or []
        try:
            bars=normalize(raw,now=now,simulation=simulation)
            today=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==now.astimezone(ET).date()]
            if today:choices.append((today[-1]['timestamp'],feed,raw,bars,today))
        except (KeyError,ValueError,TypeError):continue
    if not choices:return out
    _,feed,raw,bars,today=max(choices,key=lambda x:x[0]);tail=today[-31:]
    out.update(feed_quality=feed,provider='alpaca-'+feed.lower(),rows=raw,bars=today,
               source_timestamp=datetime.fromtimestamp(today[-1]['timestamp']+60,timezone.utc).isoformat(),last_completed_close=today[-1]['close'])
    age=now.timestamp()-today[-1]['timestamp']-60;out['bar_end_age_seconds']=age
    if not market_session(now)['active']:out['reason']='OUTSIDE_REGULAR_SESSION';return out
    if not 0<=age<=120:out['reason']='COMPLETED_BAR_END_AGE_EXCEEDS_120_SECONDS';return out
    if len(tail)<31 or any(b['timestamp']-a['timestamp']!=60 for a,b in zip(tail,tail[1:])):
        out['reason']='31_GENUINE_COMPLETED_MINUTES_REQUIRED_FOR_BAR_RESEARCH';return out
    daily=snapshot.get('history_daily:'+feed.lower()) or ((snapshot.get('daily') or {}).get('payload',{}).get('bars',[]) if feed=='SIP' else [])
    try:
        from features.indicators import from_normalized
        fs=from_normalized(bars,normalize(daily,1440,now,simulation),now)
        for frame,minutes in (('5m',5),('15m',15),('30m',30),('1h',60)):
            if fs[frame].get('trend') not in (None,'UNAVAILABLE'):continue
            native=(snapshot.get('history_frames:'+feed.lower()) or {}).get(frame,[])
            native=normalize(native,minutes,now,simulation)
            native=[b for b in native if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).hour*60+datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).minute+minutes<=market_session(datetime.fromtimestamp(b['timestamp'],timezone.utc))['close_minute']]
            if native:fs[frame]=dict(calculate(native),history_source='PROVIDER_NATIVE_AGGREGATES',feed_quality=feed)
        out.update(quality='COMPLETED_BAR_RESEARCH_ONLY',reason=None,features=fs)
    except (ValueError,KeyError,TypeError):out['reason']='MALFORMED_HISTORY'
    return out

def context(store,now,simulation=False):
    keys=('stream_bars:SPY','research_stream_bars:SPY:iex','history_daily:iex','history_daily:sip','daily','history_frames:iex','history_frames:sip')
    snap=store.snapshot(keys) if hasattr(store,'snapshot') else {k:store.get(k) for k in keys}
    return from_snapshot(snap,now,simulation)

def describe(bar_context,now):
    result={};fs=bar_context.get('features') or {}
    for name,rule in RULES.items():
        frames={k:fs.get(k,{}).get('trend','UNAVAILABLE') for k in rule['frames']}
        values=list(frames.values());bias='UNAVAILABLE'
        if not bar_context.get('reason') and all(v in ('BULL','BEAR','NEUTRAL') for v in values):
            bias='UP' if all(v=='BULL' for v in values) else 'DOWN' if all(v=='BEAR' for v in values) else 'MIXED'
        end=deadline(now,name)
        result[name]={'horizon_id':name,'version':VERSION,'bias':bias,'frames':frames,'source':bar_context.get('provider','UNAVAILABLE'),
                      'as_of':bar_context.get('source_timestamp'),'max_hold_until':end.isoformat() if end else None,
                      'new_observation_eligible':end is not None and not bar_context.get('reason'),
                      'meaning':'Descriptive completed-frame alignment, not forecast probability or option eligibility.'}
    return result

def candidates(bar_context,quote,now,config=None,stop_fractions=(.5,.75),reference_price=None):
    """Pure comparative candidate generator; callers enforce strict entry/calendar.

    Pullback: completed 5m EMA9 reclaim using the preceding EMA for the preceding
    candle. ORB: genuine 09:30–09:44 range, preceding minute beyond boundary and
    latest minute retest/rejection. Context frames must both agree. Latest genuine
    minute volume >=1.2 times preceding10; quote is within half minute ATR of close.
    Risk is max(two completed5m structural distance, fraction*horizon-frame ATR).
    Targets1R/2R, full exit at stop/T2/deadline. Every grid trial has a stable ID.
    """
    if bar_context.get('reason'):return []
    fs=bar_context['features'];bars=bar_context['bars'];quote=quote or {}
    offline_reference=reference_price is not None
    px=reference_price if offline_reference else quote.get('payload',{}).get('mid')
    if len(bars)<31 or not finite(px):return []
    f=fs['1m'];atr=f.get('atr14');vwap=f.get('vwap_approx')
    if not all(finite(v) and v>0 for v in (px,atr,vwap)):return []
    last,prev=bars[-1],bars[-2];base=statistics.mean(b['volume'] for b in bars[-11:-1])
    if base<=0 or last['volume']<1.2*base or abs(px-last['close'])>.5*atr:return []
    lower=resample(bars,5)
    if len(lower)<10:return []
    low=calculate(lower);prior=calculate(lower[:-1]);ema=low.get('ema9');pe=prior.get('ema9')
    out=[];views=describe(bar_context,now)
    for name,rule in RULES.items():
        view=views[name];end=deadline(now,name)
        if not end or view['bias'] not in ('UP','DOWN'):continue
        sign=1 if view['bias']=='UP' else -1;direction='CALL' if sign==1 else 'PUT'
        if (px-vwap)*sign<=0:continue
        setup=[]
        if finite(ema) and finite(pe) and (lower[-2]['close']-pe)*sign<=0<(lower[-1]['close']-ema)*sign:
            setup.append(('TREND_PULLBACK_CONTINUATION',ema))
        boundary=(fs.get('opening_range') or {}).get('high' if sign==1 else 'low')
        if finite(boundary) and (prev['close']-boundary)*sign>0 and (last['low']<=boundary<last['close'] if sign==1 else last['high']>=boundary>last['close']):
            setup.append(('ORB_RETEST',boundary))
        context_atr=fs.get(rule['atr_frame'],{}).get('atr14')
        if not finite(context_atr) or context_atr<=0:continue
        structural=min(b['low'] for b in lower[-2:]) if sign==1 else max(b['high'] for b in lower[-2:])
        for family,trigger in setup:
            if (px-trigger)*sign<0:continue
            for fraction in stop_fractions:
                risk=max((px-structural)*sign,fraction*context_atr)
                if risk<=0 or px-sign*risk<=0:continue
                identity=[VERSION,name,family,direction,fraction,last['timestamp']]
                expiry=min(now+timedelta(seconds=(config or {}).get('signal_expiry_seconds',600)),end)
                out.append({'schema_version':3,'strategy_version':VERSION,'horizon_id':name,'horizon':name,'trial_id':f'{family}:{name}:atr{fraction}',
                    'signal_id':hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24],'timestamp':now.astimezone(timezone.utc).isoformat(),
                    'direction':direction,'setup_type':family,'early':False,'trigger':trigger,'trigger_level':trigger,'entry':px,'reference_midpoint':px,
                    'entry_mode':'ENTER NOW','entry_condition':'completed candles and context confirmed; underlying research reference only',
                    'modeled_entry_fill':None if offline_reference else quote['payload']['ask' if sign==1 else 'bid']+sign*.01,'actual_reported_fill':None,
                    'price_basis':'COMPLETED_BAR_CLOSE_RESEARCH_ONLY' if offline_reference else 'VERIFIED_UNDERLYING_QUOTE_REFERENCE',
                    'do_not_chase':px+sign*.5*atr,'spy_price':px,'atr':atr,'stop_atr_fraction':fraction,'context_atr_frame':rule['atr_frame'],
                    'invalidation':px-sign*risk,'t1':px+sign*risk,'t2':px+sign*2*risk,'risk_reward':2.,'risk_distance':risk,
                    'signal_expiry':expiry.isoformat(),'max_hold_until':end.isoformat(),'planned_holding_minutes':rule['minutes'],
                    'feed_quality':bar_context['feed_quality'],'data_provider':bar_context['provider'],'market_timestamp':quote.get('source_timestamp'),
                    'evaluation_cadence_seconds':10,'telegram_status_cadence_seconds':900,'option_expiry':None,
                    'population':'HORIZON_COMPARISON_UNDERLYING_ONLY','score':None,'actionable':False,'live_signal_ready':False})
    return out
