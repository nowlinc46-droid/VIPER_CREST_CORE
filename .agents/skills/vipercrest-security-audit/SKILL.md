---
name: vipercrest-security-audit
description: >-
  Audits, verifies, and enforces the Immunefi Top 10 security invariants across ViperCrest
  (C:\ViperCrest). Use this skill whenever inspecting, testing, modifying, or evaluating
  ViperCrest components (viper_matrix.py, session_router.py, viper_core.py, network_adapter.py,
  bridge_9x9_syntax.py, runtime/viper_state.db) to ensure fail-closed execution, air-gap containment,
  and cryptographic auditability.
---

# ViperCrest Immunefi Top 10 Security Audit Skill

This skill enforces continuous security and mathematical invariant validation for the **ViperCrest** sovereign execution engine (`C:\ViperCrest`).

## Quick CLI Audit Runbook

To perform a complete security and invariant audit of ViperCrest, execute these standard commands from any terminal or PowerShell session:

```powershell
# 1. Run Automated Invariant Audit (V01-V10 programmatic checks)
C:\ViperCrest\vca.cmd

# 2. Run Complete Unit & Integration Regression Suite (75/75 invariants)
C:\ViperCrest\vct.cmd

# 3. Run Historical Prototype Boundary Probes (31/31 defect-containment checks)
C:\ViperCrest\vcp.cmd

# 4. Verify SQLite Write-Ahead Logging & Historical State Ledger
C:\ViperCrest\vcs.cmd
```

---

## The 10 Invariant Security Vectors

### 1. `V01` — Improper Input Validation & Schema Integrity
* **Target Files:** `viper_core.py`, `session_router.py`, `viper_matrix.py`
* **Rule:** All fixture intake must reject path traversals (`..\`), enforce `.json` filename extensions, validate that the root element is a JSON object (`dict`), and reject non-conforming schema envelopes prior to staging.
* **Verification:** `vct` executes `test_fixture_path_rejects_traversal` and `test_invalid_shapes_and_partial_policy_fail_before_persistence`.

### 2. `V02` — Incorrect Calculation & Precision Loss
* **Target Files:** `viper_core.py` (`bounded_variance_score`)
* **Rule:** Variance scoring must never raise unhandled exceptions on zero-variance distributions or empty sets. All scores must be mathematically clamped between `[0.0, 1.0]` using explicit finite float assertions.
* **Verification:** `vca` checks both zero-variance and max-difference clamps.

### 3. `V03` — Reentrancy & Concurrency State Locking
* **Target Files:** `runtime/viper_state.db`, `session_router.py`
* **Rule:** SQLite must enforce `PRAGMA journal_mode=WAL;`. Concurrently dispatched runs must generate unique run-scoped staging paths (`matrix-{timestamp}-{uuid}`) to eliminate race conditions and session collisions.
* **Verification:** `test_identical_timestamp_runs_remain_distinct` and `test_wal_is_enabled_on_fresh_state`.

### 4. `V04` — Missing Access Control & Key Boundary Isolation
* **Target Files:** `runtime/signing_key.pem`, `network_config.json`
* **Rule:** Local Ed25519 signing keys must be restricted via Windows NT ACLs to the sole machine operator (`nowli`). Ingested payloads must have zero write capability to system configuration files.
* **Verification:** `vca` inspects key existence and ownership boundary.

### 5. `V05` — Oracle & External Data Source Containment (Air-Gap)
* **Target Files:** `network_config.json`, `network_adapter.py`
* **Rule:** Default configuration must enforce `NETWORK_ENABLED: false` and `ALLOWED_HOSTS: []`. Network intake must reject HTTP redirects, non-GET methods, embedded credentials, and unverified TLS certificates.
* **Verification:** `test_disabled_is_default_and_never_connects` and `test_post_and_all_redirects_rejected_without_second_request`.

### 6. `V06` — Resource Exhaustion & Payload Bounding
* **Target Files:** `network_adapter.py`, `bridge_9x9_syntax.py`
* **Rule:** All external responses are hard-bounded at 1 MB (`MAX_RESPONSE_BYTES = 1048576`). File system traversals are capped at 100 files (`max_files=100`) with binary text-fallback heuristics.
* **Verification:** `test_oversized_declared_and_streamed_responses`.

### 7. `V07` — Unchecked Return Values & Fail-Closed Error Handling
* **Target Files:** `viper_matrix.py`, `vct.cmd`, `.ps1` wrappers
* **Rule:** Any sector evaluation failure, database write error, or policy violation must immediately abort the pipeline, return a non-zero exit code (`1` or `2`), purge staging artifacts, and publish zero partial bundles.
* **Verification:** `test_write_failure_cleans_staging_and_never_publishes_partial_bundle`.

### 8. `V08` — Transaction Ordering & Chained Replay Immunity
* **Target Files:** `viper_matrix.py`, `viper_http.py`
* **Rule:** Every sector receipt must cryptographically bind the previous sector's signature hash into its own payload digest. Identical payloads replayed at a later time receive unique run IDs and timestamps, preventing historical state forgery.
* **Verification:** `test_stage_chain_binds_payload_and_every_preceding_transition`.

### 9. `V09` — State Desynchronization & Invariant Ledger Integrity
* **Target Files:** `runtime/sessions/`, `runtime/viper_state.db`
* **Rule:** The 5-file audit session bundle (`session_meta.json`, `execution_stack.ndjson`, `state_delta.json`, `receipts_audit.sig`, `variance_metrics.csv`) must match the SQLite database record bit-for-bit.
* **Verification:** `test_session_and_database_tampering_are_detected`.

### 10. `V10` — Upgradeability & Schema Immutability
* **Target Files:** `runtime/viper_state.db`, `bridge_9x9_syntax.py`
* **Rule:** The canonical schema (`runs`, `artifacts`, `receipts`, `dropzone_intake`) must be preserved across upgrades. No unmapped fields may be discarded during translation.
* **Verification:** `test_legacy_fixture_schema_remains_supported`.
