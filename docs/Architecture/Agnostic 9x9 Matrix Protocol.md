# 🧮 Agnostic 9x9 Matrix Protocol

The **9x9 Agnostic Matrix Protocol** is ViperCrest's verification harness for multi-layered observational fixtures. It structures data validations across a 9x9 grid of invariant checks (F1 through F9 tiers).

---

## 📐 Matrix Verification Grid (F1 to F9)

| Tier | Name | Target Domain | Core Invariant Verified |
| :--- | :--- | :--- | :--- |
| **F1** | Structural Integrity | JSON / Syntax | Schema compliance, type constraints, UTF-8 validity |
| **F2** | Identity & Hashing | Cryptographic Hash | SHA-256 digest match, non-empty identifiers |
| **F3** | Temporal Order | Timestamps | Monotonic progression, non-future timestamps |
| **F4** | Patient Policy & Scope | Clinical / Data Policy | Boundary isolation, sensitivity classification |
| **F5** | Anomaly Variance | Statistical Variance | Deviation bounds within configurable thresholds |
| **F6** | Dependency Resolution | Relational Graph | Reference existence, DAG cycle detection |
| **F7** | State Transition | State Machine | Allowed transitions, terminal state enforcement |
| **F8** | Signature Verification | Ed25519 / PEM | Cryptographic signature over observation manifest |
| **F9** | Provenance Seal | Audit Finality | Immutable audit record insertion in SQLite state |

---

## 🔍 Evaluation Lifecycle

```
[ Input Fixture (.json) ]
           │
           ▼
[ Schema Normalization ] ──► (F1 Check)
           │
           ▼
[ Identity & Hash Binding ] ──► (F2 Check)
           │
           ▼
[ Temporal & Policy Filter ] ──► (F3, F4 Checks)
           │
           ▼
[ Variance & Scoring ] ──► (F5 Check)
           │
           ▼
[ State & Signature Seal ] ──► (F6, F7, F8, F9 Checks)
           │
           ▼
[ Signed Matrix Output in SQLite & Session Manifest ]
```

---

## 💻 Invocation

Run matrix evaluation directly with:
```cmd
vc matrix --target fixtures\example.json
```
or via shorthand:
```cmd
vcm --target fixtures\example.json
```

---
## 🔗 Related Notes
- [[System Architecture]]
- [[Matrix Evaluation Runbook]]
- [[Universal 9x9 Syntax Bridge (vcb)]]
- [[Fixtures and Evaluation Targets]]
