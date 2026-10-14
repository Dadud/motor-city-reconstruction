@echo off
setlocal
cd /d "%~dp0"
if not defined MCO_DATA set "MCO_DATA=C:\Program Files (x86)\EA Games\Motor City Online"
if not exist "%MCO_DATA%\mcity.exe" (
  echo Original Motor City Online folder not found at:
  echo   %MCO_DATA%
  echo Edit test-fan-server-live.cmd and set MCO_DATA to your install path.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Run setup-fan-server-test.cmd first to install dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m tools.fan_server_check "%MCO_DATA%" --shard-id 44 --source nps/shardlistip.ini --login --fetch-garage %*
set "MCO_TEST_STATUS=%errorlevel%"
echo.
pause
exit /b %MCO_TEST_STATUS%

