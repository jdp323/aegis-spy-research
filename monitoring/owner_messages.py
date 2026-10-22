"""Default Telegram templates. Every number is supplied evidence, never invented."""
from datetime import datetime, timedelta, timezone
from core.sessions import ET, market_session
from data.models import finite, stamp
from core.directional_research import view

def price(v):return '$%.2f'%v if finite(v) else 'unavailable'
def clock(v):
    try:return stamp(v).astimezone(ET).strftime('%H:%M ET')
    except (ValueError,TypeError,KeyError):return 'unavailable'
def reason(text):
    text=str(text or '')
    for key,label in [('quote age','fresh price unavailable'),('COOL_OFF','research pause active'),('cool off','research pause active'),('SOURCE','fresh price unavailable'),('data not fresh','fresh price unavailable'),('BAR_','completed minutes missing'),('history','completed minutes missing'),('NEGATIVE','setup evidence under review'),('DIRECTION_COOLDOWN','similar watch recently alerted')]:
        if key in text:return label
    return text.removeprefix('NO TRADE — ').replace('_',' ').lower()[:85] or 'setup not confirmed'

def status_text(ctx,now,news,horizons=None,entry_reason=None,plan=None):
    r=view(ctx,now);out=r.get('outlooks',{}).get('H60',{})
    bias={'UP':'upward bias','DOWN':'downward bias','SIDEWAYS':'no directional edge'}.get(out.get('bias'),'unavailable — insufficient time or data')
    if not market_session(now)['active']:why='market closed'
    elif ctx.get('reason'):why=reason(ctx['reason'])
    elif news.get('quality')!='DATA_OK':why='event data unavailable'
    elif news.get('risk') not in ('NORMAL','MODERATE'):why='major event blackout'
    elif entry_reason and entry_reason.startswith(('BUY CALL','BUY PUT')):why='underlying watch; option gates separate'
    else:why=reason(entry_reason)
    source=r.get('provider','UNAVAILABLE')+(' · limited early read' if r.get('limited') else '')
    from core.primary_plan import state as plan_state
    plan_line=('Plan '+str(plan['signal_id'])+': '+plan_state(plan,now)+' — underlying research; no new entry') if plan else 'New entry: WAIT — '+why
    if plan and ctx.get('reason'):plan_line='New entry: WAIT — '+why+'; plan '+str(plan['signal_id'])+' monitoring limited'
    return '\n'.join([now.astimezone(ET).strftime('%H:%M ET')+' · SPY '+price(r['price']),
        'Current trend: '+r['trend'], 'Next hour: '+bias,
        plan_line, 'Research · '+source+' · as of '+clock(r['as_of'])])

def premarket_text(report,news,now):
    l=report.get('levels') or {};px=l.get('last');low=l.get('low');high=l.get('high')
    usable=report.get('quality') in ('IEX_RESEARCH_ONLY','PUBLIC_RESEARCH_ONLY','SIMULATED') and finite(px)
    bias={'BULLISH':'UP','BEARISH':'DOWN','UP':'UP','DOWN':'DOWN'}.get(report.get('bias'),'SIDEWAYS' if usable else 'DATA UNAVAILABLE')
    invalid=low if bias=='UP' else high if bias=='DOWN' else None
    outlook=bias+(' while SPY holds '+('above ' if bias=='UP' else 'below ')+price(invalid) if finite(invalid) else '')
    triggers=('CALL watch: confirmed break above '+price(high)) if usable and finite(high) else 'CALL watch: unavailable; reassess after open'
    reversal=('Downside reversal: below '+price(low)) if usable and finite(low) else 'Reversal level: unavailable'
    if bias=='DOWN':triggers='PUT watch: confirmed break below '+price(low) if finite(low) else 'PUT watch: unavailable';reversal='Upside reversal: above '+price(high)
    events=news.get('events') or []
    event_text='event data unavailable'
    if news.get('quality')=='DATA_OK':
        event_text='; '.join(str(e.get('name') or e.get('title') or e.get('category') or 'verified event')[:60] for e in events[:2]) or 'no required scheduled event listed; optional coverage incomplete'
    asof=report.get('as_of_bar') or report.get('as_of')
    return '\n'.join(['SPY PREMARKET · '+now.astimezone(ET).strftime('%b %d'),"Today’s outlook: "+outlook,
        'Premarket: '+price(px if usable else None)+' · as of '+clock(asof),triggers,reversal,
        'Major events: '+event_text,'Research outlook · reassess after the open'])

def i_verification(idea):return idea.get('option_verification') == 'FRESH_QUOTE_GREEKS_CHAIN_SANITY_PASSED'

