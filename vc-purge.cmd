@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
echo ======================================================================
echo  VIPERCREST SECURE PURGE: Ephemeral Cache ^& Staging Self-Scrub
echo ======================================================================
if exist "%SCRIPT_DIR%runtime\dropzone\*.tmp" del /q "%SCRIPT_DIR%runtime\dropzone\*.tmp" 2>nul
if exist "%SCRIPT_DIR%runtime\dropzone\*.json" del /q "%SCRIPT_DIR%runtime\dropzone\*.json" 2>nul
if exist "%SCRIPT_DIR%runtime\staging" rd /s /q "%SCRIPT_DIR%runtime\staging" 2>nul
mkdir "%SCRIPT_DIR%runtime\staging" 2>nul
mkdir "%SCRIPT_DIR%runtime\dropzone" 2>nul
if exist "%SCRIPT_DIR%__pycache__" rd /s /q "%SCRIPT_DIR%__pycache__" 2>nul
if exist "%SCRIPT_DIR%probes\__pycache__" rd /s /q "%SCRIPT_DIR%probes\__pycache__" 2>nul
if exist "%SCRIPT_DIR%tests\__pycache__" rd /s /q "%SCRIPT_DIR%tests\__pycache__" 2>nul
echo [PURGE] Ephemeral dropzones and staging caches scrubbed.
echo [PURGE] Immutable SQLite ledger (runtime/viper_state.db) preserved.
exit /b 0
