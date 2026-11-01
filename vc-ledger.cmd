@echo off
setlocal
echo ======================================================================
echo  VIPERCREST IMMUTABLE STATE LEDGER STATUS
echo ======================================================================
"%~dp0.venv\Scripts\python.exe" -B "%~dp0viper.py" offline --analytics %*
exit /b %ERRORLEVEL%
