# VIPERCREST 2.0 - 9-REPOSITORY TRUST & DISCLOSURE TAXONOMY
## Operationalizing NIST SP 800-218 (SSDF) Through Compartmentalized Trust Boundaries

---

### Executive Overview & Alignment with NIST SP 800-218
The **NIST Secure Software Development Framework (SSDF, SP 800-218)** establishes standard practices to:
1. **Protect Software Components Against Tampering & Unauthorized Access (PO.3)**
2. **Produce Well-Secured Software through Risk Modeling & Boundary Verification (PW.1 - PW.4)**
3. **Respond to Vulnerabilities & Disclose Securely (RV.1 - RV.3)**

In ViperCrest, the **fixed F1–F9 Logical Engine remains a single, immutable mathematical engine**. The 9-repository separation does **not** create nine splintered engine forks; rather, it establishes **nine strictly defined trust, permission, and disclosure boundaries**.

---

### The 9-Repository Architecture Matrix

| # | Repository Identifier | Visibility | Trust / Disclosure Level | Core Purpose & Contents |
|---|------------------------|------------|---------------------------|-------------------------|
| **1** | `VIPERCREST_PUBLIC` | **Public** | Low Sensitivity / Broad Disclosure | High-level architectural overviews, formal terminology, sitemaps, system diagrams, and publicly verified invariants. |
| **2** | `VIPERCREST_ACADEMIC_DISTRIBUTION` | **Public** | Verified Academic Release ($v1.0, v1.1$) | Sealed university research copies, cryptographic distribution ledgers (`ledger.jsonl`), academic citations, and immutable replication archives. |
| **3** | `VIPERCREST_VERIFICATION` | **Public** | Independent Tooling | Standalone verification scripts, JSON schemas, cryptographic hash verifiers, public key seal verifiers, and third-party validation harnesses. |
| **4** | `VIPERCREST_BENCHMARKS` | **Public** | Empirical Results | Reproducible benchmark runners, 100-Turn AbstentionBench sieges, presentation invariance suites (`LOGIC != LANGUAGE`), and empirical reports. |
| **5** | `VIPERCREST_INTEROP_PROTOCOL` | **Controlled / Public** | Standardized Protocol Specification | Canonical wire protocol specification (`VCW2`), serialization schemas, cross-machine state semantics, socket frame specifications, and interoperability conformance suites. |
| **6** | `VIPERCREST_RESEARCH_LAB` | **Private** | Raw Research / Experimental | Early-stage algorithmic discoveries, experimental state reconstructions, exploratory hypotheses, raw probe telemetry, and documented failed experiments. |
| **7** | `VIPERCREST_SECURITY_LAB` | **Private** | Defensive Threat Modeling | Adversarial attack vectors, sensor-substitution defense, air-gap egress probes, misuse analysis, trust-boundary penetration suites, and unpublished vulnerability assessments. |
| **8** | `VIPERCREST_COMMERCIAL` | **Private** | Commercial Licensing | Enterprise customer packaging, $1,000 commercial licensing workflow, offline license minting (`mint_license.py`), and commercial entitlement records. |
| **9** | `VIPERCREST_ROOT` | **Offline Air-Gap (NEVER GitHub)** | Highest Sovereign Authority | Master Root Private Signing Key (`master_license_private_ROTATED.pem`), hardware security enclave, and root certificate issuance authority. |

---

### The Linear Discovery & Controlled Disclosure Pipeline

Information moves outward toward public distribution **only** after it survives the appropriate developmental and security gates. Unvalidated research never bleeds directly into production or public distributions.

```
                              [ DISCOVERY ]
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  [6] RESEARCH LAB (Private)   │ ◄── "What is this discovery?"
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  [7] SECURITY LAB (Private)   │ ◄── "Can this be exploited or abused?"
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            SENSITIVE / WEAKNESSES          SAFE TO DISCLOSE
                    │                               │
                    ▼                               ▼
          (Stays in Security Lab)       ┌───────────┼───────────┐
                                        ▼           ▼           ▼
                                      [ 3 ]       [ 4 ]       [ 5 ]
                                     VERIFY     BENCHMARK   INTEROP
                                        │           │           │
                                        └───────────┼───────────┘
                                                    │
                                                    ▼
                                          ┌───────────────────┐
                                          │   [2] ACADEMIC    │ ◄── Tagged releases (v1.0, v1.1)
                                          └─────────┬─────────┘     to universities
                                                    │
                                                    ▼
                                          ┌───────────────────┐
                                          │   [1] PUBLIC      │ ◄── Architectural documentation
                                          └───────────────────┘     & verified claims

OUT-OF-BAND AUTHORITIES:
─────────────────────────────────────────────────────────────────────────────
[8] VIPERCREST_COMMERCIAL : Separate private licensing, client packaging, & invoicing.
[9] VIPERCREST_ROOT       : Cold-storage air-gap. NEVER connected. NEVER crosses upward.
```

---

### Critical Operational Invariants

#### Invariant 1: The Academic Distribution Freeze
* **Current Correction**: Stop allowing unvetted or active experimental discovery tests to automatically commit into `VIPERCREST_ACADEMIC_DISTRIBUTION`.
* **Standard**: Academic distributions must remain immutable, milestone-tagged research snapshots ($v1.0\text{-academic}$, $v1.1\text{-academic}$) with strict reproducibility guarantees for academic reviewers and universities.
* **Flow**: All ongoing discoveries flow strictly into `VIPERCREST_RESEARCH_LAB` first.

#### Invariant 2: The Root Key Offline Ceiling (Repo 9)
* **Standard**: `VIPERCREST_ROOT` is an offline, air-gapped sovereign authority (`C:\ViperCrest_Licensor`).
* **Enforcement**: Under no circumstance is `master_license_private.pem` or `master_license_private_ROTATED.pem` staged, committed, pushed to GitHub, or connected to any networked service.
* Public repositories contain only public verification material (`runtime/public_seal.pem`).

#### Invariant 3: Security Lab Gatekeeper (Repo 7)
* Every new compound, protocol expansion, or wire frame must undergo adversarial stress-testing in `VIPERCREST_SECURITY_LAB` before public classification.
* If a discovery reveals an unexpected semantic drift, edge-case vulnerability, or potential side-channel, it remains quarantined within `VIPERCREST_SECURITY_LAB` until resolved or formally classified.

#### Invariant 4: Unified Logical Invariance
* The fixed `F1–F9` Logical Engine remains uniform across all 9 boundaries.
* What changes across repositories is **access privilege, disclosure classification, and trust boundary depth**, not the mathematical core of the engine.
