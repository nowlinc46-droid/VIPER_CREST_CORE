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

echo ======================================================================
echo  VIPERCREST COMPREHENSIVE SECURITY AUDIT SUITE
echo ======================================================================
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
pushd "%SCRIPT_DIR%"
"!PYTHON_EXE!" -B "%SCRIPT_DIR%audit_invariant_engine.py" %*
set "AUDIT_EXIT=!errorlevel!"
if !AUDIT_EXIT! neq 0 (
    echo [-] Invariant engine failed with code !AUDIT_EXIT!
    popd
    exit /b !AUDIT_EXIT!
)
"!PYTHON_EXE!" -B -m unittest tests/test_adversarial_stress_vectors.py -v %*
set "ADV_EXIT=!errorlevel!"
popd
if !ADV_EXIT! neq 0 (
    echo [-] Adversarial stress suite failed with code !ADV_EXIT!
    exit /b !ADV_EXIT!
)
echo [+] All Invariant and Adversarial vectors passed successfully.
exit /b 0
