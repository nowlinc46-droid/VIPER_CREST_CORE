@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
call "%~dp0vc-online.cmd" %*
exit /b !errorlevel!
