> October27 current handoff: [master implementation report](reports/updates/2026-10-27_master-implementation.md), [current status](reports/CURRENT_STATUS.md), [setup](SETUP.md). Current files supersede conflicting older presentation/scope notes; dated evidence below retains its as-of meaning.

# Architecture and active algorithms

## Production paths

app.py serves the local dashboard and core APIs. ops/supervisor.py supervises dashboard, core.spy_research, core.upgrade_service, data.stream, monitoring/commands.cjs and monitoring/dispatch.cjs. core/storage.py provides SQLite transactions, coherent snapshots and append-only audit records.

core/idea_service.py is the research scheduler/context/setup and message path; core/idea_config.py defines supported setup switches. features/indicators.py builds completed-bar indicators and higher frames. strategies/ contains the underlying scoring and setup families. options/ contains quote/contract selection and reported-fill ledgers; backtesting/ separates proxy, idea and option populations. research/forward_study.py and related live modules provide diagnostics. news/ and monitoring/premarket_brief.py provide descriptive news/premarket context. risk/ and accounting/ include retained supporting research modules, not brokerage execution authorization.

## Read the exact algorithm

Source is the specification: core/idea_service.py (setup predicates, structural levels, entry/holding rules), features/indicators.py (VWAP, EMA, ATR, resampling and frame availability), strategies/ (scoring/votes/regime), options/ (actual contract and quote eligibility), backtesting/ (cost/fill/outcome assumptions). Each rejection retains measured predicates and thresholds for /why. Do not infer current configuration from an old report.

Completed-bar H60, H120 and remaining-session variants have separate research identities. Evaluation cadence, fifteen-minute notification cadence, entry expiry, planned holding deadline, realized exit and contract expiry are distinct. Higher frames use completed candles. Overnight support remains disabled.

A descriptive bar bias may remain available while a stale bid/ask blocks new entry eligibility. IEX underlying evidence cannot satisfy consolidated or option gates. Real option selection requires the actual chain, listed expiry beyond holding, valid timestamped bid/ask, feed provenance, liquidity and all hard gates. A fixed-delta estimate cannot qualify option profitability.

## Telegram and private records

monitoring/command_registry.cjs is the single command registry; commands.cjs handles role/argument checks, callbacks bind to the configured or API-verified bot identity, and notifier.cjs/dispatch.cjs enforce kinds, recipients, durable reservations, retries and dependent update order. Definitive failure and uncertain-after-send are separate. Reported fills, FORCE duplicates, VOID corrections and reconciliation remain private and append history. No command submits orders.

## Portability boundary

core/runtime_paths.py and monitoring/runtime.cjs select normal installed runtimes. Fresh installations use their own encrypted .private store and locally paired bot identity. Public defaults contain no provider token or user destination. Public research reports do not include the source installation's databases, receipts or performance evidence.
