"""Independent deterministic monitoring timer inside the existing worker process.

There is one public-plan coordinator and one composer. This thread owns its own
SQLite connection; slow maintenance never receives that connection. It is not a
real-time scheduler: host pauses, the GIL and SQLite contention remain measured
limitations, and no thread is claimed cancelled on a close timeout.
"""
import hashlib
import json
import os
import copy
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from core.background_jobs import error_fields
from core.storage import Store

VERSION = 'independent-monitor-timer-v1'
INPUT_KEYS = ('quote:SPY', 'research_quote:SPY:iex', 'stream:sip', 'stream:iex',
              'stream_bars:SPY', 'research_stream_bars:SPY:iex', 'ntp_clock',
              'daily', 'history_daily:iex', 'history_daily:sip',
              'history_frames:iex', 'history_frames:sip',
              'confirmed_minutes:iex', 'confirmed_minutes:sip',
              'primary-research-plan:v1', 'primary-admin-closures:v1')


def public_evaluation_due(store,tracker,now):
    """Keep every scheduled/session check; omit useless overnight replays.

    Existing unresolved public plans are still reviewed to their fixed
    administrative end. Private reported holdings are reviewed separately.
    This is a clock/session boundary, never change-only message throttling.
    """
    from core.sessions import ET,market_session
    local=now.astimezone(ET);session=market_session(local.replace(hour=12,minute=0))
    minute=local.hour*60+local.minute
    if session['active'] and 540<=minute<=session['close_minute']+20:return True
    retired=set(store.get('primary-admin-closures:v1',[]))
    return any(row.get('alerted') and row['signal_id'] not in retired for row in tracker.positions(active_only=True))


