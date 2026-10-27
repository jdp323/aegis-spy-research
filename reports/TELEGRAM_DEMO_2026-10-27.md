# AEGIS production-renderer demonstration

Every price, quote, event, contract and outcome below is a FICTIONAL FIXTURE. This is software behavior, not actual market evidence, a live contract or a personal fill. No Telegram network, vault or guest was used.

Actual notifier fake-transport result: {"status": "PASS", "events": 58, "calls": 58, "transport": "Actual notifier validator/send with fake client, fake clock, fixture recipient only; no network or vault"}

## Format fixtures

### Fixture 1 · PREOPEN

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

### Fixture 2 · TREND_LINE

```text
11:00 ET · SPY $500.30
Current trend: UP
Next hour: upward bias · session: upward bias
New entry: WAIT — confirmation missing
Research · IEX · as of 11:00 ET · /details
```

### Fixture 3 · SPY_IDEA

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

### Fixture 4 · IDEA_UPDATE

```text
ID aaaaaaaaaaaaaaaaaaaaaaaa · EXIT CONDITION REACHED — SPY invalidation reached in research
Research update; your fills remain separate.
```

### Fixture 5 · TREND_LINE

```text
11:00 ET · SPY $500.30
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Active plan aaaaaaaaaaaaaaaaaaaaaaaa: HOLD · no additional entry (no new entry); monitoring unavailable
Research · IEX · as of 11:00 ET · /details
```

### Fixture 6 · RECAP

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

### Fixture 7 · SPY_IDEA

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

## Full-day normal · synthetic / memory-only

{"IDEA_UPDATE": 1, "PREOPEN": 1, "RECAP": 1, "SPY_IDEA": 1, "TREND_LINE": 25}

### 2026-10-21T09:15:00-04:00 · PREOPEN

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

### 2026-10-21T09:45:00-04:00 · TREND_LINE · SILENT

```text
09:45 ET · SPY $500.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · limited early read · bar close 09:45 ET · /details
```

### 2026-10-21T09:46:00-04:00 · SPY_IDEA

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

### 2026-10-21T10:00:00-04:00 · TREND_LINE · SILENT

```text
10:00 ET · SPY $501.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · limited early read · bar close 10:00 ET · /details
```

### 2026-10-21T10:15:00-04:00 · TREND_LINE · SILENT

```text
10:15 ET · SPY $501.35
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:15 ET · /details
```

### 2026-10-21T10:30:00-04:00 · TREND_LINE · SILENT

```text
10:30 ET · SPY $501.53
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:30 ET · /details
```

### 2026-10-21T10:45:00-04:00 · TREND_LINE · SILENT

```text
10:45 ET · SPY $501.71
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:45 ET · /details
```

### 2026-10-21T10:46:00-04:00 · IDEA_UPDATE

```text
ID c33ec179fef85e55b5bcfef6 · EXIT CONDITION REACHED — holding deadline reached
Research update; your fills remain separate.
```

### 2026-10-21T11:00:00-04:00 · TREND_LINE · SILENT

```text
11:00 ET · SPY $501.89
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:00 ET · /details
```

### 2026-10-21T11:15:00-04:00 · TREND_LINE · SILENT

```text
11:15 ET · SPY $502.07
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:15 ET · /details
```

### 2026-10-21T11:30:00-04:00 · TREND_LINE · SILENT

```text
11:30 ET · SPY $502.25
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:30 ET · /details
```

### 2026-10-21T11:45:00-04:00 · TREND_LINE · SILENT

```text
11:45 ET · SPY $502.43
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:45 ET · /details
```

### 2026-10-21T12:00:00-04:00 · TREND_LINE · SILENT

```text
12:00 ET · SPY $502.61
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:00 ET · /details
```

### 2026-10-21T12:15:00-04:00 · TREND_LINE · SILENT

```text
12:15 ET · SPY $502.79
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:15 ET · /details
```

### 2026-10-21T12:30:00-04:00 · TREND_LINE · SILENT

```text
12:30 ET · SPY $502.97
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:30 ET · /details
```

