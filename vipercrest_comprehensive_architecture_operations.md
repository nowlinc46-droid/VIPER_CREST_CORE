# ViperCrest: Comprehensive Architecture & Operations Manual

## 1. Executive Summary & Core Invariants

**ViperCrest** (`C:\CrateEngine\ViperCrest`) is a secure, offline-first fixture analyzer engineered around a fixed nine-sector evaluation pipeline ($F_1$ through $F_9$). 

* **Strict Air-Gapped Operation:** The engine makes no default network requests, performs no dynamic target discovery, and executes no downloaded code or payloads.
* **Cryptographic Provenance:** Every execution event, state transition, and audit artifact is secured via local Ed25519 signing (`v6_sign\signing_key.pem`) and SHA-256 content hashing.
* **Transactional State:** Database operations are managed via SQLite WAL (Write-Ahead Logging) mode, ensuring crash-resilient concurrency and tamper-evident local audit trails (`viper_state.db`).
* **Deterministic Scoring:** Bounded structural variance scoring evaluates baseline-candidate deltas. Scores are observations for human review ($\ge 0.05$ threshold), never statistical probabilities or vulnerability verdicts.

---

## 2. Unified CLI Launcher (`viper.py`)

All engine subcomponents, agents, domain simulators, and web dashboards are unified under a single dispatch entry point. No background daemons or multi-process pools start automatically.

```powershell
# General Help & Component Options
python .\viper.py --help

# Offline Execution & Management
python .\viper.py offline --intent .\intents\example.json
python .\viper.py offline --ingest-dropzone
python .\viper.py offline --analytics

# Autonomous Local Agent & Diagnostics Dashboard
python .\viper.py agent
python .\viper.py dashboard

# Multi-Domain Policy Simulations (solana, evm, fhir, cmmc, pci, scada, ai_governance)
python .\viper.py domain solana
```

---

## 3. Secure Code Ingestion & Network Architecture

### Local Code Ingestion Module
ViperCrest supports automated local code ingestion from designated intake directories (e.g., `C:\CrateEngine\ViperCrest\intake` or dropzones):
* Scans specified source files (`.py`, `.js`, `.ts`, `.rs`, `.go`, `.c`, `.cpp`).
* Calculates SHA-256 content hashes, line counts, file sizes, and detected language metadata.
* Logs ingestion events into SQLite WAL with TamperGuard chain-of-custody and Ed25519 manifest signing.
* Enforces path-confined validation to prevent directory traversal outside local boundaries.

### Optional Controlled Online Fixture Intake
Disabled by default (`NETWORK_ENABLED: false` in `network_config.json`). When explicitly enabled, network intake is strictly bounded:
* **Protocols & Methods:** GET requests only on HTTPS port 443 with verified TLS.
* **Constraints:** Zero redirects (including same-host redirects), no environment proxies, no URL credentials, and no external cookie/token injection.
* **Limits:** Size-bounded UTF-8 JSON output (configured body limit plus one overflow-detection byte).
* **Configuration Template (`network_config.json`):**
  ```json
  {
    "NETWORK_ENABLED": false,
    "ALLOWED_HOSTS": [],
    "ALLOWED_METHODS": ["GET"],
    "TIMEOUT_SECONDS": 10,
    "MAX_RESPONSE_BYTES": 1048576
  }
  ```
* **Execution Example (Authorized Non-Production Target):**
  ```powershell
  python .\viper.py online --config .\network_config.json --url https://authorized.invalid/fixture.json --case-id authorized-fixture
  ```

---

## 4. Autonomous Local Agent (`viper_agent.py`)

The agent provides a bounded observe/select/act/record ReAct loop around the core engine without altering its fixed nine-sector layout.

* **Single-Pass Mode (Idle Drain):**
  ```powershell
  python .\viper_agent.py
  ```
* **Continuous Polling Mode:**
  ```powershell
  python .\viper_agent.py --continuous --max-iterations 1000 --poll-seconds 2
  ```
* **Local Ollama Integration (Air-Gapped Loopback Reasoning):**
  ```powershell
  python .\viper_agent.py --ollama-model 'llama3'
  ```
  * *Constraints:* Binds strictly to `http://127.0.0.1:11434/api/generate` with `OLLAMA_NO_CLOUD=1`. Transmits only anonymized 9-sector variance metrics and structural telemetry—never source bodies, credentials, or keys. Falls back to deterministic heuristics if unavailable.

---

## 5. Local Session Diagnostics & Dashboard

Every successfully persisted core or domain run generates an isolated session folder under `sessions\session_<UTC timestamp>_<run_id>\` containing exactly five immutable files:

1. `session_meta.json` — Run identity, timestamp, fixture seed hash, exit status, and receipt state.
2. `execution_stack.ndjson` — Filtered WARN/ERROR/FATAL policy events (stack traces truncated).
3. `state_delta.json` — Changed before/after values and SHA-256 comparisons.
4. `receipts_audit.sig` — Signed audit payload, artifact hashes, Merkle root, and file checksums.
5. `variance_metrics.csv` — Execution duration, peak-memory delta, and bounded variance score.

### Launching the Dashboard
```powershell
python .\viper_dashboard.py
```
Access locally at `http://127.0.0.1:8765/`. It uses inline CSS without remote assets and reads SQLite via a read-only connection.

---

## 6. Multi-Domain Policy Simulations

Simulate specialized regulatory and security constraints across distinct domains:
* **Solana / EVM:** Account mutations, storage depth, and state verification.
* **FHIR:** Consent verification and emergency overrides (enforcing mandatory $\ge 0.8$ variance review).
* **CMMC / PCI / SCADA:** Clearance tiers, merchant separation, and substation register checks.
* **AI Governance:** Tool scope authorization and boundary enforcement.

Run any domain through the evidence pipeline:
```powershell
python -m v8_sandbox.domain_pipeline solana
```

---

## 7. Testing & Verification Suite

Validate system integrity, network adapters, agent loops, and dashboard telemetry:

```powershell
# Run targeted unit tests
python -m pytest .\tests\test_network_adapter.py .\tests\test_viper_launcher.py .\tests\test_viper_agent.py -v

# Run full test suite
python -m unittest discover -s tests -v
python -m pytest -q