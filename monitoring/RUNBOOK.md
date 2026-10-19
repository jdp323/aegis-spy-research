# Telegram and service runbook

Current setup: ../SETUP.md. Current operations: ../OPERATIONS.md. Registry: command_registry.cjs. All credentials and recipients are installation-local; pair the bot using python -m ops.setup telegram. Never publish access.json, inbox/outbox, user ledgers or receipts.

Only definitive failures retry within bounded expiry. UNCERTAIN_AFTER_SEND and legacy PENDING_OR_UNCERTAIN do not automatically replay. Inspect python -m ops.receipts; owner confirmation is not guest confirmation. An accepted initial idea must precede dependent updates for that recipient.

Privacy and research gates are not bypassed by INFO messages. BUY/SELL/TRADE_PROPOSAL remain blocked. No development guest messages.
