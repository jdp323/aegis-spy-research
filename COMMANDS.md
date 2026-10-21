# Commands — generated from registry and fixture verification

Main menu: /trend /score /demo /news /more /help

Source copy, fake transports, network blocked; original ledgers untouched.

| Command | Arguments | Purpose | Fixture result |
|---|---|---|---|
| /help | [all] | Useful commands; all shows advanced tools | PASS |
| /howto |  | Quick guide to trend, morning outlook and news | PASS |
| /join | INVITATION_CODE | Join using a one-use invitation | PASS |
| /users | [PAGE_NUMBER] | Owner only: names, usernames, IDs and activity | PASS |
| /invite |  | Owner only: create a 24-hour one-use invitation | PASS |
| /revoke | ACCESS_ID | Owner only: revoke a guest’s access | PASS |
| /leave |  | Guest: disable your own access; records retained | PASS |
| /start |  | Show help and getting-started commands | PASS |
| /status |  | SPY research readiness and schedule | PASS |
| /feed |  | Provider, connection and freshness health | PASS |
| /health |  | Service health and official calendar coverage/staleness | PASS |
| /void | EVENT_ID | Append reversal of your own fill report; preserve history | PASS |
| /trend | [details] | Short gated SPY trend and research idea | PASS |
| /details |  | Horizon, source-time and entry-gate diagnostics | PASS |
| /why |  | Exact checks behind the current verdict | PASS |
| /score |  | Underlying idea outcomes: today, 7 days, 30 days and each setup | PASS |
| /fill | quantity|premium|fees|time|confirm|cancel VALUE | Answer the current actual-fill question; never submits orders | PASS |
| /more |  | All tools, grouped by purpose | PASS |
| /alerts | [CATEGORY on|off | setup NAME on|off | silent on|off] | Owner only: categories, setups and silent trends | PASS |
| /outlook |  | Clear SPY bias combining price trend and financial news | PASS |
| /sentiment |  | Wallstreetbets top-post/comment sentiment and access status | PASS |
| /research |  | Advanced saved technical research and data limits | PASS |
| /signals |  | Recent research evaluations and rejections | PASS |
| /setup |  | Latest call/put plan evaluation and exact blockers | PASS |
| /learn |  | Measured trend outcomes and improvement comparison | PASS |
| /forecast |  | Experimental closing-area estimate and limitations | PASS |
| /premarket |  | 09:15 ET saved outlook, schedule or separate premarket draft | PASS |
| /paper |  | Separate theoretical trade records | PASS |
| /plan | OCC_SYMBOL INVALIDATION T1 T2 MAX_HOLD_MINUTES | Your holding: SPY-price review conditions | PASS |
| /news |  | Financial news drivers, direction and source links | PASS |
| /request | YOUR MESSAGE | Queue research, feedback or a correction | PASS |
| /demo | start|bought|status|exit|sold|skipped|stop | Interactive fictional walkthrough | PASS |
| /option_bought | OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME [FORCE] | Report actual fill; exact duplicates require FORCE | PASS |
| /option_sold | OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME [FORCE] | Report actual disposal; exact duplicates require FORCE | PASS |
| /option_positions |  | Show your reported SPY option positions | PASS |
| /skipped | IDEA-ID | Report that you did not buy an idea | PASS |

Owner-only: users, invite, revoke, alerts. Invited members retain private fill/position reports. Stranger replies require an invitation; join accepts a genuine one-use invitation. Paper/score permissions follow existing owner-sharing rules.

V5 alert syntax: `/alerts trend_lines on|off`, `/alerts ideas on|off`, `/alerts silent on|off`, `/alerts setup SETUP_NAME on|off`. Enabling a setup explicitly overrides NEGATIVE alert suppression; it never enables live signals.

Demo scenes: `/demo start`, call, put, swing, no-trade, next, chart, bought, quantity, premium, fees, time, confirm, sold, skipped, status, stop, v5. All are simulated; none writes a real fill.

