# 🔐 Asymmetric Single-Seal Sovereign Licensing

ViperCrest implements a cryptographic licensing architecture designed specifically for sovereign, air-gapped enterprise environments.

---

## 🏛️ The Core Authority Separation

Standard software licensing relies on flimsy plaintext files or cloud phone-home DRM. ViperCrest rejects both:
* Cloud phone-home checks violate the **Air-Gap Invariant (V05)**.
* Storing the signing key inside the distributed software allows anyone to mint valid licenses for themselves.

ViperCrest resolves this by strictly enforcing:

$$\mathbf{\text{Authority}_{\text{sign}} \neq \text{Authority}_{\text{execute}}}$$

```text
CLIFTON / LICENSOR (OFFLINE)
─────────────────────────────────────
MASTER PRIVATE KEY
   │
   │ signs license_spec.json
   ▼
license.sig

DISTRIBUTED VIPERCREST RUNTIME
─────────────────────────────────────
runtime/license_spec.json
runtime/license.sig
runtime/public_seal.pem
   │
   ▼
license_gate.py (VERIFY ONLY)
   │
   ├── TRUE  ──► Bind SHA-256(Seal) into T1_ROOT Genesis Provenance
   │
   └── FALSE ──► FAIL-CLOSED (HALT / exit code 1)
```

---

## 🔒 The Three Cryptographic Artifacts

1. **The License Specification ([`runtime/license_spec.json`](file:///C:/ViperCrest/runtime/license_spec.json)):**
   ```json
   {
     "licensee": "nowli",
     "grant_type": "SINGLE_SEAL_SOVEREIGN_NODE",
     "architecture": "ViperCrest Core 2.0",
     "manifold": "1x(3x3)x(9x9)x81x(9x9)x(3x3)x1",
     "air_gap_boundary": true,
     "issued_utc": "2026-11-05T00:00:00Z",
     "issuer_authority": "CLIFTON_NOWLIN_MASTER_ROOT"
   }
   ```
2. **The Cryptographic Single Seal ([`runtime/license.sig`](file:///C:/ViperCrest/runtime/license.sig)):**
   * The binary Ed25519 digital signature of `license_spec.json` minted by the Licensor's offline master private key.
3. **The Public Verification Key ([`runtime/public_seal.pem`](file:///C:/ViperCrest/runtime/public_seal.pem)):**
   * The only key present in the distributed engine. Used strictly for `Verify()`.

---

## ⚡ The Fail-Closed Verification Gate ([`license_gate.py`](file:///C:/ViperCrest/license_gate.py))

Before any fixture, telemetry stream, or user command enters Stage $F_1$, `license_gate.py` evaluates:

$$\text{Verify}(PK, \text{License}, \text{Signature}) \in \{\mathbf{TRUE}, \mathbf{FALSE}\}$$

* If **$\mathbf{TRUE}$**: Returns the SHA-256 digest of the valid signature:
  `195fcfdc414d02c33d5f7a289d78091549c00e8863f413eba9b76c81fd3896f4`
  This digest is cryptographically bound into Genesis ($T_1\text{-ROOT}$), meaning every session receipt (`receipts_audit.sig`) inherits verified license provenance.
* If **$\mathbf{FALSE}$**: The engine halts immediately fail-closed (`sys.exit(1)`). Zero partial runs, zero output.

---

## 🛡️ Tamper-Evident Guarantees

* **License Spec Modified:** Mutating a single character (e.g. changing licensee from `nowli` to `other`) causes Ed25519 verification to fail immediately.
* **Signature Modified:** Flipping 1 bit of `license.sig` causes instant halt.
* **Public Key Replaced:** Substituting `public_seal.pem` with a rogue public key fails because the rogue key does not match the master signature.
* **Master Authority Protected:** The master private key is stored offline at `C:\ViperCrest_Licensor\master_license_private_ROTATED.pem` and has zero presence in Git or distributed runtimes.
