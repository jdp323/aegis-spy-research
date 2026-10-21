# Opening-session reliability check — October 21, 2026

## Changes

Recorded the first bounded regular-session operational review after the Telegram-experience deployment. This is a measured follow-up to the earlier premarket report, not a new code release or a claim of full live-session readiness. No production code, configuration, permissions, sharing, ledgers or freshness gates were changed. Earlier reports and failed observations remain as-of artifacts.

## Verification

At 09:32 ET all six supervised components were running with zero supervisor restarts. Dashboard health/root/upgrade/status returned HTTP 200 in 234/1015/469/344 ms. Worker completion was advancing; the sampled completed cycle took 26.109 seconds against its 10-second budget. Later at 09:34 ET the latest completed cycle was 9.125 seconds, within budget. These are variable measured samples, not sustained performance proof.

Eight opening samples for each named worker phase showed one legacy-analysis overrun (maximum 32.422 seconds) and two underlying-paper-review overruns (maximum 17.172 seconds). Idea scheduling averaged 3.932 seconds and peaked at 6.000 seconds. Capture/session checks averaged 1.943 seconds and peaked at 4.484 seconds. Other sampled phases did not exceed their individual budgets. The current process had five bounded SQLITE_BUSY retries, zero recorded database failures and a maximum measured transaction of 1.390 seconds over 17,501 transactions. The earlier premarket zero-retry sample therefore does not prove contention was eliminated. Phase duration does not establish whether a particular delay came from locks, CPU, disk, history size or networking. No single root cause is declared.

At 09:32:04 ET a genuine IEX quote had source age 3.904590 seconds, receipt age 3.457732 seconds and source/receipt skew -0.446858 seconds; the quote diagnostic reported no failed predicate. Heartbeat age was 3.457732 seconds. This is one successful quote observation, not a sustained freshness result or consolidated feed. Full underlying analysis correctly remained blocked by BAR_TAIL_SHORT while the opening history formed. Only one of the first two completed minute slots was then present; the second was checked just four seconds after its close. Its absence at that instant does not establish a permanent lost bar, and later backfill would not prove earlier decision-time availability. The daily prospective verifier starts at 09:35 ET.

Pending authenticated requests and private user-reported exposure were reviewed read-only. Private ledger contents are not published; no broker verification, expiry settlement, exercise or closure was inferred. No development message was sent, no uncertain receipt replayed and no tests touched production data. Existing source suites (780 public and 772 installed checks) remain dated prior evidence; they were not needlessly rerun for this read-only operational review.

## Limitations

The first real-session observations show that worker deadline misses remain possible. Local processes and HTTP are healthy, but reliable opening-session cadence is not established. Underlying history is still warming; stock/option/live/strategy readiness remain separate. One quote does not qualify a strategy or an option contract. The appropriate next check is the existing prospective verifier plus continued phase timings; a targeted performance fix requires a reproduced cause, not wider budgets or freshness limits. No new owner account action is required by this review.

## Setup impact

None. Keep existing configuration and normal services running. Use the existing read-only supervisor status, /details and daily live-verification/session reports. Keep the PC awake and online. Do not restart during healthy progress merely because one cycle exceeded budget. No subscription, credential or permission change was made.
