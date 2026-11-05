# 🧭 Session Router & Intent Management

ViperCrest enforces deterministic session isolation, replay protection, and cryptographic state tracking across all operations.

---

## 🔒 Session Isolation Mechanics

1. **Session Identifiers:**
   Every evaluation run generates a deterministic timestamped session:
   `session_YYYYMMDDTHHMMSSZ_matrix-<case_id>-<uuid>`
2. **Provenance Chaining:**
   Each sector evaluation builds an envelope with parent and current state hashes:
   ```json
   "state_provenance": {
     "parent_state_hash": "<parent_sha256>",
     "current_state_hash": "<current_sha256>"
   }
   ```
3. **Replay Defense:**
   Duplicate or replayed payload hashes with identical timestamps are rejected to prevent state manipulation.
4. **Self-Scrubbing Staging:**
   Temporary payloads staged in `runtime/staging/` are unlinked upon completion, while the final audit receipt is sealed into `runtime/sessions/` and `runtime/viper_state.db`.

---
*Links: [[Home]] | [[System Architecture]] | [[Matrix Evaluation Runbook]]*
