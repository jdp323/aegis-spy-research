# Setup with your own services

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
