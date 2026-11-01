@echo off
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
pushd "%~dp0"
"%~dp0.venv\Scripts\python.exe" -B "%~dp0ai_wrapper.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
