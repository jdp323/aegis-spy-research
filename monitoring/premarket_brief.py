"""Separate9:15 ET public research report; no actionable option signal or promotion."""
import math,json
from datetime import datetime,timezone,timedelta
from core.sessions import ET,market_session
from data.models import stamp,finite
from data.premarket_spy import URL,collect_once,verified
from features.indicators import ema,calculate
VERSION='spy-premarket-scenarios-v2'
def settings(config):
    c={'enabled':True,'lead_minutes':15,'catchup_minutes':5,**config.get('premarket_report',{})}
    if type(c['enabled']) is not bool or type(c['lead_minutes']) is not int or c['lead_minutes']!=15 or type(c['catchup_minutes']) is not int or not 1<=c['catchup_minutes']<=5:raise ValueError('INVALID_PREMARKET_REPORT_CONFIGURATION')
    return c
def previous_session(day):
    for delta in range(1,11):
        candidate=day-timedelta(days=delta)
        t=datetime(candidate.year,candidate.month,candidate.day,10,tzinfo=ET)
        if market_session(t)['active']:return candidate.isoformat()
    return None
def aggregate(rows,minutes):
    groups={}
    for b in rows:
        local=datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET)
        bucket=(local.hour*60+local.minute-240)//minutes
        groups.setdefault(bucket,[]).append(b)
    out=[];needed=minutes//5
    for bucket,group in sorted(groups.items()):
        first=datetime.fromtimestamp(group[0]['timestamp'],timezone.utc).astimezone(ET)
        if len(group)!=needed or first.hour*60+first.minute!=240+bucket*minutes or any(b['timestamp']-a['timestamp']!=300 for a,b in zip(group,group[1:])):continue
        out.append({'timestamp':group[0]['timestamp'],'open':group[0]['open'],'high':max(b['high'] for b in group),'low':min(b['low'] for b in group),'close':group[-1]['close'],'volume':sum(b['volume'] for b in group)})
    return out
