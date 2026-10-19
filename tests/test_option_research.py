import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backtesting.option_research import Dataset, load, replay, select, portfolio, portfolio_marks, assess, random_direction, VERSION
from backtesting.research_statistics import summarize
from backtesting.research_protocol import declaration
from core.isolation import assert_real


class OptionResearchTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 12, 14, tzinfo=timezone.utc)
        self.quotes = [];self.chains = []
        for right in ("C", "P"):
            symbol = "SPY261016" + right + "00780000"
            base = dict(symbol=symbol, provider="fixture", feed_quality="SIMULATED", data_type="option_quote", bid_size=10, ask_size=10,
                        currency="USD",premium_units="USD_PER_SHARE",size_units="CONTRACTS")
            for seconds in (0, 15, 60, 3600, 3615, 3660):
                self.quotes.append({**base, "source_timestamp": (self.now + timedelta(seconds=seconds)).isoformat(),
                                    "bid": 1.0 if seconds < 3600 else 1.5, "ask": 1.05 if seconds < 3600 else 1.55})
            self.chains.append(dict(symbol=symbol, provider="fixture", feed_quality="SIMULATED", data_type="chain_contract",
                source_timestamp=self.now.isoformat(), underlying="SPY", right=right, expiry="2026-10-16", strike=780., multiplier=100,
                listed=True, delta=.5 if right == "C" else -.5, greeks_timestamp=self.now.isoformat(), greeks_basis="CURRENT",
                volume=200, volume_asof=self.now.isoformat(), open_interest=300,
                open_interest_asof=(self.now - timedelta(days=1)).isoformat()))
        self.candidate = dict(candidate_id="idea", trial_id="trial", decision_at=self.now.isoformat(),
            planned_exit_at=(self.now + timedelta(hours=1)).isoformat(), direction="CALL", trigger_level=780.,
            entry_valid_until=(self.now + timedelta(minutes=10)).isoformat(), outcome_status="CLOSED",
            exit_event_at=(self.now + timedelta(hours=1)).isoformat(), outcome="TIME_EXIT")
        self.candidate["direction_outcomes"] = {"PUT": dict(outcome_status="CLOSED", exit_event_at=self.candidate["exit_event_at"], outcome="TIME_EXIT")}
        self.scenario = dict(human_response_seconds=0, slippage_per_side=.01, fee_per_contract_per_side=.65)
        self.limits = dict(research_cash_usd=10000, maximum_open_premium_usd=1500, maximum_contracts_per_idea=1, borrow=False)

    def dataset(self):
        return Dataset(self.quotes, self.chains, provider="fixture", fixture=True, capture_mode="SIMULATED")

    def test_ask_entry_bid_exit_fees_and_immutable_named_prices(self):
        result = replay(self.dataset(), self.candidate, self.scenario)
        self.assertEqual(result["status"], "CLOSED")
        self.assertAlmostEqual(result["modeled_entry_fill"], 1.06)
        self.assertAlmostEqual(result["modeled_exit_fill"], 1.49)
        self.assertAlmostEqual(result["net_pnl_usd"], 41.7)
        self.assertEqual(result["confirmation_trigger"], 780.)
        self.assertAlmostEqual(result["reference_quote_midpoint"], 1.025)
        self.assertIsNone(result["actual_user_reported_fill"])
        self.assertFalse(result["evidence_eligible"])
        with self.assertRaises(ValueError):assert_real(result)

    def test_human_delay_limit_and_deadline_no_bar_touch_fill(self):
        delayed = dict(self.scenario, human_response_seconds=15)
        self.assertEqual(replay(self.dataset(), self.candidate, delayed)["entry_at"], (self.now + timedelta(seconds=15)).isoformat())
        self.candidate["option_limit"] = 1.0
        self.assertEqual(replay(self.dataset(), self.candidate, self.scenario)["reason"], "QUOTED_MARKETABLE_PRICE_EXCEEDS_LIMIT")
        self.candidate.pop("option_limit");self.candidate["entry_valid_until"] = self.now.isoformat()
        self.assertEqual(replay(self.dataset(), self.candidate, self.scenario)["reason"], "ENTRY_DEADLINE_REACHED")

    def test_future_quote_and_older_quote_do_not_become_fresh(self):
        dataset = self.dataset();symbol = self.chains[0]["symbol"]
        self.assertIsNone(dataset.quote(symbol, self.now - timedelta(seconds=1)))
        self.assertIsNone(dataset.quote(symbol, self.now + timedelta(seconds=6)))
        self.assertEqual(dataset.quote(symbol, self.now + timedelta(seconds=5))["bid"], 1.)

    def test_chain_greeks_expiry_liquidity_and_spread_refusals(self):
        for change in (dict(greeks_basis="PREVIOUS_DAY"), dict(delta=.2), dict(greeks_timestamp=(self.now - timedelta(seconds=61)).isoformat()), dict(open_interest=0)):
            with self.subTest(change=change):
                old=copy.deepcopy(self.chains);self.chains[0].update(change)
                self.assertIsNone(select(self.dataset(), self.now, self.now + timedelta(hours=1), "CALL")[0]);self.chains=old
        self.assertIsNone(select(self.dataset(), self.now, datetime(2026,10,16,18,tzinfo=timezone.utc), "CALL")[0])
        self.quotes[0]["ask"] = 2.
        self.assertIsNone(select(self.dataset(), self.now, self.now + timedelta(hours=1), "CALL")[0])

    def test_invalid_chain_terms_and_duplicate_quotes_rejected(self):
        self.chains[0]["strike"] = 781
        with self.assertRaises(ValueError):self.dataset()
        self.chains[0]["strike"] = 780
        self.quotes.insert(1, copy.deepcopy(self.quotes[0]))
        with self.assertRaises(ValueError):self.dataset()

    def test_missing_exit_and_underlying_gap_reserve_capital(self):
        self.quotes = [row for row in self.quotes if datetime.fromisoformat(row["source_timestamp"]) < self.now + timedelta(hours=1)]
        result = replay(self.dataset(), self.candidate, self.scenario)
        self.assertEqual(result["status"], "UNRESOLVED_DATA")
        self.assertIsNone(result["net_pnl_usd"]);self.assertGreater(result["entry_debit_usd"], 0)
        self.candidate["outcome_status"] = "UNRESOLVED_DATA";self.candidate["exit_event_at"] = None
        self.assertEqual(replay(self.dataset(), self.candidate, self.scenario)["status"], "UNRESOLVED_DATA")
        limits = dict(self.limits, maximum_open_premium_usd=150)
        second = dict(self.candidate, candidate_id="second")
        records = portfolio(self.dataset(), [self.candidate,second], self.scenario, limits)
        self.assertEqual(records[0]["status"], "UNRESOLVED_DATA")
        self.assertEqual(records[1]["reason"], "RESEARCH_CASH_OR_PREMIUM_EXPOSURE_LIMIT")

    def test_cash_limits_and_baseline_deterministic(self):
        result=portfolio(self.dataset(), [self.candidate], self.scenario, dict(self.limits,research_cash_usd=100))[0]
        self.assertEqual(result["status"], "NOT_FILLED")
        chosen=random_direction("trial", "idea")
        self.assertEqual(chosen, random_direction("trial", "idea"))
        bench=portfolio(self.dataset(), [self.candidate], self.scenario,self.limits,baseline=True)[0]
        self.assertEqual(bench["benchmark"], "MATCHED_CLOCK_RANDOM_DIRECTION_V1")
        self.assertEqual(bench["decision_at"],self.candidate["decision_at"])
        with self.assertRaises(ValueError):portfolio(self.dataset(),[],self.scenario,dict(self.limits,borrow=True))

    def test_unaudited_genuine_labels_and_synthetic_real_mode_rejected(self):
        with self.assertRaises(ValueError):Dataset(self.quotes,self.chains,provider="fixture")
        quotes=copy.deepcopy(self.quotes);chains=copy.deepcopy(self.chains)
        for row in quotes+chains:row["feed_quality"]="OPRA"
        dataset=Dataset(quotes,chains,provider="fixture")
        self.assertEqual(replay(dataset,self.candidate,self.scenario)["reason"],"OPTION_SOURCE_AUDIT_NOT_VERIFIED")

    def test_offline_manifest_hash_audit_and_missing_dataset(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/"manifest.json";protocol=declaration()
            self.assertEqual(load(path,protocol)[0]["status"],"UNAVAILABLE")
            descriptors={}
            for name,rows in (("quotes",self.quotes),("chains",self.chains)):
                raw="\n".join(json.dumps(row) for row in rows).encode();(root/(name+".jsonl")).write_bytes(raw)
                descriptors[name]=dict(file=name+".jsonl",sha256=hashlib.sha256(raw).hexdigest(),row_count=len(rows))
            manifest=dict(schema_version=VERSION,underlying="SPY",provider="fixture",feed="SIMULATED",source_url="https://example.invalid/fixture",
                capture_mode="SIMULATED",retrieved_at="2026-10-13T00:00:00Z",**descriptors)
            path.write_text(json.dumps(manifest))
            self.assertEqual(load(path,protocol,fixtures=True)[0]["status"],"SIMULATED_ONLY")
            self.assertEqual(load(path,protocol)[0]["status"],"REJECTED")
            (root/"quotes.jsonl").write_text("{}")
            self.assertEqual(load(path,protocol,fixtures=True)[0]["status"],"REJECTED")

    def test_quote_event_drawdown_and_missing_marks_are_explicit(self):
        dataset=self.dataset();records=portfolio(dataset,[self.candidate],self.scenario,self.limits)
        marks=portfolio_marks(dataset,records,self.scenario)
        self.assertEqual(marks["status"],"UNAVAILABLE_INCOMPLETE_MARKS")
        self.assertGreater(marks["active_quote_intervals_exceeding_five_seconds"],0)
        dense=[]
        for symbol in dataset.quotes:
            template=dataset.quotes[symbol][0]
            for seconds in range(0,3601,5):
                dense.append({**template,"source_timestamp":(self.now+timedelta(seconds=seconds)).isoformat()})
        dense_dataset=Dataset(dense,self.chains,provider="fixture",fixture=True,capture_mode="SIMULATED")
        dense_records=portfolio(dense_dataset,[self.candidate],self.scenario,self.limits)
        complete=portfolio_marks(dense_dataset,dense_records,self.scenario)
        self.assertEqual(complete["status"],"QUOTE_EVENT_MARKS_AVAILABLE")
        self.assertLess(complete["max_drawdown_usd"],0)
        records[0].update(status="UNRESOLVED_DATA",actual_exit_at=None)
        marks=portfolio_marks(dataset,records,self.scenario)
        self.assertIsNone(marks["max_drawdown_usd"])

    def test_no_research_assessment_promotes_a_strategy_or_fixture(self):
        records=portfolio(self.dataset(),[self.candidate],self.scenario,self.limits)
        result=assess(summarize(records,records),declaration(),population="SIMULATED")
        self.assertEqual(result["status"],"RESEARCH_EVIDENCE_INSUFFICIENT")
        self.assertFalse(result["strategy_validated"]);self.assertFalse(result["live_ready"])

    def test_price_size_units_and_malformed_greek_times_fail_closed(self):
        self.quotes[0]["size_units"]="SHARES"
        with self.assertRaisesRegex(ValueError,"UNITS_REQUIRED"):self.dataset()
        self.quotes[0]["size_units"]="CONTRACTS";self.chains[0]["greeks_timestamp"]="not-a-time"
        self.assertIsNone(select(self.dataset(),self.now,self.now+timedelta(hours=1),"CALL")[0])


if __name__ == "__main__":unittest.main()
