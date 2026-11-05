# 📖 Matrix Evaluation Runbook

This runbook outlines the standard procedure for executing deterministic F1–F9 matrix evaluations.

---

## 🎯 Pre-requisites
- ViperCrest virtual environment bootstrapped (`bootstrap.ps1`).
- Target fixture file placed in `fixtures/` or passed via relative path.

---

## 🚀 Execution Steps

1. **Verify Target Fixture**:
   Confirm the fixture JSON format matches the standard schema:
   ```cmd
   type fixtures\example.json
   ```

2. **Execute Matrix Evaluation**:
   Run the matrix runner using the `vcm` shorthand:
   ```cmd
   vcm --target fixtures\example.json
   ```

3. **Inspect Output**:
   The output returns the session ID, verification summary across F1–F9 tiers, computed variance score, and audit status.

4. **Verify Session Directory**:
   Check `runtime/sessions/` for the newly created session directory containing `manifest.json` and signed evaluation logs.

---
## 🔗 Related Notes
- [[Agnostic 9x9 Matrix Protocol]]
- [[Fixtures and Evaluation Targets]]
- [[Shorthand Commands Quick Reference]]
