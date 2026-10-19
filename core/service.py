"""Local research status. No credentials, broker adapter, or order endpoints."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ET = ZoneInfo('America/New_York')

def read(name, default=None):
    p = ROOT / name
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default

def market(now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(ET)
    calendar = read('data/tsx_calendar.json')
    day = now.date().isoformat()
    if now.year != calendar['year']:
        status = 'CALENDAR_REFRESH_REQUIRED'
    elif now.weekday() >= 5 or day in calendar['closed']:
        status = 'CLOSED'
    else:
        end = calendar['early_close'].get(day, '16:00')
        status = 'REGULAR_SESSION' if '09:30' <= now.strftime('%H:%M') < end else 'OUTSIDE_REGULAR_SESSION'
    return {'status': status, 'local_time': now.isoformat(), 'timezone': str(ET), 'calendar_source': calendar['source']}

def snapshot(now=None):
    now = now or datetime.now(timezone.utc)
    account = read('account_snapshot.json', {})
    try:
        observed = datetime.fromisoformat(account['observed_at'])
        if observed.tzinfo is None:raise ValueError('AWARE_TIMESTAMP_REQUIRED')
        age = (now - observed).total_seconds()
    except (KeyError,TypeError,ValueError):age = None
    state = read('system_state.json', {})
    return {'generated_at': now.isoformat(), 'market': market(now),
        'mode': 'RESEARCH_AND_MANUAL_REVIEW', 'live_execution_enabled': False,
        'account': {'last_observed_equity_cad': account.get('equity_cad'),
                    'observed_at': account.get('observed_at'),
                    'fresh': age is not None and 0 <= age <= 300, 'reconciled': account.get('reconciled', False)},
        'blockers': state.get('blockers', []),
        'policy': read('research/revised_owner_policy.json'),
        'learning': read('research/learning_queue.json'),
        'briefing': read('research/latest_briefing.json', {}),
        'schedules': read('monitoring/schedules.json', []),
        'telegram': {'configured': state.get('telegram', {}).get('configured', False),
                     'bot': read('config/telegram.json', {}).get('username', 'UNCONFIGURED'), 'latest': notification_status()},
        'proposals': proposal_status(),
        'ledger': {'status': 'AWAITING_FRESH_RECONCILED_INITIALIZATION', 'protected_cash_cad': None},
        'strategies': read('research/strategy_registry.json', {})}

def notification_status():
    files = sorted((ROOT / 'logs/notifications').glob('*.json'), key=lambda p:p.stat().st_mtime, reverse=True)
    return [json.loads(p.read_text()) for p in files[:5]]

def proposal_status():
    files = sorted((ROOT / 'research/proposals').glob('*.json'), key=lambda p:p.stat().st_mtime, reverse=True)
    return [json.loads(p.read_text()) for p in files[:10]]

def review():
    result = snapshot()
    result['review_scope'] = 'Readiness and session review; no new market quote or strategy evidence inferred'
    target = ROOT / 'logs/reviews'
    target.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
    (target/name).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
