"""Compact views of gated evaluations. An idea is never a live-ready signal."""
from datetime import datetime,timezone,timedelta
from core.sessions import ET,market_session
from core.signals import quote_valid,option_quote_valid
from data.models import stamp,finite

REASONS={
 'PROXY_FRESH_FEED_AND_31_BAR_TAIL_REQUIRED':'data is not fresh or the completed-minute history is incomplete',
 'NEWS_UNAVAILABLE_OR_BLACKOUT':'an event blackout is active or the calendar is unavailable',
 'OUTSIDE_PROXY_ENTRY_SESSION':'outside the trading window',
 'PROXY_LOSS_LIMIT':'paper loss limit reached',
 'PROXY_OPEN_POSITION_LIMIT':'a paper position is already open',
 'PROXY_CONFIRMATION_MISSING':'no clean setup with all confirmations yet',
 'PROXY_SETUP_INPUTS_UNAVAILABLE':'no clean directional setup yet',
 'PREMIUM_ABOVE_CAP':'contract premium exceeds the paper cap',
 'FEED_MISMATCH':'verified underlying feeds disagree',
 'SIMULATED_DATA_FORBIDDEN':'simulated inputs are forbidden outside the demo',
}
def next_open(now):
    for i in range(9):
        d=now.astimezone(ET).date()+timedelta(days=i)
        t=datetime.combine(d,datetime.min.time(),ET)+timedelta(hours=9,minutes=30)
        if t>now and market_session(t)['active']:return t
    return None
def direction_of(s):return 'UP' if s.get('direction')=='CALL' else 'DOWN' if s.get('direction')=='PUT' else 'MIXED'
def short(s,now=None,trend=None,session=None,simulation=False):
    now=now or datetime.now(timezone.utc);session=session or market_session(now)
    direction=trend or direction_of(s);alignment=s.get('multi_timeframe_alignment',{})
    aligned='BULL' if direction=='UP' else 'BEAR' if direction=='DOWN' else None
    votes=[alignment.get(k) for k in ('1m','5m','15m','30m','1h','daily')]
    count=sum(v==aligned for v in votes) if aligned else 0
    label=direction+(' — '+str(count)+' of 6 timeframes agree' if any(v in ('BULL','BEAR','NEUTRAL') for v in votes) else ' — timeframe agreement UNAVAILABLE')
    lines=['SPY · '+now.astimezone(ET).strftime('%H:%M ET'),'Trend: '+label]
    if not session['active']:
        nxt=next_open(now)
        return '\n'.join(lines+['DECISION: NO TRADE','Market closed — saved context only; no live verdict.','Next open: '+(nxt.strftime('%a %H:%M ET') if nxt else 'UNAVAILABLE'),'Next morning message: '+((nxt-timedelta(minutes=15)).strftime('%a %H:%M ET') if nxt else 'UNAVAILABLE'),'Data: '+s.get('feed_quality','UNAVAILABLE')])
    blocked=s.get('paper_blockers',[]);eligible=s.get('paper_eligible',False) and not blocked
    if s.get('feed_quality')=='SIMULATED' and not simulation:eligible=False;blocked=['SIMULATED_DATA_FORBIDDEN']
    if not s.get('signal_expiry') or stamp(s['signal_expiry'])<=now:eligible=False;blocked=blocked or ['SIGNAL_EXPIRED']
    if not eligible or s.get('direction') not in ('CALL','PUT'):
        reason=next((REASONS[x] for x in REASONS if x in blocked), 'no clean setup passes every hard gate')
        trigger=s.get('would_change_if') or 'fresh data and a completed setup passing all checks'
        return '\n'.join(lines+['DECISION: NO TRADE','Reason: '+reason,'Would change if: '+trigger,'Data: '+s.get('feed_quality','UNAVAILABLE')])
    lines+=['DECISION: BUY '+s['direction']+' idea ✅']
    plan=s.get('option_plan');contract=s.get('option_contract')
    verified=contract and option_quote_valid(contract.get('quote',{}),now)
    if simulation and contract and contract.get('quote',{}).get('feed_quality')=='SIMULATED':verified=True
    if verified and plan:
        lines += [f"Contract: {contract['symbol']} (quote {stamp(contract['quote']['source_timestamp']).astimezone(ET).strftime('%H:%M:%S ET')})",f"Buy: limit ≈ ${plan['limit']:.2f} (bid {contract['bid']:.2f} / ask {contract['ask']:.2f}; max ${plan['max_price']:.2f})",f"Sell: T1 est. ${plan['t1_bid']:.2f} / SPY {s['t1']:.2f}; T2 est. ${plan['t2_bid']:.2f} / SPY {s['t2']:.2f}",f"Stop: est. ${plan['stop_bid']:.2f} or SPY closes {'below' if s['direction']=='CALL' else 'above'} {s['invalidation']:.2f}", 'Hold: '+plan['hold_text'],f"Cost ≈ ${plan['cost']:.2f}; stop risk est. ${plan['loss_at_stop']:.2f} (fees included)"]
    else:
        lines += ['Enter: '+s.get('entry_condition','UNAVAILABLE'),f"Exit if SPY {'falls below' if s['direction']=='CALL' else 'rises above'}: {s['invalidation']:.2f}",f"Targets: {s['t1']:.2f} · {s['t2']:.2f}",'Option: UNAVAILABLE — approximate guideline: SPY '+s['direction'].lower()+'s, 2–7 DTE, |delta| 0.40–0.55.','Check broker bid/ask; this is not a live option quote.']
    lines += ['Idea expires: '+stamp(s['signal_expiry']).astimezone(ET).strftime('%H:%M ET'),'Data: '+('IEX only (one exchange)' if s.get('feed_quality')=='IEX' else s.get('feed_quality','UNAVAILABLE')),'Premium targets are estimates.' if verified and plan else 'SPY levels only; no option premium supplied.','Unvalidated research. You place orders yourself.']
    return '\n'.join(lines[:15])
