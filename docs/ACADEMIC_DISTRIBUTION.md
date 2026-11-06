# VIPERCREST ACADEMIC DISTRIBUTION LEDGER SPECIFICATION

## Overview

The ViperCrest Academic Distribution Ledger (`ledger/ledger.jsonl`) is a deterministic, append-only, tamper-evident hash-chained registry of authorized academic research copies.

Each block establishes an unbroken chain of cryptographic provenance directly back to Genesis Block 0 (`VC-ACADEMIC-GENESIS`).

---

## Provenance Linkage Architecture

```
+-----------------------------------------------------------------------------------+
| BLOCK 0: VC-ACADEMIC-GENESIS                                                      |
| Previous Hash: 0000000000000000000000000000000000000000000000000000000000000000   |
| Block Hash:    bb5035f2e39b3c93a2465b54ce3f769312f8dd59533df96c6c2a065eff05c652   |
| Status:        GENESIS_ANCHOR                                                     |
+-----------------------------------------------------------------------------------+
                                          |
                                    (SHA-256 Link)
                                          v
+-----------------------------------------------------------------------------------+
| BLOCK 1: VC-ACADEMIC-000001 (Carnegie Mellon University)                          |
| Previous Hash: bb5035f2e39b3c93a2465b54ce3f769312f8dd59533df96c6c2a065eff05c652   |
| Block Hash:    31cb81779b98f23a6653e1615e747e4cfe554332d938c11fa5b28fc534f44c41   |
| Recipient:     Carnegie Mellon University                                         |
| Department:    Robotics Institute (RI) & Software Engineering Institute (SEI)     |
| License Class: ACADEMIC_RESEARCH ($0.00 USD)                                      |
| Commercial:    FALSE | Equity: FALSE | Issuance Authority: FALSE                  |
| Artifact Hash: bbbcb05d50ac787cfcc52ffd06da6270d3ea4dc10e0abbc88d30de86c4dc8a2a   |
+-----------------------------------------------------------------------------------+
```

---

## Canonical Block Format

Every ledger block conforms strictly to [`schemas/ledger_block.schema.json`](../schemas/ledger_block.schema.json).

```json
{
  "schema_version": "1.0",
  "block_index": 1,
  "copy_id": "VC-ACADEMIC-000001",
  "product": "ViperCrest",
  "product_version": "ViperCrest 2.0",
  "release_commit": "fe96fd4ac483b1f54779a6b08ebea0f210213521",
  "recipient_class": "UNIVERSITY",
  "recipient_name": "Carnegie Mellon University",
  "recipient_department": "Robotics Institute (RI) & Software Engineering Institute (SEI)",
  "license_class": "ACADEMIC_RESEARCH",
  "commercial_rights": false,
  "equity_rights": false,
  "profit_rights": false,
  "transferable": false,
  "redistribution_rights": false,
  "issuance_authority": false,
  "donation_price_usd": 0,
  "artifact_sha256": "bbbcb05d50ac787cfcc52ffd06da6270d3ea4dc10e0abbc88d30de86c4dc8a2a",
  "manifest_sha256": "0a63fecd4d40a4793cc0732ec94abd885bd5b664178edaf4066c2f0ec1c8a635",
  "license_sha256": "d8ffe3a1507c9577a31d6561f40bb9e247eec376b28b4240ff1137a02dbc9567",
  "sbom_sha256": "fb3f1666bc8f6dd12597e63b18e66f049f3b53527c4dc58e847ecc471e8e156b",
  "public_key_fingerprint": "bce4e2a249e2530a60557ca9aa19f5151941ef67914c60f110c8bb46844f711f",
  "previous_block_hash": "bb5035f2e39b3c93a2465b54ce3f769312f8dd59533df96c6c2a065eff05c652",
  "created_utc": "2026-11-06T06:25:35Z",
  "issuer_status": "PENDING_OFFLINE_SIGNATURE",
  "issuer_signature": null,
  "public_anchor_status": "NOT_ANCHORED",
  "public_anchor_reference": null,
  "recipient_acceptance_status": "PENDING",
  "notes": "Academic research donation. No equity, investment, commercial, or issuance rights."
}
```

---

## Non-Negotiable Legal & Regulatory Invariants

1. **Academic Provenance Only:** The ledger block represents the issuance and provenance of a non-commercial academic copy.
2. **Explicit Prohibition of Securities & Tokens:** The provenance record does NOT represent:
   * Equity or company shares
   * Profit participation or revenue rights
   * An investment contract or financial security
   * A cryptocurrency or transferable token
   * Ownership of the ViperCrest intellectual property
3. **No Dilution of Commercial Channel:** Commercial deployment remains strictly separated under the fixed $1,000 commercial license via Whop (`https://vipercrest.whop.site/`).
