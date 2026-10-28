# Setup with your own services

Current release: [October 27 implementation](reports/updates/2026-10-27_master-implementation.md). The current product uses compact v2 messages and one shared market view. Follow the optional shadow setup at the end only on adequate hardware; the deterministic service needs no AI key.

## Requirements

Windows 10/11, Python 3.12 (including pip and venv), Node.js 24 on PATH, and Git. These are standard runtimes; no Codex application or bundled runtime is required. Windows current-user DPAPI protects saved credentials. Other operating systems may run isolated tests, but encrypted operational credential setup is not supported there.

Create your own bot through Telegram's official @BotFather. Keep its token private. Obtain your own authorized Alpaca **market-data API** keys and verify which feeds your plan permits. No brokerage password, balance, order permissions or paid subscription is needed to inspect source or run fixtures. This project cannot grant data entitlements. No AI provider/key is used by the current rule-based engine.

## Install

Clone the public repository and run these commands in PowerShell:

~~~powershell
git clone https://github.com/jdp323/aegis-spy-research.git
cd aegis-spy-research
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-upgrade.txt
.\.venv\Scripts\python.exe -m ops.setup init
.\.venv\Scripts\python.exe -m ops.setup status
~~~

Use the venv Python for every command below. Node.js must be on PATH; optional AEGIS_NODE and AEGIS_PYTHON overrides select executable paths. AEGIS_PRIVATE_DIR can move the encrypted store. The .env.example file documents settings; .env files are **not** automatically loaded.

## Pair Telegram locally

~~~powershell
.\.venv\Scripts\python.exe -m ops.setup telegram
~~~

Enter your token only at the hidden local terminal prompt. Send the unique displayed challenge to your own bot in a private chat and press Enter. Setup verifies getMe/getChat, saves encrypted .private/telegram.dpapi and writes ignored config/telegram.json with the bot username. It sends no message and does not change webhooks. Stop any other poller for this bot first. If a webhook exists, remove it yourself through your bot administration workflow; setup fails rather than changing it. Pairing preserves any existing encrypted configuration. To replace it, stop services, privately back up the old encrypted file, move it out of the store, then pair again. Never upload it.

Optional owner-only transport test: use the configured bot's /status after startup. Do not send development messages to invited guests. A Telegram response confirms API processing only.

## Configure market data and calendar

~~~powershell
.\.venv\Scripts\python.exe -m ops.setup market
.\.venv\Scripts\python.exe -m news.calendar_updater
~~~

Market setup uses hidden prompts and current-user DPAPI. Presence of keys does not prove freshness or entitlement. Refresh the official Fed/BLS/BEA calendar with that command and inspect its provenance fields. The initial local calendar is explicitly incomplete. Do not edit verification timestamps. Expired/incomplete event data blocks entry eligibility while descriptive research reports a warning. See OPERATIONS.md for calendar procedures.

config/upgrade.json contains research defaults: live_signal_enabled=false, order_execution_enabled=false and options_risk_live_confirmed=false. Keep these false. New-install signals.shared=false; use /invite and /alerts only after privately reviewing guest access. Reported fills remain private regardless of sharing.

## Test before starting

~~~powershell
.\.venv\Scripts\python.exe -m ops.test_runner
.\.venv\Scripts\python.exe -m ops.verify_commands
.\.venv\Scripts\python.exe -m ops.day_simulation
.\.venv\Scripts\python.exe -m ops.release_guard --working-tree
~~~

Tests use isolated databases, fake clocks and fake transports. Their PASS does not establish a live-session feed or option strategy. Generated local diagnostic reports may include local paths or private state; never publish them without sanitizing.

## Run

~~~powershell
.\.venv\Scripts\python.exe -m ops.supervisor start
.\.venv\Scripts\python.exe -m ops.supervisor status
~~~

Open http://127.0.0.1:8767 on the same PC. Default status is read-only. Stop with python -m ops.supervisor stop. This installation uses localhost ports 8767/8768; do not run it beside another AEGIS instance using those ports. Startup shortcuts assume the local .venv. Optional monitoring/install_autostart.ps1 registers a current-user startup task; inspect it before running. Keep Windows awake and online.

A fresh installation has no history, calendar verification, option entitlement or research outcomes. Observe a genuine market session using /feed, /details and the session report before treating it as operationally verified. Never retime downloaded history as live data.

## Updating

Stop services, take a SQLite online backup of committed WAL data plus private configuration, review the public update report, pull changes, reinstall changed dependencies, rerun isolated tests, then restart and inspect progress/HTTP. Never replace your private configuration with another installation's files. Follow PUBLISHING.md for changes you publish.

## Operator review queue

/request saves local feedback for the installation owner to review. This repository does not install an AI agent or a hosted review service, and saving a request does not promise a response. No AI key is requested.

Status interpretation: python -m ops.supervisor status takes its evaluation clock after the file/database reads and bounded HTTP probe. Ages remain signed; a genuinely future timestamp remains negative, and an unavailable time stays unavailable. Process status is separate from market-data eligibility.

## Owner experience update — October21

The historical October 21 release used compact presentation v1. The current v2 release permits premarket8 lines, status5–7, watch/plan up to12, follow-up up to5 and recap8. Existing commands/sharing defaults remain unchanged. Restart the coordinated services using one supervisor after upgrading; compact metadata and the publication guard must travel together. Existing queued/uncertain messages retain their IDs and old presentation and must not be replayed.

The worker prepares premarket data asynchronously09:00–09:20 ET; missing preparation yields an honest unavailable outlook rather than blocking the09:15 slot. Independent latest-minute IEX repair runs alongside longer history warmup. Research pause v2 persists under its own control key, consumes each closed observation once and does not roll from silent losses during the same episode. /details describes the rule/episode. No private actual-position risk limits are reset.

