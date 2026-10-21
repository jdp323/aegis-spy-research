# AEGIS Telegram experience — implementation and operational handoff

## Changes

Deployed October21,2026, during the closed market. This supersedes the earlier October21 documentation-only status for the changed features. It does not overwrite old reports, private history or uncommitted production configuration. No new Telegram transcript attachment was available in this turn; retained October20 evidence, production formatting and the supplied format requirements were inspected instead. No transcript content was invented.

### Exact implementation

- Current trend v1 uses completed close versus session VWAP and the recent15-minute price change. Agreement givesUP/DOWN; conflict givesSIDEWAYS; missing/gapped/future/old data givesDATA UNAVAILABLE. Early opening reads remain explicitly limited. Quote-independent bar research never grants entry eligibility.
- Forward outlook conditional-direction-v1 is a separately named hypothesis, with VWAP invalidation and explicit H60/H120/session target times. Immutable issue records include abstentions/reference times. Premarket outcomes compare regular open to final regular-minute close; next-hour outcomes use the issue reference and an exact future observation. Same-feed genuine quotes can be sampled only0–5seconds AFTER the target. A later bar cannot repair a missing exact observation silently. Option profitability is separate.
- Entry eligibility still checks fresh bid/ask, receipt, heartbeat, continuity, signed skew, calendar, setup and controls. No threshold was widened. A rising trend does not imply a worthwhileCALL.
- Actual production formatters now produce7-line premarket,5-line silent status,9-line research opportunities,2-line changed-state updates and6-line recaps. Notifier metadata validates these limits and suppresses its former extra envelope. Experimental/manual labels, blocked live kinds, parent-before-update, revocation, deduplication and uncertain-send rules remain enforced.
- Legacy setup confirmation is honestly labelled1-minute where that is what the algorithm requires; no fictional5-minute confirmation is advertised. All eight families remain. Entry validity now ends strictly before holding cutoff; new generations use spy-ideas-v3-entry-window. Actual planned minutes are displayed rather than describing a clipped plan as a full hour.
- Research pause v2 persists processed observation IDs and an explicit reason/start/end/cause set. New losses during the same pause do not roll its timer. Three newly qualifying post-episode losses are needed for another episode. Research deterioration, direction-alert cooldown and private actual-position risk remain separate. /details shows the rule and pause; fifteen-minute trends continue.
- Store.merge_rows now parses, merges, sorts and encodes BEFORE acquiring its SQLite writer lock; a compare-and-swap transaction detects concurrent stream/backfill changes and rebuilds. Quote/last-market/stream-health state is committed in one transaction. Source and receipt timestamps remain original.
- Stream telemetry owns/closes its database handle with Store. SQLite ingestion failure is recorded as such rather than needlessly reconnecting an authenticated socket. Provider numeric rejection codes are allowlisted; raw error bodies/secrets are not logged. Genuine OPRA observations have an append-only prospective collection path but never imply entitlement or strategy qualification.
- A separate bounded latest-five-minute repair worker can recover completed IEX bars without waiting behind long history warmup. No-print rules remain provider-confirmed and continuity-only. Tail repair does not claim a quote is fresh.
- Duplicate idea-engine execution within each worker cycle was removed. Recorder fingerprints skip unchanged history, including across restart, while completion watermarks preserve future-candle activation and revisions. Payload preparation occurs outside archival write transactions. Indicator prior-session membership is linear rather than quadratic, with unchanged mathematical output.
- Receipt inventory is sampled once per minute rather than on every ten-second cycle. Premarket acquisition runs in background before the09:15slot; a missing/late result yields an honest unavailable outlook without blocking scheduled dispatch. /healthz tests HTTP responsiveness without process enumeration or busy database reads; detailed service status remains separate.

The validated production patch preserves installation-specific runtime paths. No real order, broker/account/balance query, subscription purchase, external permission change, guest development message, sharing change or blind resend occurred. Existing pending events retain their original payloads and IDs.

## Verification

### Automated checks

BASELINE:752 passed,0failed/errors/skips (686 general Python+7backtesting+4monitoring+55Node). Final current-source test result: 780 passed:712 general Python+7backtesting+4monitoring+57Node,0failures/errors/skips; retained as telegram_final_all_tests.txt. Every current Python/Node source file is bound to the isolated snapshot. Exact isolated commands: python -m ops.ci_tests; python -m ops.verify_commands; python -m ops.day_simulation. Python discovery uses test*.py in tests/,backtesting/,monitoring/ under short isolated TEMP paths with external networking blocked. Node uses an explicit23-file list with --test-concurrency=1, retained in the final test result.

