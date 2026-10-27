# October27 first-hour service and source-quality review

## Changes

Bounded read-only operational review; no production source, configuration, threshold, schedule, permission or sharing change and no service restart. Original failures, source/receipt timestamps, native verification report and prior issued packet are preserved. This review adds an explicit signed-age breakdown so the native nonnegative-age counter is not misrepresented as all production quote predicates. No broad software suite or development Telegram broadcast was repeated.

## Verification

Observed10:31–10:35 ET, October27, during the verified regular session. All seven service components report running. Listener/dispatcher heartbeats advance, dispatcher has no pending events, and /healthz, / and /api/upgrade return200. A first request after a long idle correctly returns an unavailable diagnostic snapshot while refreshing; HTTP200 does not mean its data were current. Private reported exposure and authenticated requests were reviewed locally without broker access; no private data are published.

Today's real09:15 premarket received owner Telegram API acceptance at09:15:25.651 ET. The owner separately confirmed seeing all five earlier fictional demo messages; that confirmation is recorded append-only and does not confirm the normal premarket/status messages on the phone. No message was blindly resent.

| Scheduled silent status | Owner API acceptance ET | Seconds after slot | Within30s |
|---|---|---:|---|
|09:45|09:45:51.057|51.057|No|
|10:00|10:00:43.500|43.500|No|
|10:15|10:15:13.044|13.044|Yes|
|10:30|10:30:11.971|11.971|Yes|

All four have retained composition records marked VALID_UNDERLYING by their applicable rules. The09:45/10:00 modes are explicitly limited early-session reads, not an assertion of31 genuine completed current-session minutes. The later modes remain subject to the full continuity predicates. Recorded IEX source ages at composition were0.454,1.425,2.274 and0.509 seconds; corresponding heartbeat ages were0.653,1.587,2.431 and0.480 seconds. Eligibility at composition is separate from delivery latency and option/entry permission.

The four-slot on-time count is2/4. Because two normal-day slots already exceeded30s, the predeclared at-least24-of25 timing target cannot be reached today even if every remaining slot is on time. This does not justify deleting slots, stretching the deadline or changing the silent15-minute cadence.

At10:33:30 ET, an independently sampled saved IEX BBO had signed source age0.540s, receipt age0.028s and source-to-receipt delay0.512s, with the strict quote diagnostic passing. There were63 stored completed current-session minute records through10:32 with no stored gap, one explicitly REST-backfilled row. Retained eventual coverage is not proof all records were available at the original decision time. Saved10:30 market view showed a completed-bar UP description and WAIT because an existing primary plan is active; this is descriptive research, not a calibrated forecast or an option recommendation. IEX remains one-exchange proxy evidence.

### Material reliability failures

The10:31 sample recorded55 SQLite busy retries and3 failed transactions. By the10:32:42 failed-cycle record, counters were64 retries and5 failed transactions (SQLITE_BUSY); maximum recorded transaction duration4.0s. These are worker-lifetime counters since the morning restart, not five verified missed Telegram messages. Whole-cycle10:31 duration34.250s exceeded the unchanged10s budget; subsequent failed-cycle records and a12.188s idea-scheduling phase remain retained. Fresh stream observations and responsive HTTP do not repair these failures or prove timely position reviews.

The stream service had one recorded supervisor restart. During13:30–14:35UTC, retained IEX rejection records included10,562 duplicate quote-source rejections,134 duplicate trade-source rejections,6,147 generic quote-quality rejections and15 other records without those detail fields. Duplicate/out-of-order rejection preserves source watermarks. Per-event diagnostic writes are a candidate contributor to contention, not a proven sole root cause. Generic quality records do not establish whether spread, age, skew or another field failed. No rejection was reclassified, discarded or accepted to reduce these counts. A future bounded reliability change should measure writer/transaction phases and preserve rejection counts/provenance before altering diagnostic batching.

### Native first-hour result and exact predicates

The native09:35–10:34 first-hour artifact remains FAIL with59 minute samples;10:32 is missing. Its nonnegative-source-age-within-five count is14/59 (23.73%).44 samples have small negative source ages within the existing two-second skew bound; one lacks an age. These44 are not automatically stale or invalid under every production predicate. The legacy evaluator recorded LIVE_TREND on32 samples:25 from the bounded-negative bucket and7 from the nonnegative bucket. The original report and stricter nonnegative diagnostic remain unchanged; neither statistic alone establishes the full current quote/receipt/heartbeat/continuity/calendar/option gate set.

The native report's post-warmup tail counter is32/33 and its evaluator p95 is842.64ms. That evaluator timer is not the whole worker cycle or end-to-end dispatch latency.52 samples contain independently labelled public observations whose delay remains unverified; those observations never satisfy the real-time gates.

Read-only NTP measurement at10:20:53 ET recorded approximately+0.210s offset without changing the system clock. This is a measured instant, not proof of permanent OS synchronization or an explanation of the previous clock jumps. The most recent direct SIP/OPRA probes earlier today remain403 entitlement rejections; no access upgrade, option contract or option-profitability evidence is inferred.

## Limitations

Local services and scheduled delivery progress are observed, while today's timing acceptance target has failed and database contention remains unresolved. Current valid IEX samples do not establish sustained live readiness. An unresolved primary research plan still prevents competing new primary entries; no administrative cancellation, personal fill, sale, exercise or settlement was inferred. Genuine option access, after-cost strategy evidence and neural hardware/inference remain separately blocked/pending. Periodic assistant review is not continuous exit monitoring.

## Setup impact

None. No credentials, subscriptions, external permissions, dependencies, runtime flags, alert categories or sharing preferences changed. No tests touched production ledgers and no raw licensed data, receipt identities or private reports are uploaded. Existing owner-only outage/delivery routing and uncertain-no-resend behavior remain. Original successful software suites retain their isolated meaning; they are not rerun or presented as proof this live session passed. See [current implementation](2026-10-27_master-implementation.md) and [operations](../OPERATIONS_MASTER.md).
