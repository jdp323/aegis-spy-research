"""Retrospective genuine-bar proxy study, separate from any option-performance evidence."""
from __future__ import annotations
import hashlib
import bisect
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backtesting.research_protocol import aware, digest
from core.sessions import ET, market_session
from data.models import finite
from features.indicators import ema, resample

VERSION = "retrospective-underlying-horizon-v1"


def load_bars(path, feed="IEX"):
    """Read market-only session_bars. Conflicting revisions stay excluded.

    A read-only SQLite connection includes committed WAL data. The digest covers
    the selected row IDs and contents, not a race-prone raw main-database copy.
    """
    if feed not in ("IEX", "SIP"):
        raise ValueError("VERIFIED_UNDERLYING_FEED_REQUIRED")
    path = Path(path).resolve()
    if not path.exists():
        return [], {"status": "UNAVAILABLE", "reason": "RECORDED_UNDERLYING_HISTORY_MISSING"}
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
    grouped = defaultdict(list);reasons = Counter();source_counts = Counter();hasher = hashlib.sha256()
    try:
        records = db.execute("SELECT id,provider,feed_quality,source_timestamp,recorded_at,payload FROM session_bars WHERE feed_quality=? ORDER BY source_timestamp,recorded_at,id", (feed,))
        for record in records:
            hasher.update(json.dumps(list(record), separators=(",", ":")).encode())
            try:
                raw = json.loads(record[5]);timestamp = aware(record[3]);recorded = aware(record[4])
                if record[1] != "alpaca-" + feed.lower() or raw.get("feed_quality") != feed or raw.get("provider") != record[1]:
                    raise ValueError("PROVENANCE_MISMATCH")
                if raw.get("synthetic") or raw.get("continuity_only") or raw.get("feed_quality") == "SIMULATED":
                    raise ValueError("SYNTHETIC_REJECTED")
                if int(timestamp.timestamp()) != timestamp.timestamp() or timestamp.second or timestamp.microsecond:
                    raise ValueError("MINUTE_ALIGNMENT_INVALID")
                if not market_session(timestamp).get("active"):
                    raise ValueError("NON_REGULAR_OR_UNVERIFIED_SESSION")
                row = {k: raw.get(k) for k in ("open", "high", "low", "close", "volume")}
                if not all(finite(row[k]) for k in row) or not 0 < row["low"] <= min(row["open"], row["close"]) <= max(row["open"], row["close"]) <= row["high"] or row["volume"] < 0:
                    raise ValueError("INVALID_OHLCV")
                if recorded < timestamp + timedelta(minutes=1):
                    raise ValueError("RECORDED_UNFINISHED_CANDLE")
                row.update(timestamp=int(timestamp.timestamp()), source=raw.get("source", "UNKNOWN"),
                           provider=record[1], feed_quality=feed, recorded_at=record[4])
                grouped[row["timestamp"]].append(row)
            except (ValueError, TypeError, KeyError):
                reasons["INVALID_OR_UNVERIFIED_ROW"] += 1
    except sqlite3.OperationalError:
        return [], {"status": "UNAVAILABLE", "reason": "RECORDED_SESSION_BAR_TABLE_UNAVAILABLE"}
    finally:
        db.close()
    bars = [];duplicates = 0;conflicts = []
    for timestamp, records in sorted(grouped.items()):
        hashes = {digest({k: row[k] for k in ("timestamp", "open", "high", "low", "close", "volume")}) for row in records}
        if len(hashes) != 1:
            conflicts.append(datetime.fromtimestamp(timestamp, timezone.utc).isoformat());continue
        row = records[0];bars.append(row);source_counts[row["source"]] += 1;duplicates += len(records) - 1
    by_day = defaultdict(set)
    for row in bars:
        by_day[datetime.fromtimestamp(row["timestamp"], timezone.utc).astimezone(ET).date().isoformat()].add(row["timestamp"])
    coverage = []
    for day, captured in sorted(by_day.items()):
        local = datetime.fromisoformat(day).replace(hour=12, tzinfo=ET)
        session = market_session(local);opening = local.replace(hour=9, minute=30)
        expected = set(range(int(opening.timestamp()), int(opening.timestamp()) + (session["close_minute"] - 570) * 60, 60))
        coverage.append({"date": day, "expected_minutes": len(expected), "genuine_recorded_minutes": len(captured & expected),
                         "missing_minutes": len(expected - captured), "continuity_slots_used_for_outcomes": 0})
    return bars, {"status": "RETROSPECTIVE_UNDERLYING_INPUT_ONLY", "feed_quality": feed,
                  "input_snapshot_sha256": hasher.hexdigest(), "genuine_minutes": len(bars),
                  "identical_duplicate_records": duplicates, "conflicting_revision_minutes": conflicts,
                  "row_exclusion_counts": dict(reasons), "sources": dict(source_counts), "coverage": coverage,
                  "capture_limit": "recorded_at and source provenance are retained; REST history collected later is not contemporaneous live evidence.",
                  "option_performance": None, "strategy_validated": False, "live_ready": False}