Command-role verification:36 commands ×5 roles ×3 argument forms =540 casesPASS. Full schedule verification:24 scenariosPASS,401 actual-notifier calls accepted using fake clocks/recipients/transports. Covers normal/choppy/stale sessions, restart, holiday/weekend, DST, early close, recovery and refusal. The reduced message count reflects removal of redundant entry updates; it does not change the15-minute status cadence. Fixture payload tests verify the actual five-line Telegram text after notifier processing, not just a pretty document.

Targeted owner/HTTP checks passed25 cases; the final owner group passed23 before the retained timestamp case was added. A retained October20 source19:59:53.012Z/receipt20:00:08.006Z regression preserves14.994s source age despite zero receipt age. Prices in that schema fixture are synthetic placeholders, explicitly labelled. Original signed-age/clock/provider/ordering/privacy tests remain.

Initial failures are retained: SQLite telemetry handles prevented Windows fixture cleanup; an added processing timer consumed a mocked clock unexpectedly; old verbose-template assertions did not match the new version; the prospective sample initially compared a missing feed tag instead of original provider provenance; the real notifier rejected new labels under its old-format validator. These were fixed in code and versioned semantic tests. A targeted command used the wrong worker-test module name and failed import; the full discovery suite covers the actual module. No failing check was deleted, no assertion removed merely to pass, and no freshness tolerance widened.

A new test asserts concurrent merges preserve both writers; recorder tests preserve original recorded_at and later completion/revisions; future sampling tests reject pre-target and wrong-feed prices; pause tests cover expiry/new cause/restart/deduplication. Existing active-position tests keep reported holdings open during missing data and preserve private monitoring warnings.

### Before/after measurements

| Measurement | Before | After | Limit |
|---|---|---|---|
| Isolated20,000-row history merge total |281ms |188ms | Single synthetic fixture run |
| Same merge writer-lock duration |218ms |16ms | About93% shorter; not a live latency result |
| Actual sampled worker cycle |7.344s before restart; earlier12.078s missed10s budget |2.844s and2.657s | Closed-market samples, not sustained-session proof |
| Busy counters |1,102 retries/75 failures since prior process start |0/0 across218 new-process transactions in second sample | Counters reset at restart; windows differ |
| HTTP health/root/upgrade/status before |200/200/200/200;78/125/234/78ms | Both post samples200all; latest health/root below clock resolution, APIupgrade16ms, APIstatus16ms | Earlier intermittent timeout retained; no root-cause certainty for every timeout |
| Worker capture/session phase mean |1.979s over50 prior phases |0.408s over8 post phases | Unequal closed-market windows |
| Legacy analysis phase mean |1.746s |0.689s | Includes removal of duplicate idea evaluation |

At03:13ET all six managed processes were alive with zero supervisor restarts in the new snapshot. Supervisor age1.461s,listener3.625s,dispatcher1.831s; completed worker work0.589s old. A populated diagnostic dashboard snapshot was separately observed, data_available=true and no refresh error. Cached diagnostics still cannot authorize entry. The recorded after window includes a4.860s reliability phase and5.484s legacy phase maximum: variation is preserved.

Actual code causes addressed are long lock scope, redundant scans/evaluation, coupling of SQLite failure to reconnect and blocking premarket work. These findings do not establish that every historical stale quote or reconnect had one cause. IEX can still provide sparse/old bid/ask; strict five-second eligibility remains closed when that happens. The next live session must establish decision-time capture, quote latency and continuity anew.

### Pause replay

Same eleven retained October20 candidates/outcomes, memory-only old-versus-proposed policy replay: old pause11/11 and7warnings; proposed pause2/11 and1warning. The proposed active episode13:28–14:28ET has three newly qualifying closed research losses as cause. Observations closing during that episode are consumed without extending it. No historical outcomes changed. This does not imply nine extra successful trades or actual owner losses; all other gates still apply.

### Backup, privacy and preservation

