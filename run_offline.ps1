param(
    [string]$TargetDir = "C:\Users\nowli\Downloads\contracts-v2\contracts",
    [string]$MatchPath = "test/unit/reverse-registrar/L2ReverseRegistrar.t.sol",
    [string]$FixtureName = "offline_run.json"
)

$ErrorActionPreference = "Stop"

# Ensure Foundry is on PATH in standalone PowerShell windows
$FoundryBin = "$env:USERPROFILE\.foundry\bin"
if (Test-Path $FoundryBin) {
    $env:PATH = "$FoundryBin;$env:PATH"
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [1/3] VIPERCREST OFFLINE ENGINE SELF-TEST" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
& "C:\ViperCrest\.venv\Scripts\python.exe" -m pytest "C:\ViperCrest\tests" -q

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " [2/3] FOUNDRY OFFLINE EVM SIMULATION ($MatchPath)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Push-Location $TargetDir
try {
    & forge test --offline --match-path $MatchPath -vv
} finally {
    Pop-Location
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " [3/3] VIPERCREST F1-F9 BRIDGE & SIGNED AUDIT RECEIPT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
& "C:\ViperCrest\.venv\Scripts\python.exe" "C:\ViperCrest\bridge_foundry.py" `
    --run-forge `
    --target-dir $TargetDir `
    --match-path $MatchPath `
    --name $FixtureName

$LatestSession = Get-ChildItem "C:\ViperCrest\runtime\sessions" -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($LatestSession) {
    Write-Host "`n[SESSION BUNDLE] $($LatestSession.FullName)" -ForegroundColor Green
    Get-Content (Join-Path $LatestSession.FullName "session_meta.json")
}
