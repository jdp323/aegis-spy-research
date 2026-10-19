# Service recovery review — 2026-10-19

As-of observation window: 13:28–13:34 UTC (09:28–09:34 America/New_York). This is a bounded operational review, not a strategy validation or full-session certificate.

## Changes and reason

VERIFIED IN OPERATION: the existing local supervisor was started after all six managed component processes were found absent and the dashboard HTTP request failed. No production application code, freshness threshold, credentials or sharing preference was changed. No development broadcast or uncertain-receipt replay was performed.

VERIFIED IN OPERATION: by 13:33:16 UTC, all six component processes were present, dashboard HTTP returned 200, listener/dispatcher heartbeats were recent, and worker phases had completed. Process recovery does not establish analysis or option readiness.

## Limitations and observed evidence

VERIFIED IN OPERATION: the retained pre-restart heartbeats were around 05:58 UTC; the exact stop time and cause are UNKNOWN. These timestamps alone do not establish sleep, a crash, network loss or operator action.

VERIFIED IN OPERATION: worker cycles continued to miss their 10-second cycle budget. Observed durations included 82.219 seconds on initial recovery and 29.156 seconds on a later cycle. The initial reliability phase took 53.188 seconds; later reliability phases completed below 3 seconds, while one legacy-analysis phase took 15.062 seconds. SQLite metrics subsequently recorded bounded busy retries and one failure. These are observations, not proof of a single root cause. Further focused phase/transaction investigation remains required.

VERIFIED IN OPERATION: IEX reconnected and market messages resumed, but eligibility remained intermittent/unavailable. A coherent read-only snapshot evaluated after its reads at 13:34:07.900 UTC found quote source 13:33:33.108 UTC and receipt 13:33:48.106 UTC: source age 34.792 seconds, receipt age 19.794 seconds, predicate SOURCE_TOO_OLD. The five-second source-age gate was preserved. A connection and a capture-time DATA_OK label do not make that quote fresh. Earlier IEX disconnects were also observed; their precise cause was not established.

BLOCKED: full-session continuity and sustained fresh underlying operation have not been established by this short observation. It was only minutes after the regular open; history/backfill is not contemporaneous live proof.

BLOCKED: SIP returned a generic permission error; OPRA had no contract subscriptions. Neither genuine option-quote access nor option profitability was established. LIVE_SIGNAL_READY and execution remain false. IEX remains single-exchange underlying research only.

## Verification and publication

Read-only checks: python -m ops.supervisor status; coherent SQLite state snapshot with clock taken after reads; worker completed-phase and database telemetry inspection. Safe aggregate observations only are published; private runtime records remain local. No broad suite rerun was warranted for this operational restart and report-only change.

The public source release retains its separately recorded 748 passing tests, 540 command/role cases and 24 schedule scenarios. GitHub Actions for source commit 958c863d50338d982d1dd9ec02ad4fcefb0d7a62 and documentation commit f52ef5b110614234a0c5da740ae0c6f3922d61e6 both completed SUCCESS. Passing isolated tests do not resolve the live observations above.

## Remaining action and setup impact

No new installation step. Use SETUP.md and OPERATIONS.md. Keep the host awake and online; inspect completed-cycle telemetry and exact eligibility predicates. Investigate persistent latency/deadline misses before calling live analysis ready. Preserve strict calendar, continuity and option gates. All orders remain manual and strategies unvalidated.
