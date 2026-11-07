@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=python"

pushd "%SCRIPT_DIR%"
%PYTHON_EXE% demonstrate_impossible.py %*
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%