def build(raw,news=None,now=None):
    now=now or datetime.now(timezone.utc);local=now.astimezone(ET);day=local.date().isoformat()
    report={'version':VERSION,'date':day,'generated_at':now.isoformat(),'cutoff':local.replace(hour=9,minute=15,second=0,microsecond=0).isoformat(),'quality':'UNAVAILABLE','bias':'UNAVAILABLE','action':'NO TRADE','reason':'Usable current premarket data is missing.','news':'UNAVAILABLE','option_quotes':'UNAVAILABLE','validated_prediction':False}
    try:
        from data.premarket_authorized import verified as authorized_verified
        authorized=raw.get('source')=='https://data.alpaca.markets/v2/stocks/SPY/bars' and raw.get('use')=='IEX_AUTHORIZED_PRICE_RESEARCH_ONLY' and raw.get('feed_quality')=='IEX' and authorized_verified(raw)
        if raw.get('symbol')!='SPY' or raw.get('session_date')!=day or raw.get('status')!='RESEARCH_DATA_RECEIVED' or not (authorized or raw.get('source')==URL and raw.get('use')=='DELAY_UNVERIFIED_RESEARCH_ONLY' and verified(raw)):raise ValueError('Premarket source/cache unavailable or unverified.')
        fetched=stamp(raw['fetched_at'])
        if not 0<=(now-fetched).total_seconds()<=600:raise ValueError('Premarket snapshot is stale.')
        cutoff=min(stamp(report['cutoff']),now,fetched);groups={};previous=None
        for b in raw['bars']:
            ts=b['timestamp']
            if type(ts) is not int:raise ValueError('Invalid bar timestamp.')
            if ts+300>cutoff.timestamp():continue
            if ts%300 or (previous is not None and ts<=previous):raise ValueError('Unordered or unaligned completed bars.')
            previous=ts
            if not all(finite(b.get(k)) for k in ('open','high','low','close','volume')) or not 0<b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] or b['volume']<0:raise ValueError('Invalid OHLCV.')
            t=datetime.fromtimestamp(ts,timezone.utc).astimezone(ET);groups.setdefault(t.date().isoformat(),[]).append(b)
        rows=[b for b in groups.get(day,[]) if 240<=datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).hour*60+datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).minute<555]
        if len(rows)<6 or (cutoff.timestamp()-rows[-1]['timestamp']-300)>900:raise ValueError('Not enough recent completed premarket bars.')
        volume=sum(b['volume'] for b in rows);vwap=sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in rows) /volume if volume else None
        first,last=rows[0],rows[-1];timeframes={}
        for minutes in (15,30):
            bars=aggregate(rows,minutes)
            # Warm indicators only on the final contiguous sequence, never across gaps.
            tail=[]
            for b in bars:
                if tail and b['timestamp']-tail[-1]['timestamp']!=minutes*60:tail=[]
                tail.append(b)
            features=calculate(tail);closes=[b['close'] for b in tail];moving=ema(closes,9)
            trend='UNAVAILABLE' if not moving else 'UP' if closes[-1]>moving[-1] else 'DOWN' if closes[-1]<moving[-1] else 'FLAT'
            timeframes[str(minutes)+'m']={'bars':len(tail),'trend':trend,'ema9':moving[-1] if moving else None,'rsi14':features.get('rsi14'),'momentum10':features.get('momentum10'),'as_of':datetime.fromtimestamp(tail[-1]['timestamp']+minutes*60,timezone.utc).isoformat() if tail else None}
        prior_day=previous_session(local.date());prior=[]
        for b in groups.get(prior_day,[]):
            if market_session(datetime.fromtimestamp(b['timestamp'],timezone.utc))['active']:prior.append(b)
        prior_levels=None
        if prior:
            close=market_session(datetime.fromtimestamp(prior[0]['timestamp'],timezone.utc))['close_minute']
            start=datetime.fromtimestamp(prior[0]['timestamp'],timezone.utc).astimezone(ET)
            if start.hour*60+start.minute==570 and len(prior)==(close-570)//5 and all(b['timestamp']-a['timestamp']==300 for a,b in zip(prior,prior[1:])):
                prior_levels={'date':prior_day,'close_proxy':prior[-1]['close'],'high':max(b['high'] for b in prior),'low':min(b['low'] for b in prior)}
        gap=(last['close']/prior_levels['close_proxy']-1)*100 if prior_levels else None
        agreement=timeframes['15m']['trend']==timeframes['30m']['trend']
        bias='BULLISH' if vwap is not None and prior_levels and agreement and timeframes['15m']['trend']=='UP' and last['close']>vwap and gap>=.1 else 'BEARISH' if vwap is not None and prior_levels and agreement and timeframes['15m']['trend']=='DOWN' and last['close']<vwap and gap<=-.1 else 'MIXED / WAIT'
        if vwap is None and agreement and timeframes['15m']['trend'] in ('UP','DOWN'):bias='BULLISH' if timeframes['15m']['trend']=='UP' else 'BEARISH'
        report.update(quality='IEX_RESEARCH_ONLY' if authorized else 'PUBLIC_RESEARCH_ONLY',bias=bias,reason='15m/30m EMA9 direction, approximate VWAP and gap align.' if bias in ('BULLISH','BEARISH') else 'Trend, gap and VWAP do not all align, or history is insufficient.',levels={'last':last['close'],'high':max(b['high'] for b in rows),'low':min(b['low'] for b in rows),'vwap_approx':vwap,'observed_premarket_change_pct':(last['close']/first['open']-1)*100,'gap_pct':gap},prior=prior_levels,timeframes=timeframes,as_of_bar=datetime.fromtimestamp(last['timestamp'],timezone.utc).isoformat(),observed_bars=len(rows),expected_bars=63,source=raw['source'],source_fetched_at=raw['fetched_at'],source_sha256=raw['sha256'])
        if vwap is None:report['reason']='Price-only 15m/30m EMA9 direction; VWAP and volume confirmation UNAVAILABLE (zero reported volume).'
        # News coverage is independently optional; absence never becomes "no events".
        if news and news.get('quality')=='DATA_OK' and not news.get('stale',False) and 0<=(now-stamp(news['verified_at'])).total_seconds()<=7*86400:
            from news.engine import KINDS
            report['news']=news.get('risk') if news.get('risk') in ('HIGH','MODERATE','NORMAL') else 'UNAVAILABLE'
            report['events']=[{'kind':e.get('type',e.get('kind')),'time':e.get('time_utc',e.get('time')),'time_source':e.get('time_source')} for e in news.get('events',[]) if e.get('type',e.get('kind')) in KINDS and 0<=(stamp(e.get('time_utc',e.get('time')))-now).total_seconds()<=86400][:3]
    except (KeyError,TypeError,ValueError,OverflowError,OSError) as error:report['reason']=str(error) if isinstance(error,ValueError) else 'Premarket input schema is invalid.'
    return report
