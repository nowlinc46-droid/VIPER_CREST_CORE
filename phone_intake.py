"""
Phone & USB Device Data Intake Engine (Stage F1 Ground-Truth Ingestion).
Extracts diagnostic dumps, system logs, app databases, and telemetry from connected
phones (via ADB or USB storage) or synthetic device profiles, staging them into
`runtime/dropzone/` and evaluating them through the ViperCrest F1-F9 matrix engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from viper_core import (
    DROPZONE,
    FIXTURES,
    STATE_DB,
    ensure_state_db,
    ingest_dropzone,
)

VIPER_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)


def detect_connected_devices() -> list[dict[str, str]]:
    """Detect connected Android devices via ADB if available."""
    devices = []
    adb_bin = shutil.which("adb")
    if not adb_bin:
        default_adb = Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
        if default_adb.exists():
            adb_bin = str(default_adb)

    if adb_bin:
        try:
            res = subprocess.run([adb_bin, "devices", "-l"], capture_output=True, text=True, timeout=5)
            for line in res.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] != "offline":
                    dev_id = parts[0]
                    model = "unknown"
                    for part in parts[2:]:
                        if part.startswith("model:"):
                            model = part.split(":", 1)[1]
                    devices.append({"id": dev_id, "model": model, "transport": "adb"})
        except Exception:
            pass
    return devices


def generate_synthetic_device_dump(device_id: str = "PIXEL_8A_USB_SIM", scenario: str = "security_anomaly") -> dict[str, Any]:
    """Generate structured ground-truth telemetry dump from a phone/USB device."""
    now_iso = datetime.now(timezone.utc).isoformat()
    
    if scenario == "security_anomaly":
        baseline = {
            "device_id": device_id,
            "os_build": "UP1A.231005.007",
            "security_patch": "2026-10-01",
            "selinux_mode": "Enforcing",
            "root_access": False,
            "usb_debugging": True,
            "suspicious_processes": [],
            "open_ports": [443, 8443],
            "app_permissions": {
                "com.secure.vault": ["CAMERA", "BIOMETRIC"],
                "com.android.shell": [],
            },
        }
        candidate = {
            "device_id": device_id,
            "os_build": "UP1A.231005.007",
            "security_patch": "2026-10-01",
            "selinux_mode": "Permissive",
            "root_access": True,
            "usb_debugging": True,
            "suspicious_processes": ["/data/local/tmp/frida-server", "/system/bin/su"],
            "open_ports": [443, 8443, 27042],
            "app_permissions": {
                "com.secure.vault": ["CAMERA", "BIOMETRIC", "READ_EXTERNAL_STORAGE"],
                "com.android.shell": ["SYSTEM_ALERT_WINDOW", "BIND_ACCESSIBILITY_SERVICE"],
            },
        }
    elif scenario == "app_db_audit":
        baseline = {
            "database": "accounts.db",
            "schema_version": 4,
            "record_count": 1250,
            "integrity_check": "ok",
            "unencrypted_pii_rows": 0,
            "foreign_key_violations": 0,
        }
        candidate = {
            "database": "accounts.db",
            "schema_version": 4,
            "record_count": 1285,
            "integrity_check": "ok",
            "unencrypted_pii_rows": 35,
            "foreign_key_violations": 2,
        }
    else:  # standard telemetry
        baseline = {
            "device_id": device_id,
            "battery_level": 95,
            "storage_free_mb": 45200,
            "network_state": "WIFI_CONNECTED",
            "failed_login_attempts": 0,
        }
        candidate = {
            "device_id": device_id,
            "battery_level": 92,
            "storage_free_mb": 45150,
            "network_state": "WIFI_CONNECTED",
            "failed_login_attempts": 0,
        }

    return {
        "observations": [
            {
                "id": f"phone-telemetry-{scenario}",
                "baseline": baseline,
                "candidate": candidate,
                "provenance": {
                    "source": "USB_INTAKE",
                    "device_id": device_id,
                    "extracted_at": now_iso,
                    "intake_protocol": "ViperCrest_F1_Dropzone",
                },
            }
        ]
    }


def extract_from_adb(device_id: str) -> dict[str, Any]:
    """Extract real device state from an ADB-connected device."""
    adb_bin = shutil.which("adb") or "adb"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    def run_cmd(cmd_list: list[str]) -> str:
        try:
            r = subprocess.run([adb_bin, "-s", device_id] + cmd_list, capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception as e:
            return f"error: {e}"

    build = run_cmd(["shell", "getprop", "ro.build.display.id"])
    selinux = run_cmd(["shell", "getenforce"])
    procs = run_cmd(["shell", "ps", "-A"])
    
    proc_lines = [p.split()[-1] for p in procs.splitlines() if p.strip()]

    return {
        "observations": [
            {
                "id": f"adb-device-live-{device_id}",
                "baseline": {
                    "device_id": device_id,
                    "os_build": build,
                    "selinux_mode": "Enforcing",
                    "suspicious_processes": [],
                },
                "candidate": {
                    "device_id": device_id,
                    "os_build": build,
                    "selinux_mode": selinux,
                    "suspicious_processes": [p for p in proc_lines if any(k in p.lower() for k in ("frida", "magisk", "su", "xposed"))],
                },
                "provenance": {
                    "source": "ADB_LIVE_EXTRACTION",
                    "device_id": device_id,
                    "extracted_at": now_iso,
                    "intake_protocol": "ViperCrest_F1_Dropzone",
                },
            }
        ]
    }


def stage_to_dropzone(payload: dict[str, Any], filename: str = "phone_intake_dump.json") -> Path:
    """Stage normalized observation payload into runtime/dropzone/."""
    DROPZONE.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".json"):
        filename += ".json"
    target = DROPZONE / filename
    raw = json.dumps(payload, indent=2).encode("utf-8")
    target.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    print(f"[INTAKE] Staged to dropzone: {target} (SHA256: {sha[:16]}...)")
    return target


def process_intake_and_evaluate(staged_path: Path) -> int:
    """Execute F1 dropzone intake, clean staging file, and trigger F1-F9 matrix sweep."""
    ensure_state_db(STATE_DB)
    print("[INTAKE] Triggering Stage F1 Ground-Truth Ledger Ingestion...")
    ingested = ingest_dropzone(STATE_DB)
    print(f"[INTAKE] Successfully ingested into state ledger: {ingested}")
    
    fixture_filename = staged_path.name
    # Unlink dropzone staging file now that it has been ingested and anchored in fixtures/ledger
    staged_path.unlink(missing_ok=True)
    
    fixture_path = FIXTURES / fixture_filename
    if not fixture_path.exists():
        print(f"[INTAKE] Error: Ingested fixture missing at {fixture_path}")
        return 1

    cmd = [str(PYTHON_EXE), "-B", str(VIPER_ROOT / "viper.py"), "matrix", "--target", str(fixture_path)]
    print(f"[INTAKE] Executing F1-F9 Matrix Engine: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ViperCrest Phone & USB Data Intake Pipeline (F1 Intake)")
    parser.add_argument("--simulate", action="store_true", help="Run simulated phone extraction")
    parser.add_argument(
        "--scenario",
        choices=["security_anomaly", "app_db_audit", "telemetry"],
        default="security_anomaly",
        help="Simulation scenario profile",
    )
    parser.add_argument("--device-id", default="PIXEL_8A_USB", help="Target device identifier")
    parser.add_argument("--output-name", default=None, help="Optional custom dropzone file name")
    parser.add_argument("--no-eval", action="store_true", help="Stage to dropzone and ingest only, skip matrix evaluation")
    args = parser.parse_args(argv)

    devices = detect_connected_devices()
    if devices and not args.simulate:
        target_dev = devices[0]["id"]
        print(f"[INTAKE] Detected live connected device: {target_dev} ({devices[0].get('model', 'device')})")
        payload = extract_from_adb(target_dev)
        default_name = f"phone_intake_live_{target_dev}_{int(time.time())}.json"
    else:
        if not args.simulate:
            print("[INTAKE] No live ADB device detected on USB bus. Operating in simulation mode...")
        else:
            print(f"[INTAKE] Executing simulation scenario: {args.scenario} for device {args.device_id}")
        payload = generate_synthetic_device_dump(device_id=args.device_id, scenario=args.scenario)
        default_name = f"phone_intake_{args.scenario}_{int(time.time())}.json"

    filename = args.output_name if args.output_name else default_name
    staged_path = stage_to_dropzone(payload, filename)
    
    if args.no_eval:
        ingested = ingest_dropzone(STATE_DB)
        staged_path.unlink(missing_ok=True)
        print(f"[INTAKE] Ingested without matrix evaluation: {ingested}")
        return 0

    return process_intake_and_evaluate(staged_path)


if __name__ == "__main__":
    sys.exit(main())
