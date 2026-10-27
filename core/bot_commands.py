"""Authenticated caller passes tenant; never accepts filesystem paths or shell instructions."""
import json,sys,re,math
from datetime import datetime,timezone,timedelta
from core.storage import Store,ROOT
from core.upgrade_service import snapshot,books
from options.ledger import contract
def et_text(value):
    from data.models import stamp
    from core.sessions import ET
    try:return stamp(value).astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET')
    except (ValueError,TypeError):return 'UNAVAILABLE'
def execute(data):
    tenant=data.get('tenant') or 'owner'
    if tenant!='owner' and not re.fullmatch('[a-f0-9]{24}',tenant):raise ValueError('Invalid tenant')
    s=Store()
    try:
        command=data['command']
        if command=='details':
            from core.idea_service import context
            from news.engine import NewsProvider
            from monitoring.message_format import diagnostics_text
            now=datetime.now(timezone.utc);ctx=context(s,now)
            from core.market_view import build,details
            from core.primary_plan import current
            from core.readonly_state import idea_rows
            try:rows=idea_rows(ROOT/'runtime/ideas.sqlite')
            except (OSError,__import__('sqlite3').Error):rows=[]
            news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)
            text=details(build(ctx,news,now,plan=current(s,rows,now)))+'\n\n'+diagnostics_text(ctx,now,news)
            try:
                shadow=json.loads((ROOT/'runtime/shadow_health.json').read_text());text+='\nExperimental Kronos shadow: '+shadow.get('state','UNAVAILABLE')+'; no entry control'
            except (OSError,ValueError):text+='\nExperimental Kronos shadow: unavailable; no entry control'
            pause=s.get('research-pause:v2') or {};episode=pause.get('episode') or {}
            return text[:3100]+'\nResearch pause policy '+str(pause.get('version','not yet evaluated'))+'; start '+et_text(episode.get('start'))+'; end '+et_text(episode.get('end'))+'; reason '+str(episode.get('reason','no recorded pause'))
        if command=='score':
            from backtesting.idea_tracker import IdeaTracker
            from monitoring.message_format import score_summary_text
            p=IdeaTracker(ROOT/'runtime/ideas.sqlite')
            from monitoring.research_populations import horizon_summary,horizon_text
            try:return score_summary_text(p.summary(datetime.now(timezone.utc)))+'\n\n'+horizon_text(horizon_summary(ROOT/'runtime/horizon_ideas.sqlite'))
            finally:p.close()
        if command=='trend' and data.get('text','')!='details':
            from core.upgrade_service import read_config
            c=read_config()
            if c.get('idea_engine_enabled',False):
                from core.idea_service import context,candidates,trend_line
                now=datetime.now(timezone.utc);ctx=context(s,now)
                from news.engine import NewsProvider
                from core.sessions import market_session
                if not market_session(now)['active']:
                    from core.verdict import short
                    return short({},now)
                ideas,reason=candidates(ctx,NewsProvider(ROOT/'config/news_calendar.json').snapshot(now),c,now)
                from backtesting.idea_tracker import IdeaTracker
                from core.idea_service import permit
                tracker=IdeaTracker(ROOT/'runtime/ideas.sqlite')
                try:
                    if ideas:
                        blocked,_,_=permit(s,tracker,ideas[0],c,now,preview=True)
                        if blocked:ideas=[];reason=blocked.lower().replace('_',' ')
                finally:tracker.close()
                from core.primary_plan import current as primary_current
                tracker=IdeaTracker(ROOT/'runtime/ideas.sqlite')
                try:active=primary_current(s,tracker.positions(),now)
                finally:tracker.close()
                return trend_line(ctx,now,c,active,'NO TRADE — '+(reason or 'setup confirmed; option eligibility separate') if ideas else 'NO TRADE — '+(reason or 'no confirmed setup'))
        if command=='fill':
            from core.fill_flow import execute as fill_execute
            return fill_execute(s,data.get('text',''),tenant,data['id'])
        if command=='alerts':
            from monitoring.simple_notifications import alerts
            from monitoring.sharing import display
            from core.upgrade_service import read_config
            return alerts(data.get('text',''),tenant,store=s)+'\n'+display(read_config())
        if command=='why' and data.get('text','')!='details':
            from core.upgrade_service import read_config
            c=read_config()
            if c.get('idea_engine_enabled',False):
                from core.idea_service import context,candidates,permit
                from news.engine import NewsProvider
                from backtesting.idea_tracker import IdeaTracker
                now=datetime.now(timezone.utc);ctx=context(s,now);news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)
                ideas,reason=candidates(ctx,news,c,now)
                lines=['SPY IDEA CHECKS · '+et_text(now.isoformat()),'Fresh price/bar inputs: '+('PASS' if not ctx['reason'] else ctx['reason']),'Official calendar: '+news['quality']+' / '+news['risk'],'Confirmed setups: '+str(len(ideas))]
                t=IdeaTracker(ROOT/'runtime/ideas.sqlite')
                try:
                    for i in ideas[:4]:
                        blocked,tag,_=permit(s,t,i,c,now,preview=True)
                        lines.append(i['setup_type']+': '+(blocked or 'eligible unvalidated research')+'; '+tag['evidence_tag']+'; '+'; '.join(i['explanation']))
                finally:t.close()
                traces=s.get('v6-latest-setup-traces') or []
                frames={k:ctx.get('features',{}).get(k,{}).get('trend') not in (None,'UNAVAILABLE') for k in ('1m','5m','15m','30m','1h','daily')}
                lines+=['Frames: '+' · '.join(k+(' ok' if v else ' unavailable') for k,v in frames.items()),'Confirmed-empty continuity slots: '+str(ctx.get('synthetic_continuity_minutes',0))+' (excluded from indicators/volume/fills).','Opening range: '+ctx.get('opening_range_status','UNAVAILABLE')]
                if traces:lines.append('Trace as-of '+et_text(traces[0]['at'])+' · '+traces[0]['engine_version'])
                from monitoring.message_format import measured
                for tr in traces[:2]:lines.append(tr['setup']+' '+tr['direction']+': '+(tr.get('blocker') or '; '.join(k+' '+v['state']+' [value '+measured(v.get('value'),140)+'; threshold '+measured(v.get('threshold'),85)+']' for k,v in tr['checks'].items())))
                for tr in traces[2:]:lines.append(tr['setup']+' '+tr['direction']+': '+(tr.get('blocker') or ', '.join(k for k,v in tr['checks'].items() if v['state']=='FAIL') or 'measured checks PASS'))
                reply='\n'.join(lines+['Decision reason: '+(reason or 'confirmation and alert controls shown above')])
                if len(reply)>3300:reply=reply[:3300]+'\nAbbreviated; full measured traces remain in the local observability database.'
                return reply+'\nLive signals and orders disabled.'
        if command in ('trend','why') and data.get('text','')!='details':
            from core.verdict import current,short,why
            from core.upgrade_service import read_config
            now=datetime.now(timezone.utc);evaluation,direction=current(s,read_config(),now)
            if command=='why':return why(evaluation)
            text=short(evaluation,now,trend=direction)
            if tenant=='owner' and evaluation.get('paper_eligible'):
                from monitoring.paper_alerts import HEADER,FOOTER
                from core.signals import option_quote_valid
                s.event('paper-candidate-'+evaluation['signal_id']+'-'+evaluation['strategy_version'],'paper_candidate',evaluation)
                buttons=[{'text':'📊 Chart','callback_data':'aegis:chart:'+evaluation['signal_id']},{'text':'🚫 Skip','callback_data':'aegis:skip:'+evaluation['signal_id']}]
                c=evaluation.get('option_contract')
                if c and option_quote_valid(c.get('quote',{}),now):buttons.append({'text':'✅ I bought','callback_data':'aegis:log:'+evaluation['signal_id']})
                return {'text':HEADER+'\n'+text+'\n'+FOOTER,'reply_markup':{'inline_keyboard':[buttons,[{'text':'More ▸','callback_data':'aegis:more:'+evaluation['signal_id']}]]}}
            return text
        if command=='trend':
            from research.basic_trend import on_demand_text
            from research.live_trend import evaluate,text_for as live_text
            now=datetime.now(timezone.utc);live=evaluate(s,now)
            s.put('trend_live_health',{'status':live['status'],'reason':live['reason'],'at':now.isoformat(),'max_quote_age_seconds':5})
            if live['status']=='LIVE_TREND':return live_text(live,now)
            historical=on_demand_text().replace('SPY TREND:', 'SPY HISTORICAL BAR TREND:',1)
            # A public fetch may take seconds. Re-read streaming quotes immediately
            # before constructing the reply, rather than print a pre-fetch age.
            now=datetime.now(timezone.utc);live=evaluate(s,now)
            s.put('trend_live_health',{'status':live['status'],'reason':live['reason'],'at':now.isoformat(),'max_quote_age_seconds':5})
            if live['status']=='LIVE_TREND':return live_text(live,now)
            return live_text(live,now)+'\n\nHISTORICAL CONTEXT (PUBLIC FIVE-MINUTE BARS)\n'+historical
        if command=='premarket':
            from monitoring.premarket_brief import command_text
            return command_text(s)
        if command in ('outlook','news'):
            from news.market_outlook import build,text_for
            return text_for(build(s),detail=command)
        if command=='sentiment':
            from news.reddit import text_for
            return text_for(s.get('reddit_sentiment'))
        if command=='forecast':
            from monitoring.research_alerts import observe,load
            from research.closing_estimate import estimate
            from core.sessions import market_session
            now=datetime.now(timezone.utc);session=market_session(now);f=estimate(observe(load(),session,now),session,now=now)
            if f['status']!='EXPERIMENTAL_SCENARIOS':return 'SPY CLOSING ESTIMATE\nNot established: '+f['reason']+'.\nNo closing price was invented. ACTION: NO TRADE.'
            return ('SPY CLOSING AREA — EXPERIMENTAL\nHistorical scenario range: $%.2f-$%.2f USD; midpoint $%.2f.\nHistorical sample: %d sessions.\nChronological tests: %d; median-model average error $%.2f vs no-change baseline $%.2f.\n'%(f['low'],f['high'],f['median'],f['historical_sessions'],f['chronological_test_sessions'],f['historical_mae_usd'],f['no_change_mae_usd'])+'As-of5m bar: '+f['as_of_bar']+'\nTarget: final regular5m bar, not official auction close.\n'+f['limitations']+'\nACTION: NO TRADE. No option entry or exit instruction.')
        if command=='learn':
            from research.ratio_study import summary as ratio_summary,text_for as ratio_text
            from research.forward_study import summary as earlier_summary
            earlier=earlier_summary(s)
            return ratio_text(ratio_summary(s))+'\nEarlier structure study retained: '+str(earlier['resolved'])+' completed, '+str(earlier['pending'])+' pending.\n/trend = indicator percentages | /news = detailed research'
        if command=='setup':
            from core.readiness import text_for
            return text_for(snapshot()['options_readiness'])
        if command=='research':
            from monitoring.research_alerts import load,observe,text_for
            from core.sessions import market_session
            now=datetime.now(timezone.utc);session=market_session(now)
            from research.basic_trend import saved_text
            from data.research_inputs import headline_status
            head=headline_status(s.get('news_headlines'))[:1400]
            research=text_for(observe(load(),session,now),session,now)
            prefix=saved_text(now)[:1200]+'\n\n'+head+'\n\nDETAILED RESEARCH:\n'
            return prefix+research[:max(0,3400-len(prefix))]
        if command=='health':
            from monitoring.message_format import health_text
            return health_text(snapshot(),datetime.now(timezone.utc))
        if command=='status':
            from monitoring.sharing import display
            from core.upgrade_service import read_config
            sharing=display(read_config())
            from core.idea_service import context
            from news.engine import NewsProvider
            from monitoring.message_format import status_text,plain
            now=datetime.now(timezone.utc);ctx=context(s,now);news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)
            worker=s.get('worker_health') or {};state=worker.get('state','UNAVAILABLE')
            try:
                if not 0<=(now-__import__('data.models',fromlist=['stamp']).stamp(worker['at'])).total_seconds()<=120:state='STALE_HEARTBEAT'
            except (KeyError,ValueError,TypeError):state='UNVERIFIED_HEARTBEAT'
            return ('AEGIS STATUS — '+sharing+'\n'+status_text(ctx,now,news)+'\nWorker: '+plain(state,40)+'\nAutomatic public research: silent every 15 minutes 09:45 to close−15; qualifying research alerts when eligible.\nMorning 09:15; recap close+15. Windows must remain awake/online.')
        if command=='plan':
            parts=data.get('text','').split()
            if len(parts)!=5:raise ValueError('Use /plan OCC_SYMBOL INVALIDATION T1 T2 MAX_HOLD_MINUTES (underlying SPY prices)')
            symbol=parts[0].upper();spec=contract(symbol);invalid,t1,t2=map(float,parts[1:4]);minutes=int(parts[4])
            if not all(math.isfinite(v) and v>0 for v in (invalid,t1,t2)) or not 1<=minutes<=1440:raise ValueError('Invalid price or holding time')
            if not (invalid<t1<t2 if spec['type']=='C' else invalid>t1>t2):raise ValueError('Targets must progress away from invalidation in the contract direction')
            if not any(p['contract']==symbol for p in books().get(tenant,[])):raise ValueError('Report your actual holding before setting its plan')
            from monitoring.position_rules import review_deadline
            now=datetime.now(timezone.utc);rule=review_deadline(now,spec['expiry'],minutes)
            if not rule['allowed']:return 'Private review plan not changed. '+rule['reason']+' Your reported fill and holding are retained; no order placed.'
            plan={'invalidation':invalid,'t1':t1,'t2':t2,'max_hold_until':rule['deadline'],'source':'USER_DEFINED','updated_at':now.isoformat(),'requested_hold_minutes':minutes,'session_cutoff':rule['session_cutoff'],'calendar_version':rule['calendar_version'],'holding_policy_version':rule['policy_version']}
            s.put('plan:'+tenant+':'+symbol,plan);s.audit(data['id'],'position_plan_change',tenant,{'contract':symbol,**plan});return 'Private review plan saved. Review deadline '+et_text(rule['deadline'])+(' (requested horizon shortened at verified session close minus five minutes).' if rule['shortened'] else '.')+' Prices refer to SPY, not the option premium. Reported holdings remain open until separately reported/reconciled; no guaranteed exit or broker order.'
        if command=='feed':
            from core.feed_health import text_for
            return text_for(snapshot())
        if command=='paper':
            from core.upgrade_service import read_config
            if tenant!='owner' and not read_config().get('signals',{}).get('shared',False):return 'PAPER / UNVALIDATED — paper evidence is owner-only; sharing is disabled. Your own reported positions remain private. No orders.'
            from backtesting.paper_engine import PaperEngine
            p=PaperEngine(ROOT/'runtime/paper.sqlite')
            try:positions=[x for x in p.positions() if not x.get('synthetic')]
            finally:p.store.close()
            from backtesting.proxy_engine import ProxyEngine
            proxy=ProxyEngine(ROOT/'runtime/paper.sqlite')
            try:summary=proxy.summary()
            finally:proxy.close()
            from backtesting.premium_accuracy import Accuracy
            accuracy=Accuracy(ROOT/'runtime/paper.sqlite')
            try:ar=accuracy.report()
            finally:accuracy.close()
            from backtesting.idea_tracker import IdeaTracker
            from monitoring.message_format import paper_summary_text
            ideas=IdeaTracker(ROOT/'runtime/ideas.sqlite')
            try:idea_summary=ideas.summary(datetime.now(timezone.utc))
            finally:ideas.close()
            diagnostics={}
            import sqlite3
            path=ROOT/'runtime/paper.sqlite'
            if path.exists():
                db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
                try:
                    present={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    for table,key in (('forward_evaluations','evaluations'),('forward_outcomes','outcomes')):
                        if table in present:diagnostics[key]=db.execute('SELECT count(*) FROM '+table).fetchone()[0]
                finally:db.close()
            from monitoring.research_populations import horizon_summary,horizon_text
            return paper_summary_text(idea_summary,positions,summary,ar,diagnostics)+'\n\n'+horizon_text(horizon_summary(ROOT/'runtime/horizon_ideas.sqlite'))
        if command=='signals':
            signals=s.events('signal',3)
            return 'RESEARCH SIGNALS — not actionable\n'+('\n\n'.join(et_text(x['timestamp'])+' '+x['direction']+' '+x['tier']+'\n'+', '.join(x['rejection_reasons']) for x in signals) or 'No research evaluations yet.')[:3300]
        return 'Research and private position reporting. Live signals are disabled. Use /feed for current readiness; /signals for research rejections; /paper for theoretical trades. /plan sets your own reported holding review conditions. Nothing places orders.'
    finally:s.close()
if __name__=='__main__':
    try:
        result=execute(json.load(sys.stdin));print(json.dumps(result,ensure_ascii=False) if isinstance(result,dict) else result)
    except (ValueError,KeyError,TypeError):print('Command not applied. Check /help and the required fields; no order placed.')
