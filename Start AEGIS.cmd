@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run SETUP.md first. & exit /b 1)
".venv\Scripts\python.exe" -m ops.supervisor start