def verified_option(idea,now):
    from core.signals import option_quote_valid,quote_valid
    from options.ledger import contract as parse
    c=idea.get('option_contract') or {};p=idea.get('option_plan') or {}
    try:
        term=parse(c['symbol']);end=stamp(idea['max_hold_until'])
        if not option_quote_valid(c['quote'],now) or not quote_valid(c['quote'],now,5) or not i_verification(idea):return None
        from options.trade_plan import sanity
        if sanity(c,now,{}):return None
        if datetime.fromisoformat(term['expiry']).date()<=end.astimezone(ET).date():return None
        if c.get('type')!=('C' if idea['direction']=='CALL' else 'P'):return None
        if not c.get('greeks_timestamp') or not 0<=(now-stamp(c['greeks_timestamp'])).total_seconds()<=60:return None
        if not finite(p.get('limit')) or p['limit']<=0:return None
        # Contract selector/plan remains responsible for chain sanity, liquidity,
        # expiry and entitlement. The formatter adds no eligibility of its own.
        if p.get('eligible') is False:return None
        return c,p
    except (ValueError,KeyError,TypeError):return None

def idea_text(i,tag,config):
    now=stamp(i['timestamp']);side='above' if i['direction']=='CALL' else 'below'
    entry=i.get('entry_condition') or ('completed candle close '+side+' SPY '+price(i.get('trigger_level',i.get('trigger'))))
    # Keep the actual timeframe from the strategy; never claim an unrequired 5m close.
    end=stamp(i['max_hold_until']);expiry=stamp(i['signal_expiry'])
    if expiry>=end or now>=expiry:return 'ID '+str(i['signal_id'])+' · entry cancelled — deadline reached'
    hold=i.get('horizon_id',i.get('horizon','SCALP'));label=str(max(0,int((end-now).total_seconds()//60)))+' minutes'
    verified=verified_option(i,now)
    option='Underlying watch only · option contract unavailable.'
    if verified:
        c,p=verified;cost=p['limit']*100;fee=float(config.get('paper_fee_per_contract',.65))
        option='Option: '+c['symbol']+' limit '+price(p['limit'])+'/share · 100× = '+price(cost)+' + '+price(fee)+' entry fee; premium at risk '+price(cost)+' + fees'
    return '\n'.join([i['direction']+' RESEARCH · ID '+str(i['signal_id']),
        ('ENTRY CONFIRMED · ' if i.get('entry_mode')=='ENTER NOW' else 'WAIT · Enter after ')+entry, 'Do not enter '+side+' SPY '+price(i.get('do_not_chase')),
        'SPY target: '+price(i.get('t2')), 'Exit condition: SPY at or '+('below ' if side=='above' else 'above ')+price(i.get('invalidation')),
        'Planned hold: up to '+label+'; exit by '+clock(i['max_hold_until']),
        'Entry expires: '+clock(i['signal_expiry']),option,'Experimental · manual review; underlying levels; no guaranteed stop-loss cap'])

def update_text(i,condition):
    changes={'TARGET_1_HIT':'SPY target 1 reached; full-exit policy unchanged','TARGET_2_HIT':'EXIT CONDITION REACHED — SPY target reached in research',
        'STOP_HIT':'EXIT CONDITION REACHED — SPY invalidation reached in research','TIME_EXIT':'EXIT CONDITION REACHED — holding deadline reached',
        'ENTRY_TRIGGERED':'ENTRY CONFIRMED — underlying research only','IDEA_EXPIRED':'Entry cancelled — validity expired',
        'IDEA_CANCELLED':'Entry cancelled','MONITORING_UNAVAILABLE':'Monitoring unavailable; no exit confirmed',
        'NEWS_EXIT_REVIEW':'Event risk changed; review monitoring'}
    return 'ID '+str(i.get('signal_id','unavailable'))+' · '+changes.get(condition,str(condition).replace('_',' ').lower())+'\nResearch update; your fills remain separate.'

def recap_text(rows,now,reference):
    day=now.astimezone(ET).date();today=[r for r in rows if stamp(r['timestamp']).astimezone(ET).date()==day]
    alerted=[r for r in today if r.get('alerted')]
    closed=sum(r.get('status')=='CLOSED' for r in alerted);open_=sum(r.get('status') in ('OPEN','PENDING') and r.get('coverage_status')!='UNRESOLVED_GAP' for r in alerted)
    unresolved=sum(r.get('coverage_status')=='UNRESOLVED_GAP' or r.get('status') not in ('CLOSED','OPEN','PENDING','EXPIRED','EXPIRED_NO_ENTRY','CANCELLED') for r in alerted)
    no_entry=sum(r.get('status') in ('EXPIRED','EXPIRED_NO_ENTRY','CANCELLED') for r in alerted)
    return '\n'.join(['SPY RECAP · '+now.astimezone(ET).strftime('%b %d'),
        'Ideas alerted: '+str(len(alerted))+(' · expired/cancelled: '+str(no_entry) if no_entry else ''),
        'Alerted research: '+str(closed)+' closed · '+str(open_)+' open · '+str(unresolved)+' unresolved',
        'Option-paper dollars: unavailable without genuine quotes',
        'Next session: '+('review retained session levels in /details' if reference and not reference.startswith('UNAVAILABLE') else 'wait for genuine opening-range data'),
        str(len(today)-len(alerted))+' silent observations separate · /score · data quality varies'])
