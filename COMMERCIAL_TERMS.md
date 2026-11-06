# ViperCrest 2.0 — Commercial Terms & Licensing Doctrine

## 1. The Dual-Licensing Invariant

ViperCrest is governed by a strict dual-licensing architecture designed to balance sovereign individual defense with commercial institutional monetization:

* **Non-Commercial / Individual Citizens:** **Free ($0)** under the terms of the `PolyForm-Noncommercial-1.0.0` license. Any individual, student, or researcher is granted full, unrestricted access to inspect, audit, verify, and run the engine for personal and defensive use at zero cost.
* **Commercial / Enterprise Entities:** Any commercial deployment, automated industrial operation, for-profit service, or enterprise integration requires an affirmative commercial license.

---

## 2. Standard Commercial Rates & Grants

| Tier | Fee | Scope of Grant |
| :--- | :--- | :--- |
| **Commercial Node License** | **$1,000 (One-Time Flat)** | Perpetual, non-exclusive, fully paid-up license to run and execute one production instance/node with zero recurring royalties. |
| **Enterprise Site License** | **Custom / Negotiated** | Unlimited internal deployments across all wholly-owned subsidiaries and departments of a single corporate entity. |
| **Exclusive Asset Buyout** | **$9,000,000 (Single Transaction)** | 100% transfer of all intellectual property, copyright, codebase, and physical handover of the offline Master Sovereign Root Key. |

---

## 3. Strict Air-Gapped Licensing Architecture (The Root Invariant)

To preserve the cryptographic integrity verified under Invariant V11:

* **Zero Online Exposure:** The Master Sovereign Private Key (`master_license_private_ROTATED.pem`) **never touches a network, server, or web application**.
* **Offline Minting:** All commercial licenses are generated and cryptographically signed strictly offline on an air-gapped machine using `C:\ViperCrest_Licensor\mint_license.py`.
* **Genesis Binding:** Each minted license produces a deterministic `license_spec.json` and Ed25519 `license.sig`. The runtime engine verifies the signature against [`runtime/public_seal.pem`](runtime/public_seal.pem) entirely locally without calling home.

---

## 4. "As-Is" Self-Contained Deliverable (Zero Support Obligation)

To eliminate the liability and maintenance traps of low-cost commercial licensing:

1. **Self-Contained Artifact:** The commercial license applies strictly to the frozen, cryptographically verified software snapshot as audited at release (commit `cbb84ee`).
2. **No Perpetual Support:** The one-time $1,000 commercial fee grants perpetual execution rights to the verified artifact. It **does not include ongoing consulting, custom engineering, SLA guarantees, or 24/7 customer support**.
3. **Warranty Disclaimer:** The software is provided "AS-IS", without warranties of merchantability or fitness for a particular purpose beyond the mathematical invariants proven by [`verify_asset.py`](verify_asset.py).

---

## 5. Commercial Distribution Roadmap

> *"ViperCrest is dual-licensed — free for citizens, $1,000 commercial. Reaching $9M means 9,000 paying businesses, roughly 3% of a ~300,000-entity niche — a share serious vendors take years to win. The license machinery to enforce it is built and verified; the work ahead is distribution and trust, not arithmetic."*

Commercial adoption proceeds through verifiable technical diligence:
1. Prospective enterprise buyers clone the public repository and run `python verify_asset.py` on their own air-gapped infrastructure.
2. The 8/8 diligence pillars, 100-turn adversarial siege, and dual-compiler `rustc 1.99.1` consensus (Exit Code 0) provide objective proof of soundness.
3. Upon commercial execution, licenses are signed offline and delivered for local runtime verification.
