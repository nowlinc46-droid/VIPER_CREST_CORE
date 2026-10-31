# 📊 Offline Analytics & Database (`vcs`)

The **Offline Analytics** command (`vcs` / `vc-status` / `vipercrest offline --analytics`) performs automated inspection of the local SQLite database (`runtime/viper_state.db`).

---

## 📈 Metric Output

Running `vcs` summarizes system health and operational metrics:
- **Total Executions**: Overall count of sessions recorded in the state ledger.
- **Average Variance Score**: Aggregate statistical deviation across processed observation tiers.
- **Human Review Flag Count**: Number of sessions flagged for manual evaluation due to threshold exceedances or policy exceptions.
- **Latest Timestamp & Hashing Integrity**: Validation of the most recent audit entry.

---

## 💻 Invocation

```cmd
vcs
```
or via full command:
```cmd
vc offline --analytics
```

---
## 🔗 Related Notes
- [[SQLite Database Schema & WAL]]
- [[Shorthand Commands Quick Reference]]
