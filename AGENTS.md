# AEGIS repository instructions

All trades remain manual; live_signal_enabled, order_execution_enabled and LIVE_SIGNAL_READY stay false. Do not access brokerage account/balance/order endpoints. Keep underlying, option and strategy readiness separate.

For EVERY update published to GitHub, include a new sanitized report under reports/updates/ in the same commit or PR. Report changes, reasons, exact tests/results, remaining limitations and setup impact. Update SETUP.md whenever installation, credentials, configuration, dependencies or operational procedures change. Never call an unpublished local change uploaded.

Never stage credentials, DPAPI files, .env, user/access records, fills, receipts, databases, raw market caches, private reports or owner-machine paths. Use the release guard and review the entire staged tree before publication. Preserve user sharing preferences and history. Tests use fake transports; no development guest messages.

A passing test is isolated evidence, not live-session readiness, option entitlement or strategy profitability. Preserve failures and unknown causes.
