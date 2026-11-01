@echo off
setlocal
echo [VIPERCREST DEVICE AUDIT] Scanning connected USB / Phone hardware...
"%~dp0.venv\Scripts\python.exe" -B "%~dp0phone_intake.py" %*
exit /b %ERRORLEVEL%
