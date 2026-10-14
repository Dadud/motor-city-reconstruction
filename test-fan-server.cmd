@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m tools.fan_server_test
) else (
  python -m tools.fan_server_test
)
if errorlevel 1 (
  echo The tester could not start. Install Python with Tk support and the project dependencies.
  pause
)
