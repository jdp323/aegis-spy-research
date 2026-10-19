"""Read-only market research, isolated position reviews and durable alert outbox."""

import json,time,hashlib,signal,os,tempfile

from datetime import datetime,timezone,timedelta

from core.storage import ROOT,Store,iso

from core.sessions import market_session

from data.providers import AlpacaProvider,ProviderRouter,PublicProvider

from data.models import stamp,Quality

from features.indicators import multi_timeframe

from features.market_regime import classify

from options.contract_selector import select

from options.ledger import Ledger

from monitoring.position_monitor import review

from news.engine import NewsProvider

from risk.options_policy import check

from core.signals import build

from backtesting.paper_engine import PaperEngine

def read_config():

    c=json.loads((ROOT/'config/upgrade.json').read_text())

    return validate_config(c)

def validate_config(c):

    if c.get('symbols')!=['SPY'] or c.get('order_execution_enabled') or c.get('live_signal_enabled'):raise ValueError('UNSUPPORTED_UNVALIDATED_CONFIGURATION')

    for key in ('price_poll_seconds','high_volatility_seconds','option_poll_seconds','chain_refresh_seconds','bars_refresh_seconds','daily_refresh_seconds','analysis_seconds','closed_poll_seconds'):

        if type(c.get(key)) is not int or c[key]<5:raise ValueError('UNSAFE_CADENCE')

    if not 1<=c['max_contract_subscriptions']<=30 or not 0<=c['min_dte']<=30 or c['actionable_threshold']!=75:raise ValueError('UNVALIDATED_POLICY_CHANGE')

    from monitoring.research_alerts import settings

    settings(c)

    from monitoring.premarket_brief import settings as premarket_settings

    premarket_settings(c)

    from risk.options_policy import parse_limits

    parse_limits(c['options_risk'])

    if type(c.get('options_risk_live_confirmed',False)) is not bool:raise ValueError('INVALID_LIVE_RISK_CONFIRMATION')

    if type(c.get('allow_unvalidated_paper_trading',False)) is not bool:raise ValueError('INVALID_PAPER_FLAG')

    if type(c.get('signal_expiry_seconds',600)) is not int or not 60<=c.get('signal_expiry_seconds',600)<=3600:raise ValueError('INVALID_SIGNAL_EXPIRY')

    if type(c.get('paper_daily_message_cap',8)) is not int or not 1<=c.get('paper_daily_message_cap',8)<=50:raise ValueError('INVALID_PAPER_CAP')

    if type(c.get('signals',{}).get('shared',False)) is not bool:raise ValueError('INVALID_PAPER_SHARING')

    p=c.get('proxy_paper',{})

    if p and (p.get('mode')!='UNDERLYING_PROXY_ONLY' or type(p.get('enabled')) is not bool or p.get('quantity')!=1 or p.get('max_open_positions')!=1 or not 0<=p.get('slippage_per_share',-1)<=1 or not 1<=p.get('max_holding_minutes',0)<=60 or not 0<p.get('max_risk_per_share_usd',0)<=5):raise ValueError('INVALID_PROXY_POLICY')

    from ops.heartbeat import validate_url

    validate_url(c.get('heartbeat_url',''))

    from news.engine import source_valid

    extras=c.get('calendar_official_extra_sources',[])

    if not isinstance(extras,list) or len(extras)>8 or any(not source_valid(url) for url in extras):raise ValueError('INVALID_OFFICIAL_CALENDAR_SOURCES')

    overrides=c.get('calendar_event_overrides',{})

    if not isinstance(overrides,dict):raise ValueError('INVALID_CALENDAR_OVERRIDES')

    for event_id,values in overrides.items():

        if not isinstance(event_id,str) or len(event_id)!=24 or not isinstance(values,dict) or any(k not in ('blackout_before_minutes','blackout_after_minutes') or type(v) is not int or not 0<=v<=240 for k,v in values.items()):raise ValueError('INVALID_CALENDAR_OVERRIDES')

    from core.simple_config import validate_new

    validate_new(c)
    from core.idea_config import settings as idea_settings
    idea_settings(c)

    return c

def fresh(q,now=None):

    if not q:return {'quality':'DATA_INCOMPLETE','payload':{}}

    q=dict(q);now=now or datetime.now(timezone.utc)

    try:

        age=(now-stamp(q['source_timestamp'])).total_seconds();q['freshness_seconds']=age

        if age < -q.get('accepted_future_skew_seconds',0):q['quality']='DATA_INVALID'

        elif age>15 and q['quality']=='DATA_OK':q['quality']='DATA_STALE'

    except Exception:q['quality']='DATA_INCOMPLETE'

    return q

def books():

    paths=[('owner',ROOT/'options/reported.sqlite')]

    try:members=json.loads((ROOT/'monitoring/access.json').read_text()).get('members',{})

    except FileNotFoundError:members={}

    paths += [(k,ROOT/'monitoring/users'/k/'reported.sqlite') for k in members if len(k)==24 and all(x in '0123456789abcdef' for x in k)]

    result={}

    for tenant,path in paths:

        if path.exists():

            ledger=Ledger(path)

            try:result[tenant]=[p for p in ledger.positions() if p['quantity']>0]

            finally:ledger.close()

    return result

