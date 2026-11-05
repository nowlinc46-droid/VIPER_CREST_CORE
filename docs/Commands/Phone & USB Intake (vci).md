# 📱 Phone & USB Device Data Intake Engine (`vci` / `vc-intake`)

The **Phone & USB Device Data Intake Engine** (`phone_intake.py` and `phone_intake.ps1`) manages Stage F1 ground-truth extraction and dropzone staging for connected Android / USB devices or synthetic forensic profiles.

---

## ⚙️ Capabilities & Architecture

1. **Hardware / ADB Discovery**: Automatically queries connected Android devices over USB using `adb devices -l`.
2. **Synthetic Simulation Mode (`--simulate`)**: Allows comprehensive offline testing across forensic profiles:
   - `security_anomaly`: Detects root binaries (`/system/bin/su`, Frida servers), permissive SELinux, and suspicious permissions.
   - `app_db_audit`: Assesses SQLite app databases for unencrypted PII rows, schema anomalies, and integrity breaks.
   - `telemetry`: Pulls device hardware status, battery health, and network state.
3. **Dropzone Staging**: Normalizes extracted records into immutable JSON fixtures in `runtime/dropzone/`.
4. **Stage F1 Ground-Truth Ledger Ingestion**: Validates schemas and calculates SHA-256 byte hashes, registering entries directly into the SQLite `dropzone_intake` table.
5. **Automated F1–F9 Matrix Execution**: Automatically triggers `vc matrix` against ingested fixtures, producing cryptographic audit receipts and signed 5-file session bundles.

---

## 💻 Invocation Examples

### 1. Simulated Security Anomaly Extraction
```cmd
vci --simulate --scenario security_anomaly
```
or via PowerShell:
```powershell
.\phone_intake.ps1 -Simulate -Scenario security_anomaly
```

### 2. Live ADB Device Extraction (when phone connected via USB)
```cmd
vci
```

### 3. Application Database Audit Simulation
```cmd
vci --simulate --scenario app_db_audit
```

---

## 🔗 Related Notes
- [[System Architecture]]
- [[Agnostic 9x9 Matrix Protocol]]
- [[Shorthand Commands Quick Reference]]
- [[Foundry Bridge (vcf)]]
