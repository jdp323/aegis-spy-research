# October 29: bounded stream-control recovery and final session results

The deployed supervisor now distinguishes a declared provider retry wait from a hung stream. This corrects a reproduced process-control interaction; it does not establish the cause of provider connection limits or fix all source/worker delays. Today's old-release session still failed live acceptance: **25 updates API accepted, 14 timely, zero passing applicable underlying gates**. Recap acceptance was 16:15:35 ET. Telegram acceptance is not phone display.

## Changes and reason

In the 09:20–16:00 ET evidence window, the prior supervisor recorded 73 WATCHDOG_RESTART events. Actual IEX 406 and SIP 409 refusal responses were retained separately. Seven isolated diagnostic cases reproduced the old restart predicate: after its 300-second process grace it could request termination while a one-second-old PermissionError status declared a 300-second retry wait. This identifies a restart-policy interaction; it does not prove all 73 terminations were avoidable or identify an external/retained connection holder.

The versioned **stream-control-progress-v1** policy adds bounded control-progress checks in [ops/supervisor.py](../../ops/supervisor.py). [data/stream.py](../../data/stream.py) records a separate local connection_started_at in control state and preserves it during ingest. That field is never a provider quote timestamp, quote receipt time or proof of market readiness.

| Control phase | Bounded supervisor treatment |
|---|---|
| Explicit PermissionError retry wait |Honor a finite declared delay from zero to 301 seconds, including existing jitter, plus five seconds for retry handoff|
| CONNECTING |Allow less than 40 seconds from the current attempt start, corresponding to existing open/greeting/auth/close bounds|
| CONNECTED / CONNECTED_IDLE before new market evidence |Allow less than 90 seconds from attempt start; a newer idle heartbeat cannot extend this clock|
| Expired, unknown, malformed, future or prior-process control record |No new exemption; original market-message watchdog applies|

The 300-second startup grace and existing child network timeouts remain. Permission waits can complete without a gratuitous parent restart, while expired/hung attempts remain recoverable. Supervisor state reads are query-only, coherent and use a bounded half-second lock timeout. No source/receipt five-second gate, signed-skew rule, 30-second entry heartbeat, bar continuity, calendar, risk, option or execution gate was relaxed. Missing or legacy control metadata receives no new exemption. A fresh trade, bar or process heartbeat still cannot refresh old bid/ask data.

## Verification and results

Twenty new [regressions](../../tests/test_supervisor_control_progress.py) exercise the actual supervisor predicate with isolated SQLite and the actual stream state/ingest paths. Eight failed before the implementation; all 20 now pass. Cases cover handoff/jitter boundaries, invalid/unbounded delays, old/future/naive control clocks, unknown states/errors, hung connection expiry, unchanged legacy 300-second boundaries, real receipt recovery, persisted attempt identity and rejection of a six-second-old BBO despite valid control progress. Clocks/control payloads are synthetic fixtures, not market evidence.

| Check | Result |
|---|---|
| New control-progress cases |20 passed|
| Existing related stream cases |34 passed|
| Full portable Python |795 main + 7 backtesting + 4 monitoring|
| Full portable Node |61 passed|
| Full portable total |**867 passed**, zero failures/errors/skips|
| Full installed Python |788 main + 7 backtesting + 4 monitoring|
| Full installed Node |60 passed|
| Full installed total |**859 passed**, zero failures/errors/skips|
| Source/config/history integrity |62 reviewed source/test hashes; expected configuration, original private-history prefixes and original issued packet passed|

Exact commands: public `python -X utf8 -m ops.ci_tests`; installed `python -X utf8 -m ops.test_runner`; targeted `python -X utf8 -m unittest discover -s tests -t tests -p test_supervisor_control_progress.py` and the same discovery with `-p test_*stream*.py`. Full runners use short isolated Windows roots, fake transports, stripped credentials and explicit Node files. Both full JSON successful fields were checked, not only launcher exit codes. Packaging/setup cases explain the differing totals; there were no skips. All three deployed files match the retained successful public and installed suite copies byte for byte. Existing command-role, schedule, formatter/dispatcher and receipt-order regressions are in those full suites. No development messages were sent to guests.

