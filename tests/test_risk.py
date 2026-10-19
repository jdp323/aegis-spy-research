from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from risk.engine import Account, Quote, FX, Proposal, RiskEngine


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'risk.sqlite'
        self.engine = RiskEngine(self.path, ['validated-test-only'])
        self.account = Account(200, 200, 200, 200, 0, 0, 1000, True)
        self.quote = Quote('TEST', 'CAD', 9.99, 10, 1000)
        self.fx = FX('CAD', 1, 1000, True)
        self.proposal = Proposal('test-1', 'TEST', 'CAD', 1, 10, 9, .05, 1.1, .1, 'validated-test-only')

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def check(self, **changes):
        return self.engine.evaluate(changes.get('account', self.account),
          changes.get('quote', self.quote), changes.get('fx', self.fx),
          changes.get('proposal', self.proposal), now=1000)

    def test_research_reservation_never_authorizes_execution(self):
        result = self.check()
        self.assertEqual(result.status, 'PAPER_RESEARCH_ONLY')
        self.assertFalse(result.execution_authorized)

    def test_unknown_account_fails_closed(self):
        self.assertEqual(self.check(account=None).status, 'REJECTED')

    def test_floor_is_persistent_across_restart_and_deposit(self):
        self.engine.observe_equity_floor(51, observed_at=1000, now=1000)
        self.engine.close()
        self.engine = RiskEngine(self.path, ['validated-test-only'])
        self.assertIn('PERSISTENT_HALT', self.check().reason)

    def test_floor_observation_rejects_nan_and_stale(self):
        for value, stamp in [(float('nan'),1000),(51,900),(51,1001),(-1,1000)]:
            with self.assertRaises(ValueError):
                self.engine.observe_equity_floor(value, observed_at=stamp, now=1000)

    def test_duplicate_survives_restart(self):
        self.check()
        self.engine.close()
        self.engine = RiskEngine(self.path, ['validated-test-only'])
        self.assertIn('Duplicate', self.check().reason)
        self.assertIn('Duplicate', self.check(proposal=replace(self.proposal, proposal_id='new-id')).reason)

    def test_stale_future_crossed_nonfinite_quote(self):
        for quote in [replace(self.quote,timestamp=900),replace(self.quote,timestamp=1001),
                      replace(self.quote,bid=11),replace(self.quote,ask=float('nan'))]:
            self.assertEqual(self.check(quote=quote).status,'REJECTED')

    def test_daily_remaining_budget_counts_open_risk(self):
        result=self.check(account=replace(self.account,open_risk_cad=19.5))
        self.assertIn('risk budget',result.reason)

    def test_borrowing_is_rejected(self):
        self.assertIn('Insufficient cash',self.check(account=replace(self.account,cash_cad=5)).reason)

    def test_two_positions_cap(self):
        self.assertIn('Two-position',self.check(account=replace(self.account,open_positions=2)).reason)

    def test_unvalidated_strategy_and_fx(self):
        self.assertIn('Unvalidated',self.check(proposal=replace(self.proposal,strategy_validation_id='unknown')).reason)
        self.assertEqual(self.check(fx=replace(self.fx,independently_validated=False)).status,'REJECTED')

    def test_per_trade_limit(self):
        self.assertIn('15%',self.check(proposal=replace(self.proposal,modeled_loss_cad=31)).reason)

    def test_reset_requires_explicit_owner_flag(self):
        with self.assertRaises(ValueError):
            self.engine.reset_halt(owner_confirmation=False,reason='test')


if __name__ == '__main__':
    unittest.main()
