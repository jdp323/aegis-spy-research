"""Default Telegram templates. Every number is supplied evidence, never invented."""
from datetime import datetime, timedelta, timezone
from core.sessions import ET, market_session
from data.models import finite, stamp
from core.directional_research import view

def price(v):return '$%.2f'%v if finite(v) else 'unavailable'
def clock(v):
    try:return stamp(v).astimezone(ET).strftime('%H:%M ET')
    except (ValueError,TypeError,KeyError):return 'unavailable'

def next_event(news,now):
    if news.get('quality')!='DATA_OK':return 'event data unavailable'
    rows=[]
    for e in news.get('events') or []:
        try:
            t=stamp(e['time_utc']);all_day=e.get('time_source')=='DATE_ONLY' and t.astimezone(ET).date()==now.astimezone(ET).date()
            if all_day or t>=now:rows.append((not all_day,t,e))
        except (KeyError,TypeError,ValueError):return 'event data unavailable — invalid event time'
    if not rows:return 'no required scheduled event listed; optional coverage incomplete'
    _,t,e=min(rows,key=lambda r:r[:2]);name=' '.join(str(e.get('name') or e.get('category') or 'verified event').split())[:65]
    return name+' · '+('all-day ET' if e.get('time_source')=='DATE_ONLY' else clock(e['time_utc']))
def reason(text):
    text=str(text or '')
    for key,label in [('quote age','fresh price unavailable'),('COOL_OFF','research pause active'),('cool off','research pause active'),('SOURCE','fresh price unavailable'),('data not fresh','fresh price unavailable'),('BAR_','completed minutes missing'),('history','completed minutes missing'),('NEGATIVE','setup evidence under review'),('DIRECTION_COOLDOWN','similar watch recently alerted')]:
        if key in text:return label
    return text.removeprefix('NO TRADE — ').replace('_',' ').lower()[:85] or 'setup not confirmed'

