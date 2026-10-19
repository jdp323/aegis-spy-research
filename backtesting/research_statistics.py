"""Day-clustered descriptive research statistics; no pooled forecast probabilities."""
from __future__ import annotations
import hashlib
import math
import random
import statistics
from collections import Counter, defaultdict
from statistics import NormalDist

from core.sessions import ET
from backtesting.research_protocol import aware


def _closed(rows):
    return [row for row in rows if row.get("status") == "CLOSED" and
            type(row.get("net_pnl_usd")) in (int, float) and math.isfinite(row["net_pnl_usd"])]


def metrics(rows, initial_cash=10000.0):
    closed = sorted(_closed(rows), key=lambda row: aware(row["actual_exit_at"]))
    pnl = [row["net_pnl_usd"] for row in closed]
    gains = [x for x in pnl if x > 0];losses = [x for x in pnl if x < 0]
    equity = peak = float(initial_cash);drawdown = 0.0;streak = worst_streak = 0
    for value in pnl:
        equity += value;peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
        streak = streak + 1 if value < 0 else 0;worst_streak = max(worst_streak, streak)
    return {
        "observations": len(rows), "closed": len(closed),
        "unresolved": sum(row.get("status") == "UNRESOLVED_DATA" for row in rows),
        "excluded_or_not_filled": sum(row.get("status") not in ("CLOSED", "UNRESOLVED_DATA") for row in rows),
        "net_pnl_usd": sum(pnl) if pnl else None,
        "mean_pnl_usd": statistics.mean(pnl) if pnl else None,
        "average_gain_usd": statistics.mean(gains) if gains else None,
        "average_loss_usd": statistics.mean(losses) if losses else None,
        "profit_factor": sum(gains) / -sum(losses) if losses else None,
        "profit_factor_reason": None if losses else "NO_NEGATIVE_CLOSED_OBSERVATIONS_OR_NO_DATA",
        "closed_trade_realized_equity_drawdown_usd": drawdown if pnl else None,
        "drawdown_limitation": "Closed-trade realized equity only; intratrade/mark-to-market drawdown may be worse and is not established.",
        "longest_closed_losing_streak": worst_streak if pnl else None,
        "mean_premium_return": statistics.mean([r["premium_return"] for r in closed
                                                if r.get("premium_return") is not None])
        if any(r.get("premium_return") is not None for r in closed) else None,
        "empirical_win_fraction": len(gains) / len(pnl) if pnl else None,
        "win_fraction_definition": "Fraction of this closed descriptive sample with positive net P&L; not future win probability.",
    }


def interval(rows, *, value_key="net_pnl_usd", trials=72, seed="aegis-day-block-v1",
             repetitions=2048, minimum_days=20):
    """Resample full ET days, retaining within-day correlation and trade counts.

    Bootstrap CI is descriptive. A separate normal day-cluster interval uses
    Bonferroni alpha across all declared scenarios; neither is a guarantee with
    a small or dependent set of days.
    """
    if type(trials) is not int or trials < 1 or repetitions < 100:
        raise ValueError("INVALID_UNCERTAINTY_PARAMETERS")
    days = defaultdict(list)
    for row in rows:
        value = row.get(value_key)
        if type(value) not in (int, float) or not math.isfinite(value):
            continue
        day = aware(row["decision_at"]).astimezone(ET).date().isoformat()
        days[day].append(float(value))
    blocks = [days[day] for day in sorted(days)]
    n = sum(map(len, blocks));k = len(blocks)
    mean = sum(map(sum, blocks)) / n if n else None
    out = {"trade_count": n, "day_blocks": k, "mean": mean,
           "bootstrap_95": None, "bonferroni_simultaneous_95": None,
           "tested_scenarios": trials, "status": "INSUFFICIENT_DAY_BLOCKS",
           "method": "ET-day cluster weighted-mean bootstrap and normal cluster sandwich SE; Bonferroni across every declared scenario",
           "overlap": "Trades within a day may overlap; whole days are the resampling unit. Cross-day dependence remains a limitation."}
    if k < minimum_days or n == 0:
        return out
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16));draws = []
    for _ in range(repetitions):
        sample = [rng.choice(blocks) for _ in blocks]
        draws.append(sum(map(sum, sample)) / sum(map(len, sample)))
    draws.sort()
    low = draws[int(.025 * (repetitions - 1))]
    high = draws[int(.975 * (repetitions - 1))]
    # Score contributions preserve the unequal number of trades per day.
    residuals = [sum(block) - mean * len(block) for block in blocks]
    se = math.sqrt(k / (k - 1) * sum(x * x for x in residuals)) / n
    z = NormalDist().inv_cdf(1 - .05 / (2 * trials))
    return {**out, "bootstrap_95": [low, high],
            "bonferroni_simultaneous_95": [mean - z * se, mean + z * se],
            "status": "DESCRIPTIVE_CLUSTER_INTERVAL", "standard_error": se,
            "bootstrap_repetitions": repetitions}


