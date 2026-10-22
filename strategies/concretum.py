"""Clean-room published SPY momentum equations, never an execution adapter.

Paper (Sep 2025): 14 prior same-clock sessions, 30m decisions/stops, overnight
flat. Article diagnostic is separately labeled; original code is not imported.
"""
from datetime import datetime,timezone
from statistics import mean,stdev
from math import floor
from core.sessions import ET,market_session
VERSION='concretum-paper-2025-v1'

def complete(day):
    if not day:return False
    t=datetime.fromtimestamp(day[0]['timestamp'],timezone.utc).astimezone(ET);s=market_session(t.replace(hour=10,minute=0));n=s['close_minute']-570
    return s['active'] and len(day)==n and (t.hour,t.minute)==(9,30) and all(b['timestamp']-a['timestamp']==60 for a,b in zip(day,day[1:]))

def bands(today,previous,previous_close,dividend,lookback=14):
    if not today or dividend is None or previous_close is None:return {'status':'UNAVAILABLE','reason':'explicit corporate-action coverage and prior close required'}
    if len(previous)<lookback or any(not complete(d) for d in previous[-lookback:]):return {'status':'UNAVAILABLE','reason':'14 complete prior same-clock sessions required'}
    last=today[-1];slot=datetime.fromtimestamp(last['timestamp'],timezone.utc).astimezone(ET).strftime('%H:%M');moves=[]
    for d in previous[-lookback:]:
        b=next((b for b in d if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).strftime('%H:%M')==slot),None)
        if not b:return {'status':'UNAVAILABLE','reason':'prior same-clock slot missing (including early closes)'}
        moves.append(abs(b['close']/d[0]['open']-1))
    v=sum(b['volume'] for b in today)
    if v<=0:return {'status':'UNAVAILABLE','reason':'genuine volume required'}
    sigma=mean(moves);o=today[0]['open'];prior=previous_close-dividend
    return {'status':'RESEARCH','upper':max(o,prior)*(1+sigma),'lower':min(o,prior)*(1-sigma),'vwap':sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in today)/v,'sigma':sigma,'version':VERSION}

def decision(today,previous,previous_close,dividend,position=0,stop='CURRENT_BAND_VWAP'):
    if stop not in ('OPPOSITE_BAND','CURRENT_BAND_VWAP'):raise ValueError('UNKNOWN_PUBLISHED_VARIANT')
    if not today:return {'status':'UNAVAILABLE','reason':'completed session prefix required'}
    local=datetime.fromtimestamp(today[-1]['timestamp']+60,timezone.utc).astimezone(ET);minute=local.hour*60+local.minute
    if minute%30:return {'status':'ABSTAIN','side':position,'reason':'between 30-minute decisions'}
    b=bands(today,previous,previous_close,dividend)
    if b['status']!='RESEARCH':return b
    px=today[-1]['close'];side=position
    long_stop=b['lower'] if stop=='OPPOSITE_BAND' else max(b['upper'],b['vwap'])
    short_stop=b['upper'] if stop=='OPPOSITE_BAND' else min(b['lower'],b['vwap'])
    if position==1 and px<=long_stop or position==-1 and px>=short_stop:side=0
    if px>b['upper'] and (stop=='OPPOSITE_BAND' or px>b['vwap']):side=1
    elif px<b['lower'] and (stop=='OPPOSITE_BAND' or px<b['vwap']):side=-1
    if minute>=market_session(local)['close_minute']:side=0
    return dict(b,side=side,stop_variant=stop,decision_at=local.astimezone(timezone.utc).isoformat(),long_stop=long_stop,short_stop=short_stop)

def share_count(equity,opening,prior_returns,dynamic=False):
    if equity<=0 or opening<=0:return None
    if not dynamic:return floor(equity/opening)
    if len(prior_returns)<14:return None
    vol=stdev(prior_returns[-14:])
    return floor(equity*min(4,.02/vol)/opening) if vol>0 else None

def session_replay(today,previous,prior_close,dividend,delay_seconds=60,stop='CURRENT_BAND_VWAP',horizon=None):
    """Underlying one-share delayed minute-open adaptation; no touched-limit fills.

    15/30s sensitivity both round UP to available minute opens, disclosed. Same
    strategy decisions serve production diagnostics. One position at a time.
    Costs: paper $0.0035 commission + $0.001 slippage per share per side. A one-share
    study is not a funded portfolio or option result; article minimum fee separate.
    """
    import math
    if not complete(today):return {'status':'UNAVAILABLE','reason':'incomplete session','trades':[]}
    trades=[];side=0;entry=None;opened=None;pending=None;cutoff=today[-1]['timestamp']+60
    for n,b in enumerate(today):
        t=b['timestamp']
        if pending and t>=pending[0]:
            desired=pending[1];pending=None
            if side!=desired:
                if side:trades.append({'entry_at':opened,'exit_at':t,'side':side,'entry':entry,'exit':b['open'],'net_per_share':(b['open']-entry)*side-.009})
                side=desired;entry=b['open'] if side else None;opened=t if side else None
        if side and horizon and t+60>=opened+horizon*60:
            trades.append({'entry_at':opened,'exit_at':t+60,'side':side,'entry':entry,'exit':b['close'],'net_per_share':(b['close']-entry)*side-.009});side=0;entry=None;opened=None;pending=None
        r=decision(today[:n+1],previous,prior_close,dividend,side,stop)
        if r['status']=='UNAVAILABLE':return {'status':'UNAVAILABLE','reason':r['reason'],'trades':[]}
        if r['status']=='RESEARCH' and r['side']!=side:
            available=math.ceil((t+60+delay_seconds)/60)*60
            if available<cutoff and (not horizon or available+horizon*60<=cutoff):pending=(available,r['side'])
    if side:trades.append({'entry_at':opened,'exit_at':cutoff,'side':side,'entry':entry,'exit':today[-1]['close'],'net_per_share':(today[-1]['close']-entry)*side-.009})
    return {'status':'RESEARCH','version':VERSION,'stop_variant':stop,'delay_seconds':delay_seconds,'horizon_minutes':horizon,'trades':trades,'execution':'DELAYED_MINUTE_OPEN_PROXY_AND_CLOSING_REFERENCE','option_performance':'UNAVAILABLE','strategy_qualified':False}
