"""Concise semantic research messages; no price/odds inference in formatting."""
import math
from datetime import datetime, timezone
from core.sessions import ET, market_session
from data.models import stamp

HORIZONS = (('H60', 'Next 60m'), ('H120', 'Next 120m'), ('SESSION', 'Remaining session'))

def number(value, digits=2):
    if isinstance(value, bool) or value is None:
        return 'UNAVAILABLE'
    try:
        value = float(value)
        return f'{value:.{digits}f}' if math.isfinite(value) else 'UNAVAILABLE'
    except (TypeError, ValueError, OverflowError):
        return 'UNAVAILABLE'

def et(value, full=False):
    try:
        return stamp(value).astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET' if full else '%H:%M ET')
    except (TypeError, ValueError, KeyError):
        return 'UNAVAILABLE'

def plain(value, maximum=180):
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return 'UNAVAILABLE'
    return ' '.join(str(value).split())[:maximum] or 'UNAVAILABLE'

def measured(value, maximum=180, depth=0):
    """Render nested measured evidence as labeled values, never Python repr."""
    if value is None:
        result = 'UNAVAILABLE'
    elif isinstance(value, bool):
        result = 'yes' if value else 'no'
    elif isinstance(value, (int, float)):
        result = number(value, 4)
        if result != 'UNAVAILABLE':result = result.rstrip('0').rstrip('.') if '.' in result else result
    elif depth >= 4:
        result = 'additional measured detail retained locally'
    elif isinstance(value, dict):
        result = '; '.join(plain(key, 35) + '=' + measured(item, maximum, depth + 1) for key, item in value.items()) or 'no values recorded'
    elif isinstance(value, (list, tuple)):
        result = ', '.join(measured(item, maximum, depth + 1) for item in value) or 'none listed'
    else:
        result = plain(value, maximum)
    return result[:maximum]

def horizon_rows(horizons):
    if isinstance(horizons, list):
        return {row.get('horizon_id', row.get('id')): row for row in horizons if isinstance(row, dict)}
    return horizons if isinstance(horizons, dict) else {}

def horizon_bias(row):
    if not isinstance(row, dict):
        return 'UNAVAILABLE'
    bias = row.get('bias', row.get('direction'))
    return {'CALL': 'UP', 'PUT': 'DOWN', 'BULL': 'UP', 'BEAR': 'DOWN'}.get(bias, bias) if bias in ('UP', 'DOWN', 'MIXED', 'CALL', 'PUT', 'BULL', 'BEAR') else 'UNAVAILABLE'

