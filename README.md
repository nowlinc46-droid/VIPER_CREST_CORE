# ViperCrest

Independent active installation: `C:\ViperCrest`.
Preserved master version: `C:\CrateEngine\ViperCrest` (2026-10-26).
The active root is a real directory, not the former junction. No master keys,
databases, logs, sessions, virtual environment, or legacy components were copied.
The master remains intact, including the agent, dashboard, domain drivers,
original fixtures, evidence, and original signing identity. It is a preserved
version on this disk, not an off-device backup.

## Exact lean layout

```text
C:\ViperCrest\
  bootstrap.ps1
  vipercrest.cmd
  viper.py
  viper_core.py
  viper_http.py
  viper_matrix.py
  network_adapter.py
  session_router.py
  network_config.json
  requirements.txt
  README.md
  fixtures\
    example.json
    patient_records_bola.json
  probes\
    probe_matrix.py
    probe_matrix_v2.py
  tests\
    test_layout.py
    test_network_adapter.py
    test_viper_core.py
    test_viper_http.py
    test_viper_launcher.py
    test_viper_matrix.py
  .venv\                         generated isolated Python environment
  runtime\                       generated state only
    signing_key.pem
    viper_state.db
    fixtures\                    downloaded/ingested fixtures, created on demand
    intents\                     replay intents, created on demand
    dropzone\                    inert JSON intake, created on demand
    staging\                     only run-owned temporary files; cleaned per run
    sessions\                    signed five-file bundles, created on demand
    probes\                      fresh diagnostic results, created on demand
```

SQLite can create `viper_state.db-wal` and `viper_state.db-shm` while open.
Never manually delete an active database's sidecars. No physical sector folders,
legacy output trees, old logs, copied caches, dashboard, agent, or domain servers
are required in the active installation. F1-F9 stage names remain protocol
identifiers in the database, signed receipts, and diagnostic prototypes, not
directories to recreate.

## Bootstrap and permanent CLI

```powershell
& C:\ViperCrest\bootstrap.ps1
# Or select a Python 3.10+ executable:
& C:\ViperCrest\bootstrap.ps1 -Python 'C:\Program Files\Python311\python.exe'
```

Bootstrap creates an isolated environment, installs the sole direct dependency
(`cryptography`), restricts runtime ACLs to the current Windows user, creates an
independent Ed25519 key only if absent, initializes SQLite WAL, and adds this root
to the current user's persistent PATH. It does not register a daemon, scheduled
task, firewall rule, or startup service. Existing keys and evidence are not
rotated or deleted. Restart existing terminal/VS Code processes to inherit PATH.

```powershell
vipercrest --help
vipercrest matrix --target C:\ViperCrest\fixtures\example.json
vipercrest matrix --target C:\ViperCrest\fixtures\example.json --transport http --http-port 0
vipercrest offline --analytics
```

`vipercrest.cmd` always invokes this installation's environment and launcher,
regardless of the caller's working directory. Python bytecode writes are disabled.
Bootstrap is the only installation step; no environment activation is needed.

## Full line of shorthand commands

For rapid command-line execution from any directory on PATH:

| Shorthand | Long-form Alias | Target / Workflow |
| :--- | :--- | :--- |
| `vc` | `vipercrest` | Primary launcher wrapper (e.g. `vc matrix`, `vc online`, `vc offline`, or `vc m`, `vc on`, `vc off`) |
| `vcm` | `vc-matrix` | Run F1-F9 matrix fixture evaluation directly (`vipercrest matrix %*`) |
| `vco` | `vc-online` | Run controlled online HTTPS intake directly (`vipercrest online %*`) |
| `vcoff` | `vc-offline` | Run offline management, intent replay, or analytics (`vipercrest offline %*`) |
| `vcb` | `vc-bridge` | Run Universal Agnostic F1-F9 Syntax Bridge (`bridge_9x9_syntax.py %*`) |
| `vcf` | `vc-foundry` | Run Foundry Simulation Bridge (`bridge_foundry.py %*`) |
| `vct` | `vc-test` | Execute full test suite via unittest discovery (`tests\`) |
| `vcp` | `vc-probe` | Run diagnostic matrix probes (`probe_matrix.py` & `probe_matrix_v2.py`) |
| `vcs` | `vc-status` | Run database analytics and state check (`vipercrest offline --analytics`) |
| `vcr` | `vc-run` | Run offline execution script (`run_offline.ps1`) |
| `vch` | `vc-help` | Display interactive shorthand command catalog & reference |

## Controlled online intake

Edit `network_config.json`: set `NETWORK_ENABLED` to `true` and put exact,
authorized hostnames into `ALLOWED_HOSTS`. The installed configuration is used by
default, or pass `--config` explicitly. No hosts are pre-authorized.

```powershell
vipercrest online --url https://authorized.invalid/fixture.json --case-id authorized-fixture
```

The example hostname is a placeholder, not a real endpoint. HTTPS GET only,
verified TLS, port 443, exact host allowlist, no proxies, redirects, credentials,
compressed bodies, or executable payloads. Time and response size are bounded.
The response must be a supported baseline/candidate JSON fixture, not an arbitrary
website. SHA-256 hashes of raw and normalized bytes and sanitized source provenance
are retained. Patient-policy context survives normalization. Downloads and replay
intents stay in runtime, never in bundled source fixtures.

Online intake feeds the real sequential F1-F9 matrix. Every sector returns an
Ed25519-signed, request-bound SHA-256 transition receipt; final database evidence
and the exact five-file session bundle are verified before reporting completion.
Direct dispatch is socket-free; optional matrix HTTP is run-scoped loopback only.
External retrieval happens before evaluation, not as live endpoint testing.
Variance is a review signal, not a vulnerability probability or a security verdict.
Patient-policy checks require explicit caller/patient context.

Exit codes for online/matrix: 0 = completed without recorded patient-policy
violation; 1 = recorded policy violation; 2 = input, transport, signing, state,
verification, or cleanup error. Offline management retains its existing 0/1
success/error codes. Offline intent replay is the original comparison engine;
use `matrix --target` for full matrix patient-policy evaluation.

Sessions contain exactly:
`session_meta.json`, `execution_stack.ndjson`, `state_delta.json`,
`receipts_audit.sig`, and `variance_metrics.csv`.
Back up the active key and database securely together. The new active identity
does not replace the archived master's key.

## Validation and probes

```powershell
Set-Location C:\ViperCrest
& .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -B .\probes\probe_matrix.py
& .\.venv\Scripts\python.exe -B .\probes\probe_matrix_v2.py
```

The two historical prototype probes execute only in disposable temporary
workspaces. Passing their defect-reproduction tests does not certify the
prototypes. Their new reports go to `runtime\probes`; old reports remain archived.
Regression tests use temporary keys, databases, and loopback listeners. No
external target requests are made during validation.
```

```