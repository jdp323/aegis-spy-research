"""Plain descriptive direction from verified completed public bars; not a forecast."""
from datetime import datetime,timezone,timedelta
from core.sessions import ET,market_session
from data.models import stamp,finite
from data.premarket_spy import URL,verified
from features.indicators import ema
VERSION='spy-basic-trend-v1'
def analyze(raw,now=None):
    now=now or datetime.now(timezone.utc);session=market_session(now);day=now.astimezone(ET).date().isoformat()
    out={'version':VERSION,'direction':'UNAVAILABLE','scope':session['state'],'reason':'Recent usable bars are missing.','action':'RESEARCH_ONLY','as_of':None}
    try:
        if session['quality']!='DATA_OK' or raw.get('source')!=URL or raw.get('symbol')!='SPY' or raw.get('status')!='RESEARCH_DATA_RECEIVED' or raw.get('use')!='DELAY_UNVERIFIED_RESEARCH_ONLY' or not verified(raw):return out
        fetched=stamp(raw['fetched_at'])
        if not 0<=(now-fetched).total_seconds()<=600:return {**out,'reason':'Research snapshot is stale.'}
        phase='PREMARKET' if session['state']=='PREMARKET' else 'REGULAR' if session['active'] else None
        if not phase:return {**out,'reason':'No active premarket or regular session; use /news for historical observations.'}
        start=240 if phase=='PREMARKET' else 570;end=570 if phase=='PREMARKET' else session['close_minute'];rows=[];previous=None
        for b in raw['bars']:
            ts=b['timestamp']
            if type(ts) is not int or (previous is not None and ts<=previous):raise ValueError('Unordered timestamps')
            previous=ts
            if ts+300>min(now.timestamp(),fetched.timestamp()):continue
            t=datetime.fromtimestamp(ts,timezone.utc).astimezone(ET);minute=t.hour*60+t.minute
            if t.date().isoformat()!=day or not start<=minute<end:continue
            if ts%300 or not all(finite(b.get(k)) for k in ('open','high','low','close','volume')) or not 0<b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] or b['volume']<0:raise ValueError('Invalid bar')
            # Basic direction uses OHLC prices only. Public extended-hours bars
            # sometimes omit volume; zero is not a verified absence of trading.
            # Such bars cannot establish VWAP/liquidity or authorize an option.
            rows.append(b)
        if not rows or not 0<=(now.timestamp()-rows[-1]['timestamp']-300)<=900:return {**out,'reason':'Latest completed bar is too old.'}
        tail=[]
        for b in rows:
            if tail and b['timestamp']-tail[-1]['timestamp']!=300:tail=[]
            tail.append(b)
        if len(tail)<10:return {**out,'reason':'Need ten contiguous completed five-minute bars in this session.'}
        c=[b['close'] for b in tail];moving=ema(c,9);momentum=(c[-1]/c[-4]-1)*100
        # Equal descriptive votes; correlated checks are not probabilities.
        deltas={'price_vs_ema9':c[-1]-moving[-1],'ema9_slope':moving[-1]-moving[-2],'momentum15':c[-1]-c[-4],'momentum30':c[-1]-c[-7]}
        votes={k:'UP' if v>0 else 'DOWN' if v<0 else 'NEUTRAL' for k,v in deltas.items()}
        counts={side:sum(v==side for v in votes.values()) for side in ('UP','DOWN','NEUTRAL')}
        out['support']={'version':'four-price-checks-v1','checks':votes,'counts':counts,'total':4,'up_pct':counts['UP']*25,'down_pct':counts['DOWN']*25,'neutral_pct':counts['NEUTRAL']*25,'ratio':str(counts['UP'])+':'+str(counts['DOWN'])+':'+str(counts['NEUTRAL']),'meaning':'SHARE_OF_CORRELATED_INDICATOR_CHECKS_NOT_PROBABILITY','lean':'UP' if counts['UP']>counts['DOWN'] else 'DOWN' if counts['DOWN']>counts['UP'] else 'MIXED'}
        direction='UP' if c[-1]>moving[-1]>moving[-2] and momentum>0 else 'DOWN' if c[-1]<moving[-1]<moving[-2] and momentum<0 else 'MIXED'
        volume=sum(b['volume'] for b in rows);vwap=sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in rows)/volume if volume else None
        return {**out,'direction':direction,'scope':phase,'reason':'Price is above a rising EMA9 and gained over the last 15 minutes.' if direction=='UP' else 'Price is below a falling EMA9 and fell over the last 15 minutes.' if direction=='DOWN' else 'Recent momentum and EMA9 do not agree on one direction.','as_of':datetime.fromtimestamp(rows[-1]['timestamp']+300,timezone.utc).isoformat(),'price':c[-1],'ema9':moving[-1],'momentum15_pct':momentum,'session_change_pct':(c[-1]/rows[0]['open']-1)*100,'vwap_approx':vwap,'volume_confirmation':'UNAVAILABLE' if any(b['volume']==0 for b in tail) else 'PROVIDER_REPORTED_UNVERIFIED','bars':len(tail),'source':URL,'source_sha256':raw['sha256'],'source_fetched_at':raw['fetched_at'],'delay':'UNVERIFIED'}
    except (KeyError,ValueError,TypeError,OverflowError):return {**out,'reason':'Invalid bars; direction not inferred.'}
