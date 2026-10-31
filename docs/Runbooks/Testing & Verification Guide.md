# 🧪 Testing & Verification Guide

Comprehensive guide for verifying ViperCrest code, matrix invariants, launcher aliases, and diagnostic probes.

---

## ⚡ Fast Test Suite

Run the full Python test suite with the shorthand command:
```cmd
vct
```
or via direct unittest invocation:
```cmd
vc-test
```

This runs discovery across all test modules in `tests/`:
- `test_viper_launcher.py`: CLI routing, argument forwarding, and shorthand aliases.
- `test_matrix.py`: F1–F9 verification tiers, anomaly scoring, and hash seals.
- `test_http.py` / `test_network_adapter.py`: HTTPS intake, allowlisting, and rejection codes.
- `test_session_router.py`: Session isolation, directory hashing, and replay defenses.
- `test_layout.py`: Security bounds, symlink rejection, and active runtime isolation.

---

## 🔬 Diagnostic Probes

Execute the two-phase diagnostic probe suite:
```cmd
vcp
```

---

## 📊 Offline Analytics Audit

Inspect database state integrity and human review flags:
```cmd
vcs
```

---
## 🔗 Related Notes
- [[Diagnostic Probes (vcp)]]
- [[Offline Analytics & Database (vcs)]]
- [[Shorthand Commands Quick Reference]]
