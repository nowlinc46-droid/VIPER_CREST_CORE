@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

if "%~1"=="" (
    echo [VIPERCREST AUDIT SOLANA] Usage: vc-audit-solana ^<solana_program_or_rs_file^>
    echo Examples:
    echo   vc-audit-solana fixtures\constant_product.rs
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

echo [VIPERCREST AUDIT SOLANA] Evaluating Anchor / Rust Invariant Spine...
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" "Scan %*"
exit /b !errorlevel!
