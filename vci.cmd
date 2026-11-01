@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
"%SCRIPT_DIR%.venv\Scripts\python.exe" -B "%SCRIPT_DIR%phone_intake.py" %*
exit /b %ERRORLEVEL%
