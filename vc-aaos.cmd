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
        echo [VIPER ERROR] Python executable not found. 1>&2
        echo Please ensure Python 3.10+ is available in PATH. 1>&2
        exit /b 2
    )
)

set "PYTHONPATH=%SCRIPT_DIR%;!PYTHONPATH!"
pushd "%SCRIPT_DIR%"
"!PYTHON_EXE!" -B "%SCRIPT_DIR%os_builder\aaos_cli.py" %*
set "EXIT_CODE=!errorlevel!"
popd
exit /b !EXIT_CODE!
