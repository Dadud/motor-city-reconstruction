@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Could not create .venv. Install Python 3.11+ and try again.
    pause
    exit /b 1
  )
)
echo Installing fan-server test dependencies...
".venv\Scripts\python.exe" -m pip install -e ".[network,catalogue]"
if errorlevel 1 (
  echo Dependency install failed.
  pause
  exit /b 1
)
echo.
echo Ready. Run test-fan-server.cmd or test-fan-server-live.cmd next.
pause