def why(s):
    parts=s.get('score_components') or {}
    breakdown='\nScore components: '+', '.join(k+' '+str(v) for k,v in parts.items()) if parts else '\nScore components: UNAVAILABLE (proxy checks are separate).'
    return 'AEGIS — WHY\nSetup: '+s.get('setup_type','UNAVAILABLE')+'\nScore/tier: '+str(s.get('score'))+' / '+s.get('tier','NO TRADE')+breakdown+'\n'+('\n'.join('− '+r for r in s.get('paper_blockers',[])) or '+ Every paper gate passed.')+'\n'+'\n'.join('+ '+x for x in s.get('explanation',[]))+'\nLive signals remain disabled.'
def current(store,config,now=None):
    """Recompute fresh option and explicit proxy evaluations; never reuse an old verdict."""
    now=now or datetime.now(timezone.utc)
    from news.engine import NewsProvider
    from core.storage import ROOT
    from backtesting.proxy_engine import candidate,ProxyEngine
    from research.live_trend import evaluate
    news=NewsProvider(ROOT/'config/news_calendar.json').snapshot(now)
    s,q,_=candidate(store,news,config,now)
    # Runtime limits must constrain the displayed idea as well as paper entries.
    p=ProxyEngine(ROOT/'runtime/paper.sqlite')
    try:
        state=p.risk_state(now);limits=config['options_risk']
        if state['daily_loss_usd']>=limits['max_daily_loss_usd'] or state['consecutive_losses']>=limits['max_consecutive_losses']:s.paper_blockers.append('PROXY_LOSS_LIMIT');s.paper_eligible=False
        if sum(x['status']=='OPEN' for x in p.positions())>=config['proxy_paper']['max_open_positions']:s.paper_blockers.append('PROXY_OPEN_POSITION_LIMIT');s.paper_eligible=False
    finally:p.close()
    live=evaluate(store,now)
    option=option_evaluation(store,config,news,now)
    if option and option.paper_eligible:s=option
    elif option:s.explanation+=['Option mode blocked: '+', '.join(option.paper_blockers)]
    from options.trade_plan import mismatch
    if mismatch([store.get('quote:SPY',{}) or {},store.get('research_quote:SPY:iex',{}) or {}],config,now):s.paper_blockers.append('FEED_MISMATCH');s.paper_eligible=False
    if not market_session(now)['active']:
        historical=(store.get('features') or {}).get('5m',{}).get('trend')
        direction='UP' if historical=='BULL' else 'DOWN' if historical=='BEAR' else 'MIXED'
    else:direction=live.get('direction') or 'MIXED'
    return s.dict(),direction

def option_evaluation(store,config,news,now):
    """Cached stream inputs are re-aged; no historical source is promoted to live."""
    from features.indicators import multi_timeframe
    from features.market_regime import classify
    from options.contract_selector import select
    from risk.options_policy import check
    from backtesting.paper_engine import PaperEngine
    from core.storage import ROOT
    from core.signals import build
    q=store.get('quote:SPY') or {}
    if not quote_valid(q,now):return None
    px=q['payload'].get('mid')
    if not finite(px):return None
    rows={r['t']:r for r in (store.get('bars') or {}).get('payload',{}).get('bars',[])}
    rows.update({r['t']:r for r in store.get('stream_bars:SPY',[])})
    try:fs=multi_timeframe(sorted(rows.values(),key=lambda r:r['t']),(store.get('daily') or {}).get('payload',{}).get('bars',[]),now)
    except (ValueError,KeyError,TypeError):return None
    regime=classify(fs.get('5m',{}),q.get('quality'));direction='CALL' if regime['regime'] in ('BULL','STRONG_BULL') else 'PUT'
    chain=(store.get('chain') or {}).get('payload',{}).get('contracts',{})
    selection=select(chain,px,direction,now,min_dte=config['min_dte'],max_premium=config['options_risk']['max_trade_premium_usd'],atr=fs.get('5m',{}).get('atr14'),volatility_state=regime['regime'])
    p=PaperEngine(ROOT/'runtime/paper.sqlite')
    try:state=p.risk_state(now)
    finally:p.store.close()
    c=selection.get('best_contract');premium=(c['ask']+float(config['paper_slippage_per_share']))*100+float(config['paper_fee_per_contract']) if c else None
    risk=check({**config['options_risk'],**{k:state[k] for k in ('daily_loss_usd','consecutive_losses','daily_reconciled_date')}},state['positions'],premium=premium,now=now,mode='paper')
    s=build(fs,regime,selection,q,news,market_session(now),risk,now,{**config,'clock_health':store.get('ntp_clock')})
    from options.trade_plan import mismatch
    if mismatch([q,store.get('research_quote:SPY:iex') or {}],config,now):s.paper_blockers.append('FEED_MISMATCH');s.paper_eligible=False
    return s