### 2026-10-21T12:45:00-04:00 · TREND_LINE · SILENT

```text
12:45 ET · SPY $503.15
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:45 ET · /details
```

### 2026-10-21T13:00:00-04:00 · TREND_LINE · SILENT

```text
13:00 ET · SPY $503.33
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:00 ET · /details
```

### 2026-10-21T13:15:00-04:00 · TREND_LINE · SILENT

```text
13:15 ET · SPY $503.51
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:15 ET · /details
```

### 2026-10-21T13:30:00-04:00 · TREND_LINE · SILENT

```text
13:30 ET · SPY $503.69
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:30 ET · /details
```

### 2026-10-21T13:45:00-04:00 · TREND_LINE · SILENT

```text
13:45 ET · SPY $503.87
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:45 ET · /details
```

### 2026-10-21T14:00:00-04:00 · TREND_LINE · SILENT

```text
14:00 ET · SPY $504.05
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:00 ET · /details
```

### 2026-10-21T14:15:00-04:00 · TREND_LINE · SILENT

```text
14:15 ET · SPY $504.23
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:15 ET · /details
```

### 2026-10-21T14:30:00-04:00 · TREND_LINE · SILENT

```text
14:30 ET · SPY $504.41
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:30 ET · /details
```

### 2026-10-21T14:45:00-04:00 · TREND_LINE · SILENT

```text
14:45 ET · SPY $504.59
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:45 ET · /details
```

### 2026-10-21T15:00:00-04:00 · TREND_LINE · SILENT

```text
15:00 ET · SPY $504.77
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:00 ET · /details
```

### 2026-10-21T15:15:00-04:00 · TREND_LINE · SILENT

```text
15:15 ET · SPY $504.95
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:15 ET · /details
```

### 2026-10-21T15:30:00-04:00 · TREND_LINE · SILENT

```text
15:30 ET · SPY $505.13
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:30 ET · /details
```

### 2026-10-21T15:45:00-04:00 · TREND_LINE · SILENT

```text
15:45 ET · SPY $505.31
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:45 ET · /details
```

### 2026-10-21T16:15:00-04:00 · RECAP

```text
SPY RECAP · Oct 21
Ideas alerted: 1
Alerted research: 1 closed · 0 open · 0 unresolved
Option-paper dollars: unavailable without genuine quotes
Next session: review retained session levels in /details
Confirmed plans: 1 · 0 silent observations separate
Forward direction: H60 0/0 resolved of 25 issued; H120 0/0 resolved of 25 issued; SESSION 0/0 resolved of 25 issued · unvalidated
/score · data quality varies
```

## Full-day stale · synthetic / memory-only

{"IDEA_UPDATE": 1, "PREOPEN": 1, "RECAP": 1, "SPY_IDEA": 1, "TREND_LINE": 25}

### 2026-10-21T09:15:00-04:00 · PREOPEN

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

### 2026-10-21T09:45:00-04:00 · TREND_LINE · SILENT

```text
09:45 ET · SPY $500.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · limited early read · bar close 09:45 ET · /details
```

### 2026-10-21T09:46:00-04:00 · SPY_IDEA

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

### 2026-10-21T10:00:00-04:00 · TREND_LINE · SILENT

```text
10:00 ET · SPY $501.17
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · limited early read · bar close 10:00 ET · /details
```

### 2026-10-21T10:15:00-04:00 · TREND_LINE · SILENT

```text
10:15 ET · SPY $501.35
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:15 ET · /details
```

### 2026-10-21T10:30:00-04:00 · TREND_LINE · SILENT

```text
10:30 ET · SPY $501.53
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:30 ET · /details
```

### 2026-10-21T10:45:00-04:00 · TREND_LINE · SILENT

```text
10:45 ET · SPY $501.71
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Active plan c33ec179fef85e55b5bcfef6: HOLD · no additional entry (no new entry); monitoring unavailable
Research · SIMULATED · bar close 10:45 ET · /details
```

### 2026-10-21T10:46:00-04:00 · IDEA_UPDATE

