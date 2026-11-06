# VIPERCREST 2.0 — RESEARCH QUICKSTART GUIDE

Welcome to the ViperCrest Academic Research Package (`{{COPY_ID}}`). This environment runs 100% locally and air-gapped without cloud or internet connections.

---

### Step 1: Verify the Package Integrity
Before running any code, verify that your archive matches the official provenance hash:
```powershell
# In PowerShell:
Get-FileHash VC-ACADEMIC-000001.zip -Algorithm SHA256
```
Confirm the SHA-256 matches `artifact_sha256` in `verification_receipt.json`.

---

### Step 2: Run the 30-Second Verification Suite
Execute the master 8-pillar asset diligence runner:
```powershell
python verify_asset.py
```
**Expected Result:**
* 8/8 Diligence Pillars PASS
* 23 Unit tests executed and passed
* 100 HustleForge scenarios bounded
* Final Verdict: `ASSET FULLY BOUNDED, CRYPTOGRAPHICALLY AUDITED, AND VERIFIED`

---

### Step 3: Run the 5 Interactive Compound Demonstrations
Execute the multi-stage compound test suite:
```powershell
.\vc-compounds.cmd
```
* **Option 1:** Autonomous Robotics Kinetic Cutoff (80 Nm threshold).
* **Option 2:** Treasury Settlement & OFAC Sanctions Governor.
* **Option 3:** 7-Vector Cryptographic Tamper Defense.
* **Option 4:** Immunefi V03/V05 Smart Contract Exploit Defense.
* **Option 5:** 1-Line Seed Natural Hydration into 729-Coordinate Tensor.

---

### Step 4: Test Cross-Compiler Consensus (Rust & C99)
Emit the safety governor and compile with your local Rust toolchain:
```powershell
python ai_wrapper.py "syntax rust"
rustc --edition 2021 --crate-type lib lib.rs
```
**Expected Result:** `rustc` exits with code 0 (zero errors, zero warnings).

---

### Step 5: Cite ViperCrest in Scholarly Publications
When publishing research utilizing this engine, please cite:
```bibtex
@misc{nowlin2026vipercrest,
  author = {Nowlin, Clifton},
  title = {ViperCrest 2.0: A Deterministic Fail-Closed Invariant Engine for Bare-Metal Systems},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/nowlinc46-droid/VIPER_CREST_2.0}},
  note = {Academic Copy Provenance: {{COPY_ID}}}
}
```
