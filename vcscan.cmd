@echo off
setlocal
if "%~1"=="" (
    echo [VIPERCREST SCAN] Usage: vc-scan ^<file_or_address_or_target^>
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -B "%~dp0ai_wrapper.py" "Scan %*"
exit /b %ERRORLEVEL%
