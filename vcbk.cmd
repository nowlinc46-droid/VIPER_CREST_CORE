@echo off
setlocal
call "%~dp0vc-benchmark.cmd" %*
exit /b %errorlevel%
