"""Descriptive public-chart briefs, isolated from actionable signal/position gates.

The chart's delay is unverified. A fresh fetch is never proof of a live quote.
Only explicitly selected public fields enter shared messages.
"""
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from core.storage import ROOT
from data.models import stamp
from core.sessions import market_session

ET = ZoneInfo('America/New_York')
SOURCE = 'https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=5m&range=5d&includePrePost=false'
from data.massive_research import SOURCE as MASSIVE_SOURCE
from data.premarket_spy import URL as EXTENDED_SOURCE
DEFAULTS = {'enabled': True, 'regular_seconds': 1800, 'change_seconds': 600,
            'premarket_seconds': 3600, 'after_hours_seconds': 7200, 'closed_seconds': 21600,
            'move_alert_pct': 0.3}

def settings(config):
    c = {**DEFAULTS, **config.get('research_notifications', {})}
    if type(c['enabled']) is not bool:
        raise ValueError('INVALID_RESEARCH_NOTIFICATION_CONFIGURATION')
    for name in DEFAULTS:
        if name == 'enabled':
            continue
        if name == 'move_alert_pct':
            if type(c[name]) not in (float,int) or not math.isfinite(c[name]) or not .1<=c[name]<=5:
                raise ValueError('INVALID_RESEARCH_MOVEMENT_THRESHOLD')
            continue
        minimum = 300 if name in ('regular_seconds', 'change_seconds') else 3600
        if type(c[name]) is not int or c[name] < minimum:
            raise ValueError('UNSAFE_RESEARCH_NOTIFICATION_CADENCE')
    return c