/healthz now tests bounded HTTP responsiveness only; use python -m ops.supervisor status for process/heartbeat progress. Neither proves market freshness. New prospective forecast/option observations stay in private local events. No genuine option access is bundled. For reproducible underlying diagnostics see python -m ops.published_replay --help; use read-only source databases and keep raw results private. The dividend adapter permits only the documented market-data corporate-action endpoint, not account endpoints. Current provider response did not establish complete dividend history; exact Concretum evaluation remains unavailable until verified inputs exist.

Large installations can generate a bounded current packet with python -m ops.verification_packet --run-tests --compact. The ordinary150KB refusal remains unchanged; the explicit profile scans original fields for secrets before summarizing long repeated material and retains change-manifest hashes. Rejection decisions now retain append-only revision rows; legacy minute aggregates are frozen at their first snapshot. Existing traces and backup snapshots are not overwritten.

## Primary-plan release — October 22

The current release uses one active underlying research plan. Secondary detections remain separate observations. No new credentials, AI service, dependency, subscription or sharing change is required. Feed sockets now run in separate local threads/connections; continue launching one supervisor only. Restart the affected services together after updating, then inspect completed work and HTTP as described in reports/OPERATIONS_PRIMARY_PLAN.md.

New read-only research tools: python -m ops.alert_audit --help and python -m ops.primary_comparison --help. They consume your own private local records and write private outputs. Missing dividends, executable quote history or option data refuse numerical claims; do not substitute zero dividends, estimated premiums or delayed feeds. See reports/STRATEGY_COMPARISON_2026-10-22.md.

Use the Python environment where requirements-upgrade.txt is installed. The bare bundled base interpreter does not include all chart/stream dependencies; the public venv and installed .vendor workflow are verified separately. Tests and full-day simulations use fake recipients; no Telegram development broadcast is part of setup.


## October27 shared-view and optional shadow update

Upgrade the coordinated source group and restart one supervisor. Keep your existing private configuration/credential locations, sharing and ledgers. Compact-v2 entries require the new read-only transmission guard; expired/legacy entries without a guard fail closed. Do not replay uncertain sends. `python -m ops.supervisor status` is read-only and distinguishes stale status records from current work. The current-user autostart installer now uses three bounded one-minute failure retries, limited privileges and one instance.

The default deterministic product does not require an AI API key. Optional Kronos stays shadow-only and never controls entry permission. Its separate process requires1536MiB free memory, a768MiB child memory cap, a45s deadline and one CPU thread. Do not install its pins into the main venv. On adequate hardware, run:

```powershell
.\.venv\Scripts\python.exe -m ops.setup_shadow --assets-only
.\.venv\Scripts\python.exe -m ops.setup_shadow
.\.venv\Scripts\python.exe -m ops.shadow_benchmark --request YOUR_GENUINE_COMPLETED_REQUEST.json --output YOUR_BENCHMARK.json
```

The first command downloads only pinned public source/model/tokenizer assets and retains the MIT notice/content hashes in excluded .shadow-model. The second creates its own .shadow-model/venv and installs official CPU torch plus requirements-shadow pins only after resource preflight. No Hugging Face token is required for these public checkpoints. Inference is offline; no API keys enter that child. TLS verification stays enabled. Missing environment, weights, memory or valid current bars leave the deterministic service running and the model honestly unavailable. Actual pinned mini regression remains a separate required benchmark, not a mocked PASS.

Run `python -m ops.master_demo --output A_NEW_DEMO_REPORT.md` for fictional production-renderer/fake-notifier examples; it sends no Telegram message. `python -m ops.master_session --date YYYY-MM-DD --output A_NEW_SESSION_REPORT.json` reads genuine local evidence. The independent shadow process also writes a separate close+20 local engineering report. These do not establish option profitability or full-session reliability in advance. See reports/OWNER_ACTIONS_MASTER.md for the single external dependency list.


Receipt observation is now a single-flight read-only background scan (15s scan budget,60s refresh); unavailable scans never mean zero failed deliveries. No dependency or privilege change is required. The dashboard serves a bounded diagnostic cache and may return unavailable briefly while refreshing an expired snapshot; /trend performs current gates. Keep the coordinated worker/notifier/dashboard source versions together. On an existing current-user Task Scheduler installation, start its registered AEGIS task once after a controlled stop; do not create another service group.


## Postclose WAIT-reason correction — October27

The shared view now explains a quote that ages during analysis as fresh price unavailable; entry/data/option predicates are unchanged. Restart the existing coordinated service group after deploying the validated source. There are no new dependencies or credential/configuration changes. For verification, the public clone supports `python -m ops.ci_tests` with a failure-aware exit code. Historical installed packaging may instead require `python -m ops.test_runner`; inspect the complete JSON `successful` field, since that runner's exit status alone is not a test verdict. Keep private outputs outside GitHub and never replay uncertain sends.


## IEX connection-limit troubleshooting

An authentication response406 means the provider's concurrent stream connection limit was reached; it is different from invalid credentials or missing SIP/OPRA entitlement. A REST200 does not prove the stream works. Keep one local supervisor and check whether another device/application is using the same market-data identity. Close an unnecessary competing stream only after identifying it; if none is found, ask Alpaca to identify or release a retained session. Do not paste credentials into chat, rotate keys, buy a plan or change account permissions solely because of406. Preserve bounded retries and strict freshness gates. A successful reconnect still needs genuine source/receipt/heartbeat/current-session-bar verification before entry eligibility. See the [observed diagnostic](reports/updates/2026-10-27_evening-stream-connection-limit.md) and [official socket error definitions](https://docs.alpaca.markets/us/docs/streaming-market-data).