## Generated fixture message examples — not live market data
The full timestamped command verification report contains all three roles and argument variants. Below are actual valid-argument fixture replies, abbreviated. Unavailable external data is an honest fixture outcome.

### /help
```text
EXAMPLE — fixture response
AEGIS — ALL COMMANDS

/help [all] — Useful commands; all shows advanced tools
/howto — Quick guide to trend, morning outlook and news
invitation instructions — Join using a one-use invitation
/users [PAGE_NUMBER] — Owner only: names, usernames, IDs and activity
/invite — Owner only: create a 24-hour one-use invitation
/revoke ACCESS_ID — Owner only: revoke a
```

### /howto
```text
EXAMPLE — fixture response
HOW TO USE AEGIS

1. /trend — Recalculate SPY price direction when you ask. UP means the recent price checks lean upward; DOWN means downward; MIXED means disagreement. Every reply labels its price time and feed. Fresh IEX is one exchange; public bars remain historical.

2. /outlook — Read the price/news bias first, then the main drivers. If price evidence i
```

### /join
```text
EXAMPLE — fixture response
You already have access.
```

### /users
```text
EXAMPLE — fixture response
INVITED USERS — 1 active; page 1/1
Name: pending profile update
Username: not available
Telegram ID: [EXAMPLE ID]
Access ID: [EXAMPLE ID]
Joined (UTC): 2026-10-21T07:05:16.237Z
Last bot message (UTC): not recorded
Names are self-reported Telegram profiles, not verified identities.
/users PAGE_NUMBER for more; /revoke ACCESS_ID removes access.
```

### /invite
```text
EXAMPLE — fixture response
One-use invitation, expires in24hours. Share only with your intended recipient:
invitation instructions
```

### /revoke
```text
EXAMPLE — fixture response
Access ID not found.
```

### /leave
```text
EXAMPLE — fixture response
Owner access cannot be removed here.
```

### /start
```text
EXAMPLE — fixture response
AEGIS — MARKET INFORMATION

/help — Useful commands; all shows advanced tools
/trend — Short gated SPY trend and research idea
/score — Underlying idea outcomes: today, 7 days, 30 days and each setup
/more — All tools, grouped by purpose
/news — Financial news drivers, direction and source links
/demo — Interactive fictional walkthrough

Automatic morning br
```

### /status
```text
EXAMPLE — fixture response
AEGIS STATUS — signals.shared: OFF
03:05 ET · SPY unavailable
Current trend: DATA UNAVAILABLE
Next hour: unavailable — insufficient time or data
New entry: WAIT — market closed
Research · UNAVAILABLE · as of unavailable
Worker: UNVERIFIED_HEARTBEAT
Automatic public research: silent every 15 minutes 09:45 to close−15; qualifying research alerts when el
```

### /feed
```text
EXAMPLE — fixture response
AEGIS DATA HEALTH
Session: CLOSED
Provider configuration: UNAVAILABLE (configuration only)
Clock diagnostics: no recent rejection recorded; synchronization is not established by this alone.
IEX stream: UNAVAILABLE (heartbeat unverified)
IEX single-exchange quote: DATA_INCOMPLETE | no verified quote timestamp
SIP stream: UNAVAILABLE (heartbeat unverifie
```

### /health
```text
EXAMPLE — fixture response
AEGIS HEALTH · 03:05 ET
Clock: UNAVAILABLE; NTP offset UNAVAILABLE s; skew limit 2.000 s.
services: UNAVAILABLE; heartbeat UNAVAILABLE; fresh not verified
telegram: UNAVAILABLE; heartbeat UNAVAILABLE; fresh not verified
dispatcher: UNAVAILABLE; heartbeat UNAVAILABLE; fresh not verified
Calendar: DATA_INCOMPLETE; stale yes; coverage UNAVAILABLE
Questrad
```

### /void
```text
EXAMPLE — fixture response
REVERSAL_APPENDED. Original event preserved. No order placed.
```

