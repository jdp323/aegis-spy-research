# AEGIS SPY research assistant

> Current release: [October27 implementation and verification](reports/updates/2026-10-27_master-implementation.md). Start with [SETUP.md](SETUP.md); feature status, live-data limits and external actions are separate.

A local, research-only SPY assistant with Telegram commands, a dashboard, data-quality gates, separately tracked research horizons and private user-reported fills. All trades are manual.

**Start with [SETUP.md](SETUP.md).** Use your own Telegram bot and authorized market-data access. The current engine is rule based: an AI API key is neither required nor consumed. Supported operational setup is Windows 10/11 with Python 3.12 and Node.js 24.

- [Commands](COMMANDS.md) · [Operations](OPERATIONS.md) · [Architecture and algorithms](PROJECT_DOCUMENTATION.md)
- [Research limits](STRATEGY_RESEARCH.md) · [Security](SECURITY.md) · [Update reports](reports/updates/)
- [Contributing and publication policy](CONTRIBUTING.md)

The source is portable; credentials, personal records, cached market data and the original installation's evidence are excluded. A new installation starts unconfigured with sharing off. Your configuration does not inherit another user's entitlements or validation.

IEX is single-exchange underlying research. Strict underlying freshness, option quote, calendar and strategy gates remain distinct. Live signals and execution remain disabled. No option strategy is established as profitable by this export. Missing option quotes produce **Watch only—option pricing unavailable.** Demos and fixtures are synthetic, never market evidence.

Scheduled trading-day messages: 09:15 ET preopen, 09:20 owner self-check, silent status every 15 minutes 09:45–15:45, qualifying unvalidated research alerts, 16:15 recap and local 16:20 session report; verified early closes adjust schedules. An awake, online PC is necessary. Telegram API acceptance does not prove phone delivery.
