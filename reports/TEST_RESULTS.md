# Public export verification — 2026-10-19

TESTED IN ISOLATION. This is an allowlisted summary, not the original private logs.

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| tests | 682 | 0 | 0 | 0 |
| backtesting | 7 | 0 | 0 | 0 |
| monitoring | 4 | 0 | 0 | 0 |
| node | 55 | 0 | 0 | 0 |

Total: 748 passed, 0 failures/errors/skips. Full suite checked at 2026-10-19T05:39:39.000995+00:00.

Commands: 36 commands, 540 cases, PASS. Owner, guest, stranger, revoked and expired-invitation roles; valid, invalid and empty arguments.

Schedule: 24 scenarios, PASS; 419 fake notifier calls. Includes normal/choppy/stale days, reconnect/backfill, opening-range recovery/refusal, PC pause, zero-volume premarket, holiday/weekend, early close and DST. No vault/network/real guest messages.

## Reproduce

~~~powershell
python -m ops.setup init
python -m ops.ci_tests
python -m ops.verify_commands
python -m ops.day_simulation
python -m ops.release_guard
python -m pip check
python monitoring/vault.py selftest
~~~

Python discovery: unittest discovery in tests/, backtesting/ and monitoring/ with pattern test*.py, launched from an isolated source copy with a short separate TEMP root and external networking blocked. No assertions were weakened. Node explicit file list:

~~~text
node --test --test-concurrency=1 monitoring/test_access.cjs monitoring/test_bot_identity.cjs monitoring/test_combined_menu_demo.cjs monitoring/test_command_pacing.cjs monitoring/test_command_registry.cjs monitoring/test_commands.cjs monitoring/test_dashboard_cache_view.cjs monitoring/test_delivery_order.cjs monitoring/test_demo_commands.cjs monitoring/test_details_route.cjs monitoring/test_notifier.cjs monitoring/test_paper_alerts.cjs monitoring/test_paper_callbacks.cjs monitoring/test_positions.cjs monitoring/test_profiles.cjs monitoring/test_role_routes.cjs monitoring/test_shared.cjs monitoring/test_sharing_config.cjs monitoring/test_status_encoding.cjs monitoring/test_trend_route.cjs monitoring/test_v5_schedule.cjs monitoring/test_v6_receipts.cjs
~~~

## Environment and additional checks

Windows; clean Python 3.12 virtual environment; Node v24.19.0. Dependency installation and pip check passed. DPAPI synthetic encryption/decryption self-test passed. Eighteen targeted fresh-install/pairing/publication regressions passed. The staged publication scanner passed. Fresh setup status confirmed no Telegram or market-data encrypted stores were included.

## Initial failures preserved

The first full public-export run had 679/682 main Python tests pass, plus 7 backtesting and 4 monitoring tests. Failures: omitted public BLS reader fixture; missing disabled-execution field before first research snapshot; a test assuming the original installation had sharing on. These were fixed by including the official fixture, adding the false execution field and testing both explicitly configured sharing values while fresh defaults remain off.

The first Node run passed 47 tests and reported two file-level failures after a JavaScript heap commit allocation error; those files did not finish collecting their tests. The complete serial rerun collected and passed all 55 tests. An earlier single identity fixture expected false instead of an intentional exception; its corrected assertion preserves rejection. Interrupted tool sessions were not counted as passing. Initial private logs remain retained locally.

## Limits

No genuine market session, real Telegram delivery, new-user entitlement or option strategy profitability was established. Fresh installations need their own credential pairing, event-calendar verification and live-session observation. CI checks are implemented; their remote run status must be observed separately. Coverage maps and fixture counts do not prove every possible behavior.

A duplicate schedule run after the final suite/command recheck was stopped when Windows began refusing process allocations. The earlier 24-scenario PASS is the schedule evidence reported here; the duplicate is not counted as passed.
