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
    echo [VIPERCREST PROMPT USAGE]
    echo   ask "<natural language query or command>" [--style ^<style^>]
    echo.
    echo Supported Presentation Styles:
    echo   --style plain          : Conversational context reconstruction (Default)
    echo   --style automotive     : Vehicle diagnostic OBD-II / ECU telemetry analogy
    echo   --style child          : Gentle mystery-box explanation (Zero guessing)
    echo   --style spanish        : Spanish constructive context reconstruction
    echo   --style mathematical   : Formal set-theoretic predicate evaluation
    echo   --style pseudocode     : Algorithmic epistemic retrieval logic
    echo   --style technical      : Stage F7 state machine coordinate brief
    echo.
    echo Examples:
    echo   ask "How can I remember what I forgot?"
    echo   ask "How can I remember what I forgot?" --style automotive
    echo   ask "How can I remember what I forgot?" --style child
    echo   ask "How can I remember what I forgot?" --style spanish
    echo   ask "Audit high-value wire settlement transfer $250,000"
    echo   ask "Check plant torque cutoff on sensor blinding"
    exit /b 1
)

set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"
pushd "%SCRIPT_DIR%"
"!PYTHON_EXE!" -B "%SCRIPT_DIR%ai_wrapper.py" %*
set "EXIT_CODE=!errorlevel!"
popd
exit /b !EXIT_CODE!
