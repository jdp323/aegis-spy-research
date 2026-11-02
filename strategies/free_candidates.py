"""Frozen deterministic H60 challengers. Detection never grants entry authority.

Only this arithmetic is shared by prospective shadow evaluation and offline
replay. Availability and execution assumptions remain explicit at each caller.
No model, broker operation, runtime database or transport is used here.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import statistics

from core.sessions import ET, market_session
from data.models import finite, stamp
from features.indicators import calculate, ema, normalize, resample

RULE_PATH = Path(__file__).resolve().parents[1] / 'research/FREE_CANDIDATE_RULES_2026-11-01.json'
RULES = json.loads(RULE_PATH.read_text(encoding='utf-8'))
VERSION = RULES['version']
RULE_HASH = hashlib.sha256(json.dumps(RULES, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
FAMILIES = tuple(RULES['candidate_families'])


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _view(bars, now, feed, provider, simulation, availability_mode):
    if now.tzinfo is None:
        raise ValueError('AWARE_TIME_REQUIRED')
    if feed not in ('IEX', 'SIP') or provider != 'alpaca-' + feed.lower():
        raise ValueError('MATCHING_EXPLICIT_FEED_PROVENANCE_REQUIRED')
    if availability_mode not in ('RECORDED_RECEIPT', 'RETROSPECTIVE_CLOSE_ONLY'):
        raise ValueError('AVAILABILITY_MODE_REQUIRED')
    for row in bars:
        if any(row.get(k) for k in ('synthetic', 'continuity_only', 'indicative', 'delayed')):
            raise ValueError('NON_GENUINE_INPUT')
        if row.get('provider', provider) != provider or row.get('feed_quality', feed) != feed:
            raise ValueError('MIXED_FEED_INPUT')
    rows = []
    for row in bars:
        available = row.get('recorded_at', row.get('available_at'))
        if available and availability_mode == 'RECORDED_RECEIPT' and stamp(available) > now:
            continue
        rows.append(row)
    normalized = normalize(rows, now=now, simulation=simulation)
    today = [b for b in normalized if datetime.fromtimestamp(b['timestamp'], timezone.utc).astimezone(ET).date() == now.astimezone(ET).date()]
    if not market_session(now)['active']:
        return today, 'OUTSIDE_REGULAR_SESSION'
    if not today:
        return today, 'GENUINE_COMPLETED_MINUTES_UNAVAILABLE'
    opening = now.astimezone(ET).replace(hour=9, minute=30, second=0, microsecond=0).timestamp()
    expected = list(range(int(opening), int(today[-1]['timestamp']) + 60, 60))
    if [b['timestamp'] for b in today] != expected:
        return today, 'GENUINE_SESSION_PREFIX_GAP'
    age = now.timestamp() - today[-1]['timestamp'] - 60
    if not 0 <= age <= RULES['bars_max_end_age_seconds']:
        return today, 'COMPLETED_BAR_AGE'
    return today, None


def _strict_gate(entry_gate, quote, now, feed, provider, simulation, availability_mode):
    """Require an actual observed_context result, not a truthy convenience flag.

    This returns underlying data eligibility only. Calendar/risk and option
    checks remain independent, and all candidates remain shadow observations.
    """
    if simulation or availability_mode != 'RECORDED_RECEIPT':
        return False, 'SHADOW_OR_RETROSPECTIVE_ONLY'
    if not isinstance(entry_gate, dict) or entry_gate.get('evaluated_at') is None:
        return False, 'STRICT_OBSERVED_CONTEXT_REQUIRED'
    try:
        if not 0 <= (now - stamp(entry_gate['evaluated_at'])).total_seconds() <= 1:
            return False, 'STRICT_CONTEXT_NOT_CURRENT'
    except (ValueError, TypeError):
        return False, 'STRICT_CONTEXT_CLOCK_INVALID'
    if entry_gate.get('reason') or entry_gate.get('failed_predicate'):
        return False, entry_gate.get('failed_predicate') or 'STRICT_DATA_GATE_BLOCKED'
    if entry_gate.get('feed_quality') != feed or entry_gate.get('quote') != quote:
        return False, 'STRICT_CONTEXT_SOURCE_MISMATCH'
    from core.signals import quote_valid
    if quote.get('provider') != provider or not quote_valid(quote, now, 5):
        return False, 'STRICT_QUOTE_INVALID'
    if not entry_gate.get('bars') or not entry_gate.get('features'):
        return False, 'STRICT_CONTEXT_BARS_UNAVAILABLE'
    return True, None


def evaluate_shadow(bars, now, *, feed, provider, quote=None, entry_gate=None,
                    simulation=False, availability_mode='RECORDED_RECEIPT'):
    """Return two separate shadow decisions from one genuine completed prefix.

    ``bars`` uses the existing minute OHLCV schema, optionally retaining
    ``recorded_at``. An absent quote never fabricates a midpoint. The completed
    close remains an explicitly labeled reference. No function mutates state.
    """
    out = {'version': VERSION, 'rule_hash': RULE_HASH, 'evaluated_at': now.isoformat(),
           'feed': feed, 'provider': provider, 'availability_mode': availability_mode,
           'population': 'SEPARATE_SHADOW_CANDIDATES', 'broadcast': False,
           'live_ready': False, 'option_eligible': False, 'candidates': [],
           'decisions': [], 'reason': None, 'snapshot_id': None}
    try:
        today, reason = _view(bars, now, feed, provider, simulation, availability_mode)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        out['reason'] = str(error) if isinstance(error, ValueError) else 'MALFORMED_INPUT'
        return out
    out['snapshot_id'] = _digest([feed, provider, today])[:32]
    out['genuine_minutes'] = len(today)
    if reason:
        out['reason'] = reason
        return out
    lower = resample(today, 5)
    if len(lower) < 4:
        out['reason'] = 'FOUR_GENUINE_COMPLETED_5M_CANDLES_REQUIRED'
        return out
    confirmation = datetime.fromtimestamp(lower[-1]['timestamp'] + 300, timezone.utc)
    out['bar_end_at'] = datetime.fromtimestamp(today[-1]['timestamp'] + 60, timezone.utc).isoformat()
    out['confirmation_at'] = confirmation.isoformat()
    if not 0 <= (now - confirmation).total_seconds() <= RULES['confirmation_max_age_seconds']:
        out['reason'] = 'NO_NEW_COMPLETED_5M_CONFIRMATION'
        return out
    # A later genuine minute cannot silently alter a previous 5m trigger.
    if today[-1]['timestamp'] + 60 != confirmation.timestamp():
        out['reason'] = 'WAIT_FOR_NEXT_5M_CONFIRMATION'
        return out
    last, prev = lower[-1], lower[-2]
    features = calculate(today)
    atr = features.get('atr14'); vwap = features.get('vwap_approx')
    ema9 = features.get('ema9'); ema21 = features.get('ema21')
    endpoint = next((b for b in today if b['timestamp'] == today[-1]['timestamp'] - 900), None)
    if not endpoint or not all(finite(x) and x > 0 for x in (atr, vwap, ema9, ema21)):
        out['reason'] = 'TREND_ATR_VWAP_OR_EXACT_ENDPOINT_UNAVAILABLE'
        return out
    volume = statistics.mean(b['volume'] for b in lower[-4:-1])
    if volume <= 0 or last['volume'] < 1.2 * volume:
        out['reason'] = 'COMPLETED_5M_VOLUME_CONFIRMATION_MISSING'
        return out
    close = today[-1]['close']; delta = close - endpoint['close']
    direction = 'CALL' if close > ema9 > ema21 and close > vwap and delta > 0 else 'PUT' if close < ema9 < ema21 and close < vwap and delta < 0 else None
    if not direction:
        out['reason'] = 'DIRECTIONAL_TREND_CONFLICT'
        return out
    sign = 1 if direction == 'CALL' else -1
    deadline = confirmation + timedelta(minutes=RULES['holding_minutes'])
    session = market_session(now)
    cutoff = now.astimezone(ET).replace(hour=session['close_minute'] // 60,
        minute=session['close_minute'] % 60, second=0, microsecond=0) - timedelta(minutes=RULES['close_buffer_minutes'])
    if deadline > cutoff:
        out['reason'] = 'FULL_H60_DOES_NOT_FIT_SESSION'
        return out
    expiry = confirmation + timedelta(seconds=RULES['entry_expiry_seconds_after_confirmation'])
    if now >= expiry:
        out['reason'] = 'NEW_ENTRY_EXPIRED'
        return out
    gate, gate_reason = _strict_gate(entry_gate, quote or {}, now, feed, provider, simulation, availability_mode)
    qmid = (quote or {}).get('payload', {}).get('mid')
    # The frozen candidate levels always use the completed close. A current
    # quote is a separate eligibility observation, never a silently moving plan.
    reference = close
    if gate and (not finite(qmid) or abs(qmid - close) > .5 * atr):
        gate, gate_reason = False, 'QUOTE_AWAY_FROM_CONFIRMATION'
    structural = min(b['low'] for b in lower[-2:]) if sign == 1 else max(b['high'] for b in lower[-2:])
    structural_distance = (reference - structural) * sign
    risk = max(structural_distance, .5 * atr)
    if structural_distance <= 0 or reference - sign * risk <= 0:
        out['reason'] = 'INVALID_STRUCTURAL_RISK'
        return out
    boundary = max(b['high'] for b in today[:15]) if sign == 1 else min(b['low'] for b in today[:15])
    orb = len(today[:15]) == 15 and (prev['close'] - boundary) * sign <= 0 < (last['close'] - boundary) * sign
    five_close = [b['close'] for b in lower]
    e5 = ema(five_close, 9); e5prev = ema(five_close[:-1], 9)
    higher = resample(today, 15)
    pullback = False
    if e5 and e5prev and len(higher) >= 2 and len(lower) >= 3:
        touch = prev['low'] <= e5prev[-1] if sign == 1 else prev['high'] >= e5prev[-1]
        trigger = prev['high'] if sign == 1 else prev['low']
        pullback = ((prev['close'] - lower[-3]['close']) * sign < 0 and touch
                    and (last['close'] - trigger) * sign > 0
                    and (last['close'] - e5[-1]) * sign > 0
                    and (higher[-1]['close'] - higher[-2]['close']) * sign > 0
                    and (higher[-1]['close'] - vwap) * sign > 0)
    for family, confirmed, trigger in [('ORB_5M', orb, boundary),
            ('PULLBACK_5M_15M', pullback, prev['high'] if sign == 1 else prev['low'])]:
        out['decisions'].append({'family': family, 'direction': direction,
            'confirmation': confirmed, 'reason': None if confirmed else 'NEW_CROSS_OR_PULLBACK_NOT_CONFIRMED'})
        if not confirmed:
            continue
        ident = _digest([RULE_HASH, family, direction, now.astimezone(ET).date().isoformat(), confirmation.isoformat(), trigger])[:24]
        candidate = {'signal_id': ident, 'strategy_version': VERSION, 'rule_hash': RULE_HASH,
            'snapshot_id': out['snapshot_id'], 'population': 'SEPARATE_SHADOW_CANDIDATES',
            'setup_type': family, 'direction': direction, 'horizon_id': 'H60',
            'confirmation_timeframe': '5m', 'confirmation_at': confirmation.isoformat(),
            'timestamp': now.astimezone(timezone.utc).isoformat(), 'trigger': trigger,
            'confirmation_close': close, 'reference_price': reference,
            'reference_basis': 'COMPLETED_CONFIRMATION_CLOSE_RESEARCH_ONLY',
            'reference_bid': (quote or {}).get('payload', {}).get('bid') if gate else None,
            'reference_ask': (quote or {}).get('payload', {}).get('ask') if gate else None,
            'reference_source_at': (quote or {}).get('source_timestamp') if gate else confirmation.isoformat(),
            'modeled_fill': None, 'actual_fill': None, 'invalidation': reference - sign * risk,
            't1': reference + sign * risk, 't2': reference + sign * 2 * risk,
            'risk_distance': risk, 'atr': atr, 'do_not_chase': reference + sign * .5 * atr,
            'entry_limit_kind': 'CEILING' if sign == 1 else 'FLOOR',
            'signal_expiry': expiry.isoformat(), 'max_hold_until': deadline.isoformat(),
            'strict_underlying_data_eligible': gate, 'strict_data_reason': gate_reason,
            'entry_eligible': False, 'entry_reason': 'SHADOW_ONLY; CALENDAR_RISK_AND_PUBLICATION_GATES_STILL_REQUIRED',
            'option_eligible': False, 'option_performance': 'NOT_MEASURED',
            'broadcast': False, 'live_ready': False}
        out['candidates'].append(candidate)
    if not out['candidates']:
        out['reason'] = 'NO_NEW_CANDIDATE_CONFIRMATION'
    return out
