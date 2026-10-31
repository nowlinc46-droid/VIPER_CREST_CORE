# 💻 CLI Launcher (`vc` & `vipercrest`)

`viper.py` serves as the dynamic dispatch hub for all ViperCrest operations.

---

## 🛠️ Usage & Subcommands

### 1. Matrix Subcommand (`matrix` / `m`)
Dispatches to `viper_matrix.py` to evaluate F1–F9 verification tiers on a target JSON fixture:
```cmd
vc matrix --target fixtures\example.json
vc m --target fixtures\patient_records_bola.json
```

### 2. Online Subcommand (`online` / `on`)
Dispatches to `viper_http.py` (or `network_adapter.py`) for HTTPS intake:
```cmd
vc online --url https://authorized.host/case.json --case-id CASE-001
vc on --url https://authorized.host/case.json --case-id CASE-001
```

### 3. Offline Subcommand (`offline` / `off`)
Dispatches to `viper_core.py` for database inspection and metrics analysis:
```cmd
vc offline --analytics
vc off --analytics
```

---

## 🔒 Security Properties
- Rejects non-existent commands with return code 2.
- Does not load underlying modules if arguments fail basic validation.
- Emits no bytecode caches (`-B` execution).

---
## 🔗 Related Notes
- [[Shorthand Commands Quick Reference]]
- [[System Architecture]]
