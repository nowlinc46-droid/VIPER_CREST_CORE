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
    echo [VIPERCREST SYNTAX EMITTER]
    echo   Usage: vcemit ^<c ^| rust ^| solidity ^| json ^| english^>
    echo.
    echo Examples:
    echo   vcemit c          - Emits zero-malloc C99 header for ARM/RTOS
    echo   vcemit rust       - Emits no_std Rust crate types and safety gates
    echo   vcemit solidity   - Emits Solidity on-chain EVM invariant contracts
    echo   vcemit json       - Emits canonical machine AST JSON
    echo   vcemit english    - Emits authoritative plain English executive brief
    exit /b 1
)

set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
pushd "%SCRIPT_DIR%"
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" "syntax %*"
set "EXIT_CODE=!errorlevel!"
popd
exit /b !EXIT_CODE!
