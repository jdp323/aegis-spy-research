"""Synthetic post-read control clocks on isolated SQLite; no services or network."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import json, sqlite3, tempfile, unittest
from ops.supervisor import stream_restart_due

LOOP = datetime(2026, 11, 2, 16, 27, 6, tzinfo=timezone.utc)
EVALUATED = LOOP + timedelta(milliseconds=10)

class SupervisorPostReadClockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'runtime').mkdir()
        self.path = self.root / 'runtime/aegis.sqlite'
        self.db = sqlite3.connect(self.path)
        self.db.execute('CREATE TABLE state(key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        self.started = LOOP - timedelta(hours=1)
        self.health = {'state': 'FEED_DISCONNECTED', 'error_type': 'PermissionError',
                       'next_retry_seconds': 300,
                       'connection_started_at': (LOOP-timedelta(seconds=1)).isoformat(),
                       'at': (LOOP+timedelta(milliseconds=5)).isoformat()}
        self.put(self.health)
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()
    def put(self, health):
        with self.db:
            for key, value in [('stream:iex', health), ('last_market:iex', {'received_timestamp': (LOOP-timedelta(minutes=10)).isoformat()})]:
                self.db.execute('INSERT OR REPLACE INTO state VALUES(?,?)', (key, json.dumps(value)))
    def test_concurrent_valid_refusal_is_evaluated_after_read(self):
        self.assertFalse(stream_restart_due(self.root, LOOP, self.started, clock=lambda: EVALUATED))
    def test_actual_future_control_still_cannot_claim_cooldown(self):
        self.put({**self.health, 'at': (EVALUATED+timedelta(seconds=2)).isoformat()})
        self.assertTrue(stream_restart_due(self.root, LOOP, self.started, clock=lambda: EVALUATED))
    def test_expired_retry_grace_still_requires_restart(self):
        self.put({**self.health, 'at': (LOOP-timedelta(seconds=306)).isoformat(),
                  'connection_started_at': (LOOP-timedelta(seconds=307)).isoformat()})
        self.assertTrue(stream_restart_due(self.root, LOOP, self.started, clock=lambda: EVALUATED))
    def test_omitted_clock_retains_explicit_fixture_clock(self):
        self.assertTrue(stream_restart_due(self.root, LOOP, self.started))
    def test_evaluation_clock_follows_both_reads_in_one_transaction(self):
        calls = []
        connect = sqlite3.connect
        def traced(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connection.set_trace_callback(calls.append)
            return connection
        def clock():
            self.assertTrue(any(statement == 'BEGIN' for statement in calls))
            self.assertTrue(any("'stream:iex'" in statement for statement in calls))
            self.assertTrue(any("'last_market:iex'" in statement for statement in calls))
            return EVALUATED
        with patch('ops.supervisor.sqlite3.connect', side_effect=traced):
            self.assertFalse(stream_restart_due(self.root, LOOP, self.started, clock=clock))

if __name__ == '__main__':
    unittest.main()
