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

set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
echo [VIPERCREST PROBE 1/2] Running probe_matrix.py...
"!PYTHON_EXE!" -B "%SCRIPT_DIR%probes\probe_matrix.py" %*
if !errorlevel! neq 0 (
    echo Probe 1 failed with exit code !errorlevel!. 1>&2
    exit /b !errorlevel!
)
echo.
echo [VIPERCREST PROBE 2/2] Running probe_matrix_v2.py...
"!PYTHON_EXE!" -B "%SCRIPT_DIR%probes\probe_matrix_v2.py" %*
exit /b !errorlevel!