Recoverable private backup: work/backups/telegram-experience-20261021-complete, outside production;3,297 hashed files and8 SQLite online backups including committedWAL data. An earlier interrupted backup is retained and explicitly incomplete. Read-only prefix checks matched 28 of 29 non-state tables and the configuration hash. The exception was the pre-existing mutable minute-level rejection-trace aggregate: ten rows from one minute had been updated by its old upsert while services ran. That failed preservation check is retained; it is not claimed as PASS. Idea/outcome/private records matched. This release freezes existing aggregate rows and adds immutable, append-only snapshot revisions with update/delete rejection triggers. The earlier backup retains the original aggregates. The pre-existing source histories, earlier backups, original reports and uncertain reservations remain local. Production configuration SHA256 was checked against backup; live/execution flags remainfalse and signals.shared=true is preserved. New-install sharing remainsfalse. Private reported exposure and pending queue metadata were reviewed without broker verification; no private details are published.

## Actual fixture-generated messages

Every price below is FICTIONAL and generated by the real formatter. These are examples, not current market findings, orders or evidence of profit. The [complete gallery](../TELEGRAM_FIXTURE_GALLERY_2026-10-21.md) is separately downloadable.

### premarket — EXAMPLE

~~~text
SPY PREMARKET · Oct 21
Today’s outlook: UP while SPY holds above $500.00
Premarket: $501.20 · as of 09:10 ET
CALL watch: confirmed break above $502.00
Downside reversal: below $500.00
Major events: no required scheduled event listed; optional coverage incomplete
Research outlook · reassess after the open
~~~

### trend — EXAMPLE

~~~text
11:00 ET · SPY $501.89
Current trend: UP
Next hour: upward bias
New entry: WAIT — pullback not confirmed
Research · SIMULATED · as of 11:00 ET
~~~

### idea — EXAMPLE

~~~text
CALL RESEARCH · ID aaaaaaaaaaaaaaaaaaaaaaaa
Enter after a completed 1-minute close above SPY $501.50
Do not enter above SPY $501.80
SPY target: $503.00
Exit condition: SPY at or below $500.80
Planned hold: up to 60 minutes; exit by 12:00 ET
Entry expires: 11:10 ET
Underlying watch only · option contract unavailable.
Experimental · manual review; underlying levels; no guaranteed stop-loss cap
~~~

### followup — EXAMPLE

~~~text
ID aaaaaaaaaaaaaaaaaaaaaaaa · Monitoring unavailable; no exit confirmed
Research update; your fills remain separate.
~~~

### recap — EXAMPLE

~~~text
SPY RECAP · Oct 21
Ideas alerted: 1
Underlying research: 1 closed · 0 open · 0 unresolved
Option-paper dollars: unavailable without genuine quotes
Next session: wait for genuine opening-range data
Data quality varies · /score for detailed statistics
~~~

## Strategy research findings

The new original deterministic module is shared by production read-only comparison and retrospective replay. It does not send baseline trades or auto-promote a strategy. [Primary rules/licenses/adaptations](../../research/PUBLISHED_STRATEGY_SOURCES.md) and [preregistered experiments](../OWNER_EXPERIENCE_EXPERIMENTS.md) describe Concretum IMP, QuantRocket first/last (unfiltered andVIX20), and SPY-only deterministic LumiBot ORB, alongside the separately versioned existing pullback/retest study. No third-party execution code was imported. QuantRocket source isApache2; LumiBot project isGPLv3, not copied; no explicit article-code reuse license was found for Concretum.

Retained-data replay used13,510 source rows,13,251 normalized regular-session bars across34 sessions,27 complete and7 excluded incomplete. Historical downloads are not contemporaneous live captures. The ORB time-exit diagnostic had96H60,78H120 and105SESSION observations with modeled60-second response delay and$0.03/share round-trip cost. Aggregate diagnostics were−$0.440,+$14.745 and−$2.430 per share respectively across those overlapping observations. These are NOT portfolio returns, option results, a stop/target backtest or an untouched final test. No strategy was selected from them.

Concretum mathematical decision fixtures pass, but exact retained-data evaluation remains UNAVAILABLE: the new bounded authorized corporate-action endpoint returned an empty category object rather than the required explicit cash-dividend array. Unknown coverage was not treated as zero dividends. The prior same-clock-history requirement is explicit. Full leverage/volatility sizing and the separate overnight reversal sleeve are not reproduced and their advertised returns are not claimed.

QuantRocket unfiltered agreement was calculable in26 delayed decision samples; itsVIX-filtered variant lacked genuine contemporaneous VIX. The15:31 completed-bar adaptation has fewer than30minutes left, so current registered H60/H120 and minimum30-minuteSESSION variants exclude it. This is a disclosed incompatibility, not a reason to stretch the session. LumiBot AI ranking/multi-stock/account sizing is adapted out, and no external example returns transfer to SPY options.

