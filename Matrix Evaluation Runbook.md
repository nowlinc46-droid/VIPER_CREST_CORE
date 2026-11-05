# 📋 Matrix Evaluation Runbook

This runbook outlines standard operating procedures for executing audits, scanning targets, and verifying invariant proofs using ViperCrest.

---

## 🚀 Procedure 1: Universal Target Scanning

Scan any smart contract, file, or protocol:
```powershell
.\vc-scan <target_file_or_address>
```
* **Step 1:** The reader engine automatically classifies the syntax (Solidity, Rust, Vyper, Move, etc.).
* **Step 2:** Decomposes syntax into entities, actions, and roles.
* **Step 3:** Sweeps through the F1–F9 invariant matrix.
* **Step 4:** Emits a 4-point plain English report (*What It Does, Who Controls It, Rules Enforced, Attention Needed*).

---

## 🧪 Procedure 2: Running the Immunefi Invariant Audit

To execute automated invariant verification against critical vulnerabilities:
```powershell
.\vc-audit-evm
```
* Verifies zero-window rate limit bypasses.
* Probes reentrancy execution paths.
* Validates access control transitions.

---

## 🔍 Procedure 3: Diagnostic Stress Probes

To verify internal matrix anti-cheat and integrity constraints:
```powershell
.\vcp
```
* Executes 31 automated adversarial test vectors.
* Probes multi-session isolation and cryptographic signature binding.

---

## 🧹 Procedure 4: Secure Workspace Purge

To wipe ephemeral staging without touching the immutable ledger:
```powershell
.\vc-purge
```
* Cleans temporary dropzones and staging inboxes in 0.1s.
* Preserves `runtime/viper_state.db` intact.

---
*Links: [[Home]] | [[System Architecture]] | [[Shorthand Commands Quick Reference]]*
