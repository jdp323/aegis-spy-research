"""Deterministic descriptive patterns on completed contiguous bars; not a strategy."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ET=ZoneInfo('America/New_York')
def describe(bars,now):
    days={}
    for b in bars:
        t=datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET)
        if t.weekday()>4 or not 570<=t.hour*60+t.minute<960 or b['timestamp']+300>now.timestamp() or b['volume']<=0:continue
        days.setdefault(t.date().isoformat(),[]).append(b)
    if not days:return {'status':'INSUFFICIENT_DATA','action':'NO TRADE'}
    day=max(days);seq=sorted(days[day],key=lambda b:b['timestamp'])
    last=seq[-1];out={'status':'DESCRIPTIVE_ONLY','session':day,'as_of_bar':last['timestamp'],'action':'NO TRADE','validated_strategy':False,'opening_range_15m':None,'patterns':[]}
    first=datetime.fromtimestamp(seq[0]['timestamp'],timezone.utc).astimezone(ET)
    if len(seq)>=3 and first.hour==9 and first.minute==30 and seq[1]['timestamp']-seq[0]['timestamp']==300 and seq[2]['timestamp']-seq[1]['timestamp']==300:
        hi=max(b['high'] for b in seq[:3]);lo=min(b['low'] for b in seq[:3]);out['opening_range_15m']={'high':hi,'low':lo}
        if len(seq)>3:out['patterns'].append('CLOSE_ABOVE_OPENING_RANGE' if last['close']>hi else 'CLOSE_BELOW_OPENING_RANGE' if last['close']<lo else 'INSIDE_OPENING_RANGE')
    tail=seq[-3:]
    if len(tail)==3 and all(b['timestamp']-a['timestamp']==300 for a,b in zip(tail,tail[1:])):
        up=all(b['high']>a['high'] and b['low']>a['low'] for a,b in zip(tail,tail[1:]))
        down=all(b['high']<a['high'] and b['low']<a['low'] for a,b in zip(tail,tail[1:]))
        out['structure_3bars']='HIGHER_HIGHS_HIGHER_LOWS' if up else 'LOWER_HIGHS_LOWER_LOWS' if down else 'MIXED'
    else:out['structure_3bars']='UNAVAILABLE_GAPS_OR_HISTORY'
    volume=sum(b['volume'] for b in seq);vwap=sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in seq)/volume
    out['vwap_relationship']='ABOVE' if last['close']>vwap else 'BELOW' if last['close']<vwap else 'AT'
    out['limitations']='Single-source 5m observations; no inferred option returns, probability, entry timing or multi-timeframe confirmation.'
    return out
