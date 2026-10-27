"""Immutable proposal binding and final transmission-time research eligibility."""
import hashlib,json
from datetime import timedelta
from data.models import stamp,finite
from core.sessions import market_session,ET

VERSION='entry-publication-v1'
FIELDS=('signal_id','strategy_version','direction','horizon_id','timestamp','decision_at','detected_at','market_timestamp','quote_received_at','confirmation_at','confirmation_bar_start','confirmation_timeframe','trigger','trigger_level','reference_midpoint','modeled_entry_fill','invalidation','t1','t2','do_not_chase','signal_expiry','max_hold_until','option_contract','option_plan','option_verification')

def binding(idea):
    return {k:idea.get(k) for k in FIELDS}

def digest(proposal):
    return hashlib.sha256(json.dumps(proposal,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def envelope(idea):
    p=binding(idea)
    return {'version':VERSION,'proposal':p,'sha256':digest(p)}

def check(guard,ctx,news,now,registered=None):
    """Pure refusal path, shared by tests and the read-only dispatch bridge."""
    try:
        if guard.get('version')!=VERSION:return 'GUARD_VERSION_REQUIRED'
        p=guard['proposal']
        if digest(p)!=guard.get('sha256'):return 'PROPOSAL_BINDING_MISMATCH'
        if registered is not None and binding(registered)!=p:return 'REGISTERED_PROPOSAL_MISMATCH'
        if registered is not None and (registered.get('status') not in ('OPEN','PENDING') or registered.get('coverage_status')=='UNRESOLVED_GAP'):return 'PLAN_NO_LONGER_ENTRY_ELIGIBLE'
        if not market_session(now)['active']:return 'SESSION_CLOSED'
        if ctx.get('reason'):return 'UNDERLYING_GATE_FAILED'
        from core.signals import quote_valid
        q=ctx.get('quote') or {}
        if not quote_valid(q,now,5):return 'QUOTE_NOT_FRESH'
        if news.get('quality')!='DATA_OK' or news.get('risk') not in ('NORMAL','MODERATE'):return 'CALENDAR_GATE_FAILED'
        expiry=stamp(p['signal_expiry']);end=stamp(p['max_hold_until']);confirmation=stamp(p['confirmation_at'])
        if not confirmation<=now<expiry<end:return 'ENTRY_WINDOW_EXPIRED_OR_INVALID'
        if not 0<=(now-confirmation).total_seconds()<=60:return 'CONFIRMATION_TOO_OLD'
        if p.get('horizon_id')=='H60' and end-confirmation!=timedelta(minutes=60):return 'FULL_H60_REQUIRED'
        if p.get('horizon_id')=='H120' and end-confirmation!=timedelta(minutes=120):return 'FULL_H120_REQUIRED'
        close=now.astimezone(ET).replace(hour=market_session(now)['close_minute']//60,minute=market_session(now)['close_minute']%60,second=0,microsecond=0)
        if end>close-timedelta(minutes=30):return 'HOLDING_CUTOFF_EXCEEDED'
        sign=1 if p['direction']=='CALL' else -1 if p['direction']=='PUT' else 0
        px=q['payload']['mid']
        if not sign or not all(finite(p[k]) for k in ('trigger','do_not_chase','invalidation','t2')):return 'INVALID_PLAN_LEVELS'
        if (px-p['trigger'])*sign<0:return 'CONFIRMATION_REVERSED'
        if (px-p['do_not_chase'])*sign>0:return 'NO_CHASE_LIMIT_EXCEEDED'
        if (px-p['invalidation'])*sign<=0 or (px-p['t2'])*sign>=0:return 'EXIT_CONDITION_ALREADY_REACHED'
        if p.get('option_contract'):
            from options.research_contract import current_reference
            if not current_reference(p,now):return 'OPTION_REFERENCE_NO_LONGER_VERIFIED'
        return None
    except (KeyError,ValueError,TypeError,OverflowError):return 'MALFORMED_PUBLICATION_INPUT'
