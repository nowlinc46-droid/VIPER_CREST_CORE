@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
call "%~dp0vc-offline.cmd" %*
exit /b !errorlevel!
