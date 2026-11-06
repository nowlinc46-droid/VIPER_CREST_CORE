# ViperCrest close-out -- one run, three open items
# Run on Clifton's PC from PowerShell in C:\ViperCrest:
#   .\vipercrest_closeout_2026-11-05.ps1
# It only READS files and writes one text file: C:\ViperCrest\closeout_2026-11-05.txt

$Root = 'C:\ViperCrest'
$Out  = Join-Path $Root 'closeout_2026-11-05.txt'
"" | Out-File -FilePath $Out -Encoding utf8

$cargoBin = Join-Path $env:USERPROFILE '.cargo\bin'
if ((Test-Path $cargoBin) -and ($env:PATH -notlike "*$cargoBin*")) {
    $env:PATH = "$cargoBin;$env:PATH"
}

function Say([string]$text) {
    $text | Tee-Object -FilePath $Out -Append | Out-String | Write-Host
}

Say "=== ViperCrest close-out -- $(Get-Date -Format 'yyyy-MM-dd HH:mm') ==="
Say "Root: $Root"
Say ""

# --- 1. V11 seal digest: full SHA-256 of public_seal.pem and license.sig ---
Say "--- 1. V11 seal digest (public_seal.pem and license.sig SHA-256) ---"
$seal = Get-ChildItem -Path (Join-Path $Root 'runtime') -Filter 'public_seal.pem' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $seal) {
    Say "NOT FOUND: no public_seal.pem under $Root\runtime"
} else {
    Say "File: $($seal.FullName)"
    $hash = (Get-FileHash -Path $seal.FullName -Algorithm SHA256).Hash.ToLower()
    Say "SHA-256 (public_seal.pem): $hash"
    Say "Starts with 195fcfdc414 (photo prefix)? $($hash.StartsWith('195fcfdc414'))"
}

$sig = Get-ChildItem -Path (Join-Path $Root 'runtime') -Filter 'license.sig' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $sig) {
    Say "File: $($sig.FullName)"
    $sighash = (Get-FileHash -Path $sig.FullName -Algorithm SHA256).Hash.ToLower()
    Say "SHA-256 (license.sig / V11 Seal Digest): $sighash"
    Say "Starts with 195fcfdc414 (photo prefix)? $($sighash.StartsWith('195fcfdc414'))"
}
Say ""

# --- 2. Rust safety gate: full is_safe_to_actuate text ---
Say "--- 2. is_safe_to_actuate (emitted lib.rs, verbatim) ---"
$libs = Get-ChildItem -Path $Root -Filter 'lib.rs' -ErrorAction SilentlyContinue
if ($libs.Count -eq 0) {
    Say "NOT FOUND: no lib.rs under $Root"
} else {
    foreach ($lib in $libs) {
        Say "File: $($lib.FullName)"
        $lines = Get-Content -Path $lib.FullName
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match 'is_safe_to_actuate') {
                $start = [Math]::Max(0, $i - 1)
                $end = [Math]::Min($i + 8, $lines.Count - 1)
                $lines[$start..$end] | ForEach-Object { Say $_ }
                Say ""
            }
        }
    }
}

# --- 3. Real compile: rustc on the emitted lib.rs ---
Say "--- 3. rustc compile of the emitted lib.rs ---"
$hasRustc = Get-Command rustc -ErrorAction SilentlyContinue
if ($null -ne $hasRustc) {
    $rustcVer = & rustc --version
    Say "rustc: $rustcVer"
} else {
    Say "rustc: NOT FOUND on PATH"
}

$hasCargo = Get-Command cargo -ErrorAction SilentlyContinue
if ($null -ne $hasCargo) {
    $cargoVer = & cargo --version
    Say "cargo: $cargoVer"
} else {
    Say "cargo: NOT FOUND on PATH"
}

if (($libs.Count -gt 0) -and ($null -ne $hasRustc)) {
    $lib = $libs[0].FullName
    Say "Compiling: $lib"
    $build = (rustc --edition 2021 --crate-type lib "$lib" -o "$env:TEMP\vipercrest_lib.rlib" 2>&1)
    $build | ForEach-Object { Say "$_" }
    Say "rustc exit code: $LASTEXITCODE"
    Say "(Exit 0 = it compiles. Anything else, send the lines above verbatim -- do not paraphrase.)"
}
Say ""
Say "=== Done. Send back: $Out ==="
