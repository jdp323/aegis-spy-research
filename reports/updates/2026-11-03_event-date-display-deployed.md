# November 3 — explicit event dates deployed; engineering failures retained

## Changes

The compact event line now says `today` for a same-day event and includes weekday, month, day and year for a future event. Previously a future release could be selected correctly but shown only with a clock time, making it appear to belong to the message's day. This presentation correction completes the saved candidate prepared during the opening review.

`monitoring/owner_messages.py::next_event` retains its existing event selection, ordering, invalid/unavailable-calendar handling, event-name sanitation and timezone conversion. It adds the date label before the existing time or all-day label. A synthetic future fixture now reads `Employment Situation · Fri Nov 06 2026 · 08:30 ET`; this is a display-test example, not a new event-calendar verification. Active date-only events retain priority and the all-day label; no release time is invented. Risk inputs and calendar provenance are not mutated.

Ten permanent fixtures cover future dates, same-day events, year changes, the ET/UTC day boundary, active and future all-day events, past timed-event exclusion, invalid/unavailable calendar evidence, input/risk immutability, and the actual eight-line premarket formatter. One existing exact-string all-day expectation was updated to include `today`; its selection, name sanitation and invalid-time assertions remain intact. No strategy, scoring, market-data timestamp, entry guard, option gate, schedule or notification-routing behavior changed.

## Verification

The opening candidate's failed-before result remains 7 failures out of 10, with zero errors or skips. The corrected candidate and existing owner/product/message groups passed 63 checks. That separate targeted run was preserved without another standalone rerun; the complete profiles below include those tests.

The first complete portable profile ran 953 checks: 952 passed and one existing exact-label assertion failed because it expected `FOMC fixture · all-day ET` while the intended result was `FOMC fixture · today · all-day ET`. That result and its logs were retained. The expectation was aligned with the intended dated presentation, without removing or relaxing the blackout/sanitation behavior. Complete final profiles then ran on the corrected fixtures:

| Profile | Main Python | Backtesting | Monitoring | Node | Total |
|---|---:|---:|---:|---:|---:|
| portable | 879 | 7 | 4 | 63 | 953 |
| installed | 869 | 7 | 4 | 62 | 942 |

Both final profiles have zero failures, errors and skips. Test runners used separate isolated source/data directories, fake transports and blocked external networking. No production ledger or real Telegram transport was used by the tests. Repeating the portable profile was justified by the retained complete-suite failure and the fixture correction; no further suite repetition followed the final passing profiles.

The deployed formatter and both test files exactly match the passing portable and installed copies. The formatter SHA-256 is `affae06bc462d059a20ba97b74e754e89456f9471303b2e983736ba292f4e166`. Another 336 operative code files were bound to the installed candidate before loading.

### Controlled loading and preserved evidence

Private reported exposure and pending authenticated requests were reviewed before loading. The scheduled owner recap had API acceptance at 16:15:06.512 ET, and the local session artifacts existed before the after-close change. No handset receipt or brokerage holding inference followed.

The existing current-user task's action, working directory and native Limited run level were verified and preserved. The existing supervisor was stopped after the delivery window; stop was confirmed at 2026-11-03T21:51:52.788081+00:00 UTC. Source-only replacement was followed by a start request for that same task at 2026-11-03T21:52:02.953615+00:00 UTC. Exact source/test preimages and task definition were retained for rollback. There was no database migration, restore or ledger rewind; existing WAL-aware backups were retained.

Verification confirmed 9 unchanged immutable event-table prefixes and 417 preserved issued artifacts, along with unchanged configuration, sharing and task definition. The known 14:00 slot's reservation row was also verified unchanged, with no new outbox or acceptance record and no replay.

Post-start verification required newer supervisor/listener/dispatcher timestamps and actual completed worker and independent-monitor work. The first health sample was 200; the later health sample was 200. The diagnostic endpoint was observed with a populated view after bounded checks; its cached/refreshed state remains separate from new-entry permission. Cold/failed samples remain in the retained evidence rather than being silently counted as recovery. This confirms bounded local loading/operation, not next-session timing or source reliability.

### Completed November 3 engineering evidence

The original native reports were copied as issued and hashed before testing. They were neither regenerated nor rewritten to reflect this formatter change. Their different conclusions apply to different populations:

| Population / measure | Retained result |
|---|---|
| Quarter-hour owner API acceptances | 24/25; the already reported 14:00 gap remains |
| Accepted within 30 seconds of slot | 19/25 |
| Scheduled strict underlying-analysis observations | 3/25; only 2 of these had owner API acceptance |
| Local monitor p95 | 14.156 seconds, above the one-second target |
| Failed monitor ticks | 200 |
| Maximum recorded monitor Store failure counter | 197; process-local counter, not the tick-failure population |
| Native completed monitor ticks | 2,857 |
| Retained minute coverage | 389/390, including 210 marked backfilled |
| Entry API acceptances | 0 |
| Genuine option performance | NOT MEASURED |

The native report's top-level coverage/composition status is PASS, while its `free_mode_engineering` result is FAIL and the master schedule/data target is false. The top-level coverage result does not establish delivery or live eligibility. Backfilled coverage cannot become original live continuity or quote freshness. Three composition-time strict observations are not sustained qualification, accepted ideas, option entitlement or trading edge; the missing 14:00 message is one of those three observations.

The issued first-hour result remains FAIL with 33 recorded sample minutes, rather than an invented complete first hour. Its original bytes and the earlier transcript audit and verification packet retain their as-of meaning. Five genuine engineering sessions remain an initial engineering window; no automatic strategy promotion follows.

## Limitations

This correction addresses misleading event-date display. It does not repair the separately documented reservation-to-outbox gap, SQLite contention, failed monitor ticks, worker/HTTP delays or stale IEX quotes. That handoff investigation remains the next separate reliability checkpoint. No old reservation was cleared, uncertain send blindly retried or expired opportunity replayed. All registered commands and the remaining recurring schedule remain intact.

No new changing macro/price claim or external entitlement probe was made. The operational calendar's freshness/provenance clocks were not renewed by display tests. Seven-day freshness, the owner expiry warning, date-only HIGH blackouts and unknown optional categories retain their existing treatment. News language remains descriptive context. Reddit/scanner/Questrade expansion remains frozen.

IEX remains one-exchange underlying research. SIP/OPRA, genuine option terms/BBO/Greeks/liquidity, option profitability and strategy validation remain unestablished. The incumbent stays frozen and both registered candidates remain shadow-only. No actual user trade, sale, settlement or exercise was inferred. All orders remain manual; live/execution flags and LIVE_SIGNAL_READY stay false, and BUY/SELL/TRADE_PROPOSAL kinds remain blocked.

## Setup impact

No new package, credential, account, subscription, hosting, model-inference expense, task privilege or permission is required. Cost remains $0 incremental. Load the reviewed source using the existing supervisor/task after reviewing private reports and pending requests and after scheduled delivery has completed. Preserve exact source preimages, task/configuration/sharing and append-only history; roll back source without rewinding databases. Then verify new completed-work timestamps, listener/dispatcher clocks, HTTP and a populated diagnostic view. No development guest message or manual Telegram test send is needed. Windows must stay awake/online; periodic assistant reviews are not continuous exit coverage.
