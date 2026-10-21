"""Versioned completed-price trend and explicitly uncalibrated future hypotheses."""
from datetime import datetime, timezone, timedelta
from core.sessions import ET, market_session
from data.models import finite, stamp

VERSION = 'completed-vwap-change15-v1'
FORECAST_VERSION = 'conditional-direction-v1'

def view(ctx, now):
    bar = ctx.get('bar_research') or {}
    # Early reads retain their explicit smaller sample, never borrow old quotes.
    usable = not bar.get('reason') and bar.get('quality') == 'COMPLETED_BAR_RESEARCH_ONLY'
    early = ctx.get('early') and not ctx.get('reason')
    rows = bar.get('bars', []) if usable else ctx.get('bars', []) if early else []
    fs = bar.get('features', {}) if usable else ctx.get('features', {}) if early else {}
    out = dict(version=VERSION, trend='DATA UNAVAILABLE', price=None, as_of=None,
               provider=bar.get('feed_quality') or ctx.get('feed_quality', 'UNAVAILABLE'),
               reason='completed current-session prices unavailable', invalidation=None,
               outlooks={})
    if len(rows) < 15 or not market_session(now)['active']:return out
    last = rows[-1]; age = now.timestamp() - last['timestamp'] - 60
    tail = rows[-16:]
    if not 0 <= age <= 120 or any(b['timestamp']-a['timestamp'] != 60 for a,b in zip(tail,tail[1:])):return out
    price = last['close']; vwap = fs.get('1m', {}).get('vwap_approx')
    if not finite(vwap) or vwap <= 0:return out
    change = price - tail[0]['close']
    trend = 'UP' if price > vwap and change > 0 else 'DOWN' if price < vwap and change < 0 else 'SIDEWAYS'
    source = datetime.fromtimestamp(last['timestamp']+60, timezone.utc).isoformat()
    out.update(trend=trend, price=price, as_of=source, invalidation=vwap,
               reason='completed close versus session VWAP and 15-minute change', limited=bool(early))
    session = market_session(now)
    close = now.astimezone(ET).replace(hour=session['close_minute']//60, minute=session['close_minute']%60, second=0,microsecond=0)
    for key, end in [('H60', now+timedelta(minutes=60)), ('H120', now+timedelta(minutes=120)), ('SESSION', close)]:
        supported = end <= close and end > now
        out['outlooks'][key] = dict(version=FORECAST_VERSION, bias=trend if supported else 'ABSTAIN',
            target_at=end.isoformat() if supported else None, reference=price, invalidation=vwap,
            label='conditional hypothesis; not a calibrated forecast', reason=None if supported else 'insufficient session time')
    return out

def record(store, ident, issued, research, horizon, premarket=False):
    """Append at issuance, including abstentions. Never update a forecast in place."""
    item = (research.get('outlooks') or {}).get(horizon, {})
    payload = dict(id=ident, version=FORECAST_VERSION, issued_at=issued.isoformat(),
        horizon=horizon, bias=item.get('bias','ABSTAIN'), reference=item.get('reference'),
        invalidation=item.get('invalidation'), target_at=item.get('target_at'),
        reference_at=research.get('as_of'), reference_rule='REGULAR_OPEN' if premarket else 'ISSUE_TIME_COMPLETED_PRICE',
        outcome_rule='REGULAR_SESSION_LAST_MINUTE_CLOSE' if horizon in ('SESSION','PREMARKET') else 'EXACT_COMPLETED_MINUTE_CLOSE',
        provider=research.get('provider','UNAVAILABLE'), calibrated=False)
    created=store.event('forecast:'+ident, 'directional_forecast', payload)
    if created and horizon in ('H60','H120') and payload['target_at'] and payload['bias'] in ('UP','DOWN'):
        pending=[p for p in store.get('directional_future_targets',[]) if stamp(p['target_at'])+timedelta(seconds=5)>=issued]
        store.put('directional_future_targets',(pending+[payload])[-128:])
    if created and not payload['target_at']:
        key='forecast-outcome:'+ident
        store.event(key,'directional_forecast_outcome',dict(forecast_id=ident,status='ABSTAIN',reason='no eligible future horizon',correct=None))
        store.put(key,{'at':issued.isoformat()})
    return payload

def capture_future_quote(store, quote, received):
    """The stream captures the future reference, not the slower analysis loop.

    This is observation only: no new subscription, entry eligibility or order.
    A 0–5s forward sampling window is disclosed; never use a quote before target.
    """
    from core.signals import quote_valid
    if not quote_valid(quote,received,5):return
    source=stamp(quote['source_timestamp'])
    for row in store.get('directional_future_targets',[]):
        key='forecast-outcome:'+row['id']
        feed=quote.get('feed_quality') or {'alpaca-iex':'IEX','alpaca-sip':'SIP','alpaca':'SIP'}.get(quote.get('provider'))
        if row.get('provider')!=feed or store.get(key):continue
        if not 0<=(source-stamp(row['target_at'])).total_seconds()<=5:continue
        ref=row.get('reference');px=quote.get('payload',{}).get('mid')
        if not finite(ref) or not finite(px):continue
        actual='UP' if px>ref else 'DOWN' if px<ref else 'SIDEWAYS'
        value=dict(forecast_id=row['id'],resolved_at=received.isoformat(),target_at=row['target_at'],
            status='RESOLVED',reference=ref,outcome_close=px,outcome_source=quote['source_timestamp'],
            actual=actual,correct=actual==row['bias'],sample_window_seconds=5,option_performance='UNAVAILABLE')
        store.event(key,'directional_forecast_outcome',value);store.put(key,{'at':received.isoformat()})

def resolve(store, bars, now, quote=None):
    """Exact future prices only; no nearest-bar substitution or option P&L."""
    for row in store.events('directional_forecast',1000):
        key='forecast-outcome:'+row['id']
        if store.get(key):continue
        target=row.get('target_at')
        if not target:continue
        end=stamp(target); issued=stamp(row['issued_at'])
        if end <= issued or now < end:continue
        wanted=end.timestamp()-60
        b=next((b for b in bars if b['timestamp']==wanted),None)
        reference=row.get('reference');outcome_source=None;outcome_price=b['close'] if b else None
        if row['horizon'] in ('H60','H120') and quote:
            from core.signals import quote_valid
            if quote_valid(quote,now,5):
                source=stamp(quote['source_timestamp'])
                if 0<=(source-end).total_seconds()<=5:
                    outcome_price=quote['payload']['mid'];outcome_source=quote['source_timestamp']
        if outcome_price is None and now<end+timedelta(seconds=5):continue
        if row['reference_rule']=='REGULAR_OPEN':
            opening=end.astimezone(ET).replace(hour=9,minute=30,second=0,microsecond=0).timestamp()
            first=next((b for b in bars if b['timestamp']==opening),None)
            reference=first['open'] if first else None
        status='ABSTAIN' if row['bias'] in ('ABSTAIN','SIDEWAYS','DATA UNAVAILABLE') else 'RESOLVED' if outcome_price is not None and finite(reference) else 'MISSING_OUTCOME'
        actual='UP' if outcome_price is not None and finite(reference) and outcome_price>reference else 'DOWN' if outcome_price is not None and finite(reference) and outcome_price<reference else 'SIDEWAYS' if outcome_price is not None and finite(reference) else None
        outcome=dict(forecast_id=row['id'],resolved_at=now.isoformat(),target_at=target,status=status,
            reference=reference,outcome_close=outcome_price,outcome_source=outcome_source,actual=actual,
            correct=(actual==row['bias']) if status=='RESOLVED' else None,option_performance='UNAVAILABLE')
        store.event(key,'directional_forecast_outcome',outcome);store.put(key,{'at':now.isoformat()})