def status_text(ctx, now, news, horizons=None, entry_reason=None):
    """A descriptive horizon never grants underlying or option entry eligibility."""
    from core.signals import quote_valid, option_quote_valid
    session = market_session(now)
    quote = ctx.get('quote') or {}
    source = plain(ctx.get('feed_quality', quote.get('feed_quality', 'UNAVAILABLE')), 30)
    source += ' single exchange' if source == 'IEX' else ''
    fresh_quote = quote_valid(quote, now, 5)
    bars = ctx.get('bar_research') or {}
    bar_price = number(bars.get('last_completed_close'))
    use_bar = not fresh_quote and bar_price != 'UNAVAILABLE'
    price = bar_price if use_bar else number((quote.get('payload') or {}).get('mid'))
    if use_bar:
        source = plain(bars.get('provider', 'UNAVAILABLE'), 35) + ' descriptive bar close'
    rows = horizon_rows(horizons or ctx.get('horizons'))
    lines = ['SPY ' + et(now.isoformat()) + ' · ' + price + ' USD [' + source + ']',
             ('Completed bar as-of ' + et(bars.get('source_timestamp')) + ' · not an executable quote' if use_bar else 'Quote as-of ' + et(quote.get('source_timestamp')) + (' · not entry-fresh' if not fresh_quote else ''))]
    if ctx.get('early'):lines.append('EARLY READ — limited opening-session evidence; at least 15 genuine completed bars.')
    for key, label in HORIZONS:
        row = rows.get(key) or {}
        lines.append(label + ': ' + horizon_bias(row) + (' — descriptive bars' if row else ' — evidence unavailable'))
    candidate = False
    if not session['active']:
        reason = 'market closed'
    elif ctx.get('reason'):
        reason = ctx.get('failed_predicate') or ctx['reason']
    elif not quote_valid(quote, now, 5):
        reason = 'fresh underlying quote unavailable'
    elif news.get('quality') != 'DATA_OK':
        reason = 'official calendar not verified'
    elif news.get('risk') not in ('NORMAL', 'MODERATE'):
        reason = 'event blackout active'
    else:
        reason = entry_reason or 'no confirmed qualifying setup'
        candidate = isinstance(reason, str) and reason.startswith(('BUY CALL idea', 'BUY PUT idea'))
    if candidate:
        side = 'CALL' if reason.startswith('BUY CALL') else 'PUT'
        lines.append('New entry: WATCH ONLY — ' + side + ' underlying setup confirmed; option research gates remain separate.')
    else:
        if isinstance(reason, str) and reason.startswith('NO TRADE — '):reason = reason[len('NO TRADE — '):]
        lines.append('New entry: WAIT — ' + plain(reason, 110))
    contract = ctx.get('option_contract') or {}
    if not option_quote_valid(contract.get('quote') or {}, now):
        lines.append('Watch only—option pricing unavailable.')
    if news.get('quality') != 'DATA_OK':
        lines.append('Event data warning: calendar unverified; entry ideas blocked.')
    lines += ['Bias is descriptive evidence, not odds or a trade instruction.',
              '/details · /why · /feed | Live signals and orders disabled.']
    return '\n'.join(lines)

def idea_text(idea, evidence, config):
    """Named prices remain distinct; a model price is never an actual fill."""
    from core.signals import option_quote_valid
    now = stamp(idea['timestamp'])
    direction = plain(idea.get('direction'), 8)
    trigger = idea.get('trigger_level', idea.get('trigger'))
    reference = idea.get('reference_midpoint', idea.get('spy_price'))
    horizon = idea.get('horizon_id', idea.get('horizon', 'UNAVAILABLE'))
    labels = {'H60': '60 minutes', 'H120': '120 minutes', 'SESSION': 'remaining session'}
    side = 'above' if direction == 'CALL' else 'below'
    lines = ['SPY ' + direction + ' IDEA (PAPER / UNVALIDATED)',
             'ID ' + plain(idea.get('signal_id'), 100) + ' · ' + labels.get(horizon, plain(horizon)),
             'SPY trigger: ' + side + ' ' + number(trigger) + '; ' + plain(idea.get('entry_condition', 'completed-candle confirmation required'), 110),
             'Reference midpoint: ' + number(reference) + ' USD; modeled fill: ' + number(idea.get('modeled_entry_fill')),
             'Entry valid until ' + et(idea.get('signal_expiry')),
             'SPY invalidation ' + number(idea.get('invalidation')) + ' · targets ' + number(idea.get('t1')) + ' / ' + number(idea.get('t2')),
             'Full-exit review by ' + et(idea.get('max_hold_until')) + '; stop/target may end earlier.']
    contract, plan = idea.get('option_contract') or {}, idea.get('option_plan') or {}
    if contract and plan and option_quote_valid(contract.get('quote') or {}, now):
        limit = plan.get('limit')
        lines += [plain(contract.get('symbol'), 30) + ' · option entry limit ' + number(limit) + ' USD/share',
                  'Premium at risk: ' + number(float(limit) * 100 if number(limit) != 'UNAVAILABLE' else None) + ' USD/contract, plus fees.']
        if plan.get('stop_bid') is not None:
            lines.append('Modeled stop premium ' + number(plan['stop_bid']) + '; estimate only, not maximum loss or an exit quote.')
    else:
        lines.append('Watch only—option pricing unavailable.')
    lines += ['Setup ' + plain(idea.get('setup_type'), 60) + ' · ' + plain(evidence.get('evidence_tag', 'INSUFFICIENT')) + ' (' + str(evidence.get('closed', 0)) + ' closed)',
              'Unvalidated research. You place orders yourself.']
    return '\n'.join(lines)