def text_for(r):
    lines=['SPY PREMARKET MEGA REPORT | '+r['date']+' 09:15 ET','RESEARCH OUTLOOK — not a buy/sell signal.','ACTION: NO TRADE.']
    if r['quality'] not in ('PUBLIC_RESEARCH_ONLY','IEX_RESEARCH_ONLY'):
        return '\n'.join(lines+['BIAS: UNAVAILABLE','WHY: '+r['reason'],'15m / 30m trends, overnight gap and levels: not established.','CALL / PUT: No recommendation; no premium, stop or target issued.','NEWS: UNAVAILABLE. No event-free session assumed.','Prediction accuracy and closing price: not established.','/premarket = saved report | /setup = trade readiness'])
    l=r['levels'];lens='Call-side research' if r['bias']=='BULLISH' else 'Put-side research' if r['bias']=='BEARISH' else 'Neither side favored'
    lines+=['BIAS: '+r['bias']+' | '+lens+' only.','WHY: '+r['reason'],'LAST OBSERVED: $%.2f USD | '%l['last']+stamp(r['as_of_bar']).astimezone(ET).strftime('%H:%M')+'-'+(stamp(r['as_of_bar'])+timedelta(minutes=5)).astimezone(ET).strftime('%H:%M ET'),'OVERNIGHT GAP: '+('%.2f%% vs previous regular final5m close proxy.'%l['gap_pct'] if l['gap_pct'] is not None else 'UNAVAILABLE — previous complete session missing.'),'PREMARKET: high $%.2f | low $%.2f | approximate VWAP '%(l['high'],l['low'])+('UNAVAILABLE (zero reported volume).' if l['vwap_approx'] is None else '$%.2f.'%l['vwap_approx']),'OBSERVED PREMARKET MOVE: %+.2f%% from first available premarket bar; %d/%d possible bars.'%(l['observed_premarket_change_pct'],r['observed_bars'],r['expected_bars'])]
    for name,f in r['timeframes'].items():
        detail='EMA9 $%.2f'%f['ema9'] if f['ema9'] is not None else 'EMA9 unavailable'
        if f['rsi14'] is not None:detail+=' | RSI14 %.1f'%f['rsi14']
        lines.append(name+' TREND: '+f['trend']+' | '+detail+' | '+str(f['bars'])+' contiguous bars'+(' through '+stamp(f['as_of']).astimezone(ET).strftime('%H:%M ET') if f['as_of'] else '')+'.')
    if r['prior']:lines.append('PREVIOUS SESSION '+r['prior']['date']+': high $%.2f | low $%.2f | final5m close $%.2f (auction close unverified).'%(r['prior']['high'],r['prior']['low'],r['prior']['close_proxy']))
    lines+=['BULLISH SCENARIO: After the open, strength beyond the observed premarket high would support an upward continuation thesis; failure back inside the range weakens it.','BEARISH SCENARIO: Weakness below the observed premarket low would support a downward thesis; recovery inside the range weakens it.','MIXED SCENARIO: Staying inside the range or conflicting trends means no clear direction.','These are conditional research scenarios, not entry triggers or validated predictions.','NEWS / MACRO RISK: '+r['news']+'. Unknown coverage means event risk cannot be cleared.']
    for event in r.get('events',[]):lines.append('CONFIGURED EVENT: '+event['kind']+' '+stamp(event['time']).astimezone(ET).strftime('%Y-%m-%d' if event.get('time_source')=='DATE_ONLY' else '%Y-%m-%d %H:%M ET')+(' (all-day risk; release time unavailable)' if event.get('time_source')=='DATE_ONLY' else ''))
    lines+=['CALL / PUT CONTRACT, ENTRY / STOP / TARGET: Not issued — verified option data, risk and strategy evidence are missing.','CLOSING PRICE / PROBABILITY: Not established. No calibrated premarket forecasting model.','DATA: '+r.get('source','UNAVAILABLE')+'; '+('IEX single-exchange authorized historical prices, not an executable quote' if r['quality']=='IEX_RESEARCH_ONLY' else 'public chart, delay UNVERIFIED')+'; approximate VWAP unavailable without volume.','REVIEW: Reassess with actual opening price/volume; this outlook can fail. /news for later research.']
    return '\n'.join(lines)
