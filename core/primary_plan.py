"""One immutable public research plan; private reported holdings stay separate."""
from data.models import stamp
VERSION='primary-plan-v1'
KEY='primary-research-plan:v1'
ACTIVE=('OPEN','PENDING')

def current(store,rows,now):
    saved=store.get(KEY) or {};by={r['signal_id']:r for r in rows}
    row=by.get(saved.get('signal_id'))
    if row is None or row.get('status') not in ACTIVE:
        # Adopt an already alerted active plan after an upgrade/restart. Never
        # erase older overlapping research history or manufacture a user fill.
        row=next(iter(sorted((r for r in rows if r.get('alerted') and r.get('status') in ACTIVE),key=lambda r:r['timestamp'])),None)
    return row

def reserve(store,idea,now):
    value={'version':VERSION,'signal_id':idea['signal_id'],'reserved_at':now.isoformat(),
        'holding_deadline':idea['max_hold_until'],'entry_expiry':idea['signal_expiry'],
        'meaning':'UNDERLYING_RESEARCH_ONLY; no personal fill or option eligibility'}
    store.put(KEY,value)
    return value

def state(plan,now):
    if not plan:return 'WAIT'
    if plan.get('status') not in ACTIVE:return 'EXIT CONDITION REACHED'
    if now>=stamp(plan['max_hold_until']):return 'EXIT CONDITION REACHED'
    return 'HOLD' if plan.get('status')=='OPEN' else 'ENTRY CONFIRMED' if plan.get('entry_mode')=='ENTER NOW' else 'WAIT'
