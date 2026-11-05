"""Unit & Invariant Regression Suite for Android Automotive (AAOS) Tool.

Verifies:
  1. Manifest schema parsing and safety boundaries.
  2. The Stem Android Automotive Bridge under normal and adversarial inputs.
  3. Electric Power Steering (EPS) torque gate fail-closed clamp.
  4. Dual APPS pedal sensor plausibility and ISO 26262 ASIL-D divergence enforcement.
  5. Brake-Throttle Override (BTO) enforcement.
  6. VHAL Interceptor SQLite WAL state ledger persistence and predecessor sealing.
  7. Offline appliance packaging and payload manifest generation.

ZERO PII. FAIL-CLOSED INVARIANT TESTING.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from the_stem.automotive_bridge import (
    AndroidAutomotiveStemBridge,
    AutomotiveActuatorCommand,
    AutomotiveTelemetryFrame,
    AutomotiveState,
    VehiclePropertyId,
)
from os_builder.aaos_vhal_interceptor import AAOSVhalGovernor
from os_builder.aaos_provisioner import assemble_aaos_payload, package_offline_archive


class AAOSAutomotiveToolTests(unittest.TestCase):
    def test_aaos_manifest_contains_required_safety_bounds(self):
        manifest_p = Path(__file__).resolve().parent.parent / "os_builder" / "aaos_manifest.json"
        self.assertTrue(manifest_p.exists())
        data = json.loads(manifest_p.read_text(encoding="utf-8"))
        self.assertEqual(data["target_platform"], "ANDROID_AUTOMOTIVE_OS")
        self.assertTrue(data["air_gap_enforced"])
        self.assertIn(33, data["compatible_api_levels"])
        self.assertIn("arm64-v8a", data["target_architectures"])
        limits = data["safety_invariants"]
        self.assertEqual(limits["eps_max_torque_nm"], 12.0)
        self.assertEqual(limits["fail_closed_torque_clamp_nm"], 0.0)

    def test_nominal_driving_trajectory_remains_assist_active(self):
        bridge = AndroidAutomotiveStemBridge(max_eps_torque_nm=12.0)
        cmd = AutomotiveActuatorCommand("CMD_NOM", target_steering_torque_nm=3.5, target_throttle_percent=20.0, target_brake_percent=0.0)
        telem = AutomotiveTelemetryFrame(
            timestamp_ms=1000,
            vehicle_speed_kph=45.0,
            steering_angle_deg=5.0,
            eps_current_amps=1.89,
            measured_steering_torque_nm=3.48,
            apps_sensor_1_pct=20.0,
            apps_sensor_2_pct=20.1,
            brake_pressure_bar=0.0,
        )
        st, torque, throttle, directive = bridge.evaluate_telemetry_and_actuate(cmd, telem)
        self.assertEqual(st, AutomotiveState.ASSIST_ACTIVE)
        self.assertEqual(torque, 3.5)
        self.assertEqual(throttle, 20.0)
        self.assertEqual(directive, "ALL_AUTOMOTIVE_INVARIANTS_VERIFIED_BOUNDED")

    def test_excessive_eps_torque_trips_to_zero(self):
        bridge = AndroidAutomotiveStemBridge(max_eps_torque_nm=12.0)
        cmd = AutomotiveActuatorCommand("CMD_OVER", target_steering_torque_nm=15.0, target_throttle_percent=20.0, target_brake_percent=0.0)
        telem = AutomotiveTelemetryFrame(
            timestamp_ms=1000,
            vehicle_speed_kph=45.0,
            steering_angle_deg=5.0,
            eps_current_amps=1.89,
            measured_steering_torque_nm=3.48,
            apps_sensor_1_pct=20.0,
            apps_sensor_2_pct=20.0,
            brake_pressure_bar=0.0,
        )
        st, torque, throttle, directive = bridge.evaluate_telemetry_and_actuate(cmd, telem)
        self.assertEqual(st, AutomotiveState.FAIL_CLOSED_CLAMPED)
        self.assertEqual(torque, 0.0)
        self.assertEqual(throttle, 0.0)
        self.assertTrue(bridge.torque_gate.is_tripped)

    def test_apps_pedal_divergence_forces_zero_throttle(self):
        bridge = AndroidAutomotiveStemBridge()
        cmd = AutomotiveActuatorCommand("CMD_APPS", target_steering_torque_nm=2.0, target_throttle_percent=40.0, target_brake_percent=0.0)
        telem = AutomotiveTelemetryFrame(
            timestamp_ms=1000,
            vehicle_speed_kph=45.0,
            steering_angle_deg=0.0,
            eps_current_amps=1.08,
            measured_steering_torque_nm=2.0,
            apps_sensor_1_pct=40.0,
            apps_sensor_2_pct=15.0,  # 25% difference > 5% max
            brake_pressure_bar=0.0,
        )
        st, torque, throttle, directive = bridge.evaluate_telemetry_and_actuate(cmd, telem)
        self.assertEqual(st, AutomotiveState.FAIL_CLOSED_CLAMPED)
        self.assertEqual(throttle, 0.0)
        self.assertIn("APPS_PEDAL_SENSOR_DIVERGENCE", directive)

    def test_brake_throttle_override_zeros_throttle(self):
        bridge = AndroidAutomotiveStemBridge()
        cmd = AutomotiveActuatorCommand("CMD_BTO", target_steering_torque_nm=1.0, target_throttle_percent=50.0, target_brake_percent=0.0)
        telem = AutomotiveTelemetryFrame(
            timestamp_ms=1000,
            vehicle_speed_kph=60.0,
            steering_angle_deg=0.0,
            eps_current_amps=0.54,
            measured_steering_torque_nm=1.0,
            apps_sensor_1_pct=50.0,
            apps_sensor_2_pct=50.0,
            brake_pressure_bar=10.0,  # Brake actively applied
        )
        st, torque, throttle, directive = bridge.evaluate_telemetry_and_actuate(cmd, telem)
        self.assertEqual(throttle, 0.0)
        self.assertIn("BRAKE_THROTTLE_OVERRIDE_ACTIVE", bridge.flight_recorder[-1]["gap_set"])

    def test_vhal_interceptor_persists_sqlite_wal_receipts(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            db_path = Path(tmp_dir) / "vhal_test.db"
            gov = AAOSVhalGovernor(db_path=db_path)
            cmd = AutomotiveActuatorCommand("CMD_VHAL", target_steering_torque_nm=2.0, target_throttle_percent=10.0, target_brake_percent=0.0)
            telem = AutomotiveTelemetryFrame(
                timestamp_ms=1000,
                vehicle_speed_kph=30.0,
                steering_angle_deg=2.0,
                eps_current_amps=1.08,
                measured_steering_torque_nm=2.0,
                apps_sensor_1_pct=10.0,
                apps_sensor_2_pct=10.0,
                brake_pressure_bar=0.0,
            )
            r = gov.process_vhal_cycle(cmd, telem)
            self.assertEqual(r["cycle_index"], 1)
            seal = gov.seal_session()
            self.assertEqual(seal["total_cycles"], 1)
            gov.close()

            # Inspect database directly
            con = sqlite3.connect(str(db_path))
            j_mode = con.execute("PRAGMA journal_mode;").fetchone()[0]
            self.assertEqual(j_mode.lower(), "wal")
            cnt = con.execute("SELECT count(*) FROM vehicle_receipts;").fetchone()[0]
            self.assertEqual(cnt, 1)
            con.close()

    def test_payload_packaging_generates_valid_manifest(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True):
            stage = assemble_aaos_payload()
            self.assertTrue((stage / "the_stem").exists())
            self.assertTrue((stage / "os_builder").exists())
            self.assertTrue((stage / "init.stem.rc").exists())
            self.assertTrue((stage / "run_stem.sh").exists())
            self.assertTrue((stage / "payload_manifest.json").exists())
            man = json.loads((stage / "payload_manifest.json").read_text(encoding="utf-8"))
            self.assertIn("run_stem.sh", man)


if __name__ == "__main__":
    unittest.main()
