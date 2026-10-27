"""Single-flight local diagnostic cache; cached data never grants entry readiness.

HTTP requests do not wait for the heavy producer. At most one daemon refresh runs;
overdue/failed refreshes and expired snapshots remain explicit. No payload is
written to disk, no credentials are loaded here, and timestamps are never retimed.
"""
import copy
import json
import threading
import time
from datetime import datetime, timezone
from core.sessions import market_session
from core.signals import quote_valid, option_quote_valid
from data.models import stamp
from data.reliability import quote_diagnostics

def _loader():
    # Import/provider-independent request handling stays bounded even on cold boot.
    from core.upgrade_service import snapshot
    return snapshot()

def empty_snapshot(now):
    return {'session':market_session(now),'underlying':{'quality':'DATA_INCOMPLETE','payload':{}},
            'research_underlying':{'quality':'DATA_INCOMPLETE','payload':{}},'features':{},'regime':{},
            'selection':{},'positions':None,'signals':[],'streams':{},'system':{},'news':{},
            'options_readiness':{'mode':'RESEARCH_ONLY','gates':{'LIVE_SIGNAL_READY':False}},
            'today_verdict':'NO TRADE — diagnostic snapshot unavailable; no position closure inferred.',
            'today_next_event':'UNAVAILABLE','action':'NO TRADE','live_signal_enabled':False,
            'live_execution_enabled':False,'order_execution_enabled':False,'LIVE_SIGNAL_READY':False}

def _quote(value, now, option=False):
    if not isinstance(value,dict):return {'quality':'DATA_INCOMPLETE','payload':{}},False
    maximum=10 if option and value.get('provider')=='questrade' else 15 if option else 5
    try:
        diagnostics=quote_diagnostics(value,now,budget=maximum)
        valid=option_quote_valid(value,now) if option else quote_valid(value,now,maximum)
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        diagnostics={'source_age_seconds':None,'receipt_age_seconds':None,'source_receipt_skew_seconds':None,'predicate':'MALFORMED_CACHED_QUOTE'};valid=False
    value['dashboard_recheck']={**diagnostics,'evaluated_at':now.isoformat(),'eligible':valid}
    value['freshness_seconds']=diagnostics['source_age_seconds']
    if not valid and value.get('quality')=='DATA_OK':value['quality']='DATA_STALE'
    return value,valid

def recheck(data,now):
    """Recheck clocks on every response; never use cache age as quote freshness."""
    data['underlying'],_= _quote(data.get('underlying') or {},now)
    data['research_underlying'],_= _quote(data.get('research_underlying') or {},now)
    for row in (data.get('streams') or {}).values():
        if isinstance(row,dict):
            try:age=(now-stamp(row['at'])).total_seconds()
            except (KeyError,ValueError,TypeError):age=None
            row['heartbeat_age_seconds']=age;row['fresh_heartbeat']=age is not None and 0<=age<=30
    def deactivate(value):
        if isinstance(value,list):
            for child in value:deactivate(child)
        elif isinstance(value,dict):
            for key in ('paper_eligible','actionable','live_signal_ready','live_signal_enabled','order_execution_enabled','live_execution_enabled','signal_ready','live_ready','LIVE_SIGNAL_READY'):
                if key in value:value[key]=False
            if isinstance(value.get('gates'),dict):
                for key in value['gates']:
                    if key.endswith('_READY'):value['gates'][key]=False
            if isinstance(value.get('option_contract'),dict):
                contract=value['option_contract'];contract['quote'],valid=_quote(contract.get('quote') or {},now,True)
                if not valid:value['option_contract']=None;value['option_entry_range']=[];value['option_plan']=None
            if value.get('signal_expiry'):
                try:expired=stamp(value['signal_expiry'])<=now
                except (ValueError,TypeError):expired=True
                value['display_status']='EXPIRED' if expired else 'CACHED_DIAGNOSTIC_ONLY'
            for child in list(value.values()):
                if isinstance(child,(dict,list)):deactivate(child)
    deactivate(data)
    selection=data.get('selection') or {};best=selection.get('best_contract')
    if isinstance(best,dict):
        best['quote'],valid=_quote(best.get('quote') or {},now,True)
        if not valid:selection['best_contract']=None;selection['reason']='CACHED_OPTION_QUOTE_NOT_CURRENT'
    data['selection']=selection
    for position in data.get('positions') or []:
        # A copied bid mark cannot establish a current liquidation value or exit.
        position['estimated_pnl_usd']=None;position['estimated_liquidation_usd']=None
        position['dashboard_mark_status']='UNAVAILABLE_FROM_DIAGNOSTIC_CACHE'
    live=data.get('live_trend') or {}
    live['observed_status']=live.get('status','UNAVAILABLE');live['status']='DIAGNOSTIC_SNAPSHOT_ONLY'
    live['reason']='Use a current gated evaluation; snapshot cache does not establish quote/bar/heartbeat readiness.'
    data['live_trend']=live
    data['saved_today_verdict']=data.get('today_verdict')
    data['today_verdict']='NO TRADE — dashboard snapshot is diagnostic only; /trend performs a current gated evaluation.'
    view=data.get('market_view')
    if view:
        view['entry'].update(state='WAIT',underlying_eligible=False,option_eligible=False,reason='cached diagnostic snapshot; request /trend for current gates')
        view['trend']['descriptive_only']=True
        view['price']['quote_eligible']=False
        view['price']['kind']='CACHED_REFERENCE'
        for outlook in view.get('outlooks',{}).values():
            outlook.update(bias='ABSTAIN',reason='cached diagnostic snapshot; original forecast retained separately')
        if view.get('primary_plan'):view['primary_plan']['monitoring_available']=False
    data.update(action='NO TRADE',live_signal_enabled=False,order_execution_enabled=False,live_execution_enabled=False,LIVE_SIGNAL_READY=False)
    return data

