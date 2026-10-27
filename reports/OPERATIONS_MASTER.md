> Current postclose deployment and verification: [end-of-day report](updates/2026-10-27_eod-wait-reason-fix.md). New WAIT reason deployed with gates unchanged. Full-session acceptance failed; after-close recovery is bounded local evidence.

> Latest observed opening session: [October27 first-hour service review](updates/2026-10-27_first-hour-service-review.md). All four morning statuses reached API acceptance, but two exceeded30s; database busy retries/failed cycles returned. Today cannot meet the24-of25 timing target. Strict gates remain unchanged.

# Operations and reversible deployment

One production installation remains authoritative. The sanitized Git clone, backups/restores, reference archives and isolated test trees are not launched as service groups. The supervisor manages dashboard, public research worker, market analysis worker, independent market stream process, Telegram listener, dispatcher and a separate shadow worker. Only core.idea_service/atomic day_schedule creates scheduled owner-facing preopen/status/recap envelopes. The shadow worker produces local evidence only. Existing optional news/research/sentiment pushes and all sharing preferences are preserved.

Run from the intended installation with its installed Python:

```text
python -m ops.supervisor start
python -m ops.supervisor status
python -m ops.supervisor stop
```

No argument is read-only status; unknown modes fail usage. Start is singleton guarded on loopback8768. Dashboard/health are loopback8767 and /healthz. Check actual completed worker phases, signed heartbeat ages, listener/dispatcher progress and responsive HTTP; a saved RUNNING record or reused PID is insufficient. New stale service records are explicitly labelled. Children receive explicit runtime paths so scheduled startup does not depend on an interactive shell PATH. Existing current-user task uses limited privileges; three retries at1-minute intervals are bounded and do not override an intentional owner stop. Principal/recipient permissions are unchanged.

Before deployment the dashboard/health requests failed and dated service heartbeats were about4h old. Actual process inventory found no authoritative service group; a matching PID alone could be reused. Historical log entries do not prove why this group exited. The earlier clock-discontinuity incident remains unresolved. Do not diagnose credentials, entitlement, physical sleep or duplicate installations from a generic error.

Production backup:10 committed SQLite snapshots including WAL visibility; all restored integrity/count checks passed in a separate inert directory. Source/config hashes and initial failures remain private. Initial90s observability backup timeout was retained; pinned snapshot and streamed hashing completed. No specific cause for the timeout is asserted. Original issued packets and histories remain unchanged. Deployment copies reviewed source only; existing credential adapters/private locations, configurations, access records, encrypted stores, fills, outbox/receipts and databases are preserved.

Rollback: stop the service group, use the saved source manifest to restore only changed source/config files from the timestamped backup, remove only explicitly listed newly added source files, and restore the saved task XML/settings if needed. Do not overwrite newer ledgers, delivery reservations or reported fills with old databases. Verify the separate restore before selecting any database recovery path; restored/test directories are inert. Restart once and verify heartbeat/work/HTTP progress. Never replay uncertain or expired messages.

An unresolved primary plan remains UNRESOLVED after its clock deadline. Inspect /details and history. Only an explicit local research administrative cancellation can release its slot: `python -m ops.primary_admin IDEA_ID --reason "documented coverage limitation"`. This appends a separate control event, creates no observed exit/P&L and changes no private holding. Do not administratively close a monitored live research hold merely to generate another alert.

Full verification commands: `python -m ops.ci_tests`, `python -m ops.verify_commands`, `python -m ops.day_simulation`, `python -m ops.master_demo --output A_NEW_DEMO_REPORT.md`. Tests use isolated short paths/fake recipients. Research commands and source hashes are in the research report. For prospective targets use `python -m ops.master_session --date YYYY-MM-DD --output A_NEW_SESSION_REPORT.json`. The separate worker writes a new local MASTER_SESSION artifact at close+20; the existing native report remains. All25 normal slots stay in the denominator;24/25 timing and data targets are separate from valid calendar/risk WAIT. Entry p95<=10s requires actual accepted sample counts; no sample is not a pass. Three future full sessions remain pending, individually reported; no closed-market check establishes live coverage.

Isolated session-query benchmark:40,000 synthetic rows,1,000 selected, five repeats. Old median 0.125s; indexed date-bound median 0.002889839s. Exact result hash 0d263aece05780c259705e171b71f208b6d22085131494418ef231eba2a2f363. This replaces a full historical scan with an indexed date range and is not a claim that source latency or live database contention is solved.

