# Strategy comparison — October 22

No strategy has sufficient genuine-option evidence. No published profitability claim has been reproduced on this installation. Passing rule tests establishes behavior, not an edge.

## Primary sources and licensing

Reviewed the [original paper, September2025 version](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf), the [original Python translation](https://concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/), and the [Alpaca article](https://concretumgroup.com/backtesting-7-years-of-free-data-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/). No explicit permissive redistribution license was established for their code. AEGIS imports none of it; strategies/concretum.py is an original implementation of the described mathematical rules. External notebooks/MATLAB files and data are not redistributed. The linked Colab required sign-in; accessible inline code was inspected.

The paper uses14 prior same-clock open-to-close absolute moves, gap-adjusted bands, half-hour decisions/stops and overnight-flat exposure. Opposite-band and current-band/VWAP exits are separate variants. Dynamic sizing uses prior14 returns and a4× ceiling. The Python articles differ:13-observation minimum warmup, shifted rolling volatility, rounded shares, and shifted close-return exposure. Those differences remain labeled; article behavior is not silently called the paper. The replay adds explicit delayed minute-open entry and the verified exchange close. It is an execution adaptation, not an exact replication of publisher returns.

## Frozen protocol and available data

The protocol was saved before individual October21 stop results. All inspected periods are retrospective. October21 is development-only; no parameter was selected to rescue it. Source includes13,902 rows,13,641 regular-session rows,28 complete sessions and seven incomplete sessions excluded from outcome days. Incomplete prior sessions stay in lookbacks so they cannot silently become14 complete recent sessions. No data are filled or retimed.

Registered study: two paper exit variants × three holding horizons × three delays plus nine current-strategy horizon/delay variants =27. The 60/120/session variants are separate experiments. The current comparison uses the same deterministic setup detector at matched30-minute decision clocks, one observation per population, explicit per-share cost sensitivities and day-block uncertainty. It is different from production ten-second evaluation.15/30/60-second delays round up to the next available minute open; no claim of subminute execution.

| Period | Frozen dates |
|---|---|
| development | 2026-09-02, 2026-09-03, 2026-09-08, 2026-09-09, 2026-09-10, 2026-09-11, 2026-09-14, 2026-09-15, 2026-09-17, 2026-09-18, 2026-09-21, 2026-09-22, 2026-09-23, 2026-09-24, 2026-09-28, 2026-09-29, 2026-10-21 |
| validation_retrospective | 2026-10-01, 2026-10-02, 2026-10-05, 2026-10-06, 2026-10-08, 2026-10-12 |
| evaluation_retrospective | 2026-10-14, 2026-10-15, 2026-10-16, 2026-10-19, 2026-10-20 |

## Results and refusal

The fresh authorized corporate-action request returned HTTP200 with corporate_actions={} and no pagination token, including a range containing a known dividend season. That is not verified complete dividend history. All504 Concretum variant/session evaluations therefore refused rather than defaulting missing dividends to zero. Exact numerical comparison against Concretum is BLOCKED pending audited complete raw intraday/daily history and dividend coverage; IEX-only minute history is not equivalent to the paper’s IQFeed history. The paper-rule implementation and refusal paths are TESTED IN ISOLATION.

Current-strategy delayed underlying diagnostics below use30-second response assumptions rounded to minute opens. Values are sums for one SPY share per observation, after the declared $0.03 roundtrip sensitivity; they are neither a funded portfolio nor option dollars.

| Variant / period | Observations | Active days | Net USD/share sum | Mean USD/share |
|---|---:|---:|---:|---:|
| CURRENT:SESSION:30:development | 9 | 7 | -1.243 | -0.138 |
| CURRENT:H60:30:development | 6 | 5 | -0.833 | -0.139 |
| CURRENT:H120:30:development | 6 | 5 | -0.833 | -0.139 |
| CURRENT:H60:30:validation_retrospective | 2 | 2 | 0.210 | 0.105 |
| CURRENT:SESSION:30:validation_retrospective | 2 | 2 | 0.210 | 0.105 |
| CURRENT:H120:30:validation_retrospective | 1 | 1 | 0.345 | 0.345 |
| CURRENT:H60:30:evaluation_retrospective | 2 | 2 | -0.290 | -0.145 |
| CURRENT:H120:30:evaluation_retrospective | 2 | 2 | -0.290 | -0.145 |
| CURRENT:SESSION:30:evaluation_retrospective | 2 | 2 | -0.290 | -0.145 |

There are only one or two active validation/evaluation days per displayed cell. These samples cannot establish robustness, a horizon winner, a reliable confidence interval, or option profitability. Day-block intervals are retained as descriptive diagnostics; no multiple-trial significance or automatic promotion is claimed. Initial replay output was retained when lookback handling was corrected; corrected context-preserving results are authoritative.

The individual14-alert audit separately records five frozen stop alternatives × three delays (210 evaluations) and the one-primary-plan delivery replay. Those are development sensitivities, not new untouched tests. Historical stop, target and actual-fill records were not changed. Ten of14 alerted detections were support bounces; three underlying research plans overlapped at the maximum. This concentration limits any broad strategy conclusion.

## Reproduction and remaining evidence

Run python -m ops.primary_comparison --database PRIVATE_READONLY_STATE.sqlite --output PRIVATE_RESULT.json. Optional --dividends accepts an explicitly audited map with a basis field. Missing input remains unavailable. Source SHA-256: e0c4efc8317da18685ec9e815c261fcd007fc7700baa8e7cba284d740b40e5ba.

The existing genuine-BBO option evaluator remains available for audited local chain/quote datasets, with ask entries, bid exits, fees, delays, missing quotes, cash/exposure limits and provenance refusals. No genuine option snapshots were retained by this installation at audit time. No option backtest result, premium prediction or entry qualification is inferred from the underlying study, fixed delta or Greek approximations. Production contract references now use verified actual ask quotes and a100× multiplier, with no assumed limit fill or modeled premium stop.

Untouched future evidence can begin only after versions/selection are frozen; this release establishes no successful future period. Overnight/swing operation and live execution remain disabled.

## Additional consolidated-history sensitivity — same frozen dates

A separate market-data-only request succeeded for historical SIP while real-time SIP remained403. Four hashed pages supplied31,691 original rows,14,040 regular-session bars and36 complete sessions for September1–October21. Download time was October22; none of this history was inserted into live caches or represented as decision-time capture. The original frozen outcome partitions are identical; additional source days provide lookback context only.

Exact corporate-action completeness remains unverified. The [US issuer schedule](https://www.ssga.com/library-content/products/fund-data/etfs/us/distribution/SPDR_Dividend_Distribution_Schedule.pdf) identifies the scheduled September distribution date; the [cross-listed issuer announcement](https://links.sgx.com/1.0.0/corporate-announcements/JFQWVTBZNY58JUVL/903367_SPY%20-%20Sept%202026%20-%20Attachment.pdf) still states TBA and has a different local ex date, so it was rejected as an actual US dividend amount. The following is explicitly an ASSUMPTION-ONLY no-other-scheduled-distribution scenario. September18 has no supplied amount and remains unavailable. This is not an exact publisher-result replication or verified complete-dividend backtest.

The paper exits and current setup detector ran unchanged. All three horizons/delays remain registered; no winner was chosen. Below are all30-second cells (rounded up to minute opens). Native paper costs are$0.009/share roundtrip versus the current$0.03 sensitivity. Common-cost sums additionally deduct$0.021 per Concretum observation, so costs are not hidden. Paper SESSION exits at the verified close; current SESSION uses close−5 minutes.

| Variant / period | Observations | Active days | Native net USD/share | Common $0.03 cost net | Native profit factor | Native max drawdown USD/share |
|---|---:|---:|---:|---:|---:|---:|
| CURRENT:H60:30:development | 7 | 5 | -0.173 | -0.173 | 0.863 | 1.264 |
| CURRENT:H120:30:development | 5 | 4 | 0.557 | 0.557 | 1.549 | 1.014 |
| CURRENT:SESSION:30:development | 7 | 5 | 0.307 | 0.307 | 1.243 | 1.264 |
| CONCRETUM:OPPOSITE_BAND:H60:30:development | 8 | 4 | -3.535 | -3.703 | 0.308 | 4.657 |
| CONCRETUM:OPPOSITE_BAND:H120:30:development | 4 | 3 | 0.589 | 0.505 | 1.229 | 2.569 |
| CONCRETUM:OPPOSITE_BAND:SESSION:30:development | 4 | 4 | -0.609 | -0.693 | 0.841 | 3.835 |
| CONCRETUM:CURRENT_BAND_VWAP:H60:30:development | 8 | 4 | -3.535 | -3.703 | 0.308 | 4.657 |
| CONCRETUM:CURRENT_BAND_VWAP:H120:30:development | 4 | 3 | -1.385 | -1.469 | 0.654 | 3.999 |
| CONCRETUM:CURRENT_BAND_VWAP:SESSION:30:development | 5 | 4 | -5.552 | -5.657 | 0.269 | 7.595 |
| CONCRETUM:OPPOSITE_BAND:H60:30:validation_retrospective | 7 | 4 | 0.835 | 0.688 | 1.314 | 2.658 |
| CONCRETUM:OPPOSITE_BAND:H120:30:validation_retrospective | 5 | 4 | 0.805 | 0.700 | 1.266 | 2.079 |
| CONCRETUM:OPPOSITE_BAND:SESSION:30:validation_retrospective | 4 | 4 | -4.476 | -4.560 | 0.366 | 4.476 |
| CONCRETUM:CURRENT_BAND_VWAP:H60:30:validation_retrospective | 7 | 4 | 0.223 | 0.076 | 1.068 | 2.819 |
| CONCRETUM:CURRENT_BAND_VWAP:H120:30:validation_retrospective | 6 | 4 | -0.925 | -1.051 | 0.759 | 3.817 |
| CONCRETUM:CURRENT_BAND_VWAP:SESSION:30:validation_retrospective | 5 | 4 | -1.006 | -1.111 | 0.719 | 3.567 |
| CURRENT:H60:30:validation_retrospective | 1 | 1 | -0.170 | -0.170 | 0.000 | 0.170 |
| CURRENT:H120:30:validation_retrospective | 1 | 1 | -0.170 | -0.170 | 0.000 | 0.170 |
| CURRENT:SESSION:30:validation_retrospective | 1 | 1 | -0.170 | -0.170 | 0.000 | 0.170 |
| CONCRETUM:OPPOSITE_BAND:H60:30:evaluation_retrospective | 11 | 4 | 10.470 | 10.239 | 3.288 | 2.998 |
| CONCRETUM:OPPOSITE_BAND:H120:30:evaluation_retrospective | 6 | 4 | 8.573 | 8.447 | 4.555 | 2.412 |
| CONCRETUM:OPPOSITE_BAND:SESSION:30:evaluation_retrospective | 5 | 5 | 7.485 | 7.380 | 3.140 | 3.349 |
| CONCRETUM:CURRENT_BAND_VWAP:H60:30:evaluation_retrospective | 11 | 4 | 11.630 | 11.399 | 4.405 | 1.838 |
| CONCRETUM:CURRENT_BAND_VWAP:H120:30:evaluation_retrospective | 7 | 4 | 8.037 | 7.890 | 3.803 | 2.048 |
| CONCRETUM:CURRENT_BAND_VWAP:SESSION:30:evaluation_retrospective | 6 | 5 | 9.356 | 9.230 | 7.603 | 0.819 |
| CURRENT:H60:30:evaluation_retrospective | 1 | 1 | -0.090 | -0.090 | 0.000 | 0.090 |
| CURRENT:H120:30:evaluation_retrospective | 1 | 1 | -0.090 | -0.090 | 0.000 | 0.090 |
| CURRENT:SESSION:30:evaluation_retrospective | 1 | 1 | -0.090 | -0.090 | 0.000 | 0.090 |

Later retrospective Concretum cells are positive while several earlier cells are negative. Only four or five active days support many paper cells, versus one current-strategy active day in some later cells. This is too little and too dependent on assumptions to establish superiority, statistical significance, future profitability or option performance. No production strategy, stop or risk parameter was promoted. Warmup exclusions:180 variant/session evaluations; unavailable dividend/prior-close evaluations:18. All exclusions remain in the private result.

Reproduce with python -m ops.primary_comparison --bars-export PRIVATE_HISTORICAL_EXPORT.json --frozen-manifest PRIVATE_FROZEN_MANIFEST.json --dividends PRIVATE_DISCLOSED_DIVIDEND_SCENARIO.json --output PRIVATE_RESULT.json. The export must retain capture_mode=HISTORICAL_DOWNLOAD. The source SHA-256 is ec876976b4213e3bab003e064a7824044232cabaf3b69ec738e04c5f548ca9fe. The private packet contains the exact partition manifest, scenario basis, page hashes and results for15/30/60-second variants. No licensed raw history is published.
