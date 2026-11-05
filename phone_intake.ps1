<#
.SYNOPSIS
    ViperCrest Phone & USB Device Data Intake Engine (Stage F1 Ground-Truth Ingestion).
.DESCRIPTION
    Extracts telemetry and diagnostic data from connected phones or simulated devices,
    stages normalized JSON into runtime\dropzone\, anchors ground truth into the SQLite ledger,
    and triggers F1-F9 matrix execution.
#>

[CmdletBinding()]
param (
    [switch]$Simulate,
    [ValidateSet("security_anomaly", "app_db_audit", "telemetry")]
    [string]$Scenario = "security_anomaly",
    [string]$DeviceId = "PIXEL_8A_USB",
    [string]$OutputName = "",
    [switch]$NoEval
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonExe = Join-Path $ScriptDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python.exe"
}

$ArgsList = @(
    (Join-Path $ScriptDir "phone_intake.py"),
    "--scenario", $Scenario,
    "--device-id", $DeviceId
)

if ($OutputName -ne "") {
    $ArgsList += @("--output-name", $OutputName)
}

if ($Simulate) {
    $ArgsList += "--simulate"
}

if ($NoEval) {
    $ArgsList += "--no-eval"
}

Write-Host "[VC-INTAKE] Starting Phone / USB Data Intake Pipeline..." -ForegroundColor Cyan
& $PythonExe -B @ArgsList
$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Host "[VC-INTAKE] Ingestion and F1-F9 evaluation complete." -ForegroundColor Green
} else {
    Write-Host "[VC-INTAKE] Intake pipeline returned exit code $ExitCode" -ForegroundColor Yellow
}

exit $ExitCode
