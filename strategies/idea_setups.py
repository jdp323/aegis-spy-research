"""Completed-candle SPY setups. Descriptive research, not a calibrated forecast."""
import math,statistics,hashlib,json
from datetime import timedelta,timezone
from core.idea_config import settings,SETUPS
from core.sessions import ET,market_session
from data.models import finite
VERSION='spy-ideas-v3-entry-window'
def pending_triggers(features,config=None):
    f=features.get('1m',{});o=features.get('opening_range') or {};out=[]
    enabled=settings(config or {})['setup_enabled']
    for direction,levels in [('CALL',[('OPENING_RANGE_BREAKOUT',o.get('high')),('VWAP_RECLAIM',f.get('vwap_approx')),('TREND_CONTINUATION',f.get('ema9')),('SUPPORT_BOUNCE',f.get('support')),('BREAKOUT_RETEST',o.get('high'))]),('PUT',[('OPENING_RANGE_BREAKDOWN',o.get('low')),('VWAP_REJECTION',f.get('vwap_approx')),('TREND_CONTINUATION',f.get('ema9')),('RESISTANCE_REJECTION',f.get('resistance')),('BREAKOUT_RETEST',o.get('low'))])]:
        px=f.get('close')
        sign=1 if direction=='CALL' else -1
        choices=[{'direction':direction,'setup':k,'price':v} for k,v in levels if enabled[k] and finite(v) and v>0 and (not finite(px) or (v-px)*sign>=0)]
        if choices:out.append(min(choices,key=lambda x:abs(x['price']-px) if finite(px) else 0))
    return out
def levels(entry,structural,sign,atr,f,config):
    if not all(finite(x) and x>0 for x in (entry,structural,atr)):return None
    distance=max(abs(entry-structural),settings(config)['idea_stop_atr_fraction']*atr)
    stop=entry-sign*distance
    if stop<=0:return None
    candidates=sorted({x for x in f.get('swing_highs' if sign==1 else 'swing_lows',[]) if finite(x) and (x-entry)*sign>=distance},reverse=sign==-1)
    t1=candidates[0] if candidates else entry+sign*distance
    t2=next((x for x in candidates if (x-entry)*sign>=2*distance and (x-t1)*sign>0),entry+sign*max(2*distance,abs(t1-entry)+distance))
    rr=abs(t2-entry)/distance
    if rr<settings(config)['min_rr']:return None
    return {'entry':entry,'invalidation':stop,'t1':t1,'t2':t2,'risk_reward':rr,'risk_distance':distance}
