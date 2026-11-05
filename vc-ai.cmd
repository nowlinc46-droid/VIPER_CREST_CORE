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

set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"

rem If no arguments provided, show prompt syntax and enter interactive mode
set "RAW_ARGS=%*"
if not defined RAW_ARGS (
    echo ======================================================================
    echo           VIPERCREST AI - PRECISE NATURAL LANGUAGE PROMPTS             
    echo ======================================================================
    echo  Examples of precise prompts you can type directly:
    echo.
    echo   [LEGAL DISCOVERY]
    echo     vcai "Verify discovery sanctions in case 2026-CV-99"
    echo     vcai "Audit tenant notice of default under lease section 14.2"
    echo.
    echo   [SECURITY ^& BLOCKCHAIN]
    echo     vcai "Scan contract 0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
    echo     vcai "eth_blockNumber"
    echo.
    echo   [LOGISTICS ^& SENSOR]
    echo     vcai "Audit reefer temperature excursion at -12.4C setpoint -20.0C"
    echo.
    echo   [SYSTEM ^& EXPLANATION]
    echo     vcai "Check system status"
    echo     vcai "Why is coordinate T5:S7 unresolved?"
    echo ======================================================================
    echo.
)

pushd "%SCRIPT_DIR%"
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" %*
set "EXIT_CODE=!errorlevel!"
popd
exit /b !EXIT_CODE!