def update(store,news,config,publish,now=None,collector=None):
    now=now or datetime.now(timezone.utc);session=market_session(now);c=settings(config);local=now.astimezone(ET);minute=local.hour*60+local.minute;day=session['date']
    state='DISABLED' if not c['enabled'] else 'NO_SESSION' if session['quality']!='DATA_OK' or session['state'] in ('HOLIDAY','CLOSED') else 'WAITING_09_15_ET'
    if not c['enabled'] or session['quality']!='DATA_OK' or session['state']!='PREMARKET' or not 555<=minute<555+c['catchup_minutes']:
        if minute>=555 and state=='WAITING_09_15_ET':state='WINDOW_CLOSED'
        store.put('premarket_health',{'at':now.isoformat(),'date':day,'state':state,'scheduled_time':'09:15 ET'});return None
    key='premarket_report:'+day;old=store.get(key)
    if old and old.get('queued'):return None
    raw=(collector or collect_once)(day,now)
    effective=now if collector else datetime.now(timezone.utc)
    if effective.astimezone(ET).hour*60+effective.astimezone(ET).minute>=555+c['catchup_minutes']:return None
    report=old or build(raw,news,effective);event_id='premarket-mega-'+day+'-v1'
    from news.market_outlook import build as outlook_build,text_for as outlook_text
    report['market_outlook']=outlook_build(store,effective,premarket=report)
    message='SPY MORNING BRIEF — 09:15 ET\n'+outlook_text(report['market_outlook'])
    if report.get('quality')=='PUBLIC_RESEARCH_ONLY':
        levels=report['levels'];message+='\nPremarket observed high $%.2f / low $%.2f | approximate VWAP $%.2f (public bars, delay unverified).'%(levels['high'],levels['low'],levels['vwap_approx']) if levels['vwap_approx'] is not None else '\nPremarket price levels available; VWAP UNAVAILABLE (zero reported volume).'
    # Stable event ID plus atomic publisher protects restart/uncertain delivery.
    report['message']=message[:3400]
    from monitoring.simple_notifications import enabled
    if config.get('notifications',{}).get('profile')=='simple':
        o=report['market_outlook'];events=(news or {}).get('events',[])
        today=[e.get('name',e.get('type','event'))+(' (all-day)' if e.get('time_source')=='DATE_ONLY' else '') for e in events if stamp(e.get('time_utc',e.get('time'))).astimezone(ET).date()==local.date()]
        short_message='SPY MORNING — 09:15 ET\nPrice trend: '+str(o.get('price_bias',o.get('bias','UNAVAILABLE')))+'\nNews: '+str(o.get('news_bias','UNAVAILABLE'))+'\nToday: '+('; '.join(today[:3]) or 'No listed event in the loaded calendar; completeness still applies.')+'\nSaved outlook; not a live verdict. /trend after the open; /news for sources.'
        store.put(key,report)
        if enabled(config,'morning'):publish(store,event_id,short_message,'PRIVATE','owner',kind='RESEARCH')
    else:
        store.put(key,report);publish(store,event_id,report['message'],kind='RESEARCH')
    report.update(queued=True,event_id=event_id);store.put(key,report)
    store.put('premarket_health',{'at':effective.isoformat(),'date':day,'state':'QUEUED','quality':report['quality'],'scheduled_time':'09:15 ET','event_id':event_id})
    store.audit(event_id,'premarket_research_notification','worker',{'quality':report['quality'],'bias':report['bias'],'action':'NO TRADE'});return event_id
