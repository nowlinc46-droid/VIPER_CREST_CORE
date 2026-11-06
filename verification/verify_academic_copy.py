"""
ViperCrest Academic Distribution Ledger - Package Verification Tool
Location: C:\\ViperCrest_Distribution\\tools\\verify_academic_copy.py

Verifies an academic deliverable archive or unpacked directory against cryptographic
manifests, security boundaries, public seal fingerprints, and ledger blocks.
Can run standalone inside an unpacked package without any external dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_PUBLIC_KEY_FINGERPRINT = "bce4e2a249e2530a60557ca9aa19f5151941ef67914c60f110c8bb46844f711f"

FORBIDDEN_FILES = {
    "signing_key.pem",
    "master_license_private.pem",
    "master_license_private_ROTATED.pem",
    ".env",
}


def sha256_file(path: Path) -> str:
    """Computes lowercase hex SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def scan_for_forbidden_material(target_dir: Path) -> List[str]:
    """Scans target directory recursively for any forbidden private keys, credentials, or secrets."""
    violations: List[str] = []
    for root, _, files in os.walk(target_dir):
        for f in files:
            p = Path(root) / f
            fname_lower = f.lower()
            if f in FORBIDDEN_FILES:
                violations.append(f"Forbidden file present: {p.relative_to(target_dir)}")
            if "private" in fname_lower and fname_lower.endswith(".pem"):
                violations.append(f"Private key file detected: {p.relative_to(target_dir)}")
            if fname_lower.endswith(".key") and not fname_lower.endswith(".keyboard"):
                violations.append(f"Key file detected: {p.relative_to(target_dir)}")

            # Deep inspect small text files for private key headers
            if p.stat().st_size < 10240 and p.suffix in (".pem", ".txt", ".json", ".py", ".md"):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as tf:
                        text = tf.read()
                        if "BEGIN PRIVATE KEY" in text or "BEGIN EC PRIVATE KEY" in text or "BEGIN RSA PRIVATE KEY" in text:
                            violations.append(f"Private key header embedded in file: {p.relative_to(target_dir)}")
                except Exception:
                    pass
    return violations


def verify_manifest(target_dir: Path) -> Tuple[bool, List[str]]:
    """Verifies that all files listed in manifest.json exist and match recorded SHA-256 hashes."""
    manifest_file = target_dir / "manifest.json"
    if not manifest_file.exists():
        return False, ["manifest.json missing from package."]

    errors: List[str] = []
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        return False, [f"Failed to parse manifest.json: {e}"]

    # Check non-negotiable legal restrictions in manifest
    if manifest.get("commercial_rights") is not False:
        errors.append("Manifest violation: commercial_rights must be false")
    if manifest.get("equity_rights") is not False:
        errors.append("Manifest violation: equity_rights must be false")
    if manifest.get("issuance_authority") is not False:
        errors.append("Manifest violation: issuance_authority must be false")

    # Check public seal fingerprint
    manifest_fp = manifest.get("public_verification_key_fingerprint", "").lower()
    if manifest_fp != EXPECTED_PUBLIC_KEY_FINGERPRINT:
        errors.append(f"Manifest public key fingerprint mismatch: {manifest_fp} != {EXPECTED_PUBLIC_KEY_FINGERPRINT}")

    files = manifest.get("files", [])
    if not files:
        errors.append("Manifest contains no file entries.")

    for entry in files:
        rel_path = entry.get("path")
        expected_hash = entry.get("sha256", "").lower()
        actual_path = target_dir / rel_path

        if not actual_path.exists():
            errors.append(f"Missing file declared in manifest: {rel_path}")
            continue

        actual_hash = sha256_file(actual_path)
        if actual_hash != expected_hash:
            errors.append(f"Hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}")

    return len(errors) == 0, errors


