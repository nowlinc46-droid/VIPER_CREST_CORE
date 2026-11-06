# VIPERCREST SECURITY BOUNDARIES & KEY ISOLATION NOTICE

## Fundamental Architectural Invariant: Cold-Storage Root Separation

The ViperCrest architecture maintains a strict, unbreachable boundary between the **Public Academic Distribution Layer** and the **Offline Commercial/Licensor Root**.

```
                   ========================================
                   VIPERCREST SOVEREIGN ARCHITECTURAL SPLIT
                   ========================================

    PUBLIC ACADEMIC LAYER (Online / GitHub)        OFFLINE COMMERCIAL ROOT (Cold Storage)
    ---------------------------------------        --------------------------------------
    Repo: VIPERCREST_ACADEMIC_DISTRIBUTION         Location: C:\ViperCrest_Licensor (Air-Gapped)
    * Source code & academic deliverables          * Master Root PRIVATE key (NEVER COMMITTED)
    * Public seal (public_seal.pem)                * Commercial offline minting (mint_license.py)
    * Cryptographic ledger (ledger.jsonl)          * Sovereign private signing authority
    * JSON schemas & verification scripts          * Commercial customer entitlement records
    * Zero equity / zero tokens / zero secrets     * Separate fixed $1,000 commercial pricing
```

---

## 1. Zero Private Key Commits
* **The Master Root Private Key (`master_license_private_ROTATED.pem`) is permanently held offline by the Licensor.**
* At NO time has any private key, signing key, wallet seed, or credential been committed, uploaded, embedded, or pushed to this repository.
* This repository contains **EXCLUSIVELY PUBLIC VERIFICATION MATERIAL** (`runtime/public_seal.pem`).

## 2. Air-Gap Enforcement (Zero Egress)
* The ViperCrest runtime is engineered for air-gapped workstations.
* `network_config.json` enforces `NETWORK_ENABLED: false` and `ALLOWED_HOSTS: []`.
* The engine makes zero telemetry calls, external pings, or license activation requests to any network server.

## 3. Issuance Authority Boundary
* Academic distribution grants research and pedagogical inspection rights only.
* Receipt or possession of an academic copy conveys **ZERO** authority to sign, mint, authorize, or issue official successor ViperCrest licenses.
* Any signature minted without the offline Master Root private key is cryptographically rejected by the public seal verifier.

## 4. Public Verification Fingerprint
The SHA-256 fingerprint of the authoritative public verification seal is:
```
bce4e2a249e2530a60557ca9aa19f5151941ef67914c60f110c8bb46844f711f
```
