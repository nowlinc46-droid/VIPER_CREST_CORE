# 🛡️ Immunefi Top 10 Security Audit (`vca` / `vc-audit`)

The **Immunefi Top 10 Invariant Security Audit** (`audit_immunefi.py`) performs automated verification across all 10 universal Web3 / sovereign matrix security invariants (`V01` through `V10`).

---

## 🔒 The 10 Invariant Vectors

| Code | Invariant Name | Scope Verified |
| :--- | :--- | :--- |
| **V01** | Input Validation & Schema Integrity | Rejects non-dict root payloads, malformed schemas, and path traversal |
| **V02** | Calculation Precision & Clamping | Validates deterministic `[0.0, 1.0]` variance score clamping |
| **V03** | Reentrancy & Concurrency Locking | Enforces SQLite Write-Ahead Logging (`WAL`) and session UUID isolation |
| **V04** | Access Control & Private Key Boundaries | Validates Ed25519 signing key permissions and boundary isolation |
| **V05** | Oracle Containment & Air-Gap | Enforces `NETWORK_ENABLED: false` and empty allowed hosts default |
| **V06** | Resource Exhaustion Boundaries | Verifies 1 MB maximum response byte buffer and traversal limits |
| **V07** | Fail-Closed Integrity & Unchecked Returns | Confirms cross-tenant violations raise `ERROR_PATIENT_POLICY` |
| **V08** | Replay Immunity & Chained Receipts | Validates Ed25519 payload signatures and unique session timestamps |
| **V09** | State Desynchronization Defense | Verifies session bundle alignment against SQLite state records |
| **V10** | Schema Immutability & Upgrade Integrity | Validates presence and migration integrity of canonical tables |

---

## 💻 Invocation

```cmd
vca
```
or
```cmd
vc-audit
```
