"""Live SIP quote and one-minute stream analysis; never promote public bars."""
from datetime import datetime,timezone,timedelta
from core.sessions import market_session,ET
from data.models import stamp,finite,Quality
from features.indicators import ema

MAX_QUOTE_AGE=5

def _evaluate_feed(store,now=None,feed='sip'):
    now=now or datetime.now(timezone.utc);session=market_session(now)
    label='SIP' if feed=='sip' else 'IEX'
    out={'status':'UNAVAILABLE','reason':'No authenticated live '+label+' quote is available.','direction':None}
    if session['quality']!='DATA_OK' or not session['active']:
        return {**out,'reason':'No active verified US regular session; no live regular-session trend.'}
    q=store.get('quote:SPY' if feed=='sip' else 'research_quote:SPY:iex') or {};health=store.get('stream:'+feed) or {}
    clock=store.get('stream_clock:'+feed) or {}
    try:
        if clock.get('state')=='FUTURE_TIMESTAMP_REJECTED' and 0<=(now-stamp(clock['at'])).total_seconds()<=120:
            out={**out,'reason':label+' market timestamps are ahead of this computer clock and remain rejected. Check Windows time synchronization; no quote is retimed.'}
    except (KeyError,ValueError,TypeError):pass
    if health.get('state')=='FEED_NOT_CONFIGURED':return {**out,'reason':'Live '+label+' feed is not configured. Public bars are not real-time.'}
    try:
        if q.get('provider')!='alpaca-'+feed or q.get('symbol')!='SPY' or q.get('data_type')!='quote' or q.get('entitlement')!='REALTIME' or q.get('quality')!='DATA_OK':return out
        if health.get('state') not in ('CONNECTED','CONNECTED_IDLE') or not 0<=(now-stamp(health['at'])).total_seconds()<=30:return {**out,'reason':'Live feed is disconnected or its heartbeat is stale.'}
        source=stamp(q['source_timestamp']);received=stamp(q['received_timestamp']);age=(now-source).total_seconds()
        from core.signals import quote_valid
        if not quote_valid(q,now,MAX_QUOTE_AGE):return {**out,'reason':'Live quote exceeds the five-second freshness limit or has invalid timestamps.'}
        p=q['payload'];bid=p['bid'];ask=p['ask']
        if not finite(bid) or not finite(ask) or not 0<bid<=ask:return {**out,'reason':'Live bid/ask is invalid.'}
        mid=(bid+ask)/2
        out={**out,'status':'LIVE_QUOTE_ONLY','reason':'One-minute indicator history is warming up.','quote_time':source.isoformat(),'quote_age_seconds':age,'bid':bid,'ask':ask,'mid':mid,'provider':'alpaca-'+feed,'feed':feed,'coverage':'ALL_US_EXCHANGES' if feed=='sip' else 'SINGLE_EXCHANGE_IEX','analyzed_at':now.isoformat()}
        rows=[];previous=None
        for b in store.get('stream_bars:SPY' if feed=='sip' else 'research_stream_bars:SPY:iex',[]):
            t=stamp(b['t'])
            if previous is not None and t<=previous:raise ValueError('Unordered bars')
            previous=t
            if t.second or t.microsecond:raise ValueError('Misaligned minute bars')
            if not all(finite(b.get(k)) for k in ('o','h','l','c','v')) or not 0<b['l']<=min(b['o'],b['c'])<=max(b['o'],b['c'])<=b['h'] or b['v']<0:raise ValueError('Invalid bars')
            # Partial minute values never become completed indicator observations.
            if t+timedelta(minutes=1)>now:continue
            if t.astimezone(ET).date()!=now.astimezone(ET).date() or not market_session(t)['active']:continue
            if rows and t-stamp(rows[-1]['t'])!=timedelta(minutes=1):rows=[]
            rows.append(b)
        if len(rows)<31:return {**out,'completed_bars':len(rows)}
        end=stamp(rows[-1]['t'])+timedelta(minutes=1)
        if not 0<=(now-end).total_seconds()<=120:return {**out,'reason':'Live quote is fresh but one-minute indicator bars are stale.'}
        close=[b['c'] for b in rows];moving=ema(close,9)
        deltas={'live_mid_vs_ema9':mid-moving[-1],'ema9_slope':moving[-1]-moving[-2],'completed_15m_move':close[-1]-close[-16],'completed_30m_move':close[-1]-close[-31]}
        votes={k:'UP' if v>0 else 'DOWN' if v<0 else 'NEUTRAL' for k,v in deltas.items()}
        counts={k:sum(v==k for v in votes.values()) for k in ('UP','DOWN','NEUTRAL')}
        direction='UP' if mid>moving[-1]>moving[-2] and deltas['completed_15m_move']>0 else 'DOWN' if mid<moving[-1]<moving[-2] and deltas['completed_15m_move']<0 else 'MIXED'
        return {**out,'status':'LIVE_TREND','direction':direction,'reason':'Fresh live quote compared with completed one-minute indicators.','bar_end':end.isoformat(),'ema9':moving[-1],'momentum15_pct':(close[-1]/close[-16]-1)*100,'momentum30_pct':(close[-1]/close[-31]-1)*100,'counts':counts,'votes':votes,'completed_bars':len(rows),'version':feed+'-live-quote-minute-indicators-v1'}
    except (KeyError,ValueError,TypeError,OverflowError):
        if out['status']=='LIVE_QUOTE_ONLY':return {**out,'reason':'Invalid one-minute history; trend not inferred.'}
        return {**out,'reason':'Live quote provenance or timestamps are invalid.'}

