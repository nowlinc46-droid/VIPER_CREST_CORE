@echo off
setlocal
echo [VIPERCREST DROPZONE] Ingesting dropped files and establishing ledger hashes...
"%~dp0.venv\Scripts\python.exe" -B "%~dp0viper.py" intake %*
exit /b %ERRORLEVEL%