The existing12-trial/72-execution-scenario option study, chronological development/validation/sealed-final split, purge rules, day-block uncertainty and explicit costs remain separate. Already examined dates are retrospective development. No sufficient genuine option-level evidence exists for ANY strategy.

## Limitations and exact external dependencies

1. Genuine current consolidated stock and option feeds remainBLOCKED. October21 authorized market-only probes returnedIEX200 but old/invalid closed-market bid/ask, SIP403 andOPRA403 with entitlement rejection. Credentials present, HTTP access, feed authorization and fresh quotes are separate facts. [Alpaca official market-data documentation](https://docs.alpaca.markets/us/docs/about-market-data-api) distinguishes IEX/indicative basic data from consolidatedSIP/OPRA access. Owner action: verify an authorized plan permitting the requested feeds, or provide another supported entitled source; then rerun the market-only readiness probe. No purchase or permission change was made. Sharing/redistribution rights need separate confirmation.
2. Genuine historical options need audited authorized executable bid/ask, point-in-time actual chains, listing/expiry/liquidity/Greek timestamps and adequate span. Indicative/delayed prices and fixed-delta estimates cannot qualify options or profit. The prospective genuineOPRA quote path is implemented but remains idle without permitted subscriptions/data.
3. Exact Concretum comparison needs complete verified dividend history and enough genuine prior same-clock sessions; VIX20 comparison needs timestamped contemporaneous VIX. The corporate-action malformed/empty-category failure remains preserved. Independent formatting/reliability work was completed despite these gaps.
4. The installed official calendar remains based on genuineOctober17 verification and expiresOctober24 at02:58:53ET, irrespective of longer coverage dates. Refresh with python -m news.calendar_updater before expiry and verify provenance/completeness. Do not edit verification timestamps. Expired/incomplete event data blocks entry; descriptive research remains labelled.
5. A real post-update market session has not been observed. ExistingOctober19/20 first-hour failures remain failures. Follow the implemented09:20check, capture from09:30,09:35–10:35 prospective verifier and16:20session report. Full later backfill cannot establish original decision-time availability.

## Feature readiness

| User-facing feature | Verdict |
|---|---|
| Short09:15premarket outlook | VERIFIED IN OPERATION for scheduled formatting/dispatch: seven-line message accepted at09:15:28ET; underlying quality remains separately gated |
| Silent fifteen-minute trend | TESTED IN ISOLATION; production paths deployed; new-session data verification pending |
| Timely underlying research opportunity | TESTED IN ISOLATION; manual/experimental watch only; strict entry/pause gates preserved |
| Verified contract and premium | IMPLEMENTED, EXTERNAL VERIFICATION PENDING; actual permitted chain/BBO required; currentlyBLOCKED |
| Follow-ups for reported holdings | TESTED IN ISOLATION; existing private lifecycle/monitoring checks retained; no current holding used to invent a live exit test |
| Recap | TESTED IN ISOLATION; actual six-line formatter and fake dispatch verified; next scheduled production recap pending |
| Local dashboard/services | VERIFIED IN OPERATION in two advancing post-restart samples; not continuous coverage |
| Option strategy profitability | BLOCKED; no supported profitability claim or automatic live promotion |

## Setup impact and operational handoff

[SETUP.md](../../SETUP.md) is updated separately. Existing users keep their own encrypted stores/configuration and sharing preferences. A coordinated supervisor restart is required because compact-event metadata must reach the updated worker and notifier. That restart was performed locally after validation. No new AI key, permission or subscription is required to run isolated fixtures. The engine remains deterministic/rule-based.

From the project directory using the configured Python:

~~~powershell
python -m ops.supervisor start
python -m ops.supervisor status
python -m ops.supervisor stop
python -m ops.ci_tests
python -m ops.verify_commands
python -m ops.day_simulation
python -m ops.data_readiness_probe
python -m ops.published_replay --help
python -m ops.verification_packet --run-tests --compact
~~~

Read /details for current trend rule, source/receipt ages, calendar and research pause; /why for exact setup failures; /score for detailed separate underlying populations. Never blindly resend uncertain messages. Keep the Windows PC awake/online. Manual fills stay private and are not broker verified; no expiry settlement/exercise is inferred.

Rollback: stop services, restore the validated source backup into a new inert directory, verify hashes/SQLite integrity, preserve newer append-only fills/receipts and choose the launch directory deliberately. Do not launch restored and active copies simultaneously or overwrite newer history. Current local report/packet paths and the source-hash manifest are linked below after verification.

### Ways this could be wrong

Closed-market timing samples do not establish opening-session load or network reliability. The before/after windows differ and database counters reset at restart. Sparse IEX quotes may still fail strict gates. Tests cover declared fixtures, not every provider failure or user sequence. Forecast future samples can remain missing; absence is not relabelled as neutral. Recovered minutes and API acceptance are not proof of decision-time capture or phone delivery. Research observations overlap and are not independent trades. A test or configured credential cannot establish entitlement, strategy edge or future profits.

## Owner-requested full-day demo

The October 21 simulated day passed with 29 events and a midday restart: 1 premarket, 25 silent trend updates, 1 idea, 1 update and 1 recap. All 29 traversed the actual notifier with a fake clock and fake transport. Five representative messages were then sent sequentially as private TEST events through the installed encrypted notifier. Telegram accepted all five; no guest sends, sharing changes, real orders or inferred owner fills occurred. Every real message was headed “🧪 DEMO — SIMULATED DATA” and ended “Nothing here is real.” API acceptance does not establish phone delivery. [Complete generated day transcript](../SIMULATED_DAY_DEMO_2026-10-21.md).

The first large production verification-packet attempt correctly refused PACKET_TOO_LARGE after its tests passed. An explicit --compact profile now scans the complete original payload for secrets before summarizing repeated long sections; the full change manifest remains intact and the original 150 KB final limit is unchanged. Its original failure and a deployment runtime-path import failure are retained. These are packet-generation failures, not hidden test passes.

## Latest post-audit operation check

At 08:57 ET, all six managed components were alive with zero supervisor restarts. Completed worker work was 1.393 seconds old; its sampled full cycle took 7.609 seconds against a 10-second budget. Since that process restart, 420 transactions recorded zero busy retries/failures and a maximum measured transaction of 32 ms. Health, root, upgrade and status HTTP routes all returned 200 in 78, 93, 329 and 140 ms respectively. This later premarket result is preserved alongside the faster earlier closed-market samples; no sustained-session reliability claim is made.

[Safe verification summary and source hashes](../TELEGRAM_VERIFICATION_2026-10-21.md). The full original test JSON, command-role results, schedule transcript, online backups, deployment patch and earlier failed runs remain local.

### Installed-source full verification

The corrected installed-source full suite passed 772 checks: 705 general Python, 7 backtesting, 4 monitoring and 56 Node, zero failures/errors/skips. The public suite has an additional portability population; totals are separate and are not added together. A public-default sharing assertion initially failed against the installed sharing=true configuration; its original installed-setting expectation was preserved and explicit false/true fixture cases remain. No live configuration was changed to satisfy a test. One targeted packet command used an incorrect class name and failed discovery; its corrected method and packet-bound tests passed. The first minification regression caught a second pretty-print serialization; both input and redacted output now use compact JSON only with the explicit profile, preserving all fields and the original hard cap.

### Completed packet and actual premarket dispatch

The final native compact packet was written successfully: `research/verification/VERIFICATION_PACKET_20261021T131532714921Z.md`, 122,425 Markdown bytes and 121,926 JSON bytes, both below the unchanged 150,000-byte limit. All 214 change-manifest entries remain; the original complete input was secret-scanned before summarization. It contains the corrected stored installed full-test result (772 passing checks), not a new claim of live data readiness. Markdown SHA-256: `9dbf978720506364f01155c20a1310b49d4c36c5f6fba233ebcff0532b51a987`. Raw installation packets stay private; the public safe summary retains source hashes and disclosed failures.

The actual scheduled October21 premarket message used `owner-compact-v1`, contained seven lines, and was accepted by Telegram at13:15:28.068Z (09:15:28ET). This is production scheduler/format/dispatch evidence, separate from the five owner-only fictional TEST messages. Scheduled research followed existing sharing preferences; no guest development tests were sent. It does not establish current option-data eligibility or phone delivery.

Final current-source public suite rerun completed at 2026-10-21T13:17:27.262483+00:00: 780 passed, zero failures/errors/skips, including the final compact serialization change. Original intermediate failed runs remain retained.

Final premarket service sample at09:19ET: all four HTTP routes returned200 in15/31/94/31ms; completed cycle6.469s against10s. This is another advancing local observation, not proof of opening-session quote quality. Legacy V5/V6 packet sections retain historical version counters and saved receipt scopes; use the current five-message owner-demo evidence above for this release.
