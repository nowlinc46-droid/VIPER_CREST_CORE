# 🛡️ HTTPS Intake & Security Model

The **HTTPS Intake Subsystem** (`viper_http.py` and `network_adapter.py`) manages controlled remote ingestion while strictly maintaining offline-first security bounds.

---

## 🔒 Security Principles

1. **Explicit Enablement Required**: `network_config.json` ships with `"NETWORK_ENABLED": false`. All outbound network attempts will abort immediately if this flag is disabled.
2. **Domain & Port Allowlisting**: Requests are restricted strictly to URLs matching `"ALLOWED_HOSTS"` in `network_config.json`.
3. **Payload Inspection & Limits**:
   - Inbound HTTP payloads are bounded by strict maximum body size limits.
   - Non-JSON content types and malformed streams are rejected with HTTP 400/415 before passing to the matrix.
4. **Certificate & TLS Verification**: Encrypted transport is enforced with strict certificate validation.
5. **Observation Normalization**: Ingested remote records are normalized into canonical fixture schema before entering evaluation.

---

## ⚙️ Configuration Example (`network_config.json`)

```json
{
  "NETWORK_ENABLED": false,
  "ALLOWED_HOSTS": [
    "authorized.intake.internal"
  ],
  "PORT": 8443,
  "TIMEOUT_SECONDS": 10
}
```

---

## 💻 Invocation

```cmd
vc online --url https://authorized.intake.internal/fixture.json --case-id CASE-2026-01
```
or via shorthand:
```cmd
vco --url https://authorized.intake.internal/fixture.json --case-id CASE-2026-01
```

---
## 🔗 Related Notes
- [[System Architecture]]
- [[Controlled Online Intake Runbook]]
- [[Configuration Specification (network_config.json)]]
