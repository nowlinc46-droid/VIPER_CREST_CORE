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

echo ==============================================================================
echo           VIPERCREST 2.0 - THE 100-TURN INVARIANT SIEGE
echo    Evaluating Long-Horizon Epistemic Stability Against Persistent Attack
echo ==============================================================================
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
pushd "%SCRIPT_DIR%"
"!PYTHON_EXE!" -B -m unittest tests/test_100_turn_invariant_siege.py -v %*
set "EXIT_CODE=!errorlevel!"
popd
exit /b !EXIT_CODE!