def price_frame(bars):
    """Only the necessary causal EMA/ATR/confirmed-swing features, linear in rows."""
    if not bars:
        return {"status": "UNAVAILABLE", "bars": 0, "trend": "UNAVAILABLE"}
    close = [row["close"] for row in bars]
    out = {"status": "DESCRIPTIVE_ONLY", "bars": len(bars), "close": close[-1],
           "timestamp": bars[-1]["timestamp"]}
    for period in (9, 20, 21, 50):
        values = ema(close, period);out["ema" + str(period)] = values[-1] if values else None
    tr = [max(bars[i]["high"] - bars[i]["low"], abs(bars[i]["high"] - close[i - 1]),
              abs(bars[i]["low"] - close[i - 1])) for i in range(1, len(bars))]
    atr = None
    if len(tr) >= 14:
        atr = sum(tr[:14]) / 14
        for value in tr[14:]:
            atr = (13 * atr + value) / 14
    out["atr14"] = atr
    out["trend"] = "UNAVAILABLE" if out["ema50"] is None else "BULL" if close[-1] > out["ema9"] > out["ema21"] > out["ema50"] else "BEAR" if close[-1] < out["ema9"] < out["ema21"] < out["ema50"] else "NEUTRAL"
    out["swing_highs"] = [bars[i]["high"] for i in range(2, len(bars) - 2)
                          if all(bars[i]["high"] > bars[j]["high"] for j in (i - 2, i - 1, i + 1, i + 2))][-5:]
    out["swing_lows"] = [bars[i]["low"] for i in range(2, len(bars) - 2)
                         if all(bars[i]["low"] < bars[j]["low"] for j in (i - 2, i - 1, i + 1, i + 2))][-5:]
    return out


def _daily(bars):
    groups = defaultdict(list)
    for bar in bars:
        day = datetime.fromtimestamp(bar["timestamp"], timezone.utc).astimezone(ET).date().isoformat()
        groups[day].append(bar)
    result = []
    for day, group in sorted(groups.items()):
        noon = datetime.fromisoformat(day).replace(hour=12, tzinfo=ET)
        session = market_session(noon);expected = session["close_minute"] - 570
        opening = noon.replace(hour=9, minute=30).timestamp()
        if not session.get("active") or len(group) != expected or any(row["timestamp"] != opening + i * 60 for i, row in enumerate(group)):
            continue
        result.append({"timestamp": group[0]["timestamp"], "open": group[0]["open"],
                       "high": max(row["high"] for row in group), "low": min(row["low"] for row in group),
                       "close": group[-1]["close"], "volume": sum(row["volume"] for row in group)})
    return result


