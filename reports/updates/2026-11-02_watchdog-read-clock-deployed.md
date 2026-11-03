# November 2 evening — watchdog post-read clock correction deployed

Local rollout occurred November 3 at 01:19 UTC (November 2 at 20:19 ET), after the completed session and recap. This supersedes only the earlier proposal's undeployed status. All earlier failure measurements, issued reports and source-hash clarifications remain as-of evidence.

## Changes

The supervisor previously evaluated stream-control telemetry against its loop-start clock, sampled before reading the SQLite snapshot. A concurrent valid refusal could have a timestamp a few milliseconds newer than that clock and be incorrectly treated as future control data. The earlier isolated race reproduction showed an unnecessary restart decision on the old source and no restart on the proposed source for that case. This does not prove the cause of any particular observed November 2 restart, provider refusal or database failure.

`stream_restart_due` now reads stream health and the last-market record in one read-only transaction, then samples the supplied evaluation clock. Its production caller supplies current aware UTC; callers omitting the optional clock retain their explicit deterministic fixture time. The same existing control predicates evaluate the coherent records against this post-read clock.

No control tolerance was expanded: genuinely future control/attempt times remain invalid; CONNECTING remains bounded below 40 seconds, CONNECTED/IDLE below 90 seconds from attempt start, permission retry plus jitter at most 301 seconds with five seconds handoff, and the existing 300-second watchdog remains. Quote, receipt, skew, heartbeat, continuity, calendar, risk and option gates are untouched. No market observation is retimed and no provider timestamp becomes a local control clock.

## Verification

Five permanent regressions cover a concurrent legitimate control update, a genuinely future control timestamp, expired retry grace, unchanged explicit fixture time, and clock sampling after both reads within one transaction. On the old source, one of these tests passed and four produced the expected missing-clock-argument errors; those results and the separate earlier behavioral race reproduction are retained. The corrected source passes all five plus all 20 existing supervisor control-progress tests.

Separate complete profiles ran on frozen private candidates, with fake transports and external network restrictions in the existing test runner:

| Profile | Main Python tests | Backtesting | Monitoring | Node | Total |
|---|---:|---:|---:|---:|---:|
| Portable | 869 | 7 | 4 | 63 | 943 |
| Installed | 859 | 7 | 4 | 62 | 932 |

Both final profiles have zero failures, errors or skips. The two deployed files match both passing isolated copies exactly; 336 other operative code files were bound to the tested installed candidate before rollout. These are software checks, not live-session reliability, entitlement or profitability evidence. No broad suite was repeated after the subsequent documentation-only edits.

Source SHA-256 values:

The frozen supervisor candidate uses LF line endings; its prior raw source used CRLF. Ignoring end-of-line whitespace shows only the optional clock argument, post-read evaluation and production caller change described above. The complete profiles ran the exact LF bytes deployed here.

- `ops/supervisor.py`: `95f6ac034d825b6d0e169782adb87689ca843db509426700bb8af5c941ab0756`
- `tests/test_supervisor_postread_clock.py`: `2f0169af085459fbbcb037d9b96c4e8d7b29d69e664772b5e168c0d44f7842ef`

### Controlled local rollout and preservation

Private reported holdings and pending authenticated requests were reviewed before the controlled stop. The exact prior supervisor bytes and existing task definition were retained for source rollback. The same single existing current-user task was restarted; its definition, action and independently queried Limited run level remain unchanged. The public export is not another running installation.

This source-only installer performed no database migration or restore. Existing WAL-aware backups were preserved. Nine immutable event-table prefixes and 413 issued artifacts were verified unchanged; configuration and sharing hashes matched. Rollback restores the source preimage and restarts the existing task, without rewinding live ledgers.

Initial post-restart telemetry still showed the former listener clock and STOPPED dispatcher record, so it was not accepted as new completed work. A later sample showed fresh supervisor, listener and dispatcher timestamps and new completed worker work after restart. Independent-monitor completed work also advanced. Two health responses returned HTTP 200. A bounded dashboard check first returned a cold REFRESHING/unavailable diagnostic view, then a populated diagnostic cache with entry state WAIT and live/execution flags false. Its cache is not current entry eligibility or private holding-monitoring proof. The old retained over-budget maintenance-cycle record was not represented as a newly completed cycle.

Initial task preflight also stopped before any runtime change because exported XML omitted the default RunLevel element. A separate native property read confirmed Limited. A script-file query was rejected by the existing execution policy; a direct native read succeeded without altering that policy. These failed preflight attempts are retained and were not treated as a completed rollout.

## Limitations

November 2 remains an engineering FAIL: 25/25 status slots API-accepted, 21 timely, 0/25 strict underlying eligibility, monitor p95 9.344 seconds and 13 failed ticks. This correction does not repair the demonstrated worker starvation, database contention, source delays or missing genuine option evidence. Its actual active-session effect requires future observation; the host was outside regular trading hours during rollout.

IEX authentication was observed after the close **before** this change, and again after restart. It is not attributed to this correction. The retained quote still has the old original source timestamp and remains stale; a connection or authentication event is not fresh BBO, SIP/OPRA access or genuine option eligibility. The cause of the earlier connection-limit refusal remains unconfirmed. No new entitlement probe, account operation, credential collection, subscription or permission change was performed.

The incumbent remains frozen and both registered candidates remain shadow-only. Genuine option outcomes are NOT_MEASURED and strategy validation remains unestablished. No BUY/SELL/TRADE_PROPOSAL kind was enabled; live/execution flags and LIVE_SIGNAL_READY remain false. User reports remain private and never establish broker fills, sale, settlement or exercise. No Telegram development test, guest development message or uncertain replay was performed by this rollout.

## Setup impact

No dependency, credential, schema, task privilege, paid service or user configuration change is required. Existing installations load the reviewed source through their single existing supervisor/task, with advancing actual work, listener/dispatcher clocks, HTTP and the populated diagnostic view checked separately. Preserve the old source, task definition, backups and issued evidence. Do not start an export as another producer or restore an old state database to undo code. Keep all scheduled slots and durable delivery controls unchanged. Windows must stay awake and online; periodic assistant reviews are not continuous exit coverage.
