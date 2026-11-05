@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_offline.ps1" %*
exit /b !errorlevel!
