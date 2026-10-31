# 🌐 Controlled Online Intake Runbook

This runbook guides operators through configuring and executing secure remote HTTPS intake sessions.

---

## 🔒 Step 1: Network Policy Authorization

1. Open `network_config.json`.
2. Set `"NETWORK_ENABLED": true`.
3. Add the exact destination host to `"ALLOWED_HOSTS"`:
   ```json
   {
     "NETWORK_ENABLED": true,
     "ALLOWED_HOSTS": [
       "api.trusted-partner.internal"
     ]
   }
   ```

---

## 🚀 Step 2: Ingestion Execution

Execute the intake command using `vco`:
```cmd
vco --url https://api.trusted-partner.internal/observations/case_902.json --case-id CASE-902
```

---

## 🛡️ Step 3: Post-Intake Lockdown

Immediately upon completing intake, restore the offline default in `network_config.json`:
```json
{
  "NETWORK_ENABLED": false,
  "ALLOWED_HOSTS": []
}
```

---
## 🔗 Related Notes
- [[HTTPS Intake & Security Model]]
- [[Configuration Specification (network_config.json)]]
- [[Shorthand Commands Quick Reference]]
