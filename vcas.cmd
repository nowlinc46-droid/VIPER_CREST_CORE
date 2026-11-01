@echo off
setlocal
if "%~1"=="" (
    echo [VIPERCREST AUDIT SOLANA] Usage: vc-audit-solana ^<solana_program_or_rs_file^>
    exit /b 1
)
echo [VIPERCREST AUDIT SOLANA] Evaluating Anchor / Rust Invariant Spine...
"%~dp0.venv\Scripts\python.exe" -B "%~dp0ai_wrapper.py" "Scan %*"
exit /b %ERRORLEVEL%
