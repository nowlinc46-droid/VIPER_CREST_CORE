# ⚙️ Configuration Specification (`network_config.json`)

The `network_config.json` file controls the networking surface of ViperCrest.

---

## 📄 Schema Definition

```json
{
  "NETWORK_ENABLED": false,
  "ALLOWED_HOSTS": [
    "example.com"
  ],
  "PORT": 8443,
  "TIMEOUT_SECONDS": 10
}
```

---

## 🗝️ Field Reference

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NETWORK_ENABLED` | `boolean` | `false` | Master circuit breaker. If `false`, all remote network requests fail immediately. |
| `ALLOWED_HOSTS` | `list[string]` | `[]` | Explicit domain whitelist. Requests to unlisted hosts are rejected. |
| `PORT` | `integer` | `8443` | Default port used when not specified in the intake URL. |
| `TIMEOUT_SECONDS` | `integer` | `10` | Hard socket connection and read timeout. |

---
## 🔗 Related Notes
- [[HTTPS Intake & Security Model]]
- [[Controlled Online Intake Runbook]]
