# VIPER-LOMBARD-2026-001: Zero-Window Configuration Silently Disables Cumulative Bridge Rate Limiting

## 1. Title
**Zero-Window Configuration Silently Disables Cumulative Bridge Rate Limiting**

---

## 2. Executive Summary
`RateLimits.setRateLimit()` accepts a configuration with `window == 0`. In `availableAmountToSend()`, the comparison `timeSinceLastDeposit >= window` consequently evaluates `true` for every valid unsigned elapsed-time value. The effective in-flight amount is therefore reset during every capacity calculation instead of accumulating across operations. An isolated Foundry PoC using Solc 0.8.24 reproduces successive limit-sized updates without `RateLimitExceeded()`.

> **Note:** No live-system exploitation is claimed. This vulnerability was identified via offline invariant evaluation against the target commit and independently reproduced locally.

---

## 3. Target
- **Repository:** `lombard-finance/evm-smart-contracts`
- **Target Commit:** `7fe83e5` (Merge PR #571)
- **Compiler:** Solidity `0.8.24`
- **Affected Contracts:**
  - `contracts/libs/RateLimits.sol` (`setRateLimit`, `availableAmountToSend`, `updateLimit`)
  - `contracts/bridge/BridgeV2.sol` (`setTokenRateLimits`, `_withdraw`)
- **Scope Context:** `BridgeV2.sol` is a core in-scope asset governing cross-chain asset movement, deployed on Ethereum Mainnet at `0x451c54981C7DA5d95901b770C540547cF5FE0A2D`.

---

## 4. Root Cause
In `contracts/libs/RateLimits.sol` (lines 82-86):

```solidity
uint256 timeSinceLastDeposit = block.timestamp - _lastUpdated;
if (timeSinceLastDeposit >= _window) {
    currentAmountInFlight = 0;
    amountCanBeSent = _limit;
} else {
    uint256 decay = (_limit * timeSinceLastDeposit) / _window;
    ...
}
```

When `_window = 0`:
1. `timeSinceLastDeposit >= 0` is an unconditional tautology for all unsigned integers (`uint256`).
2. The `if` branch is taken on **every invocation**, unconditionally resetting `currentAmountInFlight = 0` and setting `amountCanBeSent = _limit`.
3. The decay calculation branch is never reached, and cumulative volume fails to accumulate across transactions.

---

## 5. Configuration Path
The call graph from owner administration down to the capacity calculation:

```text
BridgeV2.setTokenRateLimits(token, config)  [onlyOwner]
       │
       ▼
RateLimits.setRateLimit(rl, config)         [Accepts config.window = 0 without validation]
       │
       ▼
Storage Updated: rl.limit = L, rl.window = 0
       │
       ▼
Bridge Inbound Withdrawal: BridgeV2._withdraw()
       │
       ▼
RateLimits.updateLimit(rl, amount)
       │
       ▼
RateLimits.availableAmountToSend()
       │
       ▼
elapsed >= 0  ==>  currentAmountInFlight = 0  ==>  amountCanBeSent = limit
       │
       ▼
Amount never accumulates; multiple transfers up to limit succeed in the same block
```

---

## 6. Proof of Concept (PoC)
The minimal reproduction demonstrates that setting `window = 0` allows consecutive limit-sized transfers to execute without reverting:

```solidity
// Set rate limit with window = 0
bridge.setTokenRateLimits(TOKEN, RateLimits.Config({
    chainId: CHAIN_ID,
    limit: 1000 ether,
    window: 0
}));

// Three successive 1000 ether withdrawals succeed in the exact same block:
bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether); // PASS
bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether); // PASS
bridge.handleInboundWithdraw(CHAIN_ID, TOKEN, RECIPIENT, 1000 ether); // PASS

// Result: 3000 ether minted despite 1000 ether rate limit cap!
assert(bridge.totalMinted() == 3000 ether);
```

The complete test suite is available in `poc/test/RateLimitsValidationTest.t.sol` and can be executed with `forge test --root poc`.

---

## 7. Expected vs Actual Behavior

| Scenario | Expected Behavior | Actual Behavior (`window == 0`) |
| :--- | :--- | :--- |
| **Operation 1 (1000 units)** | Succeeds; consumes full capacity | Succeeds; in-flight reset to 0 |
| **Operation 2 (1000 units)** | Reverts with `RateLimitExceeded()` | Succeeds; in-flight reset to 0 |
| **Operation 3 (1000 units)** | Reverts with `RateLimitExceeded()` | Succeeds; in-flight reset to 0 |
| **Cumulative Accounting** | Throttles cumulative volume within duration | **Disabled; allows unbounded cumulative transfer volume** |

---

## 8. Control Experiment (A/B Isolation)
To prove that `window == 0` is the single variable responsible for the bypass, the test suite executes an exact A/B control experiment (`test_BridgeV2_ABControl_NonzeroWindowVsZeroWindow`):

```text
       CONTROL (window = 86400)               NEGATIVE CONTROL (window = 0)
─────────────────────────────────────       ─────────────────────────────────────
Transfer 1 (1000 ether): PASS               Transfer 1 (1000 ether): PASS
Transfer 2 (1000 ether): REVERT             Transfer 2 (1000 ether): PASS
                         [RateLimitExceeded] Transfer 3 (1000 ether): PASS
```

---

## 9. Security Impact
A zero-window configuration causes the cumulative rate-limit mechanism demonstrated by the tested library path to stop accumulating in-flight volume across successive operations. 

If this configuration occurs on an active in-scope bridge route, otherwise-authorized transfers could potentially proceed without the intended cumulative throttling. The ultimate financial impact depends on the bridge's surrounding authorization, liquidity, and settlement controls.

---

## 10. Preconditions

### Required:
1. `window` configured to zero via `BridgeV2.setTokenRateLimits()`.
2. The affected `RateLimits` library implementation is active on the route.
3. The affected transfer path reaches `updateLimit()`.
4. Inbound messages are otherwise validly signed by the bridge consortium / relayers.

### Not Established:
- **Malicious Unprivileged Configuration:** `setTokenRateLimits()` is strictly guarded by `onlyOwner` (`Ownable2StepUpgradeable`). An unprivileged attacker cannot invoke this function directly.
- **Current Deployed Zero-Window Configuration:** Not established. Live on-chain configurations were not actively probed.
- **Direct Loss of Funds:** No direct drainage is possible without valid incoming bridge message attestations.

---

## 11. Remediation
Add explicit validation rejecting `window == 0` in `RateLimits.setRateLimit()`:

```solidity
function setRateLimit(Data storage rl, Config memory config) internal {
    // Prevent zero-window configuration from disabling rate limit accumulation
    if (config.window == 0) revert MalformedRateLimit();

    updateLimit(rl, 0);

    rl.limit = config.limit;
    rl.window = config.window;
}
```

> **Note on `limit == 0`:** Do not automatically prohibit `limit == 0` without verifying whether Lombard intentionally uses `limit = 0` as a deliberate route-halting mechanism. In our tests, `limit = 0` cleanly clamps capacity to 0 and reverts all transfers. Only `window == 0` causes silent bypass.

This fix was implemented in `poc/src/PatchedRateLimits.sol` and validated in `test_FixValidation_PatchedRateLimits_RejectsZeroWindow()`.

---

## 12. Reproduction Evidence
- **PoC Source:** `poc/test/RateLimitsValidationTest.t.sol`
- **Foundry Test Command:** `forge test --root poc`
- **Test Output:** `evidence/forge-output.txt` (12/12 passed)
- **Target Commit:** `evidence/target-commit.txt` (`7fe83e5`)
- **Integrity Manifest:** `evidence/hashes.sha256`
