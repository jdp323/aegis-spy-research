# Producer and reliability inventory — October 22

One active production installation was found on this Windows host, plus a separate public source clone. Timestamped backups, restore directories and historical test workspaces are dormant copies. No second running AEGIS installation or Windows service was found. This is a bounded host inventory, not visibility into other computers or third-party bot clients.

| Component | Role | Telegram authority |
|---|---|---|
| ops.supervisor | Local singleton; six managed children; backoff and status | Private service warnings only |
| app.py | Dashboard HTTP on localhost8767 | No scheduled market producer |
| core.upgrade_service | Main worker; ideas, review, calendars, scheduled messages | Sole current premarket/status/recap composer via core.idea_service |
| core.spy_research | Public historical research collection | No Telegram transport; historical context remains labeled |
| data.stream | SIP/IEX/OPRA read-only feeds | Writes source-tagged inputs; no market-message composer |
| monitoring/commands.cjs | Authenticated polling and command replies | On-demand replies, not a second schedule |
| monitoring/dispatch.cjs | Durable per-recipient delivery | Sole queued-message transport; acceptance is not phone receipt |

One current-user startup task launches ops.supervisor with IgnoreNew. Local singleton port8768 and dashboard port8767 each had one listener. The production path, PIDs, executable paths, command hashes and task details are retained privately in the verification packet. Unrelated processes were not stopped.

Current scheduled IDs are v5-preopen-DATE, v5-trend-DATE-SLOT and v5-recap-DATE. Their durable reservations now use atomic INSERT OR IGNORE. Legacy premarket and paper notification routes are disabled when the idea engine owns the schedule. Optional public periodic/extended/news/sentiment pushes remain off. Existing signals.shared=true remains unchanged; development tests used fake recipients only.

Exactly one October21 PREOPEN and one RECAP envelope were retained. The apparent recap conflict is evidenced by mixed populations:14 alerted ideas versus37 total underlying observations. The new recap reports the alerted cohort and names silent observations separately. On-demand trend and scheduled trend use the same compact formatter/primary-plan state; saved premarket and historical replies retain explicit as-of labels. No claim is made that an unseen external producer was removed.

Active databases: runtime/aegis.sqlite (state/audit/forecast events); runtime/history.sqlite (append-only bars/options); runtime/ideas.sqlite (legacy/main observations and matched-clock baseline); runtime/horizon_ideas.sqlite (separate horizon populations); runtime/observability.sqlite (stream/continuity/decision evidence); runtime/paper.sqlite (proxy/genuine-option/forward populations); options/reported.sqlite (private reports); risk/control.sqlite (risk reservations); and two separate invited-user report ledgers. Their paths and identity mapping remain private. Ten SQLite online backups were restored into isolated directories with integrity/count checks;3,621 backed-up files also passed hash restoration.

## Evidence and limits

On the same13,902 retained rows, three sequential read-only repetitions reduced median normalization0.567→0.309s and latest-position reads0.100→0.026s (same122 latest positions). This measures local parsing/query work, not provider latency. The normalizer now reuses verified session windows and coherent validated bars; the tracker selects latest append-only snapshots in SQL without hiding external appends.

The previous stream ran three sockets on one event loop with synchronous SQLite/history work. Each feed now owns an independent thread, event loop and SQLite connection. Transport receipt is captured before decode/sort/SQLite and local queue delay is reported separately. It is never replaced with processing time. Original source timestamps, strict source/receipt/skew gates and real missing gaps remain. The change removes a demonstrated blocking mechanism; it does not prove that every old stale quote had that cause.

Closed-session proxy reviews skip unnecessary indicator reconstruction. Network history and latest-tail repair remain separate bounded background paths. Existing SQLite bounded retries, coherent reads and append-only records remain. HTTP/service and post-restart phase measurements are in the release report. Genuine market-hour before/after comparison remains pending; October21's failed first-hour verifier is preserved.