class InputStore(Store):
    """Coherent snapshot digest and bounded feature memo; clocks never cached."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._snapshot_digests = {}
        self.feature_memo = OrderedDict()

    def snapshot(self, keys):
        self.db.execute('BEGIN')
        try:
            result = {}
            digests = {}
            for key in keys:
                row = self.db.execute('SELECT payload FROM state WHERE key=?', (key,)).fetchone()
                body = row[0] if row else None
                result[key] = json.loads(body) if body is not None else None
                digests[key] = hashlib.sha256((body or 'null').encode()).hexdigest()
            self.db.rollback()
            self._snapshot_digests = digests
            return result
        except Exception:
            self.db.rollback()
            raise

    def market_cache_revision(self, keys):
        # These hashes belong to the snapshot just read, not a later database
        # read which could associate old bars with a newer input revision.
        if not all(key in self._snapshot_digests for key in keys):
            return None
        return tuple((key, self._snapshot_digests[key]) for key in keys)

    def memo_put(self, key, value):
        self.feature_memo[key] = value
        self.feature_memo.move_to_end(key)
        while len(self.feature_memo) > 4:
            self.feature_memo.popitem(last=False)

    def input_revision(self):
        placeholders = ','.join('?' for _ in INPUT_KEYS)
        return tuple(tuple(row) for row in self.db.execute('SELECT key,updated FROM state WHERE key IN ('+
                                    placeholders+') ORDER BY key', INPUT_KEYS))


def feature_key(store, population, keys, now, simulation=False):
    revision = store.market_cache_revision(keys) if hasattr(store, 'market_cache_revision') else None
    return (population, bool(simulation), int(now.timestamp()//60), revision) if revision is not None else None


def feature_get(store, key):
    if key is None:
        return None
    value = store.feature_memo.get(key)
    store.metrics['feature_cache_hits' if value is not None else 'feature_cache_misses'] = store.metrics.get('feature_cache_hits' if value is not None else 'feature_cache_misses', 0)+1
    # Consumers cannot mutate the saved calculation and poison a later quote.
    return copy.deepcopy(value) if value is not None else None


def feature_put(store, key, value):
    if key is not None:
        store.memo_put(key, copy.deepcopy(value))


def phase_times(quote, decision_at, elapsed):
    """Signed observed intervals; unknown stages remain unavailable."""
    from data.models import stamp
    out = {'evaluated_at': decision_at.isoformat(),
           'local_evaluation_seconds': elapsed,
           'source_timestamp': quote.get('source_timestamp'),
           'received_timestamp': quote.get('received_timestamp'),
           'source_to_receipt_seconds': None,
           'receipt_to_decision_seconds': None,
           'decode_seconds': None, 'queue_seconds': None,
           'clock_basis': 'LOCAL_RECEIPT_AND_DECISION; provider clock independent'}
    try:
        source = stamp(quote['source_timestamp']); received = stamp(quote['received_timestamp'])
        out['source_to_receipt_seconds'] = (received-source).total_seconds()
        out['receipt_to_decision_seconds'] = (decision_at-received).total_seconds()
    except (KeyError, ValueError, TypeError):
        pass
    return out


class FastPath:
    def __init__(self, root, callback, store_factory=InputStore, interval=1,
                 clock=time.monotonic, wall=None):
        if not .1 <= interval <= 5:
            raise ValueError('INVALID_MONITOR_INTERVAL')
        self.root = Path(root); self.callback = callback
        self.store_factory = store_factory; self.interval = interval
        self.clock = clock; self.wall = wall or (lambda: datetime.now(timezone.utc))
        self.stopping = threading.Event(); self.ready = threading.Event()
        self.thread = None; self.latest = {}; self._lock = threading.Lock()

    def _publish(self, value):
        folder = self.root/'runtime'; folder.mkdir(parents=True, exist_ok=True)
        target = folder/'fast_path_progress.json'
        temporary = folder/('fast_path_progress-'+str(os.getpid())+'.tmp')
        with self._lock:
            self.latest = value
        try:
            temporary.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
            temporary.replace(target)
            if value.get('state') in ('COMPLETED','FAILED_TICK','START_FAILED'):
                from core.sessions import ET
                day=self.wall().astimezone(ET).date().isoformat()
                logs=self.root/'logs/fast_path';logs.mkdir(parents=True,exist_ok=True)
                with (logs/(day+'.jsonl')).open('a',encoding='utf-8') as output:
                    output.write(json.dumps(value,allow_nan=False)+'\n')
        except OSError:
            temporary.unlink(missing_ok=True)

    def start(self):
        if self.thread and self.thread.is_alive():
            return False
        if self.stopping.is_set():
            return False
        self.thread = threading.Thread(target=self._run, name='aegis-monitor-timer', daemon=True)
        self.thread.start()
        return True

    def _run(self):
        store = None; previous = None; previous_minute = None; previous_check = None
        last_completed = None; expected = self.clock(); count = 0
        try:
            store = self.store_factory(self.root/'runtime/aegis.sqlite', lock_timeout=.25, retry_attempts=2)
            self.ready.set()
            while not self.stopping.is_set() and not (self.root/'runtime/shutdown.request').exists():
                started = self.clock(); now = self.wall(); count += 1
                value = {'version': VERSION, 'pid': os.getpid(), 'at': now.isoformat(),
                         'state': 'RUNNING', 'tick_number': count,
                         'last_completed_at': last_completed,
                         'timer_lag_seconds': max(0, started-expected),
                         'interval_seconds': self.interval,
                         'thread_cancellation_claimed': False}
                self._publish(value) # A blocked tick must not masquerade as a completed one.
                try:
                    revision = store.input_revision() if hasattr(store, 'input_revision') else count
                    minute = int(now.timestamp()//60)
                    # Unchanged inputs still get a short deadline/expiry check.
                    # No backlog is replayed after a host pause or clock jump.
                    due = revision != previous or minute != previous_minute or previous_check is None or started-previous_check >= 5
                    if due:
                        result = self.callback(store, now)
                        previous_check = self.clock(); previous = revision; previous_minute = minute
                        last_completed = self.wall().isoformat()
                        value.update(state='COMPLETED', last_completed_at=last_completed,
                                     result=result if isinstance(result, dict) else None)
                    else:
                        value['state'] = 'IDLE_INPUTS_UNCHANGED'
                    value['database'] = dict(getattr(store, 'metrics', {}))
                except Exception as error:
                    value.update(state='FAILED_TICK', **error_fields(error))
                duration = self.clock()-started
                value.update(at=self.wall().isoformat(), duration_seconds=duration,
                             budget_seconds=1, deadline_missed=duration > 1)
                self._publish(value)
                expected = self.clock()+self.interval
                self.stopping.wait(self.interval)
        except Exception as error:
            self._publish({'version': VERSION, 'pid': os.getpid(), 'at': self.wall().isoformat(),
                           'state': 'START_FAILED', 'last_completed_at': last_completed, **error_fields(error)})
            self.ready.set()
        finally:
            if store:
                store.close()
            value = dict(self.latest)
            if value.get('state') != 'START_FAILED':
                value.update(state='STOPPED', at=self.wall().isoformat())
                self._publish(value)

    def health(self):
        with self._lock:
            value = dict(self.latest)
        value['thread_alive'] = bool(self.thread and self.thread.is_alive())
        value['shutdown_requested'] = self.stopping.is_set()
        return value

    def close(self, timeout=2):
        self.stopping.set()
        if self.thread:
            self.thread.join(timeout)
        return self.health()
