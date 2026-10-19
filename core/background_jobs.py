"""Bounded daemon maintenance jobs and secret-free worker phase evidence.

Jobs never share the worker's SQLite connection. Completion does not retimestamp
market observations or imply that an overdue thread has stopped. Results are
applied by the owning worker thread through its registered completion callback.
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


def error_fields(error):
    """Exception classes/codes only: provider messages can contain credentials."""
    fields = {'error_type': type(error).__name__}
    for key in ('sqlite_errorcode', 'sqlite_errorname'):
        value = getattr(error, key, None)
        if isinstance(value, int) or isinstance(value, str) and re.fullmatch(r'[A-Z_]{1,64}', value):
            fields[key] = value
    return fields


class Jobs:
    def __init__(self, maximum=48, clock=time.monotonic):
        self.maximum = maximum
        self.clock = clock
        self.lock = threading.Lock()
        self.running = {}
        self.completed = []
        self.closed = False

    def submit(self, key, work, apply=None, budget=15):
        if not re.fullmatch(r'[a-z0-9:_-]{1,80}', key) or budget <= 0:
            raise ValueError('INVALID_BACKGROUND_JOB')
        with self.lock:
            if self.closed or key in self.running or len(self.running) >= self.maximum:
                return False
            entry = {'key': key, 'started': self.clock(), 'budget_seconds': budget,
                     'started_at': datetime.now(timezone.utc).isoformat(), 'state': 'RUNNING', 'apply': apply}
            self.running[key] = entry

        def run():
            try:
                value = work()
                result = {'key': key, 'value': value, 'state': 'COMPLETED'}
            except Exception as error:
                result = {'key': key, 'value': None, 'state': 'FAILED', **error_fields(error)}
            with self.lock:
                result.update(duration_seconds=self.clock()-entry['started'],
                              budget_seconds=budget, completed_at=datetime.now(timezone.utc).isoformat(), apply=apply)
                result['deadline_missed'] = result['duration_seconds'] > budget
                entry['state'] = 'COMPLETED_PENDING_APPLY'
                self.completed.append(result)

        # Network calls retain their adapter timeout. Daemon jobs cannot keep a
        # requested shutdown alive indefinitely; no thread cancellation is claimed.
        thread = threading.Thread(target=run, name='aegis-'+key, daemon=True)
        with self.lock:
            entry['thread'] = thread
        thread.start()
        return True

    def drain(self):
        with self.lock:
            results, self.completed = self.completed, []
            for row in results:
                self.running.pop(row['key'], None)
        summaries = []
        for row in results:
            apply = row.pop('apply')
            value = row.pop('value')
            # Completing a request does not establish usable market data.
            candidate = value[0] if isinstance(value, tuple) and value else value
            if isinstance(candidate, dict):
                quality = candidate.get('quality', candidate.get('status'))
                if isinstance(quality, str) and re.fullmatch(r'[A-Z_0-9]{1,64}', quality):
                    row['result_quality'] = quality
            if row['state'] == 'COMPLETED' and apply:
                try:
                    apply(value)
                except Exception as error:
                    row.update(state='APPLY_FAILED', **error_fields(error))
            summaries.append(row)
        return summaries

    def health(self):
        with self.lock:
            rows = []
            for row in self.running.values():
                elapsed = self.clock()-row['started']
                rows.append({'key': row['key'], 'started_at': row['started_at'],
                             'elapsed_seconds': elapsed, 'budget_seconds': row['budget_seconds'],
                             'state': 'RUNNING_OVER_BUDGET' if elapsed > row['budget_seconds'] and row['state'] == 'RUNNING' else row['state'],
                             'thread_alive': row['thread'].is_alive() if row.get('thread') else False})
            return {'at': datetime.now(timezone.utc).isoformat(), 'active_jobs': rows,
                    'maximum_jobs': self.maximum, 'shutdown_requested': self.closed}

    def close(self, timeout=1):
        with self.lock:
            self.closed = True
            threads = [r.get('thread') for r in self.running.values()]
        deadline = self.clock()+timeout
        for thread in threads:
            if thread:
                thread.join(max(0, deadline-self.clock()))
        return self.health()


class Phases:
    """Independent JSON progress survives a blocked/failed market database write."""
    def __init__(self, root, clock=time.monotonic, wall=None):
        self.root = Path(root)
        self.clock = clock
        self.wall = wall or (lambda: datetime.now(timezone.utc))
        self.current = None
        self.rows = []
        self.last_completed_at = None

    def _publish(self, row):
        folder = self.root/'runtime'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder/'worker_progress.json'
        temporary = folder/('worker_progress-'+str(os.getpid())+'.tmp')
        value = {'pid': os.getpid(), 'at': self.wall().isoformat(),
                 'last_completed_at': self.last_completed_at, **row}
        try:
            temporary.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
            temporary.replace(target)
        except OSError:
            # Telemetry failure must not stop position reviews. Prior file remains.
            temporary.unlink(missing_ok=True)

    def start(self, name, budget=10):
        if not re.fullmatch(r'[a-z0-9_]{1,64}', name):
            raise ValueError('INVALID_WORKER_PHASE')
        self.finish()
        self.current = {'phase': name, 'started_at': self.wall().isoformat(),
                        'started_mono': self.clock(), 'budget_seconds': budget}
        self._publish({'state': 'RUNNING_PHASE', 'phase': name,
                       'phase_started_at': self.current['started_at'], 'budget_seconds': budget})

    def finish(self, error=None):
        if not self.current:
            return
        current, self.current = self.current, None
        duration = self.clock()-current.pop('started_mono')
        completed = self.wall()
        row = {**current, 'completed_at': completed.isoformat(), 'duration_seconds': duration,
               'deadline_missed': duration > current['budget_seconds'],
               'wall_minus_monotonic_seconds': (completed-datetime.fromisoformat(current['started_at'])).total_seconds()-duration,
               'state': 'FAILED' if error else 'COMPLETED'}
        if error:
            row.update(error_fields(error))
        else:
            self.last_completed_at = completed.isoformat()
        self.rows.append(row)
        self.rows = self.rows[-64:]
        self._publish(row)
        try:
            # Daily partitions bound each active file; older evidence is kept,
            # never deleted. API state exposes only 24 of the last 64 phases.
            folder = self.root/'logs/worker_phases'
            folder.mkdir(parents=True, exist_ok=True)
            with (folder/(completed.date().isoformat()+'.jsonl')).open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row, allow_nan=False)+'\n')
        except OSError:
            pass

    def summary(self):
        return {'last_completed_at': self.last_completed_at,
                'recent_phases': self.rows[-24:],
                'deadline_misses': sum(r['deadline_missed'] for r in self.rows)}
