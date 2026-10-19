"""Session-bounded private review plans; never broker orders or inferred exits."""
from datetime import datetime, timedelta, timezone
from core.sessions import ET, market_session

VERSION = 'private-intraday-review-v2'

def review_deadline(now, expiry, minutes):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('AWARE_TIME_REQUIRED')
    local = now.astimezone(ET)
    expiry_day = datetime.fromisoformat(expiry).date()
    if expiry_day < local.date():
        return {'allowed': False, 'reason': 'Contract expiry has passed; manually reconcile the reported holding. No settlement, exercise or closure is inferred.'}
    session = market_session(now)
    if session.get('quality') != 'DATA_OK':
        return {'allowed': False, 'reason': 'Verified US exchange calendar unavailable for ' + str(local.year) + '; refresh the official exchange calendar before creating a new review plan.'}
    if not session['active']:
        return {'allowed': False, 'reason': 'Current US session is ' + session['state'] + '; new intraday review plans require an active verified regular session.'}
    cutoff = local.replace(hour=session['close_minute'] // 60, minute=session['close_minute'] % 60, second=0, microsecond=0) - timedelta(minutes=5)
    if now >= cutoff:
        return {'allowed': False, 'reason': 'Intraday review cutoff ' + cutoff.strftime('%H:%M ET') + ' has been reached (verified session close minus five minutes).'}
    requested = now + timedelta(minutes=minutes)
    deadline = min(requested, cutoff)
    return {'allowed': True, 'deadline': deadline.astimezone(timezone.utc).isoformat(),
            'session_cutoff': cutoff.astimezone(timezone.utc).isoformat(), 'shortened': requested > cutoff,
            'calendar_version': session['calendar_version'], 'policy_version': VERSION}
