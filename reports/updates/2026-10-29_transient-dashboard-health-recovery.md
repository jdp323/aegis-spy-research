# October 29: dashboard health timeouts and observed recovery

The dashboard failed five observed health checks during separate samples around 15:30–15:33 ET. The final check before a prepared controlled restart returned **200 at 15:36:38 ET**, so **no process was terminated or restarted**. These samples do not prove continuous downtime between checks or a root cause.

## Measurements and evidence

| Observation | Result |
|---|---|
| Two existing read-only status samples |Health endpoint unavailable; worker/listener/dispatcher processes still present|
| Three direct localhost health requests |TimeoutError with a two-second socket timeout; measured elapsed 2.969, 2.015 and 2.047 seconds|
| Final direct pre-restart health request |200;151-byte response;0.468 seconds|
| Restart actually performed |None; recovery occurred before the termination path|

The three direct probes bypassed proxies and fetched only the local health endpoint. They did not warm the full diagnostic view. Proxy scheme inventory was empty; no proxy root cause is established. Time-separated failures and a later success cannot establish a causal performance improvement. The health response establishes local HTTP response at that time, not continuous availability, a fresh diagnostic snapshot or market-data readiness.

The exact registered dashboard process, expected serve command and parent supervisor were checked locally before preparing recovery. The installed app.py bytes matched its retained successful full-suite copy. Source/log/status preimages were preserved privately. The final health recheck prevented an unnecessary termination. No second producer, task, installation, privilege or credential change occurred.

## Current product limits

At 15:31 ET, 23 scheduled owner statuses had received Telegram API acceptance; the 15:30 slot subsequently received acceptance at 15:31:59 ET. Acceptance is distinct from display on a phone. Private user-reported exposure and pending authenticated requests were reviewed locally; no broker account, actual fill, sale, settlement or exercise was inferred.

Actual completed worker phases resumed during the checks, while the earlier sampled whole cycle was still 92.813 seconds against a ten-second budget. Cumulative busy retries and failed transactions in that sample were 67 and16. Those failures remain unresolved; a live process or a recovered health response cannot erase them. The stored underlying bid/ask remained stale and was rejected. Existing IEX connection-limit/SIP subscription evidence and unavailable genuine option data remain separate from this dashboard incident.

The earlier [verified BEA macro report](2026-10-29_bea-growth-inflation-context.md) remains source context. Nothing here establishes a new SPY forecast, eligible entry, real option outcome or profitable strategy. The known watchdog/backoff interaction has a retained isolated diagnostic reproduction; no revised production restart policy is claimed here.

## Verification and Limitations

Five failed health observations and the successful pre-restart sample remain retained with their original timestamps. No software code changed. The unchanged app.py binding uses the October28 full installed suite; **839 installed / 847 portable checks and34 targeted checks remain earlier as-of results**, not newly executed tests. No broad suite was repeated for this operational review. Source hashes, process identity, receipts and logs are retained privately; no raw private records were exported.

No root cause was declared. There was no sustained post-recovery performance test, populated-view acceptance test or new live-session qualification. Recurrent refresh overruns, contention, source access and worker deadlines remain open work.

## Changes and setup impact

Only this report and its current-status link are new. No software/configuration/schema/history/schedule/routing change, actual restart, Telegram test send or uncertain-message replay occurred. Existing [SETUP](../../SETUP.md) remains applicable; no new installation step. Live/execution flags remain false, all orders remain manual, and private fill ledgers remain separate. Periodic checks do not provide continuous exit monitoring.
