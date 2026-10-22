# Verification results — October 22

## Complete suites

| Source | General Python | Backtesting Python | Monitoring Python | Node | Total | Fail / error / skip |
|---|---:|---:|---:|---:|---:|---|
| Public portable source | 731 | 7 | 4 | 57 | 799 | 0 / 0 / 0 |
| Installed production source | 724 | 7 | 4 | 56 | 791 | 0 / 0 / 0 |

These are two source configurations, not pooled independent checks. Public source includes additional portable-install/runtime tests. Public completed 2026-10-22T06:11:16.624054+00:00; installed completed 2026-10-22T06:15:32.625769+00:00.

The real command registry passed36 commands × five roles × three argument forms =540 cases, including /details. Roles:owner,guest,stranger,revoked,expired invitation. The day scheduler passed24 scenarios and393 actual-notifier fake sends. Windows short isolated TEMP roots, blocked network/fake recipients and copied test workspaces preserve production state. No assertions were removed and no market-data tolerance widened.

## Initial failures preserved

The first bundled-base-interpreter run:725 general checks; two assertion failures and17 dependency errors; Node57,backtesting7,monitoring4 passed. Dependencies were present in the project venv; the corrected public run used that environment. The nine-idea daily-cap fixture was changed to nine sequential closed plans while retaining its nine-alert assertion; a separate new regression requires one primary plan for concurrent detections. The outage status regression restored WAIT/fresh-price refusal while retaining the active research record. A new exact-dollar assertion found a floating-point premium artifact; production dollar values now round to cents. The first full-day run lacked a direction-cooldown case under primary suppression; separate previewed control reasons were retained and the original scenario assertions then passed. Installed ops.ci_tests is absent; the supported installed entry point ops.test_runner was used. All failed outputs remain in private evidence.

New regressions cover concurrent detections, restart adoption, unresolved deadlines, entry expiry versus HOLD, compact recap cohorts, competing durable reservations, external ledger appends, original receipt time, per-feed independent threads, early-close/holiday/unknown-year rejection, genuine-contract data refusals and original-paper rules. Existing suites exercise auth/callback/fill corrections, privacy, uncertainty, ordering, source errors, append-only migrations and risk gates.

## Before and after reliability

Same retained13,902-row benchmark, three sequential repetitions: normalization median0.567→0.309s; latest-position read median0.100→0.026s for122 latest records. Source/result record counts match. This isolates local parsing/query work.

| Completed phase | Before samples | Before mean / max s | After samples | After mean / max s | Deadline misses before / after |
|---|---:|---|---:|---|---|
| idea_schedule | 25 | 2.550 / 13.297 | 19 | 0.733 / 2.078 | 1 / 0 |
| underlying_paper_reviews | 25 | 1.844 / 6.657 | 19 | 0.971 / 2.032 | 0 / 0 |
| reliability | 25 | 0.319 / 2.719 | 19 | 0.584 / 4.063 | 0 / 0 |
| reported_position_reviews | 25 | 0.014 / 0.078 | 19 | 0.011 / 0.016 | 0 / 0 |
| capture_and_session_checks | 25 | 0.291 / 0.797 | 19 | 0.289 / 0.484 | 0 / 0 |

These are closed-session windows under varying concurrent local test/backup load, with startup included. Reliability phase mean rose; do not read the table as a controlled market-hour experiment. Post-restart cycle samples9.875s(initial),1.281s and1.156s; the earlier pre-change sample14.703s occurred during audit/backup load. All four HTTP routes returned200 in all three post samples; the slowest observed post response was0.203s. New worker DB metrics showed zero busy retries/failures in the bounded sample and a0.031s maximum transaction duration. Production proof remains limited to those measurements.

The prior October21 first-hour live verifier remains FAIL. Source,transport receipt,queue delay,processing,evaluation and heartbeat times stay distinct. Provider rejects/reconnects are separated by feed;78 SIP rejection/reconnect episodes in the prior regular session do not prove78 IEX failures. No new live regular session was observed during this release.

## Recovery and preservation

3,621 backed-up files and eight SQLite online backups passed isolated restoration with hashes,integrity and counts. Two additional private ledgers were backed up online and restored separately. Every original row in the named idea/horizon/bar/option-snapshot/report tables compared equal after deployment; later legitimate appends were allowed. Current sharing and live/execution configuration hash remained identical. Calendar was independently refreshed from newly retrieved official sources and has its own provenance, not a timestamp-only extension.

Commands: public python -m ops.ci_tests; installed python -m ops.test_runner; python -m ops.verify_commands; python -m ops.day_simulation. Use the configured environment from SETUP.md. Raw commands,isolated paths,logs and JSON remain private. No broker/account/order operations, real development sends or guest messages were used.

Final re-verification after the historical-source input/partition work: public799 and installed791 passed, including three added frozen-partition/export checks. Both installed and portable24-scenario runs passed with393 actual-notifier fake calls. The earlier passing796/788 runs remain dated evidence. A temporary attempt to serialize test processes left a local audit helper looping on an empty process list; it was stopped by its verified PID/start time. No production process was targeted, and both final suites completed normally.

After the final expired-entry/gap recap classifier, the complete public799 and installed791 suites passed again with zero failures/errors/skips. A final installed normal-day transcript with a noon restart passed29 actual-notifier fake sends:one premarket,25 silent trends,one plan,one linked update,one recap. No real transport was used.