```text
ID c33ec179fef85e55b5bcfef6 · EXIT CONDITION REACHED — holding deadline reached
Research update; your fills remain separate.
```

### 2026-10-21T11:00:00-04:00 · TREND_LINE · SILENT

```text
11:00 ET · SPY $501.89
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Research · SIMULATED · bar close 11:00 ET · /details
```

### 2026-10-21T11:15:00-04:00 · TREND_LINE · SILENT

```text
11:15 ET · SPY $502.07
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — fresh price unavailable
Research · SIMULATED · bar close 11:15 ET · /details
```

### 2026-10-21T11:30:00-04:00 · TREND_LINE · SILENT

```text
11:30 ET · SPY $502.25
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:30 ET · /details
```

### 2026-10-21T11:45:00-04:00 · TREND_LINE · SILENT

```text
11:45 ET · SPY $502.43
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 11:45 ET · /details
```

### 2026-10-21T12:00:00-04:00 · TREND_LINE · SILENT

```text
12:00 ET · SPY $502.61
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:00 ET · /details
```

### 2026-10-21T12:15:00-04:00 · TREND_LINE · SILENT

```text
12:15 ET · SPY $502.79
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:15 ET · /details
```

### 2026-10-21T12:30:00-04:00 · TREND_LINE · SILENT

```text
12:30 ET · SPY $502.97
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:30 ET · /details
```

### 2026-10-21T12:45:00-04:00 · TREND_LINE · SILENT

```text
12:45 ET · SPY $503.15
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 12:45 ET · /details
```

### 2026-10-21T13:00:00-04:00 · TREND_LINE · SILENT

```text
13:00 ET · SPY $503.33
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:00 ET · /details
```

### 2026-10-21T13:15:00-04:00 · TREND_LINE · SILENT

```text
13:15 ET · SPY $503.51
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:15 ET · /details
```

### 2026-10-21T13:30:00-04:00 · TREND_LINE · SILENT

```text
13:30 ET · SPY $503.69
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:30 ET · /details
```

### 2026-10-21T13:45:00-04:00 · TREND_LINE · SILENT

```text
13:45 ET · SPY $503.87
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 13:45 ET · /details
```

### 2026-10-21T14:00:00-04:00 · TREND_LINE · SILENT

```text
14:00 ET · SPY $504.05
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:00 ET · /details
```

### 2026-10-21T14:15:00-04:00 · TREND_LINE · SILENT

```text
14:15 ET · SPY $504.23
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:15 ET · /details
```

### 2026-10-21T14:30:00-04:00 · TREND_LINE · SILENT

```text
14:30 ET · SPY $504.41
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:30 ET · /details
```

### 2026-10-21T14:45:00-04:00 · TREND_LINE · SILENT

```text
14:45 ET · SPY $504.59
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 14:45 ET · /details
```

### 2026-10-21T15:00:00-04:00 · TREND_LINE · SILENT

```text
15:00 ET · SPY $504.77
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:00 ET · /details
```

### 2026-10-21T15:15:00-04:00 · TREND_LINE · SILENT

```text
15:15 ET · SPY $504.95
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:15 ET · /details
```

### 2026-10-21T15:30:00-04:00 · TREND_LINE · SILENT

```text
15:30 ET · SPY $505.13
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:30 ET · /details
```

### 2026-10-21T15:45:00-04:00 · TREND_LINE · SILENT

```text
15:45 ET · SPY $505.31
Last completed-bar trend: UP
Next hour: unavailable · session: unclear
New entry: WAIT — confirmation missing
Research · SIMULATED · bar close 15:45 ET · /details
```

### 2026-10-21T16:15:00-04:00 · RECAP

```text
SPY RECAP · Oct 21
Ideas alerted: 1
Alerted research: 1 closed · 0 open · 0 unresolved
Option-paper dollars: unavailable without genuine quotes
Next session: review retained session levels in /details
Confirmed plans: 1 · 0 silent observations separate
Forward direction: H60 0/0 resolved of 25 issued; H120 0/0 resolved of 25 issued; SESSION 0/0 resolved of 25 issued · unvalidated
/score · data quality varies
```
