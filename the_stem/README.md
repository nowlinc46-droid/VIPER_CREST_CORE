# 🦾 The Stem: Standalone Epistemic Brainstem Tool

### *Deterministic, Fail-Closed Actuator Governor for Embodied AI & Robotics*

---

## 1. Overview

**The Stem** is a standalone, sovereign epistemic brainstem designed to sit between continuous, probabilistic neural planners (LLMs, Vision-Language-Action models) and physical robot actuators (humanoids like Tesla Optimus, robotic arms, autonomous vehicles).

### The Core Problem
Neural networks predict probabilistic tokens and trajectory curves. Under occlusion, sensor blinding, or model drift, probabilistic networks hallucinate and **fail open**. On physical hardware, a hallucinated motor command is an ungrounded kinetic collision.

### The Stem Solution
The Stem operates as a strict, fail-closed physical governor:
$$\mathcal{G}(S) \neq \emptyset \implies \mathbf{SUSPENDED} \ (0.0\text{ Nm Torque})$$

If sensor telemetry is blinded, stale, or contradictory, or if electrical current deviates from physical torque ($\tau \neq I_a \cdot k_t$), The Stem immediately cuts motor torque to zero before kinetic mutation occurs.

---

## 2. Architecture & Modules

```mermaid
flowchart TD
    A["Probabilistic Neural Cortex (LLM / VLA)"] -->|Commanded Trajectory| B["The Stem Governor"]
    C["Sensors (Optical, Encoders, IMU)"] --> D["Sensor Substitution & Bias Defense"]
    E["Actuator Telemetry (Current, Torque)"] --> F["Kinetic Torque Gate (Ia * kt)"]
    D --> B
    F --> B
    B -->|G(S) != Ø| G["FAIL-CLOSED: 0.0 Nm"]
    B -->|G(S) == Ø| H["BOUNDED DISPATCH: Motor Actuation"]
```

- **`stem_governor.py`**: Real-time tick evaluating sensor health, plant bounds, and torque limits.
- **`kinetic_gate.py`**: Actuator torque gate enforcing physical current-to-torque relationships ($I_a \cdot k_t \leftrightarrow \tau$).
- **`physical_grounding.py`**: Autonomous plant phase-space quantizer with zero OS APIs.
- **`sensor_bridge.py`**: Multi-modal sensor substitution and flatline-collapse defense.
- **`verify_stem.py`**: Standalone self-verification test runner.

---

## 3. Usage & CLI

```bash
# Run status inspection
python -m the_stem status
# Or using the root launcher:
stem status

# Run real-time brainstem cycle demo
python -m the_stem demo

# Run independent tool verification
python -m the_stem verify
```

---

## 4. Verification & Diligence

```bash
python the_stem/verify_stem.py
```
All internal tests pass 100% fail-closed on sensor fault, overcurrent excursion, and physical phase-space boundaries.
