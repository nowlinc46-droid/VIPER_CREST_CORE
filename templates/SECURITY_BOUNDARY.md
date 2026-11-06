# VIPERCREST SECURITY BOUNDARY & KEY ISOLATION NOTICE

**Package Copy ID:** {{COPY_ID}}  
**Verification Seal:** `runtime/public_seal.pem`  
**Security Model:** Asymmetric Single-Seal Air-Gapped Verification  

---

### Non-Negotiable Boundary Guarantees

1. **NO MASTER PRIVATE KEY ENCLOSED:**
   * This academic research package contains **EXCLUSIVELY PUBLIC VERIFICATION MATERIAL** (`public_seal.pem`).
   * The Master Root Private Key (`master_license_private_ROTATED.pem`) is permanently held offline by the Licensor in cold storage.
   * At no time has the Master Root private key been committed, uploaded, packaged, or embedded inside this distribution.

2. **AIR-GAP ENFORCEMENT (ZERO EXTERNAL EGRESS):**
   * The ViperCrest runtime enforces fail-closed execution.
   * `network_config.json` is configured with `NETWORK_ENABLED: false` and `ALLOWED_HOSTS: []`.
   * The engine does not make telemetry calls, analytics uploads, or license activation requests to any external server.

3. **ISSUANCE AUTHORITY RESTRICTION:**
   * Possession of this package does NOT convey authority to sign, mint, authorize, or issue official successor ViperCrest licenses.
   * Any signature minted without the offline Master Root private key is cryptographically invalid and will immediately fail closed with **Exit Code 1**.

4. **INTEGRITY VERIFICATION:**
   * The SHA-256 fingerprint of the authorized public verification key is:
     `BCE4E2A249E2530A60557CA9AA19F5151941EF67914C60F110C8BB46844F711F`
