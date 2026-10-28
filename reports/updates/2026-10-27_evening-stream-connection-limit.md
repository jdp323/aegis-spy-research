# October27 evening review: IEX stream connection limit

Observation window: October27 19:56–20:02 ET, crossing October28 00:00 UTC. This is an after-hours diagnostic, not a live-session acceptance test.

## Changes

No production code, service configuration, credentials, sharing preferences, data thresholds or research history changed. No service restart or Telegram test was performed. This report records a newly identified operational blocker; current status, owner actions and the separate setup instructions now explain it. All earlier issued evidence remains as-of evidence.

The production IEX stream was disconnected and repeatedly recorded generic PermissionError events. The existing stream log discards authentication-response codes, so those events alone did not establish bad credentials, missing entitlement or a connection-limit cause. A separate, bounded read-only diagnostic opened one IEX socket, received the normal connected greeting, sent authentication through the existing authorized credential mechanism and received numeric error **406**. It closed without subscribing or requesting any broker information.

Alpaca documents406 as **connection limit exceeded**, separately from402 authentication failure and409 insufficient subscription. This confirms the diagnostic request encountered the provider's connection limit; it does not identify the holder of that connection or prove every earlier generic rejection had the same cause. [Alpaca WebSocket documentation](https://docs.alpaca.markets/us/docs/streaming-market-data).

## Verification

| Check | Observed result and limit |
|---|---|
| IEX market-data REST | HTTP200; returned BBO source20:00:18.750067 UTC, about four hours old at evaluation. It is rejected by strict freshness checks; REST acceptance does not establish working streaming. |
| IEX socket diagnostic | Normal greeting, authentication response406; no subscription, automatic retry or raw response text retained. |
| SIP and OPRA market-data REST | Both HTTP403, classified as entitlement rejection from provider responses. This is separate from the IEX406 finding. |
| Local service inventory | One observed AEGIS supervisor and one stream process, with the existing seven managed components. No second local AEGIS producer was found in the process inventory; this does not exclude a remote client, browser, another implementation or a provider-retained session. |
| Telegram | All25 scheduled trend receipts remain API accepted. The previously issued recap acceptance is unchanged. Listener/dispatcher heartbeats are recent; no pending authenticated owner request was found. API acceptance is not phone delivery. |
| HTTP | Health/root/API returned200. Four follow-up API requests also returned200, but the diagnostic cache was refreshing and then overdue at6.531s against its5s budget. HTTP responsiveness does not establish current analysis. |
| Worker | Recent completed work observed. One whole cycle23.016s exceeded10s; a later saved cycle3.671s did not. New-process counters0busy retries/0failures over25,916 transactions do not erase the earlier270retries/18failedtransactions. Sustained deadlines and contention remain unresolved. |
| Integrity | All57 tracked production source hashes, configuration hashes, original private-history prefixes and the issued October22 packet passed the existing read-only integrity check. |

No source change warranted another full suite. The last delivered postclose source verification remains839portable/831installed checks, zero final failures/errors/skips, with initial failures preserved in its report. Those counts are earlier evidence, not rerun tonight. The earlier inline diagnostic shell invocation failed before execution due to quoting; the corrected private file-based diagnostic completed. It did not change production state.

The current stored minute cache now contains389 genuine minutes and14 REST-origin rows, versus388/13 in the issued16:20 report. This later repair does not rewrite the original report or prove decision-time availability. The remaining gap and provider-confirmed no-print provenance stay explicit. No invented close, option outcome, personal exit, exercise or settlement is inferred.

## Remaining action

Review other devices or applications using the same Alpaca market-data identity and close an unnecessary competing IEX stream if found. If none exists, ask Alpaca to identify or release a retained connection associated with the406 response. The observed local group alone does not identify an external holder. No new credentials, key rotation, paid plan or account permission change is justified merely by406. Do not paste credentials into chat or stop unrelated applications blindly. Repeated local service restarts are not a demonstrated remedy.

After the connection becomes available, verify production AUTHENTICATED and actual original source/receipt times, then collect the required completed current-session bars and heartbeat evidence. A successful handshake or resumption of messages alone does not make analysis ready. Keep the existing bounded reconnect policy and all freshness, skew, continuity, calendar and option gates.

## Limitations

The IEX stream has not recovered in this review. The diagnostic cannot inspect other clients or clear an external/provider-held connection. It does not establish SIP/OPRA entitlement, a fresh option chain, executable option prices, strategy profitability or the next session's readiness. Strict entry and live/execution restrictions remain unchanged. No personal holding was inferred from the private report ledger. Periodic reviews remain separate from continuous monitoring.

The official calendar still has its genuine October22 verification and October29 05:44:45UTC seven-day expiry. Its retained October28 date-only HIGH event continues to enforce the all-day entry blackout; this review neither invented a release time nor renewed calendar verification.

## Setup impact

No installation or dependency change. SETUP now distinguishes the406 socket limit from credential and entitlement failures, with the smallest external recovery step above. Continue using one authoritative local supervisor and private owner-only diagnostics. No guest development message or uncertain resend occurred. [Setup](../../SETUP.md).
