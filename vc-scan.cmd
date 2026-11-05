@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

if "%~1"=="" (
    echo [VIPERCREST SCAN] Usage: vc-scan ^<file_or_address_or_target^>
    echo Examples:
    echo   vc-scan USDtb.sol
    echo   vc-scan fixtures\constant_product.rs
    echo   vc-scan 0x0000000000000000000000000000000000000000
    exit /b 1
)

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
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" "Scan %*"
exit /b !errorlevel!
