# AEGIS complete updated project report — October 21, 2026

## Changes

This is the current consolidated handoff, checked at 00:54 ET on October 21 (2026-10-21T04:54:58Z). It supersedes older readiness summaries where they conflict; historical evidence remains an as-of artifact. The most recent completed market session reviewed is October 20. This report does not claim October 21 live operation before the open.

This publication adds the consolidated report and a current-status pointer, and restores one isolated receipt-test fixture to the public repository. A broad monitoring/*receipts* ignore rule accidentally excluded test_v6_receipts.cjs from GitHub while leaving it locally available. A narrow exception now includes that source fixture without allowing runtime receipts. No trading algorithm, risk control, production configuration, sharing preference or service was changed or restarted for this report. The separately published October 20 diagnostic clock correction is included in the reviewed source.

## Six separate conclusions

| Area | Classification | Current conclusion |
|---|---|---|
| Accessible core software | TESTED IN ISOLATION | Reliability instrumentation, strict eligibility, eight legacy setup families, completed-bar horizons, research infrastructure, Telegram lifecycle and manual fill records exist. External dependencies below remain incomplete. This is not unrestricted end-to-end completion. |
| Automated verification | TESTED IN ISOLATION | Latest remotely observed CI passed 697 Python and 50 Node checks. Its omitted five receipt tests are disclosed and restored in this update. Current local full Node rerun is reported below. Command and schedule CI steps succeeded. |
| Local services | VERIFIED IN OPERATION | Six managed processes present; recent supervisor/listener/dispatcher/worker progress and HTTP 200 at 00:54 ET. A preceding bounded HTTP probe failed at 00:52 ET. This is a sampled observation, not uninterrupted availability. |
| Real-session data | VERIFIED IN OPERATION | October 19 and 20 were genuinely observed. Retained capture improved, but sustained strict live-analysis reliability FAILED. Both prospective first-hour verifiers failed. |
| Genuine option research data | BLOCKED | SIP/OPRA access is not established; no authorized executable historical BBO plus point-in-time chain dataset is established. No verified option recommendation or option P&L is available. |
| Strategy evidence | BLOCKED | No strategy has sufficient option-level evidence for its stated use. Underlying observations and synthetic demonstrations cannot establish option profitability. |

LIVE_SIGNAL_READY=false, live_signal_enabled=false and order_execution_enabled=false. BUY, SELL and TRADE_PROPOSAL kinds remain blocked. All orders are reviewed and submitted manually by the user. No profitability, calibrated win probability or continuous exit coverage is claimed.

## What the application actually does

AEGIS is a local SPY research assistant with a dashboard, market-data capture, rule-based directional analysis, research observations, Telegram commands/alerts and private manually reported positions. The engine does not currently consume an AI key. /request queues local feedback; this repository does not install a hosted AI reviewer. It does not inspect broker accounts, balances or orders.

The production installation is separate from this sanitized public repository. New users supply their own Telegram bot and authorized market-data credentials using the local encrypted setup. Original credentials, encrypted stores, access records, destinations, fills, receipts, databases, raw market caches and private operational logs are excluded from GitHub. Existing production sharing=true is preserved; a fresh installation starts with sharing=false.

| Production area | Implementation and role | Verification boundary |
|---|---|---|
| Dashboard and APIs | app.py; localhost dashboard 8767 and bounded /healthz | HTTP sampled in operation; broader API/caching behavior tested in isolation |
| Supervisor | ops/supervisor.py; six child services, singleton port 8768, restart/backoff, graceful stop, read-only status | CLI/singleton/recovery regressions; current processes/progress observed; unknown arguments fail with usage |
| Research service | core.spy_research; saved descriptive research/news | Source and fixtures; source failures stay visible |
| Worker | core.upgrade_service; capture, analysis, reports, maintenance and position reviews | Phase/deadline/DB telemetry; deadline misses and contention remain observable |
| Streams/history | data.stream and provider adapters; source watermarks, cache validation, same-feed REST repair, native history warmup | Fixtures plus real-session capture; fresh heartbeat/history never renews bid/ask |
| Listener/dispatcher | monitoring/commands.cjs and dispatch.cjs | Role/authentication/queue tests; recent heartbeats; API acceptance distinct from handset receipt |
| Storage | SQLite coherent snapshots, bounded transactions, append-only events/audit and private fill ledgers | Isolated migrations/restart tests; prior online-backup restore evidence |
| Research testing | backtesting/; registered protocols, reproduction, splits, costs and portfolio constraints | Infrastructure tested; genuine option evaluation remains externally blocked |

Modules under risk/, accounting/, research/ and retained options adapters are supporting research infrastructure; their presence does not authorize brokerage execution. Demos and historical files are not active-service proof. See [architecture](../../PROJECT_DOCUMENTATION.md), [operations](../../OPERATIONS.md) and [setup](../../SETUP.md).

## Algorithms and horizons

features/indicators.py validates finite OHLCV, ordered minute-aligned timestamps and completed regular-session candles. Invalid, duplicate/out-of-order and unfinished observations do not become usable history. Intraday aggregation requires complete contiguous buckets. Current-day daily candles are excluded from completed daily context. Confirmed swing highs/lows require two later candles, avoiding an unconfirmed endpoint swing.

Indicators include EMA 9/20/21/50/200; typical-price volume-weighted approximate VWAP; Wilder-style RSI14 and ATR14; MACD 12/26 with signal9; ten-bar momentum; twenty-return realized volatility; same-slot relative volume where sufficient genuine prior sessions exist; support/resistance and HH/HL versus LH/LL structure. Frame trend is BULL when price > EMA9 > EMA21 > EMA50, BEAR for the reversed order, otherwise NEUTRAL; unavailable inputs remain unavailable. Available-frame counts and correlated checks are descriptive evidence, not prediction probabilities.

Eight retained legacy setup switches are OPENING_RANGE_BREAKOUT, OPENING_RANGE_BREAKDOWN, VWAP_RECLAIM, VWAP_REJECTION, TREND_CONTINUATION, SUPPORT_BOUNCE, RESISTANCE_REJECTION and BREAKOUT_RETEST. They use family-specific structure, trigger-distance, volume, candle, VWAP and higher-frame predicates. Exact source conditions remain in core/idea_service.py and strategies/; /why exposes measured rejection reasons. All eight remain unvalidated research, not proven profitable strategies. A score is a heuristic rubric, not a pooled win chance.

Completed-bar descriptive evidence, fresh underlying eligibility and verified option eligibility are separate. The version spy-horizon-comparison-v2 defines:

| Variant | Context | ATR frame | Deadline |
|---|---|---|---|
| H60 | completed 15m and 5m | 15m | evaluation +60 minutes, only if before verified close minus5m |
| H120 | completed 30m and 1h | 30m | evaluation +120 minutes, only if before verified close minus5m |
| SESSION | completed 1h and daily | 1h | verified close minus5m; at least30 minutes remain |

The comparative generator requires agreement in both context frames and the VWAP side; latest genuine minute volume at least1.2 times the previous ten-minute mean; reference price within0.5 minute ATR of the completed close; at least ten completed5m bars. Trend pullback confirms a completed5m EMA9 reclaim using the preceding EMA for the preceding candle. Opening-range breakout/retest uses the genuine09:30–09:44 range, an earlier close beyond its boundary and a later retest/rejection. Stop distance is the larger of two-completed5m structural distance and the declared horizon ATR floor (0.50 or0.75). Targets are1R/2R; full exit is at stop,2R or deadline. A1R marker never means selling half of one contract.

Operational worker evaluation is nominally ten seconds; comparative observations follow genuine completed minute boundaries; scheduled status messages remain fifteen minutes. Entry validity, planned hold, actual reported exit and listed expiry are different fields. Entry expiry cannot exceed the applicable cutoff. Confirmation level, quote midpoint, modeled entry and actual reported fill remain distinct immutable named prices. The new comparative populations are tracked separately and do not broadcast as proven option ideas. No adaptive extra horizon or overnight strategy is qualified automatically.

## Strict data eligibility and provider status

| Layer | Rule and current limit |
|---|---|
| Completed-bar description |31 genuine contiguous completed current-session minutes; completed-bar end age0–120s. A descriptive view cannot grant entry eligibility. |
| Full underlying eligibility | Valid independently timestamped quote source and receipt ages at most5s, heartbeat at most30s, strict signed skew budget2s and31 completed current-session continuity slots. |
| Continuity exception | At most2 explicitly provider-confirmed no-print slots; continuity only, excluded from indicators, volumes, fills and real-bar stores. No invented bars. |
| Early09:45/10:00 reads | Explicitly limited; require at least15 genuine bars and applicable strict checks. |
| Calendar | Official-source provenance, complete required coverage and seven-day freshness; expired/incomplete data blocks gated entry. |
| Options | Actual listed SPY chain/contract, genuine entitled feed, timestamped valid bid/ask, spread/liquidity/Greeks and every separate hard gate. No rough strike fallback. |

IEX is single-exchange SPY proxy evidence only. Public historical bars fetched now remain historical with unverified transport delay; they are not a real-time independent quote. SIP/OPRA market-data requests previously returned403; stream PermissionError is a rejection observation, not proof of a specific credential or entitlement cause. No external permissions were changed.

No genuine option entry premium, option-dollar exit or option paper entry is claimed without verified fresh non-delayed option BBO. Questrade is retained but unconfigured and timestamp/Greek normalization remains incomplete; expansion is deferred. Reddit approved OAuth remains unconfigured; no anonymous bypass, raw text/author retention or training. Other-stock scanning and overnight/swing expansion remain DEFERRED OUTSIDE CORE SCOPE.

News uses Alpaca SPY headlines and official Fed/BLS/BEA plus CNBC feeds where accessible. Directional headline language is descriptive context, not a calibrated model or a complete future-event calendar. Reddit never overrides price/news bias. This report makes no new current-market-direction claim.

## Actual completed-session evidence

| Measure | October19 | October20 |
|---|---:|---:|
| Retained regular minutes |388/390 |390/390 |
| REST-backfill-tagged minutes |56 |62 |
| Missing minutes at generation |2 (15:55,15:59) |0 |
| Scheduled trend records |25 |25 |
| VALID_UNDERLYING |11 |13 |
| DESCRIPTIVE_ONLY |7 |3 |
| UNAVAILABLE |7 |9 |
| Stored SOURCE_TOO_OLD predicates |10 |10 |
| Stored BAR_TAIL_GAP predicates |4 |2 |
| Distinct underlying observations |21 |11 |
| Alerted observations |9 |0 |
| Underlying outcome labels |7 target2,11 stop,3 time |3 target2,7 stop,1 time |
| Selected API-accepted receipt records |312 |183 |

October20 generation was16:20:13 ET. Its narrow coverage/status PASS means at least95% retained minutes and all scheduled status artifacts, not sustained fresh quotes or profitability. All15 opening-range minutes were retained by report generation; this does not prove their availability at09:45. No real REST minute was first recorded after close, but intraday decision-time gaps still occurred. October20 hourly expected/retained/backfilled totals:09:30–09:59 30/30/14;10h60/60/18;11h60/60/14;12h60/60/9;13h60/60/3;14h60/60/0;15h60/60/4.

The October20 owner morning-outlook receipt recorded Telegram API acceptance at09:15:09 ET. One PREOPEN, one RECAP and25 TREND_LINE artifacts were counted; no SPY_IDEA or IDEA_UPDATE artifact was counted. Read-only ledger reconciliation found all eleven observations alerted=false with alert_blocker=COOL_OFF. The configured three-loss/60-minute cool-off examines closed underlying research observations, including silently tracked observations; it is not evidence of losses in a personal broker account. No control was bypassed. These eleven observations are not eleven alerts, actual trades or option returns.

October20 retained3,890 regular-session setup/direction/minute traces. Failed checks overlap: structure1,798; trigger distance1,577; volume1,410; candle1,095; price/VWAP1,055; higher-frame20. Counts are not independent trades or odds. Across feeds the report counted264 reconnects,85 PROCESS_PAUSED markers,one WATCHDOG_RESTART and116 backfills (115 DATA_OK,one UNAVAILABLE/OperationalError). Reconnect count is not an IEX-only outage count; pause markers do not prove Windows slept. Last observed NTP offset approximately+0.201s is not a whole-session clock series.

Both genuine first-hour prospective verifiers FAILED. October19:60 samples,13 eligible quote-age checks,3 combined LIVE_TREND passes (3/34 after warmup). October20:59 samples,11 eligible quote-age checks,zero combined passes (0/33 after warmup). The missing sample is not fabricated. Each had49 delayed/public cross-check observations. Legacy bar_tail_qualifies includes preceding quote/heartbeat conditions, so it is not an independent coverage fraction. Local evaluation runtime is not feed transport latency. Later recovered bars do not erase these failures.

The session JSON SHA256 values bind the reviewed private evidence without publishing it:

- October19: fdd07c51fbb7aacc052b7325317a585a663a548402b9eca69192710fbd5dde7c
- October20: 8906f6c6f18ba3c2e414b2fec7bd4e5c0f56e283431687eabd543112bce1c3a7

## Current local operation and unresolved reliability

At00:54:58 ET all six processes were RUNNING, process_alive=true, restart counters0 in that supervisor snapshot. Supervisor age2.130s, listener4.557s, dispatcher2.177s; worker last completed work2.706s old. The latest completed cycle was6.875s against10s. Dashboard bounded HTTP returned200. At00:52 ET an earlier bounded HTTP probe returned unavailable despite processes being present; this failed observation is retained. The previous sampled cycle10.703s missed budget. No root cause for that HTTP timeout was established and no restart was performed merely to conceal it.

Process-local database counters were1,102 busy retries and75 failures since the existing worker launch, not daily counts. Last error class SQLITE_BUSY; maximum recorded transaction4.843s. The last-good and overrun samples demonstrate variability, not a resolved contention problem. The next engineering investigation must isolate the specific transaction/phase and source-to-receipt delay path. A connection, recent worker heartbeat or HTTP200 does not establish market-data readiness. The October20 status-clock fix takes its evaluation clock after reads/probe; genuinely future timestamps stay negative and unavailable ages stay unavailable. No freshness tolerance was widened.

Authenticated pending owner queue metadata and private reported exposure were checked without account inspection; no personal details are included here. A stale market reading never closes a reported holding. Fill reports remain user-reported, not broker verified, and expiry never implies exercise or settlement.

## Telegram commands, messages and privacy

The six-entry main menu is /trend /score /demo /news /more /help. All36 typed commands remain:

| Group | Commands |
|---|---|
| Help/access | /help [all], /howto, /join INVITATION_CODE, /leave, /start |
| Owner administration | /users [PAGE_NUMBER], /invite, /revoke ACCESS_ID, /alerts [CATEGORY on/off; setup NAME on/off; silent on/off] |
| Status/diagnostics | /status, /feed, /health, /trend [details], /details, /why, /more |
| Research/news | /score, /outlook, /sentiment, /research, /signals, /setup, /learn, /forecast, /premarket, /paper, /news, /request MESSAGE |
| Private reported trades | /fill quantity/premium/fees/time/confirm/cancel VALUE; /void EVENT_ID; /plan OCC_SYMBOL INVALIDATION T1 T2 MAX_HOLD_MINUTES; /option_bought and /option_sold OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME [FORCE]; /option_positions; /skipped IDEA-ID |
| Fictional practice | /demo start/bought/status/exit/sold/skipped/stop |

See [full arguments and roles](../../COMMANDS.md). Owner/guest/stranger/revoked/expired-invitation routes are distinct. Own-user fill output, administration and monitoring limitations stay private. FORCE explicitly acknowledges a separate duplicate-looking reported fill; VOID appends reversal and preserves history. No command submits an order. Demos never establish real fills or strategy evidence.

Durable event IDs/reservations enforce deduplication. Initial idea acceptance must precede dependent updates per recipient. Definitive rejection can retry within bounds and expiry; uncertain-after-send and legacy uncertain receipts never blindly replay. Revocation is checked before dispatch. TELEGRAM_ACCEPTED means Telegram accepted the API request, not that a phone displayed it. Receipt totals above are a selected as-of population, not proof about all historical uncertain records.

EXAMPLE — illustrative wording, fictional price, not a current signal or captured market output:

>10:15 ET · SPY $500.00 · IEX completed-bar research
>Next hour: MIXED · Session: UP evidence
>New entry: WAIT — option pricing unavailable.

EXAMPLE — watch-only research, not a recommendation:

>CALL watch · IDEA-EXAMPLE · unvalidated research
>Hold:60 minutes · entry valid until10:20 ET
>Watch only—option pricing unavailable.
>Underlying confirmation $500.10 · invalidation $499.50 · target $501.00
>Exit deadline11:15 ET · manual review required.

EXAMPLE — update:

>IDEA-EXAMPLE · monitoring unavailable
>Fresh quotes are missing. No exit or position closure is confirmed.

Premium at risk on a purchased option is distinct from an estimated loss at a planned stop; a modeled stop loss is never called the maximum possible loss.

## Schedule and calendar

Verified trading days retain09:15 ET morning outlook,09:20 owner self-check, silent15-minute status lines09:45–15:45, timely qualifying unvalidated research alerts,16:15 recap and local16:20 session report. There is no change-only throttle. Early closes use verified close-relative deadlines; holiday/weekend/DST simulations cover session conversion. Storage is UTC, display America/New_York.

The installed official calendar was genuinely verified2026-10-17T06:58:53.753504Z; coverage_through2026-12-05T04:59:59Z (December4 ET). Coverage date is not freshness expiry. Seven-day freshness expires October24 at02:58:53 ET; the three-day owner-warning threshold begins October21 at02:58:53 ET, after this observation. No timestamp was edited to renew verification. Official fetch failures and last-good data are retained. Refresh with python -m news.calendar_updater and inspect successful provenance/completeness; RSS availability alone does not refresh a calendar. Official2027 exchange dates are supported; unknown2028 remains fail closed.

## Research protocol and genuine option evaluation

The registered comparison has12 trials:two families ×three horizons ×two ATR floors. Costs disclose72 execution scenarios:human delay0/15/60s ×slippage$0.01/$0.03 per premium share per side across12 trials; fees$0.65 per contract per side. These assumptions do not replace executable observations. Development20 sessions, validation10 and sealed final20 must use frozen chronological dates after registration; trades with outcome windows crossing boundaries are purged. Selection is pinned before final. Reusing final outcomes for tuning consumes that final period. Already inspected October history is retrospective exploration.

No-trade and MATCHED_CLOCK_RANDOM_DIRECTION_V1 are explicit baselines; the latter randomizes direction at identical decision times, not entry times. Day-block uncertainty and Bonferroni simultaneous intervals account for disclosed comparisons. Fewer than20 day blocks cannot support uncertainty claims. Qualification requires at least100 closed genuine option observations,20 final days, positive simultaneous net expectancy and paired-baseline bounds, at most5% unresolved outcomes, concentration checks and robustness to worse fills. Passing would support further research, never enable live flags.

The study contract rule requires actual standard SPY OCC terms, listed expiry strictly after the ET holding-deadline date, current |delta|0.40–0.55 with Greek timestamp≤60s, positive sized quotes, spread≤10%, reported OI≥100 and volume≥100, plus genuine quote age≤5s and entitlement/provenance. Prior-day Greeks cannot satisfy current-Greek requirements. The trusted authorized historical-export receipt list starts empty; a manifest label or hash alone does not establish licensed feed access.

Option evaluation models ask-side entry and bid-side exit, fees/slippage, alert/human delay, missing quotes, ambiguous stop/target ordering and portfolio cash/premium constraints. A limit bar touch alone is not a fill; unresolved outcomes retain reserved capital. Reported actual fills remain a separate private ledger. Fixed delta/gamma/theta and underlying proxies are sensitivity analysis only. No genuine option-dollar expectancy, profit factor, drawdown or returns can presently be reported. External QuantConnect/LEAN, LumiBot and QuantRocket design references are research patterns; no execution module or example return is imported as a SPY options claim. See [research status](../../STRATEGY_RESEARCH.md) and [third-party notices](../../THIRD_PARTY_NOTICES.md).

## Verification

Latest independently retrieved successful remote run: [GitHub Actions39492816835](https://github.com/jdp323/aegis-spy-research/actions/runs/39492816835), reviewed commit c9ecc0bcc247bc3abed223a56e1841b07e3cafed. Full-suite output checked_at2026-10-20T20:34:32.774938Z:

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| General Python |686 |0 |0 |0 |
| Backtesting Python |7 |0 |0 |0 |
| Monitoring Python |4 |0 |0 |0 |
| Explicit Node files in that CI run |50 |0 |0 |0 |
| CI total |747 |0 |0 |0 |

That CI checkout contained21 Node files. Earlier local export verification passed55 tests in22 files because the ignored receipt fixture existed locally. These are different executed populations; the old748 total is not the latest CI total. This update restores the missing five tests covering bounded definitive retry, uncertain no-retry, allowlisted failure fields, expiry and blocked live kinds. No test/assertion was deleted or weakened. The public runner discovers committed test_*.cjs files then passes their explicit list serially to Node. Current local full Node rerun: 55 passed,0 failed,0 cancelled,0 skipped across22 explicit files (53.375s); fake transports only. Combined with the697 Python checks in current CI, these cover752 checks in separate runs, not a single fresh combined run.

Exact top-level CI commands: python -m ops.setup init; python -m ops.release_guard --working-tree; python -m ops.release_guard --base BASE_COMMIT; python -m ops.ci_tests; python -m ops.verify_commands; python -m ops.day_simulation. Python discovery is unittest test*.py under tests/, backtesting/ and monitoring/ in a short isolated copy with external networking blocked. CI used Python3.12.10 and Node24.21.0 on Windows. The latest command/schedule CI steps completed successfully; logs contain generated filenames rather than their full matrices. The separately retained full verification reports document36×5 roles×3 argument cases=540 PASS, and24 schedule scenarios/419 fake notifier events PASS. This report does not invent fresh case totals from CI filenames.

Previously retained checks also include all nine online-backup databases restored/integrity-checked in a new inert directory, source hashes verified, frozen research reproduction, DPAPI synthetic roundtrip, clean install/pip check, targeted delivery/order/cache/skew/calendar/option refusal tests and post-restart service smokes. Those are dated retained checks, not rerun today. Initial baseline/failing runs, path-limit errors, Node allocation/timeout failures and subsequent fixes remain recorded; passing later tests does not erase them. The full Python suite is not repeated locally for this documentation and test-export correction; current remote CI and targeted/current Node evidence are stated separately. Staged release-guard result: PASS:324 staged files scanned, zero findings; secret/private-path refusal remained enabled.

The22-file explicit current Node command is:

~~~text
node --test --test-concurrency=1 monitoring/test_access.cjs monitoring/test_bot_identity.cjs monitoring/test_combined_menu_demo.cjs monitoring/test_command_pacing.cjs monitoring/test_command_registry.cjs monitoring/test_commands.cjs monitoring/test_dashboard_cache_view.cjs monitoring/test_delivery_order.cjs monitoring/test_demo_commands.cjs monitoring/test_details_route.cjs monitoring/test_notifier.cjs monitoring/test_paper_alerts.cjs monitoring/test_paper_callbacks.cjs monitoring/test_positions.cjs monitoring/test_profiles.cjs monitoring/test_role_routes.cjs monitoring/test_shared.cjs monitoring/test_sharing_config.cjs monitoring/test_status_encoding.cjs monitoring/test_trend_route.cjs monitoring/test_v5_schedule.cjs monitoring/test_v6_receipts.cjs
~~~

## Remaining work and smallest next action

| Item | Classification | Precise dependency / next action |
|---|---|---|
| Sustained fresh underlying analysis | BLOCKED | Investigate per-phase source→receipt delay and contended transaction using genuine next-session timestamps; repeat prospective observation without widening strict gates. |
| Intermittent HTTP/deadline/SQLITE_BUSY | BLOCKED | Correlate bounded request timing, worker phase and specific DB transactions; retain failures. A later200 is not a root-cause fix. |
| Genuine options | BLOCKED | Authorized provider must supply entitled, timestamped actual chain/BBO and adequate historical span; verify using market-data endpoints only. Do not buy or change permissions automatically. |
| Option strategy evidence | BLOCKED | Acquire audited genuine data and complete preregistered chronological study; disclose all trials, costs, exclusions and day-block results. No earnings promise. |
| Calendar renewal | IMPLEMENTED, EXTERNAL VERIFICATION PENDING | Run supported official updater before seven-day expiry; verify new payload/hash/completeness, preserve last-good on failure. |
| Handset receipt | IMPLEMENTED, EXTERNAL VERIFICATION PENDING | Owner observes an actual delivered message if needed; API acceptance alone cannot attest phone delivery. Never resend uncertain messages blindly. |
| New-user installation | TESTED IN ISOLATION | Follow separate SETUP.md with own local credentials; each installation must verify its own feed, calendar and live session. |
| Extra horizons, partial exits, overnight/swing, scanner/Reddit/Questrade expansion | DEFERRED OUTSIDE CORE SCOPE | Separate authorized specification/data/validation required; retained config/module names are not working support. |

## Setup impact and operational handoff

No install, dependency, credential, operational CLI or default configuration changed in this report. The receipt source-test ignore exception changes public test inclusion only. [SETUP.md](../../SETUP.md) remains the separate complete fresh-install guide; [OPERATIONS.md](../../OPERATIONS.md) covers recovery/rollback. New users need Windows10/11, Python3.12, Node24, Git, their own private Telegram pairing and authorized market-data keys. No AI key is required. Keep Windows awake/online; periodic assistant review is not continuous position monitoring.

From the project directory with its venv activated:

~~~powershell
python -m ops.supervisor start
python -m ops.supervisor status
python -m ops.supervisor stop
python -m ops.ci_tests
python -m ops.verify_commands
python -m ops.day_simulation
python -m ops.reproduce_research --help
python -m ops.session_report --date YYYY-MM-DD
python -m ops.verification_packet --run-tests
~~~

Generated operational packets/session reports stay private until sanitized. Before upgrades use SQLite online backup including committed WAL plus encrypted configuration; restore into a new inert directory, check integrity/hashes and reconcile newer append-only fills/receipts before choosing a launch directory. Do not overwrite newer history or launch both copies. No production database was rewritten for this report. Existing issued packets and source manifests retain their original as-of meaning.

Next-session procedure is implemented, not already passed: check09:20 self-check; capture from09:30; inspect limited09:45 read, source/receipt/heartbeat ages and continuity; review09:35–10:35 prospective samples and16:20 session report. Record failures honestly. Real October19/20 sessions were observed; this October21 update itself is a closed-market operational check.

## Limitations and ways this could be wrong

The selected session reports/receipts may omit unrelated legacy populations. Backfill improves retained coverage without proving decision-time availability. A process or heartbeat can progress while quotes are stale. Local HTTP is only sampled. Cumulative DB counters are not daily failure counts. Correlated underlying outcomes, cool-off suppression and incomplete histories cannot be converted into option profitability. The latest CI had a test-publication omission, now disclosed and repaired; fixtures cannot prove every behavior or external provider response. Calendar coverage and freshness are separate. Sanitization excludes private raw evidence, so the public report supplies hashes and bounded aggregates rather than independently redistributable raw licensed data. No external blocker is described as solved.

Every future published update must include a new sanitized update report and refresh SETUP.md if setup changes. Hook/CI checks support this policy; administrators can bypass repository workflow controls, so they are not absolute enforcement. This release improves capture truthfulness and observability; it does not validate a strategy or enable live signals.

## Reviewed public source manifest

SHA256 of reviewed source files; the reviewed base commit is c9ecc0bcc247bc3abed223a56e1841b07e3cafed. The new receipt fixture is identified separately by its own hash. Original as-of manifests remain preserved.

| File | SHA256 |
|---|---|
| app.py | 47e8aa75073ede483ffe5d19b189816d86a8ecb8af4e7620212a5ecf90b27459 |
| ops/supervisor.py | 48207c5472a4ee7a5f11396da8143a59b087981a71ca044fa30f86265a2e3ab3 |
| ops/test_runner.py | c90609feb41333f26dd3a46a2570168b1a723c36da1e25fccef90a79fd65d147 |
| core/idea_service.py | dd8215a3ea7d08d6a90a2ba5f4aa328718f11f48d883f6fc1c80a3fa92a0dc61 |
| core/research_horizons.py | 6fc423cc526552c1134df2c957c9db82a6d7821b5ea88fae327c583ce6d70bc6 |
| features/indicators.py | e302a92ced1c7af702ddfc1f4849771f692f7572ccaf92425d0d5abaf30c16bf |
| core/storage.py | 08baed339948b240dd0fdbf0d5aeb47632a8ce22e2be0c3ac247a381523689fb |
| data/stream.py | c0dd306781fbb942d2477e57a077aea475b80c8dcfb7e411c6d0d8806ff5eaa7 |
| monitoring/command_registry.cjs | dd96e0bbb52692bce78b43a64b7754360301bfd9aa48bc2cd6e67d6ad91eff01 |
| monitoring/notifier.cjs | 318a682a9d47c9cb8c384eed9830f81ea63c60251d4e8861614a4606dc51ee98 |
| monitoring/dispatch.cjs | f62e03931429e939a210e1acaba12254a99a88a0b473fffc695b72c80f7029e9 |
| monitoring/test_v6_receipts.cjs | b251b8f01daf8a80259dc6285382fdea0d289a518b2f0fa2bab4cad39f739bcb |
| SETUP.md | 56e897b2860f48723e7d2bbd77f4efda45c27f8c09ffff44f02ce5342d2a50c0 |
