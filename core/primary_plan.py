"""One immutable public research plan; private reported holdings stay separate."""
from data.models import stamp
from datetime import timedelta
VERSION='primary-plan-v3-bounded-administrative-end'
KEY='primary-research-plan:v1'
ACTIVE=('OPEN','PENDING')
ADMIN_GRACE_SECONDS=300

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
        'administrative_end':administrative_end(idea).isoformat(),
        'meaning':'UNDERLYING_RESEARCH_ONLY; no personal fill or option eligibility'}
    store.put(KEY,value)
    return value

def administrative_end(plan):
    """Fixed five-minute evidence grace; this never extends entry or holding."""
    return stamp(plan['max_hold_until'])+timedelta(seconds=ADMIN_GRACE_SECONDS)

def public_state(plan,now,monitoring_available=False):
    """Public research-slot state, deliberately separate from a personal position."""
    if not plan:return 'WATCH'
    if plan.get('administrative_closure'):return 'ADMIN CLOSED UNRESOLVED'
    old=state(plan,now)
    if old=='UNRESOLVED' or plan.get('coverage_status')=='UNRESOLVED_GAP':return 'COVERAGE UNKNOWN'
    if plan.get('status') in ('EXPIRED','EXPIRED_NO_ENTRY'):return 'ENTRY EXPIRED'
    if plan.get('status')=='CANCELLED':return 'CANCELLED'
    if old=='EXIT CONDITION REACHED':return old
    if old=='HOLD':return 'MONITORING' if monitoring_available else 'COVERAGE UNKNOWN'
    return 'ENTRY CONFIRMED' if old=='ENTRY CONFIRMED' else 'WATCH'

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
    value={'signal_id':ident,'at':now.isoformat(),'reason':reason,'status':'ADMIN CLOSED UNRESOLVED','version':VERSION,'administrative_end':administrative_end(plan).isoformat(),'holding_deadline':plan['max_hold_until'],'observed_exit':False,'pnl':None,'private_holdings_unchanged':True,'outcome_status':'UNRESOLVED; later genuine evidence may settle research only'}
    # Event and retired-slot index commit together: a crash cannot leave a
    # durable closure that is adopted as a new active public plan on restart.
    if getattr(store,'db',None) is not None and hasattr(store,'transaction'):
        from core.storage import encode
        def write():
            store.db.execute('BEGIN IMMEDIATE')
            row=store.db.execute('SELECT payload FROM state WHERE key=?',('primary-admin-closures:v1',)).fetchone()
            import json
            retired=json.loads(row[0]) if row else []
            store.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?)',('primary-admin-close:'+ident,'primary_admin_closure',encode(value),now.isoformat()))
            if ident not in retired:retired.append(ident)
            store.db.execute('INSERT INTO state VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',('primary-admin-closures:v1',encode(retired),now.isoformat()))
            store.db.commit()
        store.transaction(write)
    elif store.event('primary-admin-close:'+ident,'primary_admin_closure',value):
        store.put('primary-admin-closures:v1',store.get('primary-admin-closures:v1',[])+[ident])
    return value

def close_due_unresolved(store,rows,now,maximum=40):
    """Release only overdue public slots; preserve all outcome/fill histories."""
    closed=[]
    for _ in range(maximum):
        plan=current(store,rows,now)
        if not plan or now<administrative_end(plan) or state(plan,now)!='UNRESOLVED':break
        value=administrative_close(store,rows,plan['signal_id'],'No qualifying exit observation by the declared administrative end; research slot released, outcome remains unknown.',now)
        closed.append((plan,value))
    return closed