def feature_snapshots(bars):
    """Linear-time exact causal EMA/ATR snapshots, including confirmed swings.

    This equals price_frame(prefix) without repeatedly recalculating every
    historical prefix during a multi-session reproduction.
    """
    out=[];averages={period:None for period in (9,20,21,50)};total=0.;trs=[];atr=None;highs=[];lows=[]
    for i,bar in enumerate(bars):
        total+=bar["close"]
        row={"status":"DESCRIPTIVE_ONLY","bars":i+1,"close":bar["close"],"timestamp":bar["timestamp"]}
        for period in averages:
            if i+1==period:averages[period]=total/period
            elif i+1>period:
                alpha=2/(period+1);averages[period]=alpha*bar["close"]+(1-alpha)*averages[period]
            row["ema"+str(period)]=averages[period]
        if i:
            prior=bars[i-1]["close"];tr=max(bar["high"]-bar["low"],abs(bar["high"]-prior),abs(bar["low"]-prior))
            if i<=14:trs.append(tr)
            if i==14:atr=sum(trs)/14
            elif i>14:atr=(13*atr+tr)/14
        row["atr14"]=atr
        if i>=4:
            j=i-2
            if all(bars[j]["high"]>bars[k]["high"] for k in (j-2,j-1,j+1,j+2)):highs.append(bars[j]["high"])
            if all(bars[j]["low"]<bars[k]["low"] for k in (j-2,j-1,j+1,j+2)):lows.append(bars[j]["low"])
        row["swing_highs"]=highs[-5:];row["swing_lows"]=lows[-5:]
        row["trend"]="UNAVAILABLE" if row["ema50"] is None else "BULL" if bar["close"]>row["ema9"]>row["ema21"]>row["ema50"] else "BEAR" if bar["close"]<row["ema9"]<row["ema21"]<row["ema50"] else "NEUTRAL"
        out.append(row)
    return out