def diagnostics_text(ctx, now, news, horizons=None, extra=None):
    from core.directional_research import VERSION,view
    measured_view=view(ctx,now)
    lines = ['SPY RESEARCH DETAILS · ' + et(now.isoformat(), True),
             'Current trend rule '+VERSION+': completed close and 15m change must agree with session VWAP; disagreement = SIDEWAYS; missing inputs = DATA UNAVAILABLE.',
             'Forward outlook: conditional hypothesis with VWAP invalidation, exact H60/H120/session deadlines; not calibrated odds. Current trend '+measured_view['trend'],
             'New-entry predicate: ' + plain(ctx.get('failed_predicate') or ctx.get('reason') or 'underlying checks passed'),
             'Event gate: ' + plain(news.get('quality')) + ' / ' + plain(news.get('risk')),
             'Calendar verified ' + et(news.get('verified_at'), True) + '; coverage ' + et(news.get('coverage_through'), True)]
    for diagnostic in ctx.get('diagnostics') or []:
        if not isinstance(diagnostic, dict):
            continue
        signed = lambda value: ('%+.3f' % float(value)) if number(value) != 'UNAVAILABLE' else 'UNAVAILABLE'
        lines.append(plain(diagnostic.get('provider'), 30) + ': source age ' + signed(diagnostic.get('source_age_seconds')) + ' s; receipt age ' + signed(diagnostic.get('receipt_age_seconds')) + ' s; source−receipt skew ' + signed(diagnostic.get('source_receipt_skew_seconds')) + ' s; ' + plain(diagnostic.get('predicate') or 'PASS', 70))
    lines += ['Heartbeat age ' + number(ctx.get('heartbeat_age_seconds'), 3) + ' s (limit 30); bar-end age ' + number(ctx.get('bar_end_age_seconds'), 3) + ' s (limit 120).',
              'Frames: ' + ' · '.join(frame + ' ' + plain((ctx.get('features') or {}).get(frame, {}).get('trend', 'UNAVAILABLE'), 14) for frame in ('1m', '5m', '15m', '30m', '1h', 'daily')),
              'Opening range: ' + plain(ctx.get('opening_range_status', 'UNAVAILABLE')),
              'Confirmed-empty slots: ' + str(ctx.get('synthetic_continuity_minutes', 0)) + '; continuity only, excluded from indicators, volume and fills.']
    bars = ctx.get('bar_research') or {}
    lines.append('Completed-bar research: ' + plain(bars.get('quality')) + '; ' + plain(bars.get('reason') or 'no rejection recorded') + '; source ' + plain(bars.get('provider')) + '; as-of ' + et(bars.get('source_timestamp'), True))
    for key, row in horizon_rows(horizons or ctx.get('horizons')).items():
        if not isinstance(row, dict):
            continue
        frames = row.get('frames') or {}
        requirements = ' / '.join(plain(name, 12) + ' ' + plain(value, 14) for name, value in frames.items()) if isinstance(frames, dict) and frames else plain(row.get('reason') or row.get('frame_requirements') or row.get('required_frames'), 100)
        lines.append(plain(key, 20) + ': ' + horizon_bias(row) + '; version ' + plain(row.get('version', row.get('strategy_version')), 65) + '; cutoff ' + et(row.get('max_hold_until', row.get('exit_deadline'))) + '; frames ' + requirements)
    if extra:
        lines.extend(plain(line, 220) for line in extra if isinstance(line, str))
    return '\n'.join(lines + ['Entry validity, planned holding, actual exit and option expiry are different clocks.', 'No broker verification, calibrated win probability, live signal or order.'])[:3400]