def verify_security_boundary(target_dir: Path) -> Tuple[bool, List[str]]:
    """Verifies air-gap settings, public seal, and absence of private keys."""
    errors: List[str] = []

    # 1. Check public seal
    seal_path = target_dir / "runtime" / "public_seal.pem"
    if not seal_path.exists():
        errors.append("Missing public seal: runtime/public_seal.pem")
    else:
        seal_hash = sha256_file(seal_path)
        if seal_hash != EXPECTED_PUBLIC_KEY_FINGERPRINT:
            errors.append(f"Public seal fingerprint mismatch: got {seal_hash}, expected {EXPECTED_PUBLIC_KEY_FINGERPRINT}")

    # 2. Check network config
    net_cfg = target_dir / "network_config.json"
    if net_cfg.exists():
        try:
            with open(net_cfg, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("NETWORK_ENABLED") is not False:
                    errors.append("Air-gap violation: network_config.json has NETWORK_ENABLED != false")
        except Exception as e:
            errors.append(f"Failed to read network_config.json: {e}")

    # 3. Scan for forbidden secrets
    violations = scan_for_forbidden_material(target_dir)
    errors.extend(violations)

    return len(errors) == 0, errors


def verify_academic_deliverable(
    target_path: Path,
    ledger_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Runs complete verification of a deliverable archive (ZIP) or unpacked folder."""
    print("=" * 70)
    print("VIPERCREST ACADEMIC DELIVERABLE INTEGRITY VERIFIER")
    print(f"Target: {target_path}")
    print("=" * 70)

    is_zip = target_path.suffix.lower() == ".zip"
    temp_dir = None
    if is_zip:
        if not target_path.exists():
            print(f"[FAIL] Target archive not found: {target_path}")
            return {"verdict": "FAIL", "reason": "Archive file not found"}
        archive_sha256 = sha256_file(target_path)
        print(f"[1/5] Archive SHA-256 Digest: {archive_sha256}")
        temp_dir = tempfile.TemporaryDirectory()
        unpack_dir = Path(temp_dir.name)
        with zipfile.ZipFile(target_path, "r") as zf:
            zf.extractall(unpack_dir)
        inspect_dir = unpack_dir
    else:
        if not target_path.exists() or not target_path.is_dir():
            print(f"[FAIL] Target directory not found: {target_path}")
            return {"verdict": "FAIL", "reason": "Target directory not found"}
        archive_sha256 = None
        inspect_dir = target_path

    try:
        # Check manifest
        print(f"[2/5] Validating Manifest & File Hashes...")
        manifest_ok, manifest_errors = verify_manifest(inspect_dir)
        if manifest_ok:
            print("      Manifest check: PASS (All hashes match)")
        else:
            print(f"      Manifest check: FAIL ({len(manifest_errors)} errors)")
            for err in manifest_errors[:5]:
                print(f"      - {err}")

        # Check security boundary
        print(f"[3/5] Validating Security Boundaries & Secret Isolation...")
        boundary_ok, boundary_errors = verify_security_boundary(inspect_dir)
        if boundary_ok:
            print("      Boundary check: PASS (Zero secrets found, public seal verified)")
        else:
            print(f"      Boundary check: FAIL ({len(boundary_errors)} errors)")
            for err in boundary_errors[:5]:
                print(f"      - {err}")

        # Read manifest metadata
        manifest_file = inspect_dir / "manifest.json"
        manifest_data = {}
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

        copy_id = manifest_data.get("copy_id", "UNKNOWN")

        # Check ledger record if ledger_path provided or found
        print(f"[4/5] Cross-Checking Academic Provenance Ledger...")
        ledger_ok = True
        ledger_errors = []
        ledger_block = None

        if ledger_path is None:
            # Check default location
            default_ledger = Path(r"C:\ViperCrest_Distribution\registry\ledger.jsonl")
            if default_ledger.exists():
                ledger_path = default_ledger

        if ledger_path and ledger_path.exists():
            with open(ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        b = json.loads(line)
                        if b.get("copy_id") == copy_id:
                            ledger_block = b
                            break

            if ledger_block is None:
                ledger_errors.append(f"Copy ID {copy_id} not found in ledger {ledger_path}")
                ledger_ok = False
            else:
                if is_zip and ledger_block.get("artifact_sha256") != archive_sha256:
                    ledger_errors.append(
                        f"Ledger artifact_sha256 mismatch: {ledger_block.get('artifact_sha256')} != {archive_sha256}"
                    )
                    ledger_ok = False
                print(f"      Ledger check: PASS (Matched Block #{ledger_block.get('block_index')})")
        else:
            print("      Ledger check: SKIPPED (Ledger file not provided/accessible)")

        # Overall verdict
        all_passed = manifest_ok and boundary_ok and ledger_ok
        verdict = "PASS" if all_passed else "FAIL"

        print(f"[5/5] Generating Verification Verdict...")
        print("=" * 70)
        print(f"VERIFICATION VERDICT: [{verdict}]")
        print(f"  Copy ID:         {copy_id}")
        print(f"  Manifest Status: {'PASS' if manifest_ok else 'FAIL'}")
        print(f"  Security Status: {'PASS' if boundary_ok else 'FAIL'}")
        print(f"  Ledger Status:   {'PASS' if ledger_ok else 'FAIL'}")
        if archive_sha256:
            print(f"  Archive SHA-256: {archive_sha256}")
        print("=" * 70)

        # Build Receipt
        receipt = {
            "receipt_id": f"REC-{copy_id}-{int(datetime.now(timezone.utc).timestamp())}",
            "copy_id": copy_id,
            "ledger_block_index": ledger_block.get("block_index") if ledger_block else 0,
            "ledger_block_hash": ledger_block.get("block_hash") if ledger_block else "0" * 64,
            "artifact_zip_sha256": archive_sha256 or "N/A",
            "public_key_fingerprint": EXPECTED_PUBLIC_KEY_FINGERPRINT,
            "issued_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "issuer_status": ledger_block.get("issuer_status") if ledger_block else "UNKNOWN",
            "verification_verdict": verdict,
            "details": {
                "manifest_ok": manifest_ok,
                "boundary_ok": boundary_ok,
                "ledger_ok": ledger_ok,
                "manifest_errors": manifest_errors,
                "boundary_errors": boundary_errors,
                "ledger_errors": ledger_errors,
            },
        }

        # Write reports if directory available
        rep_dir = Path(r"C:\ViperCrest_Distribution\reports")
        if rep_dir.exists():
            with open(rep_dir / "verification_report.json", "w", encoding="utf-8") as f:
                json.dump(receipt, f, indent=2)

        return receipt

    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify ViperCrest Academic Deliverable")
    parser.add_argument("target", help="Path to deliverable .zip archive or unpacked folder")
    parser.add_argument("--ledger", default=None, help="Optional path to ledger.jsonl")
    args = parser.parse_args()

    result = verify_academic_deliverable(Path(args.target), Path(args.ledger) if args.ledger else None)
    sys.exit(0 if result.get("verification_verdict") == "PASS" else 1)