def generate(bars, protocol, *, evaluation_dates=None, simulation=False):
    """Replay the actual core candidate function with explicit completed-bar reference.

    Aggregates may be precomputed for efficiency, but each frame is sliced by its
    own completion time before any feature is calculated. This is tested against
    modified future candles. No fabricated quote is created.
    """
    from core.research_horizons import candidates as core_candidates
    if not bars:
        return [], {"status": "UNAVAILABLE", "reason": "NO_GENUINE_UNDERLYING_BARS"}
    if any(b["timestamp"] >= a["timestamp"] for b, a in zip(bars, bars[1:])):
        raise ValueError("BARS_MUST_BE_STRICTLY_ORDERED")
    if any(row.get("continuity_only") for row in bars) or (not simulation and any(row.get("synthetic") or row.get("feed_quality") == "SIMULATED" for row in bars)):
        raise ValueError("SYNTHETIC_RESEARCH_INPUT_FORBIDDEN")
    frame_rows = {name: resample(bars, minutes) for name, minutes in (("1m", 1), ("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60))}
    frame_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60}
    frame_ends = {name: [row["timestamp"] + frame_minutes[name] * 60 for row in rows] for name, rows in frame_rows.items()}
    daily = _daily(bars);snapshots={name:feature_snapshots(rows) for name,rows in frame_rows.items()};by_day = defaultdict(list)
    for row in bars:
        by_day[datetime.fromtimestamp(row["timestamp"], timezone.utc).astimezone(ET).date().isoformat()].append(row)
    selected = set(evaluation_dates or by_day.keys())
    all_trials = {row["trial_id"] for row in protocol["trials"]}
    records = [];seen = set();checks = Counter();frames_available = Counter()
    for day, day_bars in sorted(by_day.items()):
        if day not in selected:
            continue
        opening = datetime.fromisoformat(day).replace(hour=9, minute=30, tzinfo=ET).timestamp()
        opening_by_time = {row["timestamp"]: row for row in day_bars}
        opening_rows = [opening_by_time.get(int(opening) + i * 60) for i in range(15)]
        opening_range = {"high": max(row["high"] for row in opening_rows), "low": min(row["low"] for row in opening_rows)} if all(opening_rows) else None
        daily_before = [row for row in daily if datetime.fromtimestamp(row["timestamp"], timezone.utc).astimezone(ET).date().isoformat() < day]
        daily_features = price_frame(daily_before)
        for offset, last in enumerate(day_bars):
            clock = datetime.fromtimestamp(last["timestamp"] + 60, timezone.utc)
            current = day_bars[:offset + 1];tail = current[-31:]
            if len(tail) < 31 or any(b["timestamp"] - a["timestamp"] != 60 for a, b in zip(tail, tail[1:])):
                checks["31_GENUINE_COMPLETED_MINUTES_UNAVAILABLE"] += 1;continue
            fs = {"daily": daily_features}
            for name, rows in frame_rows.items():
                count = bisect.bisect_right(frame_ends[name], clock.timestamp())
                fs[name] = dict(snapshots[name][count-1]) if count else price_frame([])
                frames_available[f"{name}:{fs[name]['trend']}"] += 1
            v = sum(row["volume"] for row in current)
            fs["1m"]["vwap_approx"] = sum((row["high"] + row["low"] + row["close"]) / 3 * row["volume"] for row in current) / v if v else None
            # The range is unavailable until all15 constituent candles complete.
            fs["opening_range"] = opening_range if clock.timestamp() >= opening + 900 else None
            bar_context = {"reason": None, "features": fs, "bars": current, "feed_quality": last.get("feed_quality", "IEX"),
                           "provider": last.get("provider", "alpaca-iex"), "source_timestamp": clock.isoformat()}
            generated = core_candidates(bar_context, None, clock, reference_price=last["close"])
            checks["CAUSAL_MINUTE_EVALUATIONS"] += 1
            for item in generated:
                if item["trial_id"] not in all_trials:
                    raise ValueError("CORE_TRIAL_NOT_PREREGISTERED")
                if item["signal_id"] in seen:
                    continue
                seen.add(item["signal_id"])
                record = {"candidate_id": item["signal_id"], "trial_id": item["trial_id"],
                          "strategy_version": item["strategy_version"], "decision_at": clock.isoformat(),
                          "features_through": clock.isoformat(), "planned_exit_at": item["max_hold_until"],
                          "entry_valid_until": item["signal_expiry"], "direction": item["direction"],
                          "horizon_id": item["horizon_id"], "family": item["setup_type"],
                          "trigger_level": item["trigger_level"], "reference_price": last["close"],
                          "reference_price_kind": "COMPLETED_BAR_CLOSE_RESEARCH_ONLY",
                          "reference_quote_midpoint": None, "risk_distance": item["risk_distance"],
                          "invalidation": item["invalidation"], "t1": item["t1"], "t2": item["t2"],
                          "event_label": "UNKNOWN", "regime": fs[item["context_atr_frame"]]["trend"],
                          "feed_quality": "SIMULATED" if simulation else item["feed_quality"], "data_provider": item["data_provider"],
                          "evaluation_cadence_seconds": 60, "telegram_cadence_seconds": 900,
                          "option_expiry": None, "evidence_eligible": False}
                records.append(record)
    return records, {"status": "RETROSPECTIVE_UNDERLYING_EXPLORATION_NOT_SEALED_FINAL", "evaluation_dates": sorted(selected),
                     "evaluation_counts": dict(checks), "frame_availability_counts": dict(frames_available),
                     "registered_trial_count": len(all_trials), "candidate_count": len(records),
                     "native_history_limit": "Features reconstructed from genuine minute bars only; complete prior-session daily bars only. Missing native higher-frame histories are not invented.",
                     "calendar_event_limit": "Historical event classification unavailable; these retrospective proxy candidates do not satisfy live calendar entry eligibility.",
                     "option_performance": None, "strategy_validated": False, "live_ready": False}


def context(bars, clock):
    clock = aware(clock);epoch = clock.timestamp()
    completed = [row for row in bars if row["timestamp"] + 60 <= epoch]
    local_day = clock.astimezone(ET).date()
    today = [row for row in completed if datetime.fromtimestamp(row["timestamp"], timezone.utc).astimezone(ET).date() == local_day]
    frames = {name: price_frame(resample(completed, minutes)) for name, minutes in
              (("1m", 1), ("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60))}
    opening = clock.astimezone(ET).replace(hour=9, minute=30, second=0, microsecond=0).timestamp()
    by_time = {row["timestamp"]: row for row in today}
    opening_rows = [by_time.get(int(opening) + i * 60) for i in range(15)]
    opening_range = {"high": max(row["high"] for row in opening_rows),
                     "low": min(row["low"] for row in opening_rows)} if all(opening_rows) else None
    volume = sum(row["volume"] for row in today)
    vwap = sum((row["high"] + row["low"] + row["close"]) / 3 * row["volume"] for row in today) / volume if volume else None
    return {"bars": today, "frames": frames, "opening_range": opening_range,
            "mid": today[-1]["close"] if today else None, "vwap": vwap,
            "session": market_session(clock), "clock": clock.isoformat(),
            "availability": "COMPLETED_BAR_DESCRIPTIVE_ONLY",
            "fresh_underlying_entry_eligible": False,
            "reference_price_kind": "COMPLETED_BAR_CLOSE_NOT_BID_ASK_QUOTE"}


def outcome(candidate, bars, *, direction=None, spread=.02, slippage=.01):
    """Next genuine minute open proxy; stop-first OHLC ambiguity, gaps unresolved."""
    decision = aware(candidate["decision_at"]);planned = aware(candidate["planned_exit_at"])
    sign = 1 if (direction or candidate["direction"]) == "CALL" else -1
    by_time = {row["timestamp"]: row for row in bars}
    expected = math.ceil(decision.timestamp() / 60) * 60
    distance = candidate["risk_distance"]
    result = {"outcome_status": "UNRESOLVED_DATA", "exit_event_at": None,
              "net_pnl_usd": None, "premium_return": None, "status": "UNRESOLVED_DATA"}
    first = by_time.get(expected)
    if not first or expected >= planned.timestamp():
        return {**result, "reason": "NEXT_GENUINE_ENTRY_MINUTE_UNAVAILABLE"}
    entry_reference = first["open"];fill = entry_reference + sign * (spread / 2 + slippage)
    stop = candidate["reference_price"] - sign * distance
    target = candidate["reference_price"] + sign * 2 * distance
    result.update(modeled_entry_fill=fill, entry_at=datetime.fromtimestamp(expected, timezone.utc).isoformat(),
                  entry_debit_usd=abs(fill), confirmation_trigger=candidate.get("trigger_level"),
                  actual_user_reported_fill=None,
                  reference_quote_midpoint=None, modeled_entry_price_basis="NEXT_MINUTE_OPEN_PROXY_NOT_QUOTE")
    for timestamp in range(expected, int(planned.timestamp()), 60):
        bar = by_time.get(timestamp)
        if not bar:
            return {**result, "reason": "UNCONFIRMED_OUTCOME_MINUTE_GAP"}
        hit_stop = bar["low"] <= stop if sign == 1 else bar["high"] >= stop
        hit_target = bar["high"] >= target if sign == 1 else bar["low"] <= target
        end = datetime.fromtimestamp(timestamp + 60, timezone.utc)
        if hit_stop:
            exit_reference = min(bar["open"], stop) if sign == 1 else max(bar["open"], stop)
            tag = "STOP_FIRST_AMBIGUOUS" if hit_target else "INVALIDATION"
        elif hit_target:
            exit_reference = target;tag = "TARGET_2R"
        elif end >= planned:
            exit_reference = bar["close"];tag = "TIME_EXIT"
        else:
            continue
        exit_fill = exit_reference - sign * (spread / 2 + slippage)
        return {**result, "outcome_status": "CLOSED", "status": "CLOSED", "outcome": tag,
                "exit_event_at": end.isoformat(), "actual_exit_at": end.isoformat(),
                "modeled_exit_fill": exit_fill, "net_pnl_usd": sign * (exit_fill - fill),
                "pnl_unit": "USD_PER_UNDERLYING_SHARE_NOT_OPTION_RETURN",
                "assumed_round_trip_cost_per_share": spread + 2 * slippage,
                "option_exit_timing_limit": "Option replay observes this underlying event only at completed minute end; intraminute event order/timing is not known."}
    return {**result, "reason": "PLANNED_WINDOW_NOT_FULLY_OBSERVED"}


def evaluate(candidates, bars):
    records = [];baseline = []
    from backtesting.option_research import random_direction
    for candidate in candidates:
        directions = {right: outcome(candidate, bars, direction=right) for right in ("CALL", "PUT")}
        actual = {**candidate, **directions[candidate["direction"]], "direction_outcomes": directions,
                  "population": "RETROSPECTIVE_UNDERLYING_PROXY", "evidence_eligible": False,
                  "strategy_validated": False, "live_ready": False}
        chosen = random_direction(candidate["trial_id"], candidate["candidate_id"])
        bench = {**candidate, **directions[chosen], "direction": chosen,
                 "benchmark": "MATCHED_CLOCK_RANDOM_DIRECTION_V1", "evidence_eligible": False,
                 "strategy_validated": False, "live_ready": False}
        records.append(actual);baseline.append(bench)
    return records, baseline
