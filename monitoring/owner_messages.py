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
    h=bias.get(s['outlooks']['H60']['bias'],'unavailable');session=bias.get(s['outlooks']['SESSION']['bias'],'unclear')
    label='Last completed-bar trend: ' if t['descriptive_only'] and t['state']!='UNAVAILABLE' else 'Current trend: '
    line='New entry: '+s['entry']['state']+' — '+s['entry']['reason']
    warning=None
    if s['primary_plan']:
        active=s['primary_plan'];line='Active plan '+active['signal_id']+': '+active['state']+' · no additional entry (no new entry)'
        if not active['monitoring_available']:
            warning=line+'; monitoring unavailable';line='New entry: WAIT — '+s['entry']['reason']
    lines=[now.astimezone(ET).strftime('%H:%M ET')+' · SPY '+price(p['value']),label+t['state'],
        'Next hour: '+h+' · session: '+session,line,
        'Research · '+p['provider']+(' · limited early read' if s['evidence']['early_limited'] else '')+' · '+('bar close ' if p['kind']=='COMPLETED_BAR_CLOSE' else 'as of ')+clock(p['source_at'])+' · /details']
    if warning:lines.insert(-1,warning)
    return '\n'.join(lines)

def premarket_text(report,news,now):
    from core.market_view import premarket_view
    p=premarket_view(report,now);px=p['reference'];low=p['low'];high=p['high'];asof=p['source_at'];current=p['current_premarket'];bias=p['opening_hour_lean'];usable=p['reference_kind']=='CURRENT_PREMARKET_BAR_RESEARCH'
    invalid=low if bias=='UP' else high if bias=='DOWN' else None
    outlook=bias+(' while SPY holds '+('above ' if bias=='UP' else 'below ')+price(invalid) if finite(invalid) else '')
    triggers=('CALL watch: confirmed break above '+price(high)) if usable and finite(high) else 'CALL watch: unavailable; reassess after open'
    reversal=('Downside reversal: below '+price(low)) if usable and finite(low) else 'Reversal level: unavailable'
    if bias=='DOWN':triggers='PUT watch: confirmed break below '+price(low) if finite(low) else 'PUT watch: unavailable';reversal='Upside reversal: above '+price(high)
    events=news.get('events') or []
    event_text='event data unavailable'
    if news.get('quality')=='DATA_OK':
        event_text='; '.join(str(e.get('name') or e.get('title') or e.get('category') or 'verified event')[:60] for e in events[:2]) or 'no required scheduled event listed; optional coverage incomplete'
    event_text=next_event(news,now)
    label='Premarket: ' if current else 'Prior-close projection: '
    return '\n'.join(['SPY PREMARKET · '+now.astimezone(ET).strftime('%b %d · %H:%M ET'),'Opening-hour lean: '+outlook+' · conditional',
        'Session lean: UNCLEAR · reassess after opening range',triggers+'; '+reversal,
        'Watch: completed opening-range confirmation after 09:45 ET','Next major event: '+event_text,
        label+price(px if finite(px) else None)+' · '+str(report.get('quality','DATA UNAVAILABLE'))+' · as of '+clock(asof),'Research only · reassess after the open; no regular-session entry confirmed'])

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
        option='Option: '+c['symbol']+' limit '+price(p['limit'])+'/share · 100× = '+price(cost)+' + '+price(fee)+' entry fee; premium at risk '+price(cost)+' + fees'
    heading=i['direction']+' RESEARCH · ID '+str(i['signal_id']) if verified else 'SPY WATCH · ID '+str(i['signal_id'])+' · '+i['direction']+' direction'
    return '\n'.join([heading,
        ('ENTRY CONFIRMED · ' if i.get('entry_mode')=='ENTER NOW' else 'WAIT · Enter after ')+entry, 'Do not enter '+side+' SPY '+price(i.get('do_not_chase')),
        'SPY target: '+price(i.get('t2')), 'Exit condition: SPY at or '+('below ' if side=='above' else 'above ')+price(i.get('invalidation')),
        'Planned hold: '+hold+' · up to '+label+'; exit by '+clock(i['max_hold_until']),
        'Entry expires: '+clock(i['signal_expiry']),option,'Experimental · manual review; underlying levels; no guaranteed stop-loss cap'])

def update_text(i,condition):
    changes={'TARGET_1_HIT':'SPY target 1 reached; full-exit policy unchanged','TARGET_2_HIT':'EXIT CONDITION REACHED — SPY target reached in research',
        'STOP_HIT':'EXIT CONDITION REACHED — SPY invalidation reached in research','TIME_EXIT':'EXIT CONDITION REACHED — holding deadline reached',
        'ENTRY_TRIGGERED':'ENTRY CONFIRMED — underlying research only','IDEA_EXPIRED':'Entry cancelled — validity expired',
        'IDEA_CANCELLED':'Entry cancelled','MONITORING_UNAVAILABLE':'Monitoring unavailable; no exit confirmed',
        'NEWS_EXIT_REVIEW':'Event risk changed; review monitoring'}
    return 'ID '+str(i.get('signal_id','unavailable'))+' · '+changes.get(condition,str(condition).replace('_',' ').lower())+'\nResearch update; your fills remain separate.'

def recap_text(rows,now,reference,forecast_score=None,snapshot=None):
    from core.market_view import recap_view
    r=(snapshot or {}).get('recap') or recap_view(rows,now)
    closed=r['closed'];open_=r['open'];unresolved=r['unresolved'];no_entry=r['cancelled']
    return '\n'.join(['SPY RECAP · '+now.astimezone(ET).strftime('%b %d'),
        'Ideas alerted: '+str(r['alerted'])+(' · expired/cancelled: '+str(no_entry) if no_entry else ''),
        'Alerted research: '+str(closed)+' closed · '+str(open_)+' open · '+str(unresolved)+' unresolved',
        'Option-paper dollars: unavailable without genuine quotes',
        'Next session: '+('review retained session levels in /details' if reference and not reference.startswith('UNAVAILABLE') else 'wait for genuine opening-range data'),
        'Confirmed plans: '+str(r['confirmed'])+' · '+str(r['silent_observations'])+' silent observations separate',
        forecast_score or 'Forward outlook: outcomes unavailable; no accuracy claimed',
        '/score · data quality varies'])
