@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_offline.ps1" %*
exit /b %errorlevel%