def load():
    try:
        return json.loads((ROOT/'research/spy_research_latest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}

def observe(snapshot, session, now):
    """Reject stale/invalid observations rather than filling gaps with old prices."""
    try:
        if session.get('quality') != 'DATA_OK':
            raise ValueError('CALENDAR_UNAVAILABLE')
        if snapshot.get('source') not in (SOURCE,MASSIVE_SOURCE,EXTENDED_SOURCE) or snapshot.get('data_use') != 'DELAYED_OR_UNVERIFIED_RESEARCH_ONLY':
            raise ValueError('PUBLIC_SOURCE_UNVERIFIED')
        if (snapshot.get('multi_source') or {}).get('intraday_comparison',{}).get('status')=='DISAGREEMENT':raise ValueError('SOURCE_DISAGREEMENT')
        if snapshot.get('data_status') != 'RESEARCH_DATA_RECEIVED':
            raise ValueError('PUBLIC_DATA_UNAVAILABLE')
        fetched = stamp(snapshot['source_fetched_at'])
        generated = stamp(snapshot['generated_at'])
        max_fetch_age = 600 if session['active'] else 25200
        if any(not -10 <= (now-t).total_seconds() <= max_fetch_age for t in (fetched, generated)):
            raise ValueError('PUBLIC_SNAPSHOT_STALE')
        l = snapshot['levels']; bar = stamp(l['last_completed_bar_at'])
        if bar.astimezone(ET).date().isoformat() != l['session_date'] or bar.minute % 5:
            raise ValueError('BAR_SESSION_INVALID')
        local_bar = bar.astimezone(ET)
        if not market_session(bar)['active']:
            raise ValueError('BAR_OUTSIDE_REGULAR_SESSION')
        end = bar+timedelta(minutes=5)
        if end > min(now, fetched)+timedelta(seconds=10):
            raise ValueError('BAR_NOT_COMPLETE')
        if session['active'] and (l['session_date'] != session['date'] or (now-end).total_seconds() > 900):
            raise ValueError('PUBLIC_BAR_STALE')
        if not session['active'] and (now-end).total_seconds() > 7*86400:
            raise ValueError('HISTORICAL_BAR_TOO_OLD')
        values = [l[k] for k in ('last_close', 'high', 'low', 'open', 'bar_based_vwap_approx')]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError('PUBLIC_LEVEL_INVALID')
        if not l['low'] <= min(l['open'], l['last_close'], l['bar_based_vwap_approx']) <= max(l['open'], l['last_close'], l['bar_based_vwap_approx']) <= l['high']:
            raise ValueError('PUBLIC_LEVEL_INCONSISTENT')
        p = snapshot.get('patterns', {})
        if p.get('status') != 'DESCRIPTIVE_ONLY' or p.get('session') != l['session_date'] or p.get('as_of_bar') != int(bar.timestamp()):
            raise ValueError('PATTERN_TIMESTAMP_MISMATCH')
        structure = p.get('structure_3bars', 'UNAVAILABLE')
        relation = p.get('vwap_relationship', 'UNAVAILABLE')
        if relation not in ('ABOVE', 'BELOW', 'AT', 'UNAVAILABLE'):
            raise ValueError('INVALID_VWAP_RELATIONSHIP')
        expected_relation = 'ABOVE' if l['last_close'] > l['bar_based_vwap_approx'] else 'BELOW' if l['last_close'] < l['bar_based_vwap_approx'] else 'AT'
        if relation != expected_relation:
            raise ValueError('INVALID_VWAP_RELATIONSHIP')
        # Conservative, descriptive alignment; not a forecast or multi-timeframe regime.
        trend = 'UPWARD 5m STRUCTURE' if structure == 'HIGHER_HIGHS_HIGHER_LOWS' and relation == 'ABOVE' else 'DOWNWARD 5m STRUCTURE' if structure == 'LOWER_HIGHS_LOWER_LOWS' and relation == 'BELOW' else 'MIXED / INSUFFICIENT 5m STRUCTURE'
        labels = [x for x in p.get('patterns', []) if x in ('CLOSE_ABOVE_OPENING_RANGE', 'CLOSE_BELOW_OPENING_RANGE')]
        opening = p.get('opening_range_15m')
        if opening and (any(type(opening.get(k)) not in (float, int) or not math.isfinite(opening[k]) or opening[k] <= 0 for k in ('high','low')) or opening['high'] < opening['low']):
            raise ValueError('OPENING_RANGE_INVALID')
        expected_labels=['CLOSE_ABOVE_OPENING_RANGE'] if opening and l['last_close']>opening['high'] else ['CLOSE_BELOW_OPENING_RANGE'] if opening and l['last_close']<opening['low'] else []
        if labels!=expected_labels:raise ValueError('OPENING_RANGE_MISMATCH')
        return {'quality': 'PUBLIC_RESEARCH_ONLY', 'levels': l, 'bar': bar,
                'trend': trend, 'relationship': relation, 'labels': labels, 'opening': opening,'source':snapshot['source'],'multi_source':snapshot.get('multi_source',{}),'structure':structure}
    except (ValueError, KeyError, TypeError, OverflowError) as e:
        reason = str(e) if str(e) in ('CALENDAR_UNAVAILABLE','PUBLIC_SOURCE_UNVERIFIED','PUBLIC_DATA_UNAVAILABLE','PUBLIC_SNAPSHOT_STALE','BAR_SESSION_INVALID','BAR_OUTSIDE_REGULAR_SESSION','BAR_NOT_COMPLETE','PUBLIC_BAR_STALE','HISTORICAL_BAR_TOO_OLD','PUBLIC_LEVEL_INVALID','PUBLIC_LEVEL_INCONSISTENT','PATTERN_TIMESTAMP_MISMATCH','INVALID_VWAP_RELATIONSHIP','OPENING_RANGE_INVALID','OPENING_RANGE_MISMATCH') else 'PUBLIC_SNAPSHOT_INVALID'
        if str(e)=='SOURCE_DISAGREEMENT':reason='SOURCE_DISAGREEMENT'
        return {'quality': 'UNAVAILABLE', 'reason': reason,'multi_source':snapshot.get('multi_source',{})}

def text_for(observation, session, now):
    lines=['SPY | '+now.astimezone(ET).strftime('%Y-%m-%d %H:%M ET'),
           'ACTION: NO TRADE — no verified option entry or exit.']
    if observation['quality']=='UNAVAILABLE':
        lines += ['TREND: Not established — usable recent data is missing.',
                  'CLOSING ESTIMATE: Not available.',
                  'BUY / SELL PRICES: Not issued. Check /feed for data details.']
    else:
        from research.closing_estimate import estimate
        f=estimate(observation,session,now=now);l=observation['levels'];bar=observation['bar'];trend=observation['trend']
        label='BULLISH' if trend=='UPWARD 5m STRUCTURE' else 'BEARISH' if trend=='DOWNWARD 5m STRUCTURE' else 'MIXED / UNCLEAR'
        why='Higher highs/lows; above approximate VWAP.' if label=='BULLISH' else 'Lower highs/lows; below approximate VWAP.' if label=='BEARISH' else 'Recent structure and VWAP do not clearly align.'
        outlook='Recent upward momentum; continuation is uncertain.' if label=='BULLISH' else 'Recent downward momentum; continuation is uncertain.' if label=='BEARISH' else 'No clear directional outlook from recent bars.'
        lines += ['TREND: '+label+' (observed5m bars).',
                  'LAST OBSERVED: $%.2f USD | '%l['last_close']+bar.astimezone(ET).strftime('%Y-%m-%d %H:%M')+'-'+(bar+timedelta(minutes=5)).astimezone(ET).strftime('%H:%M ET'),
                  'WHY: '+why,'OUTLOOK: '+outlook]
        if f['status']=='EXPERIMENTAL_SCENARIOS':
            lines += ['CLOSING AREA — EXPERIMENTAL: $%.2f-$%.2f; midpoint $%.2f USD.'%(f['low'],f['high'],f['median']),
                      'Based on %d prior sessions; unvalidated historical scenarios, not a calibrated forecast.'%f['historical_sessions']]
            if not f['beats_no_change']:lines.append('Evidence: this baseline has not beaten a no-change estimate in its historical test.')
        else:lines.append('CLOSING ESTIMATE: Not established — '+('session is closed or closing' if f['reason'] in ('NO_FRESH_ACTIVE_SESSION_OBSERVATION','SESSION_CLOSE_TOO_NEAR') else 'not enough usable historical evidence')+'.')
        lines += ['OBSERVED LEVELS: Approx. VWAP $%.2f | session low $%.2f / high $%.2f.'%(l['bar_based_vwap_approx'],l['low'],l['high']),
                  'CALL / PUT: No recommendation.', 'ENTRY / STOP / TARGET: Not issued.']
        if not session['active']:lines.append('Market inactive: these are previous regular-session observations.')
    from research.source_consensus import message_context
    lines += [message_context(observation,observation.get('trend'))]
    source='Massive API bars' if observation.get('source')==MASSIVE_SOURCE else 'Yahoo public chart'
    lines += ['DATA: '+source+'. Delay UNVERIFIED; not real-time options data.',
              '/setup = trade blockers | /forecast = estimate details | /news = update']
    return '\n'.join(lines)

def context(o):
    if o['quality']!='PUBLIC_RESEARCH_ONLY':return {'quality':o['quality']}
    return {'quality':o['quality'],'session_date':o['levels']['session_date'],'bar':o['bar'].isoformat(),'close':o['levels']['last_close'],'trend':o['trend'],'relationship':o['relationship'],'labels':o['labels'],'source':o.get('source',SOURCE)}

def short_text(o,session,now,basic_raw=None):
    """Basic direction first; detailed evidence remains available through /news."""
    from research.basic_trend import analyze,text_for as basic_text
    from data.trend_spy import load as basic_load
    r=analyze(basic_load() if basic_raw is None else basic_raw,now)
    if o.get('reason')=='SOURCE_DISAGREEMENT':
        return 'SPY TREND: UNAVAILABLE\nIndependent sources disagree; no current direction claimed. /feed shows details.'
    if r['direction']!='UNAVAILABLE':return basic_text(r)+'\n/trend = simple direction | /news = detailed research'
    if o['quality']=='PUBLIC_RESEARCH_ONLY':
        label='UP' if o['trend']=='UPWARD 5m STRUCTURE' else 'DOWN' if o['trend']=='DOWNWARD 5m STRUCTURE' else 'MIXED'
        scope='RECENT REGULAR SESSION' if session['active'] else 'LAST REGULAR SESSION — historical'
        structure=o.get('structure','UNAVAILABLE')
        signs=[1 if structure=='HIGHER_HIGHS_HIGHER_LOWS' else -1 if structure=='LOWER_HIGHS_LOWER_LOWS' else 0,1 if o['relationship']=='ABOVE' else -1 if o['relationship']=='BELOW' else 0,1 if o['levels']['last_close']>o['levels']['open'] else -1 if o['levels']['last_close']<o['levels']['open'] else 0]
        counts=[signs.count(x) for x in (1,-1,0)]
        ratios='\nINDICATOR SUPPORT: UP %.1f%% | DOWN %.1f%% | NEUTRAL %.1f%%.\nRATIO: %d:%d:%d (three fallback checks: structure, VWAP, session change; percentages count checks, not forecast probability).'%tuple([v/3*100 for v in counts]+counts)
        return 'SPY TREND: '+label+' | HISTORICAL PUBLIC BARS | '+scope+'\nNOT REAL-TIME — completed bars, not a current quote.\nObserved through '+(o['bar']+timedelta(minutes=5)).astimezone(ET).strftime('%Y-%m-%d %H:%M ET')+ratios+'\nLAST OBSERVED: $%.2f USD.'%o['levels']['last_close']+'\nEMA9/15m/30m checks unavailable; using the three named fallback checks.\nPublic five-minute data; delay unverified. /trend = percentages | /news = detailed research'
    return basic_text(r)

def changes(o,old,session,threshold=.3):
    """Compare only verified current-session observations, not old-session snapshots."""
    if not session['active'] or o['quality']!='PUBLIC_RESEARCH_ONLY' or old.get('quality')!='PUBLIC_RESEARCH_ONLY':return []
    if old.get('source',SOURCE)!=o.get('source',SOURCE):return []
    try:
        distance=(o['bar']-stamp(old['bar'])).total_seconds()
        if old['session_date']!=session['date'] or not 0<distance<=2100 or type(old['close']) not in (float,int) or not math.isfinite(old['close']) or old['close']<=0:return []
        out=[]
        if old['trend']!=o['trend']:
            out.append('Recent5m structure turned upward.' if o['trend']=='UPWARD 5m STRUCTURE' else 'Recent5m structure turned downward.' if o['trend']=='DOWNWARD 5m STRUCTURE' else 'Direction became mixed; the earlier structure is no longer aligned.')
        if old['relationship']=='BELOW' and o['relationship']=='ABOVE':out.append('SPY reclaimed approximate session VWAP between the two reported observations.')
        elif old['relationship']=='ABOVE' and o['relationship']=='BELOW':out.append('SPY lost approximate session VWAP between the two reported observations.')
        if old['labels']!=o['labels']:
            out.append('Observed close moved above the first15-minute opening range.' if 'CLOSE_ABOVE_OPENING_RANGE' in o['labels'] else 'Observed close moved below the first15-minute opening range.' if 'CLOSE_BELOW_OPENING_RANGE' in o['labels'] else 'Observed close returned inside the first15-minute opening range.')
        move=(o['levels']['last_close']/old['close']-1)*100
        if abs(move)>=threshold:out.append('Observed SPY price moved %+.2f%% since the prior report (%s ET).'%(move,stamp(old['bar']).astimezone(ET).strftime('%H:%M')))
        return out
    except (KeyError,TypeError,ValueError):return []

def change_text(o,highlights,now):
    l=o['levels'];label='UPWARD' if o['trend']=='UPWARD 5m STRUCTURE' else 'DOWNWARD' if o['trend']=='DOWNWARD 5m STRUCTURE' else 'MIXED / WAIT'
    lens='Call-side research lens only' if label=='UPWARD' else 'Put-side research lens only' if label=='DOWNWARD' else 'Neither call nor put side is favored'
    return '\n'.join(['SPY RESEARCH ALERT | '+now.astimezone(ET).strftime('%Y-%m-%d %H:%M ET'),'HISTORICAL PUBLIC BARS — NOT REAL-TIME; no current quote.','ACTION: NO TRADE — observation, not a buy/sell instruction.','WHAT CHANGED:']+['• '+x for x in highlights]+['BAR-BASED DIRECTION: '+label+' (recent5m structure).','OPTIONS VIEW: '+lens+'. No contract recommendation.','LAST OBSERVED: $%.2f USD | '%l['last_close']+o['bar'].astimezone(ET).strftime('%H:%M')+'-'+(o['bar']+timedelta(minutes=5)).astimezone(ET).strftime('%H:%M ET'),'Approx. VWAP $%.2f | session low $%.2f / high $%.2f.'%(l['bar_based_vwap_approx'],l['low'],l['high']),'REASSESS: Continuation can fail; a reversal or loss of alignment weakens the directional thesis.','DATA: Yahoo public5m bars; delay UNVERIFIED. No verified live option quotes or complete news coverage.','ENTRY / STOP / TARGET: Not issued. /setup = readiness | /news = full research | /premarket = morning outlook'])

def update(store, snapshot, session, config, publish, now=None):
    now = now or datetime.now(timezone.utc); c = settings(config)
    if not c['enabled']:
        store.put('research_notification_health', {'state':'DISABLED','at':now.isoformat()}); return None
    # Avoid overnight messages while retaining requested weekend/closed reviews.
    if not session['active'] and not 8 <= now.astimezone(ET).hour < 20:
        return None
    o = observe(snapshot, session, now)
    from news.market_outlook import build as outlook_build,text_for as outlook_text
    outlook=outlook_build(store,now,observation=o)
    news_context=[[x['url'],x['published_at'],x['direction']] for x in outlook['news']['items'][:4]]
    # New major news can be useful even when price bars are missing. Query time
    # alone cannot make a meaningful change or generate repeated outage alerts.
    signature = hashlib.sha256(json.dumps(['market-outlook-v1',o['quality'],o.get('reason'),o.get('trend'),o.get('relationship'),o.get('labels'),news_context,session['state'],session['date']], sort_keys=True).encode()).hexdigest()
    previous = store.get('automatic_research', {})
    highlights=changes(o,previous.get('observation',{}),session,c['move_alert_pct'])
    elapsed = (now-stamp(previous['at'])).total_seconds() if previous else float('inf')
    interval = c['regular_seconds'] if session['active'] else c['premarket_seconds'] if session['state']=='PREMARKET' else c['after_hours_seconds'] if session['state']=='AFTER_HOURS' else c['closed_seconds']
    changed = previous.get('signature') != signature or bool(highlights)
    store.put('research_notification_health', {'state':'ENABLED','at':now.isoformat(),'observation_quality':o['quality'],'interval_seconds':interval,'change_cooldown_seconds':c['change_seconds'],'last_queued_at':previous.get('at')})
    if elapsed < c['change_seconds'] or (not changed and elapsed < interval):
        return None
    if config.get('notifications',{}).get('profile')=='simple':
        from monitoring.simple_notifications import enabled
        allowed=enabled(config,'extended') if not session['active'] else (enabled(config,'changes') and changed or enabled(config,'periodic') and elapsed>=interval)
        if not allowed:return None
    # Unchanged outages get one notice per phase/day, not periodic outage spam.
    if o['quality']=='UNAVAILABLE' and not news_context and not changed:
        return None
    slot = int(now.timestamp())//c['change_seconds']
    event_id = 'research-brief-'+hashlib.sha256((signature+str(slot)).encode()).hexdigest()[:32]
    message=change_text(o,highlights,now) if highlights else short_text(o,session,now)
    # Keep the automatic feed focused on the same concise price/news view.
    # The original detailed technical formatter remains /research.
    message=outlook_text(outlook)
    if highlights:message+='\nCHANGED: '+' '.join(highlights)
    if config.get('notifications',{}).get('profile')=='simple':publish(store,event_id,message,'PRIVATE','owner',kind='RESEARCH')
    else:publish(store,event_id,message,kind='RESEARCH')
    # Persist only after atomic outbox publication; restarts retain the cooldown.
    store.put('automatic_research', {'at':now.isoformat(),'signature':signature,'event_id':event_id,'observation':context(o)})
    if highlights:store.put('latest_research_highlight',{'at':now.isoformat(),'event_id':event_id,'highlights':highlights,'action':'NO TRADE'})
    store.put('research_notification_health', {'state':'ENABLED','at':now.isoformat(),'observation_quality':o['quality'],'interval_seconds':interval,'change_cooldown_seconds':c['change_seconds'],'last_queued_at':now.isoformat()})
    store.audit(event_id,'public_research_notification','worker',{'quality':o['quality'],'session':session['state'],'action':'NO TRADE'})
    return event_id
