# Read-only status observation clock — 2026-10-20

## Changes

TESTED IN ISOLATION: status used to take its evaluation clock before reading concurrently updated heartbeat files and worker state. A heartbeat written during the reads could then appear to be in the future even when the clocks agreed. For example, evaluation at 13:30:00 followed by a read of a genuine 13:30:01 heartbeat produced age -1 s. Taking the clock at 13:30:02 after the reads gives age +1 s. This race explains an artificial negative diagnostic age; it does not establish the cause of delayed market quotes or all observed negative timestamps.

The read-only ops.supervisor.status function now reads each heartbeat observation, reads worker cycle state and performs its bounded local HTTP probe before sampling the evaluation clock and calculating signed ages. It reuses the already-read services snapshot for both component metadata and its heartbeat. Missing/malformed times remain unavailable. A genuinely future timestamp still produces a negative age; there is no clamp and no widened quote, receipt, skew, heartbeat, bar or calendar budget.

Changed files: ops/supervisor.py; tests/test_supervisor_status.py (four regression cases); SETUP.md (status interpretation); this update report. No config/schema changes. Runtime start, singleton, watchdog, restart and stop functions were preserved. Local source/test backups plus a setup-document copy were retained before replacement under the private backup folder status-clock-20261020T143544331Z; the private manifest records original SHA-256 values. Databases and historical data were not migrated or rewritten.

## Verification

Baseline targeted module: two tests passed. With the new read-race regression before the fix: four tests passed and one failed at the expected post-read-clock assertion. The failure is retained in the private test checkpoint; no assertion was weakened. After the fix and the additional bounded-HTTP-probe case:

| Exact command after the environment's Python executable | Passed | Failed / errors / skipped |
|---|---:|---:|
| -X utf8 -m unittest discover -s tests -p test_supervisor_status.py -v | 6 | 0 / 0 / 0 |
| -X utf8 -m unittest discover -s tests -p test_completion_stream_cache.py -v | 9 | 0 / 0 / 0 |
| -X utf8 -m unittest discover -s tests -p test_worker_reliability_completion.py -v | 21 | 0 / 0 / 0 |
| -X utf8 -m unittest discover -s tests -p test_completion_endpoints.py -v | 2 | 0 / 0 / 0 |
| Total distinct targeted public-copy cases | 38 | 0 / 0 / 0 |

These used the public clone's isolated Python environment. The six status regressions also passed with bundled Python against the production source while using temporary fixture files/databases and fake transports. Tests verify advancing file-read time, the bounded local HTTP probe, genuinely future timestamps, unavailable timestamps, single services-file read, read-only file bytes, and existing CLI/worker/cache/endpoint protections. The HTTP timing test uses a fake response and asserts the existing two-second timeout and 4096-byte bounded read.

VERIFIED IN OPERATION: a fresh bundled-Python invocation of python -X utf8 -m ops.supervisor status at 14:38:36 UTC returned all six component processes present, dashboard HTTP 200 and recent completed-work telemetry. Its reported supervisor/listener/dispatcher ages were +0.941/+0.616/+1.758 s. This is one observation, not proof of ongoing uptime. Worker cycle duration remained 15.719 s against its ten-second budget, so the existing worker deadline/SQLite issues are not marked solved. LIVE_SIGNAL_READY and execution remained false.

The tested status-function change was applied to the production module while preserving the other production functions. No service restart, notification, credential read, brokerage request or private-ledger rewrite was needed. A fresh CLI invocation loads it immediately. An already-running process that cached the old function is not claimed refreshed; it loads the change on its next normal restart. No session readiness or strategy evidence is inferred.

Public file hashes before staging:

- SETUP.md: 56e897b2860f48723e7d2bbd77f4efda45c27f8c09ffff44f02ce5342d2a50c0
- ops/supervisor.py: 48207c5472a4ee7a5f11396da8143a59b087981a71ca044fa30f86265a2e3ab3
- tests/test_supervisor_status.py: 45669fd49eea0b93583647cfb101e5a32d33ca96356fdfc7c2fe7da0fcb50579

The staged-tree release guard is required before publication. The earlier full-suite results remain their original as-of artifacts; no new full Python/Node-suite completion is claimed by these targeted checks. GitHub CI is triggered by publication and its result must be inspected independently.

## Limitations

This is diagnostic truthfulness only. It does not fix source/receipt latency, database contention, missing bars, permission errors, Windows clock synchronization or stream availability. Multi-file observations are read once each; this is not an atomic snapshot spanning all processes and SQLite. Genuine negative ages remain visible.

The current session remains research-only. Strict five-second source/receipt eligibility and continuity requirements still apply. SIP/OPRA access and sufficient option-level strategy evidence remain unestablished; live signals and execution remain disabled. No overnight operation or profitability is claimed. New tests and passing CLI output are not live-market validation.

## Setup impact

No dependency, credential, configuration, installation command or permission change. SETUP.md explains the corrected status-age semantics. Existing startup/status/stop commands are unchanged. A fresh read-only CLI invocation needs no restart; a long-running importer uses the new function after its next normal restart. Preserve personal configuration and sharing preferences.