def evaluate(store,now=None):
    now=now or datetime.now(timezone.utc)
    primary=_evaluate_feed(store,now,'sip')
    if primary['status']!='UNAVAILABLE':return primary
    secondary=_evaluate_feed(store,now,'iex')
    if secondary['status']!='UNAVAILABLE':
        return {**secondary,'selection':'EXPLICIT_SINGLE_EXCHANGE_RESEARCH_FALLBACK','primary_reason':primary['reason']}
    return {**primary,'iex_reason':secondary['reason']}

def text_for(result,now=None):
    now=now or datetime.now(timezone.utc)
    if result['status']=='UNAVAILABLE':
        extra='\nIEX: '+result['iex_reason'] if result.get('iex_reason') else ''
        return 'REAL-TIME: UNAVAILABLE\n'+result['reason']+extra+'\nThe analysis below is historical bar research, not a current entry/exit price.'
    label='Alpaca IEX — SINGLE EXCHANGE' if result.get('feed')=='iex' else 'Alpaca SIP — CONSOLIDATED'
    lines=['REAL-TIME QUOTE: SPY | '+label,'QUOTE TIME: '+stamp(result['quote_time']).astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET')+' | age %.1fs.'%result['quote_age_seconds'],
           'BID $%.2f | ASK $%.2f | MID $%.2f USD (midpoint, not a fill or last trade).'%(result['bid'],result['ask'],result['mid'])]
    if result['status']=='LIVE_TREND':
        c=result['counts'];lines+=['LIVE-QUOTE TREND: '+result['direction'],
            'INDICATOR SUPPORT: %d of 4 UP | %d of 4 DOWN | %d of 4 NEUTRAL.'%(c['UP'],c['DOWN'],c['NEUTRAL']),
            'RATIO: %d:%d:%d (four descriptive checks; not a forecast probability).'%(c['UP'],c['DOWN'],c['NEUTRAL']),
            'ONE-MINUTE BARS THROUGH: '+stamp(result['bar_end']).astimezone(ET).strftime('%H:%M:%S ET'),
            'Completed-bar movement: 15m %+.2f%% | 30m %+.2f%%.'%(result['momentum15_pct'],result['momentum30_pct']),
            'Current midpoint vs EMA9; EMA9 slope; completed 15m and30m changes.']
    else:lines+=['LIVE TREND: NOT ESTABLISHED — '+result['reason'],'The quote alone does not establish a trend; historical research is separate.']
    if result.get('feed')=='iex':lines+=['COVERAGE: IEX only; not consolidated NBBO, total-market volume or live options data.','SIP unavailable: '+result.get('primary_reason','not selected')]
    lines+=['ANALYZED: '+now.astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET'),'Quotes can change after this reply; no option entry/exit recommendation.']
    return '\n'.join(lines)
