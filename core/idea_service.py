"""V5 SPY-only ideas and schedule. Options are optional; all live paths remain closed."""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import json,statistics
from core.storage import ROOT
from core.sessions import ET,market_session
from core.idea_config import settings
from data.models import stamp,finite
from features.indicators import normalize,multi_timeframe
from strategies.idea_setups import detect,pending_triggers
from backtesting.idea_tracker import IdeaTracker,score_text,evidence
from core.signals import quote_valid,option_quote_valid
def context(store,now,simulation=False):
    from core.observed_context import evaluate
    from core.research_horizons import context as bar_context,describe
    result=evaluate(store,now,simulation)
    tail=result.get('bars',[])[-31:]
    if not result['reason'] and len(tail)==31 and all(b['timestamp']-a['timestamp']==60 for a,b in zip(tail,tail[1:])):
        # Reuse the coherent genuine-bar calculation; no second read or duplicate
        # indicator pass. Confirmed-empty slots never satisfy this shortcut.
        result['bar_research']={'quality':'COMPLETED_BAR_RESEARCH_ONLY','reason':None,'features':result['features'],'bars':result['bars'],'rows':result['rows'],'provider':result['quote'].get('provider','UNAVAILABLE'),'feed_quality':result['feed_quality'],'entry_eligible':False,'source_timestamp':datetime.fromtimestamp(tail[-1]['timestamp']+60,timezone.utc).isoformat(),'last_completed_close':tail[-1]['close'],'bar_end_age_seconds':result.get('bar_end_age_seconds')}
    else:result['bar_research']=bar_context(store,now,simulation)
    result['horizons']=describe(result['bar_research'],now)
    return result
def candidates(ctx,news,config,now,simulation=False):
    if ctx['reason'] or not market_session(now)['active']:return [],ctx['reason'] or 'outside trading window'
    if not simulation and not quote_valid(ctx.get('quote') or {},now,5):return [],'fresh underlying quote unavailable'
    if news.get('quality')!='DATA_OK' or news.get('risk') not in ('NORMAL','MODERATE'):return [],'calendar not verified' if news.get('quality')!='DATA_OK' else 'event blackout active'
    from options.trade_plan import mismatch
    ideas=detect(ctx['features'],ctx['bars'],ctx['quote'],now,config,ctx['early'])
    for i in ideas:i['news_status']=news['risk'];i['feed_quality']=ctx['feed_quality']
    return ideas,None
