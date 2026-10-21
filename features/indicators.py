"""Completed regular-session OHLCV only. Null means insufficient evidence."""
import math,statistics,re
from datetime import datetime,timezone,timedelta
from data.models import finite,stamp
from core.sessions import market_session,ET
def normalize(rows,minutes=1,now=None,simulation=False):
    if not simulation:
        from core.isolation import assert_real
        assert_real(rows)
    now=now or datetime.now(timezone.utc);out=[];previous=None
    for r in rows:
        t=stamp(r['t']) if 't' in r else datetime.fromtimestamp(r['timestamp'],timezone.utc)
        fraction=re.search(r'[T ]\d{2}:\d{2}:\d{2}[.,](\d+)',r.get('t',''))
        if minutes<1440 and (t.timestamp()%60!=0 or (fraction and any(c!='0' for c in fraction.group(1)))):raise ValueError('MISALIGNED_BAR_TIMESTAMP')
        b={k:r.get(k,r.get(short)) for k,short in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v')]};b['timestamp']=t.timestamp()
        if not all(finite(b[k]) for k in ('open','high','low','close','volume')) or not 0<b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] or b['volume']<0:raise ValueError('INVALID_BAR')
        if previous is not None and t.timestamp()<=previous:raise ValueError('UNORDERED_BARS')
        previous=t.timestamp()
        if minutes>=1440:
            if t.astimezone(ET).date()>=now.astimezone(ET).date():continue
        elif t+timedelta(minutes=minutes)>now or not market_session(t)['active']:continue
        out.append(b)
    return out
def resample(bars,minutes):
    if minutes==1:return list(bars)
    buckets={}
    for b in bars:
        t=datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET);m=t.hour*60+t.minute-570;k=(t.date(),m//minutes);buckets.setdefault(k,[]).append(b)
    out=[]
    for (_,bucket),group in sorted(buckets.items()):
        first=datetime.fromtimestamp(group[0]['timestamp'],timezone.utc).astimezone(ET)
        if len(group)!=minutes or first.hour*60+first.minute!=570+bucket*minutes:continue
        if any(group[i]['timestamp']-group[i-1]['timestamp']!=60 for i in range(1,len(group))):continue
        out.append({'timestamp':group[0]['timestamp'],'open':group[0]['open'],'high':max(x['high'] for x in group),'low':min(x['low'] for x in group),'close':group[-1]['close'],'volume':sum(x['volume'] for x in group)})
    return out
def ema(values,n):
    if len(values)<n:return []
    v=sum(values[:n])/n;out=[v];alpha=2/(n+1)
    for x in values[n:]:v=alpha*x+(1-alpha)*v;out.append(v)
    return out
def calculate(bars):
    if not bars:return {'status':'UNAVAILABLE','bars':0}
    c=[b['close'] for b in bars];n=len(c);last=bars[-1];day=datetime.fromtimestamp(last['timestamp'],timezone.utc).astimezone(ET).date()
    current=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==day];current_ids={id(b) for b in current};prior=[b for b in bars if id(b) not in current_ids]
    v=sum(b['volume'] for b in current);vwap=sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in current)/v if v else None
    changes=[c[i]-c[i-1] for i in range(1,n)];rsi=None;atr=None
    if len(changes)>=14:
        gain=sum(max(x,0) for x in changes[:14])/14;loss=sum(max(-x,0) for x in changes[:14])/14
        for x in changes[14:]:gain=(gain*13+max(x,0))/14;loss=(loss*13+max(-x,0))/14
        rsi=50 if gain==loss==0 else 100 if loss==0 else 100-100/(1+gain/loss)
        tr=[max(bars[i]['high']-bars[i]['low'],abs(bars[i]['high']-c[i-1]),abs(bars[i]['low']-c[i-1])) for i in range(1,n)];atr=sum(tr[:14])/14
        for x in tr[14:]:atr=(atr*13+x)/14
    macd=None
    if n>=34:
        fast=ema(c,12);slow=ema(c,26);line=[a-b for a,b in zip(fast[14:],slow)];sig=ema(line,9);macd={'line':line[-1],'signal':sig[-1],'histogram':line[-1]-sig[-1]}
    swings_hi=[bars[i]['high'] for i in range(2,n-2) if all(bars[i]['high']>bars[j]['high'] for j in (i-2,i-1,i+1,i+2))]
    swings_lo=[bars[i]['low'] for i in range(2,n-2) if all(bars[i]['low']<bars[j]['low'] for j in (i-2,i-1,i+1,i+2))]
    structure='UNAVAILABLE'
    if len(swings_hi)>=2 and len(swings_lo)>=2:structure='HH_HL' if swings_hi[-1]>swings_hi[-2] and swings_lo[-1]>swings_lo[-2] else 'LH_LL' if swings_hi[-1]<swings_hi[-2] and swings_lo[-1]<swings_lo[-2] else 'MIXED'
    returns=[math.log(c[i]/c[i-1]) for i in range(max(1,n-20),n)]
    t=datetime.fromtimestamp(last['timestamp'],timezone.utc).astimezone(ET);same_slot=[b['volume'] for b in prior if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).time()==t.time()]
    rvol=last['volume']/statistics.mean(same_slot[-20:]) if len(same_slot)>=5 and statistics.mean(same_slot[-20:])>0 else None
    result={'status':'DESCRIPTIVE_ONLY','bars':n,'timestamp':last['timestamp'],'close':c[-1],'vwap_approx':vwap,'rsi14':rsi,'atr14':atr,'volume':last['volume'],'rvol_same_slot':rvol,'momentum10':c[-1]-c[-11] if n>=11 else None,'macd':macd,'realized_volatility_per_bar':statistics.stdev(returns) if len(returns)==20 else None,'swing_highs':swings_hi[-5:],'swing_lows':swings_lo[-5:],'support':max((x for x in swings_lo if x<c[-1]),default=None),'resistance':min((x for x in swings_hi if x>c[-1]),default=None),'structure':structure,'range':max(b['high'] for b in current)-min(b['low'] for b in current),'gap':current[0]['open']-prior[-1]['close'] if prior else None}
    previous=current[:-1];pv=sum(b['volume'] for b in previous)
    result.update(previous_close=c[-2] if n>=2 else None,previous_low=bars[-2]['low'] if n>=2 else None,previous_high=bars[-2]['high'] if n>=2 else None,previous_vwap_approx=sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in previous)/pv if pv else None)
    for period in (9,20,21,50,200):e=ema(c,period);result['ema'+str(period)]=e[-1] if e else None
    result['trend']='UNAVAILABLE' if result['ema50'] is None else 'BULL' if c[-1]>result['ema9']>result['ema21']>result['ema50'] else 'BEAR' if c[-1]<result['ema9']<result['ema21']<result['ema50'] else 'NEUTRAL'
    return result
def multi_timeframe(minute_rows,daily_rows=None,now=None,simulation=False):
    bars=normalize(minute_rows,now=now,simulation=simulation);out={str(n)+'m':calculate(resample(bars,n)) for n in (1,5,15,30,60)}
    out['1h']=out.pop('60m');out['daily']=calculate(normalize(daily_rows or [],1440,now,simulation=simulation))
    today=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==(now or datetime.now(timezone.utc)).astimezone(ET).date()]
    opening=[b for b in today if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).hour*60+datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).minute<585]
    out['opening_range']={'high':max(b['high'] for b in opening),'low':min(b['low'] for b in opening)} if len(opening)==15 and opening[-1]['timestamp']-opening[0]['timestamp']==840 else None
    return out
