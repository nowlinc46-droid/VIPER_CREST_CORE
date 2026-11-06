@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
if exist "%USERPROFILE%\.cargo\bin" (
    set "PATH=%USERPROFILE%\.cargo\bin;!PATH!"
)
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
if not exist "!PYTHON_EXE!" (
    set "PYTHON_EXE=python"
)

cls
echo ========================================================================
echo   VIPERCREST 2.0 - UNIQUE COMPOUND 2: TREASURY SETTLEMENT GOVERNOR
echo   Dual-Executive Authorization ^& OFAC Sanctions (FP-001 Policy)
echo ========================================================================
echo.
echo [STAGE 1] Attempting High-Value Disbursement ($500k) with MISSING Auth B...
echo [*] Triggering fail-closed statutory check...
echo.
"!PYTHON_EXE!" -B "%SCRIPT_DIR%financial_cli.py" --amount 500000 --currency USD --auth-a PRESENT --auth-b MISSING --counterparty VENDOR_ALLOWLIST_01 --sanctions CLEAR
echo.
echo [STAGE 2] Submitting Counter-Signature B + OFAC Clearance Recovery Evidence...
echo [*] Advancing transaction state across T4-T5-T6...
echo.
"!PYTHON_EXE!" -B "%SCRIPT_DIR%financial_cli.py" --amount 500000 --currency USD --auth-a PRESENT --auth-b PRESENT --counterparty VENDOR_ALLOWLIST_01 --sanctions CLEAR --sanctions-age 2
echo.
echo [STAGE 3] Emitting On-Chain EVM Solidity Anchor (ViperCrestState.sol)...
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" "syntax solidity"
echo.
echo ========================================================================
echo   COMPOUND 2 COMPLETE: Financial Settlement Governed by Invariant Engine
echo ========================================================================
exit /b 0
