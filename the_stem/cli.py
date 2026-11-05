"""The Stem: Standalone Brainstem Governor CLI (the_stem/cli.py).

Provides live, operational execution of The Stem brainstem engine.
Positioned between high-level neural planners and physical actuators to enforce:
  G(S) != empty => Involuntary Fail-Closed Suspension (0.0 Nm Actuator Torque)

Operating Modes:
  - Interactive Live REPL : Live command line controlling joint states and testing sensor faults.
  - One-Shot Actuate      : Evaluates a single real-time sensor/actuation cycle.
  - Stream                : Ingests and governs a continuous stream of sensor frames.
  - Status                : Inspects hardware limits, motor ID, and torque gate state.
"""
from __future__ import annotations

import argparse
import json
try:
    import readline  # type: ignore
except ImportError:
    readline = None  # type: ignore
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stem_governor import StemGovernor, ActuationCommand, GovernorState
from .sensor_bridge import SensorReading
from .kinetic_gate import TorqueLimitConfig


def cmd_status(gov: Optional[StemGovernor] = None):
    """Displays live operational status of the brainstem governor."""
    g = gov or StemGovernor()
    print("=" * 68)
    print("      THE STEM - DETERMINISTIC EPISTEMIC BRAINSTEM GOVERNOR")
    print("=" * 68)
    print(f"  Target Motor ID       : {g.motor_id}")
    print(f"  Current State         : {g.state.value}")
    print(f"  Torque Gate Status    : {'TRIPPED' if g.torque_gate.is_tripped else 'ARMED_HEALTHY'}")
    print(f"  Max Torque Limit      : {g.torque_gate.config.max_torque_nm:.1f} Nm")
    print(f"  Max Current Limit     : {g.torque_gate.config.max_current_amps:.1f} A")
    print(f"  Torque Constant (Kt)  : {g.torque_gate.config.torque_constant_kt:.2f} Nm/A")
    print(f"  Tolerance Margin      : {g.torque_gate.config.tolerance_margin_percent * 100:.1f} %")
    print(f"  Trip Status           : {g.torque_gate.trip_reason or 'None (Clean)'}")
    print(f"  Flight Log Entries    : {len(g.flight_recorder)}")
    print(f"  Fail-Closed Invariant : G(S) != empty => Dispatched Torque = 0.0 Nm")
    print("=" * 68)


def evaluate_single_tick(
    gov: StemGovernor,
    joint_id: str = "ACTUATOR_SHOULDER_01",
    target_torque_nm: float = 25.0,
    target_velocity_rad_s: float = 1.2,
    optical_val: float = 1.0,
    optical_var: float = 0.05,
    encoder_val: float = 0.45,
    encoder_var: float = 0.01,
    measured_current_amps: Optional[float] = None,
    measured_torque_sensor_nm: Optional[float] = None,
    pos_rad: float = 0.45,
    vel_rad_s: float = 1.2,
    acc_rad_s2: float = 2.1,
    planner: str = "CORTEX_TRAJECTORY_PLANNER",
) -> Dict[str, Any]:
    """Executes a single live cycle through The Stem."""
    # Default electrical current calculation: I = tau / K_t (K_t ~= 2.28 Nm/A)
    curr = measured_current_amps if measured_current_amps is not None else (target_torque_nm / 2.28)
    torq_meas = measured_torque_sensor_nm if measured_torque_sensor_nm is not None else (target_torque_nm * 0.99)

    cmd = ActuationCommand(
        joint_id=joint_id,
        target_torque_nm=target_torque_nm,
        target_velocity_rad_s=target_velocity_rad_s,
        max_duration_ms=50,
        source_planner=planner,
    )
    opt = SensorReading("CAM_01", "OPTICAL", value=optical_val, variance=optical_var, timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000))
    enc = SensorReading("ENC_01", "ENCODER", value=encoder_val, variance=encoder_var, timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000))

    state, dispatched_torque, msg = gov.evaluate_cycle(
        command=cmd,
        optical_reading=opt,
        encoder_reading=enc,
        measured_current_amps=curr,
        measured_torque_sensor_nm=torq_meas,
        pos_rad=pos_rad,
        vel_rad_s=vel_rad_s,
        acc_rad_s2=acc_rad_s2,
    )

    last_record = gov.flight_recorder[-1] if gov.flight_recorder else {}
    return {
        "joint_id": joint_id,
        "commanded_torque_nm": target_torque_nm,
        "dispatched_torque_nm": dispatched_torque,
        "state": state.value,
        "gate_tripped": gov.torque_gate.is_tripped,
        "explanation": msg,
        "gaps": list(gov.gap_set),
        "digest": last_record.get("record_digest", "N/A"),
    }