def status_text(ctx,now,news,horizons=None,entry_reason=None,plan=None):
    from core.market_view import build
    s=build(ctx,news,now,plan=plan,entry_reason=entry_reason);p=s['price'];t=s['trend']
    bias={'UP':'upward bias','DOWN':'downward bias','MIXED':'conflicting evidence','SIDEWAYS':'range-bound hypothesis'}
    o=s['outlooks']['H60'];h=bias.get(o['bias'],'unavailable')
    condition=(' while SPY holds '+('above ' if o['bias']=='UP' else 'below ')+price(o['invalidation'])) if o['bias'] in ('UP','DOWN') and finite(o.get('invalidation')) else ''
    label='Last completed-bar trend: ' if t['descriptive_only'] and t['state']!='UNAVAILABLE' else 'Current trend: '
    line='New entry: '+s['entry']['state']+' — '+s['entry']['reason']
    active_line='Public plan: NONE.'
    if s['primary_plan']:
        active=s['primary_plan'];active_line='Public plan '+active['signal_id']+': '+active['public_state']+' ('+active['state']+') · no new entry'
        if not active['monitoring_available']:
            active_line+='; monitoring unavailable';line='New entry: WAIT — '+s['entry']['reason']
    local=now.astimezone(ET);minute=local.hour*60+local.minute;nxt=(minute//15+1)*15;close=market_session(now)['close_minute']
    next_summary=('%02d:%02d ET'%(nxt//60,nxt%60)) if nxt<=close-15 and market_session(now)['active'] else 'next trading session'
    watch='Setup watch: await a new completed-candle confirmation.'
    if not ctx.get('reason'):
        from strategies.idea_setups import pending_triggers
        try:
            watches=pending_triggers(ctx.get('features') or {},{})
            if watches:watch='Setup watch: '+watches[0]['direction']+' direction '+('above ' if watches[0]['direction']=='CALL' else 'below ')+price(watches[0]['price'])+'; rule confirmation required.'
        except (KeyError,ValueError,TypeError):pass
    lines=[now.astimezone(ET).strftime('%H:%M ET')+' · SPY '+price(p['value']),label+t['state']+' through '+clock(t['as_of'])+' completed candle',
        'Next hour: '+h+condition+' · conditional',watch,active_line,line,
        'Research · '+p['provider']+(' · limited early read' if s['evidence']['early_limited'] else '')+' · '+('bar close ' if p['kind']=='COMPLETED_BAR_CLOSE' else 'as of ')+clock(p['source_at'])+'; option quote unavailable' if not s['entry']['option_eligible'] else 'Research · '+p['provider']+' · verified option reference only',
        'Next summary: '+next_summary+'; confirmed changes alert sooner. /details']
    return '\n'.join(lines)

def premarket_text(report,news,now):
    from core.market_view import premarket_view
    p=premarket_view(report,now);px=p['reference'];low=p['low'];high=p['high'];asof=p['source_at'];current=p['current_premarket'];bias=p['opening_hour_lean'];usable=p['reference_kind']=='CURRENT_PREMARKET_BAR_RESEARCH'
    bullish='a completed 5m candle breaks '+price(high) if usable and finite(high) else 'unavailable; genuine premarket range missing'
    bearish='a completed 5m candle breaks '+price(low) if usable and finite(low) else 'unavailable; genuine premarket range missing'
    return '\n'.join(['SPY PREMARKET · '+now.astimezone(ET).strftime('%b %d · %H:%M ET'),'Opening-hour lean: '+bias+' · conditional; Session lean: UNCLEAR',
        'Premarket range: '+(price(low)+'–'+price(high) if usable and finite(low) and finite(high) else 'unavailable; prior-close projection is not premarket'),
        'Bullish scenario: '+bullish,'Bearish scenario: '+bearish,'Events: '+next_event(news,now),
        'Action: WAIT; opening range not known yet; reassess after the open. First update 09:45 ET.',
        'Data: '+str(report.get('quality','DATA UNAVAILABLE'))+' · as of '+clock(asof)+'; research only'])

def i_verification(idea):return idea.get('option_verification') == 'FRESH_QUOTE_GREEKS_CHAIN_SANITY_PASSED'

def verified_option(idea,now):
    from options.research_contract import current_reference
    return current_reference(idea,now)

def idea_text(i,tag,config,now=None):
    now=now or stamp(i['timestamp']);side='above' if i['direction']=='CALL' else 'below'
    from core.market_view import plan_view
    # All public plan levels come from the same immutable named-field view.
    canonical=plan_view(i,now)
    i={**i,**{k:v for k,v in canonical.items() if v is not None}}
    entry=i.get('entry_condition') or ('completed candle close '+side+' SPY '+price(i.get('trigger_level',i.get('trigger'))))
    # Keep the actual timeframe from the strategy; never claim an unrequired 5m close.
    end=stamp(i['max_hold_until']);expiry=stamp(i['signal_expiry'])
    if expiry>=end or now>=expiry:return 'ID '+str(i['signal_id'])+' · entry cancelled — deadline reached'
    hold=i.get('horizon_id',i.get('horizon','UNAVAILABLE'));label=str(i.get('planned_holding_minutes',max(0,int((end-stamp(i.get('confirmation_at',i['timestamp']))).total_seconds()//60))))+' minutes'
    verified=verified_option(i,now)
    option='Underlying watch only · option contract unavailable.'
    if verified:
        c,p=verified;cost=p['limit']*100;fee=float(config.get('paper_fee_per_contract',.65))
        option='Option: '+c['symbol']+' · '+c['expiry']+' '+str(c['strike'])+c['type']+' · bid/ask '+price(c['bid'])+'/'+price(c['ask'])+' @ '+clock(c['quote']['source_timestamp'])+'; limit '+price(p['limit'])+'/share · 100× = '+price(cost)+' + '+price(fee)+' entry fee; premium at risk '+price(cost)+' + fees'
    heading='SPY SETUP CONFIRMED · research · ID '+str(i['signal_id'])+' · '+i['direction']+' direction'
    return '\n'.join([heading,
        ('ENTRY CONFIRMED · ' if i.get('entry_mode')=='ENTER NOW' else 'WAIT · Enter after ')+entry, 'SPY reference: '+price(i.get('reference_midpoint',i.get('entry')))+'; do not enter '+side+' SPY '+price(i.get('do_not_chase')),
        'SPY target: '+price(i.get('t2'))+' · target 1 '+price(i.get('t1')), 'Exit condition: SPY at or '+('below ' if side=='above' else 'above ')+price(i.get('invalidation')),
        'Planned hold: '+hold+' · up to '+label+'; exit by '+clock(i['max_hold_until']),
        'Entry expires: '+clock(i['signal_expiry']),option,'Experimental · manual review; underlying levels; no guaranteed stop-loss cap'])

def update_text(i,condition):
    changes={'TARGET_1_HIT':'SPY target 1 reached; full-exit policy unchanged','TARGET_2_HIT':'EXIT CONDITION REACHED — SPY target reached in research',
        'STOP_HIT':'EXIT CONDITION REACHED — SPY invalidation reached in research','TIME_EXIT':'EXIT CONDITION REACHED — holding deadline reached',
        'ENTRY_TRIGGERED':'ENTRY CONFIRMED — underlying research only','IDEA_EXPIRED':'Entry cancelled — validity expired',
        'IDEA_CANCELLED':'Entry cancelled','MONITORING_UNAVAILABLE':'Monitoring unavailable; no exit confirmed',
        'ADMIN_CLOSED_UNRESOLVED':'ADMIN CLOSED UNRESOLVED — research slot released at its administrative end; outcome unknown',
        'NEWS_EXIT_REVIEW':'Event risk changed; review monitoring'}
    level=i.get({'STOP_HIT':'invalidation','TARGET_1_HIT':'t1','TARGET_2_HIT':'t2'}.get(condition,''))
    provenance=('SPY level '+price(level)+' · ' if finite(level) else '')+'bar as of '+clock(i.get('last_bar_end'))+' · '+str(i.get('feed_quality','UNAVAILABLE'))+'; monitoring freshness unverified. '
    return 'ID '+str(i.get('signal_id','unavailable'))+' · '+changes.get(condition,str(condition).replace('_',' ').lower())+'\n'+provenance+'Research update; your fills remain separate.'

def recap_text(rows,now,reference,forecast_score=None,snapshot=None):
    from core.market_view import recap_view
    r=(snapshot or {}).get('recap') or recap_view(rows,now)
    closed=r['closed'];open_=r['open'];unresolved=r['unresolved'];no_entry=r['cancelled']
    ops=r.get('operations');operation=(str(ops['accepted'])+'/'+str(ops['expected'])+' accepted; '+str(ops['late_or_missing'])+' late/missing') if ops else 'not measured in this fixture/view'
    calendar=(snapshot or {}).get('evidence',{}).get('calendar_quality')
    return '\n'.join(['SPY RECAP · '+now.astimezone(ET).strftime('%b %d'),
        'Ideas alerted: '+str(r['alerted'])+(' · expired/cancelled: '+str(no_entry) if no_entry else ''),
        'Alerted research: '+str(closed)+' closed · '+str(open_)+' open · '+str(unresolved)+' unresolved',
        'Option-paper dollars: unavailable without genuine quotes',
        'Next session: '+('review retained session levels in /details' if reference and not reference.startswith('UNAVAILABLE') else 'wait for genuine opening-range data'),
        'Confirmed plans: '+str(r['confirmed'])+' · '+str(r['silent_observations'])+' silent observations separate · '+str(r.get('carried_in',0))+' carried in',
        'Admin closed unresolved: '+str(r.get('administratively_closed_unresolved',0))+'; outcomes remain unknown',
        'Operations: '+operation+' · calendar '+('verified' if calendar=='DATA_OK' else 'unavailable')+'; /score for after-cost research'])