Post-deployment evidence is appended by the final report generator after actual checks. No source check, test or current HTTP result establishes complete exit monitoring, option entitlement, a personal fill or profitable strategy.

## Measured final local operation

Observed October27,08:17–08:42 ET, before the regular session. Seven configured service components are running under the one existing current-user scheduled task/singleton supervisor; listener, dispatcher and completed worker phases advance. Only one authoritative scheduled-message producer remains (idea_service with atomic day_schedule); the old public research collector, model worker, exports and restored copies do not produce scheduled Telegram messages. Current task principal remains limited, with three bounded failure retries. Task launch is owned by Windows Task Scheduler, avoiding dependence on an interactive automation process lifetime.

Before restart, local HTTP was unavailable and work heartbeats were hours old. First final-restart probes of /healthz and / failed; /api/upgrade returned200. Later probes of all three paths returned200. At08:41:57 ET their measured durations were0.031s,0.016s and0.078s respectively. A further four /api/upgrade probes returned200 with a populated canonical market view, source age7.28–13.55s and response times0.031–0.250s. The cache explicitly grants no entry eligibility. A first request after its45s expiry correctly shows unavailable while background refresh runs; HTTP200 alone does not prove a populated current snapshot.

| Measure | Before receipt-observer delta | After delta, bounded sample |
|---|---:|---:|
| Completed cycles represented by monotonic phase sums | 37 | 12 |
| Median sum of instrumented phases | 6.797s | 9.141s |
| Phase sums above10s | 10 | 5 |
| Reliability phase maximum | 77.485s | 5.656s |
| Reliability phase overruns | 2 | 0 |

Phase sums exclude inter-phase overhead and are not the whole-cycle timer. The first initial deployed whole cycle was119.032s. The final restart's cold phase sum was88.687s, including32.657s idea scheduling and another legacy-analysis overrun; these failures remain preserved. Subsequent whole-cycle samples were11.796s (miss),5.015s (pass) and9.938s (pass), against the unchanged10s budget. The median did not improve in this small nonrandom before/after comparison. This is **not** a solved-deadlines verdict or a controlled causal experiment.

The warm synchronous receipt scan measured1.514s. The new single-flight observer runs outside the worker and reports CURRENT/available in the final sample. Its isolated blocked/over-budget/failure tests prove a poll need not wait for a scan; they do not establish an operating-system scheduling deadline. The earlier77.485s reliability phase has multiple operations, so receipt traversal is a measured blocking contributor, not a proven sole root cause. Indexed-query timing is synthetic and is separately labelled above.

Final sampled worker-lifetime database counters:0 busy retries,0 failed transactions, maximum transaction0.344s across1539 transactions. Previous lifetime counters and old SQLITE_BUSY failures remain retained; the samples cover different durations and do not prove contention eliminated. The host has2GB RAM and about110MiB free in the current sample. Resource pressure is measured; it is not asserted to explain every delay or previous process termination. Neural startup safely refuses on this host.

Read-only premarket market-data probing at08:20 ET obtained IEX200 with signed source age−0.480s; the strict nonnegative-age diagnostic and existing bounded-skew eligibility predicate remain separate. SIP and OPRA each returned403 entitlement rejection. Original source/receipt clocks are retained. No full regular session was observed for this release. Source-to-receipt delay, decision-time continuity, entry delivery latency and three-session operational acceptance remain prospective verification requirements, not passing unit tests.

**Local operation verdict: VERIFIED IN OPERATION for bounded service work and HTTP recovery; ten-second cycle performance is not consistently met.** Default presentation/lifecycle/dispatch paths are TESTED IN ISOLATION. Real option data, neural inference and strategy qualification remain blocked/pending as separately listed. No full-session readiness or continuous exit coverage is claimed.

**Retained primary-plan limitation:** current research control is UNRESOLVED because adequate observed coverage is missing. It is not silently closed at a clock deadline. New primary entries stay paused until supported resolution or an explicit documented administrative cancellation. Trend/status research continues independently. Inspect `/details`; `python -m ops.primary_admin IDEA_ID --reason "documented coverage limitation"` releases only a research control slot and records a separate cancellation. It never reports a personal sale, fills in missing prices or creates P&L. No such cancellation was performed during this release.

Configuration hashes,57 deployed source-file hashes, original historical-row prefixes and the issued October22 packet hash all matched. Private reported holdings and authenticated requests were reviewed locally; no private identifiers or ledgers are exported. Tests use isolated copies and fake transports. No development message was transmitted. Exact packet and rollback manifests remain private.
