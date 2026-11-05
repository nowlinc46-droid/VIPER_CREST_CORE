@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

where anvil >nul 2>&1
if !errorlevel! neq 0 (
    echo [VIPERCREST ERROR] Foundry Anvil is not found in PATH.
    echo Please install Foundry via https://getfoundry.sh or run 'foundryup'.
    exit /b 1
)

echo ======================================================================
echo  VIPERCREST PRIVATE BLOCKCHAIN SANDBOX (Anvil Local Node)
echo  RPC URL:  http://127.0.0.1:8545
echo  Chain ID: 31337
echo  (Press Ctrl+C to stop)
echo ======================================================================
anvil %*
exit /b !errorlevel!
