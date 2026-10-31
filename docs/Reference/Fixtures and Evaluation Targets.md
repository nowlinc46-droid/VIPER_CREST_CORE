# 📦 Fixtures and Evaluation Targets

ViperCrest ships with reference fixtures and test targets located in `fixtures/` and `targets/`.

---

## 📂 Bundled Fixtures (`fixtures/`)

| File | Purpose | Key Observation Domains |
| :--- | :--- | :--- |
| `example.json` | Standard baseline fixture | Basic observations, variance verification |
| `patient_records_bola.json` | Clinical policy fixture | Evaluates policy violation triggers and boundaries |
| `sample_target.json` | Target profile | Canonical target parameters for F1-F9 passes |

---

## 🔒 Resolution Safety

All fixture names passed via CLI parameters are strictly resolved within the project root directory. Path traversal sequences (such as `..\`) are detected and rejected with `IntentError`.

---
## 🔗 Related Notes
- [[Agnostic 9x9 Matrix Protocol]]
- [[Matrix Evaluation Runbook]]
- [[System Architecture]]
