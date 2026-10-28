"""Current, actionable engineering blockers; never grants signal permission."""
def evaluate(data,config=None,dataset=None):
    config=config or {};dataset=dataset or {};blocks=[]
    def add(code,status,detail,resolution):
        blocks.append({'code':code,'status':status,'detail':detail,'resolution':resolution})
    live=data.get('live_trend') or {}
    if live.get('status')!='LIVE_TREND':
        add('UNDERLYING','WAITING',live.get('reason','No verified live trend'),
            'Observe a quote at most 5 seconds old and 31 contiguous completed current-session minute bars; IEX remains single-exchange research.')
    availability=data.get('data_availability') or {}
    if availability.get('options')!='DATA_OK':
        add('OPTION_DATA','EXTERNAL_ACCESS',availability.get('options','UNAVAILABLE'),
            'Verify entitled OPRA quotes and full contract liquidity/IV/Greeks from the current or another authorized provider; indicative quotes cannot substitute.')
    selection=data.get('selection') or {}
    if not selection.get('best_contract'):
        add('CONTRACT','WAITING','No eligible contract selected',
            'Validate exact terms, source timestamps, bid/ask, volume, open interest and Greeks before contract selection.')
    news=data.get('news') or {};headlines=data.get('news_headlines') or {}
    if news.get('quality')!='DATA_OK' or news.get('risk') not in ('NORMAL','MODERATE'):
        add('NEWS','LOCAL_AND_EXTERNAL',
            ('Headlines available; ' if headlines.get('quality')=='DATA_OK' else 'Headlines unavailable; ')+(news.get('reason') or 'calendar unavailable or event blackout'),
            'Combine fresh provider headlines with independently verified scheduled-event coverage; do not assume a quiet news query means no event risk.')
    risk=data.get('risk') or {}
    if not risk.get('ready'):
        add('RISK','CONFIGURATION_REQUIRED',', '.join(risk.get('reasons') or ['USD option caps/reconciliation missing']),
            'Set explicit USD premium/exposure/daily-loss/streak caps and reconcile dated loss metrics. Do not convert the old CAD budget without a verified funding basis.')
    if not dataset.get('structural_valid'):
        sample=data.get('history_sample') or {}
        count=sum(r.get('bars',0) for r in sample.get('history',[]))
        add('HISTORICAL_QUOTES','DATA_REQUIRED',
            ('Historical trade-bar samples collected: '+str(count)+'. ' if count else '')+'Executable historical option quote dataset missing',
            'Collect/verify licensed bid-ask history with costs and chronological coverage. Trade bars alone cannot model executable fills.')
    add('STRATEGY','EVIDENCE_REQUIRED','Options strategy has no reviewed promotion evidence',
        'Run chronological cost-aware backtests and prospective paper observations; preserve failures and review evidence before any promotion.')
    from core.signals import option_quote_valid,quote_valid
    from datetime import datetime,timezone
    now=datetime.now(timezone.utc);q=data.get('underlying') or {};best=selection.get('best_contract')
    gates={'DATA_READY':live.get('status')=='LIVE_TREND' and live.get('feed')=='sip' and quote_valid(q,now),'OPTIONS_READY':bool(best and option_quote_valid(best.get('quote',{}),now)),'NEWS_READY':news.get('quality')=='DATA_OK' and news.get('risk') in ('NORMAL','MODERATE'),'RISK_READY':bool(config.get('options_risk_live_confirmed',False) and risk.get('mode')=='live' and risk.get('live_ready')),'STRATEGY_READY':False,'LIVE_SIGNAL_READY':False}
    return {'schema_version':2,'mode':'RESEARCH_ONLY','live_ready':False,'gates':gates,'blockers':blocks,
            'order_execution_enabled':False,'config_live_requested':bool(config.get('live_signal_enabled'))}

def text_for(state):
    lines=['SPY OPTIONS READINESS','ACTION: NO TRADE — live option recommendations are not enabled.']
    for block in state['blockers']:
        lines.extend(['',block['code']+' — '+block['status'],block['detail'],'Next: '+block['resolution']])
    lines.append('\n/trend = refreshed underlying analysis | /news = research/headline status | /feed = freshness')
    return '\n'.join(lines)[:3400]
