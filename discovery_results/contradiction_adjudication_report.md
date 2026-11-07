# Contradiction Adjudication Full-Stack Report

**Target:** ViperCrest Architecture (`C:\ViperCrest`)  
**Test Suite:** `tests/test_contradiction_adjudication.py`  
**Execution Status:** 4/4 Tests Passed  

---

## 1. Executive Summary

This test evaluated how contradictory evidence (specifically the Case-6 pair: *Record A: "secondary seal confirmed clean"* vs. *Record B: "secondary seal confirmed failed"*) behaves as it traverses the four architectural layers of ViperCrest.

The central finding:
> **The overwrite behavior is strictly contained within Tier 1 (the bare convergence loop dictionary). In Tiers 2, 3, and 4, higher-level domain cartridges, statutory adapters, and physical governors intercept contradictory assertions and enforce fail-closed containment (0.0 Nm torque / exception halt / S4 contradiction lock).**

---

## 2. Multi-Tier Adjudication Matrix

| Architectural Tier | Component Tested | Mechanism | Result on Contradictory Input | Status Emitted |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Bare Convergence Loop** | `convergence_engine.py` | `parse_recovery_data()` dictionary update (`resolved_map[seed] = val`) | **CONTRADICTION_COLLAPSED** (Last write wins; S7 marked resolved) | `BOUNDED` |
| **Tier 2: Domain Cartridge** | `reader_engine.py` / `domain_space.py` | Coordinate `S4` Invariant `INV_CONTRADICTION_LOCK` | **CONTRADICTION_PRESERVED** (Isolated to S4 under F7/F8) | `EVIDENTIARY_CONTRADICTION_FLAGGED` |
| **Tier 3: Statutory Settlement Gate** | `financial_adapter.py` | Policy FP-001 Invariant Rule | **CONTRADICTION_INTERCEPTED** (Raises `PolicyContradictionError`) | `CONTRADICTED` |
| **Tier 4: Embodied Kinetic Governor** | `the_stem/stem_governor.py` & `kinetic_gate.py` | Multi-modal cross-validation & Current/Torque Decoupling | **FAIL_CLOSED_CLAMPED** (Involuntary gate trip) | `SUSPENDED` / `0.0 Nm` |

---

## 3. Detailed Findings by Tier

### Tier 1 — Bare Convergence Loop (`convergence_engine.py`)
- **Mechanism:** Ingests raw text and executes regex extraction into a standard Python `dict`.
- **Observation:** When Record A is followed by Record B for the same coordinate (`S7`), Record B replaces Record A. Because `S7` is now present in `resolved_seed_map`, the gap evaluation treats `S7` as resolved. If `S7` was the sole remaining gap, status advances to `BOUNDED`.
- **Architectural Boundary:** The bare convergence engine is an invariant syntactic state sequencer, not an epistemic truth arbiter. It does not possess internal semantic conflict resolution.

### Tier 2 — Domain Cartridge Layer (`domain_space.py`, `reader_engine.py`)
- **Mechanism:** Coordinates $S_1 \dots S_9$ map semantic domain semantics. In CourtForge Legal and WMS Logistics, $S_4$ represents *Contradictions & Irreconcilable Conflicts*.
- **Observation:** When conflicting claims and sensor readings are parsed together, the cartridge isolates the conflict into $S_4$, setting state to `EVIDENTIARY_CONTRADICTION_FLAGGED` and holding the item in $F_7$ (Epistemic Uncertainty) for trier-of-fact review.

### Tier 3 — Statutory & Financial Policy Gate (`financial_adapter.py`)
- **Mechanism:** Evaluates high-value transactions against statutory policy rules and sanctions allowlists.
- **Observation:** When evidence submits contradictory assertions (e.g. verified vendor allowlist combined with an SDN sanctions match), the adapter intercepts the conflict before settlement transition and raises `PolicyContradictionError`:
  > *"CONTRADICTION DETECTED: Counterparty is matched on SDN sanctions list. State transition into BOUNDED settlement release is PERMANENTLY FORBIDDEN."*

### Tier 4 — Embodied Brainstem Governor (`the_stem`)
- **Mechanism:** Cross-validates multi-modal sensor pairs (optical vs. encoder) and physical transducer laws ($\tau = I_a \cdot K_t$).
- **Observation:** When physical signals contradict (e.g. optical flatlines while encoder measures motion, or measured torque diverges from electrical current), the kinetic gate trips immediately to `TRIPPED_FAIL_CLOSED` or `SUSPENDED`. Permitted actuator torque is clamped to strictly `0.0 Nm`.

---

## 4. Conclusion & Systemic Integrity Assessment

The dictionary overwrite observed in Case 6 is **not systemic**. It is an isolated property of the raw `parse_recovery_data()` dictionary mapper. As soon as evidence is routed through domain cartridges, statutory adapters, or physical governors, contradictory evidence trips the system into an explicit contradiction lock, an unhandled policy exception, or a 0.0 Nm kinetic clamp.