def update_text(idea, condition):
    names = {'TARGET_1_HIT': 'Underlying target 1 reached; full-exit policy unchanged.',
             'TARGET_2_HIT': 'Underlying target 2 reached in the research model.',
             'STOP_HIT': 'Underlying invalidation reached in the research model.',
             'TIME_EXIT': 'Research holding deadline reached.',
             'ENTRY_TRIGGERED': 'Research entry condition triggered.',
             'NEWS_EXIT_REVIEW': 'Event risk changed; review monitoring and your own position.',
             'MONITORING_UNAVAILABLE': 'Monitoring unavailable; no exit or closed position inferred.',
             'IDEA_EXPIRED': 'Entry validity expired without a modeled entry.',
             'IDEA_CANCELLED': 'Research entry cancelled before modeled entry.'}
    return '\n'.join(['SPY ' + plain(idea.get('direction'), 8) + ' · ' + plain(idea.get('signal_id'), 100), names.get(condition, plain(condition, 130)), 'Unvalidated research. Research outcomes are separate from your private reported fills. No order placed.'])

def health_text(data, now):
    news, ntp = data.get('news') or {}, data.get('ntp_clock') or {}
    lines = ['AEGIS HEALTH · ' + et(now.isoformat()), 'Clock: ' + plain(ntp.get('state')) + '; NTP offset ' + number(ntp.get('offset_seconds'), 3) + ' s; skew limit ' + number(data.get('skew_budget_seconds'), 3) + ' s.']
    for name, row in (data.get('system') or {}).items():
        if isinstance(row, dict):
            lines.append(plain(name, 30) + ': ' + plain(row.get('state', row.get('status', 'UNAVAILABLE')), 50) + '; heartbeat ' + et(row.get('at')) + '; fresh ' + ('yes' if row.get('fresh_heartbeat') is True else 'not verified'))
    qt = data.get('questrade_health') or {}
    lines += ['Calendar: ' + plain(news.get('quality')) + '; stale ' + ('yes' if news.get('stale', True) else 'no') + '; coverage ' + et(news.get('coverage_through'), True), 'Questrade: ' + plain(qt.get('status', qt.get('state', 'QUESTRADE_NOT_CONFIGURED'))), 'Process existence is not data freshness. /details and /feed show exact checks.', 'LIVE_SIGNAL_READY=false; live signals and orders disabled.']
    return '\n'.join(lines)[:3400]

def interval(value):
    return number(value[0]) + ' to ' + number(value[1]) if isinstance(value, (list, tuple)) and len(value) == 2 else 'UNAVAILABLE'

def score_summary_text(summary):
    lines = ['SPY SCORE — UNDERLYING (not option P&L)',
             'Population: underlying ideas only; proxy trades, option paper and forward diagnostics are separate.',
             'Labels require 50 closed ideas per tested setup/variant. Multiple comparisons and overlapping outcomes limit these descriptive intervals.']
    for name, row in (summary.get('windows') or {}).items():
        lines.append(plain(name, 20) + ': ' + str(row.get('closed', 0)) + ' closed; ' + str(row.get('expired_no_entry', 0)) + ' expired without entry; mean R ' + number(row.get('average_r')) + '; 95% interval ' + interval(row.get('expectancy_ci95')) + '; ' + plain(row.get('evidence_tag'), 30))
    setups = summary.get('setups') or {}
    lines.append('Setups/variants being tested: ' + str(len(setups)) + '; apparent winners can arise by chance.')
    for name, row in list(setups.items())[:12]:
        lines.append(plain(name, 60) + ': ' + str(row.get('closed', 0)) + ' closed; ' + plain(row.get('evidence_tag'), 30))
    if len(setups) > 12:
        lines.append('Additional variants remain in the downloadable research report.')
    baseline, paired = summary.get('random_direction_baseline') or {}, summary.get('paired_baseline_comparison') or {}
    lines += ['Matched-clock random-direction baseline: ' + str(baseline.get('closed', 0)) + ' closed; not random entry times.',
              'Closed pairs ' + str(paired.get('closed_pairs', 0)) + '; mean difference ' + number(paired.get('mean_difference_r')) + ' R; 95% interval ' + interval(paired.get('ci95')) + '.',
              'Underlying evidence cannot establish option profitability or enable live signals.']
    return '\n'.join(lines)[:3400]

