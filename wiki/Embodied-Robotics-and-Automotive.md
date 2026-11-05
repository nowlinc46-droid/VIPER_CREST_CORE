# 🦾 Embodied Robotics & Android Automotive (AAOS) Safety

ViperCrest bridges discrete cognitive reasoning to real-world continuous physics through **The Stem** and the **Android Automotive OS (AAOS) Safety Bridge**.

---

## 🦾 The Stem: Epistemic Brainstem Governor

**The Stem** (`the_stem/`) sits directly between high-level probabilistic neural cortex models (LLMs, Vision-Language-Action models) and physical robot joint actuators:

$$\mathcal{G}(S) \neq \emptyset \implies \mathbf{0.0\text{ Nm Torque (FAIL-CLOSED)}}$$

If sensor telemetry is blinded, stale, or contradictory, or if electrical current deviates from physical torque ($\tau \neq I_a \cdot k_t$), The Stem immediately cuts motor torque to zero before kinetic mutation occurs.

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

### Core Robotics Modules:
* **[`kinetic_gate.py`](file:///C:/ViperCrest/the_stem/kinetic_gate.py):** Actuator torque gate enforcing physical current-to-torque relationships ($\tau = I_a \cdot k_t$). Clamps to $80\text{ Nm}$ and $35\text{ A}$ thermal fuses.
* **[`sensor_bridge.py`](file:///C:/ViperCrest/the_stem/sensor_bridge.py):** Defends against sensor blinding, spoofing, and flatline collapse ($< 10^{-6}$ variance).
* **[`physical_grounding.py`](file:///C:/ViperCrest/the_stem/physical_grounding.py):** Autonomous plant phase-space quantizer with zero OS APIs, clamping kinematic state to $[-\pi, +\pi]$ and bounding structural acceleration ($< 250\text{ rad/s}^2$).

---

## 🚗 Android Automotive OS (AAOS) Safety Bridge ([`automotive_bridge.py`](file:///C:/ViperCrest/the_stem/automotive_bridge.py))

Implements **ISO 26262 ASIL-D** deterministic fail-closed gating between Android Automotive (AAOS CarService / VHAL) and physical vehicle actuators:

1. **Electric Power Steering (EPS) Assist Torque Gate:** Clamps assist torque strictly between $\pm 12.0\text{ Nm}$, enforcing $\tau_{\text{steer}} = I_{\text{motor}} \cdot k_t$.
2. **Dual APPS Plausibility & Flatline Defense:** Cross-checks Accelerator Pedal Position Sensor 1 and Sensor 2. If divergence exceeds $5.0\%$, throttle is immediately clamped to $0.0\%$.
3. **Brake-Throttle Override (BTO):** If brake pedal pressure is detected, throttle actuation is forcefully zero-clamped regardless of ADAS or driver commands.
4. **J2534 VCI Integration ([`os_builder/j2534_bridge.py`](file:///C:/ViperCrest/os_builder/j2534_bridge.py)):** Standardized vehicle communication interface supporting ISO 15765 CAN diagnostics and hardware pass-through.

---

## 🏃 Running Robotics & Automotive Verifications

```powershell
# Run Standalone Stem Verification Suite (5/5 PASS)
python the_stem/verify_stem.py

# Run AAOS Automotive Tool & VHAL Tests (7/7 PASS)
python -m unittest tests/test_aaos_automotive_tool.py

# Run J2534 VCI Bridge Protocol Tests
python -m unittest tests/test_j2534_vci_bridge.py
```
