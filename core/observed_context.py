"""V6 coherent snapshots and persisted exact data-rejection diagnostics."""
from datetime import datetime,timezone
from core.sessions import ET,market_session
from data.models import stamp,finite
from data.reliability import quote_diagnostics,describe,Events
from data.backfill import continuity
from features.indicators import normalize,multi_timeframe

def evaluate(store,now,simulation=False):
    keys=('quote:SPY','research_quote:SPY:iex','ntp_clock','v5_skew_budget','stream:sip','stream:iex','stream_bars:SPY','research_stream_bars:SPY:iex','daily','history_daily:iex','history_daily:sip','history_frames:iex','history_frames:sip','confirmed_minutes:iex','confirmed_minutes:sip')
    snapshot=store.snapshot(keys) if hasattr(store,'snapshot') else {k:store.get(k) for k in keys}
    # Tests/replay supply an explicit historical clock. Operational callers pass
    # a current clock; take it again after the coherent read to avoid receipt races.
    clock=datetime.now(timezone.utc)
    if not simulation and (getattr(store,'path',None) is not None or abs((clock-now).total_seconds())<60):now=clock
    result={'quote':{},'feed_quality':'UNAVAILABLE','bars':[],'rows':[],'features':{},'reason':None,'early':False,'direction':'MIXED','evaluated_at':now.isoformat(),'diagnostics':[],'synthetic_continuity_minutes':0}
    def reject(predicate,reason,**fields):
        result['reason']=reason;result['failed_predicate']=predicate;result.update(fields)
        if not simulation:
            minute=now.replace(second=0,microsecond=0).isoformat();key='v6-rejection:'+predicate
            if store.get(key)!=minute:
                store.put(key,minute);store.put('v6-latest-data-rejection',{'at':now.isoformat(),'predicate':predicate,'reason':reason,'diagnostics':result['diagnostics'],'heartbeat_age_seconds':result.get('heartbeat_age_seconds'),'bar_end_age_seconds':result.get('bar_end_age_seconds'),'feed_quality':result['feed_quality']})
                if getattr(store,'path',None):
                    log=Events(store.path.with_name('observability.sqlite'))
                    try:
                        d=next((d for d in result['diagnostics'] if d.get('predicate')==predicate),{})
                        log.add('DATA_REJECTION',result['feed_quality'].lower() if result['feed_quality'] in ('SIP','IEX') else 'worker',now,predicate=predicate,**{k:d[k] for k in ('source_age_seconds','receipt_age_seconds','source_receipt_skew_seconds','provider') if k in d})
                    finally:log.close()
        return result
    for key,label in [('quote:SPY','SIP'),('research_quote:SPY:iex','IEX')]:
        candidate=snapshot.get(key) or {}
        if simulation and candidate.get('feed_quality')=='SIMULATED':
            age=(now-stamp(candidate['source_timestamp'])).total_seconds()
            if 0<=age<=5:result.update(quote=candidate,feed_quality='SIMULATED');break
            result['feed_quality']='SIMULATED'
            return reject('SOURCE_TOO_OLD' if age>5 else 'SOURCE_AFTER_CLOCK','simulated source quote age outside five-second entry gate')
        d=quote_diagnostics(candidate,now,'alpaca-'+label.lower());result['diagnostics'].append(d)
        if not simulation and d['predicate'] is None:result.update(quote=candidate,feed_quality=label);break
    if not result['quote']:
        d=next((d for d in reversed(result['diagnostics']) if d['source_age_seconds'] is not None),result['diagnostics'][-1] if result['diagnostics'] else {'predicate':'QUOTE_TIMESTAMP_UNAVAILABLE','provider':'UNAVAILABLE','source_age_seconds':None,'receipt_age_seconds':None,'source_receipt_skew_seconds':None})
        return reject(d['predicate'],'data not fresh — '+describe(d))
    feed=result['feed_quality'];clock=snapshot.get('ntp_clock') or {}
    if clock.get('state')=='MEASURED' and abs(clock.get('offset_seconds',0))>(snapshot.get('v5_skew_budget') or 2):return reject('CLOCK_OFFSET','clock offset beyond tolerance')
    if not simulation:
        health=snapshot.get('stream:'+feed.lower()) or {}
        try:
            age=(now-stamp(health['at'])).total_seconds();result['heartbeat_age_seconds']=age
            if health.get('state') not in ('CONNECTED','CONNECTED_IDLE'):return reject('STREAM_DOWN','stream down: '+health.get('state','UNAVAILABLE')+'; reconnect status '+str(health.get('reconnect_attempt','UNAVAILABLE')))
            if not 0<=age<=30:return reject('HEARTBEAT_AGE',f'feed heartbeat not fresh: signed heartbeat age {age:+.3f} s; budget 30 s')
        except (KeyError,ValueError):return reject('HEARTBEAT_UNAVAILABLE','feed heartbeat unavailable')
    rows=snapshot.get('stream_bars:SPY' if feed in ('SIP','SIMULATED') else 'research_stream_bars:SPY:iex') or []
    result['rows']=rows
    try:
        bars=normalize(rows,now=now,simulation=simulation)
        today=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==now.astimezone(ET).date() and market_session(datetime.fromtimestamp(b['timestamp'],timezone.utc))['active']]
        if not today:return reject('BAR_TAIL_UNAVAILABLE','contiguous history missing: no completed current-session bars')
        age=now.timestamp()-today[-1]['timestamp']-60;result['bar_end_age_seconds']=age
        if not 0<=age<=120:return reject('BAR_END_AGE',f'completed bars not fresh: signed end age {age:+.3f} s; budget 120 s')
        minute=now.astimezone(ET).hour*60+now.astimezone(ET).minute;early=585<=minute<=600 and len(today)<31
        need=15 if early else 31
        start=max(today[-1]['timestamp']-(need-1)*60,int(now.astimezone(ET).replace(hour=9,minute=30,second=0,microsecond=0).timestamp()))
        slots,n=continuity(today,set(snapshot.get('confirmed_minutes:'+feed.lower()) or []),start,today[-1]['timestamp'],maximum=0 if early else 2)
        if len(slots)<need:return reject('BAR_TAIL_SHORT','opening range forming; insufficient completed history')
        # Ephemeral confirmed-empty slots do not reach features, signals or stores.
        result['synthetic_continuity_minutes']=n
        daily=snapshot.get('history_daily:'+feed.lower()) or ((snapshot.get('daily') or {}).get('payload',{}).get('bars',[]) if feed!='IEX' else [])
        fs=multi_timeframe(rows,daily,now,simulation=simulation)
        from features.indicators import calculate
        for frame,minutes in (('5m',5),('15m',15),('30m',30),('1h',60)):
            if fs[frame].get('trend') in (None,'UNAVAILABLE'):
                native=(snapshot.get('history_frames:'+feed.lower()) or {}).get(frame,[])
                # Native provider aggregates stay explicitly separate from strict
                # minute resampling. No synthetic minute creates an hourly candle.
                verified=normalize(native,minutes,now,simulation=simulation)
                verified=[b for b in verified if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).hour*60+datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).minute+minutes<=market_session(datetime.fromtimestamp(b['timestamp'],timezone.utc))['close_minute']]
                if verified:
                    value=calculate(verified);value.update(history_source='PROVIDER_NATIVE_AGGREGATES',feed_quality=feed)
                    fs[frame]=value
        px=result['quote']['payload']['mid'];vwap=fs['1m'].get('vwap_approx')
        fifteen=today[-1]['timestamp']-15*60;older=next((b for b in today if b['timestamp']==fifteen),None);move=today[-1]['close']-older['close'] if older else None
        direction='UP' if finite(vwap) and finite(move) and px>vwap and move>0 else 'DOWN' if finite(vwap) and finite(move) and px<vwap and move<0 else 'MIXED'
        result.update(bars=today,features=fs,early=early,direction=direction,price_change_15m=move,opening_range_status='AVAILABLE' if fs['opening_range'] else 'OPENING RANGE UNAVAILABLE',early_context=store.get('premarket_report:'+now.astimezone(ET).date().isoformat()) or {})
        if not simulation:store.put('v6-frame-availability',{k:fs.get(k,{}).get('trend') not in (None,'UNAVAILABLE') for k in ('1m','5m','15m','30m','1h','daily')})
    except (ValueError,KeyError,TypeError,IndexError) as error:return reject('BAR_TAIL_GAP','contiguous history missing: '+(str(error) if isinstance(error,ValueError) else 'invalid bar inputs'))
    return result
