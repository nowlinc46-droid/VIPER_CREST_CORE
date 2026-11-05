# 🗄️ SQLite Database Schema & WAL

ViperCrest maintains state and immutable audit records in `runtime/viper_state.db`.

---

## ⚡ Write-Ahead Logging (WAL) Mode

The database is initialized with:
- `PRAGMA journal_mode = wal;` — Provides concurrent read operations while writes are safely queued.
- `PRAGMA synchronous = NORMAL;` — Maximizes throughput while guaranteeing corruption resistance.
- `PRAGMA integrity_check;` — Run during initialization and diagnostics.

---

## 🏛️ Core Tables

### 1. `runs` Table
Tracks execution attempts, manifests, and hashes:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (TEXT UNIQUE NOT NULL)
- `case_id` (TEXT NOT NULL)
- `manifest_hash` (TEXT NOT NULL)
- `status` (TEXT NOT NULL)
- `created_at` (TEXT NOT NULL)

### 2. `matrix_evaluations` Table
Stores tier evaluations and variance calculations:
- `run_id` (INTEGER REFERENCES runs(id))
- `tier` (TEXT NOT NULL, e.g. 'F1', 'F2', ..., 'F9')
- `status` (TEXT NOT NULL)
- `variance_score` (REAL)
- `requires_human_review` (BOOLEAN)
- `details` (TEXT JSON)

---
## 🔗 Related Notes
- [[Session Router & Intent Management]]
- [[Offline Analytics & Database (vcs)]]
