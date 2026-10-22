# Operations handoff — October 22

Use the existing production installation. The separate public clone is for publication and isolated verification, not a second running bot.

From the installation directory, using its configured Python:

~~~text
python -m ops.supervisor status
python -m ops.supervisor stop
python -m ops.supervisor start
~~~

Status is read-only. Unknown CLI arguments fail with usage. Inspect recent completed worker phases, listener/dispatcher times and bounded HTTP responses; process existence alone is insufficient. Dashboard: http://127.0.0.1:8767/ ; cheap liveness: /healthz. Never run two pollers for the same Telegram bot. Keep the current-user startup task and singleton ports; do not add another installation.

The worker composes one09:15 premarket,09:20 owner self-check, silent15-minute status slots09:45–15:45, instant eligible experimental research plans,16:15 recap and local16:20 session report on verified trading days, adjusted to early closes. One primary underlying research plan stays active until its recorded terminal event. Additional detections remain separate observations and do not overwrite its trigger, levels or deadline. HOLD means an underlying research observation; it never asserts a personal purchase. A missing price blocks new entry; unresolved monitoring does not close a reported position.

After restart, inspect /trend, /details, /feed and /health. A contract/premium remains unavailable until every genuine option data gate passes. Technical diagnostics are in /details; private reported fills stay in their own ledgers. Existing sharing preferences and live-disabled flags remain unchanged. Do not replay uncertain receipts or resend old slots. A duplicate producer investigation must inspect source paths, task actions, outbox IDs and recipient receipts before changing history.

## Next genuine session

1. Verify the official calendar is still within seven days and covers required releases; date-only HIGH events retain full-day blackouts.
2. Confirm source, transport receipt, local queue, quote/trade/bar and heartbeat ages independently. Missing or future data stay rejected. New source collection does not establish entitlement.
3. The existing prospective live verifier samples09:35–10:34 ET and writes the dated live report; compare quote ages, actual data predicates, decision-time continuity and worker phase durations. Preserve any FAIL. Do not reinterpret the old October21 failure as a pass.
4. Inspect the25 scheduled slots, single primary-plan lifecycle and one recap by durable IDs. Telegram acceptance is not phone receipt. Do not send development messages to guests.
5. After close, compare decision-time captures with later bar repairs; complete final backfill is not proof of availability when a decision was made.

This release was deployed while the market was closed. It cannot establish next-session exit coverage or future strategy profitability. Services require an awake, online Windows PC; periodic assistant reviews are separate.

## Rollback and recovery

Stop through the supervisor. Restore source/config from the timestamped pre-change backup and keep newer append-only history. SQLite backups were online snapshots including committed WAL data. Recover a damaged database into a new isolated directory first, run integrity/count/hash checks, then choose a deliberate recovery point; never overwrite newer history casually. The primary-plan key and SQL index are additive and do not require destructive migration. Do not copy a private encrypted credential store to GitHub. Raw backup paths, source change hashes and restore evidence are in the private verification packet.
