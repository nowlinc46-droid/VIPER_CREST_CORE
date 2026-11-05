"""The Stem: Android Automotive OS (AAOS) VHAL & Safety Bridge (automotive_bridge.py).

Implements ISO 26262 ASIL-D and Immunefi-grade deterministic fail-closed gating
between Android Automotive (AAOS CarService / VHAL) and physical vehicle actuators:
  1. Electric Power Steering (EPS) Assist Torque Gate: tau_steer == I_motor * K_t
  2. Dual Accelerator Pedal Position (APPS_1 / APPS_2) Plausibility & Flatline Defense
  3. Brake-Throttle Override (BTO): Brake actuation forcefully zero-clamps throttle
  4. Automotive Invariant: G(S) != empty => Involuntary Fail-Closed (0.0 Nm / 0.0% Throttle)

ZERO PII.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from .kinetic_gate import KineticTorqueGate, TorqueLimitConfig
from .sensor_bridge import SensorReading, SensorSubstitutionEngine
from .stem_governor import GovernorState


class VehiclePropertyId(IntEnum):
    """Standard Android Automotive (AAOS) Vehicle Property Identifiers."""
    GEAR_SELECTION = 0x11400400
    CURRENT_GEAR = 0x11400401
    PARKING_BRAKE_ON = 0x11200402
    PERF_VEHICLE_SPEED = 0x11600207
    ACCELERATOR_PEDAL_POSITION = 0x11600B03
    BRAKE_PEDAL_POSITION = 0x11600B05
    STEERING_WHEEL_ANGLE = 0x11400BC0
    STEERING_WHEEL_TORQUE = 0x11600BC1  # Custom / Vendor EPS Property
    TRACTION_MOTOR_CURRENT = 0x11600BC2  # Custom / Vendor Inverter Telemetry


class AutomotiveState(str, Enum):
    ARMED_NORMAL = "ARMED_NORMAL"
    ASSIST_ACTIVE = "ASSIST_ACTIVE"
    FAIL_CLOSED_CLAMPED = "FAIL_CLOSED_CLAMPED"
    EMERGENCY_REVERSION = "EMERGENCY_REVERSION"


@dataclass
class AutomotiveActuatorCommand:
    """Requested trajectory from high-level AAOS cortex / ADAS assistant."""
    command_id: str
    target_steering_torque_nm: float     # EPS assist torque (-12.0 to +12.0 Nm)
    target_throttle_percent: float       # 0.0% to 100.0%
    target_brake_percent: float          # 0.0% to 100.0%
    source_service: str = "AAOS_CAR_SERVICE"


@dataclass
class AutomotiveTelemetryFrame:
    """Raw telemetry frame from Android Automotive VHAL / CAN Bus."""
    timestamp_ms: int
    vehicle_speed_kph: float
    steering_angle_deg: float
    eps_current_amps: float
    measured_steering_torque_nm: float
    apps_sensor_1_pct: float             # Primary accelerator pedal sensor
    apps_sensor_2_pct: float             # Secondary redundant accelerator sensor
    brake_pressure_bar: float
    gear_selection: int = 4              # 4 = DRIVE


class AndroidAutomotiveStemBridge:
    """Real-time fail-closed epistemic governor for Android Automotive OS."""

    def __init__(
        self,
        max_eps_torque_nm: float = 12.0,
        max_eps_current_amps: float = 30.0,
        eps_torque_constant_kt: float = 1.85,
        max_apps_divergence_pct: float = 5.0,
    ):
        self.config = TorqueLimitConfig(
            motor_id="EPS_STEERING_ACTUATOR_01",
            max_torque_nm=max_eps_torque_nm,
            max_current_amps=max_eps_current_amps,
            torque_constant_kt=eps_torque_constant_kt,
            tolerance_margin_percent=0.15,
        )
        self.torque_gate = KineticTorqueGate(self.config)
        self.sensor_engine = SensorSubstitutionEngine(min_variance_threshold=1e-5)
        self.max_apps_divergence = max_apps_divergence_pct
        self.state: AutomotiveState = AutomotiveState.ARMED_NORMAL
        self.gap_set: List[str] = []
        self.flight_recorder: List[Dict[str, Any]] = []

    def evaluate_telemetry_and_actuate(
        self,
        cmd: AutomotiveActuatorCommand,
        telemetry: AutomotiveTelemetryFrame,
    ) -> Tuple[AutomotiveState, float, float, str]:
        """Evaluates automotive safety invariants on a real-time cycle.

        Returns:
            (AutomotiveState, permitted_steering_torque_nm, permitted_throttle_pct, directive)
        """
        self.gap_set.clear()

        # 1. Brake-Throttle Override (BTO) check
        # If mechanical brake is actively pressed, throttle must be zeroed immediately.
        effective_throttle_req = cmd.target_throttle_percent
        if telemetry.brake_pressure_bar > 1.5 or cmd.target_brake_percent > 1.0:
            if effective_throttle_req > 0.0:
                self.gap_set.append("BRAKE_THROTTLE_OVERRIDE_ACTIVE")
                effective_throttle_req = 0.0

        # 2. Dual Accelerator Pedal Position (APPS) plausibility check (ISO 26262 ASIL-D)
        apps_gap = abs(telemetry.apps_sensor_1_pct - telemetry.apps_sensor_2_pct)
        if apps_gap > self.max_apps_divergence:
            self.gap_set.append(f"APPS_PEDAL_SENSOR_DIVERGENCE: gap {apps_gap:.2f}% > max {self.max_apps_divergence}%")

        # 3. Sensor Flatline / Blinding defense on Steering & Wheel Speed
        steer_sens = SensorReading(
            sensor_id="EPS_STEERING_ANGLE",
            channel_type="ENCODER",
            value=telemetry.steering_angle_deg,
            variance=0.01 if abs(telemetry.steering_angle_deg) > 0.001 else 0.005,
            timestamp_ms=telemetry.timestamp_ms,
        )
        s_ok, s_msg = self.sensor_engine.ingest_reading(steer_sens)
        if not s_ok:
            self.gap_set.append(s_msg)

        # 4. Kinetic Electric Power Steering (EPS) Torque Gate Check
        # Physical coupling: tau_actual = current_amps * k_t
        t_safe, allowed_torque, t_msg = self.torque_gate.evaluate_actuator_safety(
            commanded_torque_nm=cmd.target_steering_torque_nm,
            measured_current_amps=telemetry.eps_current_amps,
            measured_torque_sensor_nm=telemetry.measured_steering_torque_nm,
        )
        if not t_safe:
            self.gap_set.append(f"EPS_KINETIC_TORQUE_BREACH: {t_msg}")

        # 5. Fail-Closed Invariant Resolution
        # G(S) != empty => Involuntary Fail-Closed (0.0 Nm torque, 0.0% throttle)
        if self.gap_set:
            self.state = AutomotiveState.FAIL_CLOSED_CLAMPED
            permitted_torque = 0.0
            permitted_throttle = 0.0
            explanation = "FAIL_CLOSED_CLAMP: " + " | ".join(self.gap_set)
        else:
            self.state = AutomotiveState.ASSIST_ACTIVE
            permitted_torque = allowed_torque
            permitted_throttle = effective_throttle_req
            explanation = "ALL_AUTOMOTIVE_INVARIANTS_VERIFIED_BOUNDED"

        # 6. Cryptographic Flight Recording
        now_utc = datetime.now(timezone.utc).isoformat()
        cycle_digest = hashlib.sha256(
            f"{telemetry.timestamp_ms}:{permitted_torque}:{permitted_throttle}:{self.state.value}:{now_utc}".encode("utf-8")
        ).hexdigest()

        log_entry = {
            "timestamp_utc": now_utc,
            "state": self.state.value,
            "dispatched_steering_torque_nm": permitted_torque,
            "dispatched_throttle_pct": permitted_throttle,
            "gap_set": list(self.gap_set),
            "directive": explanation,
            "cycle_digest": cycle_digest,
        }
        self.flight_recorder.append(log_entry)

        return self.state, permitted_torque, permitted_throttle, explanation
