"""The Stem: Master Epistemic Brainstem Governor (stem_governor.py).

Positioned between high-level neural planners (LLMs / VLAs) and physical actuators.
Enforces involuntary fail-closed suspension:
  G(S) != empty => SUSPENDED (0.0 Nm Actuator Torque)

ZERO PII.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from .kinetic_gate import KineticTorqueGate, TorqueLimitConfig
from .physical_grounding import PhysicalPlantQuantizer, PlantState
from .sensor_bridge import SensorSubstitutionEngine, SensorReading


class GovernorState(str, Enum):
    IDLE = "IDLE"
    BOUNDED_ACTIVE = "BOUNDED_ACTIVE"
    SUSPENDED = "SUSPENDED"
    EMERGENCY_HALT = "EMERGENCY_HALT"


@dataclass
class ActuationCommand:
    joint_id: str
    target_torque_nm: float
    target_velocity_rad_s: float
    max_duration_ms: int
    source_planner: str


class StemGovernor:
    """The Autonomous Brainstem State Governor for Embodied Artificial Intelligence."""

    def __init__(self, motor_id: str = "JOINT_ACTUATOR_01"):
        self.motor_id = motor_id
        self.torque_gate = KineticTorqueGate(TorqueLimitConfig(motor_id=motor_id))
        self.plant_quantizer = PhysicalPlantQuantizer()
        self.sensor_engine = SensorSubstitutionEngine()
        self.state: GovernorState = GovernorState.IDLE
        self.gap_set: List[str] = []
        self.flight_recorder: List[Dict[str, Any]] = []

    def log_transition(self, event: str, payload: Dict[str, Any]) -> str:
        now_utc = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(f"{event}:{json.dumps(payload, sort_keys=True)}:{now_utc}".encode("utf-8")).hexdigest()
        record = {
            "timestamp": now_utc,
            "event": event,
            "payload": payload,
            "record_digest": digest,
        }
        self.flight_recorder.append(record)
        return digest

    def evaluate_cycle(
        self,
        command: ActuationCommand,
        optical_reading: SensorReading,
        encoder_reading: SensorReading,
        measured_current_amps: float,
        measured_torque_sensor_nm: float,
        pos_rad: float,
        vel_rad_s: float,
        acc_rad_s2: float,
    ) -> Tuple[GovernorState, float, str]:
        """Main real-time tick of The Stem brainstem.
        
        Returns:
            (GovernorState, dispatched_torque_nm, explanation)
        """
        self.gap_set.clear()

        # 1. Ingest & Validate Sensors (Check for flatline or spoofing)
        ok_opt, err_opt = self.sensor_engine.ingest_reading(optical_reading)
        if not ok_opt:
            self.gap_set.append(f"GAP_OPTICAL_FAULT: {err_opt}")

        ok_enc, err_enc = self.sensor_engine.ingest_reading(encoder_reading)
        if not ok_enc:
            self.gap_set.append(f"GAP_ENCODER_FAULT: {err_enc}")

        # 2. Plant Stability Check
        plant = self.plant_quantizer.quantize_state(
            joint_name=command.joint_id,
            pos_rad=pos_rad,
            vel_rad_s=vel_rad_s,
            acc_rad_s2=acc_rad_s2,
        )
        if not plant.is_stable:
            self.gap_set.append(f"GAP_PLANT_UNSTABLE: Accel {acc_rad_s2:.2f} rad/s2 out of kinetic envelope")

        # 3. Epistemic Gap Evaluation: G(S) != empty => FAIL CLOSED
        if self.gap_set:
            self.state = GovernorState.SUSPENDED
            self.log_transition("FAIL_CLOSED_SUSPENSION", {"gaps": self.gap_set, "dispatched_torque": 0.0})
            return GovernorState.SUSPENDED, 0.0, f"SUSPENDED: Epistemic gap set active: {self.gap_set}"

        # 4. Kinetic Torque & Electrical Gate
        is_safe, torque_out, gate_msg = self.torque_gate.evaluate_actuator_safety(
            commanded_torque_nm=command.target_torque_nm,
            measured_current_amps=measured_current_amps,
            measured_torque_sensor_nm=measured_torque_sensor_nm,
        )

        if not is_safe:
            self.state = GovernorState.EMERGENCY_HALT
            self.log_transition("KINETIC_GATE_TRIPPED", {"reason": gate_msg, "dispatched_torque": 0.0})
            return GovernorState.EMERGENCY_HALT, 0.0, f"EMERGENCY_HALT: {gate_msg}"

        # 5. All Invariants Satisfied: BOUNDED_ACTIVE
        self.state = GovernorState.BOUNDED_ACTIVE
        self.log_transition("ACTUATION_BOUNDED", {"dispatched_torque": torque_out, "joint": command.joint_id})
        return GovernorState.BOUNDED_ACTIVE, torque_out, "BOUNDED_SAFE_TO_ACTUATE"
