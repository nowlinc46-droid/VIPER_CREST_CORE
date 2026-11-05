# ⚡ Shorthand Commands Quick Reference

ViperCrest provides single-token shorthand commands and descriptive long-form launchers located directly in the root repository (`C:\ViperCrest`). Every launcher enforces UTF-8, automatic Python virtual environment detection, argument forwarding, and exit code propagation.

---

## 🚀 Complete Command Matrix

### 1. Diligence, Audit & Asset Verification
| Shorthand | Long-form Alias | Target Script / Operation | Typical Syntax |
| :--- | :--- | :--- | :--- |
| `vcv` | `verify`, `vc-verify` | 8-Pillar Asset Verification & Diligence Suite | `vcv` or `verify` |
| `vcsiege` | `siege`, `vc-siege` | 100-Turn Invariant Siege (falsification against drift) | `siege` or `vcsiege` |
| `vcops` | `vc-ops`, `status` | Operational Dashboard (Kernels, Ledger, Air-Gap) | `vcops` or `status` |
| `vcaa` | `vc-audit-all` | Combined Invariant Engine + 8 Adversarial Vectors | `vcaa` |
| `vcae` / `vca` | `vc-audit-evm`, `vc-audit` | Immunefi Top 10 Invariant Security Audit | `vcae` |
| `vcas` | `vc-audit-solana` | Solana / Anchor Rust Invariant Security Audit | `vcas` |
| `vcda` | `vc-device-audit` | Live Hardware Forensic & Rootkit Detection | `vcda` |
| `vct` | `vc-test` | Complete 120+ Unit Test Suite Runner | `vct` |
| `vcp` | `vc-probe` | Diagnostic Stress Probes (`probe_matrix.py` v1/v2) | `vcp` |

### 2. The Stem — Autonomous Robotics Brainstem & Kinetic Safety
| Shorthand | Long-form Alias | Target Script / Operation | Typical Syntax |
| :--- | :--- | :--- | :--- |
| `vcstem` | `stem`, `vc-stem` | Standalone Epistemic Brainstem CLI | `vcstem status` |
| `vcstv` | `vc-stem-verify` | Physical Plant Phase Space & Invariant Verifier | `vcstv` |
| `vcstd` | `vc-stem-demo` | Real-Time Sensor Blinding & Torque Cutoff Demo | `vcstd` |

### 3. Convergence & State-Space Engines
| Shorthand | Long-form Alias | Target Script / Operation | Typical Syntax |
| :--- | :--- | :--- | :--- |
| `vcc` | `vc-converge` | Recursive F1-F9 Convergence Loop (Gaps -> Seal) | `vcc` |
| `vcm` | `vc-matrix` | 9-Sector Deterministic State Matrix (729-tensor) | `vcm --target fixtures\example.json` |
| `vchf` | `vc-hustleforge` | 100-Scenario Autonomous Life-Path State Traversal | `vchf` |
| `vcseed` | `vc-seed` | Minimal Seed Inversion & Tensor Emergence | `vcseed` |
| `vchyd` | `vc-hydrate` | Tri-Domain Space & Minimal Seed Hydration | `vchyd` |
| `vcb` | `vc-bridge` | Universal 9x9 Syntax Grammar Bridge | `vcb --input <FILE> --format 9x9` |
| `vcread` | `vc-reader` | Air-Gapped Multi-Format Parser & AST Decompiler | `vcread <FILE>` |
| `vcf` | `vc-foundry` | Foundry EVM Simulation & Fuzzing Bridge | `vcf --scenario <NAME>` |

### 4. Telemetry, Intake & Blockchain
| Shorthand | Long-form Alias | Target Script / Operation | Typical Syntax |
| :--- | :--- | :--- | :--- |
| `vcscan` | `vc-scan` | Universal Code & Smart Contract Security Scanner | `vcscan <CONTRACT.sol>` |
| `vcblk` | `vc-scan-blocks` | Block Height & ParentHash Continuity Scanner | `vcblk` |
| `vcrpc` | `vc-rpc` | Typed Multi-Chain RPC Dispatcher with Fallbacks | `vcrpc eth_blockNumber` |
| `vcfin` | `vc-financial` | FinCEN / SWIFT MT103 / Fedwire Settlement Audit | `vcfin` |
| `vci` | `vc-intake` | Phone & Hardware Forensic Telemetry Intake | `vci` |
| `vcdrop` | `vc-drop-intake` | SHA-256 Hashing, Quarantine & Intake Dropzone | `vcdrop` |
| `vcsb` | `vc-sandbox` | Launch Local Anvil Testnet Node (127.0.0.1:8545) | `vcsb` |

### 5. System Controls & State Ledger
| Shorthand | Long-form Alias | Target Script / Operation | Typical Syntax |
| :--- | :--- | :--- | :--- |
| `vco` | `vc-online` | Controlled Online Intake Mode | `vco --url <URL> --case-id <ID>` |
| `vcoff` | `vc-offline` | Strictly Air-Gapped Offline Mode (Default) | `vcoff --analytics` |
| `vcl` | `vc-ledger` | Inspect SQLite Ledger (`runtime/viper_state.db`) | `vcl` |
| `vcs` | `vc-status` | Quick State Database Block Counts & Receipts | `vcs` |
| `vcpurge` | `vc-purge` | Safe Ephemeral Cache Scrub (Preserves Ledger DB) | `vcpurge` |
| `vcai` | `vc-ai` | Interactive Plain-English AI Security Shell | `vcai` |
| `vcprompt` | `vc-prompt` | Execute Precise Natural Language Prompt | `vcprompt "<PROMPT>"` |
| `vcemit` | `vc-emit` | Communicate Solely via Syntax (C, Rust, Sol, JSON) | `vcemit <c\|rust\|sol\|json>` |
| `vcdisc` | `vc-discovery` | Run Discovery Invariant Suite or Discovery Prompt | `vcdisc` or `vcdisc "<QUERY>"` |
| `vch` | `vc-help` | Master Interactive Command Reference Index | `vch` |
| `vc` | `vipercrest` | Universal Master ViperCrest CLI | `vc matrix` / `vc offline` |

---

## 💡 Subcommand Aliases in `viper.py`

When using `vc` or `vipercrest`, subcommands also support ultra-short aliases:
- `vc m` ➔ `vc matrix`
- `vc on` ➔ `vc online`
- `vc off` ➔ `vc offline`

---

## 🔒 Guaranteed Invariants
- **Fail-Closed Default**: Any missing telemetry, unresolved coordinate, or corrupted input halts in `SUSPENDED` (zero speculation).
- **Air-Gap Containment**: Zero external socket egress unless explicitly run in `--online` mode.
- **Frozen Kernel Parity**: Bit-for-bit SHA-256 invariance maintained across `convergence_engine.py`, `viper_matrix.py`, `viper_core.py`, and `viper_http.py`.
- **Cryptographic Receipts**: Every state transition signed with Ed25519 and chained to predecessor hash.
