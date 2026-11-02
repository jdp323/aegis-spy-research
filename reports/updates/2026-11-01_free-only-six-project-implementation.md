# AEGIS — free-only implementation, six-project review and verification

Prepared 1 November 2026. This report describes the actual local implementation and separately timestamped evidence. It supersedes conflicting presentation/provider recommendations in older handoffs. Older reports, issued session results, original failures and the October 31 expert review remain as-of evidence.

**Verdict:** the free underlying research product has been implemented and exercised locally. Initial local engineering acceptance is NOT MET: the short post-start monitor p95 exceeded one second, and IEX streaming remains refused with406. These are remaining readiness limits, not passing software-test results. Genuine-session reliability remains pending. No strategy is established as the most profitable, and genuine option performance is NOT MEASURED. Orders remain manual. Live/execution flags and LIVE_SIGNAL_READY remain false; BUY/SELL/TRADE_PROPOSAL kinds remain blocked.

## Changes

This is a software deployment, not a documentation-only review. It introduces a centrally enforced free-only network policy, one independent monitoring coordinator inside the existing worker process, indexed latest-state projections over immutable idea history, explicit unresolved public-slot closure, eight-line status messages validated by the actual dispatcher, two frozen shadow candidates, prospective IEX bid/ask capture and a five-session engineering evidence path. No paid subscription, trial, cloud server, wallet signer, model API or new brokerage account was acquired.

The owner’s broad resource authorization was applied within the master prompt’s explicit $0 incremental subscription constraint. Three coding agents worked on reliability, strategy and product interfaces; they subsequently hit an account usage limit. The coordinator continued integration, code review and verification sequentially. No upgrade or credit purchase was requested or made. This is not represented as an independent external audit.

## 1. What the six logical roles now do

| Role | Actual component | Trigger and boundary |
|---|---|---|
| Data reader and health | data/stream.py; data/free_quote_recorder.py; existing backfill/recorder | Authorized IEX messages; original source/receipt clocks retained. Bounded prospective writer queue, no model calls. |
| Trend and scenario | core/observed_context.py; core/research_horizons.py; core/market_view.py | Completed genuine bars, independent strict quote checks, versioned conditional H60 view. |
| Strategy evaluator | strategies/idea_setups.py; strategies/free_candidates.py | Incumbent remains public comparator; only two new candidates, both shadow-only. |
| Plan/risk monitor | core/fast_path.py; core/idea_service.py; core/primary_plan.py | Independent timer, one public coordinator, deadlines/conditions; private reported positions remain separate. |
| Telegram composer/dispatcher | monitoring/owner_messages.py; day_schedule.py; notifier.cjs | One presentation version, durable current-slot reservations, per-recipient parent dependencies. |
| Research reviewer | ops/free_candidate_study.py; existing research modules | Offline/maintenance only; frozen data/rules/costs; never automatically changes permissions or strategies. |

The 09:20 self-check and initial outage/recovery checks now use the independent timer, with their existing durable keys; maintenance disables its copy. A restart alone cannot generate recovery without a received market timestamp. Session reports and receipt audits remain maintenance work and their completion clocks remain independently visible.

Six roles do not mean six new processes or paid agents at runtime. The existing supervised process group and current-user task are reused. Heavy maintenance cannot receive the monitoring thread’s SQLite connection. CLI/on-demand reads are not an additional scheduled producer.

## 2. Free-provider policy and direct capability evidence

The runtime policy is `free-only-provider-v1`. Its supported operating mode is FREE_ONLY. Production REST requests are checked before transport; runtime streams request IEX only. Previously unestablished SIP/OPRA streams are recorded as POLICY_DISABLED_UNVERIFIED, with historical refusal evidence retained. There is no automatic indicative fallback.

The exact market-only probe used the existing encrypted credential child and three bounded requests. No account, balance, position, order, permission or subscription endpoint was used. Credential presence is reported only as a boolean. The observed results were:

| Feed | Direct result | Source clock UTC | Quality/refusal | Request duration |
|---|---|---|---|---|
| IEX | RESPONSE_RECEIVED | 2026-10-30T20:32:57.785016598Z | SOURCE_TOO_OLD | 0.516 s |
| SIP | REFUSED | unavailable | RECENT_SIP_PERMISSION_REFUSED | 0.156 s |
| OPRA | REFUSED | unavailable | CAUSE_UNSPECIFIED | 0.14 s |

IEX’s old Friday quote is correctly unavailable for a Sunday entry. A successful HTTP receipt is not a current market quote. The recent-SIP refusal had a recognized permission classification in its response; OPRA’s 403 did not establish a specific cause. The adapter retains only allowlisted classifications/integer codes, never the raw response body or credentials.

Capability records distinguish UNKNOWN, REFUSED, RESPONSE_RECEIVED, NOT_REQUESTED and POLICY_DISABLED_UNVERIFIED. A quote response does not prove bars, current Greeks, point-in-time chain completeness, liquidity, deliverables, free continuous monitoring or redistribution rights. The capability JSON is an as-of record, not an entitlement certificate.

