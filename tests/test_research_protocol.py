import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backtesting.research_protocol import (declaration, register, digest, deadline,
    trials, partition_candidates, freeze_selection, assign_splits)
from backtesting.research_statistics import interval, metrics, paired_comparison, concentration, overlap


class ResearchProtocolTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 17, 6, tzinfo=timezone.utc)

    def test_grid_and_execution_multiplicity_declared(self):
        protocol = declaration(self.now)
        self.assertEqual(len(trials()), 12)
        self.assertEqual(len({t["trial_id"] for t in trials()}), 12)
        self.assertEqual(len(protocol["execution_scenarios"]), 6)
        self.assertEqual(protocol["execution_scenario_count"], 72)
        self.assertEqual(protocol["trusted_export_receipt_hashes"], [])
        self.assertFalse(protocol["live_ready"])

    def test_registration_immutable_and_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "protocol.json"
            first = register(path, self.now)
            self.assertEqual(first, register(path, self.now + timedelta(days=5)))
            bad = json.loads(path.read_text());bad["protocol"]["trial_count"] = 1
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, "PROTOCOL_HASH_MISMATCH"):
                register(path, self.now)

    def test_early_close_horizon_and_naive_time(self):
        # Friday after Thanksgiving closes13:00ET; cutoff12:55ET.
        self.assertEqual(deadline("2026-11-27T10:00:00-05:00", "H120").hour, 17)
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT_HOLDING_WINDOW"):
            deadline("2026-11-27T10:56:00-05:00", "H120")
        with self.assertRaises(ValueError):
            deadline(datetime(2026, 10, 19, 15), "H60")
        with self.assertRaises(ValueError):
            deadline("2026-10-17T10:00:00-04:00", "H60")

    def test_verified_session_sequence_only(self):
        protocol = declaration(self.now)
        self.assertEqual(assign_splits(protocol, ["2026-10-19", "2026-10-20"])["development"], ["2026-10-19", "2026-10-20"])
        for days in (["2026-10-20", "2026-10-19"], ["2026-10-19", "2026-10-19"], ["2099-10-19"], ["2026-10-17"]):
            with self.subTest(days=days):
                if days == ["2026-10-17"]:
                    self.assertEqual(assign_splits(protocol, days)["development"], [])
                else:
                    with self.assertRaises(ValueError):assign_splits(protocol, days)

    def test_purge_planned_outcome_not_short_realized_exit(self):
        windows = {"development": ("2026-10-19T13:30:00Z", "2026-10-20T13:30:00Z"),
                   "sealed_final": ("2026-10-20T13:30:00Z", "2026-10-21T13:30:00Z")}
        row = dict(candidate_id="a", decision_at="2026-10-20T13:29:00Z", planned_exit_at="2026-10-20T14:29:00Z", actual_exit_at="2026-10-20T13:29:30Z")
        parts, excluded = partition_candidates([row], windows)
        self.assertEqual(parts["development"], [])
        self.assertEqual(excluded[0]["reason"], "OUTCOME_WINDOW_OVERLAPS_SPLIT")

    def test_final_seal_freeze_and_contamination(self):
        windows = {"sealed_final": ("2026-12-01T14:30:00Z", "2026-12-31T21:00:00Z")}
        row = dict(candidate_id="a", trial_id=trials()[0]["trial_id"], decision_at="2026-12-01T15:00:00Z", planned_exit_at="2026-12-01T16:00:00Z")
        self.assertEqual(partition_candidates([row], windows)[1][0]["reason"], "SEALED_FINAL_NOT_OPENED")
        with self.assertRaises(ValueError):partition_candidates([row], windows, release_final=True)
        frozen = dict(protocol_sha256="hash", frozen_at="2026-11-30T15:00:00Z",trial_ids=[trials()[0]["trial_id"]],validation_results_sha256="a"*64)
        self.assertEqual(len(partition_candidates([row], windows, release_final=True, frozen_selection=frozen, protocol_sha256="hash")[0]["sealed_final"]), 1)
        with self.assertRaises(ValueError):partition_candidates([row], windows, final_used_for_tuning=True)
        frozen["frozen_at"] = "2026-12-01T15:00:00Z"
        with self.assertRaises(ValueError):partition_candidates([row], windows, release_final=True, frozen_selection=frozen, protocol_sha256="hash")

    def test_final_only_frozen_trial_and_nonoverlapping_splits(self):
        windows={"sealed_final":("2026-12-01T14:30:00Z","2026-12-31T21:00:00Z")}
        row=dict(candidate_id="a",trial_id=trials()[1]["trial_id"],decision_at="2026-12-01T15:00:00Z",planned_exit_at="2026-12-01T16:00:00Z")
        frozen=dict(protocol_sha256="hash",frozen_at="2026-11-30T15:00:00Z",trial_ids=[trials()[0]["trial_id"]],validation_results_sha256="a"*64)
        parts,excluded=partition_candidates([row],windows,release_final=True,frozen_selection=frozen,protocol_sha256="hash")
        self.assertEqual(parts["sealed_final"],[])
        self.assertEqual(excluded[0]["reason"],"TRIAL_NOT_SELECTED_BEFORE_FINAL")
        with self.assertRaisesRegex(ValueError,"NONOVERLAPPING"):
            partition_candidates([],{"development":("2026-10-01T00:00:00Z","2026-10-20T00:00:00Z"),"validation":("2026-10-19T00:00:00Z","2026-10-30T00:00:00Z")})

    def test_future_features_refused_and_selection_single_use(self):
        row = dict(candidate_id="a", decision_at="2026-10-19T15:00:00Z", planned_exit_at="2026-10-19T16:00:00Z", features_through="2026-10-19T15:01:00Z")
        with self.assertRaises(ValueError):partition_candidates([row], {})
        with tempfile.TemporaryDirectory() as folder:
            envelope = register(Path(folder) / "protocol.json", self.now)
            output = Path(folder) / "frozen.json"
            freeze_selection(output, envelope, [trials()[0]["trial_id"]], "a" * 64, self.now)
            with self.assertRaises(FileExistsError):freeze_selection(output, envelope, [trials()[1]["trial_id"]], "b" * 64, self.now)