### /trend
```text
EXAMPLE — fixture response
SPY · 03:05 ET
Trend: MIXED — timeframe agreement UNAVAILABLE
DECISION: NO TRADE
Market closed — saved context only; no live verdict.
Next open: Wed 09:30 ET
Next morning message: Wed 09:15 ET
Data: UNAVAILABLE
```

### /details
```text
EXAMPLE — fixture response
SPY RESEARCH DETAILS · 2026-10-21 03:05:33 ET
Current trend rule completed-vwap-change15-v1: completed close and 15m change must agree with session VWAP; disagreement = SIDEWAYS; missing inputs = DATA UNAVAILABLE.
Forward outlook: conditional hypothesis with VWAP invalidation, exact H60/H120/session deadlines; not calibrated odds. Current trend DATA UNAVAI
```

### /why
```text
EXAMPLE — fixture response
SPY IDEA CHECKS · 2026-10-21 03:05:37 ET
Fresh price/bar inputs: data not fresh — Quote rejected: quote timestamp unavailable; source age UNAVAILABLE, receipt age UNAVAILABLE, skew UNAVAILABLE; UNAVAILABLE
Official calendar: DATA_INCOMPLETE / UNAVAILABLE
Confirmed setups: 0
Frames: 1m unavailable · 5m unavailable · 15m unavailable · 30m unavailable · 1h 
```

### /score
```text
EXAMPLE — fixture response
SPY SCORE — UNDERLYING (not option P&L)
Population: underlying ideas only; proxy trades, option paper and forward diagnostics are separate.
Labels require 50 closed ideas per tested setup/variant. Multiple comparisons and overlapping outcomes limit these descriptive intervals.
today: 0 closed; 0 expired without entry; mean R UNAVAILABLE; 95% interval UNAV
```

### /fill
```text
EXAMPLE — fixture response
Fill flow expired. Use /option_bought for a past actual fill; never infer a suggested fill.
```

### /more
```text
EXAMPLE — fixture response
AEGIS — MORE
market: /outlook /sentiment /premarket
trades: /void /fill /plan /option_bought /option_sold /option_positions /skipped
system: /howto /start /status /feed /health /details /why /research /signals /setup /learn /forecast /paper /request
access: invitation instructions
admin: /users /invite /revoke /alerts
Score is in the main menu. Alerts: trend
```

### /alerts
```text
EXAMPLE — fixture response
ALERTS — simple
ideas: ON
idea_updates: ON
morning: ON
system: ON
periodic: OFF
changes: OFF
extended: OFF
news: OFF
sentiment: OFF
trend_lines: ON
/alerts CATEGORY on|off. No live permissions change.
signals.shared: OFF
```

### /outlook
```text
EXAMPLE — fixture response
SPY OUTLOOK | 2026-10-21 03:05 ET
BIAS: UNAVAILABLE — News language only; current price trend missing.
PRICE TREND: UNAVAILABLE | NO USABLE CURRENT PRICE TREND.
SESSION: CLOSED — regular-session trend is not running now.
Next regular open: Wed 2026-10-21 09:30 ET; morning outlook: 09:15 ET.
Overnight news is context; it cannot confirm the direction of t
```

### /sentiment
```text
EXAMPLE — fixture response
WALLSTREETBETS | 2026-10-21 03:05 ET
SENTIMENT: UNAVAILABLE | FEED_NOT_CONFIGURED
Authorized Reddit API access is not configured.
SETUP: owner needs Reddit-approved Data API access and read-only OAuth credentials in the encrypted local setup form. A Reddit website login alone does not enable the API.
Missing Reddit data is not neutral sentiment. /outlook
```

### /research
```text
EXAMPLE — fixture response
SPY TREND CHECKS: 0/4 (0% usable coverage)
Recent usable bars are missing.
Up/down percentages need current price evidence. /news shows saved research.

PROVIDER HEADLINE CHECK
DATA_INCOMPLETE; articles: 0
Query time: UNAVAILABLE
SPY-tagged headlines only. Delay UNVERIFIED. Complete macro/event coverage is not established.

DETAILED RESEARCH:
SPY |
```

