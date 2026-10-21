# Verification evidence — Telegram experience, October 21, 2026

## Scope

This safe public evidence summary excludes private ledgers, recipient identifiers, raw credentials, runtime databases and unsanitized installation packets. Original failed and passing runs remain local. These hashes bind the canonical staged Git source to the named checks; no test proves entitlement, phone delivery or profitability.

## Automated verification

- Initial public baseline: 752 passed.
- Final public full run: 780 passed, zero failures/errors/skips (712 general Python, 7 backtesting, 4 monitoring, 57 explicit Node tests).
- Corrected installed full run: 772 passed, zero failures/errors/skips (705 general Python, 7 backtesting, 4 monitoring, 56 Node). Separate population; do not pool.
- Command roles: 540 cases, all 36 commands across five roles and three argument forms.
- Full schedules: 24 scenarios, 401 actual-notifier fake sends.
- Owner-requested day: 29 actual-notifier fake sends; midday restart; no duplicates.
- Real owner-only demo: five Telegram API acceptances; no guest test sends or claims of phone delivery.
- Targeted final audit/packet tests: 71 passed.

Commands: `python -m ops.ci_tests`, `python -m ops.verify_commands`, `python -m ops.day_simulation`, `python -m ops.verification_packet --run-tests --compact`. See the update report for retained failures, operational measurements and unavailable market-session checks.

## Source and test SHA-256 manifest

Canonical Git blobs, before publication. Installation-specific runtime path substitutions are separately retained in the local deployment manifest.

| File | SHA-256 |
|---|---|
| app.py | 1b74880de8a7177498e78a49a9e0d0be1ba057d3e020114bc522df899d436a9f |
| core/bot_commands.py | 792a43b88796143c651061cb5f228b930ebb991d79c509cafd3fefb882a43a60 |
| core/directional_research.py | e589eb575d395c3dd563735a114247cb6603e88ef4a75256925eb525caac0bb5 |
| core/idea_service.py | 2948639cd6916b97313aa31f9c19b574f7f272bdb6c413724be9b4d97495d9b1 |
| core/rejection_trace.py | b965efd5f9c5f1e9dd79fbd3961b18615d8490b8a3733cf0055ec89b6464328c |
| core/research_pause.py | ee02de3a7c3513c4eb3941d92af1f1de070a3da2665e47ff12e3ab1bad2d6597 |
| core/storage.py | 1cbfb8a066203286d7a01158de53c8e1a11b921643e44906e0913c5551146e2a |
| core/upgrade_service.py | b171a5055af0d60d9187deb3491dd004c8b2fd26ef37a7fec66aafb9da717952 |
| core/v6_service.py | b014e0f042f186d28f3bdc4ace27893db9abceeb9ffedcc8447dab193c5415c9 |
| data/backfill.py | 315e9b1efb85494fc289f217fc66ea33262df94055154678f07c289370fdfca3 |
| data/corporate_actions.py | 839e7dde5837bd445eb20ed5592db4ad76bd4fb5d4321408abb17863203cb815 |
| data/providers.py | a45fa1d60b74314e1f48952a33f2d8560f6aa395e59bbdb9ecbe4013c1ba3d24 |
| data/reliability.py | dd75e3d811e67d68e3f1451cba539d5cf24a7fc1a5f0ad537de3f092af4393cc |
| data/session_recorder.py | c60d01fe0b91251261d8fb439b57652bf134e41069ec27c718bd8de5f2ffc78e |
| data/stream.py | 173776eb13c587b057b4309f1f1917e510b11b8397e428dffd1616d85947b887 |
| features/indicators.py | 263b226c1750c9a1a972935e57d6716a390f0b197cba2c35477d7e0c76aac7b0 |
| monitoring/day_schedule.py | 07832ee0947aa3a844f46a0755d9f5b26a35291cae8c2e7b2c3107aa755d6ed9 |
| monitoring/message_format.py | bcf8a8be2e1be12261aec6b00ae2e7bf5a3e6f30096fc9baf9f676a6ddab46c7 |
| monitoring/notifier.cjs | 55f166855e3a4b6774d6f7e7471d88392096c7b692047809115661ae4a130989 |
| monitoring/owner_messages.py | f6be436c1400cc5adf530046724e01934c7f678df389310953ab54a634df5ae3 |
| monitoring/test_owner_presentation.cjs | 6755e8798a8ecddb8eb4610fb000fa20b3b8047bd294ffb1ca7504031f782e5b |
| ops/day_simulation.py | 35d8fab5eb053e31302ac0f5f158876d899de5b8e0e5cefd143a40eca020adea |
| ops/demo.py | 0e79de842c938316cde468de360891a21a95f74b00f917dca710c52a89a0fd58 |
| ops/published_replay.py | a93f724278d479a76c398e9c6c87f77871d6e90c266b27a02fc4ed7d50b2b4d8 |
| ops/verification_packet.py | 41e56d91de6ba06ea4ccad7e73f79dfee1700daebeb425c8cbc82f7c2c5c289d |
| strategies/idea_setups.py | a8d2ce917f72af736bf2c7118f26aab25126973a98c5c786b725eb58de02cd68 |
| strategies/published_baselines.py | 5fa8a9e26e57c4f5ca254d74f564eb17216703f1bc406d803c6f5d90256421bf |
| tests/test_complete_telegram_messages.py | 50372734e6f7e82cc96c543458b7d66065619b68fac5a3c37de2be9f95a2944c |
| tests/test_completion_endpoints.py | a465e970b7de25763c28aac3302f99799a701027d390639e7b19f2c2bf0cc00e |
| tests/test_owner_experience.py | b00be5e096ecb63b95230d62bb91ee1f184e9f47c8c0d3a67a9bcdad3ad3ced9 |
| tests/test_scheduled_preopen.py | 8e04e8eb31be4b7aed49050fab237436cffce5e3c7421dbbbcb32a64f96f0477 |
| tests/test_v5_controls.py | 462de53ed73ded7f3476336528699c5317522530bf569efdd941047e69c1187d |
| tests/test_v5_demo.py | e18e4428588228b3ce907ed16631199e5a1bb7d90051bdfa2486cb49c5274c08 |
| tests/test_v5_ideas.py | 1938fa58f185b54dae8e8e67e7c9f71db453ab27e72e7bb31f4827bf9d736877 |
| tests/test_v6_reliability.py | ac53668091b8a285574bb519eafc50309743b7bb8e42e9ffd6a40d5194663e85 |

## Current operational observations

Actual scheduled premarket: seven lines; Telegram accepted at 09:15:28 ET on October 21. Native compact verification packet: 214 manifest entries, 122,425 Markdown bytes, all original fields secret-scanned; hard cap 150,000 bytes preserved. Native packet SHA-256: `9dbf978720506364f01155c20a1310b49d4c36c5f6fba233ebcff0532b51a987`. Raw packet stays private.

Final current-source full public rerun: 2026-10-21T13:17:27.262483+00:00, 780 passing checks, zero failures/errors/skips. This includes the final compact serialization regression.
