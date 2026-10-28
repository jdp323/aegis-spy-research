# October28 deployed fix: dashboard during a valid event blackout

This follows the separately issued [opening source/calendar review](2026-10-28_opening-source-calendar-review.md). The actual current calendar is refreshed; the all-day October28 HIGH FOMC entry blackout remains in force.

## Changes

Fixed a real dashboard refresh crash in `core/readiness.py`. A valid HIGH calendar snapshot has `reason=None`. The engineering-blocker formatter concatenated that value to a string, raising TypeError. Using `dict.get(key, default)` did not supply a fallback because the key existed. The formatter now uses the existing default when the reason is null or empty, and preserves explicit reasons. The branch condition and every NEWS, data, option, risk, strategy and live gate are unchanged.

The failure was already visible before today's calendar publication: the API refresh retained TypeError and its last successful diagnostic snapshot was from the previous evening. A bounded query-only replay of the actual production builder reproduced the TypeError at `readiness.evaluate`, line21. This is a demonstrated explanation for that refresh failure; it is not the cause of worker deadline misses, source delays or every historical HTTP failure.

Added three regressions: valid HIGH calendar with a null reason; unavailable calendar with a null reason; preservation of an explicit reason. The first two failed before the change, while the explicit-reason case passed. The tests assert readable blocker text and refusal gates, including NEWS_READY=false and LIVE_SIGNAL_READY=false. No assertion or data tolerance was weakened.

## Verification

| Check | Result |
|---|---|
| New regressions before fix |3run:1passed,2TypeErrors; preserved |
| Targeted public suites |33passed,0failures/errors/skips;2.192s |
| Full isolated portable Python |770main+7backtesting+4monitoring, all passed |
| Explicit Node suite |61passed,0failures/errors/skips |
| Full combined result |**842passed**,0failures/errors/skips |
| Installed targeted suites |33passed,0failures/errors/skips;3.250s |
| Actual builder with candidate |Completed in6.328s in a query-only replay, market view present, HIGH news, NEWS_READY=false, LIVE_SIGNAL_READY=false |
| Actual post-restart API |Populated diagnostic market view, refreshed calendar verification, HIGH risk, all readiness gates false; no refresh TypeError |
| Source/config/history integrity |59reviewed source/test hashes, expected configuration including authorized calendar-only refresh, original private-history prefixes and issued October22 packet passed |

The full runner used a short isolated Windows workspace, stripped credentials, copied source, fake transports and blocked external networking. Python groups were discovered separately and Node used the explicit test-file list. No test sent a guest message or altered a production ledger. The two deployed files were byte-for-byte compared with the retained successful full-suite workspace before copying.

Exact commands from the public repository:

```powershell
python -X utf8 -m unittest tests.test_research_inputs tests.test_dashboard_snapshot_cache tests.test_combined_calendar tests.test_completion_endpoints
.\.venv\Scripts\python.exe -X utf8 -m ops.ci_tests
```

The installed targeted command was the same unittest selection through its existing runtime. The installed full suite was not repeated for this two-file shared-code delta; its earlier831-check result remains October27 as-of evidence. Current full portable coverage includes the same modified module/test plus additional portable setup checks. Passing tests are not live-session acceptance or evidence of option profitability. Previously issued command-role and whole-day simulation packets retain their original dates; they were not relabelled as rerun today.

## Deployment and before/after operation

Preserved recoverable source/test preimages and the prior integrity-helper source. Rechecked both production preimage hashes and the successful-suite hashes, then deployed only the formatter and tests. The private verifier recognizes this explicit delta without rewriting the original deployment manifest. There is no schema migration, historical rewrite, configuration/routing change, new dependency or credential collection.

Only the verified dashboard child was deliberately recycled through the existing supervisor. The worker, Telegram listener and dispatcher were left running; the stream continued its independent existing watchdog/reconnect behavior. No entire service group was stopped.

The first cold API probe timed out at3.031s. Three following requests returned200 while the empty cache refreshed. Four later probes all returned200 with a populated market view and no refresh error, taking1.094s,0.234s,0.125s and0.063s. One refresh still exceeded its5s budget at6.906s. The09:54:17 actual response showed current calendar verification13:32:27UTC, DATA_OK/HIGH news and all six readiness gates false. Those cold/over-budget results remain failures; this change fixes the TypeError, not overall latency.

The owner premarket received API acceptance09:15:21.980ET. The09:45 status received acceptance09:46:50.902ET, **110.902s late** against its slot; that timing failure is retained. Acceptance is not confirmation that a phone displayed the message. No retry or development demo was sent. Verification overlapped normal operation on the resource-limited host; these observations are not a controlled causal performance experiment.

At09:53:31 the worker had completed work, but its latest whole cycle was121.250s against10s. Counters showed29busy retries and4failedtransactions, maximum transaction12.281s. These are unresolved failures, not hidden by the dashboard recovery. Source-to-receipt delays and current-session continuity remain independent gates. Existing data failures and all original report artifacts remain preserved.

## Limitations

The dashboard crash fix is VERIFIED IN OPERATION for the observed HIGH-calendar case and TESTED IN ISOLATION across the named cases. Sustained HTTP/worker deadlines, decision-time source quality and complete live-session acceptance remain unverified or failing. The diagnostic cache grants no new-entry permission and explicitly abstains from cached forecasts. It cannot establish current liquidation values or a personal exit.

The earlier opening report documents resumed IEX authentication/messages, fresh official calendar inputs and persistent SIP/OPRA403 entitlement rejections. None of those proves consolidated stock/options readiness or genuine option profitability. No strategy has sufficient option-level promotion evidence. The existing primary-plan controls, manual order execution, private user-report separation and disabled live/execution flags are unchanged. Periodic assistant reviews are not continuous exit coverage.

## Setup impact

No setup/configuration/key change. After deploying the validated source, recycle the dashboard process under the existing single supervisor so its resident formatter loads the update; other components need not be stopped for this formatter-only change. A cold HTTP timeout and an overdue refresh must still be recorded. Use the current setup/start/status procedures and inspect snapshot metadata as well as HTTP200. [Setup](../../SETUP.md).

### Delivered hashes

| File | SHA-256 |
|---|---|
|core/readiness.py|015fcbb2061874482e32952aaad9f62feeba876fb6cf5e8da062ad5561d36e7b|
|tests/test_research_inputs.py|c70978b4e4ceacaadd3766cbd3455a01d0d76b44a782da4f2ed5f671922d828f|
