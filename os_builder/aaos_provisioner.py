"""Android Automotive OS (AAOS) Provisioner & Deployer (aaos_provisioner.py).

Packages and provisions The Stem + ViperCrest sovereign execution engine
onto connected Android Automotive head units, IVI boards, or emulators via ADB/Fastboot.

Features:
  1. Automated AAOS Device Discovery (via ADB property inspection)
  2. Cryptographic Payload Assembly (the_stem + interceptor + SQLite ledger config)
  3. init.stem.rc Android Service Configuration Generator
  4. Push & Staging into secure device directory (/data/local/tmp/viper_stem)
  5. Standalone Offline Appliance Export (.tar.gz / .zip)

ZERO PII. FAIL-CLOSED ARCHITECTURE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = PROJECT_ROOT / "runtime" / "aaos_staging"
OUTPUT_DIR = PROJECT_ROOT / "runtime" / "aaos_packages"


def find_adb() -> Optional[str]:
    """Finds adb executable in PATH or WinGet/Android SDK directories."""
    cand = shutil.which("adb")
    if cand:
        return cand
    sdk_adb = Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    if sdk_adb.exists():
        return str(sdk_adb)
    winget_cand = list((Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages").glob("**/adb.exe"))
    if winget_cand:
        return str(winget_cand[0])
    return None


def detect_devices() -> List[Dict[str, Any]]:
    """Detects connected Android devices and inspects characteristics."""
    adb = find_adb()
    if not adb:
        return []

    devices = []
    try:
        res = subprocess.run([adb, "devices", "-l"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] != "offline":
                dev_id = parts[0]
                model = "unknown"
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1]
                
                # Query device characteristics via getprop
                prop_res = subprocess.run(
                    [adb, "-s", dev_id, "shell", "getprop", "ro.build.characteristics"],
                    capture_output=True, text=True, timeout=5
                )
                chars = prop_res.stdout.strip()
                is_automotive = "automotive" in chars or "car" in chars

                devices.append({
                    "serial": dev_id,
                    "model": model,
                    "characteristics": chars,
                    "is_automotive": is_automotive,
                })
    except Exception as e:
        print(f"[WARN] Error scanning ADB devices: {e}", file=sys.stderr)

    return devices


def generate_init_rc() -> str:
    """Generates an Android init.rc service configuration for The Stem governor."""
    return """# Android Automotive init.stem.rc
# Sovereign Epistemic Brainstem Service for Vehicle HAL Gating
service stem_governor /system/bin/sh /data/local/tmp/viper_stem/run_stem.sh
    class main
    user root
    group root system inet
    seclabel u:r:su:s0
    priority -20
    writepid /dev/cpuset/foreground/tasks
    onrestart restart car-service
"""


def generate_device_runner_sh() -> str:
    """Generates the POSIX shell bootstrap script executed on the Android device."""
    return """#!/system/bin/sh
# The Stem: AAOS Runtime Bootstrap
export STEM_ROOT=/data/local/tmp/viper_stem
export PYTHONPATH=$STEM_ROOT:$PYTHONPATH
cd $STEM_ROOT

echo "[STEM] Starting Android Automotive Sovereign Governor..."
if command -v python3 >/dev/null 2>&1; then
    exec python3 -B -m os_builder.aaos_vhal_interceptor "$@"
elif command -v python >/dev/null 2>&1; then
    exec python -B -m os_builder.aaos_vhal_interceptor "$@"
else
    echo "[STEM ERROR] Python runtime not found on Android device." >&2
    exit 127
fi
"""


def assemble_aaos_payload() -> Path:
    """Assembles all required files into the staging directory."""
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copy the_stem
    shutil.copytree(PROJECT_ROOT / "the_stem", STAGING_DIR / "the_stem", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    # 2. Copy os_builder
    target_ob = STAGING_DIR / "os_builder"
    target_ob.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "os_builder" / "aaos_manifest.json", target_ob / "aaos_manifest.json")
    shutil.copy2(PROJECT_ROOT / "os_builder" / "aaos_vhal_interceptor.py", target_ob / "aaos_vhal_interceptor.py")

    # 3. Create __init__.py for os_builder
    (target_ob / "__init__.py").write_text('"""OS Builder Package."""\n', encoding="utf-8")

    # 4. Generate init.stem.rc and run_stem.sh
    (STAGING_DIR / "init.stem.rc").write_text(generate_init_rc(), encoding="utf-8")
    (STAGING_DIR / "run_stem.sh").write_text(generate_device_runner_sh(), encoding="utf-8")

    # 5. Generate SHA256 manifest of the payload
    manifest = {}
    for p in STAGING_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(STAGING_DIR).as_posix()
            manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

    (STAGING_DIR / "payload_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return STAGING_DIR


def package_offline_archive() -> Path:
    """Creates a compressed tarball archive for manual deployment."""
    stage = assemble_aaos_payload()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = OUTPUT_DIR / "stem_viper_aaos_appliance.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(stage, arcname="viper_stem")

    return archive_path


def deploy_to_device(serial: Optional[str] = None) -> bool:
    """Deploys the payload to a connected Android Automotive device via ADB."""
    adb = find_adb()
    if not adb:
        print("[ERROR] ADB not found. Cannot deploy to hardware.", file=sys.stderr)
        return False

    devs = detect_devices()
    if not devs:
        print("[WARN] No connected Android devices detected. Assembling offline archive instead.")
        arch = package_offline_archive()
        print(f"[OK] Offline Appliance Packaged: {arch}")
        return True

    target_serial = serial or devs[0]["serial"]
    print(f"[VIPER] Deploying to target device: {target_serial}...")

    stage = assemble_aaos_payload()
    remote_dest = "/data/local/tmp/viper_stem"

    # Push files via ADB
    cmd_push = [adb, "-s", target_serial, "push", str(stage) + "/.", remote_dest]
    res_push = subprocess.run(cmd_push, capture_output=True, text=True)
    if res_push.returncode != 0:
        print(f"[ERROR] Failed to push to device: {res_push.stderr}", file=sys.stderr)
        return False

    # Chmod executable permissions
    subprocess.run([adb, "-s", target_serial, "shell", f"chmod -R 755 {remote_dest}"], capture_output=True)
    print(f"[SUCCESS] The Stem + ViperCrest deployed to {target_serial}:{remote_dest}")
    return True
