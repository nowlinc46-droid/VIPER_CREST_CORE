@echo off
setlocal
call "%~dp0vc-reader.cmd" %*
exit /b %errorlevel%
