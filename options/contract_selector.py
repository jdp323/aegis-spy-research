"""Research ranking; missing liquidity/Greeks fail closed. No synthetic Greeks."""
from datetime import datetime,timezone
import math
from options.ledger import contract
from data.models import quote,finite,Quality
from core.sessions import ET,market_session
def expected_move(spot,iv,years):
    return spot*iv*math.sqrt(years) if all(finite(x) and x>0 for x in (spot,iv,years)) else None
def select(chain,spot,direction,now=None,min_dte=1,target_distance=None,stop_distance=None,atr=None,max_premium=None,volatility_state='UNAVAILABLE',intraday_range=None):
    now=now or datetime.now(timezone.utc);day=now.astimezone(ET).date();accepted=[];rejected=[]
    for symbol,raw in chain.items():
        reasons=[]
        try:spec=contract(symbol)
        except ValueError:rejected.append({'symbol':symbol,'reasons':['UNSUPPORTED_CONTRACT']});continue
        dte=(datetime.fromisoformat(spec['expiry']).date()-day).days;kind=spec['type'];q=quote('alpaca',symbol,raw.get('latestQuote') or {},received=raw.get('received_timestamp',now.isoformat())).view(now,max_age=3 if dte==0 else 15);p=q['payload'];bid=p.get('bid');ask=p.get('ask');mid=p.get('mid');g=raw.get('greeks') or {};iv=raw.get('impliedVolatility');delta=g.get('delta');volume=raw.get('volume');oi=raw.get('openInterest')
        q['feed_quality']=raw.get('feed_quality','UNVERIFIED')
        if kind!=('C' if direction=='CALL' else 'P'):reasons.append('DIRECTION_MISMATCH')
        if not 0<=dte<=30:reasons.append('EXPIRATION_OUTSIDE_SCOPE')
        if dte<min_dte:reasons.append('INSUFFICIENT_THESIS_TIME')
        if q['quality']!=Quality.OK:reasons.append(q['quality'])
        spread=(ask-bid)/mid if finite(mid) and mid>0 else None
        if spread is None or spread>(.05 if dte==0 else .12):reasons.append('SPREAD_TOO_WIDE_OR_UNAVAILABLE')
        if not finite(volume) or volume<(500 if dte==0 else 100):reasons.append('VOLUME_INSUFFICIENT_OR_UNAVAILABLE')
        if not finite(oi) or oi<(1000 if dte==0 else 100):reasons.append('OI_INSUFFICIENT_OR_UNAVAILABLE')
        if any(not finite(g.get(k)) for k in ('delta','gamma','theta','vega')) or not finite(iv) or iv<=0:reasons.append('GREEKS_OR_IV_UNAVAILABLE')
        if finite(delta) and not (0<delta<=1 if kind=='C' else -1<=delta<0):reasons.append('INVALID_DELTA')
        if max_premium is not None and (not finite(ask) or ask*100>max_premium):reasons.extend(['PREMIUM_LIMIT','PREMIUM_ABOVE_CAP'])
        sess=market_session(now);minutes_left=sess['close_minute']-(now.astimezone(ET).hour*60+now.astimezone(ET).minute)
        if dte==0 and (not sess['active'] or minutes_left<90 or max_premium is None):reasons.append('ZERO_DTE_TIME_OR_RISK_NOT_VALIDATED')
        if dte==0 and (volatility_state in ('UNAVAILABLE','UNSAFE','ABNORMAL','HIGH_VOLATILITY') or not finite(iv) or iv>.6):reasons.append('ZERO_DTE_VOLATILITY_NOT_VALIDATED')
        years=max(0,dte+minutes_left/1440)/365;move=expected_move(spot,iv,years)
        if target_distance is not None and (move is None or target_distance>2*move):reasons.append('TARGET_EXCEEDS_EXPECTED_MOVE_LIMIT')
        record={**spec,'occ_symbol':symbol,'dte':dte,'bucket':'0DTE' if dte==0 else '1DTE' if dte==1 else '2–7 DTE' if dte<=7 else '8–30 DTE','bid':bid,'ask':ask,'mid':mid,'spread':ask-bid if finite(ask) and finite(bid) else None,'spread_pct':spread,'volume':volume,'oi':oi,'iv':iv,**{k:g.get(k) for k in ('delta','gamma','theta','vega')},'expected_move':move,'strike_distance':abs(float(spec['strike'])-spot),'target_distance':target_distance,'stop_distance':stop_distance,'atr':atr,'quote':q,'last':(raw.get('latestTrade') or {}).get('p'),'last_timestamp':(raw.get('latestTrade') or {}).get('t'),'greeks_timestamp':raw.get('greeksTimestamp'),'reasons':reasons}
        record['intraday_range']=intraday_range
        record['expected_move_comparisons']={k:(value/move if finite(value) and move else None) for k,value in {'range':intraday_range,'atr':atr,'target':target_distance,'stop':stop_distance,'strike_distance':record['strike_distance']}.items()}
        if reasons:rejected.append(record);continue
        # Preferences, not performance probabilities; penalties include carry and moneyness.
        record['selection_score']=round(max(0,100-spread*150-abs(abs(delta)-.5)*30-(15 if dte==0 else 0)-abs(g['theta'])/mid*10-abs(float(spec['strike'])-spot)/spot*100-iv*2-min(10,ask/10)+min(5,volume/10000)+min(5,oi/10000)),2)
        accepted.append(record)
    accepted.sort(key=lambda x:x['selection_score'],reverse=True)
    best=accepted[0] if accepted else None
    from options.chain_sanity import verify
    return {'best_contract':best,'chain_sanity_reasons':verify(best,accepted+rejected,now),'alternatives':accepted[1:6],'rejected':rejected,'method':'research-ranking-v2','note':'Volume/OI may be unavailable from snapshots; missing fields reject rather than invent liquidity.'}
