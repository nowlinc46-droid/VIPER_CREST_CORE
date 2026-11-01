# ViperCrest Epistemic Candidate Trace

## 1. Provenance & Coordinate Path

```text
                           Z: ENGINE OPERATOR (F1 ... F9)
                                      ▲
                                     /
                                    /  (Invariant Execution Depth)
                                   /
         Y: DOMAIN SPACE (S1 ... S9) ───► X: TEMPORAL PHASE (T1 ... T9)
           (Structural Manifestation)       (Root -> Stone Continuum)
```

- **Temporal Phase:** $T_6$ (`T6_REFRACTING`)
- **Spatial Coordinate:** $S_6$ (`S6_Containment_State`)
- **Epistemic Classification:** `POSSIBLE`
- **Invariant Spine:** $F_5$ (Governing Rules) $\rightarrow$ $F_6$ (Precision Clamping) $\rightarrow$ $F_8$ (Opposing Transition)
- **Target Ingestion:** `fixtures/lombard_lbtc_bridge.json` (4,204 lines, 100 contracts)
- **Source Construct:** `contracts/libs/RateLimits.sol` & `contracts/bridge/BridgeV2.sol`

---

## 2. Epistemic Derivation Logic

During the evaluation of Lombard Finance contracts across the 81-state matrix and 729-coordinate tensor space:

1. **At Present ($T_5$):**
   - $S_5$ (Observed State): Outbound and inbound bridge transfers operate against active rate limit storage `$.rateLimit[_calcRateLimitId(chainId, token)]`.
   - $S_8$ (Governing Constraint): Immunefi Invariants $V06$ (Resource Exhaustion) & $V07$ (Fail-Closed Integrity) require that cumulative volume in window $W$ must not exceed limit $L$.
2. **At Backward Predecessor ($T_4$):**
   - Derived baseline where `amountInFlight == 0` and `amountCanBeSent == limit`.
3. **At Forward Reachability ($T_6$):**
   - The engine derived a candidate transition: If cumulative volume breaches $L$, the contract transitions to fail-closed containment (`RateLimitExceeded()`).
   - Concurrently, during the F5 $\rightarrow$ F7 uncertainty sweep, the engine discovered that `RateLimits.setRateLimit()` omitted the sanity check `checkRateLimitSanity()`, allowing a zero-window parameter $W=0$.
   - Topological consequence: $W=0 \implies \text{elapsed} \ge 0$ (tautology) $\implies \text{amountInFlight} \equiv 0$ on every invocation $\implies$ rate limit containment collapses.

---

## 3. Independent Confirmation
This prediction was subsequently extracted, compiled, and confirmed in a 12-test Foundry test suite using native Solc 0.8.24 without false positives.
