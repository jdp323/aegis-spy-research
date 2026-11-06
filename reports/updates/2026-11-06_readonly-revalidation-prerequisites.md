# Read-only scheduled revalidation prerequisites — November 6, 2026

## Changes and reason

Added eight isolated verification cases for reusing the existing query-only SQLite facade and actual underlying evaluator in the pending scheduled publication integration. Reusing the existing evaluator preserves its source, receipt, heartbeat and continuity predicates instead of duplicating them in a new gate. No runtime algorithm or production component changed.

The cases verify missing-database refusal without creation; no-op diagnostic writes and direct SQL write refusal; a coherent snapshot during a concurrent WAL writer commit; preservation of the exact original quote and 31 completed-bar fixture population; rejection after a delayed read advances the evaluation clock; future source/receipt refusal; existing heartbeat/continuity refusal; and transaction rollback after a snapshot read failure. All data are expressly constructed offline fixtures. Fields representing real-time data are fixture inputs, not provider evidence.

## Verification

- Only the new test module ran: **8 PASS, 0 failures, 0 errors, 0 skips**. Network entry points were blocked, with an isolated temporary directory and a restricted environment. No transport, vault, market-data API or production database was used by the cases.
- The exact public test bytes match the tested private file. All ten compared runtime dependency files match the tested and public bytes. Nine also match installed raw bytes; installed `data/backfill.py` differs only by verified CRLF/LF line endings. The initial raw-byte preflight assertion failed and was retained; normalization was used only to inspect this exact line-ending difference, with no source rewrite. No runtime module was edited. Reproduction: `python -m unittest discover -s tests -p test_scheduled_readonly_revalidation.py` in an isolated environment.
- The previous 91 scoped candidate cases and the completed 953 portable / 942 installed profiles were not repeated. The total of 99 distinct scoped cases includes these eight **prerequisites**; it is not a completed integration or full-regression result.
- Original failures, issued reports and private candidate artifacts retain their as-of meaning. The earlier snapshot identity hypothesis remains NOT REPRODUCED; these new cases do not change that finding.

Operational reconciliation at 12:31:58 ET found 12 of 12 due owner statuses API-accepted once, seven within 30 seconds and five late. The 12:30 acceptance was 101.582 seconds after its scheduled time. This extends the already-issued daily timing failure; no missing/uncertain outcome appeared in this cohort and no resend was attempted. API acceptance does not establish phone delivery.

The original first-hour report remains FAIL: 32 recorded sample minutes, 3.125% quotes within five seconds and 0% qualifying 31-bar tails. Its analysis p95 of 155.527 ms is a separate population from whole-monitor, worker and transport latency. It is not a complete 60-minute coverage claim. HTTP timeout followed by one HTTP 200 and advancing work timestamps does not establish sustained recovery. Existing host/database/source failures remain.

## Limitations

The real structured scheduled-status publication gate and operational factory remain unimplemented. Exact immutable text/snapshot binding, original-observation rechecks at publication, actual worker injection, explicit schema migration, refusal/failure audit and full recipient/broadcast/dispatcher integration remain pending. The opt-in bridge is private and undeployed; the default private and production schedulers still use the legacy path. These tests grant no publication permission and do not fix the handoff gap or latency.

IEX remains one-exchange underlying research only. SIP/OPRA entitlement, genuine option terms/BBO/Greeks/liquidity and strategy profitability remain unestablished. No strict freshness, skew, heartbeat, continuity, calendar, risk or option gate was relaxed. Incumbent rules and the two shadow candidates remain unchanged. No new changing market or macro claim is made; stored news fetch metadata is not direct verification of current independent-source availability.

## Setup impact

None. No installation, credentials, dependency, configuration, schedule, sharing, service restart or operational procedure changed. No brokerage/account/order/fund operation, subscription, permission change, owner confirmation or uncertain/expired replay occurred. Live/execution flags remain false, blocked action kinds remain blocked, and every order remains manual. Periodic assistant reviews are separate from continuous holding monitoring.
