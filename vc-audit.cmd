@echo off
setlocal
call "%~dp0vca.cmd" %*
exit /b %errorlevel%