def detect(features,bars,quote,now,config,early=False):
    """Returns every confirmed candidate; eligibility gates are applied separately."""
    if len(bars)<15:return []
    f=features.get('1m',{});o=features.get('opening_range') or {};last,prev=bars[-1],bars[-2]
    px=quote.get('payload',{}).get('mid');atr=f.get('atr14');vwap=f.get('vwap_approx');pv=f.get('previous_vwap_approx')
    if not all(finite(x) and x>0 for x in (px,atr,vwap,pv)):return []
    recent=statistics.mean(b['volume'] for b in (bars[:15] if early else bars[-11:-1]))
    volume=recent>0 and last['volume']>=recent*(1.5 if early else 1.2)
    if not volume:return []
    c=settings(config);out=[];minute=now.astimezone(ET).hour*60+now.astimezone(ET).minute
    for sign in (1,-1):
        direction='CALL' if sign==1 else 'PUT';opposing='BEAR' if sign==1 else 'BULL'
        if sum(features.get(k,{}).get('trend')==opposing for k in ('15m','30m','1h'))>=2:continue
        if (last['close']-prev['close'])*sign<=0 or (px-vwap)*sign<=0:continue
        structural=min(last['low'],prev['low']) if sign==1 else max(last['high'],prev['high'])
        boundary=o.get('high' if sign==1 else 'low');choices=[]
        if finite(boundary) and (last['close']-boundary)*sign>0 and (prev['close']-boundary)*sign<=0:
            choices.append(('OPENING_RANGE_BREAKOUT' if sign==1 else 'OPENING_RANGE_BREAKDOWN',boundary,structural))
        if not early:
            if (prev['close']-pv)*sign<=0 and (last['close']-vwap)*sign>0:choices.append(('VWAP_RECLAIM' if sign==1 else 'VWAP_REJECTION',vwap,structural))
            aligned=features.get('15m',{}).get('trend')==('BULL' if sign==1 else 'BEAR') and features.get('1h',{}).get('trend')==('BULL' if sign==1 else 'BEAR')
            ema=f.get('ema9')
            if aligned and finite(ema) and (prev['close']-ema)*sign<=0<(last['close']-ema)*sign:choices.append(('TREND_CONTINUATION',ema,structural))
            support=f.get('support' if sign==1 else 'resistance')
            if finite(support) and (last['low']<=support<last['close'] if sign==1 else last['high']>=support>last['close']):choices.append(('SUPPORT_BOUNCE' if sign==1 else 'RESISTANCE_REJECTION',support,structural))
            if finite(boundary) and (prev['close']-boundary)*sign>0 and (last['low']<=boundary<last['close'] if sign==1 else last['high']>=boundary>last['close']):choices.append(('BREAKOUT_RETEST',boundary,structural))
        for name,trigger,invalid in choices:
            if not c['setup_enabled'][name]:continue
            if early and not c['early_session_ideas']:continue
            lv=levels(px,invalid,sign,atr,f,config)
            if not lv:continue
            # Already confirmed and executable midpoint beyond trigger: do not manufacture a future entry.
            if (px-trigger)*sign<0 or abs(px-last['close'])>.5*atr:continue
            end=min(now+timedelta(minutes=60),now.astimezone(ET).replace(hour=market_session(now)['close_minute']//60,minute=market_session(now)['close_minute']%60)-timedelta(minutes=30))
            if end<=now:continue
            expiry=min(now+timedelta(seconds=config.get('signal_expiry_seconds',600)),end-timedelta(seconds=1))
            if expiry<=now:continue
            identity=[VERSION,name,direction,early,last['timestamp'],round(trigger,4)]
            checks={'completed_candle':True,'volume':True,'structure':True,'higher_frame_not_opposing':True,'reward_risk':True}
            warnings=[]
            if finite(o.get('high')) and prev['high']>o['high'] and last['close']<o['high']:warnings.append('failed opening-range breakout; upward trigger needs renewed confirmation')
            if finite(o.get('low')) and prev['low']<o['low'] and last['close']>o['low']:warnings.append('failed opening-range breakdown; downward trigger needs renewed confirmation')
            idea={'schema_version':2,'strategy_version':VERSION+('-early' if early else ''),'scoring_version':'idea-check-count-v2-observed','score_components':checks,'score_meaning':'Percent of five mandatory checks passed; not a probability or ranking of return.','signal_id':hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24],'timestamp':now.astimezone(timezone.utc).isoformat(),'direction':direction,'setup_type':name,'early':early,'trigger':trigger,'entry_mode':'ENTER NOW','entry_condition':'a completed 1-minute close '+('above ' if sign==1 else 'below ')+'SPY $%.2f'%trigger,'do_not_chase':px+sign*.5*atr,'spy_price':px,'atr':atr,'score':sum(checks.values())*20,'tier':'A+','horizon':'INTRADAY' if name.startswith('OPENING_RANGE') else 'SCALP','max_hold_until':end.astimezone(timezone.utc).isoformat(),'signal_expiry':expiry.astimezone(timezone.utc).isoformat(),'market_regime':'BULL' if sign==1 else 'BEAR','feed_quality':quote.get('feed_quality') or ('IEX' if quote.get('provider')=='alpaca-iex' else 'SIP'),'data_provider':quote.get('provider'),'market_timestamp':quote.get('source_timestamp'),'multi_timeframe_alignment':{k:features.get(k,{}).get('trend','UNAVAILABLE') for k in ('1m','5m','15m','30m','1h','daily')},'explanation':['completed candle and structural confirmation','volume %.2fx recent baseline'%(last['volume']/recent),'higher frames do not strongly contradict',*warnings],'actionable':False,'live_signal_ready':False,**lv}
            out.append(idea)
    return out