class ResearchStatisticsTests(unittest.TestCase):
    def rows(self, count=20):
        start = datetime(2026, 9, 1, 15, tzinfo=timezone.utc)
        return [dict(candidate_id=str(i), decision_at=(start + timedelta(days=i)).isoformat(),
                     actual_exit_at=(start + timedelta(days=i, minutes=60)).isoformat(),
                     status="CLOSED", net_pnl_usd=(-1 if i % 2 else 3), premium_return=.01,
                     direction="CALL", event_label="UNKNOWN", regime="MIXED") for i in range(count)]

    def test_insufficient_day_blocks_is_not_positive(self):
        result = interval(self.rows(19))
        self.assertEqual(result["status"], "INSUFFICIENT_DAY_BLOCKS")
        self.assertIsNone(result["bonferroni_simultaneous_95"])

    def test_day_block_reproducibility_and_multiplicity(self):
        rows = self.rows()
        self.assertEqual(interval(rows, repetitions=200), interval(rows, repetitions=200))
        one = interval(rows, trials=1, repetitions=200)
        many = interval(rows, trials=72, repetitions=200)
        self.assertLess(many["bonferroni_simultaneous_95"][0], one["bonferroni_simultaneous_95"][0])

    def test_metrics_missing_population_and_concentration(self):
        rows = self.rows(4) + [dict(status="UNRESOLVED_DATA", net_pnl_usd=None)]
        result = metrics(rows)
        self.assertEqual(result["closed"], 4);self.assertEqual(result["unresolved"], 1)
        self.assertEqual(result["mean_pnl_usd"], 1)
        self.assertEqual(result["profit_factor"], 3)
        self.assertIn("not future", result["win_fraction_definition"])
        self.assertIn("UNKNOWN", concentration(rows)["groups"]["event"])

    def test_baseline_pairs_and_clock_refusal(self):
        rows = self.rows();baseline = [dict(row, net_pnl_usd=0) for row in rows[:-1]]
        result = paired_comparison(rows, baseline, repetitions=200)
        self.assertEqual(result["paired"], 19);self.assertEqual(result["unpaired_strategy"], 1)
        baseline[0]["decision_at"] = "2026-09-01T15:01:00Z"
        with self.assertRaisesRegex(ValueError, "BASELINE_CLOCK_MISMATCH"):
            paired_comparison(rows, baseline)

    def test_overlap_counts_at_equal_exit_entry(self):
        rows = self.rows(2);rows[1]["decision_at"] = rows[0]["actual_exit_at"]
        self.assertEqual(overlap(rows)["maximum_overlapping_closed_observations"], 1)


if __name__ == "__main__":unittest.main()
