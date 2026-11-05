@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
call "%~dp0vc-scan.cmd" %*
exit /b !errorlevel!
