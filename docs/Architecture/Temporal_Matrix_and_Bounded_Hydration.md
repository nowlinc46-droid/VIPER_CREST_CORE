# ViperCrest Temporal Matrix & Bounded Hydration

## 1. Architectural Invariant & Separation of Concerns

ViperCrest maintains a strict, mathematically closed separation between the execution engine and the domain state matrix:

$$\boxed{\mathbf{F_1 \text{--} F_9 = \text{Invariant Runtime Engine}}}$$
$$\boxed{\mathbf{S_1 \dots S_9 = \text{Domain Spatial Seeds at Time } T}}$$
$$\boxed{\mathbf{T_1 \dots T_9 = \text{The 9 Temporal Positions (Root } \rightarrow \text{ Stone)}}}$$
$$\boxed{\mathbf{9 \text{ Temporal Slices} \times 9 \text{ Spatial Seeds} = 81 \text{ State Positions}}}$$

The engine never expands to 81 functions. Exactly one fixed $F_1 \text{--} F_9$ engine evaluates every position and transition across the matrix.

---

## 2. The Matrix over Matrices Representation

```text
                    TEMPORAL MATRIX

        ┌────────────┬────────────┬────────────┐
        │ SPACE(T1)  │ SPACE(T2)  │ SPACE(T3)  │
        ├────────────┼────────────┼────────────┤
        │ SPACE(T4)  │ SPACE(T5)  │ SPACE(T6)  │
        ├────────────┼────────────┼────────────┤
        │ SPACE(T7)  │ SPACE(T8)  │ SPACE(T9)  │
        └────────────┴────────────┴────────────┘

Each SPACE(T) =
        ┌────┬────┬────┐
        │ S1 │ S2 │ S3 │
        ├────┼────┼────┤
        │ S4 │ S5 │ S6 │
        ├────┼────┼────┤
        │ S7 │ S8 │ S9 │
        └────┴────┴────┘
```

### The 9 Temporal Phases (Recovered Lineage)
1. `T1_ROOT` — Genesis Origin / Physical Bedrock
2. `T2_VEIL` — Latent / Hidden Ingress Threshold
3. `T3_PATH_IN` — Incoming Causal Vector
4. `T4_STABILITY` — Pre-Disruption Baseline
5. `T5_COMPOUNDING` — $T_0$ / Active Observed Present
6. `T6_REFRACTING` — Branching Possibilities / Prisms
7. `T7_FLAME` — Active Transformation & Friction
8. `T8_PATH_OUT` — Directed Containment & Remediated Flow
9. `T9_STONE` — Furthest Resolvable State / Forge Decree

---

## 3. The Three Verification Pillars

1. **Spatial Integrity:** Every instantiated `SPACE(T)` instance contains the exact $S_1 \dots S_9$ geometry.
2. **Temporal Integrity:** Transitions between `SPACE(T_n)` instances obey Root-derived constraints and relationships.
3. **Engine Integrity:** Exactly the same $F_1 \text{--} F_9$ runtime evaluates every position.

---

## 4. Evidence-Bounded Hydration Rules

Hydration never invents values (`if missing: invent_value()` is strictly forbidden):

```text
OBSERVED ──► RELATIONSHIPS ──► CONSTRAINTS ──► CANDIDATE ──► TEST THROUGH F1-F9 ──► STATUS
```

### Epistemic Hydration Statuses
* `OBSERVED`: Directly verified by incoming telemetry at $T_0$.
* `DERIVED`: Uniquely supported by evidence, invariants, and causal progression.
* `POSSIBLE`: Feasible candidate hypothesis awaiting further observation.
* `CONTRADICTED`: Incompatible with invariants or physical facts.
* `UNRESOLVED`: Preserved without speculation under $F_7$ (Zero Hallucination).

---

## 5. Inter-Space Transition Receipts

Transitions between full 9-spaces are sealed with cryptographic attestation:

$$R_n = \text{Hash}\left( \text{SPACE}(T_n), \, \Delta_n, \, \text{SPACE}(T_{n+1}), \, F_1 \text{:} F_9 \right)$$
