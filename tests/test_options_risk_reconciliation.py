"""Risk readiness must not infer zero loss metrics from absent/malformed records."""
import unittest
from datetime import datetime,timezone
from risk.options_policy import check as policy_check

def check(*args,**kwargs):
    return policy_check(*args,**kwargs,mode="paper")

class RiskReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,6,19,30,tzinfo=timezone.utc)
        self.policy={'max_trade_premium_usd':100,'max_exposure_usd':200,
                     'max_daily_loss_usd':50,'max_consecutive_losses':3,
                     'daily_reconciled_date':'2026-10-06','daily_loss_usd':0,
                     'consecutive_losses':0}
    def test_reconciled_date_alone_cannot_establish_zero_losses(self):
        for key in ('daily_loss_usd','consecutive_losses'):
            with self.subTest(key=key):
                policy=dict(self.policy);policy.pop(key)
                result=check(policy,[],now=self.now)
                self.assertFalse(result['ready'])
                self.assertIn('INVALID_'+key.upper(),result['reasons'])
                self.assertNotIn(key,policy)
    def test_invalid_daily_loss_fails_closed_without_exception(self):
        for value in (None,True,-1,float('nan'),float('inf'),'0'):
            with self.subTest(value=value):
                result=check({**self.policy,'daily_loss_usd':value},[],now=self.now)
                self.assertFalse(result['ready']);self.assertIn('INVALID_DAILY_LOSS_USD',result['reasons'])
    def test_loss_streak_requires_nonnegative_integer(self):
        for value in (None,True,-1,1.5,float('nan'),float('inf'),'0'):
            with self.subTest(value=value):
                result=check({**self.policy,'consecutive_losses':value},[],now=self.now)
                self.assertFalse(result['ready']);self.assertIn('INVALID_CONSECUTIVE_LOSSES',result['reasons'])
    def test_explicit_zeroes_preserve_risk_only_readiness_and_inputs(self):
        original=dict(self.policy)
        result=check(self.policy,[],premium=80,now=self.now)
        self.assertTrue(result['ready']);self.assertEqual(self.policy,original)
        self.assertEqual(result['basis'],'Paper ledger only')
    def test_loss_and_streak_threshold_equality_remain_blocked(self):
        result=check({**self.policy,'daily_loss_usd':50,'consecutive_losses':3},[],now=self.now)
        self.assertFalse(result['ready']);self.assertIn('DAILY_CIRCUIT_BREAKER',result['reasons'])
        self.assertIn('LOSS_STREAK_COOLDOWN',result['reasons'])

if __name__=='__main__':unittest.main()
