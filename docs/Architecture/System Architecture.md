# 🏗️ ViperCrest System Architecture

ViperCrest is an offline-first, cryptographic intake and matrix evaluation engine designed for deterministic, verifiable processing of structured F1–F9 fixtures and controlled HTTPS observations.

---

## 🏛️ High-Level Component Topology

```
                  +--------------------------------+
                  |  CLI Entrypoints (vc / vcm...) |
                  +---------------+----------------+
                                  |
                                  v
                  +---------------+----------------+
                  |    Session Router & Intent     |
                  +---------------+----------------+
                                  |
                 +----------------+----------------+
                 |                                 |
                 v                                 v
+--------------------------------+ +--------------------------------+
|      HTTPS Intake Engine       | |       F1-F9 Matrix Engine      |
|        (viper_http.py)         | |       (viper_matrix.py)        |
+----------------+---------------+ +---------------+----------------+
                 |                                 |
                 +----------------+----------------+
                                  |
                                  v
                  +---------------+----------------+
                  |   Cryptographic State & WAL    |
                  |     (runtime/viper_state.db)   |
                  +--------------------------------+
```

---

## 🔑 Core Subsystems

### 1. Unified Launcher (`viper.py` & `.cmd` wrappers)
- Provides standard command routing (`online`, `matrix`, `offline`) and shorthands (`on`, `m`, `off`).
- Fast entry scripts (`vc.cmd`, `vcm.cmd`, `vco.cmd`, `vcoff.cmd`, `vcb.cmd`, `vcf.cmd`, `vct.cmd`, `vcp.cmd`, `vcs.cmd`, `vcr.cmd`, `vch.cmd`).
- Operates under strict Python flags (`-B` to prevent `.pyc` clutter).

### 2. Session Router (`session_router.py`)
- Generates isolated, cryptographically signed session directories in `runtime/sessions/`.
- Computes SHA-256 hashes of input fixtures and manifests.
- Enforces replay defense and deterministic execution.

### 3. F1–F9 Matrix Engine (`viper_matrix.py`)
- Evaluates 9x9 multi-dimensional verification grids (F1 through F9).
- Validates patient observation structures, anomaly scores, and invariant bounds.
- Records structured evaluation matrices with signed hash digests.

### 4. Controlled HTTPS Intake (`viper_http.py` / `network_adapter.py`)
- Network-isolated by default via `network_config.json`.
- Strict allowlisting of destination domains and ports.
- Enforces payload size limits, certificate validation, and deterministic header inspection.

### 5. Universal Agnostic Syntax Bridge (`bridge_9x9_syntax.py`)
- Translates external schema definitions into unified 9x9 syntax structures.
- Provides invariant translation between Foundry, CrateEngine, and ViperCrest native schemas.

---

## 🔒 Security & Isolation Model

1. **Deterministic Isolation**: Active runtime root is strictly pinned to prevent directory traversal escapes (`..\outside.json` is rejected).
2. **Offline-First Default**: `network_config.json` ships with `NETWORK_ENABLED: false`. No socket connections are made without explicit user configuration.
3. **Cryptographic Integrity**: All evaluation runs sign the state manifest using `runtime/signing_key.pem`.
4. **WAL Journaling**: State SQLite database uses Write-Ahead Logging (`PRAGMA journal_mode=wal`) for ACID compliance and concurrency.

---

## 🔗 Related Notes
- [[Agnostic 9x9 Matrix Protocol]]
- [[Session Router & Intent Management]]
- [[HTTPS Intake & Security Model]]
- [[Shorthand Commands Quick Reference]]
