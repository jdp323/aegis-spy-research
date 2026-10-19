@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m monitoring.telegram_test --pair-test