## Backups and local deployment

Source/configuration/issued-report preimages were preserved before changes. After completed session jobs and private request/reported-position review, the existing service group was deliberately paused after close. Six SQLite online backups include committed WAL data and passed full integrity plus isolated restore/count checks. The 1.50 GB telemetry database's complete copy, integrity, restore and verification work took 760.000 seconds; this is not copy-only time or a worker-performance measurement. No backup was restored over production and no historical outcome or fill ledger was rewound.

Only the two reviewed source files and new test were deployed after strict preimage and successful-suite binding checks. The same limited scheduled task restarted the existing group after both full suites passed. Seven components, fresh listener/dispatcher heartbeats, new completed worker phases, actual new connection-start metadata and HTTP response were observed. Old STOPPED/progress records were not counted as new work. The sampled new whole cycle was 50.063 seconds and still exceeded its ten-second budget; its new-process counters and after-close workload do not erase the prior 74 busy retries/17 failed transactions or maximum 9.187-second transaction. Cold/over-budget refresh observations remain recorded.

## Full-session evidence and Limitations

The immutable 16:20 coverage artifact reports PASS for its narrow 95% coverage/status-presence rules: 389 genuine minute records, 388 REST-origin rows, zero confirmed no-print slots and one missing minute out of 390. Native opening verification is FAIL with 58 observations and no qualifying trend observations. Historical repair, close-time authentication or an after-hours quote cannot prove original decision-time eligibility. No accepted qualifying entry provides a latency sample; null entry percentiles remain NO_SAMPLE, not a pass.

| Separate conclusion | Status and evidence |
|---|---|
| Bounded software change |TESTED IN ISOLATION; implemented/deployed control-policy fix|
| Automated verification |TESTED IN ISOLATION; both complete suites and targeted cases pass|
| Local group/metadata operation |VERIFIED IN OPERATION for bounded after-close HTTP, new work and control fields|
| Active-session behavior of new policy |IMPLEMENTED, EXTERNAL VERIFICATION PENDING; next actual session required|
| Genuine option research data |BLOCKED; no newly verified real option dataset/selection/outcome|
| Strategy evidence |BLOCKED for option-profitability qualification; software tests do not establish edge|

There is no genuine live-session before/after restart-rate measurement for this deployment: the after-close watchdog is inactive. Do not interpret zero after-hours restarts as proof of the fix's live benefit. Source-to-receipt delays, worker starvation/contention, sustained HTTP budgets and prospective session acceptance remain unresolved. The existing unresolved primary research control and private actual fills remain separate; no personal closure was inferred.

For a recurring IEX 406, identify an unnecessary competing client or ask the provider to identify/release a retained session; holder remains unknown. SIP requires provider-confirmed permitted market-data access for the existing key. OPRA/point-in-time historical chain and executable bid/ask data remain separate requirements in [owner actions](../OWNER_ACTIONS_MASTER.md). No subscription purchase, account permission change or brokerage request was performed. A token, connection or passing test is not entitlement.

## Setup impact and rollback

No new dependency, credential, schema or strategy parameter. Reload through the existing single supervisor/task; never run a second export or restore installation. [SETUP](../../SETUP.md) describes the new control-clock fields/windows. Rollback restores the saved source preimages and restarts the same group; do not rewind live ledgers from test/backup copies. Preserve sharing preferences, stable IDs, manual execution, parent-first delivery and uncertain-send refusal. Live/execution flags and blocked BUY/SELL/TRADE_PROPOSAL kinds remain unchanged. Periodic review is not continuous monitoring.

The initial publication guard refused the missing required Setup impact label; the heading was corrected before publication.

### Delivered source hashes

| File | SHA-256 |
|---|---|
|ops/supervisor.py|a194ce38c1818d2e27fbca4651927ac0dfc128c134df7fd3703251d4b45d699a|
|data/stream.py|d2d7147f70dac6dac9fbd9da833210144c7b62ec09539c878f6917f5f17dab9b|
|tests/test_supervisor_control_progress.py|c6ede75ed6890d53b8d62099846618b3e9ac60d6d59741345733e90b8d229cdc|
