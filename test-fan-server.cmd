@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup-fan-server-test.cmd first to install dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m tools.fan_server_test
if errorlevel 1 (
  echo The tester could not start. Check Python Tk support and dependencies.
  pause
)

