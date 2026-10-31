@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo ViperCrest is not installed. Run bootstrap.ps1 first. 1>&2
    exit /b 2
)
"%~dp0.venv\Scripts\python.exe" -B "%~dp0bridge_foundry.py" %*
exit /b %errorlevel%
