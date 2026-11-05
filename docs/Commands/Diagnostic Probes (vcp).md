# 🔬 Diagnostic Probes (`vcp`)

The **Diagnostic Probes** suite (`probes/probe_matrix.py` and `probes/probe_matrix_v2.py`) performs deep inspection, edge-case probing, and matrix integrity verification.

---

## 🔍 Probe Phases

When invoked via `vcp` or `vc-probe.cmd`:
1. **Phase 1: `probe_matrix.py`**:
   - Tests matrix boundary conditions.
   - Evaluates baseline variance calculation against standard fixtures.
2. **Phase 2: `probe_matrix_v2.py`**:
   - Executes multi-case stress passes.
   - Verifies replay defenses and cryptographic signature consistency.

---

## 💻 Invocation

```cmd
vcp
```

---
## 🔗 Related Notes
- [[Shorthand Commands Quick Reference]]
- [[Testing & Verification Guide]]
