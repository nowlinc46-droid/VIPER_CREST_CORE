# VIPER-LOMBARD-2026-001 Validation Package

This repository contains the independent verification package, executable Foundry reproduction, and formal finding report for:

**VIPER-LOMBARD-2026-001: Zero-Window Configuration Silently Disables Cumulative Bridge Rate Limiting**

---

## 📁 Package Structure

```text
VIPER-LOMBARD-2026-001/
│
├── README.md                 # Package index and reproduction instructions
├── FINDING.md                # 12-section formal security audit finding report
│
├── poc/                      # Self-contained Foundry Solc 0.8.24 test project
│   ├── foundry.toml          # Foundry compiler configuration
│   ├── src/
│   │   ├── RateLimits.sol           # Original Lombard RateLimits implementation
│   │   └── PatchedRateLimits.sol    # Remediated RateLimits implementation
│   └── test/
│       └── RateLimitsValidationTest.t.sol  # 12-test suite confirming vulnerability & fix
│
├── evidence/                 # Empirical execution logs & cryptographic hashes
│   ├── forge-output.txt      # Bit-exact terminal output from forge test
│   ├── target-commit.txt     # Target repository commit & compiler metadata
│   └── hashes.sha256         # SHA-256 manifest of all validation files
│
└── vipercrest/               # Methodology & Discovery Trace
    └── candidate-trace.md    # Epistemic F5/F6/F8 -> T6:S6 candidate origin
```

---

## 🚀 Quick Reproduction

To run the complete 12-test Foundry validation locally:

```bash
cd poc
forge test -vvv
```

All 12 tests will compile with native Solc 0.8.24 and confirm:
1. Backward hydration baseline derivation ($T_4:S_2$)
2. Nominal transfer execution ($T_5:S_5$)
3. Over-capacity containment revert (`RateLimitExceeded`)
4. Revert state preservation (Invariant $V07$)
5. Zero-limit capacity clamping
6. Zero-window silent bypass proof
7. BridgeV2 integration & reachability (Test 8)
8. Nonzero-window A/B control experiment (Test 9)
9. Authorization boundary check (`onlyOwner` / Test 10)
10. Patched remediation validation (Test 12)
