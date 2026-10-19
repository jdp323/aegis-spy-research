"""Synthetic reconciliation-day tests; not trading or reconciliation evidence."""
import copy
import unittest
from datetime import datetime, timezone, timedelta
from risk.options_policy import check as policy_check

def check(*args,**kwargs):
    return policy_check(*args,**kwargs,mode="paper")


class RiskEasternDayTests(unittest.TestCase):
    def policy(self, day):
        return dict(max_trade_premium_usd=100, max_exposure_usd=200,
                    max_daily_loss_usd=50, max_consecutive_losses=3,
                    daily_loss_usd=0, consecutive_losses=0,
                    daily_reconciled_date=day)

    def assert_day(self, instant, expected_day, wrong_day):
        self.assertTrue(check(self.policy(expected_day), [], now=instant)['ready'])
        result = check(self.policy(wrong_day), [], now=instant)
        self.assertFalse(result['ready'])
        self.assertIn('DAILY_RISK_RECONCILIATION_REQUIRED', result['reasons'])

    def test_utc_midnight_does_not_advance_et_reconciliation(self):
        instant = datetime(2026, 10, 7, 0, 30, tzinfo=timezone.utc)
        self.assert_day(instant, '2026-10-06', '2026-10-07')
        # Equivalent instants in a different offset must give the same result.
        self.assert_day(instant.astimezone(timezone(timedelta(hours=9))),
                        '2026-10-06', '2026-10-07')

    def test_daylight_saving_midnight_boundary(self):
        self.assert_day(datetime(2026, 10, 7, 3, 59, 59, tzinfo=timezone.utc),
                        '2026-10-06', '2026-10-07')
        self.assert_day(datetime(2026, 10, 7, 4, 0, tzinfo=timezone.utc),
                        '2026-10-07', '2026-10-06')

    def test_standard_time_midnight_boundary(self):
        self.assert_day(datetime(2026, 12, 2, 4, 59, 59, tzinfo=timezone.utc),
                        '2026-12-01', '2026-12-02')
        self.assert_day(datetime(2026, 12, 2, 5, 0, tzinfo=timezone.utc),
                        '2026-12-02', '2026-12-01')

    def test_dst_fold_does_not_reset_loss_or_mutate_records(self):
        policy = self.policy('2026-11-01')
        policy.update(daily_loss_usd=50, consecutive_losses=3)
        original = copy.deepcopy(policy)
        for hour in (5, 6):
            result = check(policy, [], now=datetime(2026, 11, 1, hour, 30,
                                                   tzinfo=timezone.utc))
            self.assertFalse(result['ready'])
            self.assertNotIn('DAILY_RISK_RECONCILIATION_REQUIRED', result['reasons'])
            self.assertIn('DAILY_CIRCUIT_BREAKER', result['reasons'])
            self.assertIn('LOSS_STREAK_COOLDOWN', result['reasons'])
        self.assertEqual(policy, original)

    def test_ambiguous_or_invalid_clock_fails_closed(self):
        for clock in (datetime(2026, 10, 6, 16, 30), '2026-10-06', False, 0):
            with self.subTest(clock=clock):
                result = check(self.policy('2026-10-06'), [], now=clock)
                self.assertFalse(result['ready'])
                self.assertIn('INVALID_RISK_CLOCK', result['reasons'])


if __name__ == '__main__':
    unittest.main()