The local adapter budget is at most 100 REST starts per minute and four simultaneous requests per adapter process, with no blocking wait or paid fallback on exhaustion. This is not an account-wide quota guarantee against unrelated programs. Existing 429 retry-after bounds remain; source/receipt freshness is never extended by a cooldown. An explicit capability diagnostic may inspect the allowlisted SIP quote/one-contract OPRA snapshot, but cannot silently enable them. Delayed SIP history requires a separately labelled historical purpose and an explicit end at least 15 minutes old; it cannot become live evidence.

Production retains its existing dormant Questrade preference. Free mode accepts that stored preference but does not activate Questrade keepalive, polling or token acquisition. An initial installed verification caught an over-strict preference rejection; it was corrected before restart. Neither an existing preference nor an API key proves a usable free feed.

The practical provider decision is IEX underlying research, official calendars/news and existing local services. Questrade allowances/delay flags are not assumed unlimited. Tradier account opening is excluded for the Canadian-resident plan; its documented hourly Greeks also fail the existing 60-second Greek gate. IBKR is not an established unconditional free OPRA route here; its referenced documentation fetch returned 403. No credentials or accounts were requested for these alternatives.

Official references checked for this run: [Alpaca FAQ](https://docs.alpaca.markets/us/docs/market-data-faq), [Alpaca option-chain feed definition](https://docs.alpaca.markets/us/reference/optionchain), [Questrade quote/delay warning](https://www.questrade.com/api/documentation/rest-operations/market-calls/markets-quotes-id), [Tradier data/Greek cadence](https://docs.tradier.com/docs/market-data), [Tradier residency eligibility](https://support.tradier.com/kb/guide/en/permitted-and-blocked-countries-CLzSa0D1rf/Steps/4997916). Current account responses and the stricter AEGIS gates take precedence over a provider marketing description.

## 3. Four distinct answers and private actual reports

Observed trend, conditional H60 scenario, new-entry eligibility, active public-plan coverage and private reported holdings are separate. A missing option quote cannot erase eligible completed-bar evidence. A stale underlying quote can block a new entry while a timestamped bar trend remains useful. Stale bars cannot remain a present-tense UP/DOWN signal.

The incumbent observed rule remains `completed-vwap-change15-v2-explicit-range`: last completed close C, same-feed approximate session bar VWAP V, exact 15-minute change D, minute ATR14 A and 16-bar span R. SIDEWAYS requires A>0, R<=2A, |D|<=0.25A and |C−V|<=0.5A. Otherwise UP requires C>V and D>0; DOWN reverses both; disagreement is MIXED. Missing inputs are UNAVAILABLE. These are deterministic descriptions, not move probabilities.

The `market-view-v2-free-underlying` adapter verifies current regular-session genuine endpoints, exact minute continuity, no synthetic/continuity prices, bounded availability and completed-bar end age 0–120 seconds. The 15-minute comparison needs 16 endpoints; the normal underlying entry gate still requires its original 31-slot tail. Limited early mode remains explicitly labelled. The normal completed-bar research constructor requires 31 genuine contiguous completed minutes. The existing bounded confirmed-no-print continuity exception does not supply prices or volume to indicators.

H60 is a separate `h60-vwap-condition-v3-free` hypothesis: the last two complete five-minute closes and last two complete fifteen-minute closes must move in the same direction and the latest completed price must be on that side of session VWAP. Conflicting evidence is MIXED; absent complete frames abstain. VWAP is the stated conditional invalidation, the issue-time fresh midpoint is the reference, and the target is exactly 60 minutes later only if the full period fits before verified close. H120/SESSION are not copied from this rule; this view abstains on them. Separate legacy/horizon research populations remain labelled and unpromoted.

Forecast issuance retains version, ID, source population, snapshot ID, issue/reference/target times and abstentions. The previous generic completed-price label has been corrected for typed-view midpoint references; the outcome rule identifies the matching-feed future quote window or exact completed-minute alternative. No nearest convenient future bar is substituted, no old observations are retimed, and missing outcomes remain unavailable. Premarket opening-hour lean remains separate from a full-session forecast, which abstains when unsupported.

New entries retain strict source-age <=5 seconds, receipt-age <=5 seconds, bounded configured signed skew, stream heartbeat, genuine continuity, clock, calendar and risk checks. IEX never satisfies consolidated SIP/OPRA/live gates. Public research confirmation is not option eligibility or evidence of a personal purchase.

## 4. Monitoring and database changes

`independent-monitor-timer-v1` runs inside the existing worker process with its own Store, tracker and SQLite connection. The maintenance loop omits the public tick/private-review producer while this coordinator exists. Inputs changing trigger evaluation; unchanged inputs still receive short expiry/deadline checks, and the requested 15-minute summaries remain unconditional current-slot jobs. No change-only throttling was introduced.

Normalization/features use bounded memo entries keyed to the coherent snapshot’s payload digests, population and minute. Eligibility clocks are re-evaluated; cached features never retimestamp a quote. Consumers receive independent copies, preventing later mutation of a memo. Only four feature memo entries are retained. Maintenance drains at most four completed jobs at a time. Expensive comparative/forward studies run outside the monitoring tick and are throttled in maintenance; no model is called in the monitor.

Immutable idea events remain authoritative. Additive latest-state tables and insert triggers make active/latest reads independent of replaying every historical event. External/legacy appends update the projection transactionally. Both public and horizon populations were warmed while quiescent; original event rows were compared exactly with the backups. No actual-fill table is replaced by a research projection.

| Measurement | Before | After | Scope |
|---|---|---|---|
| Latest active-state lookup | 0.012013000 s | 0.000247800 s | Same synthetic 30,000-event/600-idea/12-active fixture; five counterbalanced trials |
| Whole maintenance cycle | 581.875 s | 3.7189999998081475 | Different wall-clock cohorts; not a controlled causal benchmark |
| Health HTTP | unavailable | 200 | Bounded local observations; Sunday |
| Independent monitor | absent | 23.625 | Closed-session retained samples; future genuine session pending |

The query experiment is a labelled synthetic workload with counterbalanced warm order and identical results. The actual deployed primary ledger contained 2,165 idea events at migration, not 30,000; this experiment does not establish that history scans caused the observed 581-second worker cycle. Network/source delay, host pauses, other maintenance work and locks remain independent explanations to measure.

The monitor publishes running/completed/failed progress and appends bounded metadata records to local daily fast-path logs. Source-to-receipt, receipt-to-decision and local evaluation intervals are separate; unmeasured decode/queue stages remain unavailable. Timer overruns, database failures and startup failures remain visible. A daemon thread is not kernel isolation or cancellable work, and a two-second close timeout is not proof a thread stopped.

The prospective IEX writer uses a bounded 4,096-record queue and a separate disk thread. It retains original BBO source and receipt clocks plus persistence time in local market-capture JSONL. It rejects other feeds/simulated inputs and never labels an underlying quote as an option price. Queue drops/write failures/pending work are counted; no complete-tape or lossless-on-power-failure claim is made. Raw captures stay local and are excluded from GitHub.

The first restart exposed expensive study summaries still running inside the dashboard producer. The new default HTTP loader reads a fixed list of state keys in a short query-only SQLite snapshot and local heartbeat files; it performs no provider request, history replay or private-ledger scan. The cache still rechecks original quote/receipt clocks and denies entry readiness. Composition time is not quote time. Private position panels explicitly remain unavailable in this bounded view; /mypositions retains private reported positions and their monitoring remains separate. Heavy research summaries remain in commands/reports.

Closed-session public evaluation is skipped only outside the verified exchange-day09:00–close+20 window when no unretired active public plan exists. Every regular quarter-hour and preopen/recap window is preserved, including early closes; existing unresolved plans continue through their administrative end. Private reported-position checks are independent. Consequently the post-fix Sunday fast-path timing can include the idle public path and cannot stand in for active-session trend evaluation latency.

## 5. One public plan, immutable identity and administrative closure

Public states distinguish WATCH, ENTRY CONFIRMED, MONITORING, EXIT CONDITION REACHED, ENTRY EXPIRED, CANCELLED, COVERAGE UNKNOWN and ADMIN CLOSED UNRESOLVED. Stable IDs connect the original plan, updates and recap. Trigger, confirmation close, quote reference, modeled fill, entry limit and actual user report fields remain distinct.

An unresolved public observation no longer occupies the public slot forever. The fixed administrative end is the holding deadline plus five minutes of evidence grace. At/after that time an append-only administrative-closure event and retired-slot index commit together. The original research observation remains unresolved; no win/loss, realized price, loss-counter reset, personal fill, sale, settlement or exercise is invented. Later genuine evidence may settle research only. The grace never extends entry or holding.

Parent-before-child receipt dependencies, per-destination ordering, durable reservations and no blind replay of uncertain sends remain enforced. An initial plan’s acceptance is not phone delivery. Closing a public research slot cannot close a private reported holding or disable its monitoring warnings. Private risk remains separate from research suppression and alert-stream cooldown.

The incumbent’s entry/hold policy is preserved: full H60 from confirmation must fit before close minus 30 minutes, new entry has its existing short expiry, and expiry precedes hold deadline. Stops/targets can end a plan earlier. There is no silent extension into H120, rest-of-session or overnight.

## 6. The two frozen shadow candidates

The new candidate rule file was registered before replay outcomes at 2026-11-01T22:02:23Z. Its canonical digest is `8ee815c8e7e0cbea5ceb55c68b750b8bbd850afd90b1101c867e35a549181d40`. `strategies/idea_setups.py` remains the exact incumbent comparator, version spy-ideas-v4-full-h60, SHA-256 `f1ae904cd95539ec87f09297abca96cb56750c7cb71f8df5c2e344aea764fa2d`.

| Component | Frozen rule |
|---|---|
| ORB/breakdown | Every genuine 09:30–09:44 minute; new completed five-minute close strictly crosses the fixed range from the previous five-minute close’s inside/opposite side. |
| Pullback | Complete five-minute pullback touching/crossing prior EMA9, then a new completed close beyond prior candle high/low and current EMA9; complete fifteen-minute direction/VWAP agreement. |
| Shared direction | Close>EMA9>EMA21, above same-feed session bar VWAP and positive exact 15-minute close change; PUT reverses all. Missing values abstain. |
| Volume | Current five-minute volume at least 1.2× mean of three prior complete five-minute volumes; missing volume is not zero. |
| Structure/risk | Two complete five-minute structural extrema, distance floored at 0.5 minute Wilder ATR14; positive directional distance required. |
| Levels | Confirmation-close research reference; no-chase bound ±0.5 minute ATR; targets 1R and 2R. Reference is not an executable fill. |
| Time | Confirmation age <=60 seconds; entry expires 60 seconds after confirmation; full H60 must end before close−30 minutes. No clipping or overnight extension. |
| Arbitration | Stable rule-hashed ID, ORB before pullback, one plan per experiment cell, ten-minute same-direction cooldown. |
| Ambiguity | Stop-first if stop/target both touched in a minute; adverse gap-open stop proxy; missing required minutes leave outcomes unresolved. |
| Authority | Shadow only, broadcasts false, entry/live authority false. Passing descriptive detection never grants option/strategy eligibility. |

These functions are shared by prospective shadow evaluation and offline replay. They are not six votes over the same bars, and no funding/leverage/meme-token rules are imported. Five-minute confirmation, 15-minute summary cadence, 60-minute maximum hold and option expiry remain different clocks.

## 7. Chronological research result and its limits

The frozen input contains 16,702 retained IEX rows, including extended-session rows. The regular-session window requests 42 verified sessions from September 2 through October 30: 31 complete sessions and 15 missing regular minutes across the incomplete sessions. All 16,365 retained regular minutes lack contemporaneous receipt fields in this state export. Dates already reviewed through November 1 are development-only; none is claimed an untouched holdout.

The registered comparison has 31 policy cells: three strategy policies × three delays × two cost assumptions =18; two fixed-direction H60 baselines under the same delays/costs =12; no-trade =1. Directions are reported separately, not counted as independent days. Delays are 15/30/60 seconds; round-trip underlying cost proxies are $0.03/$0.06 per share. These are assumptions, not the owner’s actual brokerage fees.

| Policy, delay15/cost0.03 | Plans | Active sessions | Closed entries | Refused/unresolved | Net expectancy |
|---|---|---|---|---|---|
| INCUMBENT | 124 | 38 | 0 | 124 | unavailable |
| ORB_5M | 33 | 22 | 0 | 33 | unavailable |
| PULLBACK_5M_15M | 16 | 14 | 0 | 16 | unavailable |
| FIXED_10_30_H60_LONG | 42 | 42 | 0 | 42 | unavailable |
| FIXED_10_30_H60_SHORT | 42 | 42 | 0 | 42 | unavailable |

The detected candidate populations differ: the illustrated delay-15/cost-0.03 cells had 124 incumbent observations, 33 ORB observations and 16 pullback observations. They are not actual trades. The first available minute-open after a positive subminute delay lands at or after the strict 60-second entry expiry, so no executable entry qualifies in these cells. The study did not move the entry window or assume an earlier fill to generate returns. No winner was selected.

The initial diagnostic emitted zero-width day intervals for empty realized populations. Review corrected the reporting version to `free-spy-shadow-study-v1.1-no-sample`: no-sample aggregate profit, expectancy, drawdown and interval are unavailable. Original output is retained, the rule/data digests are unchanged, and no strategy parameter was selected from those outputs. An empty-flow subtotal in a direction stratum is not a measured return estimate; its sample count/mean remain explicit.

This demonstrates a data-resolution limit, not proof that all strategies lose or that the two candidates are profitable. Prospective IEX BBO capture is the free path toward measuring notification/manual delays. It remains one-exchange underlying evidence. Actual option outcomes require independently qualifying contract data. Prior Concretum/published-baseline studies and all earlier trials remain additional retrospective evidence; their advertised returns are not reproduced by this new shadow diagnostic. See the retained October 31 expert report for the original baseline equations, historical comparison cells and fourteen-alert audit.

## 8. Genuine option information

The actual option-reference boundary additionally requires explicit standard terms: matching symbol/underlying, integer 100 multiplier, deliverable 100 SPY shares, adjusted=false, allowlisted authorized contract-record/master provenance, evidence digest and verification no more than 24 hours old/not in the future. The selector preserves supplied contract terms and never fills missing ones from OCC spelling alone.

All previous gates remain: genuine non-delayed BBO with source timestamp, matching bid/ask, current timestamped Greeks/units, chain neighbors, liquidity, spread, suitable expiry beyond the hold date, paper premium/fee budget and strategy/risk separation. Unsupported adjusted contracts abstain. The demonstration’s complete contract schema is synthetic, not a received provider contract.

When eligible information exists the renderer shows contract identity/expiry/right/strike, bid/ask and source time, premium limit, 100× debit and entry fee, separately labelled premium at risk. The SPY stop does not guarantee a capped option loss or authentic future bid. Missing inputs show the underlying-only option-unavailable line. No synthetic option target/P&L or fixed-delta approximation qualifies an entry or strategy.

Current free verified capability does not supply qualifying live OPRA plus current Greeks, chain/liquidity/terms or genuine historical executable contracts. OPTION PERFORMANCE NOT MEASURED. A $500 paper cap, where configured, is not a reported account balance, live funding authorization or an affordable recommended position.

## 9. Six supplied projects: adoption and rejection

| Archive | License | SHA-256 | Snapshot treatment |
|---|---|---|---|
| day-trader-skill-main.zip | MIT | a417522153234847eeaab4f0b883de1843a3ebe9b1e3f4942581070c97562054 | Reviewed supplied ZIP |
| Kronos-master.zip | MIT | 92fc55519ddc46f22e0c8ac10a37cde73d6346818f4b8aa10f0e54c9f8a620ff | Reviewed supplied ZIP |
| OpenStock-main.zip | AGPL-3.0 | 450b107de1a679b620e1030aedda4d1e82856ec9728ae08fd250e9de0131916b | Mismatch versus supplied prompt |
| strikegrok-trading-desk-main.zip | MIT | 7b5867b7c4d5d15b3f5b5454dd50d68d239f3c6a8a51d72be39ffdb475f211ee | Reviewed supplied ZIP |
| hypergrok-trading-desk-main.zip | MIT | f688c0c2221139444024fa8c2abe1a464b9f0ad2c265c680b065e3d608da5d24 | Mismatch versus supplied prompt |
| grok-bot-grokpump-main.zip | MIT | a4d1bab6aae7f0c048975a86dae9f0f67f3f8490e9603c592d85cdb529d8d940 | Reviewed supplied ZIP |

No archive bootstrap, agent instruction, wallet path or order code was executed. The HyperGrok CLAUDE.md symlink was not followed. The selected source review is not a whole-repository security audit. Five supplied projects contain MIT notices; OpenStock contains AGPL-3.0. This implementation uses new small code for general ideas, not imported OpenStock code or a combined six-stack runtime.

The actual OpenStock and HyperGrok archive hashes differ from the prompt’s listed snapshots. The report binds the files actually supplied and does not assume another ZIP or upstream HEAD is identical. Day-trader’s clock-only opening-range completeness and later reissued old triggers were specifically not copied. Its resampled paths are not independent days, and a gap cannot be assumed capped at −1R. Kronos missing-volume zero fill/path averaging is not forecast confidence; its optional offline hardware preflight remains separate and no new inference run is claimed. OpenStock’s hourly/default and 15-second cache are display choices, not execution freshness. StrikeGrok’s funding example states no backtest; HyperGrok’s stressed linear stop arithmetic does not price options. Grok Pump’s random displayed P&L is a demo, not a profit record.

## 10. Actual Telegram product and simulated transcript

The production format/version is `owner-free-v3`, accepted by the same notifier validator/send path used in operation. Prior v1/v2 formats remain valid for historical pending envelopes; their stricter own line caps are not silently reinterpreted. New caps are preopen8/status8/plan9/follow-up5/recap8. Live-kind and research/owner labels, publication guards, parent requirements and uncertain-send handling are preserved.

Default status contains completed-bar trend/time, conditional next hour, setup watch, public-plan state, new-entry blocker, source/option capability and next summary. A blocked entry is not a plan exit. Raw predicates stay in /details, /why and /feed. Follow-ups retain the original ID, relevant immutable level and known bar/source time; monitoring freshness is not invented. Recap distinguishes new alerted plans, carried-in plans, unresolved/admin closures and silent observations, with bounded scheduled receipt counts, calendar status and /score.

The actual formatter/fake-transport run accepted 58 simulated events across complete normal/restart and stale-data days, with seven gallery fixtures. No Telegram network, real recipient, vault or guest was used. Below are actual generated fixtures, not hand-authored proposed messages or current prices:



### Fixture 1 · PREOPEN

```text
SPY PREMARKET · Oct 21 · 09:15 ET
Opening-hour lean: UP · conditional; Session lean: UNCLEAR
Premarket range: $499.00–$501.00
Bullish scenario: a completed 5m candle breaks $501.00
Bearish scenario: a completed 5m candle breaks $499.00
Events: no required scheduled event listed; optional coverage incomplete
Action: WAIT; opening range not known yet; reassess after the open. First update 09:45 ET.
Data: IEX_RESEARCH_ONLY · as of 09:10 ET; research only
```

### Fixture 2 · TREND_LINE

```text
11:00 ET · SPY $500.30
Current trend: UP through 11:00 ET completed candle
Next hour: upward bias while SPY holds above $500.00 · conditional
Setup watch: await a new completed-candle confirmation.
Public plan: NONE.
New entry: WAIT — confirmation missing
Research · IEX · as of 11:00 ET; option quote unavailable
Next summary: 11:15 ET; confirmed changes alert sooner. /details
```

### Fixture 3 · SPY_IDEA

```text
SPY SETUP CONFIRMED · research · ID aaaaaaaaaaaaaaaaaaaaaaaa · CALL direction
ENTRY CONFIRMED · a completed 1-minute close above SPY $500.10
SPY reference: $500.30; do not enter above SPY $500.80
SPY target: $501.30 · target 1 $501.00
Exit condition: SPY at or below $499.80
Planned hold: H60 · up to 60 minutes; exit by 12:00 ET
Entry expires: 11:01 ET
Underlying watch only · option contract unavailable.
Experimental · manual review; underlying levels; no guaranteed stop-loss cap
```

### Fixture 4 · IDEA_UPDATE

```text
ID aaaaaaaaaaaaaaaaaaaaaaaa · EXIT CONDITION REACHED — SPY invalidation reached in research
SPY level $499.80 · bar as of unavailable · UNAVAILABLE; monitoring freshness unverified. Research update; your fills remain separate.
```

### Fixture 5 · TREND_LINE

```text
11:00 ET · SPY $500.30
Last completed-bar trend: UP through 11:00 ET completed candle
Next hour: unavailable · conditional
Setup watch: await a new completed-candle confirmation.
Public plan aaaaaaaaaaaaaaaaaaaaaaaa: COVERAGE UNKNOWN (HOLD) · no new entry; monitoring unavailable
New entry: WAIT — fresh price unavailable
Research · IEX · as of 11:00 ET; option quote unavailable
Next summary: 11:15 ET; confirmed changes alert sooner. /details
```

### Fixture 6 · RECAP

```text
SPY RECAP · Oct 21
Ideas alerted: 1
Alerted research: 1 closed · 0 open · 0 unresolved
Option-paper dollars: unavailable without genuine quotes
Next session: wait for genuine opening-range data
Confirmed plans: 1 · 0 silent observations separate · 0 carried in
Admin closed unresolved: 0; outcomes remain unknown
Operations: not measured in this fixture/view · calendar unavailable; /score for after-cost research
```

### Fixture 7 · SPY_IDEA

```text
SPY SETUP CONFIRMED · research · ID bbbbbbbbbbbbbbbbbbbbbbbb · CALL direction
ENTRY CONFIRMED · a completed 1-minute close above SPY $500.10
SPY reference: $500.30; do not enter above SPY $500.80
SPY target: $501.30 · target 1 $501.00
Exit condition: SPY at or below $499.80
Planned hold: H60 · up to 60 minutes; exit by 12:00 ET
Entry expires: 11:01 ET
Option: SPY261023C00500000 · 2026-10-23 500.0C · bid/ask $1.90/$2.00 @ 11:00 ET; limit $2.00/share · 100× = $200.00 + $0.65 entry fee; premium at risk $200.00 + fees
Experimental · manual review; underlying levels; no guaranteed stop-loss cap
```



The full-day transcript is supplied separately. Every fixture price/contract is fictional. An unavailable field is deliberately shown rather than fabricated. Historical demo source dates retain their original fixture meaning.

## Verification

| Profile | Group | Run | Pass | Fail | Errors | Skipped |
|---|---|---|---|---|---|---|
| Portable final | tests | 861 | 861 | 0 | 0 | 0 |
| Portable final | backtesting | 7 | 7 | 0 | 0 | 0 |
| Portable final | monitoring | 4 | 4 | 0 | 0 | 0 |
| Portable final | node | 63 | 63 | 0 | 0 | 0 |
| Installed final | tests | 854 | 854 | 0 | 0 | 0 |
| Installed final | backtesting | 7 | 7 | 0 | 0 | 0 |
| Installed final | monitoring | 4 | 4 | 0 | 0 | 0 |
| Installed final | node | 62 | 62 | 0 | 0 | 0 |

Complete profile totals: Portable final 935 passed, zero final failures/errors/skips; Installed final 927 passed, zero final failures/errors/skips.

Command roles: 540 checks across 36 commands; PASS. Schedule simulation: 24 scenarios, PASS. Detailed retained attempts, failures and transports are in [verification evidence](../FREE_VERIFICATION_2026-11-01.json).

The first portable attempt had 16 failures and two errors in 845 main tests. Superseded presentation caps/version strings, explicit diagnostic purpose and additive schema expectations were corrected while retaining freshness, quota, stop-order, role, privacy and option assertions. The actual fake dispatcher also exposed the new heading/eight-line mismatch with v2; a new v3 validator contract and regressions fixed the production path. Original failures remain retained.

Installed verification then exposed the dormant Questrade preference incompatibility: 25 Python errors and one dependent Node reply failure. The corrected free policy preserves the preference without activating it. A later portable run had two strict receipt-observer wall-clock failures under host load; no timing assertion was widened. The first final installed run also retained one optional model-sandbox error: after its child-kill request, Windows did not confirm termination within the existing two-second wait. The same unchanged suite was rerun sequentially with reduced host activity; neither timeout nor assertion was widened. The host-timing failure remains evidence, and optional model termination under adverse scheduling is not certified by the later pass. The deterministic monitor performs no model call. Existing installed and portable discovery inventories differ; their totals are separate complete profiles, not counts of independent unique behaviors. Final counts above describe complete runs, not a mixture of successful partials. No broad run is repeated after passing the final unchanged source without a new failure/change.

Command-role verification exercises all 36 registered commands across five roles and three argument variants. Schedule verification covers normal, outage, restart, weekend, holidays, DST and early-close cases through actual fake notifier dispatch. Original commands and main-menu routes remain. Synthetic tests and transport acceptance do not prove a phone displayed a message or a strategy is profitable.

## 11. Backup, migration, deployment and operation evidence

Eight relevant SQLite online backups include committed WAL, full integrity checks and separately restored row-count verification. The 1.98GB observability backup’s complete copy/integrity/restore/hash work took about1,055 seconds; this is not copy-only speed or monitor latency. Source/configuration/task/report preimages were preserved. The initial preservation list contained410report files:409dated/issued artifacts and one rolling PAPER_PERFORMANCE.md view. That rolling view changed normally during the first restart. The deployment guard stopped, its old/new versions were retained, every409issued hash was rechecked, and the known partial source copy was reconciled against the passing isolated source before continuing. The original manifest was retained; it was not edited to conceal the distinction. No dated issued report was rewritten. No production database was restored or historical outcome rewound.

Additive projections were warmed in both public-idea and horizon databases, including baseline populations. Exact original event rows matched their backups after migration. Existing live/risk/sharing configuration and original issued reports were preserved; only the separately verified current official calendar changed. The existing limited current-user task definition was not edited. Rollback preserves the new append-only evidence rather than restoring an old trading state.

| Check | Observed result |
|---|---|
| at | 2026-11-01T23:52:30.216739+00:00 |
| task_definition_unchanged | True |
| task_limited | True |
| all_deployed_sources_match_passing_installed_copy | True |
| configuration_preserved | True |
| issued_artifacts_preserved | 409 |
| rolling_performance_view_preimage_preserved | True |
| database_backups_integrity_and_restore | 8 |
| start_requested_at | 2026-11-01T23:52:30.321346+00:00 |
| state | DEPLOYED_AND_LOCAL_PROGRESS_VERIFIED |
| observed_at | 2026-11-01T23:55:13.252576+00:00 |
| after_restart_cohort | Sunday closed-session; no genuine live-session readiness claim |
| supervised_components | 7 |
| components_running_and_alive | True |
| listener_dispatcher_progressed | True |
| worker_completed_phases_progressed | True |
| fast_completed_checks_progressed | True |
| last_cycle_seconds | 3.7189999998081475 |
| last_cycle_deadline_missed | False |
| health_http | 200 |
| populated_dashboard_http | 200 |
| fast_samples | 16 |
| fast_p95_seconds | 23.625 |
| fast_max_seconds | 23.625 |
| fast_failed_ticks | 0 |
| fast_deadline_misses | 6 |
| counter_reset_limit | New process counters do not erase pre-release retries/failures; different cohorts, no causal benchmark |
| aegis_scheduled_tasks | 1 |
| aegis_windows_services | 0 |
| authoritative_scheduled_producer | Existing worker independent monitor -> idea_service/day_schedule/owner_messages -> durable outbox -> existing dispatcher/notifier |
| source_export_runs_services | False |
| other_installations_scope | Matched existing AEGIS task and command lines plus source-export inventory; no global forensic claim about unrelated software |
| private_exposure_and_requests | Reviewed privately before start; no personal settlement/exercise/closure inferred |
| sharing_and_manual_execution_preserved | True |
| development_telegram_messages | 0 |
| phone_display_verified | False |
| genuine_sessions | PENDING |
| live_signal_ready | False |
| order_execution_enabled | False |
| fast_scope_limit | Latest cohort may skip public calculation outside session; not an active-session trend latency result. |

The first controlled restart remained a failed readiness observation: whole maintenance cycle152.609s, over-budget fast checks and unavailable/overdue dashboard content were retained. Later source corrections address the state-only dashboard and avoid useless closed-session public replay. Exact first-versus-later cohorts and limits are in the verification JSON.

A separate IEX authentication response at23:31:57UTC returned provider code406. [Official Alpaca streaming documentation](https://docs.alpaca.markets/us/docs/streaming-market-data) defines406 as connection-limit exceeded. A fresh local process inspection after controlled stop found no data.stream process; the identity of any external/stale holder remains unknown. The five-minute permission backoff was preserved. If that refusal persists, close the other market-data client using the existing credential, or ask Alpaca support to identify/release a stale data-stream slot; no key rotation, account inspection or paid upgrade was performed. This is separate from SIP/OPRA403 and current REST capability. The final observed stream state is in the operation record.

After-close/weekend operation is bounded local evidence. A fast timer in the same process still shares host CPU, GIL, disk and memory constraints. Health HTTP alone is not a populated dashboard, and an empty/cold view is not current market data. Reset process counters do not erase earlier busy/deadline failures. The original source/receipt delays remain preserved; no quote age, heartbeat, skew, continuity, calendar or option limit was widened.

## 12. Calendar provenance and next-session observation

The new issuer candidate was verified from direct Fed/BEA HTTPS responses and a separately labelled BLS official-page reader representation. Fresh direct BLS HTML and ICS requests both failed403; those failures are retained. The reader’s exact origin download clock is unknown; its capture/verification clock and derived representation hash are explicit. All 34 returned future-section lines were retained; six future JOBS/CPI/PPI08:30 ET rows were checked. No memory-based or invented event time was inserted.

| Field | Evidence |
|---|---|
| Verified UTC | 2026-11-01T22:41:51+00:00 |
| Expires UTC | 2026-11-08T22:41:51+00:00 |
| Coverage through UTC | 2026-12-05T04:59:59+00:00 |
| Events | 11 |
| Calendar SHA-256 | 0ad36d61ffd8f8f5a341f9bf2238849eaae75f3fef7a01f54e53d5fb10aebe8c |
| Direct BLS failures | HTML403 and ICS403 retained; official reader representation labelled separately |

The refresh preserves date-only all-day HIGH handling and last-good-on-failure behavior. Optional categories remain unknown, not assumed absent. Old calendar records/issued reports retain their original verification clocks. The earlier owner expiry warning had already been accepted once; no uncertain resend was used. Future warnings retain durable per-verification identity.

A separate prospective partition declaration reserves 20 development sessions (November 2–30), 10 validation sessions (December 1–14) and 20 final sessions (December 15–January 13). These are planned cohorts, not executed tests or automatically opened holdouts. Qualification must use the existing frozen protocol/final-access workflow and audited genuine inputs; missing days and future calendar changes stay explicit. No promotion is automatic.

Five genuine sessions are registered for November2–6 as an initial engineering window, not proof of trading edge. The normal schedule is09:15preopen,09:20owner self-check, silent09:45–15:45quarter-hour statuses, qualifying research events,16:15recap and local16:20report, relative to verified early close when applicable. After DST,09:15ET is14:15UTC. No past/missed slot is replayed as a current opportunity.

The evidence path separately records expected/accepted/on-time slots, completed-bar availability, strict underlying passes, fast-path p95, failures and unresolved verification. Targets stay all expected slots accounted, at least95% accepted within30seconds, local fast-path p95<1second, zero unhandled database failures and zero orphan/duplicate plan alerts. Unknown audit evidence cannot turn into PASS. The machine must remain awake/online; a local watchdog cannot send its own power-loss warning. Periodic assistant reviews are not continuous exit coverage.

## Limitations and readiness verdict

| Feature | Current verdict | Remaining limit |
|---|---|---|
| Free-only deterministic monitor | Implemented and locally verified | Genuine market-session source/delivery behavior pending. |
| Completed-bar trend with stale quote | Implemented/tested | Requires genuine recent same-session bars; IEX can be sparse. |
| Conditional H60 view | Implemented/tested | Not calibrated accuracy or demonstrated edge; unsupported horizons abstain. |
| One public plan and unresolved release | Implemented/tested | Public research state remains separate from actual holdings/outcomes. |
| Short Telegram/default dispatcher path | Actual fake transport verified | Real next-session acceptance and phone display are separate. |
| Genuine option contract/premium | Fails closed | Current free OPRA/Greek/chain/liquidity/terms capability incomplete. |
| Strategy comparison | Frozen diagnostic executed | No executable delayed-entry sample from these minute bars; no winner. |
| Option profitability | NOT MEASURED | Genuine matching point-in-time contracts/BBO and after-cost outcomes absent. |
| Continuous coverage | Not guaranteed | Host sleep/power/network, queues and scheduling pauses remain physical limits. |
| Initial local monitor latency target | NOT MET | 16 completed post-start checks; p95 23.625 seconds; 6 overruns; same-process/host scheduling remains a limit. |
| IEX streaming | FEED_DISCONNECTED | Provider406 connection-limit refusal retained; slot holder unknown. |
| Five-session engineering acceptance | LIVE SESSION PENDING | Future genuine records and independent dependency/coverage audit required. |

No additional API/software or paid subscription is indispensable to the delivered underlying mode. Genuine option profitability cannot be supplied from the verified current free inputs. No “best strategy,” profit promise or automatic live promotion is justified. The useful next step is observing the fixed rules and real delivery path, preserving failures and comparing genuine future evidence.

## Setup impact and operator checklist

Use the existing installation, encrypted market-data configuration and current-user task. No new package/account/hosting dependency was installed. Keep current sharing preferences and all manual-execution restrictions. Read the updated SETUP instructions before migration/rollback; the latest-state tables are rebuildable projections, not replacement histories.

1. Check the existing supervisor and independent fast-path progress, actual completed work and HTTP response; PID existence alone is insufficient.
2. Use /trend for concise views and /details or /feed for exact provenance/rejections. Treat unavailable options as unavailable.
3. Keep raw market-capture and private ledgers local. Preserve source/receipt/persistence clocks and gaps when exporting authorized research inputs.
4. Retain official-calendar freshness and failure evidence. Do not manually renew timestamps; reverify issuer inputs before expiry.
5. Review genuine-session reports and every failed/unknown target. Submit all actual trades manually and report fills separately if desired.

The accompanying bundle binds the changed source inventory, frozen rules, aggregate studies, tests, actual fixture transcript, calendar/capability records and deployment evidence with SHA-256 hashes. Private identities, credentials, actual fills, operational databases/outboxes/receipts and raw market caches are excluded. A reproducible source bundle is not a security or profitability certification.


## Evidence and changed source

- [Changed-source hashes and implementation inventory](../FREE_SOURCE_INVENTORY_2026-11-01.json)
- [Verification, retained failed attempts and scoped deployment measurements](../FREE_VERIFICATION_2026-11-01.json)
- [Complete simulated production-path transcript](../FREE_SIMULATED_TELEGRAM_DAY_2026-11-01.md)
- [Frozen comparison aggregates and limitations](../FREE_SHADOW_COMPARISON_2026-11-01.json)
- [Actual supplied archive hashes and inspected files](../FREE_SIX_ARCHIVE_INVENTORY_2026-11-01.json)
- [Direct provider capability record](../FREE_PROVIDER_CAPABILITIES_2026-11-01.json)
- [Calendar verification and preserved failures](../FREE_CALENDAR_VERIFICATION_2026-11-01.json)
- [October 31 detailed expert review, incumbent algorithms, published baselines and prior alert audit](2026-10-31_expert-review.md)

Reproduce software verification with python -m ops.test_runner, python -m ops.verify_commands, python -m ops.day_simulation and python -m ops.master_demo --output <local-demo-path>.md in an isolated configured source environment. Do not send to actual recipients. The retrospective study requires the exact authorized input dataset and manifest; raw market bars are intentionally absent from the public bundle. A matching dataset hash does not supply missing decision-time receipts or executable option quotes.

This report is an as-of implementation record. A future passing session, statistical result or option capability requires new dated evidence, never a rewritten older report.
