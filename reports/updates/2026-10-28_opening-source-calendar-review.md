# October28 opening review and official calendar refresh

Observed09:28–09:37 ET. This review separates service transport, original market timestamps and entry permission. No strategy or option profitability claim is made.

## Changes

Completed one bounded source-quality improvement: refreshed the required Fed/BLS/BEA calendar using newly retrieved official inputs, verified the candidate in an isolated directory, preserved the previous calendar and deployed only the validated calendar data atomically. Production Python/Node source, strategy parameters, sharing preferences, credential configuration and strict gates are unchanged. No service restart or development Telegram message was performed.

The previous actual verification was October22 05:44:45UTC, expiring October29. The new actual verification is **October28 13:32:27UTC (09:32:27 ET)**, the earliest of the newly received source artifacts. Its unchanged seven-day rule expires **November4 13:32:27UTC (08:32:27 EST)**. The coverage boundary remains December5 04:59:59UTC; coverage is not a freshness extension. Today's October28 date-only HIGH FOMC event has the identical event identity, unavailable decision time and all-day blackout boundaries. Refreshing the file did not allow entries through that blackout.

BLS direct HTML and official ICS requests each returned403. Those failures remain preserved. The existing official-reader parser accepted a newly retrieved BLS annual-page response containing all future relevant rows through December and the explicit Eastern Time note; its retained source lines398–447 were checked for completeness. No dates or times were reconstructed from memory. Fed and BEA were fetched directly. Optional event categories and the optional FRED supplement were not expanded or represented as complete.

| Official source | Actual received UTC | Method | SHA-256 |
|---|---|---|---|
| [Fed](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) |13:34:59.940920|Direct official HTTP|a9d55e6f6f34dbb911f8c347117d02b6433a8cbb7c93735320ad92babd7d34ee|
| [BLS](https://www.bls.gov/schedule/2026/home.htm) |13:32:27|Official page reader|6ccba5638f49b2ad78db38385487ce91802746563867c9e5db0fe98dbb3e1245|
| [BEA](https://www.bea.gov/news/schedule) |13:35:00.292779|Direct official HTTP|3b5cded2cdc34c1445a65da5eb4cbaa0ce66fd5f2411402104db8a886cd1fcf2|

Calendar SHA-256 changed from `efd9b23eda98478bb2e0786e8f069d701a6e5f48c98c4500179c137f6cb6592f` to `1500d7ba6c4865dcf31b0f48434a0a01b1ade4eaee6d0d2462346a9558c045bc`. Raw source bodies, direct failures, old calendar, isolated manifest and deployment evidence remain private. No raw runtime database or credential is published. The private integrity verifier now explicitly recognizes this documented calendar-only delta; its original deployment manifest is unchanged.

## Operation and data access

Today's premarket received owner Telegram API acceptance at **09:15:21.980 ET**, with one attempt. The09:20 owner self-check is also accepted. No claim of phone delivery follows from those receipts, and no uncertain message was resent. At09:28–09:29, all seven local components were present, listener/dispatcher heartbeats were recent and the worker had recent completed phases. Private user-reported exposure and authenticated requests were reviewed without exporting personal records or inferring broker holdings, closure or settlement.

IEX production authentication and market messages have resumed since last night's406 diagnostic. The recent65-minute stream evidence contains four successful authentications and subscriptions, with subsequent SPY observations. The current observations do not establish who held the earlier connection or prove the issue cannot recur. No key rotation, purchase, permission change or manual restart was used in this review. The earlier request to investigate a competing stream is conditional on a renewed connection-limit failure; do not disrupt another client solely on the old warning.

That recovery is **transport only**. At09:29:27 the stored IEX bid/ask was474.877s old despite a recent connection state. At09:30:35, original source13:30:01.642829UTC and receipt13:30:14.158030UTC showed **12.515201s source-to-receipt delay**; at evaluation the source and receipt ages were34.208s and21.693s. The strict source-age predicate rejected it. These are measured examples, not proof of the sole delay cause. A heartbeat, connection or new trade does not refresh old bid/ask.

A separate09:30 read-only REST probe returned IEX200 with signed source age−0.403s. Its simple nonnegative-age diagnostic reports false; the application's existing bounded-skew predicate remains separate and unchanged. SIP and OPRA each still returned403 entitlement rejection. IEX remains single-exchange underlying research and cannot satisfy consolidated/options gates.

HTTP health/root/API returned200; the first API call correctly withheld an expired diagnostic snapshot while refreshing. One saved worker cycle took6.313s, and the later09:29 cycle took67.953s against the unchanged10s budget. New-lifetime counters2busy retries/1failedtransaction remain failures. Historical contention and the session's decision-time bar requirements are not solved by this review. The first15-minute status was still future during the initial snapshot; no missing regular-session bars or full trend pass was invented before the session began.

## Verification

- Existing targeted calendar suites: `python -X utf8 -m unittest tests.test_combined_calendar tests.test_paper_upgrade_b` — **7 tests passed**,0failures/errors/skips,0.776s. These exercise blackout boundaries, DST, source validation, expiry, retained failure evidence and last-good preservation using isolated fixtures.
- **9 real-source candidate checks passed:** production untouched during construction; required future categories; identical today's date-only blackout; current HIGH risk; expiry fails closed; two future BLS CPI/JOBS/PPI rows each; correct ET/DST conversions; actual newly retrieved source clocks; artifact hash matches.
- The refreshed candidate passed the existing validator, was copied atomically after rechecking its preimage hash, and the deployed hash matches exactly. Last-good preimage, verifier preimage and all source artifacts are recoverable. The7-day age limit was neither widened nor renewed by editing old timestamps.
- Existing read-only integrity verification passed57 production source hashes, all expected configuration hashes including the separately authorized calendar delta, original private-history prefixes and the unchanged issued October22 packet. The strategy/live configuration hash remains unchanged.
- The most recent full source release remains839portable/831installed checks with zero final failures/errors/skips; those are October27 as-of results, **not rerun or relabelled as current live acceptance**. No code change warranted another broad suite during market operation. Earlier failures remain in the original reports.

## Limitations

The production calendar file is refreshed; an older cached `news` state record can retain its original verification until the application rereads it. That old cache is not retimed. The actual NewsProvider and entry-publication paths read the validated calendar file. Today's HIGH blackout remains mandatory. Unexpected/optional events are unknown unless explicitly covered; no FOMC statement time was guessed.

Current-session continuity, fresh quote/receipt/heartbeat checks, plan controls and real option eligibility remain independent. No full live-session readiness, guaranteed alert timing, genuine option premium, option-paper profit or strategy qualification is established. Reddit remains unconfigured. SIP/OPRA entitlement, genuine point-in-time option data and other previously documented external requirements remain unresolved. Periodic assistant review does not provide continuous exit coverage.

## Setup impact

No dependencies, keys, subscriptions, privileges, sharing preferences or service commands changed. SETUP adds the official-source fallback/provenance rule and the distinction between reconnect recovery and analysis readiness. Run the existing `python -m news.calendar_updater` for supported direct refresh; if sources fail, preserve last-good data and retain those failures. Use an authorized official-reader/import workflow only with actual source text, URL/hash, received time and complete required future rows; a cached file cannot acquire a new verification date. [Setup](../../SETUP.md).
