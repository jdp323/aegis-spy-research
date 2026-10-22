# October 21 individual alerted-idea audit

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

## Frozen sensitivity results

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
