@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

if "%~1"=="" (
    echo [VIPERCREST SWEEP] Usage: vc-sweep ^<drive_or_folder^> [--out record.json]
    echo Read-only search for crypto wallet artifacts. Writes a case record;
    echo secrets are never printed or stored in the record.
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
"!PYTHON_EXE!" -B "%SCRIPT_DIR%viper.py" sweep %*
exit /b !errorlevel!
