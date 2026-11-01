@echo off
setlocal
echo ======================================================================
echo  VIPERCREST SECURE PURGE: Ephemeral Cache ^& Staging Self-Scrub
echo ======================================================================
if exist "%~dp0runtime\dropzone\*.tmp" del /q "%~dp0runtime\dropzone\*.tmp" 2>nul
if exist "%~dp0runtime\dropzone\*.json" del /q "%~dp0runtime\dropzone\*.json" 2>nul
if exist "%~dp0runtime\staging" rd /s /q "%~dp0runtime\staging" 2>nul
mkdir "%~dp0runtime\staging" 2>nul
mkdir "%~dp0runtime\dropzone" 2>nul
if exist "%~dp0__pycache__" rd /s /q "%~dp0__pycache__" 2>nul
if exist "%~dp0probes\__pycache__" rd /s /q "%~dp0probes\__pycache__" 2>nul
if exist "%~dp0tests\__pycache__" rd /s /q "%~dp0tests\__pycache__" 2>nul
echo [PURGE] Ephemeral dropzones and staging caches scrubbed.
echo [PURGE] Immutable SQLite ledger (runtime/viper_state.db) preserved.
exit /b 0
