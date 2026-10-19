import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from backtesting.underlying_study import load_bars, price_frame, feature_snapshots, context, generate, outcome, evaluate, _daily
from backtesting.research_protocol import declaration
from core.sessions import ET


class UnderlyingStudyTests(unittest.TestCase):
    def bars(self, n=90, start=None):
        start=start or datetime(2026,10,12,9,30,tzinfo=ET)
        return [dict(timestamp=int((start+timedelta(minutes=i)).timestamp()),open=100.,high=100.3,low=99.7,close=100.,volume=100,
                     provider="fixture",feed_quality="SIMULATED") for i in range(n)]

    def candidate(self):
        clock=datetime(2026,10,12,14,tzinfo=timezone.utc)
        return dict(candidate_id="a",trial_id="trial",decision_at=clock.isoformat(),planned_exit_at=(clock+timedelta(minutes=3)).isoformat(),
                    entry_valid_until=(clock+timedelta(minutes=2)).isoformat(),direction="CALL",reference_price=100.,reference_price_kind="COMPLETED_BAR_CLOSE_RESEARCH_ONLY",risk_distance=1.,trigger_level=100.,feed_quality="SIMULATED")

    def test_next_genuine_minute_entry_and_costs(self):
        candidate=self.candidate();bars=self.bars(3,datetime(2026,10,12,14,tzinfo=timezone.utc))
        result=outcome(candidate,bars)
        self.assertEqual(result["outcome_status"],"CLOSED");self.assertEqual(result["outcome"],"TIME_EXIT")
        self.assertAlmostEqual(result["modeled_entry_fill"],100.02);self.assertAlmostEqual(result["net_pnl_usd"],-.04)
        self.assertIsNone(result["reference_quote_midpoint"])

    def test_ambiguous_stop_first_and_missing_minutes_not_filled(self):
        candidate=self.candidate();bars=self.bars(3,datetime(2026,10,12,14,tzinfo=timezone.utc))
        bars[0].update(high=103.,low=98.)
        self.assertEqual(outcome(candidate,bars)["outcome"],"STOP_FIRST_AMBIGUOUS")
        bars=self.bars(3,datetime(2026,10,12,14,tzinfo=timezone.utc));bars.pop(1)
        result=outcome(candidate,bars)
        self.assertEqual(result["status"],"UNRESOLVED_DATA");self.assertIsNone(result["net_pnl_usd"])

    def test_baseline_has_separate_opposite_direction_outcome(self):
        candidate=self.candidate();bars=self.bars(3,datetime(2026,10,12,14,tzinfo=timezone.utc))
        bars[0].update(high=100.4,low=98.,close=99.)
        actual,baseline=evaluate([candidate],bars)
        self.assertEqual(actual[0]["direction_outcomes"]["CALL"]["outcome"],"INVALIDATION")
        self.assertEqual(actual[0]["direction_outcomes"]["PUT"]["outcome"],"TARGET_2R")
        self.assertEqual(baseline[0]["decision_at"],candidate["decision_at"])
        self.assertFalse(actual[0]["evidence_eligible"])
        self.assertEqual(actual[0]["reference_price"],candidate["reference_price"])
        self.assertEqual(actual[0]["reference_price_kind"],"COMPLETED_BAR_CLOSE_RESEARCH_ONLY")
        self.assertEqual(actual[0]["modeled_entry_price_basis"],"NEXT_MINUTE_OPEN_PROXY_NOT_QUOTE")

    def test_unconfirmed_swing_needs_two_later_completed_bars(self):
        bars=self.bars(8);bars[3]["high"]=105
        self.assertNotIn(105,price_frame(bars[:5])["swing_highs"])
        self.assertIn(105,price_frame(bars[:6])["swing_highs"])

    def test_future_candles_and_incomplete_aggregate_never_enter_features(self):
        bars=self.bars(90);seen=[]
        def capture(ctx,quote,clock,**kwargs):
            self.assertIsNone(quote)
            self.assertEqual(kwargs["reference_price"],ctx["bars"][-1]["close"])
            seen.append((clock.isoformat(),copy.deepcopy(ctx["features"])))
            return []
        with patch("core.research_horizons.candidates",side_effect=capture):
            generate(bars,declaration(),simulation=True)
        original=seen[0];seen.clear();bars[-1].update(high=900,close=899)
        with patch("core.research_horizons.candidates",side_effect=capture):
            generate(bars,declaration(),simulation=True)
        self.assertEqual(original,seen[0])
        clock=datetime.fromisoformat(original[0]);last_5m=original[1]["5m"]["timestamp"]
        self.assertLessEqual(last_5m+300,clock.timestamp())

    def test_synthetic_production_research_and_unordered_input_rejected(self):
        with self.assertRaisesRegex(ValueError,"SYNTHETIC"):generate(self.bars(),declaration())
        rows=self.bars();rows[0],rows[1]=rows[1],rows[0]
        with self.assertRaisesRegex(ValueError,"ORDERED"):generate(rows,declaration(),simulation=True)

    def test_daily_requires_complete_verified_session_early_close_dst(self):
        early=self.bars(210,datetime(2026,11,27,9,30,tzinfo=ET))
        self.assertEqual(len(_daily(early)),1);self.assertEqual(_daily(early[:-1]),[])
        before=self.bars(390,datetime(2026,10,30,9,30,tzinfo=ET))
        after=self.bars(390,datetime(2026,11,2,9,30,tzinfo=ET))
        self.assertEqual(len(_daily(before+after)),2)
        self.assertEqual(datetime.fromtimestamp(after[0]["timestamp"],timezone.utc).hour,14)
        self.assertEqual(datetime.fromtimestamp(before[0]["timestamp"],timezone.utc).hour,13)

    def test_readonly_history_duplicate_conflict_and_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"history.sqlite";db=sqlite3.connect(path)
            db.execute("CREATE TABLE session_bars(id TEXT,provider TEXT,feed_quality TEXT,source_timestamp TEXT,recorded_at TEXT,payload TEXT)")
            row=self.bars(1)[0];row.update(provider="alpaca-iex",feed_quality="IEX",source="REST_BACKFILL")
            source=datetime.fromtimestamp(row["timestamp"],timezone.utc).isoformat();recorded="2026-10-12T14:30:00Z"
            for key in ("a","b"):db.execute("INSERT INTO session_bars VALUES(?,?,?,?,?,?)",(key,"alpaca-iex","IEX",source,recorded,json.dumps(row)))
            db.commit();db.close()
            bars,evidence=load_bars(path)
            self.assertEqual(len(bars),1);self.assertEqual(evidence["identical_duplicate_records"],1)
            self.assertEqual(evidence["coverage"][0]["missing_minutes"],389)
            self.assertEqual(evidence["input_snapshot_sha256"],load_bars(path)[1]["input_snapshot_sha256"])
            db=sqlite3.connect(path);row["close"]=100.1
            db.execute("INSERT INTO session_bars VALUES(?,?,?,?,?,?)",("c","alpaca-iex","IEX",source,recorded,json.dumps(row)));db.commit();db.close()
            self.assertEqual(load_bars(path)[0],[])
            self.assertEqual(len(load_bars(path)[1]["conflicting_revision_minutes"]),1)

    def test_missing_history_is_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            rows,status=load_bars(Path(folder)/"absent.sqlite")
            self.assertEqual(rows,[]);self.assertEqual(status["status"],"UNAVAILABLE")

    def test_linear_feature_snapshots_match_full_prefix_exact_formulas(self):
        rows=self.bars(120)
        for i,row in enumerate(rows):
            row.update(close=100+i*.01+(i%7)*.03,high=101+(i%7)*.1,low=99-(i%9)*.05)
        snapshots=feature_snapshots(rows)
        for count in (1,9,14,15,20,21,49,50,77,120):
            expected=price_frame(rows[:count]);actual=snapshots[count-1]
            for key,value in expected.items():
                if isinstance(value,float):self.assertAlmostEqual(value,actual[key],places=11)
                else:self.assertEqual(value,actual[key])


if __name__=="__main__":unittest.main()
