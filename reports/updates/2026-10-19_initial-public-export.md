# Initial public export — 2026-10-19

## Changes

- Created a separate portable public source tree. The private operational installation, its credentials, user/guest settings and historical records are not the publishing source.
- Removed fixed developer Python/Node locations, external private-store locations and the original Telegram bot identity. Python uses the current interpreter or AEGIS_PYTHON; Node uses PATH or AEGIS_NODE. Saved credentials belong to the new installation under .private or AEGIS_PRIVATE_DIR.
- Added hidden local-terminal credential setup, challenge-based private Telegram pairing, verified bot-identity callbacks and non-secret setup status. No bot token is accepted in CLI arguments or printed. Existing encrypted credentials are preserved.
- Fixed first-snapshot status so live_execution_enabled is explicitly false on a fresh installation; retained both sharing values in isolated configuration tests. Included the missing public BLS text fixture. Node tests run serially after a heap commit allocation failure; assertions and market gates are unchanged.
- Added separate SETUP.md, public README, operations, architecture, research limits, security, command reference, examples, MIT original-source license and third-party notices. The engine is rule based; no AI API key is consumed.
- Fresh-install defaults have live/execution false, option-risk confirmation false, sharing off and no verified event calendar. Existing installations do not inherit these defaults automatically. The original owner's sharing setting is unchanged.
- Preserved all 36 registered commands, research setup families, strict freshness/calendar/option gates, manual orders, private reported-fill handling, silent fifteen-minute messages and durable delivery ordering/uncertainty handling.
- Added a staged/committed-content scanner, Git pre-commit hook, CI workflow and AGENTS/CONTRIBUTING publication policy. Every future publication requires a new sanitized update report; setup-affecting changes also require SETUP.md.
- Excluded databases, encrypted stores, .env, access/recipient records, fills, receipts, raw private reports, historical market caches, vendor binaries and original operational evidence.

## Verification

TESTED IN ISOLATION: clean Windows Python 3.12 venv installation from requirements-upgrade.txt completed; seven new Python pairing/publication regressions passed. Windows DPAPI synthetic round trip passed. The working-tree publication scan passed after literal synthetic key fixtures were constructed at runtime and the OpenAI-key pattern was corrected to avoid matching the word risk inside official HTML fixtures. Assertions remain intact.

An initial Node identity fixture expected a false return where the implementation deliberately throws on mismatch. It failed, was corrected to assert the exception, and is included in the full suite. Broad verification attempts interrupted by local tool connections are not counted as passing.

TESTED IN ISOLATION: final full public-export suite 748 passed, 0 failed, 0 errors, 0 skipped; 36 commands across 540 role/argument cases PASS; 24 day scenarios and 419 fake transport calls PASS. See [TEST_RESULTS.md](../TEST_RESULTS.md) for exact commands, explicit Node file list, initial failures and verification limits. The full suite was checked at 2026-10-19T05:39:39.000995+00:00.

Commands: python -m ops.ci_tests; python -m ops.verify_commands; python -m ops.day_simulation; python -m ops.release_guard; python -m pip check; python monitoring/vault.py selftest.

## Limitations

This release does not establish live-session operation, a user's feed entitlement, genuine option history, option strategy profitability or future returns. Each installation needs its own credentials, provider access, official calendar verification and genuine-session observation. Windows DPAPI credential setup is the supported operational path. No AI integration, brokerage execution or overnight support is added. Tests use fake transports; no real guest development messages are sent. Telegram API acceptance is not phone delivery.

The publication guard rejects known paths and secret patterns; it cannot prove that arbitrary source or prose contains no private facts. Human review remains necessary. Hooks and CI checks are not branch protection, and a maintainer can bypass them. The public source starts with no personal records or performance evidence.

## Setup impact

CHANGED. Follow the separate SETUP.md. Use normal Python 3.12 and Node.js 24, install pinned dependencies plus Windows timezone data, initialize the incomplete local calendar, pair your own bot and configure your own market-data access. No original credentials, destinations or private configuration are distributed. GitHub is the public source/update-report destination; local operational diagnostic packets remain private.