def enqueue(store,id,text,audience='SHARED',tenant=None,kind='INFO',**metadata):

    if kind not in ('INFO','RESEARCH'):raise ValueError('UNVALIDATED_ALERT_KIND')

    event={'id':id,'kind':kind,'audience':audience,'expires_at':(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),'text':text}

    if tenant:event['tenant']=tenant

    for key in ('alert_type','signal_id','strategy_version','reply_markup','disable_notification','expires_at','parent_event_id'):

        if key in metadata:event[key]=metadata[key]

    out=ROOT/'monitoring/outbox';out.mkdir(exist_ok=True);target=out/(id+'.json')

    pending=None

    try:

        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=out,suffix='.pending',delete=False) as f:json.dump(event,f);pending=f.name

        # Link publishes a complete file exclusively; dispatch never observes partial JSON.

        os.link(pending,target)

        store.audit('queued-'+id,'alert_queued','worker',{'id':id,'audience':audience,'tenant':tenant})

    except FileExistsError:pass

    finally:

        if pending:os.unlink(pending)

def position_monitoring_incident(store,position,underlying,option_quote,now,tenant,publish):
    """Private monitoring incidents bypass research caps and never infer closure."""
    from core.signals import quote_valid,option_quote_valid
    from monitoring.message_format import position_review_text
    contract=position['contract'];key='position-monitor:'+hashlib.sha256((tenant+'|'+contract).encode()).hexdigest()[:32]
    old=store.get(key) or {};reasons=[]
    if not quote_valid(underlying or {},now):reasons.append('UNDERLYING_PRICE_UNAVAILABLE')
    if not option_quote_valid(option_quote or {},now):reasons.append('OPTION_PRICING_UNAVAILABLE')
    try:
        gap=(now-stamp(old['last_review_at'])).total_seconds()
        if gap<0 or gap>30:reasons.append('REVIEW_GAP_OR_CLOCK_JUMP')
    except (KeyError,ValueError,TypeError):pass
    value={**old,'last_review_at':now.isoformat()}
    if reasons and not old.get('open'):
        ident='position-monitor-'+hashlib.sha256((key+'|'+now.isoformat()).encode()).hexdigest()[:32]
        value.update(open=True,id=ident,started_at=now.isoformat(),reasons=reasons)
        store.put(key,value) # Durable reservation before publish; no uncertain resend.
        condition='Monitoring limited: '+', '.join(reasons)+'. No exit or closure inferred.'
        text=position_review_text(position,condition,{},underlying,option_quote,now)
        publish(store,ident,text,'PRIVATE',tenant,kind='RESEARCH',alert_type='POSITION_MONITORING_WARNING')
        return 'WARNING'
    if not reasons and old.get('open'):
        value.update(open=False,recovered_at=now.isoformat())
        store.put(key,value)
        text=position_review_text(position,'Fresh underlying and verified option marks resumed. Strategy and position state are separate; no exit inferred.',{},underlying,option_quote,now)
        publish(store,old['id']+'-recovered',text,'PRIVATE',tenant,kind='RESEARCH',alert_type='POSITION_MONITORING_RECOVERY')
        return 'RECOVERY'
    store.put(key,value)
    return 'UNCHANGED'

def reconcile_monitoring_holdings(store,reported_books,now):
    """Reset incident identity only when the private reported book removes a holding.

    This records a reported-book change, never a broker exit/expiry inference.
    """
    current={'position-monitor:'+hashlib.sha256((tenant+'|'+p['contract']).encode()).hexdigest()[:32]
             for tenant,positions in reported_books.items() for p in positions if p.get('quantity',0)>0}
    old=set(store.get('position-monitor-current-holdings',[]) or [])
    for key in old-current:
        state=store.get(key) or {}
        if state:store.put(key,{**state,'open':False,'last_review_at':None,'ended_at':now.isoformat(),'end_basis':'NO_CURRENT_REPORTED_HOLDING_NOT_BROKER_VERIFIED'})
    store.put('position-monitor-current-holdings',sorted(current))

class Watchdog:

    def __init__(self,store):self.store=store

    def check(self,session,now=None):

        now=now or datetime.now(timezone.utc);key='watchdog:'+session['date'];state=self.store.get(key,{})

        if not session['active']:return False

        if not state:state={'started':now.isoformat(),'warned':False}

        since=state['started']

        # IEX is a separate research feed, but valid arrivals still mean data is

        # arriving. Never let this suppress SIP/OPRA readiness rejections.

        for feed in ('sip','iex'):

            last=self.store.get('last_market:'+feed)

            if not last:continue

            try:

                source=stamp(last['source_timestamp'])

                if stamp(since)<source<=now:since=source.isoformat()

            except (KeyError,ValueError,TypeError):continue

        stale=(now-stamp(since)).total_seconds()>=600;warn=stale and not state['warned']

        if not stale and state['warned']:state['warned']=False

        if warn:state['warned']=True

        self.store.put(key,state);return warn

