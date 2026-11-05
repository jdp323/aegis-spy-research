# November 5 daily status-timing target failed

## Changes and reason

The first three completed owner status slots already contain two late API acceptances. Even if every remaining status is timely, at most 23/25 (92%) can meet the 30-second threshold. The 95% target requires at least 24/25. This is the first documented timing-target failure for November 5, separate from retained earlier dates. The full remaining schedule still applies.

This documentation update preserves original receipt and event clock evidence. It changes no operative source, data gate, schema, task or service. The unfinished private handoff candidate remains undeployed.

## Verification

| Scheduled slot ET | Evaluation offset | Owner journal created offset | API acceptance offset | Journal to acceptance |
|---|---:|---:|---:|---:|
| 09:45 | 26.128s | 29.801s | 32.281s | 2.480s |
| 10:00 | 1.668s | 5.703s | 6.419s | 0.716s |
| 10:15 | 27.134s | 41.393s | 43.317s | 1.924s |

All three were API-accepted once: 09:45 at 09:45:32.281 ET, 10:00 at 10:00:06.419 ET and 10:15 at 10:15:43.317 ET. Only 10:00 met 30 seconds. Acceptance is not handset delivery. No missing or uncertain result was found in this completed three-slot cohort; no resend occurred.

The retained 10:30 followup was sampled at 10:30:19.801 ET and had no receipt yet. Its current window was still open; it was pending at that sample, not declared lost, rejected or expired. Later state must be assessed separately without retiming or replay.

Phase offsets do not prove a single cause. Journal-to-acceptance includes local notifier work and transport; it is not a pure network round-trip measurement. Original evaluation, source, receipt, journal and acceptance clocks are retained.

The initial bounded review found all seven service processes present, but the completed worker phase was about 31 seconds old and the preceding whole cycle was 100.781 seconds against a 10-second budget. That maintenance Store reported 260 busy retries and 30 failures; these process-local counters are not a count of all monitor ticks. Initial healthz timed out; two later probes returned 200. At that later sample, worker completion had advanced while fast-path completion had not advanced past the initial review. PIDs, a heartbeat or HTTP 200 do not establish sustained healthy operation.

The selected IEX quote was 24.646 seconds old at source and 10.309 seconds old at receipt, with the original 14.337-second source-to-receipt interval retained. It failed SOURCE_TOO_OLD. An AUTHENTICATED control message is separate from current BBO freshness, bar continuity, sustained recovery and entitlement. No additional provider/entitlement probe or timestamp repair was attempted. Independent Fed/BLS/BEA/CNBC query metadata was DATA_OK; this is separate from quote freshness and a complete upcoming-event calendar. No changing macroeconomic or market-direction claim is made here.

Private reported exposure and pending authenticated requests were reviewed locally without brokerage access, identity publication or inference of sale, exercise, settlement or closure. No first-hour report is claimed complete by this early review.

## Saved implementation state

The private prepared-event candidate has 70 distinct isolated scoped cases on retained versions. Atomic immutable persistence, local file publication, child-process exits, recipient-local notifier boundaries, current-slot enumeration and the preparation-before-claim coordinator have scoped evidence. Actual idea_service scheduled-path wiring, complete broadcast/dispatcher and failure-audit integration, required complete profiles, schema migration/backup/rollback and controlled production loading remain outstanding. No scoped or full suite was repeated for this incident review, and no candidate code was deployed.

## Limitations

This is a failed daily timing target, not proof of profitability, strategy edge or option readiness. The November 2–6 period remains an initial engineering observation window. Earlier failures and issued reports remain as-of evidence; this partial cohort is not a full November 5 session report.

IEX remains single-exchange underlying research. All existing original quote/receipt age, skew, heartbeat, 31 completed current-session minute bars, calendar and risk gates remain unchanged. SIP/OPRA and genuine option terms/BBO/Greeks/liquidity remain unestablished; no indicative premium or option-dollar outcome is substituted. The frozen incumbent and two shadow-only candidates remain unchanged. Orders remain manual; live/execution flags and LIVE_SIGNAL_READY stay false, and BUY/SELL/TRADE_PROPOSAL kinds stay blocked. Periodic assistant checks are not continuous exit coverage.

## Setup impact

None. Documentation/evidence only; no install, dependency, credential, configuration, sharing, task, operational procedure or service restart change. No account/order/fund/permission/paid action, actual test message, guest development message, uncertain resend or expired-slot replay. No private journal, outbox, identifier, raw cache or machine path is published.
