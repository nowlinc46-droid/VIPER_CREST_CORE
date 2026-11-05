"""Android Automotive OS (AAOS) Builder & Operator CLI (aaos_cli.py).

Unified CLI interface to detect, package, deploy, audit, and simulate The Stem + ViperCrest
on Android Automotive OS (AAOS) target hardware.

Commands:
  detect     - Scan for connected AAOS head units, IVI boards, or emulators via ADB.
  package    - Assembles signed offline appliance archive (.tar.gz).
  deploy     - Pushes and bootstraps the runtime onto a target Android device.
  preflight  - Executes the full 6-vector automotive safety invariant audit.
  simulate   - Simulates live VHAL cycles with fault injection and fail-closed evaluation.
  status     - Displays system manifest, EPS actuator limits, and SQLite ledger health.

ZERO PII. FAIL-CLOSED ARCHITECTURE.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from os_builder.aaos_provisioner import detect_devices, package_offline_archive, deploy_to_device
from os_builder.aaos_preflight import run_preflight_suite
from os_builder.aaos_vhal_interceptor import AAOSVhalGovernor
from the_stem.automotive_bridge import AutomotiveActuatorCommand, AutomotiveTelemetryFrame


def cmd_detect():
    print("=" * 72)
    print("   ANDROID AUTOMOTIVE (AAOS) HARDWARE DISCOVERY")
    print("=" * 72)
    devs = detect_devices()
    if not devs:
        print("  [INFO] No connected ADB devices found.")
        print("  Tip: Ensure USB debugging is active or launch an AAOS emulator.")
        return 0

    print(f"  Found {len(devs)} attached device(s):")
    for i, d in enumerate(devs, 1):
        car_tag = "[AUTOMOTIVE]" if d["is_automotive"] else "[GENERIC_ANDROID]"
        print(f"  {i}. Serial: {d['serial']:<20} Model: {d['model']:<15} Type: {car_tag}")
        print(f"     Characteristics: {d['characteristics'] or 'default'}")
    print("=" * 72)
    return 0


def cmd_package():
    print("=" * 72)
    print("   ASSEMBLING ANDROID AUTOMOTIVE OS APPLIANCE BUNDLE")
    print("=" * 72)
    tar_path = package_offline_archive()
    size_kb = tar_path.stat().st_size / 1024
    print(f"  [SUCCESS] Appliance archive generated:")
    print(f"  Path : {tar_path}")
    print(f"  Size : {size_kb:.2f} KB")
    print("=" * 72)
    return 0


def cmd_deploy(args):
    print("=" * 72)
    print("   DEPLOYING SOVEREIGN STEM + VIPERCREST RUNTIME TO AAOS DEVICE")
    print("=" * 72)
    ok = deploy_to_device(serial=args.serial)
    return 0 if ok else 1


def cmd_preflight():
    return run_preflight_suite(verbose=True)


def cmd_simulate(args):
    print("=" * 72)
    print("   RUNNING ANDROID AUTOMOTIVE VHAL SIMULATION & INJECTION")
    print("=" * 72)
    db_p = PROJECT_ROOT / "runtime" / "sim_aaos_state.db"
    gov = AAOSVhalGovernor(db_path=db_p, device_id="SIMULATED_AAOS_COCKPIT")

    print(f"  Execution Run ID : {gov.run_id}")
    print(f"  Target Device    : {gov.device_id}")
    print("-" * 72)

    scenarios = [
        ("Nominal Highway Cruise", 3.0, 25.0, 25.0, 25.1, 1.62, 3.0, 0.0),
        ("High Speed Curve Assist", 6.0, 35.0, 35.0, 35.2, 3.24, 6.0, 0.0),
        ("Pedal Divergence Injection", 3.0, 40.0, 40.0, 15.0, 1.62, 3.0, 0.0),  # Injects fault
        ("Over-Torque Hijack Attempt", 18.0, 20.0, 20.0, 20.0, 9.72, 18.0, 0.0), # Injects over-torque
        ("Driver Emergency Braking", 0.0, 50.0, 50.0, 50.0, 0.0, 0.0, 15.0),    # BTO priority
    ]

    for name, req_t, req_th, ap1, ap2, curr, meas_t, brk in scenarios:
        cmd = AutomotiveActuatorCommand("SIM_CMD", target_steering_torque_nm=req_t, target_throttle_percent=req_th, target_brake_percent=0.0)
        telem = AutomotiveTelemetryFrame(
            timestamp_ms=int(time.time() * 1000),
            vehicle_speed_kph=80.0,
            steering_angle_deg=5.0,
            eps_current_amps=curr,
            measured_steering_torque_nm=meas_t,
            apps_sensor_1_pct=ap1,
            apps_sensor_2_pct=ap2,
            brake_pressure_bar=brk,
        )
        res = gov.process_vhal_cycle(cmd, telem)
        state_tag = f"[{res['state']}]"
        print(f"  Scenario: {name:<30} -> {state_tag:<22} Dispatched: {res['dispatched_steering_torque_nm']:.1f} Nm | {res['dispatched_throttle_pct']:.1f}%")
        if res["state"] == "FAIL_CLOSED_CLAMPED":
            print(f"    Notice: {res['directive']}")

    seal = gov.seal_session()
    gov.close()
    print("-" * 72)
    print(f"  Simulation Completed. Total Cycles: {seal['total_cycles']} | Tripped Cycles: {seal['tripped_cycles']}")
    print(f"  Ledger Sealed Hash: {seal['sealed_digest'][:24]}...")
    print("=" * 72)
    return 0


def cmd_status():
    manifest_p = PROJECT_ROOT / "os_builder" / "aaos_manifest.json"
    print("=" * 72)
    print("   ANDROID AUTOMOTIVE (AAOS) SYSTEM STATUS & CONFIGURATION")
    print("=" * 72)
    if manifest_p.exists():
        data = json.loads(manifest_p.read_text(encoding="utf-8"))
        print(f"  System Identifier    : {data.get('system_identifier')}")
        print(f"  Target Platform      : {data.get('target_platform')}")
        print(f"  Air-Gap Enforced     : {data.get('air_gap_enforced')}")
        print(f"  Device Staging Path  : {data.get('device_staging_path')}")
        print(f"  Supported Architectures: {', '.join(data.get('target_architectures', []))}")
        limits = data.get("safety_invariants", {})
        print(f"  Max EPS Torque       : {limits.get('eps_max_torque_nm')} Nm")
        print(f"  Max APPS Divergence  : {limits.get('max_apps_pedal_divergence_pct')} %")
        print(f"  Fail-Closed Torque   : {limits.get('fail_closed_torque_clamp_nm')} Nm")
    else:
        print("  [WARN] Manifest file not found.")
    print("=" * 72)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Android Automotive (AAOS) Stem + ViperCrest Tool")
    sub = parser.add_subparsers(dest="command", help="Operational mode")

    sub.add_parser("detect", help="Scan for connected Android Automotive devices via ADB")
    sub.add_parser("package", help="Assemble offline appliance bundle (.tar.gz)")
    
    dep = sub.add_parser("deploy", help="Deploy runtime payload to Android device")
    dep.add_argument("--serial", type=str, default=None, help="Specific device serial number")

    sub.add_parser("preflight", help="Execute 6-vector safety invariant regression audit")
    sub.add_parser("audit", help="Alias for preflight")
    sub.add_parser("simulate", help="Run VHAL cycle simulation with fault injections")
    sub.add_parser("status", help="Inspect system manifest and actuator safety limits")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "detect":
        return cmd_detect()
    elif args.command == "package":
        return cmd_package()
    elif args.command == "deploy":
        return cmd_deploy(args)
    elif args.command in ("preflight", "audit"):
        return cmd_preflight()
    elif args.command == "simulate":
        return cmd_simulate(args)
    elif args.command == "status":
        return cmd_status()
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
