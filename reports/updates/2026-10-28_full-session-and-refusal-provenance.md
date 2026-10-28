# October28 full-session results and deployed refusal diagnostics

The real session completed. All 25 scheduled trend updates, the 09:15 premarket and 16:15 recap received owner Telegram API acceptance. **Only 9/25 statuses met the 30s timing target, and 0/25 passed their applicable underlying-data gates. Overall live-session acceptance FAILED.** Calendar/risk refusal is classified separately; today's HIGH event does not excuse missing fresh-price evidence. Telegram acceptance is not confirmation that a phone displayed a message.

## Changes

Completed one bounded source-quality improvement in [data/stream.py](../../data/stream.py): retain the provider's numeric refusal code with a fixed GREETING, AUTHENTICATION or STREAM stage in the existing append-only PROVIDER_REJECTION event. Previously, authentication responses became a generic PermissionError and discarded their code. Stream-stage errors retained a code but no stage.

The new recorder writes only an actual integer code, or null for an unknown/non-integer code, plus the fixed stage. A Boolean is not reported as numeric 1. Raw provider text, auth frames, keys and exception messages are excluded. An explicit greeting refusal closes the socket before credentials are sent. Recognized refusals use the existing permission cooldown; feed selection, retry formula, network deadlines, quote validation and all entry/risk/calendar/option gates remain unchanged. No lower-quality fallback feed was introduced.

