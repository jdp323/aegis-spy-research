# Telegram and service runbook

Current setup: ../SETUP.md. Current operations: ../OPERATIONS.md. Registry: command_registry.cjs. All credentials and recipients are installation-local; pair the bot using python -m ops.setup telegram. Never publish access.json, inbox/outbox, user ledgers or receipts.

Only definitive failures retry within bounded expiry. UNCERTAIN_AFTER_SEND and legacy PENDING_OR_UNCERTAIN do not automatically replay. Inspect python -m ops.receipts; owner confirmation is not guest confirmation. An accepted initial idea must precede dependent updates for that recipient.

Privacy and research gates are not bypassed by INFO messages. BUY/SELL/TRADE_PROPOSAL remain blocked. No development guest messages.

## October 23 measured-session review

Current as-of evidence: [October 23 review](../reports/updates/2026-10-23_measured-session-review.md). All 25 trend slots and the recap received Telegram API acceptance. Native coverage/schedule PASS accounts for 388 real bars, one provider-confirmed no-print slot and one unresolved final-minute gap; it does not establish live readiness. First-hour FAIL, database contention and deadline misses remain. No gaps, quotes or personal positions were retimed or inferred closed. Original packets and reports remain as-of artifacts; no runtime, sharing or gate change was made.

## October 26 missing-session incident, reviewed October 27 UTC

See [clock-discontinuity review](../reports/updates/2026-10-27_missed-session-clock-review.md). This installation has no retained October26 scheduled envelopes or native session verification. Windows recorded large forward/backward clock changes, and wall/monotonic phase durations diverged by about23h48m. Services respond now; after-session REST bars do not reconstruct live monitoring. Host/VM time stability and uninterrupted operation require investigation before reliance. Do not replay expired schedules or uncertain sends. The calendar warning on resumption is uncertain, not confirmed delivery. No gate, clock, permission or sharing change was made by the review.
