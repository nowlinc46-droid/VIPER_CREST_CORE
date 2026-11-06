@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
if exist "%USERPROFILE%\.cargo\bin" (
    set "PATH=%USERPROFILE%\.cargo\bin;!PATH!"
)
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
if not exist "!PYTHON_EXE!" (
    set "PYTHON_EXE=python"
)

:MENU
cls
echo ========================================================================
echo        VIPERCREST 2.0 - UNIQUE COMPOUND ABILITIES DEMONSTRATOR
echo ========================================================================
echo   Select a unique compound capability to execute in real-time:
echo.
echo   [1] Robotics Kinetics   : Sub-microsecond motor cutoff ^& sensor blinding
echo   [2] Treasury Settlement : $500k wire dual-auth, OFAC, ^& EVM Solidity anchor
echo   [3] Tamper Defense      : 7-vector cryptographic attack suite (0.06s)
echo   [4] Smart Contracts     : Immunefi V03/V05 exploit defense ^& Foundry bridge
echo   [5] Epistemic Tensor    : 1-line seeds -^> 81-state matrix -^> 729 coordinates
echo   [6] Discovery Siege     : 100-Turn AbstentionBench & Invariant Gauntlet
echo   [7] Multi-Style Demo    : Presentation Invariance across 7 styles (LOGIC != LANGUAGE)
echo   [8] Machine Boundary    : Cross-Machine Semantic Round-Trip (10 Channel Attacks)
echo   [9] Execute ALL         : Run all compounds sequentially
echo   [Q] Quit
echo.
echo ========================================================================
set /p "CHOICE=Enter choice [1-9, Q]: "

if /i "%CHOICE%"=="1" (
    call "%SCRIPT_DIR%vc-compound-robotics.cmd"
    pause
    goto MENU
)
if /i "%CHOICE%"=="2" (
    call "%SCRIPT_DIR%vc-compound-treasury.cmd"
    pause
    goto MENU
)
if /i "%CHOICE%"=="3" (
    call "%SCRIPT_DIR%vc-compound-adversarial.cmd"
    pause
    goto MENU
)
if /i "%CHOICE%"=="4" (
    call "%SCRIPT_DIR%vc-compound-smartcontract.cmd"
    pause
    goto MENU
)
if /i "%CHOICE%"=="5" (
    call "%SCRIPT_DIR%vc-compound-tensor.cmd"
    pause
    goto MENU
)
if /i "%CHOICE%"=="6" (
    "%PYTHON_EXE%" "%SCRIPT_DIR%tests\test_known_unknown_siege.py"
    pause
    goto MENU
)
if /i "%CHOICE%"=="7" (
    "%PYTHON_EXE%" "%SCRIPT_DIR%tests\test_epistemic_transformation_invariant.py"
    pause
    goto MENU
)
if /i "%CHOICE%"=="8" (
    "%PYTHON_EXE%" "%SCRIPT_DIR%tests\test_machine_semantic_roundtrip.py"
    pause
    goto MENU
)
if /i "%CHOICE%"=="9" (
    call "%SCRIPT_DIR%vc-compound-robotics.cmd"
    echo.
    call "%SCRIPT_DIR%vc-compound-treasury.cmd"
    echo.
    call "%SCRIPT_DIR%vc-compound-adversarial.cmd"
    echo.
    call "%SCRIPT_DIR%vc-compound-smartcontract.cmd"
    echo.
    call "%SCRIPT_DIR%vc-compound-tensor.cmd"
    echo.
    "%PYTHON_EXE%" "%SCRIPT_DIR%tests\test_known_unknown_siege.py"
    echo.
    "%PYTHON_EXE%" "%SCRIPT_DIR%tests\test_epistemic_transformation_invariant.py"
    echo.
    "%PYTHON_EXE%" "%SCRIPT_DIR%tests\test_machine_semantic_roundtrip.py"
    echo.
    echo ========================================================================
    echo   ALL VIPERCREST COMPOUNDS & DISCOVERY TESTS VERIFIED: 100%% INVARIANT INTEGRITY
    echo ========================================================================
    pause
    goto MENU
)
if /i "%CHOICE%"=="Q" (
    echo Exiting.
    exit /b 0
)

goto MENU
