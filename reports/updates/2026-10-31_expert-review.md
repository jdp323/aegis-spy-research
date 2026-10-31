# AEGIS: complete technical review for independent expert assessment

**Review date:** 31 October 2026, America/New_York. **Code baseline:** `b234f6672bc20d931b9862249bcf9cbdb3fcab38`. **Purpose:** explain the deployed deterministic SPY research system, expose the mathematical rules and operational boundaries, retain unfavorable evidence, and identify what an expert can and cannot verify.

This is a source-and-evidence review, not an independent certification of security, financial suitability, predictive accuracy or profitable execution. It covers all tracked files through a machine-readable inventory and the principal production paths through the narrative below. Static coverage, tested behavior, observed operation and demonstrated trading performance are different evidence classes.

## 1. Executive verdict and evidence hierarchy

AEGIS is a locally operated SPY research and manual-review application. Its useful implemented product is a premarket brief, scheduled descriptive status, gated underlying research plans, research lifecycle updates, private user-reported fill records and a local diagnostic dashboard. It has no authorized automatic order execution. The optional neural model is not supplying verified production forecasts.

| Area | Defensible current conclusion |
|---|---|
| Deterministic strategy implementation | Implemented, versioned and covered by isolated regressions; not a profitable-strategy finding |
| Telegram product | Implemented; API acceptance and handset display are separate; delivery targets have failed in genuine sessions |
| Latest bounded correction | Final status slot now has a full current-slot window, with status expiry capped at the exchange close |
| Full regression result | 879 portable and 871 installed checks passed in their final complete runs; earlier failures are retained |
| Intraday service reliability | Not established: stale quotes, database contention and cycle overruns remain observed |
| Fresh consolidated stock data | Not established; current authorized SIP REST probe returned HTTP 403 |
| Genuine options data | Not established; current authorized OPRA snapshot probe returned HTTP 403 |
| Genuine after-cost option strategy | Not established; no qualifying historical contract/BBO evaluation result |
| Published strategy replication | Mathematical implementations exist; exact publisher-return replication is not established |
| Kronos-mini | Pinned assets and isolated infrastructure exist; actual SPY inference remains NOT_RUN |
| Personal holdings | User reports only; never broker verified or inferred from a research idea |
| Live promotion | Disabled; live/execution flags remain false and blocked action kinds remain blocked |

Evidence labels used throughout: **IMPLEMENTED** means code exists; **ISOLATED PASS** means specified tests ran with fixtures; **OBSERVED** means a dated real local/source observation; **RETROSPECTIVE** means already inspected historical development data; **PENDING/BLOCKED** means required evidence is absent. An implemented guard is not proof that every external input is correct.

## 2. Review scope, provenance and completeness limits

The reviewed baseline contains 422 tracked files, 322 program/interface/test files and 2134 indexed Python classes/functions, including nested definitions. The accompanying JSON and CSV indexes give each file's SHA-256, size, line count, symbol locations and classification. The review bundle contains a source archive of this exact Git revision. No vendor dependencies, private databases, raw licensed market data, credentials, recipient identities or personal fill records are included.

The public export is a portable distribution, not a byte-for-byte disk image of the installation. The index deliberately records both installed and public hashes where available. A separate comparison distinguishes byte-only newline/BOM differences from normalized-text differences. There are 56 raw program-file differences, of which 7 normalize to identical text; the remaining 49 are explicitly enumerated. They include runtime/private-directory resolution, fixed versus configurable bot-identity parsing, operator-facing request text, launch scripts, backup exclusions and test adaptation. These are not all asserted semantically equivalent. Both installation and portable suites were tested independently. The two October 30 changed source/test files are byte-bound to both successful suite copies; the retained integrity check covers 63 reviewed changed-source/test hashes and original-history/configuration checks, not every byte in the installation.

The deployment-profile differences are important to an expert: do not assume a portable launch wrapper, identity helper or credential location is the literal deployed form. Conversely, a newline-only difference is not a strategy-rule divergence. There was no source synchronization or production reconfiguration during this reporting task.

The evidence annex includes full historical comparison tables, the complete 14-alert audit, recorded formatter output and source/license/model notes. Some historical documents contain superseded conclusions; their dates and as-of labels remain visible. Current conclusions in this report supersede conflicting undated summaries, without modifying the historical artifacts.

## 3. Production architecture and ownership

One authoritative installation is operated by the existing current-user scheduled task and a singleton supervisor. The sanitized source export, backups, restored databases, reference archives and isolated test copies are not authorized production producers.

```text
Existing scheduled task -> singleton supervisor
  -> stream feeds: separate read-only market-data loops/connections
  -> analysis worker: gates, features, research and scheduled composition
  -> public research collector: separately labelled historical/public context
  -> Telegram listener: authentication, roles, commands and reported fills
  -> durable dispatcher/notifier: ordered per-recipient sends and reservations
  -> loopback dashboard: bounded diagnostic snapshot cache
  -> shadow worker: isolated experimental model journal, no entry authority

Market data -> validation/provenance -> completed features
             -> descriptive trend / conditional outlook
             -> independent entry, calendar, risk and option gates
             -> one primary research plan -> durable outbox -> recipient receipt

Private reported fills -> separate tenant ledgers -> private monitoring/risk
```

Only the idea-service scheduling path and atomic day scheduler create the scheduled owner-facing preopen, status and recap envelopes. Public research and the shadow worker do not have independent scheduled Telegram authority. A process named RUNNING is insufficient: PID existence, timestamped heartbeats, newly completed worker phases, a new cycle record and actual HTTP response are checked separately.

The local listener is a command/authentication service, not an immediate human or AI review guarantee. A submitted `/request` is a durable request for review. The report does not promise exit monitoring while Windows sleeps, loses power, loses network or stops the services. Source paths: [ops/supervisor.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/ops/supervisor.py), [core/upgrade_service.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/upgrade_service.py), [core/background_jobs.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/background_jobs.py), [monitoring/commands.cjs](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/commands.cjs), [monitoring/dispatch.cjs](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/dispatch.cjs).

## 4. State, ledgers and immutable price meanings

| Logical store | Role and important boundary |
|---|---|
| `runtime/aegis.sqlite` | Shared market/configuration-derived state, durable reservations, events and audit chain |
| `runtime/observability.sqlite` | Stream controls/rejections, bar confirmations, backfills, rejection traces and trend-status evidence |
| `runtime/ideas.sqlite` | Append-only underlying research snapshots and separately recorded comparisons |
| `runtime/paper.sqlite` | Separate theoretical option/legacy forward-validation records; not personal transactions |
| `options/reported.sqlite` and tenant report ledgers | Private user-reported purchases/disposals and append-only reversals |
| Model journal | Separate append-only forecast requests/results/failures and comparison evidence |
| Durable outbox, reservations and receipts | Delivery intent, uncertainty and Telegram acceptance; never a brokerage fill |

The following fields must not be collapsed: completed confirmation time; trigger level; issue/detection time; quote source time; local transport receipt; reference midpoint; modeled entry fill; Telegram acceptance; human-response delay; actual user-reported fill; exit-condition observation; modeled exit; actual reported disposal. A plan update never retroactively edits the original trigger or asserts a personal order.

SQLite uses WAL and bounded busy/locked retries in the shared store. JSON encoding is generally performed outside write transactions. Atomic history merges use compare-and-swap under a write transaction so a stream update and REST repair do not silently overwrite each other. Audit chaining and append-only triggers provide tamper-evident/append-only mechanisms within their implementation limits; they are not an external cryptographic attestation of the data provider. Source paths: [core/storage.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/storage.py), [backtesting/idea_tracker.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/backtesting/idea_tracker.py), [options/ledger.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/options/ledger.py), [core/entry_publication.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/entry_publication.py).

## 5. Market sources, access and current read-only probe

Probe captured 2026-10-31T05:39:52.671721+00:00 (2026-10-31T01:39:52.671721-04:00).

| Feed | Read-only endpoint | Observed response | Source timestamp | Request time | Meaning |
|---|---|---|---|---|---|
| IEX | /v2/stocks/SPY/quotes/latest | MARKET_ENDPOINT_RESPONSE_RECEIVED | 2026-10-30T20:32:57.785016598Z | 0.313 s | not fresh / no entry |
| SIP | /v2/stocks/SPY/quotes/latest | HTTP_403 | unavailable | 0.125 s | access refused; no entitlement proof |
| OPRA | /v1beta1/options/snapshots/SPY | HTTP_403 | unavailable | 0.141 s | access refused; no entitlement proof |

These three requests used the existing authorized credential-child mechanism and market-data endpoints only. No account, balance, order, funding or brokerage endpoint was called. The report does not reproduce the key or encrypted store. On a closed Saturday, an old but newly fetched IEX quote is expected to fail a real-time entry check; its HTTP success is access evidence only. The probe result was saved separately and did not overwrite an earlier issued probe or market cache.

The application distinguishes credentials configured, provider response, feed configuration, entitlement, source timestamp, transport receipt, quote quality and operational delivery. HTTP 403 is retained as the observed refusal; its exact commercial/account cause is not inferred from generic text. WebSocket code 409 at authentication is a separate observation, not renamed HTTP 403. An IEX connection does not establish consolidated SIP or OPRA access.

Other inputs include separately labelled public historical price research, daily context, Alpaca SPY headlines and public official/financial RSS. Their availability is independent of delay verification. Questrade has a read-only adapter but is unconfigured and has unresolved source-timestamp/Greek/IV normalization requirements. A token is not an entitlement assertion. Reddit approved OAuth credentials remain unconfigured; no anonymous scraping bypass is used.

Alpaca's official documentation differentiates basic single-exchange/indicative coverage from consolidated equities and OPRA. The exact required owner/provider action is to confirm authorized real-time SIP and OPRA access for the existing configured market-data credential, or supply an approved equivalent through a supported adapter. Do not infer a particular account subscription from this report and do not buy or change permissions automatically. Provider documentation: [Alpaca market-data capabilities](https://docs.alpaca.markets/us/docs/about-market-data-api).

## 6. Time model and strict underlying eligibility

