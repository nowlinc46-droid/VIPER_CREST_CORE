# ⚡ Shorthand Commands Quick Reference

ViperCrest provides dual-layer execution: **Human Action `.cmd` scripts** and **2-letter / 3-letter terminal shortcuts**.

---

## 🛠️ Real-World Operational Action Commands

| Action Command | Shortcut | Purpose | Usage Example |
| :--- | :--- | :--- | :--- |
| **`vc-scan`** | `vcscan` | Universal Target Scanner | `.\vc-scan USDtb.sol` |
| **`vc-audit-evm`** | `vcae` | Immunefi Invariant Audit | `.\vc-audit-evm` |
| **`vc-audit-solana`** | `vcas` | Solana / Anchor Rust Audit | `.\vc-audit-solana constant_product.rs` |
| **`vc-device-audit`** | `vcda` | USB / Phone Rootkit Audit | `.\vc-device-audit` |
| **`vc-drop-intake`** | `vcdrop` | Ingest & Hash Dropzone Files | `.\vc-drop-intake` |
| **`vc-sandbox`** | `vcsb` | Local Anvil Blockchain Node | `.\vc-sandbox` |
| **`vc-purge`** | `vcpurge` | Instant Self-Scrub (0.1s) | `.\vc-purge` |
| **`vc-ledger`** | `vcl` | SQLite State Ledger Health | `.\vc-ledger` |

---

## 🧠 Core Matrix & AI Tools

| Command | Shortcut | Purpose |
| :--- | :--- | :--- |
| **`vc-ai`** | `vcai` | Launch interactive plain-English conversation shell |
| **`vc-matrix`** | `vcm` | Run F1–F9 matrix sweep on target fixture |
| **`vc-foundry`** | `vcf` | Foundry EVM simulation bridge |
| **`vc-bridge`** | `vcb` | Universal 9x9 syntax bridge |
| **`vc-test`** | `vct` | Run full unit test suite (120/120 passing) |
| **`vc-probe`** | `vcp` | Run diagnostic stress probes (31 tests) |
| **`vc-help`** | `vch` | Display terminal command index |

---

## 🌐 Linux Container Equivalence (`vc.sh`)

In Linux, all commands map directly to `./vc.sh`:
```bash
./vc.sh scan <target>
./vc.sh audit-evm
./vc.sh audit-solana <file>
./vc.sh device-audit
./vc.sh sandbox
./vc.sh purge
./vc.sh ledger
./vc.sh test
```

---
*Links: [[Home]] | [[System Architecture]] | [[Matrix Evaluation Runbook]]*