class SnapshotCache:
    def __init__(self,loader=None,refresh_seconds=15,maximum_age_seconds=45,refresh_budget_seconds=5,clock=None,monotonic=None):
        self.loader=loader or _loader;self.refresh_seconds=refresh_seconds;self.maximum_age_seconds=maximum_age_seconds;self.refresh_budget_seconds=refresh_budget_seconds
        self.clock=clock or (lambda:datetime.now(timezone.utc));self.monotonic=monotonic or time.monotonic
        self.lock=threading.Lock();self.data=None;self.running=False;self.started=None;self.completed=None;self.finished=None;self.last_error=None;self.thread=None
    def _run(self):
        try:
            value=self.loader()
            if not isinstance(value,dict):raise ValueError('INVALID_SNAPSHOT_SHAPE')
            value=json.loads(json.dumps(value,allow_nan=False))
            with self.lock:self.data=value;self.completed=self.monotonic();self.last_error=None
        except Exception as error:
            with self.lock:self.last_error=type(error).__name__
        finally:
            with self.lock:self.running=False;self.finished=self.monotonic()
    def get(self):
        with self.lock:
            mono=self.monotonic()
            baseline=self.finished if self.finished is not None else self.started
            if not self.running and (baseline is None or mono-baseline>=self.refresh_seconds):
                self.running=True;self.started=mono;self.thread=threading.Thread(target=self._run,name='aegis-dashboard-snapshot',daemon=True);self.thread.start()
            source=self.data;started=self.started;completed=self.completed;running=self.running;error=self.last_error
        # Producer only replaces source. Copy before taking the evaluation clock.
        data=copy.deepcopy(source) if source is not None else None
        now=self.clock()
        if now.tzinfo is None or now.utcoffset() is None:raise ValueError('AWARE_TIME_REQUIRED')
        age=self.monotonic()-completed if completed is not None else None
        duration=self.monotonic()-started if running and started is not None else None
        try:source_age=(now-stamp((data or {}).get('generated_at'))).total_seconds()
        except (ValueError,TypeError,KeyError,AttributeError,OverflowError):source_age=None
        available=data is not None and age is not None and 0<=age<=self.maximum_age_seconds and source_age is not None and 0<=source_age<=self.maximum_age_seconds
        state='REFRESH_OVERDUE' if running and duration>self.refresh_budget_seconds else 'REFRESHING' if running else 'REFRESH_FAILED' if error else 'DIAGNOSTIC_CACHE'
        if not available and not running and not error:state='SNAPSHOT_EXPIRED_OR_UNAVAILABLE'
        metadata={'state':state,'data_available':available,'snapshot_as_of':(data or {}).get('generated_at'),
                  'evaluated_at':now.isoformat(),'cache_age_seconds':age,'snapshot_source_age_seconds':source_age,
                  'refresh_running':running,'refresh_elapsed_seconds':duration,'refresh_budget_seconds':self.refresh_budget_seconds,
                  'refresh_error_type':error,'new_entry_eligibility':False,'scope':'DIAGNOSTIC_ONLY_NOT_ENTRY_READINESS'}
        data=recheck(data,now) if available else empty_snapshot(now)
        data['snapshot_cache']=metadata
        return data
