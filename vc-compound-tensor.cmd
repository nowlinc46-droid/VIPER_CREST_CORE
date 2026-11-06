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
echo   VIPERCREST 2.0 - UNIQUE COMPOUND 5: 729-COORDINATE EPISTEMIC TENSOR
echo   Minimal Atomic Seed Hydration Across 3 Heterogeneous Domains
echo ========================================================================
echo.
echo [STAGE 1] Ingesting 3 Atomic Strings across Security, Legal, Logistics...
echo [*] Hydrating into 81-Coordinate Matrix without Speculation...
echo.
"!PYTHON_EXE!" -B "%SCRIPT_DIR%minimal_seed_benchmark.py"
echo.
echo [STAGE 2] Generating Bates-Stamped Executive Brief for Court / Regulators...
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" "syntax english"
echo.
echo ========================================================================
echo   COMPOUND 5 COMPLETE: Multi-Domain Knowledge Bound to Verified Proof
echo ========================================================================
exit /b 0
