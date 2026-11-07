@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=python"
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
)

pushd "%SCRIPT_DIR%"
%PYTHON_EXE% prove_mathematical_invariants.py %*
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%
