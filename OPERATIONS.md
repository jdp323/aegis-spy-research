# Operations

Use SETUP.md first. Start/status/stop: python -m ops.supervisor start|status|stop. Unknown arguments exit with usage. Status probes localhost HTTP and stored service progress; process existence alone is not data readiness. Ports 8767 (dashboard) and 8768 (singleton) are local.

Use /health, /feed, /details and /why to distinguish service health, current source/receipt timestamps, continuity and strategy rejection. The underlying quote threshold is five seconds, heartbeat thirty seconds and full continuity 31 completed current-session slots. At most two explicitly provider-confirmed no-print slots may bridge continuity only; never indicators or fills. Early reads require fifteen genuine bars and remain limited.

Same-feed REST repair retains provenance. Missing minutes remain missing unless confirmed by the provider. History never refreshes an old quote. No API keys means honest unavailable responses; no broker inspection is performed. Network calls, phase budgets, reconnection and pause events are bounded and logged locally.

Calendar: run python -m news.calendar_updater to attempt official-source refresh. Verify official URL, payload hash, parser completeness, coverage and actual fetched time. Preserve last-good data on failure. Seven-day freshness applies, with an owner warning three days before expiry. An unverified next year fails closed.

Daily: python -m ops.session_report --date YYYY-MM-DD writes local Markdown/JSON. Never publish private session reports automatically. python -m ops.receipts inspects uncertain sends by role without IDs; only owner-visible messages can be manually confirmed. Never blindly resend an uncertain delivery.

Before upgrading: stop, preserve encrypted configuration, back up all SQLite files using the online backup API (WAL included), and keep a source revision. Restore into a separate directory and check integrity before operational rollback. Never copy an active database file alone. A restore may have uncertain sends: preserve durable IDs and investigate rather than replaying.

After restart: check HTTP responsiveness, fresh completed worker phases, listener/dispatcher progression, outbox processing and exact data predicates. Closed-market checks do not establish live readiness. At the next verified trading session, inspect 09:20 self-check, capture from 09:30, the early 09:45 read, 31-slot restoration and 16:20 coverage. Record actual results; do not call this scheduled procedure a passed test.