def paired_comparison(rows, baseline_rows, **kwargs):
    a = {r["candidate_id"]: r for r in _closed(rows)}
    b = {r["candidate_id"]: r for r in _closed(baseline_rows)}
    paired = []
    for key in sorted(a.keys() & b.keys()):
        left, right = a[key], b[key]
        if left["decision_at"] != right["decision_at"]:
            raise ValueError("BASELINE_CLOCK_MISMATCH")
        paired.append({"decision_at": left["decision_at"],
                       "difference": left["net_pnl_usd"] - right["net_pnl_usd"]})
    return {"baseline": "MATCHED_CLOCK_RANDOM_DIRECTION_V1",
            "definition": "Direction randomized at strategy decision clocks; entry timing is not randomized.",
            "paired": len(paired), "unpaired_strategy": len(a) - len(paired),
            "unpaired_baseline": len(b) - len(paired),
            "interval": interval(paired, value_key="difference", **kwargs)}


def concentration(rows):
    dimensions = {name: defaultdict(list) for name in ("month", "event", "regime", "direction", "time_of_day")}
    by_day = defaultdict(float)
    for row in _closed(rows):
        local = aware(row["decision_at"]).astimezone(ET)
        values = {"month": local.strftime("%Y-%m"), "event": row.get("event_label", "UNKNOWN"),
                  "regime": row.get("regime", "UNKNOWN"), "direction": row.get("direction", "UNKNOWN"),
                  "time_of_day": f"{local.hour:02d}:00-{local.hour + 1:02d}:00 ET"}
        for dimension, label in values.items():
            dimensions[dimension][label].append(row["net_pnl_usd"])
        by_day[local.date().isoformat()] += max(0, row["net_pnl_usd"])
    positive = sum(by_day.values())
    return {"groups": {name: {label: {"count": len(values), "net_pnl_usd": sum(values)}
                             for label, values in sorted(groups.items())}
                       for name, groups in dimensions.items()},
            "maximum_day_fraction_of_positive_pnl": max(by_day.values()) / positive if positive else None,
            "event_limit": "UNKNOWN means no verified historical event classification; it is not a claim that no event occurred."}


def overlap(rows):
    events = [];closed = _closed(rows)
    for row in closed:
        events.extend([(aware(row["decision_at"]), 1), (aware(row["actual_exit_at"]), -1)])
    active = maximum = 0
    for _, change in sorted(events, key=lambda item: (item[0], item[1])):
        active += change;maximum = max(maximum, active)
    return {"maximum_overlapping_closed_observations": maximum,
            "definition": "Decision-to-exit windows; simultaneous research variants are not independent trades."}


def summarize(rows, baseline_rows=(), *, trials=72, seed="aegis-study-v1"):
    return {"metrics": metrics(rows), "baseline_metrics": metrics(baseline_rows), "uncertainty": interval(_closed(rows), trials=trials, seed=seed),
            "paired_baseline": paired_comparison(rows, baseline_rows, trials=trials, seed=seed + "-paired"),
            "concentration": concentration(rows), "overlap": overlap(rows),
            "status_counts": dict(Counter(row.get("status", "UNKNOWN") for row in rows)),
            "strategy_validated": False, "live_ready": False}
