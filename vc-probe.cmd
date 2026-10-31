@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo ViperCrest is not installed. Run bootstrap.ps1 first. 1>&2
    exit /b 2
)
echo [VIPERCREST PROBE 1/2] Running probe_matrix.py...
"%~dp0.venv\Scripts\python.exe" -B "%~dp0probes\probe_matrix.py" %*
if %errorlevel% neq 0 (
    echo Probe 1 failed with exit code %errorlevel%. 1>&2
    exit /b %errorlevel%
)
echo.
echo [VIPERCREST PROBE 2/2] Running probe_matrix_v2.py...
"%~dp0.venv\Scripts\python.exe" -B "%~dp0probes\probe_matrix_v2.py" %*
exit /b %errorlevel%
