@echo off
setlocal
echo [VIPERCREST AUDIT EVM] Executing Immunefi Top 10 Invariant Audit...
"%~dp0.venv\Scripts\python.exe" -B "%~dp0audit_immunefi.py" %*
exit /b %ERRORLEVEL%