def print_tick_result(res: Dict[str, Any]):
    """Pretty prints a cycle evaluation result."""
    print("-" * 68)
    print(f" [CYCLE EVALUATION] Joint: {res['joint_id']}")
    print(f"  Commanded Torque  : {res['commanded_torque_nm']:.2f} Nm")
    print(f"  Dispatched Torque : {res['dispatched_torque_nm']:.2f} Nm  "
          f"{'-> [ACTUATION PERMITTED]' if res['dispatched_torque_nm'] > 0 else '-> [LOCKED FAIL-CLOSED 0.0 Nm]'}")
    print(f"  Governor State    : {res['state']}")
    print(f"  Gate Tripped      : {'YES (EMERGENCY HALT)' if res['gate_tripped'] else 'NO (HEALTHY)'}")
    print(f"  Diagnosis         : {res['explanation']}")
    if res["gaps"]:
        print(f"  Active Gaps       : {res['gaps']}")
    print(f"  Cryptographic Log : {res['digest']}")
    print("-" * 68)


def cmd_interactive():
    """Runs the live interactive Brainstem Governor REPL."""
    gov = StemGovernor()
    print("=" * 68)
    print("      THE STEM - DETERMINISTIC EPISTEMIC BRAINSTEM [LIVE REPL]")
    print("=" * 68)
    print("  Positioned between Neural Planners and Motor Drivers.")
    print("  Type 'help' for commands, or send live actuation cycles.\n")

    while True:
        try:
            prompt = f"STEM [{gov.state.value}]> "
            line = input(prompt).strip()
            if not line:
                continue

            lowered = line.lower()
            if lowered in {"exit", "quit", "q"}:
                print("Exiting The Stem Governor.")
                break
            elif lowered in {"help", "?"}:
                print("\nCommands:")
                print("  actuate [torque=25.0] [opt=1.0] [enc=0.45] [curr=10.96] : Dispatch motor command")
                print("  blind-optical                                           : Simulate optical sensor blackout")
                print("  blind-encoder                                           : Simulate encoder flatline/freeze")
                print("  surge                                                   : Simulate electrical overcurrent surge")
                print("  overspeed                                               : Simulate plant acceleration violation")
                print("  nominal                                                 : Send nominal clean cycle (25 Nm)")
                print("  status                                                  : Display live hardware status")
                print("  reset                                                   : Reset tripped torque gate")
                print("  log                                                     : View flight recorder logs")
                print("  exit                                                    : Exit REPL\n")
                continue
            elif lowered == "status":
                cmd_status(gov)
                continue
            elif lowered == "reset":
                gov.torque_gate.is_tripped = False
                gov.state = GovernorState.IDLE
                gov.gap_set.clear()
                print("[RESET] Torque gate cleared. Governor returned to IDLE.")
                continue
            elif lowered == "log":
                print(f"\nFlight Recorder ({len(gov.flight_recorder)} entries):")
                for i, r in enumerate(gov.flight_recorder[-5:], 1):
                    print(f"  [{i}] {r['timestamp']} | Event: {r['event']} | Digest: {r['record_digest'][:16]}...")
                print()
                continue
            elif lowered == "blind-optical":
                res = evaluate_single_tick(gov, optical_val=0.0, optical_var=0.0)
                print_tick_result(res)
                continue
            elif lowered == "blind-encoder":
                res = evaluate_single_tick(gov, encoder_val=0.0, encoder_var=0.0)
                print_tick_result(res)
                continue
            elif lowered == "surge":
                res = evaluate_single_tick(gov, measured_current_amps=95.0)
                print_tick_result(res)
                continue
            elif lowered == "overspeed":
                res = evaluate_single_tick(gov, acc_rad_s2=85.0)
                print_tick_result(res)
                continue
            elif lowered == "nominal":
                res = evaluate_single_tick(gov)
                print_tick_result(res)
                continue

            # Parse key=value arguments for actuate
            tokens = shlex.split(line)
            cmd_name = tokens[0].lower()
            if cmd_name in {"actuate", "tick", "run", "cycle"}:
                kwargs: Dict[str, Any] = {}
                for tok in tokens[1:]:
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        k = k.strip().lower()
                        v = v.strip()
                        if k in {"torque", "tau", "t"}:
                            kwargs["target_torque_nm"] = float(v)
                        elif k in {"vel", "velocity", "v"}:
                            kwargs["target_velocity_rad_s"] = float(v)
                        elif k in {"opt", "optical"}:
                            kwargs["optical_val"] = float(v)
                        elif k in {"opt_var", "optical_var"}:
                            kwargs["optical_var"] = float(v)
                        elif k in {"enc", "encoder"}:
                            kwargs["encoder_val"] = float(v)
                        elif k in {"enc_var", "encoder_var"}:
                            kwargs["encoder_var"] = float(v)
                        elif k in {"curr", "current", "i"}:
                            kwargs["measured_current_amps"] = float(v)
                        elif k in {"acc", "accel"}:
                            kwargs["acc_rad_s2"] = float(v)
                        elif k in {"joint", "id"}:
                            kwargs["joint_id"] = v
                res = evaluate_single_tick(gov, **kwargs)
                print_tick_result(res)
            else:
                print(f"Unknown command '{line}'. Type 'help' for available commands.")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting The Stem Governor.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")


