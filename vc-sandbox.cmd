@echo off
setlocal
echo ======================================================================
echo  VIPERCREST PRIVATE BLOCKCHAIN SANDBOX (Anvil Local Node)
echo  RPC URL:  http://127.0.0.1:8545
echo  Chain ID: 31337
echo  (Press Ctrl+C to stop)
echo ======================================================================
anvil %*
exit /b %ERRORLEVEL%
