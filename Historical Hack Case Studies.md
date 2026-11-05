# 🛡️ Historical Hack Case Studies & Invariant Verifications

This runbook documents the **Historical Hack Suite** available in ViperCrest. You can evaluate historical exploit vectors using either:
1. **Source-Level Scanning** (`vcscan` / `vc-scan`) on archetypal Solidity contracts in `fixtures/historical_hacks/`.
2. **State-Transition Simulation** (`vcf` / `vc-foundry`) across Immunefi invariant break scenarios.

---

## ⚡ Quick Execution Table

| Target Case | Vector / Archetype | Command | Expected Invariant Verdict |
| :--- | :--- | :--- | :--- |
| **The DAO (2016)** | Reentrancy & State Ordering | `.\vcscan fixtures\historical_hacks\the_dao_reentrancy.sol` | **Action Needed** (Check-effects-interactions / ReentrancyGuard) |
| **Parity Multi-Sig (2017)** | Unprotected Init & Selfdestruct | `.\vcscan fixtures\historical_hacks\parity_wallet_init.sol` | **Action Needed** (Initializer guard required) |
| **Nomad Bridge (2022)** | Zero-Root Acceptance | `.\vcscan fixtures\historical_hacks\nomad_bridge_zero_root.sol` | **Action Needed** (Remove `confirmAt[0x0]` root confirmation) |
| **BeautyChain BEC (2018)** | Integer Arithmetic Overflow | `.\vcscan fixtures\historical_hacks\beautychain_batch_overflow.sol` | **Action Needed** (Use SafeMath / Solidity 0.8+) |
| **Lombard Finance (2024)** | Zero-Window Rate Limit Bypass | `.\vcscan fixtures\historical_hacks\lombard_zero_window_ratelimit.sol` | **Action Needed** (Fix zero-window check in RateLimits) |

---

## 🔬 State Simulation Bridge Scenarios (`vcf`)

For full $F_1 \to F_9$ temporal matrix evaluation and ledger state transition proofs, use the Foundry bridge simulation scenarios:

```cmd
# 1. Simulate Reentrancy Vault Drainage (The DAO / Euler / Lendf.me archetype)
.\vcf --scenario reentrancy

# 2. Simulate Flash Loan Oracle Spot Price Manipulation (bZx / Mango / BonqDAO archetype)
.\vcf --scenario oracle_manipulation

# 3. Simulate Access Control Parameter Hijack (Nomad / Parity archetype)
.\vcf --scenario unauthorized_config

# 4. Simulate Proxy Storage Collision (Audius / OpenZeppelin upgrade collision)
.\vcf --scenario storage_collision

# 5. Run All Scenarios Concurrently
.\vcf --scenario all
```

Each run generates a state diff observation, executes the $F_1 \to F_9$ invariant engine, computes variance scores, and seals the result into the immutable SQLite ledger (`runtime/viper_state.db`).

---

## 📜 Historical Case Analysis Breakdown

### 1. The DAO (2016)
- **File**: `fixtures/historical_hacks/the_dao_reentrancy.sol`
- **Core Mechanism**: `msg.sender.call.value(amount)()` invokes the caller's fallback function before `balances[msg.sender] -= amount` is executed.
- **Matrix Invariant Caught**: Sector 5 / 6 forward reachability detects uncommitted state during external interaction.

### 2. Parity Multi-Sig Wallet (2017)
- **File**: `fixtures/historical_hacks/parity_wallet_init.sol`
- **Core Mechanism**: `initWallet()` lacks an `initializer` modifier or access gating, enabling unauthenticated callers to claim ownership of the shared library and invoke `kill()` (`selfdestruct`).
- **Matrix Invariant Caught**: Access control boundary failure on privileged state mutation.

### 3. Nomad Bridge (2022)
- **File**: `fixtures/historical_hacks/nomad_bridge_zero_root.sol`
- **Core Mechanism**: The contract initialized `confirmAt[bytes32(0)] = 1`. Unproven messages evaluate to `root == 0x0`, causing fraudulent bridge withdrawals to be treated as confirmed.
- **Matrix Invariant Caught**: Sector 2 / 7 boundary failure: zero-hash root acceptance bypasses consensus validation.

### 4. BeautyChain (BEC 2018)
- **File**: `fixtures/historical_hacks/beautychain_batch_overflow.sol`
- **Core Mechanism**: `uint256 amount = uint256(cnt) * _value` in Solidity `<0.8.0` without SafeMath causes arithmetic overflow, wrapping `amount` to `0` and bypassing balance requirements.
- **Matrix Invariant Caught**: Arithmetic precision and upper bound overflow without compile-time or library clamping.

### 5. Lombard Finance (2024)
- **File**: `fixtures/historical_hacks/lombard_zero_window_ratelimit.sol`
- **Core Mechanism**: In `RateLimits.sol`, configuring `window == 0` causes `timeSinceLastDeposit >= window` to evaluate true unconditionally, wiping accumulated in-flight volume.
- **Matrix Invariant Caught**: Throttling decay calculation bypass; unconstrained cumulative transfer volume.

---

## 🔗 Related Notes
- [[Home]]
- [[System Architecture]]
- [[Agnostic 9x9 Matrix Protocol]]
- [[Shorthand Commands Quick Reference]]
- [[Matrix Evaluation Runbook]]
