param(
    [string]$Python = "python.exe"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
if ((Get-Item -LiteralPath $root -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw "The active project must be a real directory, not a junction or symlink."
}
$runtime = Join-Path $root "runtime"
foreach ($path in @($runtime, (Join-Path $root ".venv"))) {
    if ((Test-Path -LiteralPath $path) -and
        ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing shared runtime or environment directory: $path"
    }
}
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv (Join-Path $root ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Could not create the isolated Python environment." }
}
& $venvPython -m pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $runtime /inheritance:r /grant:r "${identity}:(OI)(CI)F"
if ($LASTEXITCODE -ne 0) { throw "Could not restrict access to runtime evidence and signing key." }
if (-not (Test-Path -LiteralPath (Join-Path $runtime "signing_key.pem"))) {
    & $venvPython -B (Join-Path $root "viper_core.py") --init-signing-key
    if ($LASTEXITCODE -ne 0) { throw "Signing key initialization failed." }
}
& $venvPython -B (Join-Path $root "viper_core.py") --init-state-db
if ($LASTEXITCODE -ne 0) { throw "SQLite WAL initialization failed." }

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$entries = @($userPath -split ";" | Where-Object { $_ })
if (-not ($entries | Where-Object { $_.TrimEnd("\") -ieq $root.TrimEnd("\") })) {
    [Environment]::SetEnvironmentVariable("Path", (($entries + $root) -join ";"), "User")
}
if (-not (($env:Path -split ";") -contains $root)) {
    $env:Path = "$root;$env:Path"
}
& (Join-Path $root "vipercrest.cmd") --help
if ($LASTEXITCODE -ne 0) { throw "Installed CLI readiness check failed." }
Write-Output "Installed: $root. Open a new terminal to use vipercrest from any directory."
Write-Output "Online intake requires NETWORK_ENABLED=true and exact authorized ALLOWED_HOSTS in network_config.json."