Actual post-restart service events at17:09:20ET recorded **IEX 406/AUTHENTICATION** and **SIP 409/AUTHENTICATION**. Alpaca defines 406 as a connection limit and 409 as insufficient subscription. The stage records where the response arrived; AUTHENTICATION does not by itself mean bad credentials. [Official protocol reference](https://docs.alpaca.markets/us/docs/streaming-market-data).

OPRA remained idle without contract subscriptions. Its earlier authorized market-data REST 403 evidence remains as-of evidence; no new OPRA streaming entitlement or real option quote was established. This change improves diagnosis and provenance. It does not clear the IEX connection holder, establish SIP access or solve processing delays.

## Full-session evidence

| Result | Actual evidence and limit |
|---|---|
| Scheduled owner statuses |25/25 API accepted;9/25 within30s; timing target failed |
| Underlying eligibility |0/25; fresh-price failures recorded separately from HIGH-calendar refusal |
| New accepted qualifying primary entries |0; latency percentile unavailable/NO_SAMPLE, not a passing result |
| Premarket acceptance |09:15:21.980ET |
| Recap acceptance |16:15:16.390ET |
| Issued16:20 coverage report |PASS for its95% coverage/status-presence criteria:387 genuine minutes,380 REST-origin rows,2 provider-confirmed no-print slots and1unresolved minute, out of 390 |
| Native opening verifier |FAIL;48 observations,1/48 meeting its nonnegative<=5s quote-age diagnostic,0 qualifying 31-bar tails;43 public crosschecks have unverified delay |

A confirmed no-print slot is continuity metadata, never a candle for indicators, volume or fills. Later historical/REST repair does not prove the original decision-time availability of a quote or bar. Coverage PASS is therefore compatible with live-session FAIL. The report's age diagnostic is separate from the existing signed-skew predicate; its percentages count observations, not future-move probabilities. Native evaluator latency is not whole-worker cycle latency.

The last stored IEX BBO in the session evidence was sourced09:41:08.002745ET and received09:41:22.906882ET. Those original clocks were retained and old prices were rejected. The 14.904s clock interval is observed evidence, not proof of a network-only or single root cause. Reconnect/authentication events and fresh process heartbeats cannot refresh that bid/ask. Descriptive completed-bar views remained separate from abstaining forward hypotheses and WAIT entry state.

All four issued October28 session/verification documents and the earlier issued October22 packet remain unchanged. No personal fill, sale, exercise, expiry settlement or profitable option outcome was inferred. The existing unresolved primary research control was not silently closed. Private reports and authenticated requests were reviewed locally; personal records were not exported. Today's previously verified [Fed policy context](2026-10-28_fomc-policy-context.md) remains a source fact, not a demonstrated SPY reaction or forecast.

## Verification

Five new [transport regressions](../../tests/test_stream_refusal_provenance.py) failed before the fix. They now pass: greeting refusal without sending credentials; auth 406 without subscribing; binary OPRA 409 refusal; stream-stage 405; and Boolean code treated as unknown. They exercise the actual stream run loop with synthetic sockets, preserved permission cooldown, no market-readiness promotion and no secret/provider-text leakage.

| Current check | Result |
|---|---|
| Related stream discovery |34 passed, 0 failures/errors/skips |
| Full portable Python |775 main + 7 backtesting + 4 monitoring passed |
| Explicit portable Node |61 passed |
| Full portable total |**847 passed**,0 failures/errors/skips |
| Full installed Python |768 main + 7 backtesting + 4 monitoring passed |
| Explicit installed Node |60 passed |
| Full installed total |**839 passed**,0 failures/errors/skips |
| Backup/restore |6 selected SQLite state/telemetry/idea/reported-position backups, including committed WAL, passed full integrity and isolated restore/count checks |
| Post-deployment integrity |61 reviewed source/test hashes, expected configuration, original private-history prefixes and old verification packet passed |

The portable suite includes additional packaging/setup cases; the difference is not skipped tests. Both runners used short isolated Windows roots, fake transports and stripped credentials. No production database or guest transport was used by tests. Both deployed files match the corresponding retained passing suite copies byte-for-byte.

Exact test commands:

```powershell
python -X utf8 -m unittest discover -s tests -t tests -p test_*stream*.py
.\.venv\Scripts\python.exe -X utf8 -m ops.ci_tests
python -X utf8 -m ops.test_runner
```

The last command uses the installed runtime; its JSON successful field was checked explicitly. The five failing-before cases remain retained. An initial targeted module-name invocation ran 10 passing cases but had one sibling-import loader error; corrected discovery uses the same top-level configuration as the full runner. No assertion was loosened. Existing detailed command-role, full-day transcript and research reproduction packets keep their original as-of dates; unchanged default messages were not newly broadcast as a demo.

## Backup and deployment

The initial preimage check stopped on byte differences that inspection proved were existing mixed LF/CRLF formatting. Both raw preimages were preserved; normalized source equality and strict production-preimage hashes were checked before deployment. No owner logic was overwritten.

The live SQLite backup exceeded its 45s copy budget. After the session jobs and fresh private-position/request review, the existing group was deliberately paused around16:45ET. A second 45s attempt also timed out on the 1.38GB observability database. Both incomplete attempts remain failures and are excluded from the six verified backups. A size-aware 300s offline copy budget was then used, with unchanged integrity/restore checks. That database's complete backup, two integrity checks and restore verification took 586.828s; this is not a claim that the copy itself took that time. Existing issued artifacts and source/configuration preimages are recoverable.

After both full suites passed, the same limited Windows scheduled task was started at approximately17:09ET. No new installation, supervisor, privilege or sharing configuration was introduced. All seven components, listener/dispatcher heartbeats, new completed work and HTTP response were observed. The first new sampled whole cycle was 6.375s, with 0 new-process busy retries/failures over 268 transactions. These reset counters do not erase the pre-stop 102 busy retries/14 failed transactions or prove contention fixed. The pre-stop sampled cycle was 85.656s and maximum transaction 21.734s; samples cover different workloads and are not a causal performance comparison.

Four later API probes returned 200 with a populated diagnostic view and no refresh TypeError, taking 0.297s, 0.031s, 0.047s and 0.219s. A refresh still exceeded its 5s budget at 6.375s. Cold/expired snapshots were explicitly withheld. This is bounded after-hours operation, not a new passing live session. No backup was restored over a live database; no historical record, fill ledger or uncertain receipt was rewritten or resent.

## Limitations and verdicts

| Conclusion | Status |
|---|---|
| Targeted software implementation |Implemented: safe refusal provenance and early greeting refusal; broader latency work remains |
| Automated verification |TESTED IN ISOLATION:847 portable/839 installed, plus 34 targeted |
| Local service operation |VERIFIED IN OPERATION for bounded new work, HTTP and actual refusal telemetry |
| Live-session data operation |FAILED current-day acceptance; new deployment has no subsequent live-session proof |
| Genuine option research data |BLOCKED; no new real chain/BBO/Greek or historical option evidence |
| Strategy evidence |Insufficient for option-level qualification; no profitability or automatic promotion claim |

For IEX 406, identify an unnecessary competing client/device if one exists, or ask Alpaca to identify/release a retained session. The holder remains unknown. For SIP 409, provider-confirmed permitted SIP access is required; the program cannot grant it. Existing OPRA/historical-option requirements remain in [owner actions](../OWNER_ACTIONS_MASTER.md). No new credentials in chat, paid purchase, permission change, brokerage inspection or order action was requested or performed.

Worker starvation/contention, source delays, recurring connection limits, sustained HTTP budgets and future-session acceptance remain unresolved. Manual order execution, privacy, stable IDs, parent-first dispatch, no blind uncertain replay and disabled live/BUY/SELL/TRADE_PROPOSAL boundaries are preserved. Periodic assistant review is not continuous exit monitoring.

## Setup impact

No dependency, credential, schema, risk/strategy parameter or alert-category change. Load the validated stream source through the existing single supervisor/task; do not start an export or backup as a second producer. SETUP documents the new diagnostic stages and rollback boundaries. Code rollback restores the source preimage and restarts the existing group; database snapshots are recovery artifacts, not an instruction to rewind live ledgers. [Setup](../../SETUP.md).

### Delivered source hashes

| File | SHA-256 |
|---|---|
|data/stream.py|ce6542403c63f8bc051579a65bcdcdedd4ebfc592c78a25a34fbdb41e4fa749f|
|tests/test_stream_refusal_provenance.py|e9ced17a37f1820bb5d688005f1d09aa770e3a71e61ea9c9752453040dbe5cd1|
