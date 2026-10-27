"""One immutable public research plan; private reported holdings stay separate."""
from data.models import stamp
VERSION='primary-plan-v2-explicit-unresolved'
KEY='primary-research-plan:v1'
ACTIVE=('OPEN','PENDING')

def current(store,rows,now):
    saved=store.get(KEY) or {};retired=set(store.get('primary-admin-closures:v1',[]));by={r['signal_id']:r for r in rows if r['signal_id'] not in retired}
    row=by.get(saved.get('signal_id'))
    if row is None or row.get('status') not in ACTIVE:
        # Adopt an already alerted active plan after an upgrade/restart. Never
        # erase older overlapping research history or manufacture a user fill.
        row=next(iter(sorted((r for r in rows if r['signal_id'] not in retired and r.get('alerted') and r.get('status') in ACTIVE),key=lambda r:r['timestamp'])),None)
    return row

def reserve(store,idea,now):
    value={'version':VERSION,'signal_id':idea['signal_id'],'reserved_at':now.isoformat(),
        'holding_deadline':idea['max_hold_until'],'entry_expiry':idea['signal_expiry'],
        'meaning':'UNDERLYING_RESEARCH_ONLY; no personal fill or option eligibility'}
    store.put(KEY,value)
    return value

def state(plan,now):
    if not plan:return 'WAIT'
    if plan.get('coverage_status')=='UNRESOLVED_GAP':return 'UNRESOLVED'
    if plan.get('status') is None:
        if now>=stamp(plan['max_hold_until']):return 'UNRESOLVED'
        return 'ENTRY CONFIRMED' if plan.get('entry_mode')=='ENTER NOW' else 'WAIT'
    if plan.get('status') in ('EXPIRED','EXPIRED_NO_ENTRY','CANCELLED'):return 'EXPIRED/CANCELLED'
    if plan.get('status') not in ACTIVE:return 'EXIT CONDITION REACHED'
    if now>=stamp(plan['max_hold_until']):return 'UNRESOLVED'
    return 'HOLD' if plan.get('status')=='OPEN' else 'ENTRY CONFIRMED' if plan.get('entry_mode')=='ENTER NOW' else 'WAIT'

def administrative_close(store,rows,ident,reason,now):
    """Release a research slot explicitly, without editing observations or fills."""
    if not reason or len(reason)>240:raise ValueError('EXPLICIT_REASON_REQUIRED')
    plan=current(store,rows,now)
    if not plan or plan['signal_id']!=ident:raise ValueError('NOT_CURRENT_PRIMARY')
    if state(plan,now)!='UNRESOLVED':raise ValueError('ONLY_UNRESOLVED_ADMIN_CLOSURE')
    value={'signal_id':ident,'at':now.isoformat(),'reason':reason,'status':'ADMINISTRATIVELY_CANCELLED','observed_exit':False,'pnl':None,'private_holdings_unchanged':True}
    if store.event('primary-admin-close:'+ident,'primary_admin_closure',value):
        store.put('primary-admin-closures:v1',store.get('primary-admin-closures:v1',[])+[ident])
    return value