def paper_summary_text(ideas, option_positions, proxy, accuracy, diagnostics=None):
    total = ideas.get('all') or {}
    option_closed = [row for row in option_positions if row.get('status') == 'CLOSED']
    option_open = sum(row.get('status') == 'OPEN' for row in option_positions)
    underlying, baseline = proxy.get('proxy') or {}, proxy.get('matched_clock_random_direction_baseline') or {}
    diagnostic = diagnostics or {}
    lines = ['PAPER / UNVALIDATED — separate populations',
             'Underlying ideas = setup observations, not option trades: ' + str(total.get('total', 0)) + ' tracked; ' + str(total.get('closed', 0)) + ' closed.',
             'Underlying proxy = separate modeled SPY shares: ' + str(underlying.get('closed', 0)) + ' closed / ' + str(underlying.get('open', 0)) + ' open; mean ' + number(underlying.get('mean_usd_per_share')) + ' USD/share.',
             'Proxy matched-clock random-direction baseline: ' + str(baseline.get('closed', 0)) + ' closed; mean ' + number(baseline.get('mean_usd_per_share')) + ' USD/share.',
             'Real-quote option paper = genuine bid/ask simulation: ' + str(len(option_closed)) + ' closed / ' + str(option_open) + ' open.']
    if not option_positions:
        lines.append('No option paper trades. Option performance unavailable.')
    for row in option_positions[-3:]:
        lines.append(plain(row.get('contract'), 30) + ': ' + plain(row.get('status'), 20) + '; net ' + number(row.get('pnl_usd')) + ' USD (real-quote paper only).')
    lines += ['Forward diagnostics = candidate evaluations, not trades: ' + str(diagnostic.get('evaluations', 0)) + ' retained evaluations; ' + str(diagnostic.get('outcomes', 0)) + ' outcome records. Counts include unavailable legacy inputs, never proof of evidence.',
              'Premium-model accuracy = sampled model errors: ' + str((accuracy.get('overall') or {}).get('n', 0)) + ' observations; not strategy validation.',
              'Your private user-reported fills are separate and not broker verified.',
              '/score shows underlying outcomes; daily_reports/PAPER_PERFORMANCE.md has detailed populations.',
              'No live signals or orders. No claim of profitability.']
    return '\n'.join(lines)

def position_review_text(position, condition, plan, underlying, option_quote, now):
    """Private user-reported holding review, never a claimed execution or closure."""
    from core.signals import quote_valid, option_quote_valid
    underlying = underlying or {};option_quote = option_quote or {};plan = plan or {}
    px = (underlying.get('payload') or {}).get('mid') if quote_valid(underlying, now, 5) else None
    bid = (option_quote.get('payload') or {}).get('bid') if option_quote_valid(option_quote, now) else None
    lines = ['PRIVATE POSITION REVIEW · ' + plain(position.get('contract'), 30), plain(condition, 170),
             'SPY ' + number(px) + ' · option bid ' + number(bid) + ' USD/share',
             'SPY invalidation ' + number(plan.get('invalidation')) + '; targets ' + number(plan.get('t1')) + ' / ' + number(plan.get('t2')),
             'Your review deadline: ' + et(plan.get('max_hold_until'))]
    if px is None or bid is None:
        lines.append('Monitoring limited: missing current prices; no exit or position closure inferred.')
    lines.append('User-reported holding, not broker verified. Full-exit/manual review only; no order placed.')
    return '\n'.join(lines)

# Production defaults use the bounded owner experience; diagnostics stay above.
from monitoring.owner_messages import status_text, idea_text, update_text
