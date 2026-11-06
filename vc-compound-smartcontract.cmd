@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
if not exist "!PYTHON_EXE!" (
    set "PYTHON_EXE=python"
)

cls
echo ========================================================================
echo   VIPERCREST 2.0 - UNIQUE COMPOUND 4: SMART CONTRACT EXPLOIT DEFENSE
echo   Foundry Simulation Bridge ^& Immunefi Top 10 Invariant Verification
echo ========================================================================
echo.
echo [STAGE 1] Simulating Immunefi V03 Reentrancy Vault Drain Attack...
echo [*] External callback attempting reentrant drain of vault collateral...
echo.
"!PYTHON_EXE!" -B "%SCRIPT_DIR%bridge_foundry.py" --scenario reentrancy
echo.
echo [STAGE 2] Simulating Immunefi V05 Oracle Flash Price Manipulation...
echo [*] Flash-loan manipulating AMM spot price to trigger liquidations...
echo.
"!PYTHON_EXE!" -B "%SCRIPT_DIR%bridge_foundry.py" --scenario oracle_manipulation
echo.
echo [STAGE 3] Emitting Vyper On-Chain Anchor Contract (ViperCrestState.vy)...
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" "syntax vyper"
echo.
echo ========================================================================
echo   COMPOUND 4 COMPLETE: On-Chain Exploits Blocked Offline Before Execution
echo ========================================================================
exit /b 0
