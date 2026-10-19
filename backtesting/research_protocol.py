"""Immutable research declaration and leakage controls; never grants trading readiness.

This module performs no network requests and does not inspect private positions.
The historical exploratory population is deliberately separate from the sealed,
prospective session sequence beginning after registration.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from core.sessions import ET, market_session
from data.models import stamp

VERSION = "spy-horizon-study-v2"
FEATURE_VERSION = "completed-causal-price-features-v2"
HORIZONS = ("H60", "H120", "SESSION")
FAMILIES = ("TREND_PULLBACK_CONTINUATION", "ORB_RETEST")


def aware(value):
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("AWARE_TIMESTAMP_REQUIRED")
        return value.astimezone(timezone.utc)
    return stamp(value).astimezone(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def trials():
    """Twelve model variants, each with six separately disclosed execution scenarios."""
    answer = []
    for family, horizon, floor in itertools.product(FAMILIES, HORIZONS, (.5, .75)):
        item = dict(strategy_version="spy-horizon-comparison-v2", feature_version=FEATURE_VERSION,
                    family=family, horizon=horizon, stop_atr_floor=floor,
                    volume_ratio_min=1.2, target_r=2.0, full_exit=True)
        item["trial_id"] = f"{family}:{horizon}:atr{floor}"
        answer.append(item)
    return answer


def declaration(now=None):
    now = aware(now or datetime.now(timezone.utc))
    # This is prospective registration; already inspected October sessions cannot
    # be relabeled an untouched final test.
    first = max(date(2026, 10, 19), now.astimezone(ET).date() + timedelta(days=1))
    return {
        "schema_version": VERSION, "registered_at": now.isoformat(),
        "supersedes": "spy-horizon-study-v1, retained without evaluation; v2 aligns exact core horizon definitions before any outcome results are inspected",
        "earliest_prospective_date": first.isoformat(), "underlying": "SPY",
        "trials": trials(), "trial_count": 12, "execution_scenario_count": 72,
        "execution_scenarios": [dict(human_response_seconds=d, slippage_per_side=s,
                                     fee_per_contract_per_side=.65)
                                for d, s in itertools.product((0, 15, 60), (.01, .03))],
        "session_split": {"development": 20, "validation": 10, "sealed_final": 20},
        "split_rule": "Verified US trading-session ordinal; fixed before outcomes; purge planned windows crossing any split.",
        "selection_rule": "Select at most one trial using development and validation only; freeze selection and validation digest before sealed-final access.",
        "final_tuning_rule": "If final results influence tuning, mark final contaminated; require later untouched data and a new version.",
        "features": "Only completed genuine candles; confirmed swing points require two later completed candles. No fill-forward or continuity-only bars. H60 context15m+5m/ATR15m; H120 context30m+1h/ATR30m; SESSION context1h+daily/ATR1h. Both context trends must agree. Pullback is completed5m EMA9 reclaim using preceding EMA for preceding candle; ORB_RETEST uses genuine09:30-09:44 range, preceding minute beyond and latest minute retest. Latest minute volume>=1.2 prior10; reference within0.5 minuteATR of lastclose and on correct VWAP/trigger side.",
        "research_evaluation_cadence_seconds": 60,
        "operational_evaluation_cadence_seconds": 10,
        "telegram_status_cadence_seconds": 900,
        "entry_rule": "Research confirmation at completed minute close; next genuine minute open for underlying proxy. Options use a genuine timestamped ask available at decision plus human delay, subject to the declared limit and size.",
        "levels": "Stop uses signed structural distance of previous two completed5m bars with declared horizon-frame ATR floor; full exit at2R, invalidation or holding deadline. A1R marker does not sell a fraction.",
        "horizon_rule": "H60/H120 require the full interval before close minus5 minutes. SESSION exits close minus5 minutes and requires at least30 minutes remaining. No overnight positions.",
        "contract_rule": "Point-in-time listed standard SPY actual chain; expiry date strictly after holding-deadline ET date; matching OCC terms; current delta absolute .40-.55; current Greek age <=60 seconds; positive sized bid/ask and spread <=10%; OI >=100 and volume >=100 with their own as-of labels.",
        "option_fills": "Ask plus slippage entry, bid minus slippage exit, 100 multiplier, two-sided fees. Quote age <=5 seconds at decision; no bar-touch limit fills; missing quote or missing outcome minute is unresolved, not a zero return.",
        "underlying_costs": {"spread_assumption_usd": .02, "slippage_per_side_usd": .01,
                             "description": "Assumptions for separate proxy sensitivity only; not measured execution costs and never an option-return haircut."},
        "portfolio": {"research_cash_usd": 10000, "maximum_open_premium_usd": 1500,
                      "maximum_contracts_per_idea": 1, "borrow": False,
                      "unresolved_capital": "Reserved until a genuine exit; never assumed released."},
        "baselines": ["NO_TRADE_ZERO_RETURN", "MATCHED_CLOCK_RANDOM_DIRECTION_V1"],
        "baseline_definition": "SHA256 trial+candidate chooses CALL/PUT at the original decision clock. This randomizes direction, not entry time. Opposite contract must independently qualify; missing pairs are disclosed.",
        "uncertainty": "ET day-block bootstrap descriptive 95% intervals plus Bonferroni normal day-block simultaneous intervals over all 72 scenarios; correlated trades are not independent samples.",
        "acceptance": {"minimum_closed_option_observations": 100, "minimum_final_days": 20,
                       "minimum_days_for_uncertainty": 20,
                       "net_expectancy_simultaneous_lower_bound_above_zero": True,
                       "paired_baseline_simultaneous_lower_bound_above_zero": True,
                       "missing_outcomes_max_fraction": .05,
                       "maximum_single_day_fraction_of_positive_pnl": .25,
                       "worse_execution_must_pass": True,
                       "meaning": "Evidence for further prospective research only; no live authorization or future-profit claim."},
        "exclusions": ["Synthetic/indicative or unverified option data", "Unknown provider/feed",
                       "Incomplete chain provenance or revised terms", "Future/naive/out-of-order timestamps",
                       "Unconfirmed gaps or ambiguous missing-quote exits", "Outcome window crossing a split",
                       "Insufficient warmup", "Calendar coverage unavailable", "Final period already used for tuning"],
        "trusted_export_receipt_hashes": [],
        "external_data_rule": "Hashes establish consistency, not entitlement. A separately audited source receipt must be pinned before a new study version can qualify imported option data.",
        "strategy_validated": False, "live_ready": False,
    }


def register(path, now=None):
    """Create once. Re-running preserves the exact original registration."""
    path = Path(path)
    if path.exists():
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if digest(envelope["protocol"]) != envelope.get("protocol_sha256"):
            raise ValueError("PROTOCOL_HASH_MISMATCH")
        return envelope
    protocol = declaration(now)
    envelope = {"protocol": protocol, "protocol_sha256": digest(protocol)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(envelope, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return envelope


def deadline(decision, horizon):
    decision = aware(decision)
    if horizon not in HORIZONS:
        raise ValueError("UNKNOWN_RESEARCH_HORIZON")
    session = market_session(decision)
    if session.get("quality") != "DATA_OK" or not session["active"]:
        raise ValueError("VERIFIED_ACTIVE_SESSION_REQUIRED")
    local = decision.astimezone(ET)
    cutoff = local.replace(hour=session["close_minute"] // 60,
                           minute=session["close_minute"] % 60, second=0, microsecond=0) - timedelta(minutes=5)
    planned = cutoff if horizon == "SESSION" else decision + timedelta(minutes=int(horizon[1:]))
    minimum = 30 if horizon == "SESSION" else int(horizon[1:])
    if planned > cutoff or (planned - decision).total_seconds() < minimum * 60:
        raise ValueError("INSUFFICIENT_HOLDING_WINDOW")
    return planned.astimezone(timezone.utc)


def assign_splits(protocol, session_dates):
    """Only explicitly verified session dates are accepted; no guessed next year."""
    days = sorted(set(session_dates))
    if days != list(session_dates):
        raise ValueError("SESSION_SEQUENCE_MUST_BE_SORTED_UNIQUE")
    accepted = []
    for day in days:
        if day < protocol["earliest_prospective_date"]:
            continue
        check = market_session(datetime.combine(date.fromisoformat(day), time(12), ET))
        if check.get("quality") != "DATA_OK" or not check.get("active"):
            raise ValueError("UNVERIFIED_SESSION_DATE")
        accepted.append(day)
    answer = {};cursor = 0
    for name, count in protocol["session_split"].items():
        subset = accepted[cursor:cursor + count]
        answer[name] = subset
        cursor += count
    return answer


def partition_candidates(rows, windows, *, release_final=False, frozen_selection=None,
                         protocol_sha256=None, final_used_for_tuning=False):
    """Windows are [start,end); purge on PLANNED end, not convenient realized exits."""
    if final_used_for_tuning:
        raise ValueError("FINAL_CONTAMINATED_REQUIRE_LATER_DATA")
    intervals=sorted((aware(value[0]),aware(value[1]),name) for name,value in windows.items())
    if any(right<=left for left,right,_ in intervals) or any(right>next_left for (_,right,_),(next_left,_,_) in zip(intervals,intervals[1:])):
        raise ValueError("CHRONOLOGICAL_NONOVERLAPPING_SPLITS_REQUIRED")
    if release_final:
        if not frozen_selection or frozen_selection.get("protocol_sha256") != protocol_sha256:
            raise ValueError("FINAL_SEALED_SELECTION_NOT_FROZEN")
        selected=frozen_selection.get("trial_ids",[])
        if len(selected)!=1 or selected[0] not in {row["trial_id"] for row in trials()} or not re_hash(frozen_selection.get("validation_results_sha256")):
            raise ValueError("FROZEN_REGISTERED_SELECTION_AND_VALIDATION_DIGEST_REQUIRED")
        final_start = aware(windows["sealed_final"][0])
        if aware(frozen_selection["frozen_at"]) >= final_start:
            raise ValueError("SELECTION_FROZEN_AFTER_FINAL_BEGAN")
    parts = {key: [] for key in windows};excluded = []
    for row in rows:
        start = aware(row["decision_at"]);end = aware(row["planned_exit_at"])
        if end <= start or aware(row.get("features_through", row["decision_at"])) > start:
            raise ValueError("CAUSAL_WINDOW_INVALID")
        assigned = False
        for name, (left, right) in windows.items():
            left, right = aware(left), aware(right)
            if left <= start < right:
                assigned = True
                if end >= right:
                    excluded.append({"candidate_id": row["candidate_id"], "reason": "OUTCOME_WINDOW_OVERLAPS_SPLIT"})
                elif name == "sealed_final" and not release_final:
                    excluded.append({"candidate_id": row["candidate_id"], "reason": "SEALED_FINAL_NOT_OPENED"})
                elif name == "sealed_final" and row.get("trial_id") not in frozen_selection["trial_ids"]:
                    excluded.append({"candidate_id": row["candidate_id"], "reason": "TRIAL_NOT_SELECTED_BEFORE_FINAL"})
                else:
                    parts[name].append(row)
                break
        if not assigned:
            excluded.append({"candidate_id": row["candidate_id"], "reason": "OUTSIDE_DECLARED_SPLITS"})
    return parts, excluded


def re_hash(value):
    return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)


def freeze_selection(path, envelope, trial_ids, validation_digest, now=None):
    path = Path(path);now = aware(now or datetime.now(timezone.utc))
    valid = {row["trial_id"] for row in envelope["protocol"]["trials"]}
    if len(trial_ids) != 1 or not set(trial_ids) <= valid:
        raise ValueError("EXACTLY_ONE_REGISTERED_TRIAL_REQUIRED")
    if not re_hash(validation_digest):
        raise ValueError("VALIDATION_DIGEST_REQUIRED")
    payload = dict(protocol_sha256=envelope["protocol_sha256"], trial_ids=list(trial_ids),
                   validation_results_sha256=validation_digest, frozen_at=now.isoformat())
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload
