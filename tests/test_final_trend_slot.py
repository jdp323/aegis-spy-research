"""Final-slot recovery through the production scheduler, isolated stores/transports."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from core.sessions import ET
from core.storage import Store
from monitoring.day_schedule import dispatch, due


def clock(hour, minute, day='2026-10-30', second=0):
    return datetime.fromisoformat(day).replace(hour=hour, minute=minute, second=second, tzinfo=ET)


class FinalTrendSlot(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'isolated.sqlite'
        self.store = Store(self.path)
        self.addCleanup(self.store.close)
        self.config = {'signals': {'shared': False}, 'trend_lines_silent': True}
        self.sent = []

    def send(self, now, store=None, publish=None):
        return dispatch(store or self.store, now, self.config,
                        lambda kind: 'Fixture current status', publish or self.sent.append)

    def test_regular_last_slot_has_the_same_window_as_earlier_slots(self):
        for minute in (45, 46, 59):
            with self.subTest(minute=minute):
                self.assertIn(('TREND', '2026-10-30-945'), due(clock(15, minute), self.config))

    def test_early_close_last_slot_window(self):
        for minute in (45, 46, 59):
            with self.subTest(minute=minute):
                self.assertIn(('TREND', '2026-11-27-765'), due(clock(12, minute, '2026-11-27'), self.config))

    def test_dst_uses_exchange_local_time(self):
        now = datetime.fromisoformat('2026-11-02T20:46:00+00:00')
        self.assertIn(('TREND', '2026-11-02-945'), due(now, self.config))
        self.assertFalse(due(datetime.fromisoformat('2026-11-02T13:45:00+00:00'), self.config))

    def test_no_new_status_at_or_after_close(self):
        for now in (clock(16, 0), clock(16, 1), clock(13, 0, '2026-11-27')):
            self.assertFalse(any(kind == 'TREND' for kind, _ in due(now, self.config)))

    def test_weekend_and_holiday_remain_closed(self):
        for day in ('2026-10-31', '2026-11-26'):
            self.assertFalse(due(clock(15, 46, day), self.config))

    def test_current_slot_only_never_catches_up_an_old_slot(self):
        self.assertEqual([('TREND', '2026-10-30-930')], due(clock(15, 44), self.config))
        self.assertEqual([('TREND', '2026-10-30-945')], due(clock(15, 59, second=59), self.config))

    def test_preopen_and_recap_windows_unchanged(self):
        self.assertIn(('PREOPEN', '2026-10-30'), due(clock(9, 15), self.config))
        self.assertFalse(due(clock(9, 20), self.config))
        self.assertIn(('RECAP', '2026-10-30'), due(clock(16, 15), self.config))
        self.assertFalse(due(clock(16, 20), self.config))

    def test_final_status_envelope_cannot_outlive_exchange_close(self):
        for now, end in ((clock(15, 59), clock(16, 0)),
                         (clock(12, 59, '2026-11-27'), clock(13, 0, '2026-11-27'))):
            with self.subTest(now=now):
                event = self.send(now)[0]
                self.assertEqual(datetime.fromisoformat(event['expires_at']), end)

    def test_failed_uncommitted_reservation_can_run_in_next_minute(self):
        original = self.store.reserve
        self.store.reserve = lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError('fixture busy'))
        with self.assertRaises(sqlite3.OperationalError):
            self.send(clock(15, 45, second=40))
        self.store.reserve = original
        self.assertIsNone(self.store.get('v5-slot:TREND:2026-10-30-945'))
        self.send(clock(15, 46, second=4))
        self.send(clock(15, 47))
        self.assertEqual(len(self.sent), 1)
        event = self.sent[0]
        self.assertEqual(event['id'], 'v5-trend-2026-10-30-945')
        self.assertTrue(event['disable_notification'])
        self.assertEqual(event['audience'], 'PRIVATE')
        self.assertEqual(datetime.fromisoformat(event['expires_at']), clock(15, 51, second=4))

    def test_uncertain_publish_reservation_survives_restart_without_replay(self):
        def uncertain(event):
            raise TimeoutError('fixture uncertain transport boundary')
        with self.assertRaises(TimeoutError):
            self.send(clock(15, 45), publish=uncertain)
        reopened = Store(self.path)
        try:
            self.send(clock(15, 46), store=reopened)
            self.send(clock(15, 59), store=reopened)
            self.assertFalse(self.sent)
            self.assertEqual(reopened.get('v5-slot:TREND:2026-10-30-945')['status'], 'RESERVED_NO_BLIND_RETRY')
        finally:
            reopened.close()

    def test_full_day_one_minute_late_calls_produce_all_25_slots(self):
        start = clock(9, 46)
        for number in range(25):
            now = start + timedelta(minutes=15 * number)
            self.send(now)
            self.send(now + timedelta(seconds=20))
        self.send(clock(16, 1))
        self.assertEqual(len(self.sent), 25)
        self.assertEqual(len({event['id'] for event in self.sent}), 25)
        self.assertEqual(self.sent[-1]['id'], 'v5-trend-2026-10-30-945')
        self.assertTrue(all(event['disable_notification'] for event in self.sent))

    def test_early_close_day_one_minute_late_calls_produce_13_slots(self):
        start = clock(9, 46, '2026-11-27')
        for number in range(13):
            self.send(start + timedelta(minutes=15 * number))
        self.send(clock(13, 0, '2026-11-27'))
        self.assertEqual(len(self.sent), 13)
        self.assertEqual(self.sent[-1]['id'], 'v5-trend-2026-11-27-765')


if __name__ == '__main__':
    unittest.main()