### /signals
```text
EXAMPLE — fixture response
RESEARCH SIGNALS — not actionable
No research evaluations yet.
```

### /setup
```text
EXAMPLE — fixture response
SPY OPTIONS READINESS
ACTION: NO TRADE — live option recommendations are not enabled.

UNDERLYING — WAITING
No active verified US regular session; no live regular-session trend.
Next: Observe a quote at most 5 seconds old and 31 contiguous completed current-session minute bars; IEX remains single-exchange research.

OPTION_DATA — EXTERNAL_ACCESS
FEED
```

### /learn
```text
EXAMPLE — fixture response
TREND LEARNING: 0 completed observations; 0 awaiting future prices.
These are observed underlying-price results, not chances of profit.
Improvement review: COLLECTING_EVIDENCE. Small samples remain preliminary.
Earlier structure study retained: 0 completed, 0 pending.
/trend = indicator percentages | /news = detailed research
```

### /forecast
```text
EXAMPLE — fixture response
SPY CLOSING ESTIMATE
Not established: NO_FRESH_ACTIVE_SESSION_OBSERVATION.
No closing price was invented. ACTION: NO TRADE.
```

### /premarket
```text
EXAMPLE — fixture response
SPY PREMARKET REPORT
NOT DUE YET — the scheduled report is at 09:15 ET today.
No report saved for 2026-10-21.
Next scheduled report: Wed 2026-10-21 09:15 ET.
Computer must remain awake/online. /outlook and /news show current available news context.
Current-session public premarket bars start at 04:00 ET; sufficient completed bars are required. Public da
```

### /paper
```text
EXAMPLE — fixture response
PAPER / UNVALIDATED — separate populations
Underlying ideas = setup observations, not option trades: 0 tracked; 0 closed.
Underlying proxy = separate modeled SPY shares: 0 closed / 0 open; mean UNAVAILABLE USD/share.
Proxy matched-clock random-direction baseline: 0 closed; mean UNAVAILABLE USD/share.
Real-quote option paper = genuine bid/ask simulation: 
```

### /plan
```text
EXAMPLE — fixture response
Command not applied. Check /help and the required fields; no order placed.
```

### /news
```text
EXAMPLE — fixture response
SPY NEWS | 2026-10-21 03:06 ET
BIAS: UNAVAILABLE — News language only; current price trend missing.
PRICE TREND: UNAVAILABLE | NO USABLE CURRENT PRICE TREND.
SESSION: CLOSED — regular-session trend is not running now.
Next regular open: Wed 2026-10-21 09:30 ET; morning outlook: 09:15 ET.
Overnight news is context; it cannot confirm the direction of the 
```

### /request
```text
EXAMPLE — fixture response
Request fixture-76 saved for operator review. This application does not run an AI review agent or authorize trades. Contact the installation owner directly for urgent changes.
```

### /demo
```text
EXAMPLE — fixture response
🧪 DEMO — SIMULATED DATA
Choose a fictional Call, Put, Swing or No-trade day. Tap Next; no timers, no real trades.
Nothing here is real.
```

### /option_bought
```text
EXAMPLE — fixture response
RECORDED_USER_REPORT. Event ID: fixture-82. Standard SPY contracts only, multiplier100; USD premium is per share. Report saved, no order placed. Option monitoring needs valid entitled quotes; no guaranteed exit coverage.
```

### /option_sold
```text
EXAMPLE — fixture response
RECORDED_USER_REPORT. Event ID: fixture-85. Standard SPY contracts only, multiplier100; USD premium is per share. Report saved, no order placed. Option monitoring needs valid entitled quotes; no guaranteed exit coverage.
```

### /option_positions
```text
EXAMPLE — fixture response
SPY option reports (not broker verified):
SPY261014C00500000: 0 contracts; remaining cost USD0.00; realized USD68.70
No live mark/P&L available. Expired contracts require exercise/expiry reconciliation; never assumed closed.
```

### /skipped
```text
EXAMPLE — fixture response
Not-purchased report queued for the next review. No holding created.
```