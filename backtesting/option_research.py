"""Offline genuine-BBO option replay with explicit refusal and fixture boundaries.

No provider endpoints are guessed. Data arrive from an audited local export or an
explicit in-memory fixture. This module cannot send, execute or mutate a ledger.
"""
from __future__ import annotations
import bisect
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from backtesting.research_protocol import aware, digest
from core.sessions import ET
from options.ledger import contract

VERSION = "genuine-option-bbo-replay-v1"
MAX_FILE_BYTES = 64 * 1024 * 1024


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def safe_url(value):
    parsed = urlsplit(value)
    return bool(parsed.scheme == "https" and parsed.hostname and not
                (parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port))


def _read_component(folder, descriptor):
    name = descriptor.get("file")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}\.jsonl", name):
        raise ValueError("LOCAL_COMPONENT_PATH_REQUIRED")
    path = folder / name
    if path.is_symlink() or path.resolve().parent != folder.resolve():
        raise ValueError("DATA_PATH_ESCAPE")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("DATASET_TOO_LARGE")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != descriptor.get("sha256"):
        raise ValueError("COMPONENT_HASH_MISMATCH")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if descriptor.get("row_count") != len(rows):
        raise ValueError("COMPONENT_ROW_COUNT_MISMATCH")
    return rows


def load(path, protocol, *, fixtures=False):
    """File hashes are consistency checks; source approval needs a pinned audit receipt.

    The initial protocol pins no receipts, so supplied files cannot silently
    promote themselves to accepted data by claiming entitlement in a manifest.
    """
    path = Path(path)
    if not path.exists():
        return {"status": "UNAVAILABLE", "reason": "GENUINE_OPTION_BBO_DATASET_NOT_CONFIGURED",
                "option_performance": None, "evidence_eligible": False,
                "strategy_validated": False, "live_ready": False}, None
    try:
        if path.stat().st_size > 65536:
            raise ValueError("MANIFEST_TOO_LARGE")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != VERSION or manifest.get("underlying") != "SPY":
            raise ValueError("OPTION_MANIFEST_SCHEMA_INVALID")
        if not safe_url(manifest["source_url"]):
            raise ValueError("SAFE_PUBLIC_SOURCE_URL_REQUIRED")
        if manifest.get("capture_mode") not in ("HISTORICAL_DOWNLOAD", "CONTEMPORANEOUS_CAPTURE", "SIMULATED"):
            raise ValueError("CAPTURE_MODE_REQUIRED")
        if manifest.get("feed") != ("SIMULATED" if fixtures else "OPRA"):
            raise ValueError("GENUINE_OPRA_REQUIRED")
        retrieved = aware(manifest["retrieved_at"])
        if retrieved > datetime.now(timezone.utc):
            raise ValueError("FUTURE_RETRIEVAL_TIME")
        quotes = _read_component(path.parent, manifest["quotes"])
        chains = _read_component(path.parent, manifest["chains"])
        receipt = manifest.get("source_verification_receipt", {})
        receipt_hash = digest(receipt)
        if not fixtures and (receipt.get("status") != "AUDITED_AUTHORIZED_SOURCE" or
                             receipt_hash not in protocol.get("trusted_export_receipt_hashes", [])):
            raise ValueError("SOURCE_AUDIT_RECEIPT_NOT_PINNED")
        if not fixtures and (receipt.get("quotes_sha256") != manifest["quotes"]["sha256"] or
                             receipt.get("chains_sha256") != manifest["chains"]["sha256"]):
            raise ValueError("AUDIT_RECEIPT_DATA_HASH_MISMATCH")
        dataset = Dataset(quotes, chains, provider=manifest["provider"], fixture=fixtures,
                          capture_mode=manifest["capture_mode"], provenance_verified=not fixtures)
        if dataset.last_time and dataset.last_time > retrieved:
            raise ValueError("DATA_AFTER_RETRIEVAL_TIME")
        return {"status": "SIMULATED_ONLY" if fixtures else "AUDITED_OFFLINE_DATASET_LOADED",
                "evidence_eligible": not fixtures, "quote_rows": len(quotes), "chain_rows": len(chains),
                "capture_mode": manifest["capture_mode"], "source_url": manifest["source_url"],
                "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "provenance_limit": "Pinned audit is a reviewed input attestation; file hashes do not independently establish provider entitlement or complete coverage.",
                "strategy_validated": False, "live_ready": False}, dataset
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        # Never echo untrusted rows, paths, HTTP text or exception strings.
        code = str(error) if isinstance(error, ValueError) and re.fullmatch(r"[A-Z0-9_]+", str(error)) else "OPTION_DATASET_VALIDATION_OR_SOURCE_AUDIT_FAILED"
        return {"status": "REJECTED", "reason": code,
                "option_performance": None, "evidence_eligible": False,
                "strategy_validated": False, "live_ready": False}, None


