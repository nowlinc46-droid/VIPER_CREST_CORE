@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
call "%~dp0vc-verify.cmd" %*
set "EXIT_CODE=!errorlevel!"
if not "%~1"=="--no-pause" (
    echo.
    pause
)
exit /b !EXIT_CODE!
