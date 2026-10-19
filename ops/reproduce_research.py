"""Offline research reproduction. No credentials, orders, private ledger or sends."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from core.storage import ROOT
from core.sessions import ET
from backtesting.research_protocol import register, digest

SOURCES = ("backtesting/research_protocol.py", "backtesting/research_statistics.py",
           "backtesting/option_research.py", "backtesting/underlying_study.py",
           "ops/reproduce_research.py", "core/research_horizons.py", "features/indicators.py",
           "core/sessions.py", "core/exchange_calendar.py", "core/spy_research.py")


def _safe_write(path, body):
    from ops.verification_packet import scan
    if scan(body):raise ValueError("RESEARCH_OUTPUT_REFUSED_SECRET_PATTERN")
    path = Path(path)
    # Hash exact UTF-8/LF bytes on Windows too; text newline translation would
    # otherwise make an immediately reproduced input fail its own digest.
    with path.open("x", encoding="utf-8", newline="\n") as handle:handle.write(body)


def compute(bars, envelope, dates, option_manifest=None):
    from backtesting.underlying_study import generate, evaluate
    from backtesting.research_statistics import summarize
    from backtesting.option_research import load, portfolio, portfolio_marks
    protocol = envelope["protocol"]
    candidates, generation = generate(bars, protocol, evaluation_dates=dates)
    records, baseline = evaluate(candidates, bars)
    underlying = []
    for trial in protocol["trials"]:
        rows = [row for row in records if row["trial_id"] == trial["trial_id"]]
        comparison = [row for row in baseline if row["trial_id"] == trial["trial_id"]]
        underlying.append({"trial": trial, **summarize(rows, comparison, seed=trial["trial_id"]),
                           "population": "RETROSPECTIVE_UNDERLYING_PROXY", "option_performance": None,
                           "qualification": "NOT_OPTION_EVIDENCE_NOT_SEALED_FINAL"})
    option_status, dataset = load(option_manifest or ROOT / "research/option_bbo_manifest.json", protocol)
    options = []
    if dataset is not None:
        for trial in protocol["trials"]:
            selected = [row for row in records if row["trial_id"] == trial["trial_id"]]
            for scenario in protocol["execution_scenarios"]:
                actual = portfolio(dataset, selected, scenario, protocol["portfolio"])
                bench = portfolio(dataset, selected, scenario, protocol["portfolio"], baseline=True)
                analysis = summarize(actual, bench, seed=trial["trial_id"] + digest(scenario))
                analysis["portfolio_marks"] = portfolio_marks(dataset, actual, scenario, protocol["portfolio"]["research_cash_usd"])
                options.append({"trial_id": trial["trial_id"], "scenario": scenario, **analysis,
                                "population": "RETROSPECTIVE_OPTION_REPLAY_NOT_SEALED_FINAL",
                                "strategy_validated": False, "live_ready": False})
    return {"generation": generation, "underlying": underlying, "option_data": option_status,
            "option_scenarios": options, "declared_scenarios": protocol["execution_scenario_count"],
            "option_performance": None if dataset is None else "DESCRIPTIVE_RETROSPECTIVE_ONLY",
            "prospective_final_status": "NOT_STARTED_OR_NOT_RELEASED",
            "strategy_validated": False, "live_ready": False}, records, baseline


def report_text(manifest, analysis):
    lines = ["# SPY strategy research reproduction", "",
             "Status: TESTED IN ISOLATION infrastructure; retained inputs inspected read-only. Strategy evidence remains insufficient.", "",
             "This is retrospective underlying exploration. It is not a sealed final evaluation, an option profit result, a calibrated win probability or a live recommendation.", "",
             f"Protocol SHA256: `{manifest['protocol_sha256']}`. Analysis SHA256: `{manifest['analysis_sha256']}`.",
             f"Evaluation dates: {', '.join(manifest['evaluation_dates']) or 'UNAVAILABLE'}. Evaluation cadence:60seconds; Telegram cadence remains15minutes.",
             f"Option data status: **{analysis['option_data']['status']}**. {analysis['option_data'].get('reason', '')}", "",
             "## Twelve declared underlying variants", "",
             "Every dollar below is per underlying SPY share under assumed $0.02 spread and $0.01 slippage per side. It is not option P&L. Missing output stays unavailable; unresolved windows are not zero-return trades.", "",
             "| Family | Horizon | ATR floor | Closed | Unresolved | Mean/share | Matched-clock direction baseline mean/share | Day blocks |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in analysis["underlying"]:
        metric=row["metrics"];trial=row["trial"];bench=row["paired_baseline"]["interval"]
        mean = "UNAVAILABLE" if metric["mean_pnl_usd"] is None else f"${metric['mean_pnl_usd']:.4f}"
        baseline_mean = row["baseline_metrics"]["mean_pnl_usd"]
        baseline = "UNAVAILABLE" if baseline_mean is None else f"${baseline_mean:.4f}"
        lines.append(f"| {trial['family']} | {trial['horizon']} | {trial['stop_atr_floor']} | {metric['closed']} | {metric['unresolved']} | {mean} | {baseline} | {row['uncertainty']['day_blocks']} |")
    lines += ["", "The baseline randomizes CALL/PUT direction at the strategy's decision clocks; it does not randomize entry times. Each direction has separately evaluated symmetric structural distances and holding rules. Underlying simulations are one-share diagnostic observations and can overlap; they are not an investable aggregate portfolio.", "",
              "## Coverage and missingness", "", "| ET date | Expected minutes | Genuine minutes | Missing |", "|---|---:|---:|---:|"]
    for row in manifest["input_evidence"].get("coverage", []):
        if row["date"] in manifest["evaluation_dates"]:
            lines.append(f"| {row['date']} | {row['expected_minutes']} | {row['genuine_recorded_minutes']} | {row['missing_minutes']} |")
    lines += ["", "Conflicting revisions and malformed rows are excluded and counted in manifest.json. Genuine provider-confirmed empty minutes are not invented as outcome candles. Native historical daily/higher-frame data are not silently guessed; unsupported frames remain unavailable. Historical event labels remain UNKNOWN. A retrospective bar reference does not satisfy the live fresh-quote or calendar gate.", "",
              "## Uncertainty, overlap and comparisons", "",
              "analysis.json contains every trial, paired sample count and missing-pair count, day-block bootstrap95% interval, Bonferroni simultaneous interval across all72declared execution scenarios, overlap, realized-equity drawdown limitation, and concentration by month/event/regime/direction/ET hour. Fewer than20days yields INSUFFICIENT_DAY_BLOCKS. These short correlated historical samples cannot validate an option edge.", ""]
    for row in analysis["underlying"]:
        pair = row["paired_baseline"];ci = row["uncertainty"].get("bootstrap_95")
        simultaneous = row["uncertainty"].get("bonferroni_simultaneous_95")
        difference=pair["interval"].get("mean")
        lines.append(f"- {row['trial']['trial_id']}: n={row['metrics']['closed']}; paired={pair['paired']}; mean difference={difference if difference is not None else 'UNAVAILABLE'};95%CI={ci or 'UNAVAILABLE'}; simultaneousCI={simultaneous or 'UNAVAILABLE'}; uncertainty={row['uncertainty']['status']}.")
    lines += ["", "## Genuine option evaluation", "",
              "No option strategy has sufficient evidence for its stated use. Existing option trade bars and post-outcome contract samples do not provide executable historical bid/ask, point-in-time chain selection or current Greek history. The strict option replay infrastructure supports an audited offline BBO/chain export, ask-side entry, bid-side exit, fees, slippage, human-delay scenarios, full exits, missing-quote refusal, cash/exposure limits and quote-event drawdown. The initial immutable protocol pins no externally audited source receipts. Option performance is UNAVAILABLE until the actual data and authorization are verified.", "",
              "## Reproduction and sealing", "",
              "The run freezes an allowlisted genuine-bar input file, protocol hash, exact source hashes and full candidate/outcome results. `python -m ops.reproduce_research --reproduce RUN_DIRECTORY` refuses modified code, input or protocol and recomputes the analysis digest. All inputs/results are local; do not redistribute licensed raw data. New prospective development/validation/final results are not auto-opened or auto-promoted.", "",
              "The software cannot independently prove an imported file's license, entitlement or provider authenticity. Pinned audit receipts are reviewed input attestations. Gaps, source revisions, bar-level ambiguity, missing historical event classification, different historical quote latency and unmodeled execution competition can change conclusions. No fills, account balances or broker orders were read; no Telegram message was sent.", ""]
    return "\n".join(lines)


def create_run(args, envelope):
    from backtesting.underlying_study import load_bars
    from ops.verification_packet import scan
    bars,evidence=load_bars(args.history)
    days=sorted({datetime.fromtimestamp(row["timestamp"],timezone.utc).astimezone(ET).date().isoformat() for row in bars})
    dates=days[-args.sessions:]
    source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}
    analysis,records,baseline=compute(bars,envelope,dates,args.option_manifest)
    if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected for name,expected in source_hashes.items()):
        raise ValueError("RESEARCH_SOURCE_CHANGED_DURING_RUN_RETRY_AFTER_EDITS")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out=args.output/stamp;out.mkdir(parents=True,exist_ok=False)
    input_body="\n".join(json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False) for row in bars)+"\n"
    manifest={"schema_version":"aegis-research-reproduction-v1","created_at":datetime.now(timezone.utc).isoformat(),
              "protocol_sha256":envelope["protocol_sha256"],"protocol":envelope["protocol"],
              "source_hashes":source_hashes,"input_evidence":evidence,"evaluation_dates":dates,
              "input_file":"underlying_input.jsonl","input_sha256":hashlib.sha256(input_body.encode()).hexdigest(),
              "analysis_sha256":digest(analysis),"records_sha256":digest(records),"baseline_records_sha256":digest(baseline),
              "option_manifest":str(args.option_manifest.resolve()) if args.option_manifest and args.option_manifest.exists() else None,
              "strategy_validated":False,"live_ready":False}
    bodies={"underlying_input.jsonl":input_body,"manifest.json":json.dumps(manifest,indent=2,allow_nan=False),
            "analysis.json":json.dumps(analysis,indent=2,allow_nan=False),
            "underlying_outcomes.json":json.dumps(records,indent=2,allow_nan=False),
            "matched_clock_direction_baseline.json":json.dumps(baseline,indent=2,allow_nan=False),
            "STRATEGY_RESEARCH_REPORT.md":report_text(manifest,analysis)}
    if any(scan(body) for body in bodies.values()):raise ValueError("RESEARCH_OUTPUT_REFUSED_SECRET_PATTERN")
    for name,body in bodies.items():_safe_write(out/name,body+"\n" if not body.endswith("\n") else body)
    return {"status":"RETROSPECTIVE_RESEARCH_REPRODUCED","run_directory":str(out),
            "candidate_observations":len(records),"option_data_status":analysis["option_data"]["status"],
            "strategy_validated":False,"live_ready":False}


def reproduce(path):
    path=Path(path);manifest=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
    if digest(manifest["protocol"])!=manifest["protocol_sha256"]:raise ValueError("REPRODUCTION_PROTOCOL_HASH_MISMATCH")
    for name,expected in manifest["source_hashes"].items():
        if name not in SOURCES or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError("REPRODUCTION_SOURCE_CODE_CHANGED")
    raw=(path/"underlying_input.jsonl").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest["input_sha256"]:raise ValueError("REPRODUCTION_INPUT_CHANGED")
    bars=[json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    envelope={"protocol":manifest["protocol"],"protocol_sha256":manifest["protocol_sha256"]}
    analysis,records,baseline=compute(bars,envelope,manifest["evaluation_dates"],manifest.get("option_manifest"))
    if digest(analysis)!=manifest["analysis_sha256"] or digest(records)!=manifest["records_sha256"] or digest(baseline)!=manifest["baseline_records_sha256"]:
        raise ValueError("REPRODUCTION_RESULT_MISMATCH")
    return {"status":"REPRODUCTION_VERIFIED","analysis_sha256":manifest["analysis_sha256"],
            "strategy_validated":False,"live_ready":False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register-only", action="store_true")
    parser.add_argument("--protocol", type=Path, default=ROOT / "research/studies/spy-horizon-study-v2/protocol.json")
    parser.add_argument("--history",type=Path,default=ROOT/"runtime/history.sqlite")
    parser.add_argument("--option-manifest",type=Path)
    parser.add_argument("--output",type=Path,default=ROOT/"research/studies/spy-horizon-study-v2/runs")
    parser.add_argument("--sessions",type=int,default=5,help="Last retained sessions for explicitly retrospective exploration; all earlier data supply causal warmup.")
    parser.add_argument("--reproduce",type=Path)
    args = parser.parse_args(argv)
    if args.sessions<1 or args.sessions>60:parser.error("--sessions must be1..60")
    if args.reproduce:
        print(json.dumps(reproduce(args.reproduce),indent=2));return 0
    envelope = register(args.protocol)
    if not args.register_only:
        print(json.dumps(create_run(args,envelope),indent=2));return 0
    print(json.dumps({"status": "REGISTERED_RESEARCH_ONLY", "protocol_sha256": envelope["protocol_sha256"],
                      "strategy_validated": False, "live_ready": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
