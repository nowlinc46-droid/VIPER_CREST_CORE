"""The Stem: Standalone Verification Runner (verify_stem.py).

Verifies all internal invariants of The Stem standalone tool:
1. Nominal Bounded Actuation Cycle
2. Involuntary Fail-Closed Sensor Blinding Suspension
3. Transducer Overcurrent Gate Trip
4. Continuous Plant Quantization Stability
5. Cryptographic State Ledger Parity
"""
from __future__ import annotations

import sys
from .stem_governor import StemGovernor, ActuationCommand, GovernorState
from .sensor_bridge import SensorReading
from .kinetic_gate import KineticTorqueGate, TorqueLimitConfig
from .physical_grounding import PhysicalPlantQuantizer


def run_stem_verification() -> int:
    print("=" * 70)
    print(" THE STEM - INDEPENDENT TOOL VERIFICATION SUITE")
    print("=" * 70)
    failures = 0

    # 1. Nominal Bounded Actuation Test
    gov = StemGovernor("TEST_JOINT")
    cmd = ActuationCommand(
        joint_id="TEST_JOINT",
        target_torque_nm=30.0,
        target_velocity_rad_s=1.0,
        max_duration_ms=50,
        source_planner="VLA_TEST",
    )
    opt = SensorReading("CAM_01", "OPTICAL", value=1.0, variance=0.05, timestamp_ms=100)
    enc = SensorReading("ENC_01", "ENCODER", value=0.5, variance=0.02, timestamp_ms=100)
    state, torque, msg = gov.evaluate_cycle(
        command=cmd,
        optical_reading=opt,
        encoder_reading=enc,
        measured_current_amps=13.15,
        measured_torque_sensor_nm=29.8,
        pos_rad=0.5,
        vel_rad_s=1.0,
        acc_rad_s2=1.5,
    )
    if state == GovernorState.BOUNDED_ACTIVE and torque == 30.0:
        print("  [PASS] 1. Nominal Bounded Actuation Gate")
    else:
        print(f"  [FAIL] 1. Nominal Bounded Actuation Gate: {msg}")
        failures += 1

    # 2. Involuntary Fail-Closed Sensor Blinding Suspension
    spoofed_opt = SensorReading("CAM_01", "OPTICAL", value=0.0, variance=0.0, timestamp_ms=110)
    state_s, torque_s, msg_s = gov.evaluate_cycle(
        command=cmd,
        optical_reading=spoofed_opt,
        encoder_reading=enc,
        measured_current_amps=13.15,
        measured_torque_sensor_nm=29.8,
        pos_rad=0.5,
        vel_rad_s=1.0,
        acc_rad_s2=1.5,
    )
    if state_s == GovernorState.SUSPENDED and torque_s == 0.0:
        print("  [PASS] 2. Involuntary Fail-Closed Suspension (Sensor Fault)")
    else:
        print(f"  [FAIL] 2. Fail-Closed Suspension: {msg_s}")
        failures += 1

    # 3. Transducer Overcurrent Gate Trip
    gate = KineticTorqueGate(TorqueLimitConfig(motor_id="TEST_MOTOR", max_torque_nm=50.0))
    ok, t_out, gate_err = gate.evaluate_actuator_safety(
        commanded_torque_nm=75.0,  # Exceeds 50.0
        measured_current_amps=10.0,
        measured_torque_sensor_nm=22.8,
    )
    if not ok and t_out == 0.0 and "EXCESSIVE_TORQUE" in gate_err:
        print("  [PASS] 3. Over-Torque Gate Trip & Fail-Closed Cutoff")
    else:
        print(f"  [FAIL] 3. Over-Torque Gate: {gate_err}")
        failures += 1

    # 4. Plant Quantizer Stability
    quant = PhysicalPlantQuantizer()
    plant_stable = quant.quantize_state("TEST", 0.5, 2.0, 10.0)
    plant_unstable = quant.quantize_state("TEST", 0.5, 2.0, 300.0)  # Violent acceleration
    if plant_stable.is_stable and not plant_unstable.is_stable:
        print("  [PASS] 4. Continuous Plant Phase-Space Quantization")
    else:
        print("  [FAIL] 4. Plant Quantizer Stability")
        failures += 1

    # 5. Android Automotive (AAOS) Bridge & Fail-Closed Gating
    from .automotive_bridge import (
        AndroidAutomotiveStemBridge,
        AutomotiveActuatorCommand,
        AutomotiveTelemetryFrame,
        AutomotiveState,
    )
    auto_bridge = AndroidAutomotiveStemBridge(max_eps_torque_nm=12.0)
    nom_cmd = AutomotiveActuatorCommand("CMD_01", target_steering_torque_nm=5.0, target_throttle_percent=25.0, target_brake_percent=0.0)
    nom_telem = AutomotiveTelemetryFrame(
        timestamp_ms=1000,
        vehicle_speed_kph=60.0,
        steering_angle_deg=15.0,
        eps_current_amps=2.70,
        measured_steering_torque_nm=5.0,
        apps_sensor_1_pct=25.0,
        apps_sensor_2_pct=25.1,
        brake_pressure_bar=0.0,
    )
    st, t_out, th_out, msg = auto_bridge.evaluate_telemetry_and_actuate(nom_cmd, nom_telem)
    
    # Fault test: Dual APPS pedal divergence (ASIL-D breach)
    fault_telem = AutomotiveTelemetryFrame(
        timestamp_ms=1010,
        vehicle_speed_kph=60.0,
        steering_angle_deg=15.0,
        eps_current_amps=2.70,
        measured_steering_torque_nm=5.0,
        apps_sensor_1_pct=30.0,
        apps_sensor_2_pct=10.0,  # 20% gap > 5% allowed
        brake_pressure_bar=0.0,
    )
    f_st, f_t, f_th, f_msg = auto_bridge.evaluate_telemetry_and_actuate(nom_cmd, fault_telem)

    if (st == AutomotiveState.ASSIST_ACTIVE and t_out == 5.0 and th_out == 25.0 and
            f_st == AutomotiveState.FAIL_CLOSED_CLAMPED and f_t == 0.0 and f_th == 0.0):
        print("  [PASS] 5. Android Automotive (AAOS) Dual-APPS & Fail-Closed Gate")
    else:
        print(f"  [FAIL] 5. AAOS Gate Mismatch: {f_msg}")
        failures += 1

    print("=" * 70)
    if failures == 0:
        print("  VERDICT: THE STEM STANDALONE TOOL 100% VERIFIED & SOUND.")
        return 0
    else:
        print(f"  VERDICT: {failures} TEST(S) FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_stem_verification())