class Dataset:
    def __init__(self, quotes, chains, *, provider, fixture=False, capture_mode="HISTORICAL_DOWNLOAD", provenance_verified=False):
        if not isinstance(provider, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", provider):
            raise ValueError("PROVIDER_IDENTIFIER_REQUIRED")
        if fixture != (capture_mode == "SIMULATED"):
            raise ValueError("FIXTURE_CAPTURE_MODE_MISMATCH")
        self.fixture = fixture;self.provider = provider;self.capture_mode = capture_mode
        self.provenance_verified = provenance_verified is True
        self.quotes = defaultdict(list);self.chains = defaultdict(list);self.times = {}
        self.last_time = None
        for row in quotes:
            self._provenance(row, "option_quote")
            if row.get("currency") != "USD" or row.get("premium_units") != "USD_PER_SHARE" or row.get("size_units") != "CONTRACTS":
                raise ValueError("EXPLICIT_OPTION_PRICE_AND_SIZE_UNITS_REQUIRED")
            spec = contract(row["symbol"]);timestamp = aware(row["source_timestamp"])
            if timestamp.astimezone(ET).date().isoformat() > spec["expiry"]:
                raise ValueError("QUOTE_AFTER_EXPIRY")
            if not all(number(row.get(k)) for k in ("bid", "ask")) or not 0 <= row["bid"] <= row["ask"] or row["ask"] <= 0:
                raise ValueError("INVALID_OPTION_BID_ASK")
            if any(type(row.get(k)) is not int or row[k] < 0 for k in ("bid_size", "ask_size")):
                raise ValueError("INVALID_OPTION_QUOTE_SIZE")
            prior = self.quotes[row["symbol"]]
            if prior and timestamp <= aware(prior[-1]["source_timestamp"]):
                raise ValueError("DUPLICATE_OR_OUT_OF_ORDER_OPTION_QUOTE")
            if capture_mode == "CONTEMPORANEOUS_CAPTURE":
                receipt = aware(row["received_timestamp"])
                if receipt < timestamp:
                    raise ValueError("QUOTE_RECEIPT_BEFORE_SOURCE")
            self.quotes[row["symbol"]].append(dict(row))
            self.last_time = max(timestamp, self.last_time) if self.last_time else timestamp
        for row in chains:
            self._provenance(row, "chain_contract")
            spec = contract(row["symbol"]);observed = aware(row["source_timestamp"])
            if row.get("underlying") != "SPY" or row.get("right") != spec["type"] or row.get("expiry") != spec["expiry"] or float(row.get("strike", 0)) != float(spec["strike"]) or row.get("multiplier") != 100 or row.get("listed") is not True:
                raise ValueError("ACTUAL_CHAIN_TERMS_MISMATCH")
            if observed.astimezone(ET).date().isoformat() > spec["expiry"]:
                raise ValueError("CHAIN_AFTER_EXPIRY")
            self.chains[row["symbol"]].append(dict(row))
            self.last_time = max(observed, self.last_time) if self.last_time else observed
        for symbol, rows in self.chains.items():
            times = [aware(r["source_timestamp"]) for r in rows]
            if times != sorted(set(times)):
                raise ValueError("DUPLICATE_OR_OUT_OF_ORDER_CHAIN")
        for symbol, rows in self.quotes.items():
            self.times[symbol] = [aware(r["source_timestamp"]) for r in rows]

    def _provenance(self, row, kind):
        expected = "SIMULATED" if self.fixture else "OPRA"
        if row.get("provider") != self.provider or row.get("feed_quality") != expected or row.get("data_type") != kind:
            raise ValueError("OPTION_ROW_PROVENANCE_MISMATCH")
        if not self.fixture and (row.get("synthetic") or row.get("indicative") or row.get("delayed") or row.get("continuity_only")):
            raise ValueError("NON_GENUINE_OPTION_DATA")

    def quote(self, symbol, clock, *, max_age=5):
        clock = aware(clock);times = self.times.get(symbol, [])
        index = bisect.bisect_right(times, clock) - 1
        if index < 0 or (clock - times[index]).total_seconds() > max_age:
            return None
        row = self.quotes[symbol][index]
        if self.capture_mode == "CONTEMPORANEOUS_CAPTURE":
            received = aware(row["received_timestamp"])
            if not 0 <= (clock - received).total_seconds() <= max_age:
                return None
        return row

    def chain(self, symbol, clock):
        clock = aware(clock)
        candidates = [r for r in self.chains.get(symbol, []) if aware(r["source_timestamp"]) <= clock]
        if not candidates:
            return None
        item = candidates[-1]
        return item if (clock - aware(item["source_timestamp"])).total_seconds() <= 300 else None


def select(dataset, decision, planned_exit, direction, *, limit=None, allowed_symbol=None):
    decision = aware(decision);planned_exit = aware(planned_exit)
    if direction not in ("CALL", "PUT") or planned_exit <= decision:
        return None, "INVALID_OPTION_SELECTION_WINDOW"
    eligible = []
    for symbol in dataset.chains:
        if allowed_symbol is not None and symbol != allowed_symbol:
            continue
        row = dataset.chain(symbol, decision);quote = dataset.quote(symbol, decision)
        if not row or not quote or row["right"] != ("C" if direction == "CALL" else "P"):
            continue
        if row["expiry"] <= planned_exit.astimezone(ET).date().isoformat():
            continue
        if quote["bid"] <= 0 or quote["bid_size"] < 1 or quote["ask_size"] < 1:
            continue
        midpoint = (quote["bid"] + quote["ask"]) / 2
        if (quote["ask"] - quote["bid"]) / midpoint > .10:
            continue
        greek_at = row.get("greeks_timestamp")
        try:
            greek_age = (decision - aware(greek_at)).total_seconds() if greek_at else None
            oi_time = aware(row["open_interest_asof"]) if row.get("open_interest_asof") else None
            volume_age = (decision - aware(row["volume_asof"])).total_seconds() if row.get("volume_asof") else None
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        if row.get("greeks_basis") != "CURRENT" or greek_age is None or not 0 <= greek_age <= 60:
            continue
        delta = row.get("delta")
        if not number(delta) or not .40 <= abs(delta) <= .55 or delta * (1 if direction == "CALL" else -1) <= 0:
            continue
        if not all(number(row.get(k)) and row[k] >= 100 for k in ("volume", "open_interest")):
            continue
        # OI is often previous-day. Preserve and require its own causal date;
        # never claim it is a current-session measurement.
        if oi_time is None or oi_time > decision:
            continue
        if volume_age is None or not 0 <= volume_age <= 300:
            continue
        if limit is not None and quote["ask"] > limit:
            continue
        rank = ((quote["ask"] - quote["bid"]) / midpoint, abs(abs(delta) - .5), row["expiry"], symbol)
        eligible.append((rank, {"contract": row, "quote": quote}))
    return (min(eligible, key=lambda item: item[0])[1], None) if eligible else (None, "VERIFIED_POINT_IN_TIME_CONTRACT_UNAVAILABLE")


def replay(dataset, candidate, scenario, *, direction=None):
    """Full-exit observed underlying event requires a genuine bid at exit clock.

    ``exit_event_at`` comes from causal completed-bar event observation, never a
    modeled premium. A missing underlying outcome gives no option outcome.
    """
    decision = aware(candidate["decision_at"]);planned = aware(candidate["planned_exit_at"])
    delay = scenario["human_response_seconds"];slip = scenario["slippage_per_side"]
    fee = scenario["fee_per_contract_per_side"]
    if any(not number(x) or x < 0 for x in (delay, slip, fee)):
        raise ValueError("INVALID_EXECUTION_COST_SCENARIO")
    chosen_direction = direction or candidate["direction"]
    if chosen_direction != candidate["direction"]:
        alternate = candidate.get("direction_outcomes", {}).get(chosen_direction)
        if alternate:
            candidate = {**candidate, **alternate}
        else:
            return {"candidate_id": candidate["candidate_id"], "trial_id": candidate["trial_id"],
                    "decision_at": decision.isoformat(), "direction": chosen_direction,
                    "status": "EXCLUDED", "net_pnl_usd": None,
                    "reason": "MATCHED_CLOCK_OPPOSITE_DIRECTION_OUTCOME_UNAVAILABLE",
                    "evidence_eligible": False, "strategy_validated": False, "live_ready": False}
    result = {"candidate_id": candidate["candidate_id"], "trial_id": candidate["trial_id"],
              "decision_at": decision.isoformat(), "planned_exit_at": planned.isoformat(),
              "direction": chosen_direction, "status": "NOT_FILLED", "net_pnl_usd": None,
              "premium_return": None, "feed_quality": "SIMULATED" if dataset.fixture else "OPRA",
              "evidence_eligible": not dataset.fixture and dataset.provenance_verified, "strategy_validated": False, "live_ready": False,
              "event_label": candidate.get("event_label", "UNKNOWN"), "regime": candidate.get("regime", "UNKNOWN")}
    if not dataset.fixture and not dataset.provenance_verified:
        return {**result, "status": "EXCLUDED", "reason": "OPTION_SOURCE_AUDIT_NOT_VERIFIED"}
    reference, reason = select(dataset, decision, planned, chosen_direction)
    if not reference:
        return {**result, "reason": reason}
    clock = decision + timedelta(seconds=delay)
    if clock >= planned or clock >= aware(candidate["entry_valid_until"]):
        return {**result, "reason": "ENTRY_DEADLINE_REACHED"}
    symbol = reference["contract"]["symbol"];entry_quote = dataset.quote(symbol, clock)
    delayed_selection, _ = select(dataset, clock, planned, chosen_direction, allowed_symbol=symbol)
    limit = candidate.get("option_limit", reference["quote"]["ask"] + .10)
    if not number(limit) or not entry_quote or not delayed_selection or entry_quote["ask_size"] < 1 or entry_quote["bid_size"] < 1:
        return {**result, "reason": "DELAYED_ENTRY_GENUINE_QUOTE_UNAVAILABLE"}
    fill = entry_quote["ask"] + slip
    if fill > limit:
        return {**result, "reason": "QUOTED_MARKETABLE_PRICE_EXCEEDS_LIMIT"}
    entry_debit = fill * 100 + fee
    result.update(symbol=symbol, confirmation_trigger=candidate.get("trigger_level"),
                  reference_quote_midpoint=(reference["quote"]["bid"] + reference["quote"]["ask"]) / 2,
                  modeled_entry_fill=fill, actual_user_reported_fill=None,
                  entry_at=clock.isoformat(), entry_debit_usd=entry_debit,
                  premium_at_risk_usd=entry_debit, entry_limit=limit,
                  contract_greeks_asof=reference["contract"]["greeks_timestamp"],
                  contract_greeks_basis=reference["contract"]["greeks_basis"],
                  open_interest_asof=reference["contract"]["open_interest_asof"],
                  fill_assumption="MODELED_SIZED_MARKETABLE_ASK_NOT_ACTUAL_FILL; no bar-touch assumption")
    if candidate.get("outcome_status") == "UNRESOLVED_DATA" or not candidate.get("exit_event_at"):
        return {**result, "status": "UNRESOLVED_DATA", "reason": "UNDERLYING_OUTCOME_UNAVAILABLE_CAPITAL_RESERVED",
                "actual_exit_at": None}
    event = aware(candidate["exit_event_at"])
    if event <= clock:
        return {**result, "status": "NOT_FILLED", "reason": "OUTCOME_OCCURRED_BEFORE_DELAYED_ENTRY",
                "entry_debit_usd": None, "modeled_entry_fill": None}
    exit_clock = event + timedelta(seconds=delay)
    exit_quote = dataset.quote(symbol, exit_clock)
    if not exit_quote or exit_quote["bid_size"] < 1 or exit_quote["bid"] <= 0:
        return {**result, "status": "UNRESOLVED_DATA", "reason": "EXIT_GENUINE_BID_UNAVAILABLE_CAPITAL_RESERVED",
                "actual_exit_at": None}
    exit_fill = max(0, exit_quote["bid"] - slip)
    credit = exit_fill * 100 - fee
    pnl = credit - entry_debit
    return {**result, "status": "CLOSED", "actual_exit_at": exit_clock.isoformat(),
            "modeled_exit_fill": exit_fill, "exit_credit_usd": credit,
            "net_pnl_usd": pnl, "premium_return": pnl / entry_debit,
            "outcome": candidate.get("outcome", "TIME_EXIT"),
            "fees_usd": 2 * fee, "slippage_usd": 2 * slip * 100,
            "holding_time_seconds": (exit_clock - clock).total_seconds()}


def random_direction(trial_id, candidate_id):
    return "CALL" if hashlib.sha256(("matched-clock-direction-v1:" + trial_id + candidate_id).encode()).digest()[0] < 128 else "PUT"


def portfolio(dataset, candidates, scenario, limits, *, baseline=False):
    """Separate cash-funded simulation per model/scenario and benchmark."""
    cash = limits["research_cash_usd"];cap = limits["maximum_open_premium_usd"]
    if not number(cash) or cash <= 0 or not number(cap) or cap <= 0 or limits.get("borrow") is not False or limits.get("maximum_contracts_per_idea") != 1:
        raise ValueError("CASH_FUNDED_ONE_CONTRACT_RESEARCH_LIMITS_REQUIRED")
    active = [];results = []
    for candidate in sorted(candidates, key=lambda row: (aware(row["decision_at"]), row["candidate_id"])):
        clock = aware(candidate["decision_at"]) + timedelta(seconds=scenario["human_response_seconds"])
        pending = []
        for old in active:
            if old["status"] == "CLOSED" and aware(old["actual_exit_at"]) <= clock:
                cash += old["exit_credit_usd"]
            else:
                pending.append(old)
        active = pending
        direction = random_direction(candidate["trial_id"], candidate["candidate_id"]) if baseline else None
        result = replay(dataset, candidate, scenario, direction=direction)
        debit = result.get("entry_debit_usd")
        if debit is not None and result["status"] in ("CLOSED", "UNRESOLVED_DATA"):
            premium_open = sum(row["entry_debit_usd"] for row in active)
            if debit > cash or premium_open + debit > cap:
                result = {**result, "status": "NOT_FILLED", "reason": "RESEARCH_CASH_OR_PREMIUM_EXPOSURE_LIMIT",
                          "net_pnl_usd": None, "premium_return": None, "entry_debit_usd": None,
                          "modeled_entry_fill": None, "actual_exit_at": None}
            else:
                cash -= debit;active.append(result)
        result["benchmark"] = "MATCHED_CLOCK_RANDOM_DIRECTION_V1" if baseline else None
        results.append(result)
    return results


def portfolio_marks(dataset, records, scenario, initial_cash=10000):
    """Quote-event liquidation marks, never option OHLC or estimated Greeks.

    Missing fresh marks make full drawdown unavailable. The partial observed
    drawdown is retained separately, with no interpolation across unknown gaps.
    """
    positions = [row for row in records if row.get("entry_debit_usd") is not None and row.get("status") in ("CLOSED", "UNRESOLVED_DATA")]
    if not positions:
        return {"status": "UNAVAILABLE", "reason": "NO_MODELED_OPTION_ENTRIES", "max_drawdown_usd": None}
    moments = set()
    for row in positions:
        entry = aware(row["entry_at"]);end = aware(row["actual_exit_at"]) if row.get("actual_exit_at") else dataset.last_time
        moments.add(entry)
        if end is not None:moments.add(end)
        moments.update(t for t in dataset.times.get(row["symbol"], []) if entry <= t and (end is None or t <= end))
    peak = float(initial_cash);partial = 0.;missing = 0;marks = 0;minimum_cash = float(initial_cash)
    coverage_gaps = 0
    for row in positions:
        entry=aware(row["entry_at"]);end=aware(row["actual_exit_at"]) if row.get("actual_exit_at") else dataset.last_time
        if end is not None:
            times=[entry]+[t for t in dataset.times.get(row["symbol"],[]) if entry<t<end]+[end]
            coverage_gaps+=sum((right-left).total_seconds()>5 for left,right in zip(times,times[1:]))
    for clock in sorted(moments):
        cash = float(initial_cash);active = []
        for row in positions:
            if aware(row["entry_at"]) > clock:continue
            cash -= row["entry_debit_usd"]
            if row.get("actual_exit_at") and aware(row["actual_exit_at"]) <= clock:
                cash += row["exit_credit_usd"]
            else:active.append(row)
        minimum_cash = min(minimum_cash, cash)
        equity = cash;complete = True
        for row in active:
            quote = dataset.quote(row["symbol"], clock)
            if not quote or quote["bid_size"] < 1 or quote["bid"] <= 0:
                complete = False;break
            equity += max(0, quote["bid"] - scenario["slippage_per_side"]) * 100 - scenario["fee_per_contract_per_side"]
        marks += 1
        if not complete:
            missing += 1;continue
        peak = max(peak, equity);partial = min(partial, equity - peak)
    unresolved = any(row["status"] == "UNRESOLVED_DATA" for row in positions)
    return {"status": "UNAVAILABLE_INCOMPLETE_MARKS" if missing or unresolved or coverage_gaps else "QUOTE_EVENT_MARKS_AVAILABLE",
            "max_drawdown_usd": None if missing or unresolved or coverage_gaps else partial,
            "partial_observed_mark_drawdown_usd": partial, "mark_events": marks,
            "missing_mark_events": missing, "unresolved_positions": unresolved,
            "active_quote_intervals_exceeding_five_seconds":coverage_gaps,
            "minimum_modeled_cash_usd": minimum_cash,
            "definition": "Liquidation bid minus exit slippage/fee at actual quote-event clocks; no marks or drawdown inferred inside absent-quote intervals."}


def assess(summary, protocol, *, population, final_frozen=False, all_execution_scenarios_pass=False):
    """Acceptance is further-research evidence only, never a live promotion path."""
    required = protocol["acceptance"];gaps = []
    if population != "SEALED_FINAL_GENUINE_OPTION_QUOTES":gaps.append("GENUINE_SEALED_FINAL_OPTION_POPULATION_REQUIRED")
    if not final_frozen:gaps.append("SELECTION_NOT_FROZEN_BEFORE_FINAL")
    metric = summary["metrics"];uncertainty = summary["uncertainty"]
    if metric["closed"] < required["minimum_closed_option_observations"]:gaps.append("INSUFFICIENT_CLOSED_OPTION_OBSERVATIONS")
    if uncertainty["day_blocks"] < required["minimum_final_days"]:gaps.append("INSUFFICIENT_FINAL_DAY_BLOCKS")
    bounds = uncertainty.get("bonferroni_simultaneous_95")
    if not bounds or bounds[0] <= 0:gaps.append("POSITIVE_NET_EXPECTANCY_NOT_ESTABLISHED")
    paired = summary["paired_baseline"]["interval"].get("bonferroni_simultaneous_95")
    if not paired or paired[0] <= 0:gaps.append("ADVANTAGE_OVER_MATCHED_CLOCK_DIRECTION_BASELINE_NOT_ESTABLISHED")
    denominator = metric["closed"] + metric["unresolved"]
    if not denominator or metric["unresolved"] / denominator > required["missing_outcomes_max_fraction"]:gaps.append("MISSING_OUTCOME_COVERAGE_INSUFFICIENT")
    concentration = summary["concentration"]["maximum_day_fraction_of_positive_pnl"]
    if concentration is None or concentration > required["maximum_single_day_fraction_of_positive_pnl"]:gaps.append("POSITIVE_RESULT_CONCENTRATION_LIMIT_NOT_MET")
    if not all_execution_scenarios_pass:gaps.append("WORSE_EXECUTION_ROBUSTNESS_NOT_ESTABLISHED")
    if summary.get("portfolio_marks", {}).get("max_drawdown_usd") is None:gaps.append("GENUINE_QUOTE_EVENT_DRAWDOWN_UNAVAILABLE")
    return {"status": "FURTHER_PROSPECTIVE_RESEARCH_SUPPORTED" if not gaps else "RESEARCH_EVIDENCE_INSUFFICIENT",
            "reasons": gaps, "strategy_validated": False, "live_ready": False,
            "scope": "No future profitability, calibrated odds, live signal or order permission follows from this assessment."}