Stored operational times are UTC; user-facing schedules use `America/New_York`. The US equity calendar is used for SPY, including verified holidays, early closes and DST. Unknown calendar years fail closed. The retained calendar implementation covers 2026 and 2027; it does not infer a 2028 session. [NYSE hours and calendars](https://www.nyse.com/markets/hours-calendars) were rechecked for this review. This exchange-page check does not renew the separate combined economic calendar.

For evaluation clock `t`, quote source `s`, receipt `r` and accepted future-skew budget `b`, the quote predicate requires valid aware timestamps, a genuine quote type, DATA_OK quality, REALTIME entitlement, finite positive noncrossed bid/ask, and:

```text
-b <= (t - s) <= 5 seconds
 0 <= (t - r) <= 5 seconds
      (s - r) <= b
```

The implementation supports a declared bounded negative source age to handle measured/accepted clock skew; it is not equivalent to an arbitrary future timestamp. The configured skew budget is included in the configuration annex. Signed ages remain signed. A receipt, heartbeat, trade, bar, reconnect or later download cannot freshen an older BBO.

The full strict underlying context additionally requires matching provider/feed provenance, usable clock state, connected stream state, a fresh stream heartbeat within 30 seconds, a completed current-session bar end within 120 seconds, and the required continuous tail. Normally 31 completed current-session minute slots are required. At most two explicitly provider-confirmed no-print slots may count for continuity only; they never become real OHLCV, volume, indicator input or fills. The explicitly limited opening view can use 15 genuine minutes during its declared early window; it does not claim a full 31-minute sample.

Completed-bar descriptive research is separate: it requires 31 genuine contiguous completed current-session bars and appropriate bar age, without requiring a current executable BBO. Thus a stale quote can block entry while a clearly labelled completed-bar trend remains available. Missing evidence is UNAVAILABLE, not SIDEWAYS. Source paths: [core/observed_context.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/observed_context.py), [core/signals.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/signals.py), [data/reliability.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/data/reliability.py), [core/research_horizons.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/research_horizons.py), [core/sessions.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/sessions.py).

## 7. Bars, indicators and causal feature construction

The normalizer rejects invalid OHLC relationships, negative volume, unordered or misaligned timestamps and incomplete/future intervals. Minute features use regular-session completed bars. Daily features exclude the current incomplete ET date. Resampling produces 5/15/30/60-minute bars only from complete aligned constituent groups with consecutive minute timestamps. Native higher-timeframe provider aggregates are explicitly labelled separately; they do not manufacture missing minute bars.

Approximate session VWAP uses volume-weighted typical price `(high + low + close) / 3`, not a trade-by-trade consolidated VWAP. EMA seeds use a simple mean of the first period and then alpha `2/(n+1)`. Declared EMA periods include 9, 20, 21, 50 and 200. RSI14 and ATR14 use recursive smoothing after an initial 14-change/true-range mean. MACD uses EMA12 minus EMA26 and an EMA9 signal. Realized volatility uses 20 log returns when available. Relative volume compares the same clock slot with prior sessions and requires at least five usable prior observations.

Swing highs/lows require two completed neighbors on each side. Therefore a swing cannot be known at its own candle close. Higher-frame BULL/BEAR alignment uses ordered price/EMA relations, not an independently calibrated model. The true opening range requires all 15 genuine 09:30-09:44 minutes, not merely that the clock has reached 09:45. No synthetic continuity slot contributes a price or volume. Source: [features/indicators.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/features/indicators.py).

## 8. Current trend: exact versioned rule

Version: `completed-vwap-change15-v2-explicit-range`. The reference is the latest eligible completed minute close `C`; `V` is approximate session VWAP; `D = C - C_15min_earlier`; `A` is minute ATR14; `R` is the highest high minus lowest low across the 16-bar/15-minute comparison window.

```text
SIDEWAYS if A > 0 and R <= 2*A and |D| <= 0.25*A and |C - V| <= 0.5*A
otherwise UP   if C > V and D > 0
otherwise DOWN if C < V and D < 0
otherwise MIXED
```

The SIDEWAYS predicate is evaluated before directional agreement. MIXED is conflicting evidence, not missing data. The last close must remain recent enough, and the required tail must be continuous. DATA UNAVAILABLE is returned if usable completed-price evidence is absent. Early limited mode remains labelled.

This is a deterministic description of completed prices. It is not a forecast probability, option-return estimate or justification to enter in the same direction. The old conflict-to-SIDEWAYS labeling and the explicit-range version were compared chronologically on a frozen diagnostic population. The diagnostic did not establish improved directional accuracy or an option edge. Full counts and dependence limits appear in the research annex. Source: [core/directional_research.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/directional_research.py).

## 9. Forward outlook, issuance and outcome accounting

The typed product view separates `PriceView`, `TrendView`, `OutlookView`, `EntryView`, `PremarketView`, `RecapView` and a named immutable plan view. The live-facing conditional H60/H120/SESSION outlook requires strict fresh underlying eligibility; a missing quote therefore abstains from the forward view without deleting eligible descriptive bars.

| Population | Registered reference and target |
|---|---|
| H60 / H120 | Fresh issue-time midpoint in the typed product view; target 60/120 minutes after issue, only if the full period fits before close |
| Remaining session | Issue-time midpoint to the stated regular-session closing reference |
| Premarket full session | Regular-session opening reference to regular-session last-minute close; currently the displayed session lean remains UNCLEAR and the corresponding directional forecast abstains |
| Premarket opening hour | Separately identified opening-hour lean, with regular open to 10:30 ET outcome; not silently called a full-day forecast |

Every issued record has an immutable ID, version, issue/availability time, source population, target, invalidation, snapshot identity, reference rule and `calibrated=false`. Queue creation is distinct from per-recipient Telegram acceptance. Abstentions and missing outcomes are retained. The stream can capture a qualifying matching-feed quote in the 0-5 second window after a target; resolution otherwise requires an exact future completed bar where supported. It does not choose a convenient nearest bar. Missing or late outcomes are not assigned zero return or success.

**Metadata limitation for expert review:** the generic nonpremarket ledger label still says `ISSUE_TIME_COMPLETED_PRICE`, while the typed market view passes a fresh midpoint as its outlook reference. The generic outcome label also does not fully describe the stream quote-resolution alternative. Numeric references, source times and actual resolution provenance must be inspected; the label alone is insufficient. This report identifies the discrepancy without rewriting issued history. Pending quote targets are bounded to 128 and summary reads to 1,000 forecast/outcome events; a complete long-history audit requires a separate controlled full-ledger extraction, not an assumption that the command summary is exhaustive.

Directional accuracy is reported with issued, abstained, resolved and missing denominators. These observations overlap within sessions and are not independent trades. Source paths: [core/market_view.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/market_view.py), [core/directional_research.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/directional_research.py), [core/idea_service.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/idea_service.py).

## 10. Premarket calculation and limits

The 09:15 report uses prepared source evidence and the post-fetch/evaluation clock. Preparation is bounded; the scheduled report cannot be replaced by a later ad hoc draft. Accepted inputs are verified authorized IEX price research or explicitly delay-unverified public historical research. Current source date, provenance, fetch age, bar alignment and completion are checked. At least six current completed 5-minute premarket bars and a sufficiently recent final completed bar are required. Complete 15/30-minute groups are built from genuine 5-minute constituents.

The implemented lean combines 15/30-minute EMA9 direction, approximate VWAP and a prior-session close proxy/gap when available. The directional gap threshold is 0.1 percent. Missing genuine volume can produce an explicitly labelled price-only context; it cannot invent VWAP/volume confirmation. The full-session lean is deliberately UNCLEAR in the current view. Premarket watch levels come from observed premarket highs/lows; an unobserved target is not fabricated.

The brief has a separate major-event line. A calendar that is unavailable cannot be rendered as no events. A premarket trend/watch is not a confirmed regular-session entry. Current formatting has eight lines, which exceeds the owner's original maximum-seven-line request; this is recorded as a remaining presentation gap, not called compliant. Sources: [monitoring/premarket_brief.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/premarket_brief.py), [monitoring/owner_messages.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/owner_messages.py), [data/premarket_authorized.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/data/premarket_authorized.py), [data/premarket_spy.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/data/premarket_spy.py).

## 11. Production underlying setup families

Active detector version: `spy-ideas-v4-full-h60`. Eight names are enabled through explicit configuration, not eight independently validated edges.

| Family | Implemented completed-candle confirmation |
|---|---|
| OPENING_RANGE_BREAKOUT / BREAKDOWN | Latest close crosses the genuine range high/low while the preceding close was on the other side |
| VWAP_RECLAIM / VWAP_REJECTION | Preceding close versus preceding session VWAP and latest close versus current VWAP cross in the proposed direction |
| TREND_CONTINUATION | 15-minute and hourly trends align; completed minute reclaims the EMA9 comparison used by this detector |
| SUPPORT_BOUNCE / RESISTANCE_REJECTION | Completed candle tests the confirmed structural level and closes back through it |
| BREAKOUT_RETEST | Preceding close is beyond the opening-range boundary; latest candle tests and rejects that boundary in the same direction |

Common requirements: at least 15 completed bars before detector evaluation; valid positive midpoint/ATR/VWAP/previous VWAP; latest close moves in the proposed direction and midpoint is on the correct side of VWAP; no two opposing higher frames among 15m/30m/1h; volume at least 1.2 times the prior-ten-minute mean, or 1.5 times the initial 15-minute baseline in early mode; fresh context supplied by the outer gate; midpoint beyond trigger and within half a minute ATR of latest close; confirmation age 0-60 seconds. Early mode allows only its declared opening-range families and configuration flag.

Production uses a **completed one-minute confirmation**. It must not be presented as a five-minute close merely because an earlier desired format used that wording. The detector's trend-continuation EMA comparison uses the current EMA for both neighboring comparisons; the separate horizon-study detector explicitly uses the preceding EMA for the preceding candle. Those are different versioned research populations. Source: [strategies/idea_setups.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/idea_setups.py), [strategies/idea_setups_v3.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/idea_setups_v3.py), [core/idea_config.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/idea_config.py).

## 12. Levels, entry expiry and holding deadlines

For directional sign `s` (+1 CALL research, -1 PUT research), midpoint reference `E`, two-bar structural extreme `S` and minute ATR `A`:

```text
risk distance d = max(|E - S|, configured_ATR_floor * A)
invalidation   = E - s*d
no-chase limit = E + s*0.5*A
```

The structural extreme is the minimum low of the last two completed bars for CALL research or maximum high for PUT research. The configured ATR floor is 0.5. T1 prefers a favorable confirmed swing at least 1R away, otherwise 1R. T2 prefers a farther swing at least 2R and beyond T1, otherwise a synthetic **rule-defined underlying level** at least 2R and one additional risk distance beyond T1. This is a transparent modeled target rule, not a market forecast or guaranteed achievable price. Minimum allowed configured reward/risk is 1.5; the current construction normally produces T2 at least 2R.

The production H60 deadline is exactly confirmation plus 60 minutes, frozen thereafter. The entire interval must fit before the verified close minus 30 minutes. Entry expires at the earliest of issue plus configured signal lifetime, confirmation plus 60 seconds, or one second before the hold deadline. Therefore the general configuration value of 600 seconds does not make this detector's confirmation valid for ten minutes. Actual entry expiry must precede the hold cutoff. On a regular day, the latest qualifying confirmation is at most 14:30 ET; on a 13:00 early close it is at most 11:30 ET, subject also to the strict inequalities and actual data.

Targets/stops can end research earlier. No confirmation already invalidated or beyond its no-chase limit is a new opportunity. The five-check 100-point display is a mandatory-check count: a qualifying detector has all five checks true, not a calibrated 100-percent chance of profit. Source: [strategies/idea_setups.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/idea_setups.py).

## 13. One primary plan and publication-time protection

`primary-plan-v2-explicit-unresolved` retains the durable `primary-research-plan:v1` key for compatibility. On restart it can adopt the earliest already-alerted active plan. Additional detections are separate observations or appropriately linked updates; they do not become an unrestricted second primary position. Historical overlapping ideas are not deleted.

States distinguish WAIT, ENTRY CONFIRMED, HOLD, EXIT CONDITION REACHED, expired/cancelled and UNRESOLVED. A gap or elapsed deadline without a verified terminal observation can leave the research plan UNRESOLVED. This does not mean the owner still owns an option. An explicitly reasoned research-only administrative cancellation can release an unresolved research control without altering the original observations, inventing P&L or changing private holdings. The retained unresolved primary is a real practical blocker for new primary entries until supported resolution or an explicit authorized administrative decision; the report does not silently clear it.

The publication guard binds a SHA-256 digest of immutable proposal fields to the registered plan. Before delivery it checks binding/version, current registered state, session, fresh underlying, calendar, confirmation age, full horizon, entry expiry, holding cutoff, trigger direction, no-chase limit, invalidation/target already reached and any included verified option reference. Current prices can invalidate a previously valid proposal. It is a refusal path, never a mechanism to authorize live trading.

Sources: [core/primary_plan.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/primary_plan.py), [core/entry_publication.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/entry_publication.py), [ops/entry_check.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/ops/entry_check.py), [monitoring/notifier.cjs](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/notifier.cjs).

## 14. Three separate risk-control populations

**Strategy deterioration:** deterministic `research-loss-episodes-v2` consumes each closed underlying observation ID once, including silent research, because it measures research behavior. Three consecutive qualifying negative R outcomes create a fixed 60-minute episode with cause IDs, explicit start/end and one initial warning. Closed observations during the active episode are consumed but do not extend that same episode. Once expired, a new qualifying sequence is required. Restart persistence depends on durable seen IDs/state. Silent losses are never described as personal trading losses.

**Alert stream:** same-direction/same-setup detections within ten minutes and within half an ATR of the previous trigger can be suppressed. There is a daily runaway safety breaker of 40 alerts; configured daily cap is otherwise null. Setup evidence is computed from closed underlying research; fewer than 50 observations is INSUFFICIENT DATA. At larger counts a heuristic t interval can mark POSITIVE, NEGATIVE or UNCLEAR. These correlated-observation intervals are not independent validation. A negative setup can be deliberately overridden through authorized configuration; no override is applied in this review.

**Private actual-position risk:** separate USD limits and dated reconciliation operate on reported records. Live owner confirmation is independently required and remains false. The software cannot establish actual available funds, broker equity, fills, settlement or current realized loss merely from a configuration marker. The current configured paper limits are shown later; they are not a live account balance or permission to risk that sum.

Trends, scheduled status and eligible educational watch context remain independent of a research-entry pause. Source: [core/research_pause.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/research_pause.py), [core/idea_service.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/idea_service.py), [backtesting/idea_tracker.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/backtesting/idea_tracker.py), [risk/options_policy.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/risk/options_policy.py).

## 15. Genuine option selection: hard gates and remaining gaps

The research selector parses actual standard SPY OCC contracts, matching right/strike/expiry and a 100 multiplier. It checks DTE, bid/ask quality, spread, volume, OI, finite Greeks and positive IV. Ordinary selector limits include spread no more than 12 percent, volume/OI at least 100, DTE within 30 and at least configured minimum DTE. Separate zero-DTE branches have stricter spread/liquidity/time/volatility requirements; default minimum DTE is one and these branches are not a production readiness claim.

The ranking formula is a heuristic preference for spread, delta proximity, carry, moneyness, liquidity and IV. Expected move `spot * IV * sqrt(years)` is a rough comparison scale, not an executable price or probability. A ranking score cannot override missing chain terms or entitlement. Neighboring same-expiry strikes are checked for missing/crossed/inconsistent prices.

The final `verified-bbo-reference-v1` gate is stricter than a selector preview: a quote must pass the five-second reference check, Greeks must be timestamped within 60 seconds, volume/OI must meet minimums, right and quoted fields must match, chain sanity must pass, expiry date must be strictly after the holding deadline's ET date, and cost must fit the configured paper premium budget. Questrade's looser low-level quote support cannot bypass this final gate.

If verified, the reference limit is the actual ask; estimated entry cost is `100 * ask + entry fee`; premium at risk is `100 * ask`, with fees labelled separately. A limit fill is not assumed. No option-dollar stop loss is inferred from a SPY stop. Without a genuine verified contract the output remains **Underlying watch only - option contract unavailable**. No fixed-delta/theta estimate qualifies an option plan or after-cost outcome.

Sources: [options/contract_selector.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/options/contract_selector.py), [options/chain_sanity.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/options/chain_sanity.py), [options/research_contract.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/options/research_contract.py), [options/trade_plan.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/options/trade_plan.py), [core/signals.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/signals.py).

## 16. Legacy evaluation and inactive historical modules

The legacy weighted rubric in `core/signals.py` is distinct from the current five-check idea count. Its maximum components are structure 20, trend 15, relative volume 10, VWAP 15, MACD 10, contract 10, news 10 and reward/risk 10. Missing inputs leave a component/score unavailable. The threshold is 75, but hard rejection, unvalidated-strategy and live-false fields remain independently enforced. A high score does not waive a single data/risk requirement.

The repository also retains earlier CAD first-cycle risk calculators, TSX calendar/status code and proposal machinery. They are historical/advanced code, not the authoritative SPY calendar or options risk limits. In particular, `app.py status/review` can invoke the legacy local snapshot path; the active HTTP `/api/status` instead serves SPY research, and `/api/upgrade` serves the current dashboard. No legacy account snapshot or balance file was inspected for this review. An expert should audit reachability before reusing old CLIs. File presence is not active-service authority.

Sources: [core/signals.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/signals.py), [core/service.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/service.py), [risk/first_cycle.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/risk/first_cycle.py), [app.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/app.py), [core/spy_research.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/spy_research.py).

## 17. Genuine option replay and preregistered research

The option dataset loader requires actual point-in-time chain/BBO components, hashes, explicit currency/premium/size units, provider/feed provenance, ordered timestamps, listed terms and an independently reviewed source receipt pinned into the study protocol. The current trusted-receipt list is empty. A self-authored manifest claiming OPRA is not enough. Missing, indicative, delayed, synthetic or unverified inputs fail closed; synthetic fixtures are separately tagged.

At delayed entry, the selected contract must still independently qualify, have a genuine sized bid/ask and respect the entry deadline and limit. Modeled entry is ask plus scenario slippage; modeled exit is bid minus slippage after the observed exit event and response delay. For one contract, net dollars equal `(exit_bid - exit_slippage - entry_ask - entry_slippage) * 100 - both fees`. Missing exits leave capital reserved and outcome unresolved. A touched limit on a bar does not prove a fill. The code's default offline limit buffer is an explicitly modeled assumption, not a live order. Total debit/premium-at-risk labels differ slightly across replay and displayed contract-reference records; the expert should distinguish premium-only risk from fee-inclusive debit.

`spy-horizon-study-v2` is separate from the 27-trial historical Concretum comparison: 2 families x 3 horizons x 2 ATR floors = 12 trials; 3 response delays (0/15/60 seconds) x 2 per-side slippages (0.01/0.03 dollars per share), with 0.65 dollars per contract per side, yields 72 scenarios. Its research-only cash is 10,000 dollars, maximum open premium 1,500 dollars, one contract per idea, no borrowing; these are simulation parameters, not personal funding.

The planned chronological split is 20 development / 10 validation / 20 sealed-final verified sessions, with outcome windows purged across boundaries. Selection is frozen before final access. Previously reviewed dates cannot be retagged untouched. Acceptance requires at least 100 closed genuine-option observations, at least 20 final/uncertainty days, simultaneous lower bounds above zero for expectancy and paired baseline difference, missing outcomes at most 5 percent, no single day's share of positive P&L above 25 percent, and adverse execution scenarios passing. These are future research requirements, not achieved results or live authorization. Day-block uncertainty and multiple-trial adjustment do not remove dataset bias or guarantee future performance.

Sources: [backtesting/research_protocol.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/backtesting/research_protocol.py), [backtesting/option_research.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/backtesting/option_research.py), [core/research_horizons.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/research_horizons.py).

## 18. Published strategy baselines and exactness

The Concretum September 2025 paper studies abnormal intraday moves relative to prior same-clock behavior, with separate exit/sizing treatments. AEGIS implements the mathematical description independently; it does not import or redistribute publisher code. No broad permissive publisher-code license was established. The linked original paper and article are research references, not a claim that advertised returns were replicated. [Original paper](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf), [author's Python article](https://concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/).

In the AEGIS paper-rule module, same-clock sigma is the mean of 14 prior complete sessions' absolute `close_at_clock / session_open - 1`. Upper/lower bands use the maximum/minimum of today's open and dividend-adjusted prior close, multiplied by `1 + sigma` / `1 - sigma`. Decisions and stops are evaluated on 30-minute clocks, with opposite-band and current-band/VWAP variants distinguished. Optional sizing implements a 14-return volatility target and four-times ceiling as a mathematical calculator; it is not borrowing authorization. The actual comparison replay is one-share delayed-minute-open research with explicit costs, so it is not an exact funded publisher portfolio. The older article diagnostic permits a 13-observation warmup and is separately labelled. Missing dividend coverage remains unavailable.

QuantRocket's tutorial uses first-half-hour return including overnight and penultimate-half-hour direction, with a VIX-20 filtered form and final-half-hour exposure. The AEGIS implementation includes an unfiltered diagnostic and a VIX-required branch; missing contemporaneous VIX makes the filtered branch unavailable. Completed-input evaluation imposes an explicit delay adaptation. No exact publisher backtest or complete VIX study is established. A repository-root LICENSE retrieval returned 404 during review; no permissive code reuse is assumed. [Official tutorial](https://www.quantrocket.com/codeload/first-last/first_last/Introduction.ipynb.html), [code explanation](https://www.quantrocket.com/codeload/first-last/first_last/Part2-Moonshot-Backtest.ipynb.html), [VIX treatment](https://www.quantrocket.com/codeload/first-last/first_last/Part5-Moonshot-Backtest-With-VIX-Filter.ipynb.html).

Lumibot's current example describes an AI-assisted multi-symbol opening-range workflow. AEGIS's baseline is only an independently written SPY long-ORB mathematical adaptation: genuine first-15-minute high/low, range-low stop and a 1.5R target. It does not reproduce AI ranking, multi-stock selection, account-percent sizing or execution. The upstream Lumibot repository LICENSE currently states GPLv3; no upstream code/assets were copied here. [Official example](https://lumibot.lumiwealth.com/agents_example_opening_range_breakout_ai_trading_bot.html), [upstream license](https://raw.githubusercontent.com/Lumiwealth/lumibot/master/LICENSE).

The full frozen historical comparison, all displayed cells and exclusions appear in Annex A. A successful historical SIP download does not establish current SIP permission. Incomplete dividends, small independent-day counts, overlap, cost assumptions, warmup and inspected periods prevent a strategy-superiority claim. Sources: [strategies/concretum.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/concretum.py), [strategies/published_baselines.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/published_baselines.py), [ops/primary_comparison.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/ops/primary_comparison.py).

## 19. The October 21 fourteen-alert cohort

The complete audit is reproduced in Annex B, including each original research ID, direction, recovered confirmation, issue/acceptance time, reference, stop distance, target levels, first touches, delayed minute-open proxy and overlap count. All 14 confirmations match the original immutable identity. The cohort recorded 12 invalidations and two T2 hits. A broader recap counted a different 37-observation population; its stop count cannot be substituted for the alerted cohort.

Tight stops, response delays and overlapping detections are observed features of that cohort. A later favorable price after an earlier stop does not undo the earlier invalidation. Some delayed proxies are already invalidated or outside no-chase limits. Actual first executable entry and genuine option fills cannot be recovered without corresponding BBO/trade evidence. Minute OHLC is not an intraminute event tape.

Five frozen stop alternatives across three response assumptions produced 210 sensitivity evaluations. No parameter was chosen to rescue that day and no original stop/target/history was rewritten. A one-primary replay retained six initial research plans and left eight overlapping detections separate; that is a delivery-policy comparison, not proof of improved financial results. October 21 and every inspected historical period remain development evidence.

## 20. News, economic calendar and Reddit

News context combines available Alpaca SPY headlines with official Fed policy/speeches, BLS, BEA and CNBC RSS. Text is treated as untrusted data, never instructions. Language rules require an explicit market subject and directional reaction; negated, conditional, sarcastic or conflicting wording stays neutral/unclear. Macro numbers are not called a positive/negative surprise without verified expectations. Topic counts and directional text shares are not calibrated move probabilities, causal attribution or a complete upcoming-event calendar. Missing source availability is not neutral sentiment.

The economic calendar validates official HTTPS hosts, duplicate IDs, supported event types, aware UTC/ET consistency and bounded blackout windows. HIGH date-only events produce explicit all-day ET blackouts, including DST-length days; no announcement time is invented. Last-good source content and failures are preserved when direct/ICS requests return 403. The snapshot's seven-day verification age is independent of its coverage-through date.

| Field | Retained value |
|---|---|
| verified_at | 2026-10-28T13:32:27+00:00 |
| freshness_expires_at | 2026-11-04T13:32:27+00:00 |
| coverage_from | 2026-10-28T13:34:59.409050+00:00 |
| coverage_through | 2026-12-05T04:59:59+00:00 |
| coverage_complete | True |
| event_count | 46 |
| date_only_event_count | 2 |

Freshness expiry in ET: 2026-11-04T08:32:27-05:00.

No calendar freshness was renewed during this review. The owner warning policy is three days before expiry; the exact fresh issuer inputs must be obtained before a genuine renewal. Unknown optional categories are not asserted absent. Current-read RSS quality/fetch metadata is availability evidence only; source publication time and delivery delay need separate checks.

Reddit's bounded read-only OAuth adapter can score top posts/comments only when approved credentials exist. It is unconfigured in the current system. No raw Reddit author/text archive, training or scraping bypass is permitted, and Reddit cannot override the price/news bias. Sources: [news/market_outlook.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/news/market_outlook.py), [news/engine.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/news/engine.py), [news/calendar_updater.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/news/calendar_updater.py), [news/reddit.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/news/reddit.py).

## 21. Telegram commands, schedule and message contract

The actual registry contains 36 typed commands; the current main menu is `/trend /score /demo /news /more /help`. All retained advanced tools remain discoverable. `/details` is a first-class command, not only an undocumented alias. Owner administrative routes are separate from guest-visible routes. An authentication role check is not substituted by a destination string alone.

| Command | Arguments | Purpose | Role |
|---|---|---|---|
| /help | [all] | Useful commands; all shows advanced tools | Authenticated role/tenant checks apply |
| /howto | (none) | Quick guide to trend, morning outlook and news | Authenticated role/tenant checks apply |
| /join | INVITATION_CODE | Join using a one-use invitation | Authenticated role/tenant checks apply |
| /users | [PAGE_NUMBER] | Owner only: names, usernames, IDs and activity | Owner admin |
| /invite | (none) | Owner only: create a 24-hour one-use invitation | Owner admin |
| /revoke | ACCESS_ID | Owner only: revoke a guest’s access | Owner admin |
| /leave | (none) | Guest: disable your own access; records retained | Authenticated role/tenant checks apply |
| /start | (none) | Show help and getting-started commands | Authenticated role/tenant checks apply |
| /status | (none) | SPY research readiness and schedule | Authenticated role/tenant checks apply |
| /feed | (none) | Provider, connection and freshness health | Authenticated role/tenant checks apply |
| /health | (none) | Service health and official calendar coverage/staleness | Authenticated role/tenant checks apply |
| /void | EVENT_ID | Append reversal of your own fill report; preserve history | Authenticated role/tenant checks apply |
| /trend | [details] | Short gated SPY trend and research idea | Authenticated role/tenant checks apply |
| /details | (none) | Horizon, source-time and entry-gate diagnostics | Authenticated role/tenant checks apply |
| /why | (none) | Exact checks behind the current verdict | Authenticated role/tenant checks apply |
| /score | (none) | Underlying idea outcomes: today, 7 days, 30 days and each setup | Authenticated role/tenant checks apply |
| /fill | quantity&#124;premium&#124;fees&#124;time&#124;confirm&#124;cancel VALUE | Answer the current actual-fill question; never submits orders | Authenticated role/tenant checks apply |
| /more | (none) | All tools, grouped by purpose | Authenticated role/tenant checks apply |
| /alerts | [CATEGORY on&#124;off &#124; setup NAME on&#124;off &#124; silent on&#124;off] | Owner only: categories, setups and silent trends | Owner admin |
| /outlook | (none) | Clear SPY bias combining price trend and financial news | Authenticated role/tenant checks apply |
| /sentiment | (none) | Wallstreetbets top-post/comment sentiment and access status | Authenticated role/tenant checks apply |
| /research | (none) | Advanced saved technical research and data limits | Authenticated role/tenant checks apply |
| /signals | (none) | Recent research evaluations and rejections | Authenticated role/tenant checks apply |
| /setup | (none) | Latest call/put plan evaluation and exact blockers | Authenticated role/tenant checks apply |
| /learn | (none) | Measured trend outcomes and improvement comparison | Authenticated role/tenant checks apply |
| /forecast | (none) | Experimental closing-area estimate and limitations | Authenticated role/tenant checks apply |
| /premarket | (none) | 09:15 ET saved outlook, schedule or separate premarket draft | Authenticated role/tenant checks apply |
| /paper | (none) | Separate theoretical trade records | Authenticated role/tenant checks apply |
| /plan | OCC_SYMBOL INVALIDATION T1 T2 MAX_HOLD_MINUTES | Your holding: SPY-price review conditions | Authenticated role/tenant checks apply |
| /news | (none) | Financial news drivers, direction and source links | Authenticated role/tenant checks apply |
| /request | YOUR MESSAGE | Queue research, feedback or a correction | Authenticated role/tenant checks apply |
| /demo | start&#124;bought&#124;status&#124;exit&#124;sold&#124;skipped&#124;stop | Interactive fictional walkthrough | Authenticated role/tenant checks apply |
| /option_bought | OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME [FORCE] | Report actual fill; exact duplicates require FORCE | Authenticated role/tenant checks apply |
| /option_sold | OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME [FORCE] | Report actual disposal; exact duplicates require FORCE | Authenticated role/tenant checks apply |
| /option_positions | (none) | Show your reported SPY option positions | Authenticated role/tenant checks apply |
| /skipped | IDEA-ID | Report that you did not buy an idea | Authenticated role/tenant checks apply |

| Job | Verified ordinary-session ET schedule |
|---|---|
| Prepared morning brief | 09:15, bounded five-minute catch-up; once per trading day |
| Owner self-check | 09:20 |
| Silent status | Every 15 minutes, 09:45 through 15:45; 25 logical slots; never change-only throttled |
| Qualifying experimental research | Event-driven, with strict publication revalidation and one primary plan |
| Recap | Close plus 15 minutes, normally 16:15 |
| Local session report | Close plus 20 minutes, normally 16:20 |

Early-close times derive from the verified exchange close. The October 30 fix gives the final status the same current 15-minute window as earlier slots and caps status expiry at the earlier of five minutes or exchange close. Existing reservations/uncertain sends are not retried blindly. A status emitted late within that window still fails the 30-second timing target.

Durable recipient reservations, expiry checks, initial-before-dependent ordering and explicit uncertainty states govern sending. A definitive Telegram rejection is different from an uncertain-after-send outcome. Telegram acceptance does not mean phone display; the owner's separate confirmation of the earlier five fictional demo messages supports only that particular demo. No new Telegram demo/test was sent for this report.

| Requested message limit | Current actual production construction | Assessment |
|---|---|---|
| Premarket maximum 7 lines | 8 lines | Remaining presentation mismatch |
| Status maximum 5 lines | 5 normally; 6 with active-plan monitoring warning | Exception exceeds requested cap; warning is meaningful but not cap-compliant |
| Opportunity maximum 9 lines | 9 lines for a nonexpired ordinary plan | Meets that structural limit; content remains gated research |
| Recap maximum 6 lines | 8 lines | Remaining presentation mismatch |
| Changes linked to original idea | Short ID-linked change/update | Implemented; no personal fill or sale assertion |

Current production uses a one-minute confirmation and appropriately prints that fact. The report does not hide this discrepancy from the earlier fictional five-minute-format example. Actual retained formatter output and full-day fake-dispatch details appear in Annex C. Sources: [monitoring/command_registry.cjs](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/command_registry.cjs), [monitoring/owner_messages.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/owner_messages.py), [monitoring/day_schedule.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/day_schedule.py), [monitoring/notifier.cjs](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/notifier.cjs).

## 22. Privacy, fills, roles and execution

Actual fill reports require standard SPY OCC symbols, integer contracts, USD premium per share, total fees and an aware past fill time. Exact duplicates require explicit FORCE for a genuinely separate fill; VOID appends a reversal rather than deleting history. Purchases/disposals are private to the correct tenant. A skipped idea creates no holding. Reported quantities, fees and timestamps are not broker reconciliation.

Owner-only invitations/revocations and per-role routes remain distinct. Shared research follows existing sharing preferences; private actual fills, monitoring incidents, requests and administrative details must not become guest development messages. Sender/callback identity, private-chat binding, age and replay checks exist. The portable and installed identity implementations have profile-specific differences listed in the source index; this is not a formal complete security proof.

No path in this report invokes orders, transfers, borrowing, paid subscriptions, account/balance endpoints or external permission changes. The application maintains `live_signal_enabled=false`, `order_execution_enabled=false`, `LIVE_SIGNAL_READY=false` and blocks BUY/SELL/TRADE_PROPOSAL action kinds. It must not route an unsupported actionable recommendation through a harmless-looking RESEARCH/INFO label. Existing option expiry is never interpreted as automatic settlement, exercise or disposal.

## 23. Model and supplied-reference assessment

Kronos is an optional shadow research challenger, not the source of current deterministic eligibility. The reviewed local assets pin the mini model/tokenizer revisions and hashes; upstream training-data overlap with SPY and evaluated dates is unknown. Individual sampled paths are not forecast probabilities. Actual mini inference is NOT_RUN: the retained preflight measured insufficient free memory against the 1,536 MiB headroom requirement on this 2 GiB host. No neural accuracy, latency or option-profit result exists.

The implemented child containment uses a separate environment/process, offline assets, one computational thread, a 45-second wall deadline, 768 MiB memory bound and secret-free environment. Fixture timeout/crash/memory/malformed/oversized-output tests demonstrate those fixture paths, not the actual mini model's production reliability. The comparison journal records availability after actual completion and keeps missing/failed outputs. Future-only outcomes, no-change baseline, earlier-session time-of-day baseline and deterministic comparator remain separate; no point forecast is invented for a direction-only rule.

The user-supplied Day Trader, Kronos and OpenStock archives were treated as reference data, not instructions or installed skills. Static upstream tests are not counted as AEGIS-executed passes. Day Trader/Kronos MIT and OpenStock AGPL-3.0 findings, exact archive hashes, pinning and what was/was not reused appear in Annex D. No OpenStock protected assets or Day Trader broker/accounting code was imported. No AI API key is needed for the rule-based product.

## 24. Operational reliability and genuine-session results

| Session | Owner status acceptances | Within 30 seconds | Applicable underlying gate evidence | Overall result |
|---|---:|---:|---|---|
| Oct 27 | 25/25 | 9/25 | 20/25 data targets failed | FAILED |
| Oct 28 | 25/25 | 9/25 | 0/25 passing | FAILED |
| Oct 29 | 25/25 | 14/25 | 0/25 passing | FAILED |
| Oct 30 | 24/25 | 3/25 | 6/25 passing applicable underlying predicates | FAILED |

These are small, changing operational cohorts, not a controlled trend in strategy profitability. Missing status and failed gates remain in denominators. No accepted qualifying entries supplied an entry-latency population in the October 30 master report; null percentiles mean NO_SAMPLE, not PASS. The original October 30 coverage report is WARN: 389 genuine minutes, 62 backfilled/REST-origin rows, no confirmed no-print slots and one missing minute out of 390. Coverage reconstructed later does not establish what the bot had at the original decision time.

The October 28 dashboard HIGH-calendar TypeError was corrected. The October 29 bounded stream-control policy distinguishes a finite provider permission retry from a hung attempt, with separate attempt-start metadata. It honors bounded declared waits and 40/90-second connection phases without turning control progress into market freshness. The October 30 correction addressed the actual last-slot recovery bug after a SQLITE_BUSY failure. None of these fixes is claimed to solve all worker contention or upstream/source delay.

Shared-store bounded retry counts and maximum durations still rise during problematic sessions. The October 30 pre-maintenance sample recorded 1,434 retries and 135 failed operations. A new process resets counters, so the later one-retry/zero-failure sample cannot erase that day. The private phase diagnostic found lengthy idea scheduling, legacy analysis and underlying-paper review phases. Its elapsed durations include host scheduling, reads, writes and subordinate work; the lock holder and causal share are not established.

An isolated paper-database query initially looked faster with an index (3.879 versus 0.383 seconds), but counterbalanced warm measurements were 0.411/0.431/0.491/0.601 seconds. The claimed large improvement disappeared; no speculative index was deployed. Existing `ingest_processing_ms` is recorded before final cache commit and future-quote capture, so it is not full end-to-end ingest latency. Source-to-receipt intervals also cannot distinguish provider/network delay from internally queued socket processing. These instrumentation limits matter when diagnosing stale output.

## 25. Latest actual operation, separated from session acceptance

| Observation | As-of measured value |
|---|---|
| Snapshot UTC / ET | 2026-10-31T05:36:39.872720+00:00 / 2026-10-31T01:36:39.872720-04:00 |
| Components with existing live PIDs | 7/7 |
| Supervisor heartbeat age | 0.633 s |
| Listener heartbeat age | 31.762 s; exact age retained, not assumed timely |
| Dispatcher heartbeat age | 4.747 s |
| Worker last completed | 2026-10-31T05:36:29.212865+00:00 |
| Sampled whole cycle | 132.34399999980815 s; budget 10 s; missed=True |
| Current process database counters | 1 busy retries / 0 failures; counters reset at restart |
| HTTP health | 200; responsiveness only |
| Cached IEX source age | 34632.947206 s; closed session, fails strict entry check |
| Fresh read-only option access probe | 2026-10-31T05:39:52.671721+00:00; OPRA HTTP_403 |
| Current primary research state | UNRESOLVED; not a personal holding |
| Review-only source/probe effects | No production source/configuration/service/send changes |

This snapshot was taken on a closed Saturday. A fresh process heartbeat or successful health response is liveness evidence only. In particular the new sampled cycle is over the unchanged ten-second cycle budget; it must not be replaced in the report by a favorable after-close sample. The earlier verified post-restart cycle of 5.938 seconds and four populated HTTP 200 views remain bounded historical observations, not sustained reliability proof. The initial cold response was a data-unavailable refresh and old STOPPED cycle records were not counted as new work.

The delayed stored IEX quote is not interpreted as a Saturday entry opportunity or a new market-hours outage. The report does not infer why the host was slow. The listener heartbeat's exact signed age is retained; a RUNNING label does not waive its timestamp. No new pending-request or personal-position details are disclosed. Periodic reviews are separate from continuous exit coverage.

## 26. Verification, retained failures and backups

The last source-changing deployment's final complete isolated results are 807 main Python + 7 backtesting + 4 monitoring + 61 Node = **879 portable**, and 800 main Python + 7 backtesting + 4 monitoring + 60 Node = **871 installed**, with no final failures/errors/skips. Packaging/runtime-profile tests explain the different totals; they are not silently merged into one number. The 31 targeted scheduler/preopen/primary-delivery checks also passed. Both changed files match both successful isolated copies.

Retained failed attempts include nine failures/subtests across the initial eleven last-slot tests; two later close-expiry failing subtests; one targeted-launcher import-path error; a first full portable run with 22 missing-dependency errors from the wrong environment; and a subsequent full run with a receipt-observer elapsed-time failure of 0.235 seconds against its unchanged 0.2-second limit. The final complete rerun passed after backup work finished. That sequence does not prove the sole cause of the timing failure, and no assertion/freshness limit was weakened. Actual mini-model inference is explicitly unexecuted, not counted as a skipped passing test.

Before the latest source deployment, seven SQLite online backups included committed WAL data, passed full integrity checks and were restored/count-checked in separate inert copies. The telemetry database's complete copy/integrity/restore/verification work took about 814.8 seconds, not a market-worker latency measurement. No backup was restored over newer live ledgers. Source/configuration and issued-report preimages were retained, the existing limited task's XML was unchanged, and the same task restarted the one service group. Original Oct 22 packet and private-history prefixes passed the integrity review.

For this reporting task, no complete suite, strategy backtest or model inference was rerun; no service, sharing preference, source gate, permission or trading state was changed. Read-only operational checks, source inventory, primary-source browsing, three approved market-data probes and document rendering/QA are new evidence. See Annex E for the exact verification categories and reproducibility paths.

## 27. Current parameter profile

| Installed parameter or effective default | As-of value |
|---|---|
| schema_version | 1 |
| symbols | ["SPY"] |
| primary_provider | "alpaca" |
| secondary_provider | "UNCONFIGURED" |
| price_poll_seconds | 45 |
| high_volatility_seconds | 10 |
| option_poll_seconds | 45 |
| chain_refresh_seconds | 300 |
| bars_refresh_seconds | 60 |
| daily_refresh_seconds | 21600 |
| analysis_seconds | 60 |
| closed_poll_seconds | 1800 |
| actionable_threshold | 75 |
| min_dte | 1 |
| max_contract_subscriptions | 30 |
| premarket_report.enabled | true |
| premarket_report.lead_minutes | 15 |
| premarket_report.catchup_minutes | 5 |
| paper_slippage_per_share | "0.01" |
| paper_fee_per_contract | "0.65" |
| live_signal_enabled | false |
| order_execution_enabled | false |
| options_risk_live_confirmed | false |
| allow_unvalidated_paper_trading | true |
| signal_expiry_seconds | 600 |
| paper_daily_message_cap | 8 |
| signals.shared | true |
| proxy_paper.enabled | true |
| proxy_paper.mode | "UNDERLYING_PROXY_ONLY" |
| proxy_paper.quantity | 1 |
| proxy_paper.slippage_per_share | 0.01 |
| proxy_paper.max_holding_minutes | 60 |
| proxy_paper.max_open_positions | 1 |
| proxy_paper.max_risk_per_share_usd | 5.0 |
| max_future_skew_seconds | 2.0 |
| option_data_provider | "questrade" |
| price_mismatch_tolerance.percent | 0.1 |
| price_mismatch_tolerance.usd | 0.5 |
| buy_limit_buffer.usd | 0.1 |
| buy_limit_buffer.percent | 4.0 |
| horizons.scalp_minutes | 60 |
| horizons.intraday_exit_minutes_before_close | 30 |
| horizons.swing_days | 3 |
| horizons.swing_enabled | false |
| notifications.profile | "simple" |
| notifications.categories.ideas | true |
| notifications.categories.idea_updates | true |
| notifications.categories.morning | true |
| notifications.categories.system | true |
| notifications.categories.periodic | false |
| notifications.categories.changes | false |
| notifications.categories.extended | false |
| notifications.categories.news | false |
| notifications.categories.sentiment | false |
| notifications.categories.trend_lines | true |
| idea_engine_enabled | true |
| trend_lines_silent | true |
| idea_daily_cap | null |
| idea_cooldown_minutes | 10 |
| cooloff_minutes | 60 |
| cooloff_losses | 3 |
| min_rr | 1.5 |
| early_session_ideas | true |
| rough_risk_delta_range | [0.4, 0.6] |
| premium_cap_mode | "warn" |
| report_time | "09:15" |
| recap_time | "16:15" |
| idea_runaway_limit | 40 |
| idea_stop_atr_fraction | 0.5 |
| setup_enabled.OPENING_RANGE_BREAKOUT | true |
| setup_enabled.OPENING_RANGE_BREAKDOWN | true |
| setup_enabled.VWAP_RECLAIM | true |
| setup_enabled.VWAP_REJECTION | true |
| setup_enabled.TREND_CONTINUATION | true |
| setup_enabled.SUPPORT_BOUNCE | true |
| setup_enabled.RESISTANCE_REJECTION | true |
| setup_enabled.BREAKOUT_RETEST | true |
| negative_setup_overrides | [] |
| require_chain_sanity | true |
| options_risk.max_trade_premium_usd | 500.0 |
| options_risk.max_exposure_usd | 1500.0 |
| options_risk.max_daily_loss_usd | 300.0 |
| options_risk.max_consecutive_losses | 3 |
| effective_idea_defaults.idea_engine_enabled | true |
| effective_idea_defaults.trend_lines_silent | true |
| effective_idea_defaults.idea_daily_cap | null |
| effective_idea_defaults.idea_cooldown_minutes | 10 |
| effective_idea_defaults.cooloff_minutes | 60 |
| effective_idea_defaults.cooloff_losses | 3 |
| effective_idea_defaults.min_rr | 1.5 |
| effective_idea_defaults.early_session_ideas | true |
| effective_idea_defaults.rough_risk_delta_range | [0.4, 0.6] |
| effective_idea_defaults.premium_cap_mode | "warn" |
| effective_idea_defaults.report_time | "09:15" |
| effective_idea_defaults.recap_time | "16:15" |
| effective_idea_defaults.idea_runaway_limit | 40 |
| effective_idea_defaults.idea_stop_atr_fraction | 0.5 |
| effective_idea_defaults.setup_enabled.OPENING_RANGE_BREAKOUT | true |
| effective_idea_defaults.setup_enabled.OPENING_RANGE_BREAKDOWN | true |
| effective_idea_defaults.setup_enabled.VWAP_RECLAIM | true |
| effective_idea_defaults.setup_enabled.VWAP_REJECTION | true |
| effective_idea_defaults.setup_enabled.TREND_CONTINUATION | true |
| effective_idea_defaults.setup_enabled.SUPPORT_BOUNCE | true |
| effective_idea_defaults.setup_enabled.RESISTANCE_REJECTION | true |
| effective_idea_defaults.setup_enabled.BREAKOUT_RETEST | true |

The table is generated from the installed configuration allowlist and effective idea defaults, not copied from public defaults. In particular the portable sample risk values differ from installed paper limits. Neither profile is a broker balance, portfolio entitlement or owner-confirmed live risk budget. Credential locations, URLs containing secrets, identity/access records and actual loss/fill state are omitted.

## 28. Findings register and precise remaining work

| Priority | Finding | What would resolve it |
|---|---|---|
| P0 | Genuine-option data and profitability are unestablished | Authorized current and point-in-time historical chain/BBO with audited provenance; complete after-cost chronological research; no automatic live promotion |
| P1 | Intraday source freshness and worker timing targets failed | Attribute source/receipt/queue/commit timing and writer lock waits; reproduce and fix measured causes; observe genuine future sessions |
| P1 | Existing primary research control can remain UNRESOLVED | Verify supported terminal evidence or explicitly authorize a research-only administrative cancellation; never infer a personal sale |
| P1 | Current report snapshot includes a 132.344-second closed-session cycle | Investigate actual phase/subphase timing and host continuity; do not select favorable samples as recovery proof |
| P1 | Three consecutive real-session engineering acceptance targets remain unfulfilled | Prospective observation with full denominators, original timestamps, missing entries/statuses and adverse states retained |
| P2 | Final-slot scheduling fix has no subsequent genuine-session observation yet | Verify the next actual ordinary/early-close final slot and its recipient receipt; no retrospective replay |
| P2 | Premarket/recap and warning status exceed original line limits | Agree and implement concise production templates with actual formatter/dispatcher regressions, preserving required safety context |
| P2 | Requested five-minute example differs from actual one-minute production confirmation | Treat current rule accurately; any timeframe change is a new version and study, not a wording substitution |
| P2 | Forecast ledger generic reference/outcome labels underdescribe typed midpoint and quote capture | Add explicit schema/versioned reference and outcome instrument fields; preserve issued records and compare cohorts separately |
| P2 | Portable/installed profile differences are broader than two latest edited files | Use both hash profiles, inspect normalized differences, and avoid blanket source-equivalence or drop-in-deployment claims |
| P2 | Exact Concretum replication lacks complete dividend/ex-date and full matching data | Obtain audited coverage and maintain paper/article/execution-adaptation distinctions |
| P2 | Filtered first/last and Lumibot-equivalent studies are not complete replications | Obtain genuine contemporaneous VIX and required chronology; reproduce exact rules before comparing advertisements |
| P2 | Model assets exist without actual mini SPY inference | Adequate verified resources, isolated installed environment and genuine benchmark/prospective outputs; no resource-guard bypass |
| P2 | Legacy CAD/TSX CLIs remain in the tree | Audit reachability and document/deprecate separately; do not use them as current SPY/account status |
| P2 | Calendar expires at its genuine seven-day boundary | Refresh official issuer inputs with retained failures; coverage-through December does not extend freshness |

No particular trading strategy is recommended as a winner. Additional indicators, looser stops, wider freshness limits or disabling risk controls are not substitutes for resolving these evidence gaps.

## 29. Independent expert verification sequence

1. Verify the code revision and tree hash in the index; compare the supplied source archive and SHA manifest. Inspect normalized installed/export differences, not only Git status.
2. Trace the live process entry points and singleton scheduled authority. Use new timestamps and completed work; distinguish legacy code, disabled features and fixtures.
3. Inspect current data access through market-data-only adapters. Check original source/receipt clocks, provider/feed labels, permissions and bar continuity without retiming old data.
4. Review the actual strategy equations, rule versions, signal ID composition, immutable fields, confirmation timeframe, no-chase rule and full horizon deadlines.
5. Trace one idea from detection through primary control, publication guard, recipient reservation, acceptance, reported fill and research outcome. Keep all those populations distinct.
6. Reproduce the frozen historical studies only with lawful private data and original manifests. Preserve every trial, excluded day, assumption and previously inspected date.
7. Reproduce genuine-option evaluation with actual executable BBO, chain terms, costs, sizes and response times. Leave absent contracts/outcomes unavailable.
8. Re-run isolated command-role, formatter/dispatcher, all-day/early-close/DST, restart/uncertainty, calendar and data-failure regressions if source changes justify it. Never use test-generated production state or real guests.
9. Evaluate day-block uncertainty and trial selection, followed by genuinely untouched prospective periods. Passing engineering targets does not prove profitable trading.
10. Inspect operational incident evidence, database backups/restores, source-only rollback and private data separation. Preserve all issued reports and append-only history.

Representative commands are listed in Annex E. They are reproduction instructions, not commands executed against private production state during this report. Do not run legacy CLI account snapshots or any brokerage endpoint for this review.

## 30. Changes, Verification, Limitations and Setup impact of this review

**Changes:** documentation, sanitized source/evidence index, review artifacts and current-status pointer only. No production strategy, risk configuration, calendar timestamp, source freshness gate, task permission, sharing preference or trading/notification state was changed.

**Verification:** exact Git/source inventory; read-only operation; three authorized market-data probes; reviewed current production paths and dated evidence; primary publications and licenses re-opened; PDF/text/render checks and release privacy guard; remote publication verified separately before delivery. Previous successful and failed suites retain their original timestamps.

**Limitations:** source review and recorded evidence are not an independent end-to-end financial/security certification. Licensed raw history and personal ledgers are deliberately absent. External account entitlements, complete historical data, actual option profitability, model inference and prospective reliability remain incomplete. The finding list is explicit about unresolved mismatches rather than asserting perfect completeness.

**Setup impact:** none for operating AEGIS. The review bundle is inert documentation/source material; it must not be launched as a second installation. All trade execution remains manual.

## Annex A. Full retained historical strategy comparison

The following original report is retained as dated retrospective evidence. All cells, assumptions, unavailable cases and original source hashes remain visible. Its internal relative references are resolved against the pinned source archive.

Retained source: [reports/STRATEGY_COMPARISON_2026-10-22.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/STRATEGY_COMPARISON_2026-10-22.md). SHA-256: `d8912121dfb6f92e3020c54c7579d2b10b7196995541edd6c83d40b1c248dc22`.

### Strategy comparison — October 22

No strategy has sufficient genuine-option evidence. No published profitability claim has been reproduced on this installation. Passing rule tests establishes behavior, not an edge.

#### Primary sources and licensing

Reviewed the [original paper, September2025 version](https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf), the [original Python translation](https://concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/), and the [Alpaca article](https://concretumgroup.com/backtesting-7-years-of-free-data-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/). No explicit permissive redistribution license was established for their code. AEGIS imports none of it; strategies/concretum.py is an original implementation of the described mathematical rules. External notebooks/MATLAB files and data are not redistributed. The linked Colab required sign-in; accessible inline code was inspected.

The paper uses14 prior same-clock open-to-close absolute moves, gap-adjusted bands, half-hour decisions/stops and overnight-flat exposure. Opposite-band and current-band/VWAP exits are separate variants. Dynamic sizing uses prior14 returns and a4× ceiling. The Python articles differ:13-observation minimum warmup, shifted rolling volatility, rounded shares, and shifted close-return exposure. Those differences remain labeled; article behavior is not silently called the paper. The replay adds explicit delayed minute-open entry and the verified exchange close. It is an execution adaptation, not an exact replication of publisher returns.

#### Frozen protocol and available data

The protocol was saved before individual October21 stop results. All inspected periods are retrospective. October21 is development-only; no parameter was selected to rescue it. Source includes13,902 rows,13,641 regular-session rows,28 complete sessions and seven incomplete sessions excluded from outcome days. Incomplete prior sessions stay in lookbacks so they cannot silently become14 complete recent sessions. No data are filled or retimed.

Registered study: two paper exit variants × three holding horizons × three delays plus nine current-strategy horizon/delay variants =27. The 60/120/session variants are separate experiments. The current comparison uses the same deterministic setup detector at matched30-minute decision clocks, one observation per population, explicit per-share cost sensitivities and day-block uncertainty. It is different from production ten-second evaluation.15/30/60-second delays round up to the next available minute open; no claim of subminute execution.

| Period | Frozen dates |
|---|---|
| development | 2026-09-02, 2026-09-03, 2026-09-08, 2026-09-09, 2026-09-10, 2026-09-11, 2026-09-14, 2026-09-15, 2026-09-17, 2026-09-18, 2026-09-21, 2026-09-22, 2026-09-23, 2026-09-24, 2026-09-28, 2026-09-29, 2026-10-21 |
| validation_retrospective | 2026-10-01, 2026-10-02, 2026-10-05, 2026-10-06, 2026-10-08, 2026-10-12 |
| evaluation_retrospective | 2026-10-14, 2026-10-15, 2026-10-16, 2026-10-19, 2026-10-20 |

#### Results and refusal

The fresh authorized corporate-action request returned HTTP200 with corporate_actions={} and no pagination token, including a range containing a known dividend season. That is not verified complete dividend history. All504 Concretum variant/session evaluations therefore refused rather than defaulting missing dividends to zero. Exact numerical comparison against Concretum is BLOCKED pending audited complete raw intraday/daily history and dividend coverage; IEX-only minute history is not equivalent to the paper’s IQFeed history. The paper-rule implementation and refusal paths are TESTED IN ISOLATION.

Current-strategy delayed underlying diagnostics below use30-second response assumptions rounded to minute opens. Values are sums for one SPY share per observation, after the declared $0.03 roundtrip sensitivity; they are neither a funded portfolio nor option dollars.

| Variant / period | Observations | Active days | Net USD/share sum | Mean USD/share |
|---|---:|---:|---:|---:|
| CURRENT:SESSION:30:development | 9 | 7 | -1.243 | -0.138 |
| CURRENT:H60:30:development | 6 | 5 | -0.833 | -0.139 |
| CURRENT:H120:30:development | 6 | 5 | -0.833 | -0.139 |
| CURRENT:H60:30:validation_retrospective | 2 | 2 | 0.210 | 0.105 |
| CURRENT:SESSION:30:validation_retrospective | 2 | 2 | 0.210 | 0.105 |
| CURRENT:H120:30:validation_retrospective | 1 | 1 | 0.345 | 0.345 |
| CURRENT:H60:30:evaluation_retrospective | 2 | 2 | -0.290 | -0.145 |
| CURRENT:H120:30:evaluation_retrospective | 2 | 2 | -0.290 | -0.145 |
| CURRENT:SESSION:30:evaluation_retrospective | 2 | 2 | -0.290 | -0.145 |

There are only one or two active validation/evaluation days per displayed cell. These samples cannot establish robustness, a horizon winner, a reliable confidence interval, or option profitability. Day-block intervals are retained as descriptive diagnostics; no multiple-trial significance or automatic promotion is claimed. Initial replay output was retained when lookback handling was corrected; corrected context-preserving results are authoritative.

The individual14-alert audit separately records five frozen stop alternatives × three delays (210 evaluations) and the one-primary-plan delivery replay. Those are development sensitivities, not new untouched tests. Historical stop, target and actual-fill records were not changed. Ten of14 alerted detections were support bounces; three underlying research plans overlapped at the maximum. This concentration limits any broad strategy conclusion.

#### Reproduction and remaining evidence

Run python -m ops.primary_comparison --database PRIVATE_READONLY_STATE.sqlite --output PRIVATE_RESULT.json. Optional --dividends accepts an explicitly audited map with a basis field. Missing input remains unavailable. Source SHA-256: e0c4efc8317da18685ec9e815c261fcd007fc7700baa8e7cba284d740b40e5ba.

The existing genuine-BBO option evaluator remains available for audited local chain/quote datasets, with ask entries, bid exits, fees, delays, missing quotes, cash/exposure limits and provenance refusals. No genuine option snapshots were retained by this installation at audit time. No option backtest result, premium prediction or entry qualification is inferred from the underlying study, fixed delta or Greek approximations. Production contract references now use verified actual ask quotes and a100× multiplier, with no assumed limit fill or modeled premium stop.

Untouched future evidence can begin only after versions/selection are frozen; this release establishes no successful future period. Overnight/swing operation and live execution remain disabled.

#### Additional consolidated-history sensitivity — same frozen dates

A separate market-data-only request succeeded for historical SIP while real-time SIP remained403. Four hashed pages supplied31,691 original rows,14,040 regular-session bars and36 complete sessions for September1–October21. Download time was October22; none of this history was inserted into live caches or represented as decision-time capture. The original frozen outcome partitions are identical; additional source days provide lookback context only.

Exact corporate-action completeness remains unverified. The [US issuer schedule](https://www.ssga.com/library-content/products/fund-data/etfs/us/distribution/SPDR_Dividend_Distribution_Schedule.pdf) identifies the scheduled September distribution date; the [cross-listed issuer announcement](https://links.sgx.com/1.0.0/corporate-announcements/JFQWVTBZNY58JUVL/903367_SPY%20-%20Sept%202026%20-%20Attachment.pdf) still states TBA and has a different local ex date, so it was rejected as an actual US dividend amount. The following is explicitly an ASSUMPTION-ONLY no-other-scheduled-distribution scenario. September18 has no supplied amount and remains unavailable. This is not an exact publisher-result replication or verified complete-dividend backtest.

The paper exits and current setup detector ran unchanged. All three horizons/delays remain registered; no winner was chosen. Below are all30-second cells (rounded up to minute opens). Native paper costs are$0.009/share roundtrip versus the current$0.03 sensitivity. Common-cost sums additionally deduct$0.021 per Concretum observation, so costs are not hidden. Paper SESSION exits at the verified close; current SESSION uses close−5 minutes.

| Variant / period | Observations | Active days | Native net USD/share | Common $0.03 cost net | Native profit factor | Native max drawdown USD/share |
|---|---:|---:|---:|---:|---:|---:|
| CURRENT:H60:30:development | 7 | 5 | -0.173 | -0.173 | 0.863 | 1.264 |
| CURRENT:H120:30:development | 5 | 4 | 0.557 | 0.557 | 1.549 | 1.014 |
| CURRENT:SESSION:30:development | 7 | 5 | 0.307 | 0.307 | 1.243 | 1.264 |
| CONCRETUM:OPPOSITE_BAND:H60:30:development | 8 | 4 | -3.535 | -3.703 | 0.308 | 4.657 |
| CONCRETUM:OPPOSITE_BAND:H120:30:development | 4 | 3 | 0.589 | 0.505 | 1.229 | 2.569 |
| CONCRETUM:OPPOSITE_BAND:SESSION:30:development | 4 | 4 | -0.609 | -0.693 | 0.841 | 3.835 |
| CONCRETUM:CURRENT_BAND_VWAP:H60:30:development | 8 | 4 | -3.535 | -3.703 | 0.308 | 4.657 |
| CONCRETUM:CURRENT_BAND_VWAP:H120:30:development | 4 | 3 | -1.385 | -1.469 | 0.654 | 3.999 |
| CONCRETUM:CURRENT_BAND_VWAP:SESSION:30:development | 5 | 4 | -5.552 | -5.657 | 0.269 | 7.595 |
| CONCRETUM:OPPOSITE_BAND:H60:30:validation_retrospective | 7 | 4 | 0.835 | 0.688 | 1.314 | 2.658 |
| CONCRETUM:OPPOSITE_BAND:H120:30:validation_retrospective | 5 | 4 | 0.805 | 0.700 | 1.266 | 2.079 |
| CONCRETUM:OPPOSITE_BAND:SESSION:30:validation_retrospective | 4 | 4 | -4.476 | -4.560 | 0.366 | 4.476 |
| CONCRETUM:CURRENT_BAND_VWAP:H60:30:validation_retrospective | 7 | 4 | 0.223 | 0.076 | 1.068 | 2.819 |
| CONCRETUM:CURRENT_BAND_VWAP:H120:30:validation_retrospective | 6 | 4 | -0.925 | -1.051 | 0.759 | 3.817 |
| CONCRETUM:CURRENT_BAND_VWAP:SESSION:30:validation_retrospective | 5 | 4 | -1.006 | -1.111 | 0.719 | 3.567 |
| CURRENT:H60:30:validation_retrospective | 1 | 1 | -0.170 | -0.170 | 0.000 | 0.170 |
| CURRENT:H120:30:validation_retrospective | 1 | 1 | -0.170 | -0.170 | 0.000 | 0.170 |
| CURRENT:SESSION:30:validation_retrospective | 1 | 1 | -0.170 | -0.170 | 0.000 | 0.170 |
| CONCRETUM:OPPOSITE_BAND:H60:30:evaluation_retrospective | 11 | 4 | 10.470 | 10.239 | 3.288 | 2.998 |
| CONCRETUM:OPPOSITE_BAND:H120:30:evaluation_retrospective | 6 | 4 | 8.573 | 8.447 | 4.555 | 2.412 |
| CONCRETUM:OPPOSITE_BAND:SESSION:30:evaluation_retrospective | 5 | 5 | 7.485 | 7.380 | 3.140 | 3.349 |
| CONCRETUM:CURRENT_BAND_VWAP:H60:30:evaluation_retrospective | 11 | 4 | 11.630 | 11.399 | 4.405 | 1.838 |
| CONCRETUM:CURRENT_BAND_VWAP:H120:30:evaluation_retrospective | 7 | 4 | 8.037 | 7.890 | 3.803 | 2.048 |
| CONCRETUM:CURRENT_BAND_VWAP:SESSION:30:evaluation_retrospective | 6 | 5 | 9.356 | 9.230 | 7.603 | 0.819 |
| CURRENT:H60:30:evaluation_retrospective | 1 | 1 | -0.090 | -0.090 | 0.000 | 0.090 |
| CURRENT:H120:30:evaluation_retrospective | 1 | 1 | -0.090 | -0.090 | 0.000 | 0.090 |
| CURRENT:SESSION:30:evaluation_retrospective | 1 | 1 | -0.090 | -0.090 | 0.000 | 0.090 |

Later retrospective Concretum cells are positive while several earlier cells are negative. Only four or five active days support many paper cells, versus one current-strategy active day in some later cells. This is too little and too dependent on assumptions to establish superiority, statistical significance, future profitability or option performance. No production strategy, stop or risk parameter was promoted. Warmup exclusions:180 variant/session evaluations; unavailable dividend/prior-close evaluations:18. All exclusions remain in the private result.

Reproduce with python -m ops.primary_comparison --bars-export PRIVATE_HISTORICAL_EXPORT.json --frozen-manifest PRIVATE_FROZEN_MANIFEST.json --dividends PRIVATE_DISCLOSED_DIVIDEND_SCENARIO.json --output PRIVATE_RESULT.json. The export must retain capture_mode=HISTORICAL_DOWNLOAD. The source SHA-256 is ec876976b4213e3bab003e064a7824044232cabaf3b69ec738e04c5f548ca9fe. The private packet contains the exact partition manifest, scenario basis, page hashes and results for15/30/60-second variants. No licensed raw history is published.


## Annex B. Complete fourteen-alert audit and stop sensitivities

These are research IDs, not private trade identities. Original prices belong to the dated research audit; they are not current prices or invented examples.

Retained source: [reports/OCT21_INDIVIDUAL_ALERT_AUDIT.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/OCT21_INDIVIDUAL_ALERT_AUDIT.md). SHA-256: `220d718b4919b686d749e571a6161c4c8cbfc7ba8b1a425812d18101268320b7`.

### October 21 individual alerted-idea audit

Retrospective development evidence, inspected October 22. These are underlying research observations, not personal trades or verified option results. Original records are unchanged.

All 14 confirmation candles match their immutable signal IDs. All 14 owner envelopes were Telegram-accepted (not proof of phone delivery). The recorded cohort is 12 invalidations and two target-2 hits. The broader recap previously mixed 37 observations with the 14 alerts; its 25 stops were a different population. One scheduled recap envelope was found; the OS inventory found one current supervisor/task, not evidence of two active installations.

| Idea ID | Direction | Confirmation ET | Issue ET | Acceptance ET | Acceptance lag s | Reference | Stop distance | Stop | Target 1 | Target 2 | Recorded result | Other overlapping IDs count |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| c595906efa280d6827714eef | CALL | 10:03:00 | 10:03:24 | 10:03:29 | 4.415 | $770.800 | $0.560 | $770.240 | $771.360 | $771.920 | STOP_HIT | 0 |
| 422f298d1c7d38023a3001fd | PUT | 10:06:00 | 10:06:09 | 10:06:13 | 4.284 | $769.165 | $1.565 | $770.730 | $767.600 | $766.035 | STOP_HIT | 2 |
| 0abf5fc7b78b525dd7aee7bf | PUT | 10:06:00 | 10:06:29 | 10:06:34 | 4.775 | $769.030 | $1.700 | $770.730 | $767.330 | $765.630 | STOP_HIT | 2 |
| 3255879d883a7b0e5da7d3d6 | PUT | 10:11:00 | 10:11:27 | 10:11:31 | 4.139 | $768.660 | $0.540 | $769.200 | $768.120 | $767.580 | STOP_HIT | 2 |
| 088fcc090aaa1ccb6e37d5d0 | CALL | 11:30:00 | 11:30:06 | 11:30:11 | 5.733 | $772.040 | $0.415 | $771.625 | $772.455 | $772.870 | TARGET_2_HIT | 2 |
| 6eaafb8328d5655de500bf7c | CALL | 11:38:00 | 11:38:14 | 11:38:19 | 4.880 | $772.625 | $0.450 | $772.175 | $773.075 | $773.525 | STOP_HIT | 3 |
| f4e1648e92bf59b73428598f | CALL | 11:46:00 | 11:46:58 | 11:47:02 | 3.883 | $772.770 | $0.330 | $772.440 | $773.100 | $773.430 | STOP_HIT | 3 |
| e3dee46e6472a638ced29eac | CALL | 11:57:00 | 11:57:10 | 11:57:16 | 6.013 | $772.715 | $0.155 | $772.560 | $772.905 | $773.060 | STOP_HIT | 2 |
| 15022ce81e6e740716ee6328 | CALL | 13:36:00 | 13:36:34 | 13:36:39 | 4.941 | $773.710 | $0.280 | $773.430 | $774.000 | $774.280 | TARGET_2_HIT | 2 |
| dda255dde625f4f02ee6c4a4 | CALL | 13:43:00 | 13:43:19 | 13:43:27 | 7.140 | $774.120 | $0.280 | $773.840 | $774.400 | $774.680 | STOP_HIT | 1 |
| 2a17847919805f6c0a354e9c | CALL | 13:57:00 | 13:57:35 | 13:57:40 | 5.182 | $774.110 | $0.080 | $774.030 | $774.190 | $774.270 | STOP_HIT | 1 |
| 0bb52f20d10ee959a87f776c | CALL | 14:16:00 | 14:16:59 | 14:17:05 | 6.676 | $774.310 | $0.320 | $773.990 | $774.630 | $774.950 | STOP_HIT | 2 |
| a3647419a4ec986ae200258c | CALL | 14:26:00 | 14:26:16 | 14:26:22 | 6.269 | $774.215 | $0.065 | $774.150 | $774.405 | $774.470 | STOP_HIT | 2 |
| 615cd3dd94ab38d3557e33cc | CALL | 14:27:00 | 14:27:42 | 14:27:47 | 5.429 | $774.355 | $0.205 | $774.150 | $774.560 | $774.765 | STOP_HIT | 2 |

The confirmation time is the completed candle end recovered by hashing the original strategy identity, not the later evaluation or notification clock. Entry reference, modeled fill, trigger and personal fill remain distinct. The latter is never inferred.

| Idea ID | First invalidation bar end ET | First T1 bar end ET | First T2 bar end ET | Receipt +30s rounded-up minute-open proxy | Proxy result |
|---|---|---|---|---|---|
| c595906efa280d6827714eef | 10:05:00 | unavailable | unavailable | 10:04:00 / $770.730 | INVALIDATION |
| 422f298d1c7d38023a3001fd | 10:48:00 | unavailable | unavailable | 10:07:00 / $769.355 | INVALIDATION |
| 0abf5fc7b78b525dd7aee7bf | 10:48:00 | unavailable | unavailable | 10:08:00 / $769.360 | INVALIDATION |
| 3255879d883a7b0e5da7d3d6 | 10:24:00 | unavailable | unavailable | 10:13:00 / $769.010 | INVALIDATION |
| 088fcc090aaa1ccb6e37d5d0 | unavailable | 11:37:00 | 11:51:00 | 11:31:00 / $771.980 | TARGET |
| 6eaafb8328d5655de500bf7c | 12:28:00 | unavailable | unavailable | 11:39:00 / $772.605 | INVALIDATION |
| f4e1648e92bf59b73428598f | 12:01:00 | 12:40:00 | 12:40:00 | 11:48:00 / $772.785 | INVALIDATION |
| e3dee46e6472a638ced29eac | 12:01:00 | 12:40:00 | 12:40:00 | 11:58:00 / $772.700 | INVALIDATION |
| 15022ce81e6e740716ee6328 | unavailable | 13:43:00 | 14:16:00 | 13:38:00 / $773.720 | TARGET |
| dda255dde625f4f02ee6c4a4 | 13:47:00 | 14:17:00 | unavailable | 13:44:00 / $774.070 | INVALIDATION |
| 2a17847919805f6c0a354e9c | 13:59:00 | 14:16:00 | 14:16:00 | 13:59:00 / $773.905 | ALREADY_INVALIDATED |
| 0bb52f20d10ee959a87f776c | 14:48:00 | unavailable | unavailable | 14:18:00 / $774.260 | INVALIDATION |
| a3647419a4ec986ae200258c | 14:37:00 | unavailable | unavailable | 14:27:00 / $774.320 | CHASE_LIMIT_REJECTED |
| 615cd3dd94ab38d3557e33cc | 14:37:00 | unavailable | unavailable | 14:29:00 / $774.300 | INVALIDATION |

First touches shown over the original holding window may occur **after** an invalidation; they do not resurrect an exited observation. Minute OHLC cannot establish intraminute stop/target order. Each exact level must be rechecked against a fresh executable quote after receipt; there is no complete underlying BBO/trade archive at those times. Therefore first achievable entries and actual option fills are unavailable. The proxies above are not fills, even when their open is within the entry limit.

Original stops range from $0.065 to $1.700 of SPY. Several later favorable moves came after the earlier invalidation. That combination, concurrent plans, and detection-to-receipt/human delays explains why later rising prices do not negate the recorded stops. It does not prove a wider stop would be profitable.

#### Frozen sensitivity results

Five stop rules × three response delays = 15 trials per idea, 210 total evaluations. The grid was written before individual stop results were inspected: original; last three completed 5m extremes with 0.10×5m ATR buffer; and 1/1.5/2×5m ATR. Original targets are held fixed to isolate stop effects. No alternative was selected for production.

| Stop variant | Delay s | Results |
|---|---:|---|
| ORIGINAL | 15 | INVALIDATION: 10; TARGET: 2; ALREADY_INVALIDATED: 1; CHASE_LIMIT_REJECTED: 1 |
| ORIGINAL | 30 | INVALIDATION: 10; TARGET: 2; ALREADY_INVALIDATED: 1; CHASE_LIMIT_REJECTED: 1 |
| ORIGINAL | 60 | ALREADY_INVALIDATED: 2; INVALIDATION: 9; TARGET: 2; CHASE_LIMIT_REJECTED: 1 |
| STRUCTURE_3X5M_ATR_BUFFER | 15 | INVALIDATION: 6; TIME_EXIT: 4; TARGET: 3; CHASE_LIMIT_REJECTED: 1 |
| STRUCTURE_3X5M_ATR_BUFFER | 30 | INVALIDATION: 6; TIME_EXIT: 4; TARGET: 3; CHASE_LIMIT_REJECTED: 1 |
| STRUCTURE_3X5M_ATR_BUFFER | 60 | ALREADY_INVALIDATED: 1; TIME_EXIT: 4; INVALIDATION: 5; TARGET: 3; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_1 | 15 | INVALIDATION: 10; TARGET: 2; TIME_EXIT: 1; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_1 | 30 | INVALIDATION: 10; TARGET: 2; TIME_EXIT: 1; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_1 | 60 | ALREADY_INVALIDATED: 1; INVALIDATION: 9; TARGET: 2; TIME_EXIT: 1; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_1.5 | 15 | INVALIDATION: 6; TARGET: 5; TIME_EXIT: 2; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_1.5 | 30 | INVALIDATION: 6; TARGET: 5; TIME_EXIT: 2; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_1.5 | 60 | INVALIDATION: 6; TARGET: 5; TIME_EXIT: 2; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_2 | 15 | INVALIDATION: 6; TARGET: 5; TIME_EXIT: 2; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_2 | 30 | INVALIDATION: 6; TARGET: 5; TIME_EXIT: 2; CHASE_LIMIT_REJECTED: 1 |
| ATR5M_2 | 60 | INVALIDATION: 6; TARGET: 5; TIME_EXIT: 2; CHASE_LIMIT_REJECTED: 1 |

The same-clock one-primary-plan replay retains six initial plans and leaves eight overlapping detections separate. This uses original terminal times and is a delivery-policy comparison, not a new strategy backtest or proof of improved returns. All original history remains.

Reproduce privately with `python -m ops.alert_audit --root YOUR_INSTALLATION --day 2026-10-21 --output PRIVATE_OUTPUT.json`. Inputs are read-only. Source bars SHA-256: 329d25263a700cea96683f1d4ea7dba20de22838a7de987b4eca25c71f89f34e.


## Annex C. Actual retained formatter and fake-dispatch transcript

All prices and fixture identities in this annex are simulated. It is an existing dated production-path test artifact, not a new real Telegram send or current market finding.

Retained source: [reports/TELEGRAM_DEMO_RELEASE_2026-10-27.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/TELEGRAM_DEMO_RELEASE_2026-10-27.md). SHA-256: `f8800870f4ecee81a1d747875bae99a2b539ccfe918a7aad3517173455b2c09d`.

### AEGIS production-renderer demonstration

Every price, quote, event, contract and outcome below is a FICTIONAL FIXTURE. This is software behavior, not actual market evidence, a live contract or a personal fill. No Telegram network, vault or guest was used.

Actual notifier fake-transport result: {"status": "PASS", "events": 58, "calls": 58, "transport": "Actual notifier validator/send with fake client, fake clock, fixture recipient only; no network or vault"}

#### Format fixtures

##### Fixture 1 · PREOPEN

```text
SPY PREMARKET · Oct 21 · 09:15 ET
Opening-hour lean: UP while SPY holds above $499.00 · conditional
Session lean: UNCLEAR · reassess after opening range
CALL watch: confirmed break above $501.00; Downside reversal: below $499.00
Watch: completed opening-range confirmation after 09:45 ET
Next major event: no required scheduled event listed; optional coverage incomplete
Premarket: $500.30 · IEX_RESEARCH_ONLY · as of 09:10 ET
Research only · reassess after the open; no regular-session entry confirmed
```

##### Fixture 2 · TREND_LINE

```text
11:00 ET · SPY $500.30
Current trend: UP
Next hour: upward bias · session: upward bias
New entry: WAIT — confirmation missing
Research · IEX · as of 11:00 ET · /details
```

##### Fixture 3 · SPY_IDEA

```text
SPY WATCH · ID aaaaaaaaaaaaaaaaaaaaaaaa · CALL direction
ENTRY CONFIRMED · a completed 1-minute close above SPY $500.10
Do not enter above SPY $500.80
SPY target: $501.30
Exit condition: SPY at or below $499.80
Planned hold: H60 · up to 60 minutes; exit by 12:00 ET
Entry expires: 11:01 ET
Underlying watch only · option contract unavailable.
Experimental · manual review; underlying levels; no guaranteed stop-loss cap
```

##### Fixture 4 · IDEA_UPDATE

```text
ID aaaaaaaaaaaaaaaaaaaaaaaa · EXIT CONDITION REACHED — SPY invalidation reached in research
Research update; your fills remain separate.
```

##### Fixture 5 · TREND_LINE

```text
11:00 ET · SPY $500.30
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Active plan aaaaaaaaaaaaaaaaaaaaaaaa: HOLD · no additional entry (no new entry); monitoring unavailable
Research · IEX · as of 11:00 ET · /details
```

##### Fixture 6 · RECAP

```text
SPY RECAP · Oct 21
Ideas alerted: 1
Alerted research: 1 closed · 0 open · 0 unresolved
Option-paper dollars: unavailable without genuine quotes
Next session: wait for genuine opening-range data
Confirmed plans: 1 · 0 silent observations separate
Forward outlook: outcomes unavailable; no accuracy claimed
/score · data quality varies
```

##### Fixture 7 · SPY_IDEA

```text
CALL RESEARCH · ID bbbbbbbbbbbbbbbbbbbbbbbb
ENTRY CONFIRMED · a completed 1-minute close above SPY $500.10
Do not enter above SPY $500.80
SPY target: $501.30
Exit condition: SPY at or below $499.80
Planned hold: H60 · up to 60 minutes; exit by 12:00 ET
Entry expires: 11:01 ET
Option: SPY261023C00500000 limit $2.00/share · 100× = $200.00 + $0.65 entry fee; premium at risk $200.00 + fees
Experimental · manual review; underlying levels; no guaranteed stop-loss cap
```

#### Full-day normal · synthetic / memory-only

{"IDEA_UPDATE": 1, "PREOPEN": 1, "RECAP": 1, "SPY_IDEA": 1, "TREND_LINE": 25}

##### 2026-10-21T09:15:00-04:00 · PREOPEN

```text
SPY PREMARKET · Oct 21 · 09:15 ET
Opening-hour lean: UNCLEAR · conditional
Session lean: UNCLEAR · reassess after opening range
CALL watch: unavailable; reassess after open; Reversal level: unavailable
Watch: completed opening-range confirmation after 09:45 ET
Next major event: no required scheduled event listed; optional coverage incomplete
Prior-close projection: $500.00 · SIMULATED · as of unavailable
Research only · reassess after the open; no regular-session entry confirmed
```

##### 2026-10-21T09:45:00-04:00 · TREND_LINE · SILENT

```text
09:45 ET · SPY $500.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · limited early read · bar close 09:45 ET · /details
```

##### 2026-10-21T09:46:00-04:00 · SPY_IDEA

```text
SPY WATCH · ID c33ec179fef85e55b5bcfef6 · CALL direction
ENTRY CONFIRMED · a completed 1-minute close above SPY $500.22
Do not enter above SPY $501.09
SPY target: $502.79
Exit condition: SPY at or below $500.12
Planned hold: H60 · up to 60 minutes; exit by 10:46 ET
Entry expires: 09:47 ET
Underlying watch only · option contract unavailable.
Experimental · manual review; underlying levels; no guaranteed stop-loss cap
```

##### 2026-10-21T10:00:00-04:00 · TREND_LINE · SILENT

```text
10:00 ET · SPY $501.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · limited early read · bar close 10:00 ET · /details
```

##### 2026-10-21T10:15:00-04:00 · TREND_LINE · SILENT

```text
10:15 ET · SPY $501.35
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:15 ET · /details
```

##### 2026-10-21T10:30:00-04:00 · TREND_LINE · SILENT

```text
10:30 ET · SPY $501.53
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:30 ET · /details
```

##### 2026-10-21T10:45:00-04:00 · TREND_LINE · SILENT

```text
10:45 ET · SPY $501.71
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:45 ET · /details
```

##### 2026-10-21T10:46:00-04:00 · IDEA_UPDATE

```text
ID c33ec179fef85e55b5bcfef6 · EXIT CONDITION REACHED — holding deadline reached
Research update; your fills remain separate.
```

##### 2026-10-21T11:00:00-04:00 · TREND_LINE · SILENT

```text
11:00 ET · SPY $501.89
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:00 ET · /details
```

##### 2026-10-21T11:15:00-04:00 · TREND_LINE · SILENT

```text
11:15 ET · SPY $502.07
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:15 ET · /details
```

##### 2026-10-21T11:30:00-04:00 · TREND_LINE · SILENT

```text
11:30 ET · SPY $502.25
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:30 ET · /details
```

##### 2026-10-21T11:45:00-04:00 · TREND_LINE · SILENT

```text
11:45 ET · SPY $502.43
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:45 ET · /details
```

##### 2026-10-21T12:00:00-04:00 · TREND_LINE · SILENT

```text
12:00 ET · SPY $502.61
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:00 ET · /details
```

##### 2026-10-21T12:15:00-04:00 · TREND_LINE · SILENT

```text
12:15 ET · SPY $502.79
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:15 ET · /details
```

##### 2026-10-21T12:30:00-04:00 · TREND_LINE · SILENT

```text
12:30 ET · SPY $502.97
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:30 ET · /details
```

##### 2026-10-21T12:45:00-04:00 · TREND_LINE · SILENT

```text
12:45 ET · SPY $503.15
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:45 ET · /details
```

##### 2026-10-21T13:00:00-04:00 · TREND_LINE · SILENT

```text
13:00 ET · SPY $503.33
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:00 ET · /details
```

##### 2026-10-21T13:15:00-04:00 · TREND_LINE · SILENT

```text
13:15 ET · SPY $503.51
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:15 ET · /details
```

##### 2026-10-21T13:30:00-04:00 · TREND_LINE · SILENT

```text
13:30 ET · SPY $503.69
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:30 ET · /details
```

##### 2026-10-21T13:45:00-04:00 · TREND_LINE · SILENT

```text
13:45 ET · SPY $503.87
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:45 ET · /details
```

##### 2026-10-21T14:00:00-04:00 · TREND_LINE · SILENT

```text
14:00 ET · SPY $504.05
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:00 ET · /details
```

##### 2026-10-21T14:15:00-04:00 · TREND_LINE · SILENT

```text
14:15 ET · SPY $504.23
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:15 ET · /details
```

##### 2026-10-21T14:30:00-04:00 · TREND_LINE · SILENT

```text
14:30 ET · SPY $504.41
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:30 ET · /details
```

##### 2026-10-21T14:45:00-04:00 · TREND_LINE · SILENT

```text
14:45 ET · SPY $504.59
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:45 ET · /details
```

##### 2026-10-21T15:00:00-04:00 · TREND_LINE · SILENT

```text
15:00 ET · SPY $504.77
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:00 ET · /details
```

##### 2026-10-21T15:15:00-04:00 · TREND_LINE · SILENT

```text
15:15 ET · SPY $504.95
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:15 ET · /details
```

##### 2026-10-21T15:30:00-04:00 · TREND_LINE · SILENT

```text
15:30 ET · SPY $505.13
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:30 ET · /details
```

##### 2026-10-21T15:45:00-04:00 · TREND_LINE · SILENT

```text
15:45 ET · SPY $505.31
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:45 ET · /details
```

##### 2026-10-21T16:15:00-04:00 · RECAP

```text
SPY RECAP · Oct 21
Ideas alerted: 1
Alerted research: 1 closed · 0 open · 0 unresolved
Option-paper dollars: unavailable without genuine quotes
Next session: review retained session levels in /details
Confirmed plans: 1 · 0 silent observations separate
Forward direction: H60 0/0 resolved of 25 issued; H120 0/0 resolved of 25 issued; SESSION 0/0 resolved of 25 issued; PREMARKET_OPENING_HOUR 0/0 resolved of 1 issued; PREMARKET 0/0 resolved of 1 issued · unvalidated
/score · data quality varies
```

#### Full-day stale · synthetic / memory-only

{"IDEA_UPDATE": 1, "PREOPEN": 1, "RECAP": 1, "SPY_IDEA": 1, "TREND_LINE": 25}

##### 2026-10-21T09:15:00-04:00 · PREOPEN

```text
SPY PREMARKET · Oct 21 · 09:15 ET
Opening-hour lean: UNCLEAR · conditional
Session lean: UNCLEAR · reassess after opening range
CALL watch: unavailable; reassess after open; Reversal level: unavailable
Watch: completed opening-range confirmation after 09:45 ET
Next major event: no required scheduled event listed; optional coverage incomplete
Prior-close projection: $500.00 · SIMULATED · as of unavailable
Research only · reassess after the open; no regular-session entry confirmed
```

##### 2026-10-21T09:45:00-04:00 · TREND_LINE · SILENT

```text
09:45 ET · SPY $500.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · limited early read · bar close 09:45 ET · /details
```

##### 2026-10-21T09:46:00-04:00 · SPY_IDEA

```text
SPY WATCH · ID c33ec179fef85e55b5bcfef6 · CALL direction
ENTRY CONFIRMED · a completed 1-minute close above SPY $500.22
Do not enter above SPY $501.09
SPY target: $502.79
Exit condition: SPY at or below $500.12
Planned hold: H60 · up to 60 minutes; exit by 10:46 ET
Entry expires: 09:47 ET
Underlying watch only · option contract unavailable.
Experimental · manual review; underlying levels; no guaranteed stop-loss cap
```

##### 2026-10-21T10:00:00-04:00 · TREND_LINE · SILENT

```text
10:00 ET · SPY $501.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · limited early read · bar close 10:00 ET · /details
```

##### 2026-10-21T10:15:00-04:00 · TREND_LINE · SILENT

```text
10:15 ET · SPY $501.35
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:15 ET · /details
```

##### 2026-10-21T10:30:00-04:00 · TREND_LINE · SILENT

```text
10:30 ET · SPY $501.53
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:30 ET · /details
```

##### 2026-10-21T10:45:00-04:00 · TREND_LINE · SILENT

```text
10:45 ET · SPY $501.71
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:45 ET · /details
```

##### 2026-10-21T10:46:00-04:00 · IDEA_UPDATE

```text
ID c33ec179fef85e55b5bcfef6 · EXIT CONDITION REACHED — holding deadline reached
Research update; your fills remain separate.
```

##### 2026-10-21T11:00:00-04:00 · TREND_LINE · SILENT

```text
11:00 ET · SPY $501.89
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Research · SIMULATED · bar close 11:00 ET · /details
```

##### 2026-10-21T11:15:00-04:00 · TREND_LINE · SILENT

```text
11:15 ET · SPY $502.07
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Research · SIMULATED · bar close 11:15 ET · /details
```

##### 2026-10-21T11:30:00-04:00 · TREND_LINE · SILENT

```text
11:30 ET · SPY $502.25
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:30 ET · /details
```

##### 2026-10-21T11:45:00-04:00 · TREND_LINE · SILENT

```text
11:45 ET · SPY $502.43
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:45 ET · /details
```

##### 2026-10-21T12:00:00-04:00 · TREND_LINE · SILENT

```text
12:00 ET · SPY $502.61
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:00 ET · /details
```

##### 2026-10-21T12:15:00-04:00 · TREND_LINE · SILENT

```text
12:15 ET · SPY $502.79
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:15 ET · /details
```

##### 2026-10-21T12:30:00-04:00 · TREND_LINE · SILENT

```text
12:30 ET · SPY $502.97
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:30 ET · /details
```

##### 2026-10-21T12:45:00-04:00 · TREND_LINE · SILENT

```text
12:45 ET · SPY $503.15
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:45 ET · /details
```

##### 2026-10-21T13:00:00-04:00 · TREND_LINE · SILENT

```text
13:00 ET · SPY $503.33
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:00 ET · /details
```

##### 2026-10-21T13:15:00-04:00 · TREND_LINE · SILENT

```text
13:15 ET · SPY $503.51
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:15 ET · /details
```

##### 2026-10-21T13:30:00-04:00 · TREND_LINE · SILENT

```text
13:30 ET · SPY $503.69
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:30 ET · /details
```

##### 2026-10-21T13:45:00-04:00 · TREND_LINE · SILENT

```text
13:45 ET · SPY $503.87
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:45 ET · /details
```

##### 2026-10-21T14:00:00-04:00 · TREND_LINE · SILENT

```text
14:00 ET · SPY $504.05
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:00 ET · /details
```

##### 2026-10-21T14:15:00-04:00 · TREND_LINE · SILENT

```text
14:15 ET · SPY $504.23
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:15 ET · /details
```

##### 2026-10-21T14:30:00-04:00 · TREND_LINE · SILENT

```text
14:30 ET · SPY $504.41
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:30 ET · /details
```

##### 2026-10-21T14:45:00-04:00 · TREND_LINE · SILENT

```text
14:45 ET · SPY $504.59
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:45 ET · /details
```

##### 2026-10-21T15:00:00-04:00 · TREND_LINE · SILENT

```text
15:00 ET · SPY $504.77
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:00 ET · /details
```

##### 2026-10-21T15:15:00-04:00 · TREND_LINE · SILENT

```text
15:15 ET · SPY $504.95
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:15 ET · /details
```

##### 2026-10-21T15:30:00-04:00 · TREND_LINE · SILENT

```text
15:30 ET · SPY $505.13
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:30 ET · /details
```

##### 2026-10-21T15:45:00-04:00 · TREND_LINE · SILENT

```text
15:45 ET · SPY $505.31
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:45 ET · /details
```

##### 2026-10-21T16:15:00-04:00 · RECAP

```text
SPY RECAP · Oct 21
Ideas alerted: 1
Alerted research: 1 closed · 0 open · 0 unresolved
Option-paper dollars: unavailable without genuine quotes
Next session: review retained session levels in /details
Confirmed plans: 1 · 0 silent observations separate
Forward direction: H60 0/0 resolved of 25 issued; H120 0/0 resolved of 25 issued; SESSION 0/0 resolved of 25 issued; PREMARKET_OPENING_HOUR 0/0 resolved of 1 issued; PREMARKET 0/0 resolved of 1 issued · unvalidated
/score · data quality varies
```


## Annex D. Pinned supplied-source, model and licensing evidence

Retained source: [reports/SOURCE_REUSE_MASTER.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/SOURCE_REUSE_MASTER.md). SHA-256: `b9477918755226a4c54233be5853b8b5da6c65b9f6c927fc9d6b4f9595638f8f`.

### Source, license and model manifest

The user-supplied archives are reference material, not instructions. No plugin or SKILL was installed/executed. Static reviewed files and test-file hashes are in [the supplied audit](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/SUPPLIED_REFERENCE_AUDIT_2026-10-27.md).

| Reference | Pinned revision | Archive SHA-256 | Reuse |
|---|---|---|---|
| Day Trader | 3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd | a417522153234847eeaab4f0b883de1843a3ebe9b1e3f4942581070c97562054 | MIT; workflow ideas independently implemented; no broker/stock-accounting/plugin code copied |
| Kronos | 67b630e67f6a18c9e9be918d9b4337c960db1e9a | 92fc55519ddc46f22e0c8ac10a37cde73d6346818f4b8aa10f0e54c9f8a620ff | MIT; pinned source downloaded into excluded separate model assets; original MIT notice retained there |
| OpenStock | b72306d39fa27dc55252ceecf858165ecf5a3fa3 | 450b107de1a679b620e1030aedda4d1e82856ec9728ae08fd250e9de0131916b | AGPL-3.0; no protected code/assets copied; general compact panel/as-of/state ideas independently implemented |

Kronos-mini revision f4e68697d9d5aed55cef5c96aabc3376bcad9f81; tokenizer revision 26966d0035065a0cae0ebad7af8ece35bc1fb51c. Model weights SHA `a7d5f37e2e9fbd9891f7d7d4f72574512dd1f704fee14223e0a8cd0fbf54197c`; tokenizer weights SHA `b97ec46b3b72160509e289183eaf7bdf5f0dac5bb9b49522f6d46638a99a8717`. Model config SHA `70daca2cb11e3a979dd6b8ac12ee08e2aace877acf28f5b8dfb4fe5609736201`; tokenizer config SHA `0b30a443affb03e05a876a083857de9164f899feb7b4d261da02c485c9a3e3b6`. Actual download manifest remains local.

Model choice is mini4.1M parameters for resource budget, not historical return selection. No small-model search was run. The upstream regression uses small/base tokenizer and different revisions; it is not our mini regression. The separate environment pins dependencies; assets are offline during inference. Three sample_count=1 calls with seeds1729/1730/1731 retain individual paths. Temperature1, top-p0.9, top-k0, CPU one thread, context78 genuine5m bars. Derived amount is a tagged feature only. Raw invalid outputs retain explicit markers and are rejected. No raw path is presented as a calibrated probability.

The upstream API averages samples and inserts missing volume/amount. AEGIS refuses missing volume and retains its own individual paths. No averaged-path high/low is used as a probability. Training-date/SPY overlap is not established. The paper's Chinese equity/daily simulation is not SPY intraday option evidence. Actual mini smoke is NOT_RUN, not an upstream-paper success.

Day Trader review confirmed clock-based range completeness can leave missing constituent bars, old triggers can persist, long-stock exit math is not PUT-option math, and independent slot resampling/exact-1R stops do not establish executable option results. AEGIS retains genuine range completeness, current-publication checks, correct long-option accounting and real chronological replay. No 0.05%-of-price stop floor was copied. OpenStock's hourly/15s cache and5m alerts are presentation/cache patterns, not5s BBO gates; mode alone never creates a Live badge.

Concretum equations remain an independent implementation of published mathematics. No broad publisher-code license was assumed and no publisher code was imported. Original versus adapted stops/costs/horizons are recorded in the existing [comparison](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/STRATEGY_COMPARISON_2026-10-22.md).

Primary links: [Day Trader](https://github.com/Jakeschincariol/day-trader-skill), [Kronos](https://github.com/shiyu-coder/Kronos), [paper](https://arxiv.org/html/2508.02739v1), [mini model card](https://huggingface.co/NeoQuasar/Kronos-mini), [OpenStock](https://github.com/Open-Dev-Society/OpenStock), [Concretum](https://concretumgroup.com/backtesting-7-years-of-free-data-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/), [Alpaca market data](https://docs.alpaca.markets/us/docs/about-market-data-api), [corporate-action filter semantics](https://docs.alpaca.markets/us/reference/corporateactions-1).


Retained source: [reports/MASTER_MODEL_BENCHMARK.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/MASTER_MODEL_BENCHMARK.md). SHA-256: `7dce6db474ad5dc111d326aa8cb82f5077aadf7b75bd4162a72ae61d8f4211ea`.

### Model resources and failure isolation

Actual mini inference: **NOT_RUN**. Preflight measured 212418560 available bytes against 1610612736 required. Refusal took 0.015999999828636646s. This2GB host did not safely meet the1536MiB-free headroom requirement; the separate neural environment was not installed. Pinned public weights/code were downloaded and hashed. No invented neural forecast, latency or profitability is reported.

The model worker is a separate supervised process. It has no Telegram producer or entry authority. Its child is offline, has a45s wall deadline,768MiB Windows job memory bound, one torch/BLAS thread and low process priority. It refuses without headroom and stops if headroom falls below512MiB. Output is bounded on disk instead of accumulated in RAM. Provider/AI/bot secrets are excluded from the environment. Each result is append-only in its own database, with cutoff/source/input/model/config hashes and actual completion/availability. Restart read times do not duplicate an identical trial; changed input data is a new revision.

Actual isolated Python fixture results (not neural benchmarks):

| Fixture | Result | Seconds |
|---|---|---:|
| timeout | TIMEOUT | 0.5 |
| malformed | CONTAINMENT_OR_PROTOCOL_FAILED | 0.219 |
| crash | MODEL_PROCESS_FAILED | 0.203 |
| memory | MODEL_PROCESS_FAILED | 0.188 |
| output | OUTPUT_TOO_LARGE | 0.265 |

Parent progress: 45 ticks; largest measured tick gap 0.031999999890103936s. These128MiB-capped fixture children used injected preflight headroom solely to exercise containment. They do not establish that actual neural inference preserves live-session deadlines. That remains a future operational measurement.

After adequate memory is available, run the separate setup and genuine completed-input benchmark in SETUP.md. Missing weights, bad dimensions/OHLC, nonfinite outputs, future/partial/gapped inputs, expiry/early-close/DST and append-only records are covered by isolated tests. Real pinned mini deterministic regression is explicitly pending, not silently counted as a skipped passing test.


## Annex E. Requirements, feature mapping and reproduction

The following dated matrix remains useful for locating implementation and tests. Current findings and post-October-27 updates above supersede older readiness/count statements. A static function list is not a test result.

Retained source: [reports/MASTER_REQUIREMENTS_VERIFICATION.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/MASTER_REQUIREMENTS_VERIFICATION.md). SHA-256: `4a7033c20c6787a871fafb1ee5a9d923406501efe8ccc28a24946ebc924f0169`.

### Requirements to verification — master release

Statuses distinguish isolated tests, local operation and external evidence. No function count implies behavioral correctness.

| Requirement | Current implementation | Change needed / delivered | Production path | Test/evidence | Remaining external blocker |
|---|---|---|---|---|---|
| Actual installation, sources, processes, tasks | Oct22 one-authority release plus retained Oct26 failure | Current process/heartbeat inventory; stale-record label; bounded task restart | ops/supervisor.py; ops/install_autostart.ps1 | Private before/after inventory; OPERATIONS_MASTER; supervisor tests | Host/VM time and future continuous uptime remain unverified |
| Recoverable source/config and WAL-aware SQLite backup | Existing append-only ledgers | Pinned online snapshot; streaming hashes; separate restore | Private backup helper, operational10 databases | 10/10 restored integrity/counts; original packet hash preserved | None |
| Shared typed/versioned product view | Separate legacy presentation helpers | market-view-v1 plus typed premarket/recap and immutable named plan view | core/market_view.py; core/idea_service.py; core/bot_commands.py; dashboard | test_master_boundaries; owner/semantic templates; actual fake notifier | Future-session consistency pending |
| UP/DOWN/MIXED/SIDEWAYS/UNAVAILABLE | v1 mapped conflict to SIDEWAYS | v2 explicit range predicate; missing remains unavailable; early mode labelled | core/directional_research.py | 36 historical sessions; fixed protocol; no accuracy improvement selected | Forecast validation unestablished |
| Trend versus forecast versus entry | Strict quote/heartbeat/continuity gates already present | Stale quote retains only eligible completed-bar trend; outlook abstains and entry waits | core/market_view.py; core/observed_context.py | Stale/heartbeat/missing/sideways regression fixtures | Sustained genuine live data pending |
| Premarket opening-hour/session leans | Prepared09:15 report | Separate conditional opening-hour lean and UNCLEAR session lean; distinct issued forecasts | monitoring/owner_messages.py; core/idea_service.py | Prepared-slot, stale preparation, date-only event, calendar tests | Usable current premarket evidence required |
| All25 silent scheduled statuses and recap | Atomic scheduled-authority-v2 | Preserved cadence, categories and sharing; v2 bounded presentation | monitoring/day_schedule.py; notifier.cjs | Full schedule/day fake transport; command registry retained | Telegram acceptance is not handset delivery |
| One primary plan and secondary observations | primary-plan-v1 | Additive v2 unresolved/admin state, same durable reservation key | core/primary_plan.py | Restart/adoption/opposing-candidate/append-only tests | No personal fill or exit is inferred |
| Practical H60 holding and pending entry expiry | v3 could clip at session cutoff | v4 full60m from confirmation; fixed deadline; latest entry<=confirmation+60s | strategies/idea_setups.py | Both directions, late/early-close and expiry regressions | H120/SESSION comparative plans remain separate research populations |
| Publication-time safety and immutable price meanings | Parent-first durable outbox already implemented | Exact-proposal digest; per-recipient/per-definitive-retry read-only gate | core/entry_publication.py; ops/entry_check.py; monitoring/notifier.cjs | Binding/no-chase/expiry/current BBO/refusal/uncertainty tests | Actual market-hours latency requires future observations |
| Private actual fills and holdings | Separate user-reported ledgers | Preserved FORCE/VOID/reconciliation/roles; no expiry settlement assumption | core/fill_flow.py; options/ledger.py; monitoring/commands.cjs | Full Python/Node and all-role harness | Reports are never broker verified |
| Research cooldown and risk populations | research-loss-episodes-v2 | Policy unchanged; silent/alerted/actual populations explicitly separated | core/research_pause.py; core/idea_service.py | Deduplication, expiry, new causes and restart regressions | No policy promoted from Oct21 outcomes |
| Genuine option reference and premium | verified-bbo-reference-v1 | Shared current-reference verifier; OI/volume/BBO match/ask premium/100x risk | options/research_contract.py; owner_messages.py | Real-schema isolated fixture plus stale/malformed/refusal cases | Live OPRA403; genuine point-in-time option history missing |
| After-cost option evaluation | Genuine-BBO replay and collector already implemented | Preserved ask+slippage/bid-slippage, both fees, delay/cash/overlap refusals | backtesting/option_research.py; research collection | Existing full suite; no genuine option performance manufactured | Audited historical chain/BBO/Greeks/OI coverage required |
| Concretum frozen original rules and comparison | Existing original-equation implementation and27 trials | Frozen v3 AEGIS comparator preserved; exact previous sensitivity reproduction | strategies/concretum.py; idea_setups_v3.py; ops/primary_comparison.py | Analysis hash matches original; declared assumptions remain assumptions | Complete verified dividend/ex-date and full historical replication inputs |
| Corporate-action quality | Response had omitted cash_dividends | Process-date response never verifies zero ex-date dividend; decimal rate normalization | data/corporate_actions.py; published_baselines.py | Official docs; empty/schema/decimal/pagination regressions | Provider/issuer completeness still not established |
| Day Trader workflow/replay reference | Supplied MIT archive | Static code/tests review; independent binding/deadline design only | SUPPLIED_REFERENCE_AUDIT; SOURCE_REUSE_MASTER | All supplied archive hashes match; no SKILL executed | No stock-risk or independent-slot simulation copied as options evidence |
| OpenStock presentation reference | Supplied AGPL archive | Independent source/as-of/state presentation; no protected code/assets copied | dashboard/upgrade.html; owner_messages.py | Actual dashboard/script and semantic formatter tests | No migration or other-stock platform in core scope |
| Pinned optional Kronos mini adapter | No deployed model before this work | Separate offline environment/process, raw3 paths, hashes, seed/config and availability | research/shadow_forecast.py; ops/kronos_infer.py | Assets downloaded/hash-pinned; transform/path/calendar/refusal tests | Actual model smoke BLOCKED by insufficient memory; env not installed |
| Model isolation and bounded failure | Main worker must never import torch | 45s/768MiB process bound,1 CPU thread,1536MiB free preflight, offline/no secrets | ops/shadow_worker.py | Actual fixture timeout/crash/OOM/output-limit; parent progress retained | These are fixture failures, not measured neural speed or live feed protection |
| Model chronological comparison | No trustworthy mini SPY outcomes | Append-only separate journal; no-change/rule/TOD baselines; all failures retained | research/shadow_evaluation.py | Future-only/path dimensions/denominator/missingness tests | Future frozen-model sessions and checkpoint independence audit |
| Service reliability and source ages | Oct22 feed isolation/receipt-before-processing/CAS/bounded background jobs | Preserved; date-bound indexed session report query; explicit runtimes/task retry | data/stream.py; core/storage.py; ops/session_report.py; supervisor | Synthetic identical-result query benchmark; real local before/after checks | No claimed root cause for upstream stale quotes or host termination |
| Calendars, DST, early closes and all-day events | Verified exchange calendar;7-day issuer freshness | Preserved last-good/failure provenance; all-day blackout stays visible | core/sessions.py; news/engine.py; owner_messages.py | Full day/holiday/DST/early-close and malformed-event tests | Genuine refresh required at actual expiry; no retimed verification |
| Three future engineering sessions | Existing minute verifier and local report | New separate local MASTER_SESSION evidence job at close+20 | ops/master_session.py; shadow_worker.py | 25-slot denominator, missing evidence fail, risk WAIT separate | All three genuine future sessions PENDING |
| All registered commands, roles, callbacks | Existing main menu and registry | Preserved, including /details; diagnostics behind commands | monitoring/command_registry.cjs; core/bot_commands.py | Dynamic command-role verification and full callback tests | External sources/handset receipt separately unverified |
| Public export/report/setup and privacy | Sanitized public Git clone and release guard | Dated report/setup/source manifest; exclude model env/private runtime | ops/release_guard.py; SETUP.md; reports/updates | Staged full-tree guard and verified remote tree required | No private records, credentials or raw licensed cache published |
| Overnight/swing, scanner, Reddit, Questrade expansion | Demonstrations/adapters retained | DEFERRED OUTSIDE CORE SCOPE; operational flags remain disabled/unconfigured | Existing advanced tools only | Existing refusal/demo tests; no expansion | Not part of this release; no credential collection or scraping |


### Reproduction commands and restrictions

```text
# Complete isolated software checks, using the already configured environments:
python -X utf8 -m ops.ci_tests
python -X utf8 -m ops.test_runner

# Frozen historical study; lawful private exports and original partition manifest:
python -m ops.primary_comparison --bars-export PRIVATE_HISTORY.json --frozen-manifest PRIVATE_MANIFEST.json --dividends PRIVATE_DISCLOSED_INPUT.json --output PRIVATE_RESULT.json
python -m ops.trend_rule_comparison --bars-export PRIVATE_HISTORY.json --output PRIVATE_DIAGNOSTIC.json

# Individual alerted-idea audit; read-only inputs, private output:
python -m ops.alert_audit --root PRIVATE_INSTALLATION --day 2026-10-21 --output PRIVATE_AUDIT.json

# Optional shadow only after its unchanged resource/access preflight passes:
python -m ops.shadow_benchmark --request PRIVATE_GENUINE_REQUEST.json --output PRIVATE_BENCHMARK.json
```

Use module `--help` and the pinned SETUP for exact supported arguments and environments. No command above is authority for subscription changes, brokerage inspection, live execution, guest development sends or a second service producer. Raw exports stay private. The review bundle supplies all tracked source, source/function indexes and sanitized verification JSON, not licensed price history.

## Annex F. Key evidence index and reading order

| Pinned source/evidence | Version or SHA-256 |
|---|---|
| [monitoring/day_schedule.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/monitoring/day_schedule.py) |  / d8a05415d7d64b00d2d5c97f861b41fd2e0b46219461ba75f0a7ce809d7584cc |
| [tests/test_final_trend_slot.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/tests/test_final_trend_slot.py) |  / 7595e839570f8f8c4751b9f02f255b3a022920f54220d2dc144d4cbf47abbee5 |
| [core/market_view.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/market_view.py) | market-view-v1 / 5dfeb0749d5b69dfb80fd97c7b74e85b4851b8475738d3b52bd80ca041050bb8 |
| [core/directional_research.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/directional_research.py) | completed-vwap-change15-v2-explicit-range / cfb5983dd30939a5394d31da4f30f5d8599fc0b45019540e7a11becc491dc21b |
| [core/observed_context.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/observed_context.py) |  / 9af3c9289faf107641c98ccd28cab8fa14243c596cde412bc3d6f1094db6eef8 |
| [strategies/idea_setups.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/idea_setups.py) | spy-ideas-v4-full-h60 / f1ae904cd95539ec87f09297abca96cb56750c7cb71f8df5c2e344aea764fa2d |
| [strategies/idea_setups_v3.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/idea_setups_v3.py) | spy-ideas-v3-entry-window / 1c99d84ba986201c2ca4e007b017b9f3cdf1061b62d6184b47b0ee7ed1db04f8 |
| [strategies/concretum.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/concretum.py) | concretum-paper-2025-v1 / f6300927f95e8a109969d93742c5df7aaebc94fc18c6dd6fe9242dcc3680f224 |
| [strategies/published_baselines.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/strategies/published_baselines.py) | published-spy-baselines-v1 / b023ff5f578b6a25bdb7400cf752099cc4f79ea5ef448e9d7530227a7c22ee55 |
| [core/research_pause.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/research_pause.py) | research-loss-episodes-v2 / ee02de3a7c3513c4eb3941d92af1f1de070a3da2665e47ff12e3ab1bad2d6597 |
| [core/primary_plan.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/primary_plan.py) | primary-plan-v2-explicit-unresolved / 649d4706282b0caa3451640fe1e28821e242a2f2004abdde4e785f7f2dc50067 |
| [core/entry_publication.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/core/entry_publication.py) | entry-publication-v1 / 9a1fa8980db0f2cec9c02e53aad9b89c844cdf14e6c0afa2eab777f4ae4ed586 |
| [options/research_contract.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/options/research_contract.py) |  / 2af88a16a68ebc4604e4e13f5a7a7b513ef841524ee58ee5bb81577ee4aa818c |
| [backtesting/option_research.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/backtesting/option_research.py) | genuine-option-bbo-replay-v1 / 340ba40c63702310ba9e96a049fe1e82ea3a7c39c04f6e34127b641fd3821b8d |
| [backtesting/research_protocol.py](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/backtesting/research_protocol.py) | spy-horizon-study-v2 / f8d5bb03eb24a27fdfb882bedcffdb433eacfd861b84830f9e76d7543eac49d2 |
| [reports/updates/2026-10-30_final-status-slot-recovery.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/updates/2026-10-30_final-status-slot-recovery.md) |  / 8c728d7f35bc03813314fb0df9ead4565b5d0d55ad9fcc50d4ff3244cba3c8c8 |
| [reports/MASTER_TEST_RESULTS.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/MASTER_TEST_RESULTS.md) |  / f6c8313abd7ce0ff3c47aa135c4471ad19b880f4e8b0f1c707fa575720f55b95 |
| [reports/MASTER_FEATURE_VERIFICATION.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/MASTER_FEATURE_VERIFICATION.md) |  / d02a87dd64537d5c7463a73edeed69459bffa0d5358d1da0c2b8fcb2e000928e |
| [reports/OWNER_ACTIONS_MASTER.md](https://github.com/jdp323/aegis-spy-research/blob/b234f6672bc20d931b9862249bcf9cbdb3fcab38/reports/OWNER_ACTIONS_MASTER.md) |  / bda311ba7f42f11b173aadf4647506b41c806ab4da4c96390ca44b1f51b67e9c |

The full machine-readable JSON and two CSV inventories enumerate the complete pinned file population and symbol locations. Review results are as-of artifacts. A later code/data change requires a new version and a new evidence packet; this document must not be silently reused as current certification.