class Engine:

    def __init__(self,store=None,provider=None,background=None):

        self.root=ROOT;self.background=(store is None and provider is None) if background is None else background
        self.store=store or Store();self.provider=provider or AlpacaProvider();self.option_provider=None;self.router=ProviderRouter(self.provider);self.due={};self.last_phase=None;self.stop=False;self.watchdog=Watchdog(self.store)
        from core.background_jobs import Jobs,Phases
        self.jobs=Jobs();self.phases=Phases(self.root)

        from data.research_inputs import ResearchInputs

        self.research_inputs=ResearchInputs()

        from news.market_outlook import RSSProvider

        from news.reddit import RedditProvider

        self.market_news=RSSProvider();self.reddit=RedditProvider()
        from core.v6_service import Reliability
        self.reliability=Reliability(self.store,self.provider,root=self.root,background=self.background)

    def collect(self,key,work,apply,budget=15):
        """Production network work cannot block scheduled analysis or reviews."""
        if self.background:return self.jobs.submit(key,work,apply,budget)
        apply(work());return True

    def market_result(self,key,value):
        # Background REST cannot replace a newer stream quote. Failed responses
        # remain visible through job/provider health without erasing last-good
        # provenance. The preserved quote still ages normally at every gate.
        current=self.store.get(key) or {}
        try:
            if current.get('source_timestamp') and (not value.get('source_timestamp') or stamp(value['source_timestamp'])<stamp(current['source_timestamp'])):return
        except (ValueError,TypeError):return
        if value.get('quality') in ('DATA_INVALID','DATA_INCOMPLETE','FEED_DISCONNECTED','FEED_NOT_CONFIGURED') and current.get('source_timestamp'):return
        self.store.put(key,value)

    def maintenance_calendar(self,c,now):
        from news.calendar_updater import maintenance
        if not self.background:return maintenance(self.store,c,now,root=self.root)
        separate=Store(self.store.path)
        try:return maintenance(separate,c,now,root=self.root)
        finally:separate.close()

    def close(self):
        self.jobs.close(timeout=1);self.reliability.close();self.phases._publish({'state':'STOPPED'});self.store.close()

    def tick(self):

        start=time.monotonic();self.phases.start('cycle_inputs');now=datetime.now(timezone.utc);session=market_session(now);c=read_config();digest=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
        completed=self.jobs.drain()
        self.store.put('worker_jobs',{'completed':completed,'current':self.jobs.health()})

        self.phases.start('reliability')
        self.reliability.tick(now,enqueue);now=datetime.now(timezone.utc);session=market_session(now)
        self.phases.start('idea_schedule')
        if c.get('idea_engine_enabled',False):
            from core.idea_service import tick as idea_tick
            def idea_publish(event):
                enqueue(self.store,event['id'],event['text'],event['audience'],event['tenant'],kind='RESEARCH',alert_type=event['alert_type'],disable_notification=event['disable_notification'],expires_at=event['expires_at'],**({key:event[key] for key in ('reply_markup','parent_event_id') if event.get(key)}))
            self.store.put('v5_skew_budget',c.get('max_future_skew_seconds',2))
            idea_tick(self.store,NewsProvider(ROOT/'config/news_calendar.json').snapshot(now),c,now,idea_publish,root=ROOT)

        if session['state']!=self.last_phase:self.due.clear();self.last_phase=session['state']

        if self.store.get('config_hash')!=digest:self.store.audit('config-'+str(time.time_ns()),'configuration_change','local-file',{'sha256':digest,'execution':False});self.store.put('config_hash',digest)

        self.phases.start('clock_and_subscriptions')
        from data.clock_health import tick as clock_tick

        if self.background:
            from data.clock_health import measure
            clock_state=self.store.get('ntp_clock') or {}
            try:clock_due=not 0<=(now-stamp(clock_state['at'])).total_seconds()<3600
            except (KeyError,ValueError,TypeError):clock_due=True
            if clock_due:self.collect('clock_measure',measure,lambda result:clock_tick(self.store,c,datetime.now(timezone.utc),enqueue,probe=lambda:result),5)
        else:clock_tick(self.store,c,now,enqueue)

        from monitoring.simple_notifications import enabled

        if c.get('option_data_provider')=='questrade':

            from data.questrade import QuestradeProvider

            if self.option_provider is None:self.option_provider=QuestradeProvider(config=c.get('questrade',{}))

            self.option_provider.config=c.get('questrade',{})
            self.collect('option_keep_alive',self.option_provider.keep_alive,lambda value:self.store.put('questrade_health',value),15)
            qh=self.store.get('questrade_health') or self.option_provider.health()

            hours=qh.get('hours_until_policy_expiry')

            if enabled(c,'system') and (qh.get('status') in ('QUESTRADE_TOKEN_EXPIRED','QUESTRADE_REFRESH_UNCERTAIN') or hours is not None and hours<=c.get('questrade',{}).get('token_warning_hours',24)):

                enqueue(self.store,'questrade-warning-'+session['date'],'DATA WARNING — '+qh['status']+'. Generate a new refresh token in Questrade API Hub and enter it only in Configure Market Data.cmd. Do not share the token.','PRIVATE','owner',kind='RESEARCH')

        else:self.option_provider=self.provider

        allbooks=books();reconcile_monitoring_holdings(self.store,allbooks,now);paper=PaperEngine(ROOT/'runtime/paper.sqlite')

        try:paper_positions=[p for p in paper.positions() if p['status']=='OPEN']

        finally:paper.store.close()

        baseline_engine=PaperEngine(ROOT/'runtime/paper.sqlite',kind='paper_baseline')

        try:baseline_positions=[p for p in baseline_engine.positions() if p['status']=='OPEN']

        finally:baseline_engine.store.close()

        symbols=sorted({p['contract'] for positions in allbooks.values() for p in positions}|{p['contract'] for p in paper_positions+baseline_positions});self.store.put('subscriptions',symbols[:c['max_contract_subscriptions']])

        self.phases.start('network_scheduling')
        active=session['active'];health=self.provider.health();configured=health['status']!='FEED_NOT_CONFIGURED';clock=time.monotonic()

        def due(k,seconds):

            if clock>=self.due.get(k,0):self.due[k]=clock+seconds;return True

            return False

        if active and self.option_provider and self.option_provider.health()['status'] not in ('QUESTRADE_NOT_CONFIGURED','FEED_NOT_CONFIGURED') and due('option_keep_poll',c.get('questrade',{}).get('active_quote_seconds',10)):

            for symbol in symbols[:c['max_contract_subscriptions']]:self.collect('option_quote:'+symbol.lower(),lambda symbol=symbol:self.option_provider.get_option_quote(symbol).view(),lambda value,symbol=symbol:self.market_result('quote:'+symbol,value),15)

        if active and self.option_provider and self.option_provider.health()['status'] not in ('QUESTRADE_NOT_CONFIGURED','FEED_NOT_CONFIGURED') and due('option_chain_independent',c['chain_refresh_seconds']):self.collect('option_chain',lambda:self.option_provider.get_option_chain().view(max_age=300),lambda value:self.store.put('chain',value),30)

        if configured and active:

            interval=c['high_volatility_seconds'] if self.store.get('regime',{}).get('regime')=='HIGH_VOLATILITY' else c['price_poll_seconds']

            if due('quote',interval):

                q=fresh(self.store.get('quote:SPY'),now)

                if q['quality']!='DATA_OK':
                    def quote_result(value):
                        result,attempts=value;self.market_result('quote:SPY',result);self.store.put('provider_attempts',attempts)
                    self.collect('underlying_quote',lambda:self.router.request('get_underlying_quote','SPY'),quote_result,15)

                if q['quality']=='DATA_OK':self.store.put('last_market:sip',{'source_timestamp':q['source_timestamp'],'received_timestamp':q['received_timestamp']})

            if due('options',min(interval,c['option_poll_seconds'])):

                for symbol in symbols[:30]:

                    if fresh(self.store.get('quote:'+symbol))['quality']!='DATA_OK':self.collect('option_quote:'+symbol.lower(),lambda symbol=symbol:self.option_provider.get_option_quote(symbol).view(),lambda value,symbol=symbol:self.market_result('quote:'+symbol,value),15)

            for name,tf,seconds in [('bars','1Min',c['bars_refresh_seconds']),('daily','1Day',c['daily_refresh_seconds'])]:

                if due(name,seconds):self.collect('provider_'+name,lambda tf=tf:self.provider.get_bars('SPY',tf).view(max_age=172800 if tf=='1Day' else 120),lambda value,name=name:self.store.put(name,value),30)

            if due('chain',c['chain_refresh_seconds']):

                self.collect('option_chain',lambda:self.option_provider.get_option_chain().view(max_age=300),lambda value:self.store.put('chain',value),30)

        if due('news_headlines',300 if active else 1800):

            self.collect('news_headlines',lambda now=now:self.research_inputs.headlines(now),lambda value:self.store.put('news_headlines',value),15)

        if due('market_news',600 if active or session['state']=='PREMARKET' else 1800):

            from news.market_outlook import SOURCES

            for key in SOURCES:self.collect('rss:'+key,lambda key=key:self.market_news.collect(key),lambda value,key=key:self.store.put('market_news:'+key,value),15)

        if due('reddit_sentiment',3600 if active or session['state']=='PREMARKET' else 7200):

            self.collect('reddit_sentiment',self.reddit.collect,lambda value:self.store.put('reddit_sentiment',value),15)

        self.phases.start('news_interpretation')
        from news.market_outlook import build as outlook_build

        self.store.put('market_outlook',outlook_build(self.store))

        from monitoring.simple_notifications import source_pushes

        source_pushes(self.store,c,now,enqueue)

        # One bounded sample per completed session; no repeat storm on restart,

        # weekends or access rejection. Files preserve both success and failure.

        if not active and due('history_sample',1800) and configured:

            from backtesting.history_sampler import window,collect

            w=window(now)

            if w:

                key='history_sampler:'+w[0].date().isoformat()

                if not self.store.get(key):

                    self.store.put(key,{'state':'ATTEMPT_RESERVED','at':now.isoformat()})

                    def sample_result(sample,key=key):self.store.put(key,sample);self.store.put('history_sample',sample)
                    self.collect('history_sample',lambda now=now:collect(self.research_inputs,now,root=self.root),sample_result,60)

        if due('calendar',86400):self.collect('calendar',lambda c=c,now=now:self.maintenance_calendar(c,now),lambda value:None,60)

        # Network collection can span seconds or a session boundary. Evaluate

        # newly received quotes against the current clock, not cycle start.

        self.phases.start('legacy_analysis')
        now=datetime.now(timezone.utc);session=market_session(now);active=session['active']

        underlying=fresh(self.store.get('quote:SPY'),now)

        news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)

        if c.get('idea_engine_enabled',False):idea_tick(self.store,news,c,now,idea_publish,root=ROOT)

        from monitoring.simple_notifications import calendar_warning

        calendar_warning(self.store,news,now,enqueue,c)

        if news.get('coverage_complete') and news.get('coverage_through'):

            remaining=(stamp(news['coverage_through'])-now).total_seconds()

            if 0<=remaining<=14*86400:

                warning='calendar-coverage-'+hashlib.sha256(news['coverage_through'].encode()).hexdigest()[:24]

                enqueue(self.store,warning,'DATA WARNING — Official calendar coverage ends '+stamp(news['coverage_through']).astimezone(__import__('core.sessions',fromlist=['ET']).ET).strftime('%Y-%m-%d %H:%M ET')+'. Refresh is required.','PRIVATE','owner',kind='RESEARCH')

        if due('analysis',c['analysis_seconds'] if active else c['closed_poll_seconds']):

            minute=self.store.get('bars',{}).get('payload',{}).get('bars',[]);stream=self.store.get('stream_bars:SPY',[])

            merged={r['t']:r for r in minute};merged.update({r['t']:r for r in stream});minute=sorted(merged.values(),key=lambda r:r['t'])

            try:features=multi_timeframe(minute,self.store.get('daily',{}).get('payload',{}).get('bars',[]),now)

            except Exception:features={};self.store.audit('bad-bars-'+str(time.time_ns()),'data_rejection','worker',{'reason':'INVALID_BARS'})

            regime=classify(features.get('5m',{}),underlying['quality']);self.store.put('features',features);self.store.put('regime',regime)

            px=underlying.get('payload',{}).get('mid');direction='CALL' if regime['regime'] in ('BULL','STRONG_BULL') else 'PUT'

            chain=self.store.get('chain',{}).get('payload',{}).get('contracts',{})

            opening=features.get('opening_range');distance=abs(px-opening['high' if direction=='CALL' else 'low']) if px and opening else None

            selection=select(chain,px,direction,now,min_dte=c['min_dte'],max_premium=c['options_risk'].get('max_trade_premium_usd'),target_distance=2*distance if distance else None,stop_distance=distance,atr=features.get('5m',{}).get('atr14'),volatility_state=regime['regime'],intraday_range=features.get('5m',{}).get('range')) if px else {'best_contract':None,'alternatives':[],'rejected':[]}

            from ops.premium_cap import observe as cap_observe

            cap_observe(self.store,selection,c,now)

            self.store.put('selection',selection);best=selection.get('best_contract');premium=(best['ask']+float(c['paper_slippage_per_share']))*100+float(c['paper_fee_per_contract']) if best else None

            risk=check(c['options_risk'],allbooks.get('owner',[]),premium=premium,now=now,live_confirmed=c.get('options_risk_live_confirmed',False));self.store.put('risk',risk)

            paper=PaperEngine(ROOT/'runtime/paper.sqlite')

            try:state=paper.risk_state(now)

            finally:paper.store.close()

            paper_risk=check({**c['options_risk'],**{k:state[k] for k in ('daily_loss_usd','consecutive_losses','daily_reconciled_date')}},state['positions'],premium=premium,now=now,mode='paper')

            s=build(features,regime,selection,underlying,news,session,paper_risk,now,{**c,"clock_health":self.store.get("ntp_clock")})

            from backtesting.forward_validation import ForwardValidation

            forward=ForwardValidation(ROOT/'runtime/paper.sqlite')

            try:forward.record(s);forward.observe(minute,now,'SIP')

            finally:forward.close()

            self.store.put('latest_evaluation',s.dict())

            if self.store.event(s.signal_id,'signal',s.dict()):self.store.audit('signal-'+s.signal_id,'signal_generation','worker',{'signal_id':s.signal_id,'rejected':s.hard_rejection,'reasons':s.rejection_reasons})

            if s.paper_eligible and s.option_contract:

                paper=PaperEngine(ROOT/'runtime/paper.sqlite')

                try:opened=paper.open(s,s.option_contract['quote'],slippage=c['paper_slippage_per_share'],fee=c['paper_fee_per_contract'],now=now)

                except ValueError:opened=None

                finally:paper.store.close()

                from monitoring.paper_alerts import candidate_alert

                if not c.get('idea_engine_enabled',False):candidate_alert(self.store,s.dict(),c,enqueue,now)

                from backtesting.option_baseline import open_baseline

                opposite=select(chain,px,'PUT' if s.direction=='CALL' else 'CALL',now,min_dte=c['min_dte'],max_premium=c['options_risk']['max_trade_premium_usd']).get('best_contract')

                baseline=open_baseline(ROOT/'runtime/paper.sqlite',s.dict(),opposite,c,news,now) if opened is not None else None

                self.store.put('option_baseline_health',{'at':now.isoformat(),'state':baseline if isinstance(baseline,str) else 'RECORDED_REAL_QUOTES'})

        self.phases.start('reported_position_reviews')
        now=datetime.now(timezone.utc);session=market_session(now)

        underlying=fresh(self.store.get('quote:SPY'),now)

        news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)

        for tenant,positions in allbooks.items():

            reviewed=[]

            for p in positions:

                plan=self.store.get('plan:'+tenant+':'+p['contract'],{})

                from core.signals import quote_valid,option_quote_valid

                from monitoring.paper_alerts import reserve

                uq=underlying if quote_valid(underlying,now) else fresh(self.store.get('research_quote:SPY:iex'),now)

                oq=fresh(self.store.get('quote:'+p['contract']),now)

                position_monitoring_incident(self.store,p,uq,oq,now,tenant,enqueue)

                if plan.get('stop_bar_minutes'):

                    bar=(self.store.get('features') or {}).get('5m',{});age=now.timestamp()-bar.get('timestamp',0)

                    plan['invalidation_bar_close']=bar.get('close') if 300<=age<=420 else None

                r=review(p,oq if option_quote_valid(oq,now) else None,uq if quote_valid(uq,now) else None,plan,news,self.store.get('regime',{}).get('regime'),now);reviewed.append(r)

                for alert in r['alerts']:

                    # Once per condition/day/contract; no guessed prices, private to record owner.

                    aid='position-'+hashlib.sha256((tenant+p['contract']+alert+session['date']).encode()).hexdigest()[:32]

                    if alert in ('ABNORMAL_DATA',) or str(alert).startswith('MONITORING_UNAVAILABLE'):continue
                    # Actual reported holdings are private to their own tenant.
                    # They are not research ideas and do not consume its cap.
                    if not self.store.get('private-review:'+aid):
                        from monitoring.message_format import position_review_text
                        self.store.put('private-review:'+aid,{'at':now.isoformat()})
                        text=position_review_text(p,alert,plan,uq,oq,now)
                        enqueue(self.store,aid,text,'PRIVATE',tenant,kind='RESEARCH',alert_type='EXIT_REVIEW')

            self.store.put('positions:'+tenant,reviewed)

        self.phases.start('option_paper_reviews')
        for p in paper_positions:

            q=fresh(self.store.get('quote:'+p['contract']),now);s=p['signal'];plan={k:s.get(k) for k in ('invalidation','t1','t2','signal_expiry')};plan['max_hold_until']=(s.get('option_plan') or {}).get('max_hold_until') or (stamp(p['opened_at'])+timedelta(minutes=s['max_holding_minutes'])).isoformat()

            for key in ('t1','t2','stop'):plan['option_'+key]=(s.get('option_plan') or {}).get(key+'_bid')

            r=review({'contract':p['contract'],'quantity':p['quantity'],'cost_usd':p['entry_cost']},q,underlying,plan,news,self.store.get('regime',{}).get('regime'),now)

            exits=[a for a in r['alerts'] if a in ('T2_REACHED','UNDERLYING_INVALIDATION','MAX_HOLD_TIME_REACHED','MAJOR_NEWS_RISK','ZERO_DTE_FINAL_HOUR_REVIEW','OPTION_STOP_CONDITION','EXPIRATION_APPROACHING')]

            paper=PaperEngine(ROOT/'runtime/paper.sqlite')

            try:

                from backtesting.premium_accuracy import Accuracy

                accuracy=Accuracy(ROOT/'runtime/paper.sqlite')

                try:accuracy.observe(p,underlying,q,now)

                finally:accuracy.close()

                marked=paper.mark(p['signal_id'],q,exit_reason=exits[0] if exits else None,slippage=c['paper_slippage_per_share'],fee=c['paper_fee_per_contract'],now=now)

                from monitoring.paper_alerts import emit,HEADER,FOOTER

                for condition in ([marked['exit_reason']] if marked.get('status')=='CLOSED' else [a for a in r['alerts'] if a=='T1_REACHED']):emit(self.store,s,'PAPER_UPDATE',c,enqueue,now,HEADER+'\nPAPER_UPDATE — '+condition+'\nOPTIONS_REAL_QUOTES\nSPY '+str(underlying.get('payload',{}).get('mid') if quote_valid(underlying,now) else 'UNAVAILABLE')+' / option bid '+str(q.get('payload',{}).get('bid') if option_quote_valid(q,now) else 'UNAVAILABLE')+'\n'+FOOTER,condition)

            except ValueError:pass

            finally:paper.store.close()

        for p in baseline_positions:

            q=fresh(self.store.get('quote:'+p['contract']),now);s=p['signal'];op=s.get('option_plan') or {};plan={k:s.get(k) for k in ('invalidation','t1','t2')};plan['max_hold_until']=op.get('max_hold_until')

            for k in ('t1','t2','stop'):plan['option_'+k]=op.get(k+'_bid')

            r=review({'contract':p['contract'],'quantity':p['quantity'],'cost_usd':p['entry_cost']},q,underlying,plan,news,now=now)

            exits=[x for x in r['alerts'] if x in ('T2_REACHED','OPTION_STOP_CONDITION','UNDERLYING_INVALIDATION','MAX_HOLD_TIME_REACHED','MAJOR_NEWS_RISK','EXPIRATION_APPROACHING')]

            engine=PaperEngine(ROOT/'runtime/paper.sqlite',kind='paper_baseline')

            try:engine.mark(p['signal_id'],q,exit_reason=exits[0] if exits else None,slippage=c['paper_slippage_per_share'],fee=c['paper_fee_per_contract'],now=now)

            except ValueError:pass

            finally:engine.store.close()

        self.phases.start('underlying_paper_reviews')
        from core.paper_service import tick as paper_tick

        now=datetime.now(timezone.utc);session=market_session(now)

        news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)

        proxy_signal,changes=paper_tick(self.store,news,c,now,root=ROOT)

        from monitoring.paper_alerts import candidate_alert,position_alerts,lifecycle

        if not c.get('idea_engine_enabled',False):candidate_alert(self.store,proxy_signal.dict(),c,enqueue,now);position_alerts(self.store,changes,c,enqueue,now)

        if not c.get('idea_engine_enabled',False):lifecycle(self.store,fresh(self.store.get('research_quote:SPY:iex'),now),c,enqueue,now)

        self.store.put('news',news);self.store.put('provider',self.provider.health());self.store.put('session',session)

        self.phases.start('capture_and_session_checks')
        from data.session_recorder import tick as record_tick

        record_tick(self.store,now,root=ROOT)

        from ops.live_verify import scheduled as verify_scheduled

        verify_scheduled(self.store,datetime.now(timezone.utc),root=ROOT)

        from ops.heartbeat import tick as heartbeat_tick

        heartbeat_tick(self.store,c,session,now)

        from monitoring.research_alerts import update,load

        public_snapshot=load()

        from monitoring.premarket_brief import update as update_premarket

        if not c.get('idea_engine_enabled',False):update_premarket(self.store,news,c,enqueue,now)

        if enabled(c,'periodic') or enabled(c,'changes') or enabled(c,'extended'):update(self.store,public_snapshot,session,c,enqueue,now)
        else:self.store.put('research_notification_health',{'state':'DISABLED_SIMPLE_PROFILE','at':now.isoformat(),'enabled_categories':[]})

        self.phases.start('diagnostic_studies')
        from research.forward_study import tick,rows_from_disk

        tick(self.store,public_snapshot,rows_from_disk(),session,now)

        from research.ratio_study import tick as ratio_tick

        from data.trend_spy import load as ratio_load

        ratio_tick(self.store,ratio_load(),now)

        watch_now=datetime.now(timezone.utc);watch_session=market_session(watch_now)

        if enabled(c,'system') and self.watchdog.check(watch_session,watch_now):
            incident=self.store.get('v6-outage:'+watch_session['date']) or {}
            if incident.get('id'):
                escalation=incident['id']+'-escalated'
                if not self.store.get(escalation):
                    self.store.put(escalation,{'at':watch_now.isoformat()})
                    enqueue(self.store,escalation,'DATA WARNING — The same data outage remains unresolved after 10 minutes. Cause: '+incident.get('reason','UNKNOWN')+'. Monitoring is limited; no fresh-data entry is issued.','PRIVATE','owner',kind='RESEARCH',alert_type='DATA_WARNING')

        self.phases.finish()
        self.store.put('worker_health',{'pid':os.getpid(),'at':iso(),'state':'RUNNING','cycle_seconds':time.monotonic()-start,'cycle_budget_seconds':10,'cycle_deadline_missed':time.monotonic()-start>10,'data_configured':configured,'phases':self.phases.summary(),'database':getattr(self.store,'metrics',{}),'background_jobs':self.jobs.health()})

        return {'session':session['state'],'provider':health['status'],'action':'NO TRADE'}

    def run(self):

        def stop(*args):self.stop=True

        signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)

        while not self.stop and not (ROOT/'runtime/shutdown.request').exists():

            try:self.tick()

            except Exception as e:
                from core.background_jobs import error_fields
                self.phases.finish(e)
                try:self.store.put('worker_health',{'at':iso(),'state':'FAILED_CYCLE',**error_fields(e),'phases':self.phases.summary(),'database':getattr(self.store,'metrics',{})})
                except Exception:pass

            for _ in range(10):

                if self.stop or (ROOT/'runtime/shutdown.request').exists():break

                time.sleep(1)

        try:self.store.put('worker_health',{'at':iso(),'state':'STOPPED'})
        finally:self.close()

