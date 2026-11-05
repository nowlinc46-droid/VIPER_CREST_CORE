"""The Stem: Kinetic Torque Gate (kinetic_gate.py).

Physical Actuator Safety Governor.
Enforces the fundamental physical coupling:
  tau_actual = current_amps * motor_torque_constant (k_t)

If measured torque deviates from electrical current expectations, or if
commanded torque exceeds absolute safety margins, the gate trips to FAIL-CLOSED (0.0 Nm).
ZERO PII.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Optional, Tuple


@dataclass(frozen=True)
class TorqueLimitConfig:
    motor_id: str
    max_torque_nm: float = 80.0          # Hard physical limit (e.g. humanoid joint)
    max_current_amps: float = 35.0       # Thermal fuse limit
    torque_constant_kt: float = 2.28     # Nm / A
    tolerance_margin_percent: float = 0.15


class KineticTorqueGate:
    """Deterministic kinetic torque governor for physical robotics."""

    def __init__(self, config: Optional[TorqueLimitConfig] = None):
        self.config = config or TorqueLimitConfig(motor_id="DEFAULT_ACTUATOR")
        self.is_tripped: bool = False
        self.trip_reason: Optional[str] = None
        self.last_gate_digest: str = ""

    def evaluate_actuator_safety(
        self,
        commanded_torque_nm: float,
        measured_current_amps: float,
        measured_torque_sensor_nm: float,
    ) -> Tuple[bool, float, str]:
        """Validates physical command against multi-modal electric/kinetic invariants.
        
        Returns:
            (is_safe, permitted_torque_nm, status_directive)
        """
        # 1. Check if gate is already tripped
        if self.is_tripped:
            return False, 0.0, f"TRIPPED_FAIL_CLOSED: {self.trip_reason}"

        # 2. Check commanded torque against physical limits
        if abs(commanded_torque_nm) > self.config.max_torque_nm:
            self.is_tripped = True
            self.trip_reason = f"EXCESSIVE_TORQUE_COMMAND: {commanded_torque_nm} Nm > max {self.config.max_torque_nm} Nm"
            return False, 0.0, self.trip_reason

        # 3. Check measured current against electrical limits
        if abs(measured_current_amps) > self.config.max_current_amps:
            self.is_tripped = True
            self.trip_reason = f"OVERCURRENT_EXCURSION: {measured_current_amps} A > max {self.config.max_current_amps} A"
            return False, 0.0, self.trip_reason

        # 4. Physical cross-check: Electrical Torque vs Transducer Torque (Ia * kt ~= tau)
        expected_torque = measured_current_amps * self.config.torque_constant_kt
        diff = abs(expected_torque - measured_torque_sensor_nm)
        max_allowed_diff = self.config.max_torque_nm * self.config.tolerance_margin_percent

        if diff > max_allowed_diff:
            self.is_tripped = True
            self.trip_reason = (
                f"TRANSDUCER_CURRENT_DECOUPLING: Expected {expected_torque:.2f} Nm from current, "
                f"measured {measured_torque_sensor_nm:.2f} Nm. Gap={diff:.2f} Nm > tolerance {max_allowed_diff:.2f} Nm"
            )
            return False, 0.0, self.trip_reason

        # 5. Safe: Compute cryptographic gate digest
        now_utc = datetime.now(timezone.utc).isoformat()
        raw = f"{commanded_torque_nm}:{measured_current_amps}:{measured_torque_sensor_nm}:{now_utc}"
        self.last_gate_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        return True, commanded_torque_nm, "BOUNDED_SAFE_TO_ACTUATE"

    def reset(self) -> None:
        """Manual reset required after safety trip."""
        self.is_tripped = False
        self.trip_reason = None
