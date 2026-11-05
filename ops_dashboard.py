"""
ViperCrest Operational Dashboard (ops_dashboard.py).
Fast operational health check across state ledger, air-gap boundary,
frozen kernels, signing keys, and the stem kinetic gate.
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent

FROZEN_KERNELS = {
    "convergence_engine.py": "4AC3936D8915EF7F20B474C601F3444259F721B3F910C7D6CBE84608E9E33E18",
    "viper_matrix.py": "7498B5D192687EB8C2E5087390371B6ACD6A487BB9723968834D9F25A83474C3",
    "viper_core.py": "09B40E86BACF816752FC9BC35C4487A4A551A160D8B5D3B6A06A68E7B5FC2457",
    "viper_http.py": "A6F570EDDD4344ED303C90ECA6BAA41F01A5F9AAF14C2DF7DF6FC55EEEE635EA",
}


def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    print("=" * 72)
    print("              VIPERCREST 2.0 - OPERATIONAL STATUS DASHBOARD")
    print("=" * 72)

    # 1. Frozen Kernels Check
    print("\n[1] FROZEN KERNEL PARITY:")
    kernel_ok = True
    for name, expected in FROZEN_KERNELS.items():
        fp = VIPER_ROOT / name
        if not fp.exists():
            print(f"  [-] {name:<22} MISSING!")
            kernel_ok = False
            continue
        actual = get_sha256(fp)
        if actual == expected:
            print(f"  [+] {name:<22} INVARIANT PASS  ({actual[:16]}...)")
        else:
            print(f"  [-] {name:<22} MISMATCH! {actual} != {expected}")
            kernel_ok = False

    # 2. SQLite Ledger
    print("\n[2] STATE LEDGER (runtime/viper_state.db):")
    db_path = VIPER_ROOT / "runtime" / "viper_state.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM runs")
            runs = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM receipts")
            receipts = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM artifacts")
            artifacts = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM dropzone_intake")
            dropzone = cur.fetchone()[0]
            conn.close()
            print(f"  [+] Runs Logged      : {runs:,}")
            print(f"  [+] Chained Receipts : {receipts:,}")
            print(f"  [+] State Artifacts  : {artifacts:,}")
            print(f"  [+] Dropzone Records : {dropzone:,}")
        except Exception as exc:
            print(f"  [-] Ledger error: {exc}")
    else:
        print("  [!] SQLite database not found (fresh state).")

    # 3. Cryptographic Signing Key
    print("\n[3] CRYPTOGRAPHIC ATTESTATION:")
    key_path = VIPER_ROOT / "runtime" / "signing_key.pem"
    if key_path.exists():
        size = key_path.stat().st_size
        print(f"  [+] Ed25519 Signing Key Active ({key_path.name}, {size} bytes)")
    else:
        print("  [!] Signing key not found (ephemeral generated on-demand).")

    # 4. Standalone Tool: The Stem
    print("\n[4] AUTONOMOUS ROBOTICS BRAINSTEM (the_stem):")
    stem_init = VIPER_ROOT / "the_stem" / "__init__.py"
    if stem_init.exists():
        try:
            from the_stem.stem_governor import StemGovernor
            gov = StemGovernor()
            print(f"  [+] Tool Package     : the_stem (INSTALLED & OPERATIONAL)")
            print(f"  [+] Governor State   : {gov.state}")
            print(f"  [+] Active Gaps      : {len(gov.gap_set)}")
            print(f"  [+] Kinetic Cutoff   : {gov.torque_gate.config.max_torque_nm} Nm MAX")
            print(f"  [+] Trip Status      : {'TRIPPED' if gov.torque_gate.is_tripped else 'CLEAR / ARMED'}")
        except Exception as exc:
            print(f"  [-] The Stem load error: {exc}")
    else:
        print("  [!] The Stem package not found.")

    # 5. Air-Gap Mode
    print("\n[5] AIR-GAP & BOUNDARY ENFORCEMENT:")
    try:
        from network_adapter import NetworkConfig
        cfg = NetworkConfig()
        print(f"  [+] Air-Gap Mode     : {'ENFORCED (FAIL-CLOSED)' if not cfg.network_enabled else 'ENABLED'}")
        print(f"  [+] Allowed Hosts    : {cfg.allowed_hosts if cfg.allowed_hosts else 'NONE (Zero External Egress)'}")
    except Exception as exc:
        print(f"  [!] Network adapter check error: {exc}")

    print("\n" + "=" * 72)
    overall = "HEALTHY & INVARIANT VERIFIED" if kernel_ok else "KERNEL MISMATCH / ATTENTION REQUIRED"
    print(f"  OVERALL SYSTEM STATUS: {overall}")
    print("=" * 72 + "\n")
    return 0 if kernel_ok else 1


if __name__ == "__main__":
    sys.exit(main())
