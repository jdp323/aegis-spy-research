"""Paper-only coordinator. No live flags, reported ledgers or brokerage methods."""
from pathlib import Path
from core.storage import ROOT
from core.signals import finalize
from backtesting.proxy_engine import ProxyEngine,candidate
def tick(store,news,config,now,root=None):
    root=Path(root or ROOT);engine=ProxyEngine(root/'runtime/paper.sqlite')
    try:
        s,q,rows=candidate(store,news,config,now);state=engine.risk_state(now);reasons=list(s.paper_blockers)
        if state['daily_loss_usd']>=config['options_risk']['max_daily_loss_usd']:reasons.append('PROXY_DAILY_LOSS_LIMIT')
        if state['consecutive_losses']>=config['options_risk']['max_consecutive_losses']:reasons.append('PROXY_LOSS_STREAK_LIMIT')
        if sum(p['status']=='OPEN' for p in engine.positions())>=config['proxy_paper']['max_open_positions']:reasons.append('PROXY_OPEN_POSITION_LIMIT')
        finalize(s,reasons,config);store.put('proxy_evaluation',s.dict());store.event('proxy-evaluation-'+s.signal_id+'-'+s.timestamp,'proxy_evaluation',s.dict())
        from backtesting.forward_validation import ForwardValidation
        forward=ForwardValidation(root/'runtime/paper.sqlite')
        try:forward.record(s);forward.observe(rows,now,s.feed_quality)
        finally:forward.close()
        changes=[]
        for feed,key in [('SIP','stream_bars:SPY'),('IEX','research_stream_bars:SPY:iex')]:changes+=engine.mark(store.get(key,[]) or [],news,now,feed_quality=feed)
        if s.paper_eligible:
            try:
                result=engine.open(s,q,config,now)
                if isinstance(result,dict):store.audit('proxy-entry-'+s.signal_id,'proxy_paper_entry','worker',{'signal_id':s.signal_id,'mode':s.paper_mode})
            except ValueError as e:store.put('proxy_routing_rejection',{'signal_id':s.signal_id,'reason':str(e),'at':now.isoformat()})
        summary=engine.summary();store.put('proxy_paper_summary',summary);store.put('proxy_paper_positions',engine.positions());store.put('proxy_paper_changes',changes)
        root=root/'daily_reports';root.mkdir(exist_ok=True)
        import json,os
        from ops.report import option_paper_report
        combined={'underlying_proxy_only':summary,'options_real_quotes':option_paper_report(root.parent/'runtime/paper.sqlite'),'live_signal_ready':False,'strategy_validated':False}
        tmp=root/'PAPER_PERFORMANCE.md.pending';tmp.write_text('# Paper evidence performance\n\nUNDERLYING_PROXY_ONLY is separate from options and reported holdings. NOT VALIDATED.\n\n```json\n'+json.dumps(combined,indent=2)+'\n```\n',encoding='utf-8');os.replace(tmp,root/'PAPER_PERFORMANCE.md')
        return s,changes
    finally:engine.close()
