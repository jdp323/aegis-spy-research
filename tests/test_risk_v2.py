import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from risk.v2 import (CycleLedger, AccountSnapshot, MarketQuote, MarketSession,
                     StrategyEvidence, Proposal, RiskEngineV2)


class RiskV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "risk.sqlite"
        self.now = 1000000.0
        self.registry = {"trend": StrategyEvidence("e1", self.now-100, self.now+1000, True)}
        self.engine = RiskEngineV2(self.path, self.registry)
        self.ledger = CycleLedger("first", 1, 51, 51, 0, 21, 0, self.now, True)
        self.account = AccountSnapshot(51, 51, 51, 0, 0, 0, 0, {}, {}, self.ledger,
                                       self.now, True, True)
        self.quote = MarketQuote("ABC", 9.9, 10, self.now)
        self.session = MarketSession("ABC", True, self.now, True)
        self.proposal = Proposal("p1", "ABC", "BUY", 1, 10, .1, True, 2, 1,
                                 "Trend may reverse", "trend", "e1", self.now+120)

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def evaluate(self, **changes):
        return self.engine.evaluate(changes.get("account", self.account),
                                    changes.get("quote", self.quote),
                                    changes.get("session", self.session),
                                    changes.get("proposal", self.proposal), now=changes.get("now", self.now))

    def reject(self, **changes):
        result = self.evaluate(**changes)
        self.assertEqual(result.status, "REJECTED", result)
        self.assertFalse(result.execution_authorized)
        return result

    def test_positive_paper_only_and_cost_in_risk(self):
        d = self.evaluate()
        self.assertEqual(d.status, "PENDING_RESEARCH_ONLY")
        self.assertEqual(d.reserved_cash_cad, 10.1)
        self.assertEqual(d.reserved_risk_cad, 2.1)
        self.assertFalse(d.execution_authorized)

    def test_peak_cap_20_40_at_51(self):
        p = replace(self.proposal, fees_cad=0, gap_inclusive_loss_cad=20.4)
        self.assertEqual(self.evaluate(proposal=p).status, "PENDING_RESEARCH_ONLY")
        self.reject(proposal=replace(p, proposal_id="other", symbol="XYZ", gap_inclusive_loss_cad=20.40001),
                    quote=replace(self.quote, symbol="XYZ"), session=replace(self.session, symbol="XYZ"))

    def test_peak_cap_over_boundary_without_pending(self):
        self.reject(proposal=replace(self.proposal, fees_cad=0, gap_inclusive_loss_cad=20.40001))

    def test_cumulative_cycle_loss_and_existing_risk_reduce_budget(self):
        a = replace(self.account, ledger=replace(self.ledger, cumulative_loss_cad=19), open_risk_cad=.5)
        self.reject(account=a)
        self.assertEqual(self.evaluate(account=a, proposal=replace(self.proposal, gap_inclusive_loss_cad=1)).status,
                         "PENDING_RESEARCH_ONLY")

    def test_floor_projects_loss(self):
        a = replace(self.account, equity_cad=31, peak_equity_cad=31, own_cash_cad=31)
        self.reject(account=a)

    def test_persistent_halt_restart_and_explicit_reset(self):
        self.reject(account=replace(self.account, equity_cad=30, own_cash_cad=30))
        self.engine.close()
        self.engine = RiskEngineV2(self.path, self.registry)
        self.assertIn("PERSISTENT_HALT", self.reject().reason)
        with self.assertRaises(ValueError):
            self.engine.reset_halt(owner_confirmation=False, reason="no")
        self.engine.reset_halt(owner_confirmation=True, reason="Owner reviewed corrected reconciliation")
        self.assertEqual(self.evaluate().status, "PENDING_RESEARCH_ONLY")

    def test_cash_protection_and_no_borrowing(self):
        self.reject(account=replace(self.account, ledger=replace(self.ledger, protected_cash_cad=45)))
        self.reject(account=replace(self.account, own_cash_cad=10))
        self.reject(account=replace(self.account, open_orders_reserved_cash_cad=45))

    def test_cycle_one_rules(self):
        for changes in ({"starting_capital_cad": 52}, {"loss_cap_cad": 21.1}, {"verified": False}):
            self.reject(account=replace(self.account, ledger=replace(self.ledger, **changes)))

    def test_later_cycle_verified_stake_and_protected_reserve(self):
        ledger = CycleLedger("second", 2, 100, 20, 80, 10, 0, self.now, True)
        a = replace(self.account, equity_cad=100, peak_equity_cad=100, own_cash_cad=100, ledger=ledger)
        self.assertEqual(self.evaluate(account=a).status, "PENDING_RESEARCH_ONLY")
        self.reject(account=replace(a, ledger=replace(ledger, protected_cash_cad=79)))
        self.reject(account=replace(a, ledger=replace(ledger, trading_stake_cad=21)))

    def test_two_positions_counts_orders_and_pending(self):
        self.reject(account=replace(self.account, open_positions=1, open_order_count=1))
        a = replace(self.account, open_positions=1)
        self.assertEqual(self.evaluate(account=a).status, "PENDING_RESEARCH_ONLY")
        self.reject(account=a, proposal=replace(self.proposal, proposal_id="p2", symbol="XYZ"),
                    quote=replace(self.quote, symbol="XYZ"), session=replace(self.session, symbol="XYZ"))

    def test_exact_idempotency_and_economic_duplicates_survive_restart(self):
        first = self.evaluate()
        self.engine.close()
        self.engine = RiskEngineV2(self.path, self.registry)
        self.assertEqual(self.evaluate(), first)
        self.assertEqual(len(self.engine.pending(now=self.now)), 1)
        self.reject(proposal=replace(self.proposal, proposal_id="p2"))
        self.reject(proposal=replace(self.proposal, quantity=2))

    def test_expiry_keeps_cash_reservation_and_blocks_duplicate(self):
        self.evaluate()
        later = self.now+121
        a = replace(self.account, timestamp=later, ledger=replace(self.ledger, timestamp=later))
        q = replace(self.quote, timestamp=later)
        s = replace(self.session, timestamp=later)
        result = self.evaluate(account=a, quote=q, session=s, now=later)
        self.assertEqual(result.status, "EXPIRED_REVIEW_REQUIRED")
        row = self.engine.pending(now=later)[0]
        self.assertEqual(row["review_status"], "EXPIRED_REVIEW_REQUIRED")
        self.assertEqual(row["cash"], 10.1)
        self.reject(account=a, quote=q, session=s, now=later,
                    proposal=replace(self.proposal, proposal_id="p2", expires_at=later+60))

    def test_explicit_release_and_terminal_id(self):
        self.evaluate()
        with self.assertRaises(ValueError):
            self.engine.resolve("p1", status="OWNER_CANCELLED", owner_confirmation=False,
                                reason="reviewed", reconciled_account=self.account, now=self.now)
        self.engine.resolve("p1", status="OWNER_CANCELLED", owner_confirmation=True,
                            reason="Owner confirmed no manual order", reconciled_account=self.account, now=self.now)
        self.assertEqual(self.engine.pending(now=self.now), [])
        self.reject()
        self.assertEqual(self.evaluate(proposal=replace(self.proposal, proposal_id="p2")).status,
                         "PENDING_RESEARCH_ONLY")

    def test_sell_bounded_holdings_and_reserved_sales(self):
        a = replace(self.account, holdings={"ABC": 3}, open_positions=1, own_cash_cad=21,
                    sell_reserved_quantities={"ABC": 2})
        p = replace(self.proposal, side="SELL", limit_price=9.9, expected_net_profit_cad=-1)
        self.assertEqual(self.evaluate(account=a, proposal=p).status, "PENDING_RESEARCH_ONLY")
        self.reject(account=a, proposal=replace(p, proposal_id="p2", quantity=2))
        self.assertEqual(self.engine.pending(now=self.now)[0]["risk"], 0)

    def test_sell_never_short_and_halt_allows_exit_research(self):
        p = replace(self.proposal, side="SELL", limit_price=9.9)
        self.reject(proposal=p)
        a = replace(self.account, equity_cad=30, own_cash_cad=20, holdings={"ABC": 1}, open_positions=1)
        self.assertEqual(self.evaluate(account=a, proposal=p).status, "PENDING_RESEARCH_ONLY")

    def test_quotes_and_timestamps_fail_closed(self):
        for value in (float("nan"), float("inf"), None, "1000000", True, self.now+1, self.now-31):
            self.reject(quote=replace(self.quote, timestamp=value))
        for q in (replace(self.quote, bid=11), replace(self.quote, ask=0), replace(self.quote, bid=float("nan"))):
            self.reject(quote=q)
        for value in (None, float("nan"), self.now+1, self.now-61):
            self.reject(account=replace(self.account, timestamp=value))
            self.reject(session=replace(self.session, timestamp=value))

    def test_strategy_and_session_validation(self):
        self.reject(proposal=replace(self.proposal, strategy_id="invented"))
        self.reject(proposal=replace(self.proposal, evidence_id="wrong"))
        self.reject(session=replace(self.session, is_open=False))
        self.reject(session=replace(self.session, verified=False))
        for evidence in (StrategyEvidence("e1", self.now-31*86400, self.now+1000, True),
                         StrategyEvidence("e1", self.now+1, self.now+1000, True),
                         StrategyEvidence("e1", self.now-1, self.now, True)):
            self.engine.registry = {"trend": evidence}
            self.reject()

    def test_missing_cost_model_ev_counter_thesis_and_fx_rejected(self):
        for field in ("fees_cad", "gap_inclusive_loss_cad", "expected_net_profit_cad", "expires_at", "limit_price"):
            for value in (None, float("nan"), float("inf"), True):
                self.reject(proposal=replace(self.proposal, **{field: value}))
        for changes in ({"fees_known": False}, {"fees_cad": -1}, {"gap_inclusive_loss_cad": 0},
                        {"expected_net_profit_cad": 0}, {"counter_thesis": ""}, {"currency": "USD"},
                        {"quantity": True}, {"quantity": 10**1000}):
            self.reject(proposal=replace(self.proposal, **changes))

    def test_account_and_ledger_numeric_validation(self):
        for field in ("equity_cad", "peak_equity_cad", "own_cash_cad", "open_risk_cad"):
            self.reject(account=replace(self.account, **{field: float("nan")}))
        self.reject(account=replace(self.account, reconciled=False))
        self.reject(account=replace(self.account, open_orders_verified=False))
        self.reject(account=replace(self.account, holdings={"ABC": 1}))
        self.reject(account=replace(self.account, ledger=replace(self.ledger, loss_cap_cad=float("nan"))))

    def test_loss_budget_cannot_be_replenished(self):
        a = replace(self.account, ledger=replace(self.ledger, cumulative_loss_cad=1))
        self.evaluate(account=a)
        self.assertIn("replenish", self.reject().reason)

    def test_peak_cannot_be_lowered_and_zero_equity_halts(self):
        self.reject(account=replace(self.account, equity_cad=0, own_cash_cad=0))
        self.engine.reset_halt(owner_confirmation=True, reason="Reconciled")
        self.assertIn("Peak equity", self.reject(account=replace(self.account, equity_cad=50,
                                                                 own_cash_cad=50, peak_equity_cad=50)).reason)

    def test_aggregate_pending_risk_and_existing_investments(self):
        first = replace(self.proposal, gap_inclusive_loss_cad=15)
        self.assertEqual(self.evaluate(proposal=first).status, "PENDING_RESEARCH_ONLY")
        second = replace(self.proposal, proposal_id="p2", symbol="XYZ", gap_inclusive_loss_cad=6)
        self.assertIn("risk budget", self.reject(proposal=second, quote=replace(self.quote, symbol="XYZ"),
                                                  session=replace(self.session, symbol="XYZ")).reason)

    def test_cycle_stake_not_reused_alongside_existing_holdings(self):
        ledger = CycleLedger("second", 2, 100, 20, 60, 10, 0, self.now, True)
        a = replace(self.account, equity_cad=100, peak_equity_cad=100, own_cash_cad=80,
                    ledger=ledger, holdings={"XYZ": 1}, open_positions=1)
        self.assertIn("cycle cash", self.reject(account=a).reason)

    def test_resolve_requires_fresh_account_and_new_cycle_preserves_reserve(self):
        a = replace(self.account, ledger=replace(self.ledger, protected_cash_cad=10))
        self.evaluate(account=a)
        with self.assertRaises(ValueError):
            self.engine.resolve("p1", status="OWNER_EXECUTED_RECONCILED", owner_confirmation=True,
                                reason="Manual fill", reconciled_account=replace(a, timestamp=self.now-61), now=self.now)
        self.engine.resolve("p1", status="OWNER_CANCELLED", owner_confirmation=True,
                            reason="No order outstanding", reconciled_account=a, now=self.now)
        newer = CycleLedger("second", 2, 51, 41, 9, 20, 0, self.now, True)
        self.assertIn("protected reserve", self.reject(account=replace(a, ledger=newer)).reason)


if __name__ == "__main__":
    unittest.main()
