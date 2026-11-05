# 🛡️ HTTPS Intake & Security Model

ViperCrest maintains a strict, fail-closed security boundary separating the host machine, the network, and the internal invariant engine.

---

## 🔐 Security Principles

1. **Air-Gap Default:**
   All evaluation, reader, and matrix functions operate 100% offline. Network interfaces are never touched unless explicitly invoked via controlled intake.
2. **Loopback Circuit Guarding:**
   Controlled online intake enforces strict allowlisting, TLS certificate validation, maximum payload size limits (e.g. 10MB ceiling), and Content-Type filtering (`application/json` only). Any request violating boundaries returns immediate HTTP 400/403/413/415 rejections.
3. **Hardware Non-Destructive Ingestion:**
   Phone and USB hardware intake (`vc-device-audit`) executes read-only diagnostic telemetry queries via ADB. It never modifies firmware, installs apps, or alters device partitions.
4. **Cryptographic Proof Receipts:**
   Every terminal verdict emits an Ed25519 or SHA-256 consensus root hash that binds the evaluated payload to the immutable ledger.

---
*Links: [[Home]] | [[System Architecture]] | [[Shorthand Commands Quick Reference]]*
