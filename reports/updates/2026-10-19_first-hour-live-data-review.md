# First-hour live data review — 2026-10-19

## Changes

This report adds a bounded source-quality review and clarifies how to interpret the existing live verifier. No application code, configuration, market-data tolerance, sharing setting or schedule changed. No restart was required, and no development messages were sent.

## Verification

VERIFIED IN OPERATION at 14:34:17 UTC (10:34:17 ET): all six managed component processes were present with no supervisor restarts, dashboard HTTP returned 200, and listener, dispatcher and worker completed-work timestamps were recent. This confirms progress at the observation time, not uninterrupted operation or analysis readiness.

VERIFIED IN OPERATION: the retained prospective verifier contains 60 distinct minute samples from 09:35:10 through 10:34:11 ET. Its overall result is FAIL. Thirteen samples (21.67%) passed its quote-age measurement after earlier provider/heartbeat gates. Three samples (5%) reached LIVE_TREND. Among 34 samples at or after 10:01 ET, three (8.82%) reached LIVE_TREND. Forty-nine samples retained an independent public cross-check labelled PUBLIC_DELAY_UNVERIFIED; these are not consolidated real-time evidence.

Source review of ops/live_verify.py and research/live_trend.py shows an important measurement limitation: the field named bar_tail_qualifies is true only when the whole legacy live-trend evaluation reaches LIVE_TREND. That path first requires a usable quote and heartbeat. Thus 5% is a combined eligibility rate, not proof that 95% of minute bars are missing. Similarly fresh_quote is not an independent tally of all received quotes; early rejection leaves its age unavailable. These legacy percentages must retain these definitions when compared over time.

VERIFIED IN OPERATION, separate coherent read-only snapshot at 14:36:45 UTC: 65 of 66 completed regular-session IEX minute slots were present in the retained minute cache, including all 15 opening-range minutes. Only the latest completed minute (10:35 ET) was absent at that instant. At 14:37:50 UTC the cache held 66 of 67 completed slots, with the latest minute (10:36 ET) absent. These as-of cache counts include retained recovery data and do not establish availability at historical decision times. A missing newest bar within the allowed tail-age budget is distinct from an internal continuity gap.

VERIFIED IN OPERATION at 14:36:45 UTC: exact strict quote predicate SOURCE_TOO_OLD; signed source age +10.593 s, receipt age +0.343 s, source/receipt difference -10.250 s. At 14:37:50 UTC it again failed SOURCE_TOO_OLD with source age +73.198 s and receipt age +58.216 s. Recent receipt alone cannot satisfy the five-second source-age gate.

VERIFIED IN OPERATION: the worker continued completing cycles. Observed cycle durations included 16.360 s, 6.437 s and 15.390 s against its 10 s cycle budget. The first and third missed that budget; the middle did not. Retained metrics at 14:34:17 UTC showed bounded SQLite busy retries and two failures since process start. This does not establish a single causal explanation for latency.

Verification used python -m ops.supervisor status, read-only SQLite transactions, a clock taken after coherent snapshot reads, independent completed-minute set comparison, and source inspection of the verifier. No new synthetic observations entered production stores. Broad tests were not repeated for this report-only change. The release guard was run on the staged public report; its result is part of the publication check rather than evidence of live readiness.

## Limitations

BLOCKED: sustained fresh underlying eligibility is not established. Capture recovery and connected services do not resolve delayed quotes. The cause of recurrent source/receipt delays and intermittent cycle overruns remains undetermined; do not attribute it to provider entitlement, local clock, networking or database contention without additional evidence.

BLOCKED: genuine option data access and option-level strategy evidence remain unestablished. LIVE_SIGNAL_READY, live signals and execution remain false. IEX is single-exchange underlying research only. No option recommendation, option profit or future-return probability is inferred.

The live verifier is a once-per-minute prospective sample, not a tick census or full-session report. Its sub-millisecond median computation time is local evaluator execution time, not source-to-receipt network latency. The full-session report remains scheduled separately for 16:20 ET. Initial failures and previous issued reports remain as-of artifacts.

## Setup impact

None. Continue using SETUP.md and OPERATIONS.md. Keep the host awake and online. The next focused engineering investigation should separately measure quote source/receipt/evaluation ages, provider transport timing, cycle phases and independent bar coverage. Preserve strict gates; never retime history, widen freshness limits or replay uncertain messages to make results appear ready.