def cmd_stream(filepath: str):
    """Ingests and evaluates a continuous telemetry file (JSON array)."""
    p = Path(filepath)
    if not p.exists():
        print(f"[ERROR] Telemetry file not found: {filepath}")
        return 1

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = [data]
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON stream: {e}")
        return 1

    gov = StemGovernor()
    print(f"Running stream evaluation on {len(data)} telemetry frames from {p.name}...\n")
    for i, frame in enumerate(data, 1):
        res = evaluate_single_tick(
            gov=gov,
            joint_id=frame.get("joint_id", "ACTUATOR_SHOULDER_01"),
            target_torque_nm=float(frame.get("target_torque_nm", 25.0)),
            target_velocity_rad_s=float(frame.get("target_velocity_rad_s", 1.2)),
            optical_val=float(frame.get("optical_val", 1.0)),
            optical_var=float(frame.get("optical_var", 0.05)),
            encoder_val=float(frame.get("encoder_val", 0.45)),
            encoder_var=float(frame.get("encoder_var", 0.01)),
            measured_current_amps=frame.get("measured_current_amps"),
            pos_rad=float(frame.get("pos_rad", 0.45)),
            vel_rad_s=float(frame.get("vel_rad_s", 1.2)),
            acc_rad_s2=float(frame.get("acc_rad_s2", 2.1)),
        )
        print(f"Frame {i:03d}: State={res['state']:<14} Dispatched={res['dispatched_torque_nm']:>5.1f} Nm | Gate={'TRIP' if res['gate_tripped'] else 'OK':<4} | Digest={res['digest'][:16]}...")
    print(f"\nStream complete: {len(data)} frames processed. All transitions recorded.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="The Stem: Live Autonomous Brainstem Governor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Operational Subcommands")

    # status
    subparsers.add_parser("status", help="Display governor operational status & limits")

    # actuate
    p_act = subparsers.add_parser("actuate", help="Execute single live cycle evaluation")
    p_act.add_argument("--torque", type=float, default=25.0, help="Commanded torque (Nm)")
    p_act.add_argument("--velocity", type=float, default=1.2, help="Commanded velocity (rad/s)")
    p_act.add_argument("--optical", type=float, default=1.0, help="Optical sensor reading")
    p_act.add_argument("--optical-var", type=float, default=0.05, help="Optical sensor variance")
    p_act.add_argument("--encoder", type=float, default=0.45, help="Encoder reading (rad)")
    p_act.add_argument("--encoder-var", type=float, default=0.01, help="Encoder variance")
    p_act.add_argument("--current", type=float, default=None, help="Measured current (Amps)")
    p_act.add_argument("--acc", type=float, default=2.1, help="Measured acceleration (rad/s2)")
    p_act.add_argument("--joint", type=str, default="ACTUATOR_SHOULDER_01", help="Joint ID")

    # interactive
    subparsers.add_parser("interactive", help="Launch live interactive governor REPL")

    # stream
    p_stream = subparsers.add_parser("stream", help="Stream and evaluate telemetry file")
    p_stream.add_argument("file", help="Path to JSON telemetry file")

    # verify
    subparsers.add_parser("verify", help="Run 8-pillar stem verification tests")

    # demo (preserved for reference, but not default)
    subparsers.add_parser("demo", help="Run quick 2-cycle verification demo")

    args = parser.parse_args()

    if args.command is None or args.command == "interactive":
        cmd_interactive()
    elif args.command == "status":
        cmd_status()
    elif args.command == "actuate":
        gov = StemGovernor(motor_id=args.joint)
        res = evaluate_single_tick(
            gov=gov,
            joint_id=args.joint,
            target_torque_nm=args.torque,
            target_velocity_rad_s=args.velocity,
            optical_val=args.optical,
            optical_var=args.optical_var,
            encoder_val=args.encoder,
            encoder_var=args.encoder_var,
            measured_current_amps=args.current,
            acc_rad_s2=args.acc,
        )
        print_tick_result(res)
    elif args.command == "stream":
        sys.exit(cmd_stream(args.file))
    elif args.command == "verify":
        from .verify_stem import run_stem_verification
        sys.exit(run_stem_verification())
    elif args.command == "demo":
        gov = StemGovernor()
        print("[NOMINAL CYCLE]")
        print_tick_result(evaluate_single_tick(gov))
        print("[BLINDED SENSOR ATTACK]")
        print_tick_result(evaluate_single_tick(gov, optical_val=0.0, optical_var=0.0))


if __name__ == "__main__":
    main()
