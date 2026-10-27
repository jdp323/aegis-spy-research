> October27 current handoff: [master implementation report](reports/updates/2026-10-27_master-implementation.md), [current status](reports/CURRENT_STATUS.md), [setup](SETUP.md). Current files supersede conflicting older presentation/scope notes; dated evidence below retains its as-of meaning.

# Verification

Use the venv created in SETUP.md. Run python -m ops.ci_tests for isolated Python discovery plus the explicit monitoring/test_*.cjs list. Run python -m ops.verify_commands for actual command handlers across owner, guest, stranger, revoked and expired-invitation roles and valid/invalid/empty arguments. Run python -m ops.day_simulation for fake-clock schedules and transports. No real guest messages are sent.

python -m ops.release_guard inspects the Git index before publication. --base SHA scans a committed change and requires a newly added update report. --working-tree scans selected public files but does not enforce an update report. Review the staged diff as well.

The existing verification_packet CLI generates local diagnostic evidence, not an automatically public artifact. It may summarize personal installation state; keep it private unless independently sanitized. Public update reports contain allowlisted summaries instead.

Status vocabulary: VERIFIED IN OPERATION requires observed operation; TESTED IN ISOLATION covers fixtures; IMPLEMENTED, EXTERNAL VERIFICATION PENDING requires direct source checks; BLOCKED identifies unmet dependencies; DEFERRED OUTSIDE CORE SCOPE does not claim support. Passing tests do not establish fresh quotes, option entitlement or profitability.
