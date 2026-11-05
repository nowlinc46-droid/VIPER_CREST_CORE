@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not exist "!PYTHON_EXE!" (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        echo [VIPERCREST ERROR] Python executable not found. 1>&2
        echo Please run .\bootstrap.ps1 or install Python 3.10+ in PATH. 1>&2
        exit /b 2
    )
)

set "RAW_ARGS=%*"
if not defined RAW_ARGS (
    echo [VIPERCREST PROMPT USAGE]
    echo   vcprompt "<your precise natural language query or command>"
    echo.
    echo Examples:
    echo   vcprompt "Verify discovery sanctions in case 2026-CV-99"
    echo   vcprompt "Audit high-value wire settlement transfer $250,000"
    echo   vcprompt "Scan block height continuity and parent hash"
    echo   vcprompt "Check plant torque cutoff on sensor blinding"
    exit /b 1
)

set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
pushd "%SCRIPT_DIR%"
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" %*
set "EXIT_CODE=!errorlevel!"
popd
exit /b !EXIT_CODE!