def trend_line_details(ctx,now,config,active=None,decision=None):
    if ctx['reason']:
        minute=now.astimezone(ET).hour*60+now.astimezone(ET).minute;nxt=(minute//15+1)*15
        return 'SPY '+now.astimezone(ET).strftime('%H:%M ET')+'\nTrend unavailable: '+ctx['reason']+'\nFailed check: '+ctx.get('failed_predicate','UNAVAILABLE')+'\nDECISION: NO TRADE\nNext retry '+('%02d:%02d ET'%(nxt//60,nxt%60) if nxt<=market_session(now)['close_minute']-15 else 'next trading session')+'.'
    f=ctx['features'];px=ctx['quote']['payload']['mid'];direction=ctx['direction'];aligned='BULL' if direction=='UP' else 'BEAR' if direction=='DOWN' else None
    count=sum(x.get('trend')==aligned for k,x in f.items() if k in ('1m','5m','15m','30m','1h','daily')) if aligned else 0
    lines=['SPY '+now.astimezone(ET).strftime('%H:%M ET')+f' · {px:.2f}']
    if ctx['early']:
        r=ctx.get('early_context',{});prior=r.get('prior',{});gap=r.get('levels',{}).get('gap_pct');fmt=lambda x:'%.2f'%x if finite(x) else 'UNAVAILABLE'
        lines+=['EARLY READ (opening range complete; limited data)','Premarket bias '+r.get('bias','UNAVAILABLE')+'; gap '+fmt(gap)+'%; prior low/high '+fmt(prior.get('low'))+'/'+fmt(prior.get('high')),'Daily/hourly structure: '+f.get('daily',{}).get('trend','UNAVAILABLE')+'/'+f.get('1h',{}).get('trend','UNAVAILABLE')]
    frames={k:f.get(k,{}).get('trend','UNAVAILABLE') for k in ('1m','5m','15m','30m','1h','daily')}
    available={k:v for k,v in frames.items() if v not in (None,'UNAVAILABLE')};missing=[k for k in frames if k not in available]
    count=sum(v==aligned for v in available.values()) if aligned else sum(v=='NEUTRAL' for v in available.values())
    detail='above bar VWAP, positive 15-minute change' if direction=='UP' else 'below bar VWAP, negative 15-minute change' if direction=='DOWN' else 'VWAP and price change do not align or an endpoint is missing'
    lines+=['Price bias: '+direction+' ('+detail+')','Frames: '+str(count)+' of '+str(len(available))+' available '+('bullish' if direction=='UP' else 'bearish' if direction=='DOWN' else 'neutral')+' ('+str(len(missing))+' unavailable)']
    if missing:lines.append('Unavailable frames: '+', '.join(missing)+'. Counts are correlated checks, not prediction odds.')
    if available and direction in ('UP','DOWN') and count==0:lines.append('Price bias uses VWAP and recent change; frame trends use EMA9/21/50 and do not confirm that bias.')
    lines.append('Opening range: '+('AVAILABLE' if f.get('opening_range') else 'OPENING RANGE UNAVAILABLE — opening-range setups disabled until genuine bars recover.'))
    if ctx.get('synthetic_continuity_minutes'):lines.append(str(ctx['synthetic_continuity_minutes'])+' confirmed-empty continuity slots; excluded from indicators, volume and fills.')
    for t in pending_triggers(f,config):lines.append(t['direction']+(' idea if a completed candle closes above ' if t['direction']=='CALL' else ' idea if a completed candle closes below ')+f"{t['price']:.2f} with volume and structure")
    for direction in ('CALL','PUT'):
        if not any(t['direction']==direction for t in pending_triggers(f,config)):lines.append(direction+' unmet trigger: UNAVAILABLE; wait for new structure')
    if active:lines.append('Active idea: '+active['direction']+f" · trigger {active['trigger']:.2f} · valid until "+stamp(active['signal_expiry']).astimezone(ET).strftime('%H:%M ET'))
    lines+=['DECISION: '+(decision or 'NO TRADE — no confirmed idea right now')]
    minute=now.astimezone(ET).hour*60+now.astimezone(ET).minute;nxt=(minute//15+1)*15
    lines+=['Next update '+('%02d:%02d ET'%(nxt//60,nxt%60) if nxt<=market_session(now)['close_minute']-15 else 'next trading session')+'.','Data: '+ctx['feed_quality']+(' only (one exchange)' if ctx['feed_quality']=='IEX' else '')+' · quote '+stamp(ctx['quote']['source_timestamp']).astimezone(ET).strftime('%H:%M:%S ET')]
    return '\n'.join(lines)
def legacy_idea_text(i,tag,config):
    c=settings(config);sign=1 if i['direction']=='CALL' else -1;distance=abs(i['entry']-i['invalidation']);d=c['rough_risk_delta_range'];time=stamp(i['timestamp']).astimezone(ET)
    lines=['🔔 SPY '+i['direction']+' IDEA · '+time.strftime('%H:%M ET')+' (PAPER / UNVALIDATED)',('ENTER NOW: SPY '+f"{i['entry']:.2f}"+'; do not chase '+('above ' if sign==1 else 'below ')+f"{i['do_not_chase']:.2f}" if i['entry_mode']=='ENTER NOW' else 'WHEN SPY TRADES '+('ABOVE ' if sign==1 else 'BELOW ')+f"{i['trigger']:.2f}"),'Stop: EXIT REVIEW if SPY '+('falls below ' if sign==1 else 'rises above ')+f"{i['invalidation']:.2f}",f"Target 1: {i['t1']:.2f} · Target 2: {i['t2']:.2f}",'Hold: '+i['horizon'].lower()+' — review exit by '+stamp(i['max_hold_until']).astimezone(ET).strftime('%H:%M ET'),'Valid until '+stamp(i['signal_expiry']).astimezone(ET).strftime('%H:%M ET'),f'Rough risk: ${distance*d[0]*100:.0f}–${distance*d[1]*100:.0f}/contract (approx.; delta {d[0]:.2f}–{d[1]:.2f}, before fees; not a premium quote)','Setup: '+i['setup_type']+('-early' if i.get('early') else '')+' · Evidence: '+tag['evidence_tag']+' ('+str(tag['closed'])+' closed)','Why: '+' · '.join(i.get('explanation',[])),'Pick the option yourself; guideline: 2–7 DTE, delta about 0.40–0.55.','Data: '+i['feed_quality'],'Unvalidated research. You place orders yourself.']
    plan=i.get('option_plan');contract=i.get('option_contract')
    if plan and contract and option_quote_valid(contract.get('quote',{}),stamp(i['timestamp'])):
        lines[6:7]=[f"Optional {contract['symbol']}: limit est. ${plan['limit']:.2f}; T1/T2 est. ${plan['t1_bid']:.2f}/${plan['t2_bid']:.2f}; stop est. ${plan['stop_bid']:.2f}. IV/spread can change.",*plan.get('warnings',[])]
    return '\n'.join(lines)
def trend_line(ctx,now,config,active=None,decision=None):
    from monitoring.message_format import status_text
    from news.engine import NewsProvider
    news=ctx.get('calendar_status') or NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)
    return status_text(ctx,now,news,ctx.get('horizons'),decision)
def idea_text(i,tag,config):
    from monitoring.message_format import idea_text as render
    return render(i,tag,config)
def recap_levels(store,now,simulation=False):
    """Completed-session references need bar provenance, not a live closing quote."""
    session=market_session(now);day=now.astimezone(ET).date()
    close=datetime.combine(day,datetime.min.time(),ET)+timedelta(minutes=session['close_minute'])
    if now<close:return 'UNAVAILABLE — session not complete'
    for key,feed in [('stream_bars:SPY','SIP'),('research_stream_bars:SPY:iex','IEX')]:
        rows=store.get(key,[])
        if not rows:continue
        try:
            bars=normalize(rows,now=now,simulation=simulation)
            today=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==day and market_session(datetime.fromtimestamp(b['timestamp'],timezone.utc))['active']]
            if len(today)<31 or today[0]['timestamp']!=close.timestamp()-(session['close_minute']-570)*60 or today[-1]['timestamp']!=close.timestamp()-60:continue
            if any(b['timestamp']-a['timestamp']!=60 for a,b in zip(today,today[1:])):continue
            f=multi_timeframe(rows,[],now,simulation=simulation)['1m']
            fmt=lambda value:'%.2f'%value if finite(value) else 'UNAVAILABLE'
            return 'Completed-session references ('+('SIMULATED' if simulation else feed)+', not live): support '+fmt(f.get('support'))+' / resistance '+fmt(f.get('resistance'))+'; session low/high '+fmt(min(b['low'] for b in today))+'/'+fmt(max(b['high'] for b in today))
        except (ValueError,KeyError,TypeError,IndexError):continue
    return 'UNAVAILABLE — complete contiguous current-session bars missing'
def preopen_text(store,news,now,config,report=None):
    from monitoring.owner_messages import premarket_text
    r=report or store.get('premarket_report:'+now.astimezone(ET).date().isoformat()) or {}
    return premarket_text(r,news,now)

def scheduled_preopen(store,news,now,config,simulation=False):
    """Validate against the post-fetch clock; never reserve a late morning slot."""
    from monitoring.day_schedule import due
    day=now.astimezone(ET).date().isoformat();effective=now
    if not config.get('notifications',{}).get('categories',{}).get('morning',True):return None
    if ('PREOPEN',day) not in due(now,config):return None
    report=store.get('premarket_report:'+day)
    if not report and not simulation:
        # Preparation runs in a bounded background job, never blocks this slot.
        report=store.get('premarket_prepared:'+day) or {}
        effective=datetime.now(timezone.utc)
        try:
            if not 0<=(effective-stamp(report['generated_at'])).total_seconds()<=600:report={}
        except (KeyError,ValueError,TypeError):report={}
        effective=datetime.now(timezone.utc)
    elif not simulation:effective=datetime.now(timezone.utc)
    if ('PREOPEN',day) not in due(effective,config):return None
    report=dict({'quality':'UNAVAILABLE','reason':'prepared premarket evidence unavailable'},**(report or {}))
    report['message_version']='spy-preopen-compact-v1'
    if not simulation:
        from news.market_outlook import build as outlook_build
        report['market_outlook']=outlook_build(store,effective,premarket=report)
    message=preopen_text(store,news,effective,config,report)
    report['message']=message;store.put('premarket_report:'+day,report)
    return message
def permit(store,tracker,i,config,now,preview=False):
    from core.research_pause import advance
    c=settings(config);day=now.astimezone(ET).date().isoformat()
    state=store.get('idea-control:'+day) or {'alerts':0,'last':{},'cooloff_until':None,'loss_checkpoint':None}
    rows=tracker.positions()
    pause,paused,warnings=advance(store.get('research-pause:v2'),rows,now,c['cooloff_losses'],c['cooloff_minutes'])
    if not preview:store.put('research-pause:v2',pause)
    state['cooloff_until']=(pause.get('episode') or {}).get('end');state['loss_checkpoint']=(pause.get('episode') or {}).get('id')
    tag=evidence([r for r in rows if r['setup_type']==i['setup_type'] and bool(r.get('early'))==bool(i.get('early'))]);blocked=None
    if state['cooloff_until'] and now<stamp(state['cooloff_until']):blocked='COOL_OFF'
    if tag['evidence_tag']=='NEGATIVE' and i['setup_type'] not in config.get('negative_setup_overrides',[]):blocked='NEGATIVE_EVIDENCE';warnings.append('Evidence NEGATIVE — '+i['setup_type']+' alerts suppressed; still tracked silently. /alerts setup '+i['setup_type']+' on to override deliberately.')
    if state['alerts']>=c['idea_runaway_limit']:blocked='RUNAWAY_BREAKER';warnings.append('DATA WARNING — runaway safety breaker paused ideas for this ET day.')
    if c['idea_daily_cap'] is not None and state['alerts']>=c['idea_daily_cap']:blocked='DAILY_CAP'
    last=state['last'].get(i['direction'])
    if not blocked and last and (now-stamp(last['at'])).total_seconds()<c['idea_cooldown_minutes']*60 and last['setup']==i['setup_type'] and abs(last['trigger']-i['trigger'])<=.5*i['atr']:blocked='DIRECTION_COOLDOWN'
    if not blocked and not preview:state['alerts']+=1;state['last'][i['direction']]={'at':now.isoformat(),'setup':i['setup_type'],'trigger':i['trigger']}
    if not preview:store.put('idea-control:'+day,state)
    return blocked,tag,warnings
def tick(store,news,config,now,publish,root=ROOT,tracker=None,simulation=False):
    if not config.get('idea_engine_enabled',False):return []
    if simulation and tracker is None:raise ValueError('SIMULATION_MEMORY_TRACKER_REQUIRED')
    owned=tracker is None;tracker=tracker or IdeaTracker(Path(root)/'runtime/ideas.sqlite');ctx=context(store,now,simulation)
    if not simulation and getattr(store,'path',None) is not None:now=datetime.now(timezone.utc)
    ctx['calendar_status']=news;events=[]
    def emit(event):
        from core.directional_research import view,record
        if event.get('alert_type')=='TREND_LINE':
            r=view(ctx,now)
            for h in ('H60','H120','SESSION'):record(store,event['id']+':'+h,now,r,h)
        elif event.get('alert_type')=='PREOPEN':
            report=store.get('premarket_report:'+now.astimezone(ET).date().isoformat()) or {}
            session=market_session(now.astimezone(ET).replace(hour=10,minute=0))
            end=now.astimezone(ET).replace(hour=session['close_minute']//60,minute=session['close_minute']%60,second=0,microsecond=0)
            bias={'BULLISH':'UP','BEARISH':'DOWN'}.get(report.get('bias'),'ABSTAIN')
            r={'provider':'IEX' if report.get('quality')=='IEX_RESEARCH_ONLY' else 'PUBLIC_DELAY_UNVERIFIED','as_of':report.get('as_of_bar'),'outlooks':{'PREMARKET':{'bias':bias,'target_at':end.isoformat(),'invalidation':(report.get('levels') or {}).get('low' if bias=='UP' else 'high')}}}
            record(store,event['id'],now,r,'PREMARKET',premarket=True)
        publish(event);events.append(event)
    def send(key,text,type_,silent=False,buttons=None,parent=None):
        if store.get(key):return
        store.put(key,{'reserved_at':now.isoformat()});e={'id':key,'kind':'RESEARCH','audience':'SHARED' if config.get('signals',{}).get('shared',False) else 'PRIVATE','tenant':'owner','text':text,'alert_type':type_,'expires_at':(now+timedelta(minutes=10)).isoformat(),'disable_notification':silent}
        if type_ in ('SPY_IDEA','IDEA_UPDATE'):e['presentation_version']='owner-compact-v1'
        if buttons:e['reply_markup']=buttons
        if parent:e['parent_event_id']=parent
        emit(e)
    try:
        stale_key='v5-stale:'+now.astimezone(ET).date().isoformat()
        if not ctx['reason'] and store.get(stale_key):store.put(stale_key,False)
        # Only same-feed bars can mark these separate underlying records.
        if True:
            bar_context=ctx.get('bar_research') or {}
            observation_rows=bar_context.get('rows',[]) if not bar_context.get('reason') else ctx['rows'] if not ctx['reason'] else []
            observation_feed=bar_context.get('feed_quality') if not bar_context.get('reason') else ctx['feed_quality']
            for p,condition in tracker.observe(observation_rows,now,news,observation_feed):
                if p['status'] not in ('OPEN','PENDING'):store.put('paper_terminal:'+p['signal_id'],{'at':now.isoformat(),'reason':condition})
                if p.get('alerted') and config.get('notifications',{}).get('categories',{}).get('idea_updates',True):
                    from monitoring.message_format import update_text
                    send('v5-update-'+p['signal_id']+'-'+condition,update_text(p,condition),'IDEA_UPDATE',parent=p.get('idea_event_id') or 'v5-idea-'+p['signal_id']+'-'+p['strategy_version'])
        if not simulation:
            # Separate comparison population, no broadcasts or inferred option P&L.
            from core.research_horizons import candidates as horizon_candidates
            with_tracker=IdeaTracker(Path(root)/'runtime/horizon_ideas.sqlite')
            try:
                with_tracker.observe(observation_rows,now,news,observation_feed)
                comparisons=[]
                if not ctx['reason'] and market_session(now)['active'] and news.get('quality')=='DATA_OK' and news.get('risk') in ('NORMAL','MODERATE'):
                    comparisons=horizon_candidates(bar_context,ctx['quote'],now,config)
                    for comparison in comparisons:with_tracker.register(comparison,ctx['quote'],now,False)
                store.put('horizon_research',{'at':now.isoformat(),'variants':ctx['horizons'],'candidate_count':len(comparisons),'population':'HORIZON_COMPARISON_UNDERLYING_ONLY','alerts_enabled':False,'option_performance':'UNAVAILABLE','validated':False})
            finally:with_tracker.close()
        if not simulation and store.get('published-comparison-minute')!=now.replace(second=0,microsecond=0).isoformat():
            from strategies.published_baselines import compare_context
            store.put('published_baselines',{'at':now.isoformat(),**compare_context(ctx.get('bar_research') or {},now,store.get('corporate_action_history'))})
            store.put('published-comparison-minute',now.replace(second=0,microsecond=0).isoformat())
        if not simulation:
            from core.rejection_trace import measure,persist
            traces=measure(ctx,news,config,now);persist(Path(root)/'runtime/observability.sqlite',traces,now)
            store.put('v6-latest-setup-traces',traces)
        from core.directional_research import resolve
        minute_id=now.replace(second=0,microsecond=0).isoformat()
        if store.get('directional-resolve-minute')!=minute_id:
            resolve(store,(ctx.get('bar_research') or {}).get('bars',[]),now,quote=ctx.get('quote'))
            store.put('directional-resolve-minute',minute_id)
        ideas,reason=candidates(ctx,news,config,now,simulation)
        from options.trade_plan import mismatch
        if not simulation and mismatch([store.get('quote:SPY') or {},store.get('research_quote:SPY:iex') or {}],config,now):ideas=[];reason='feed mismatch'
        for i in ideas:
            if any(x['signal_id']==i['signal_id'] for x in tracker.positions()):continue
            category_on=config.get('notifications',{}).get('categories',{}).get('ideas',True)
            blocked,tag,warnings=permit(store,tracker,i,config,now,preview=not category_on)
            for w in warnings:send('v5-warning-'+now.astimezone(ET).date().isoformat()+'-'+('negative-'+i['setup_type'] if 'NEGATIVE' in w else 'cooloff-'+str((store.get('idea-control:'+now.astimezone(ET).date().isoformat()) or {}).get('loss_checkpoint','preview')) if 'Research entries paused' in w else 'runaway'),w,'IDEA_WARNING')
            alerted=not blocked and config.get('notifications',{}).get('categories',{}).get('ideas',True)
            i['alert_blocker']=blocked or (None if category_on else 'ALERTS_DISABLED')
            i.update(trigger_level=i['trigger'],reference_midpoint=ctx['quote']['payload']['mid'],modeled_entry_fill=ctx['quote']['payload']['ask' if i['direction']=='CALL' else 'bid']+(1 if i['direction']=='CALL' else -1)*.01,actual_reported_fill=None,idea_event_id='v5-idea-'+i['signal_id']+'-'+i['strategy_version'])
            if alerted:
                try:
                    from options.contract_selector import select
                    from options.trade_plan import build as plan_build
                    contracts=(store.get('chain') or {}).get('payload',{}).get('contracts',{})
                    selection=store.get('selection') or {}
                    if not selection.get('best_contract') or selection['best_contract'].get('type')!=('C' if i['direction']=='CALL' else 'P') or not option_quote_valid(selection['best_contract'].get('quote',{}),now):selection=select(contracts,i['spy_price'],i['direction'],now,min_dte=config.get('min_dte',1),max_premium=None if config.get('premium_cap_mode')=='warn' else config['options_risk']['max_trade_premium_usd'])
                    best=selection.get('best_contract')
                    greek_age=(now-stamp(best['greeks_timestamp'])).total_seconds() if best and best.get('greeks_timestamp') else None
                    if best and best.get('type')==('C' if i['direction']=='CALL' else 'P') and option_quote_valid(best.get('quote',{}),now) and greek_age is not None and 0<=greek_age<=60 and selection.get('chain_sanity_reasons')==[]:
                        i['option_contract']=best;i['option_plan']=plan_build(i,now,config,news);i['option_verification']='FRESH_QUOTE_GREEKS_CHAIN_SANITY_PASSED'
                except (ValueError,KeyError,TypeError):pass
            tracker.register(i,ctx['quote'],now,alerted)
            if alerted:
                store.put('v5-latest-idea',i)
                store.event('paper-candidate-'+i['signal_id']+'-'+i['strategy_version'],'paper_candidate',{**i,'paper_eligible':True,'underlying_entry_range':[i['entry'],i['do_not_chase']],'max_holding_minutes':60})
                buttons={'inline_keyboard':[[{'text':'📊 Chart','callback_data':'aegis:chart:'+i['signal_id']},{'text':'🚫 Skip','callback_data':'aegis:skip:'+i['signal_id']},{'text':'More ▸','callback_data':'aegis:more:'+i['signal_id']}]]}
                if i.get('option_contract'):buttons['inline_keyboard'].append([{'text':'✅ I bought','callback_data':'aegis:log:'+i['signal_id']}])
                send('v5-idea-'+i['signal_id']+'-'+i['strategy_version'],idea_text(i,tag,config),'SPY_IDEA',buttons=buttons)
                # Confirmation is already in the initial watch; no redundant entry update.
        from monitoring.day_schedule import dispatch
        def compose(kind):
            if kind=='PREOPEN':
                return scheduled_preopen(store,news,now,config,simulation)
            if kind=='RECAP':
                from monitoring.owner_messages import recap_text
                return recap_text(tracker.positions(),now,recap_levels(store,now,simulation))
            if not config.get('notifications',{}).get('categories',{}).get('trend_lines',True):return None
            key='v5-stale:'+now.astimezone(ET).date().isoformat()
            if ctx['reason']:
                store.put(key,True)
            elif store.get(key):store.put(key,False)
            active=store.get('v5-latest-idea');active=active if active and stamp(active['signal_expiry'])>now and not store.get('paper_terminal:'+active['signal_id']) else None
            if not simulation:
                from monitoring.trend_evidence import record
                slot=now.astimezone(ET).date().isoformat()+'-'+str((now.astimezone(ET).hour*60+now.astimezone(ET).minute)//15*15)
                record(Path(root)/'runtime/observability.sqlite','v5-trend-'+slot,now,ctx,news)
            episode=(store.get('research-pause:v2') or {}).get('episode') or {}
            entry_reason='research pause active until '+stamp(episode['end']).astimezone(ET).strftime('%H:%M ET') if episode.get('end') and now<stamp(episode['end']) else 'NO TRADE — '+reason if reason else None
            return trend_line(ctx,now,config,active,entry_reason)
        dispatch(store,now,config,compose,emit)
        store.put('v5-idea-health',{'at':now.isoformat(),'reason':reason or ctx['reason'],'feed_quality':ctx['feed_quality'],'candidates':len(ideas),'live_signal_ready':False})
        return events
    finally:
        if owned:tracker.close()
