import unittest
from ops.free_candidate_study import summarize
class NoSampleStatistics(unittest.TestCase):
    def test_refused_entries_do_not_manufacture_zero_profit_or_zero_width_confidence(self):
        rows=[{'day':'2026-10-21','direction':'CALL','status':'ENTRY_EXPIRED_AFTER_DELAY','net_per_share':None}]
        r=summarize(rows,['2026-10-21','2026-10-22'])
        self.assertEqual(r['closed'],0);self.assertIsNone(r['net_per_share_sum']);self.assertIsNone(r['max_drawdown_per_share']);self.assertIsNone(r['day_block_mean_ci95']);self.assertIsNone(r['net_expectancy_per_closed'])
