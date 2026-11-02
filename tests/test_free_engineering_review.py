import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from ops.free_engineering_review import collect

class EngineeringReviewTests(unittest.TestCase):
    def test_weekend_not_missed_trading_day(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(collect('2026-11-01',d)['status'],'NO_SESSION')
    def test_future_session_is_pending_not_pass_or_synthetic_success(self):
        with tempfile.TemporaryDirectory() as d:
            r=collect('2026-11-02',d,datetime(2026,11,1,tzinfo=timezone.utc))
            self.assertEqual(r['status'],'LIVE_SESSION_PENDING');self.assertEqual(r['expected_slots'],25);self.assertFalse(r['strategy_edge_proved'])
    def test_missing_completed_session_fails_and_no_sample_is_not_fast(self):
        with tempfile.TemporaryDirectory() as d:
            r=collect('2026-11-02',d,datetime(2026,11,3,tzinfo=timezone.utc))
            self.assertEqual(r['status'],'FAIL');self.assertIsNone(r['local_fast_path_p95_seconds']);self.assertFalse(r['targets']['zero_unhandled_tick_failures'])
    def test_early_close_correct_slot_count(self):
        with tempfile.TemporaryDirectory() as d:
            r=collect('2026-11-27',d,datetime(2026,11,28,tzinfo=timezone.utc))
            self.assertEqual(r['expected_slots'],13);self.assertEqual(r['timely_slots'],0)

if __name__=='__main__':unittest.main()
