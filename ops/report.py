"""Local paper-performance report. No synthetic/live-ledger mixing."""
import json,statistics
from decimal import Decimal
from pathlib import Path
from core.storage import ROOT,iso
from backtesting.paper_engine import PaperEngine
def option_paper_report(path=None,kind='paper'):
    engine=PaperEngine(path or ROOT/'runtime/paper.sqlite',kind=kind)
    try:rows=engine.positions()
    finally:engine.store.close()
    closed=[p for p in rows if p['status']=='CLOSED' and not p.get('synthetic')];closed.sort(key=lambda p:p['closed_at'])
    pnl=[float(p['pnl_usd']) for p in closed];wins=[v for v in pnl if v>0];losses=[v for v in pnl if v<0];peak=0;equity=0;drawdown=0
    for value in pnl:equity+=value;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
    def grouped():
        from backtesting.proxy_engine import critical_t
        import math
        dimensions={'horizon':lambda p:p.get('horizon','UNAVAILABLE'),'dte':lambda p:p.get('signal',{}).get('option_contract',{}).get('bucket','UNAVAILABLE'),'setup':lambda p:p.get('setup','UNAVAILABLE'),'delta_band':lambda p:'low' if abs(p.get('delta') or 0)<.35 else 'preferred' if abs(p.get('delta') or 0)<=.65 else 'high','regime':lambda p:p.get('regime','UNAVAILABLE'),'score_bucket':lambda p:str(int((p.get('score') or 0)//10)*10)}
        result={}
        for key,fn in dimensions.items():
            result[key]={}
            for label in sorted({fn(p) for p in closed}):
                xs=[float(p['pnl_usd']) for p in closed if fn(p)==label];n=len(xs);mean=statistics.mean(xs);margin=critical_t(n)*statistics.stdev(xs)/math.sqrt(n) if n>=2 else None
                result[key][label]={'n':n,'mean_usd':mean,'mean_95pct_ci':[mean-margin,mean+margin] if margin is not None else None}
        return result
    groups=grouped();h=groups.get('horizon',{});eligible={k:v for k,v in h.items() if v['n']>=20 and v['mean_95pct_ci'] is not None}
    comparison={'state':'DESCRIPTIVE_ONLY' if len(eligible)>=2 else 'INSUFFICIENT_EVIDENCE','eligible_groups':eligible,'note':'At least 20 closed trades per horizon; correlated samples and multiple comparisons remain. No automatic promotion.'}
    return {'breakdowns':groups,'horizon_comparison':comparison,'at':iso(),'matched_clock_random_direction_baseline':option_paper_report(path,'paper_baseline') if kind=='paper' else None,'mode':'THEORETICAL_ONLY_NOT_STRATEGY_VALIDATION','closed_trades':len(closed),'open_trades':sum(p['status']=='OPEN' and not p.get('synthetic') for p in rows),'excluded_synthetic':sum(bool(p.get('synthetic')) for p in rows),'net_pnl_usd':sum(pnl) if pnl else None,'win_rate':len(wins)/len(pnl) if pnl else None,'average_win':statistics.mean(wins) if wins else None,'average_loss':statistics.mean(losses) if losses else None,'profit_factor':sum(wins)/abs(sum(losses)) if losses else None,'expectancy_usd':statistics.mean(pnl) if pnl else None,'maximum_realized_drawdown_usd':drawdown if pnl else None,'average_holding_seconds':statistics.mean(p['holding_seconds'] for p in closed) if closed else None,'trades':closed}
def paper_report(path=None):
    from backtesting.proxy_engine import ProxyEngine
    report=option_paper_report(path);proxy=ProxyEngine(path or ROOT/'runtime/paper.sqlite')
    try:report['underlying_proxy_only']=proxy.summary()
    finally:proxy.close()
    report['option_statistics_exclude_proxy']=True;report['live_signal_ready']=False
    from backtesting.premium_accuracy import Accuracy
    accuracy=Accuracy(path or ROOT/'runtime/paper.sqlite')
    try:report['premium_estimate_accuracy']=accuracy.report()
    finally:accuracy.close()
    from backtesting.idea_tracker import IdeaTracker
    from datetime import datetime,timezone
    ideas=IdeaTracker((Path(path).parent if path else ROOT/'runtime')/'ideas.sqlite')
    try:report['underlying_ideas_separate']=ideas.summary(datetime.now(timezone.utc))
    finally:ideas.close()
    return report
if __name__=='__main__':
    value=paper_report();target=ROOT/'daily_reports/paper_performance.json';target.write_text(json.dumps(value,indent=2));(ROOT/'research/PREMIUM_ACCURACY.json').write_text(json.dumps(value['premium_estimate_accuracy'],indent=2));print('Saved',target)
