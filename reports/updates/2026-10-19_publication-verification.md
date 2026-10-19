# Publication verification and documentation correction — 2026-10-19

## Changes

Corrected the initial release report's setup-impact line from Node.js 22 to Node.js 24. SETUP.md, README.md, the CI workflow and the actual tested runtime already use Node 24 (tested locally as v24.19.0). No application source, strategy, data gate, credentials or operational configuration changed in this follow-up.

## Verification

VERIFIED IN OPERATION: the public repository exists at https://github.com/jdp323/aegis-spy-research and main accepted source commit 958c863d50338d982d1dd9ec02ad4fcefb0d7a62. Its 315-file Git tree matched the sanitized local index byte-for-byte and by mode, with no missing files or unexpected extras. SETUP.md and the release report were fetched back successfully. The local clone tracks origin/main and has the publication hook configured.

TESTED IN ISOLATION: 748 full-suite passes, zero failures/errors/skips; 540 cases across all 36 commands and five roles; 24 schedule scenarios with 419 fake transport calls. These are retained as-of results; this documentation-only correction does not require rerunning the broad suite. See ../TEST_RESULTS.md.

VERIFIED IN OPERATION: GitHub Actions completed successfully for the published source commit: https://github.com/jdp323/aegis-spy-research/actions/runs/39208571081 . This direct remote result is separate from the local isolated results. A subsequent documentation-only commit may have its own queued check; this statement refers to source commit 958c863d50338d982d1dd9ec02ad4fcefb0d7a62.

## Limitations

No new live-session, phone-delivery, provider-entitlement or option-profitability evidence is claimed. The initial SOURCE_MANIFEST.md is preserved as an as-of artifact for the initial source commit; later documentation changes are recorded by Git history and this update report. Private credentials, owner/guest records and operational datasets remain excluded.

## Setup impact

No new installation change. Use Python 3.12 and Node.js 24 exactly as the separate SETUP.md states. Fresh users supply their own Telegram bot and authorized market-data access. The current engine does not consume an AI key.
