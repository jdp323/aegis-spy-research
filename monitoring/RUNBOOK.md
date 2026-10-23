# Telegram and service runbook

Current setup: ../SETUP.md. Current operations: ../OPERATIONS.md. Registry: command_registry.cjs. All credentials and recipients are installation-local; pair the bot using python -m ops.setup telegram. Never publish access.json, inbox/outbox, user ledgers or receipts.

Only definitive failures retry within bounded expiry. UNCERTAIN_AFTER_SEND and legacy PENDING_OR_UNCERTAIN do not automatically replay. Inspect python -m ops.receipts; owner confirmation is not guest confirmation. An accepted initial idea must precede dependent updates for that recipient.

Privacy and research gates are not bypassed by INFO messages. BUY/SELL/TRADE_PROPOSAL remain blocked. No development guest messages.

## October 23 measured-session review

Current as-of evidence: [October 23 review](../reports/updates/2026-10-23_measured-session-review.md). All 25 trend slots and the recap received Telegram API acceptance. Native coverage/schedule PASS accounts for 388 real bars, one provider-confirmed no-print slot and one unresolved final-minute gap; it does not establish live readiness. First-hour FAIL, database contention and deadline misses remain. No gaps, quotes or personal positions were retimed or inferred closed. Original packets and reports remain as-of artifacts; no runtime, sharing or gate change was made.