def text_for(r):
    if r['direction']=='UNAVAILABLE':return 'SPY TREND CHECKS: 0/4 (0% usable coverage)\n'+r['reason']+'\nUp/down percentages need current price evidence. /news shows saved research.'
    s=r['support']
    return '\n'.join(['SPY TREND: '+r['direction']+' | HISTORICAL PUBLIC BARS | '+r['scope'],'NOT REAL-TIME — this is completed-bar analysis, not a current quote.','Observed through '+stamp(r['as_of']).astimezone(ET).strftime('%Y-%m-%d %H:%M ET'),'INDICATOR SUPPORT: UP %d%% | DOWN %d%% | NEUTRAL %d%%.'%(s['up_pct'],s['down_pct'],s['neutral_pct']),'RATIO: '+s['ratio']+' (up:down:neutral checks, four total).','RECENT PRICE MOVE: 15m %+.2f%% | session %+.2f%%.'%(r['momentum15_pct'],r['session_change_pct']),'LAST OBSERVED: $%.2f USD.'%r['price'],'WHY: '+r['reason'],'The percentages count price indicators; they are not the chance of a future rise/fall.','DATA: Public five-minute price bars; delay unverified. Volume confirmation '+r['volume_confirmation'].lower()+'.'])
def saved_text(now=None):
    from data.trend_spy import load
    now=now or datetime.now(timezone.utc);r=analyze(load(),now)
    if r['direction']!='UNAVAILABLE':return text_for(r)
    from monitoring.research_alerts import short_text,observe,load as regular_load
    session=market_session(now)
    return short_text(observe(regular_load(),session,now),session,now)

def on_demand_text(now=None):
    """Recompute for each command; never disguise a fetch failure as current data."""
    from data.trend_spy import refresh,COMMAND_CACHE_SECONDS
    requested=now or datetime.now(timezone.utc)
    raw=refresh(requested,max_age_seconds=COMMAND_CACHE_SECONDS)
    analyzed=now or datetime.now(timezone.utc)
    result=analyze(raw,analyzed)
    rendered=text_for(result)
    bar_end=result.get('as_of')
    # Early opening-session warmup and closed-session history use the same
    # freshly retrieved, hash-verified payload, never an unrelated old snapshot.
    if raw.get('status')=='RESEARCH_DATA_RECEIVED' and verified(raw):
        try:
            if 0<=(analyzed-stamp(raw['fetched_at'])).total_seconds()<=600:
                from core.spy_research import analyze as regular_analyze
                from monitoring.research_alerts import observe,short_text,load as regular_load
                regular=regular_analyze(raw,analyzed)
                prior=regular_load();comparison=(prior.get('multi_source') or {}).get('intraday_comparison',{})
                levels=regular.get('levels') or {}
                if comparison.get('status')=='DISAGREEMENT' and comparison.get('bar')==levels.get('last_completed_bar_at') and 0<=(analyzed-stamp(prior['source_fetched_at'])).total_seconds()<=600:
                    regular['multi_source']={'intraday_comparison':comparison}
                session=market_session(analyzed);observation=observe(regular,session,analyzed)
                if observation.get('reason')=='SOURCE_DISAGREEMENT' or (result['direction']=='UNAVAILABLE' and result['reason'] in ('Need ten contiguous completed five-minute bars in this session.','No active premarket or regular session; use /news for historical observations.') and observation['quality']=='PUBLIC_RESEARCH_ONLY'):
                    rendered=short_text(observation,session,analyzed,basic_raw=raw)
                    if observation.get('bar'):bar_end=(observation['bar']+timedelta(minutes=5)).isoformat()
        except (KeyError,ValueError,TypeError,OverflowError):pass
    mode=raw.get('refresh_mode','UNAVAILABLE')
    labels={'FRESH_FETCH':'Fetched for this request','RECENT_CACHE':'Recent shared cache (30-second refresh cooldown)',
            'REFRESH_IN_PROGRESS':'Another refresh is running; existing snapshot only',
            'FAILURE_COOLDOWN':'Previous fetch failed/incomplete; 60-second retry cooldown',
            'FETCH_FAILED':'Fetch failed; no current trend inferred'}
    if mode in ('FETCH_FAILED','FAILURE_COOLDOWN'):
        result['reason']='Public source could not supply usable data ('+raw.get('reason',raw.get('status','UNAVAILABLE'))+').'
        rendered=text_for(result)
    fetched='UNAVAILABLE'
    if raw.get('status')=='RESEARCH_DATA_RECEIVED':
        try:fetched=stamp(raw['fetched_at']).astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET')
        except (KeyError,ValueError,TypeError):pass
    age='\nBAR END AGE: %.0f seconds at analysis.'%(analyzed-stamp(bar_end)).total_seconds() if bar_end else ''
    return rendered+age+'\n\nANALYZED: '+analyzed.astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET')+'\nREFRESH: '+labels.get(mode,mode)+'.\nFETCHED: '+fetched+'.\nAnalysis recalculated now; fetching does not make public bars real-time.'