def snapshot():

    s=Store()

    try:

        result={k:s.get(k) for k in ('features','regime','selection','risk','news','provider','worker_health','session','research_notification_health')};result['session']=market_session();result['underlying']=fresh(s.get('quote:SPY'));result['signals']=s.events('signal',30);result['positions']=s.get('positions:owner',[]);result['streams']={k:s.get('stream:'+k) for k in ('sip','opra')};from core.verdict import short

        evaluation=dict(s.get('proxy_evaluation') or {})

        from core.signals import quote_valid

        now=datetime.now(timezone.utc);q=s.get('research_quote:SPY:iex') if evaluation.get('feed_quality')=='IEX' else s.get('quote:SPY')

        current_news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)

        if not evaluation.get('timestamp') or (now-stamp(evaluation['timestamp'])).total_seconds()>read_config()['analysis_seconds'] or not quote_valid(q or {},now):evaluation.update(paper_eligible=False,paper_blockers=['PROXY_FRESH_FEED_AND_31_BAR_TAIL_REQUIRED'])

        elif current_news['quality']!='DATA_OK' or current_news['risk']=='HIGH':evaluation.update(paper_eligible=False,paper_blockers=['NEWS_UNAVAILABLE_OR_BLACKOUT'])

        result['today_verdict']=short(evaluation,datetime.now(timezone.utc),trend=('UP' if (result.get('regime') or {}).get('regime') in ('BULL','STRONG_BULL') else 'DOWN' if (result.get('regime') or {}).get('regime') in ('BEAR','STRONG_BEAR') else 'MIXED'))

        upcoming=[e for e in current_news.get('events',[]) if stamp(e['time_utc'])>=now]

        upcoming.sort(key=lambda e:e['time_utc'])

        event=upcoming[0] if upcoming and current_news['quality']=='DATA_OK' else None

        result['today_next_event']=(event['name']+' — '+(stamp(event['time_utc']).astimezone(__import__('core.sessions',fromlist=['ET']).ET).strftime('%m-%d')+' all-day ET' if event.get('time_source')=='DATE_ONLY' else stamp(event['time_utc']).astimezone(__import__('core.sessions',fromlist=['ET']).ET).strftime('%m-%d %H:%M ET'))+' — '+event['risk']) if event else 'UNAVAILABLE; optional event categories may be unknown'

        result['action']='NO TRADE';result['live_signal_enabled']=False;result['generated_at']=iso()

        result['streams']['iex']=s.get('stream:iex')

        result['clock_health']={feed:s.get('stream_clock:'+feed) for feed in ('iex','sip','opra')}

        result['questrade_health']=s.get('questrade_health');result['ntp_clock']=s.get('ntp_clock');result['skew_budget_seconds']=read_config().get('max_future_skew_seconds',2.0)

        result['proxy_paper']={'summary':s.get('proxy_paper_summary'),'evaluation':s.get('proxy_evaluation'),'positions':s.get('proxy_paper_positions',[])}

        result['research_underlying']=fresh(s.get('research_quote:SPY:iex'))

        from research.live_trend import evaluate

        result['live_trend']=evaluate(s)

        for k in ('worker_health',):

            if result[k] and (datetime.now(timezone.utc)-stamp(result[k]['at'])).total_seconds()>120:result[k]['state']='STALE_HEARTBEAT'

        result['system']={'worker':result['worker_health'],'database':'OPENED_OK'}

        for key,file in [('services','services.json'),('telegram','telegram_health.json'),('dispatcher','dispatcher_health.json')]:

            try:

                health=json.loads((ROOT/'runtime'/file).read_text());health['fresh_heartbeat']=(datetime.now(timezone.utc)-stamp(health['at'])).total_seconds()<120;result['system'][key]=health

            except Exception:result['system'][key]={'state':'UNAVAILABLE'}

        for q in result['positions']:

            if not q.get('quote_timestamp') or (datetime.now(timezone.utc)-stamp(q['quote_timestamp'])).total_seconds()>15:q['estimated_pnl_usd']=None;q['estimated_liquidation_usd']=None

        for x in result['signals']:x['display_status']='EXPIRED' if x['status']!='REJECTED' and x.get('signal_expiry') and stamp(x['signal_expiry'])<datetime.now(timezone.utc) else x['status']

        from core.spy_research import current

        result['public_research']=current()

        from monitoring.research_alerts import observe

        from research.closing_estimate import estimate

        now=datetime.now(timezone.utc)

        result['closing_estimate']=estimate(observe(result['public_research'],result['session'],now),result['session'],now=now)

        from research.forward_study import summary

        result['learning']=summary(s)

        from research.ratio_study import summary as ratio_summary

        result['ratio_learning']=ratio_summary(s)

        result['data_availability']={'underlying':result['underlying']['quality'],'options':s.get('chain',{}).get('quality','FEED_NOT_CONFIGURED'),'historical':s.get('bars',{}).get('quality','DATA_INCOMPLETE'),'news':(result['news'] or {}).get('quality','DATA_INCOMPLETE')}

        from data.research_inputs import fresh_headlines

        from core.readiness import evaluate as readiness

        from backtesting.option_dataset import inspect

        result['news_headlines']=fresh_headlines(s.get('news_headlines'))

        result['history_sample']=s.get('history_sample')

        result['news']=NewsProvider(ROOT/'config/news_calendar.json').snapshot()

        result['options_readiness']=readiness(result,config=read_config(),dataset=inspect())

        result['paper_collection']={'enabled':read_config().get('allow_unvalidated_paper_trading',False),'validated':False,'live_signal_ready':False,'recorder':s.get('recorder_health'),'calendar_updater':s.get('calendar_updater'),'external_heartbeat':s.get('external_heartbeat'),'live_verification':s.get('live_verify_deployment')}

        result['premarket_health']=s.get('premarket_health')

        result['premarket_report']=s.get('premarket_report:'+result['session']['date'])

        from news.market_outlook import build as outlook_build

        result['market_outlook']=outlook_build(s)

        return result

    finally:s.close()

if __name__=='__main__':

    import sys

    engine=Engine()

    if '--once' in sys.argv:
        try:print(json.dumps(engine.tick()))
        finally:engine.close()

    else:engine.run()

