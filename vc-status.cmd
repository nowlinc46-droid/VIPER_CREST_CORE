@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
call "%~dp0vc-ledger.cmd" %*
exit /b !errorlevel!