def saved_text(store,now=None):
    now=now or datetime.now(timezone.utc);session=market_session(now);r=store.get('premarket_report:'+session['date'])
    if not r:
        from core.verdict import next_open
        nxt=next_open(now);local=now.astimezone(ET)
        scheduled=nxt-timedelta(minutes=15) if nxt else None
        due_today=local.replace(hour=9,minute=15,second=0,microsecond=0)
        day_open=market_session(local.replace(hour=9,minute=30,second=0,microsecond=0))['active']
        if day_open and now<due_today:state='NOT DUE YET — the scheduled report is at 09:15 ET today.'
        elif day_open:state='REPORT MISSING — the scheduled window passed. Check /health for worker and delivery status.'
        else:state='NO REPORT DUE TODAY — '+session['state']+'.'
        return '\n'.join(['SPY PREMARKET REPORT',state,'No report saved for '+session['date']+'.',
            'Next scheduled report: '+(scheduled.strftime('%a %Y-%m-%d %H:%M ET') if scheduled else 'UNAVAILABLE — exchange calendar needs refresh')+'.',
            'Computer must remain awake/online. /outlook and /news show current available news context.',
            'Current-session public premarket bars start at 04:00 ET; sufficient completed bars are required. Public data delay is unverified.',
            'Call/put lens is research only; no order or live option recommendation.'])
    return 'SAVED 09:15 OUTLOOK — not current-price or exit monitoring.\n'+(r.get('message') or text_for(r))

def command_text(store,now=None,refresh=None):
    """On-demand draft, isolated from the once-daily scheduled report/reservation."""
    now=now or datetime.now(timezone.utc);local=now.astimezone(ET);session=market_session(now)
    if store.get('premarket_report:'+session['date']):return saved_text(store,now)
    if session['state']!='PREMARKET' or local.hour*60+local.minute>=555:return saved_text(store,now)
    if local.hour*60+local.minute<270:
        return saved_text(store,now)+'\nDRAFT: warming up — at least six completed 5-minute bars are needed (not before 04:30 ET).'
    actual_clock=refresh is None
    if refresh is None:
        from data.trend_spy import refresh
    raw=refresh(now=now,max_age_seconds=300)
    # Receipt can be seconds after command entry. Do not compare that source
    # against a clock captured before the fetch or reserve a missed report.
    if actual_clock:
        now=datetime.now(timezone.utc);local=now.astimezone(ET);session=market_session(now)
        if session['state']!='PREMARKET' or local.hour*60+local.minute>=555 or store.get('premarket_report:'+session['date']):return saved_text(store,now)
    raw={**raw,'session_date':session['date']}
    from news.engine import NewsProvider
    from core.storage import ROOT
    report=build(raw,NewsProvider(ROOT/'config/news_calendar.json').snapshot(now),now)
    if report['quality']!='PUBLIC_RESEARCH_ONLY':
        return saved_text(store,now)+'\nDRAFT: UNAVAILABLE — '+report.get('reason','source or completed bars unavailable')+'. No direction or price invented.'
    from news.market_outlook import build as outlook_build,text_for as outlook_text
    return ('ON-DEMAND PREMARKET DRAFT — '+local.strftime('%Y-%m-%d %H:%M ET')+'\n'
            'Separate from the scheduled 09:15 report; not a live quote or trade instruction.\n'+
            outlook_text(outlook_build(store,now,premarket=report))+'\nScheduled report is still due at 09:15 ET.')
