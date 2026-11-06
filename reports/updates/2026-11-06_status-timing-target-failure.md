# November 6 daily status-timing target failed

## Changes and reason

Two of the first four completed owner status slots were API-accepted more than 30 seconds late. Even if every remaining slot is timely, at most 23/25 (92%) can meet the daily threshold. The 95% target requires at least 24/25. This is the first documented November 6 daily timing-target failure, separate from previous dates.

The full remaining schedule remains required. This documentation review preserves original clocks and adds no runtime change, source-gate relaxation, service restart or replay.

## Verification

| Slot ET | Evaluation offset | Owner journal created offset | API acceptance offset | Journal to acceptance |
|---|---:|---:|---:|---:|
| 09:45 | 6.605s | 12.758s | 15.267s | 2.509s |
| 10:00 | 23.073s | 36.836s | 41.228s | 4.392s |
| 10:15 | 2.335s | 15.736s | 21.758s | 6.022s |
| 10:30 | 4.044s | 28.704s | 32.521s | 3.817s |

All four were API-accepted once: 09:45 at 09:45:15.267 ET, 10:00 at 10:00:41.228 ET, 10:15 at 10:15:21.758 ET and 10:30 at 10:30:32.521 ET. Two met the 30-second target. There was no missing or uncertain result in this completed four-slot owner cohort. API acceptance is not handset delivery.

The first 10:30 followup at 10:30:20.401 ET was still pending. The subsequent original journal records acceptance at +32.521 seconds, one attempt. It was not declared lost, rejected or expired, and no manual resend was attempted. Original evaluation/source/receipt/journal/acceptance timestamps are retained. Journal-to-acceptance includes local notifier work and transport, not pure network round-trip time or a proved single cause.

The initial bounded service review found all seven processes present, with completed worker work about 39 seconds old and a preceding 202.391-second whole cycle against a 10-second budget. The maintenance Store reported 422 busy retries and 52 failures; these are process-local counters, not all failed monitor ticks. Initial healthz and two immediate followup probes timed out, while completed worker/independent-monitor timestamps advanced. No blanket healthy/recovered conclusion follows from PIDs, heartbeats or authentication.

The selected original IEX quote was 37.504 seconds old at source and 23.467 seconds old at receipt; the source-to-receipt interval was 14.037 seconds. It failed SOURCE_TOO_OLD. An empty recent control-event tail is not proof that earlier refusals/outages are resolved. No new entitlement probe, provider workaround, source retime or historical-data promotion occurred. Independent Fed/BLS/BEA/CNBC query metadata was DATA_OK; that is separate from executable BBO freshness, entitlement and complete future-event coverage. No changing macroeconomic or directional market claim is made here, and no completed first-hour result is claimed by this early review.

Private reported exposure and pending authenticated requests were reviewed locally without brokerage access or published identities. Fill reports are not broker verification; sale, closure, settlement and exercise are never inferred.

## Unfinished implementation state

The saved private handoff candidate retains 91 distinct isolated scoped cases. An explicit opt-in actual-tick bridge now has scoped fake-context/gate evidence, but the default private and production scheduled paths still use legacy dispatch until a real structured status gate and operational factory are implemented and validated. No fixture gate is installed operationally.

Actual structured publication semantics, worker injection, refusal/failure auditing, complete broadcast/dispatcher integration, explicit schema migration/backups/rollback and full profiles remain outstanding. The earlier timezone-string fixture failure and its corrected aware-instant assertion are retained; no implementation clock was changed by that correction. No passing implementation tests or broad suites were repeated for this incident review. A separate two-context offline snapshot diagnostic did not reproduce its hypothesized identity difference; it is not a verified defect or repair result and adds no passing implementation case.

## Limitations

This is a failed daily timing target, not a complete November 6 session report or evidence of profitability. November 2–6 remains an initial engineering observation window; earlier issued failures and reports retain their as-of meaning. No single database, host, provider, network or transport cause is proved by these samples.

IEX remains single-exchange underlying research. Original quote/receipt age, skew, heartbeat, continuity, 31 contiguous completed current-session minute bars, calendar and risk gates remain unchanged. SIP/OPRA, genuine option terms/BBO/Greeks/liquidity and strategy validation remain unestablished. No indicative premium, fixed-delta substitute or option-dollar outcome is introduced. The incumbent remains frozen and two registered candidates remain shadow-only. Orders remain manual; live/execution flags and LIVE_SIGNAL_READY stay false, with BUY/SELL/TRADE_PROPOSAL kinds blocked. Assistant checks are not continuous exit coverage.

## Setup impact

None. Documentation/evidence only: no operative or candidate source, schema, configuration, sharing, task, dependency, credential, operational procedure or service restart change. No actual test send, guest development message, owner confirmation, uncertain or expired replay, account/order/fund/permission/paid action. Original private evidence is retained; raw journals, outboxes, caches, holdings, identifiers and machine paths are not published.
