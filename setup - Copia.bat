@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" -SetupOnly
if errorlevel 1 (
  pause
  exit /b 1
)
exit /b 0
