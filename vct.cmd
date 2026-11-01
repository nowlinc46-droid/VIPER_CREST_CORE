@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo ViperCrest is not installed. Run bootstrap.ps1 first. 1>&2
    exit /b 2
)
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
pushd "%~dp0"
"%~dp0.venv\Scripts\python.exe" -B -m unittest discover -s tests -v %*
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%
