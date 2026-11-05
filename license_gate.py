"""
ViperCrest Single-Seal Sovereign License Verification Gate (license_gate.py).

Enforces the asymmetric authority boundary:
    Authority_sign != Authority_execute

The installation contains ONLY the public verification key (public_seal.pem).
The engine has zero capability to mint or re-sign licenses.
It only evaluates:
    Verify(PK, License, Signature) -> TRUE / FALSE

If TRUE:  Binds the cryptographic digest of the seal into Genesis (T1_ROOT).
If FALSE: Immediately fails closed (HALT / exit code 1).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

VIPER_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = VIPER_ROOT / "runtime"
PUBLIC_SEAL_PATH = RUNTIME_DIR / "public_seal.pem"
LICENSE_SPEC_PATH = RUNTIME_DIR / "license_spec.json"
LICENSE_SIG_PATH = RUNTIME_DIR / "license.sig"


def verify_single_seal_or_halt() -> str:
    """Verifies the asymmetric single-seal license using ONLY the public key.
    
    Returns:
        Hex-encoded SHA-256 digest of the valid signature for Genesis binding.
    
    Raises:
        SystemExit(1) if verification fails, preserving fail-closed invariants.
    """
    if not PUBLIC_SEAL_PATH.exists():
        sys.stderr.write("[FAIL-CLOSED] Missing public verification key: runtime/public_seal.pem\n")
        sys.exit(1)

    if not LICENSE_SPEC_PATH.exists():
        sys.stderr.write("[FAIL-CLOSED] Missing license specification: runtime/license_spec.json\n")
        sys.exit(1)

    if not LICENSE_SIG_PATH.exists():
        sys.stderr.write("[FAIL-CLOSED] Missing cryptographic license seal: runtime/license.sig\n")
        sys.exit(1)

    try:
        public_bytes = PUBLIC_SEAL_PATH.read_bytes()
        public_key = load_pem_public_key(public_bytes)

        spec_bytes = LICENSE_SPEC_PATH.read_bytes()
        signature_bytes = LICENSE_SIG_PATH.read_bytes()

        # Deterministic asymmetric verification
        public_key.verify(signature_bytes, spec_bytes)

        # Compute tamper-evident digest to bind into Genesis provenance
        seal_digest = hashlib.sha256(signature_bytes).hexdigest()
        return seal_digest

    except InvalidSignature:
        sys.stderr.write("[FAIL-CLOSED] Tamper detected: License signature does not match license_spec.json!\n")
        sys.exit(1)
    except Exception as exc:
        sys.stderr.write(f"[FAIL-CLOSED] Cryptographic license gate error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    digest = verify_single_seal_or_halt()
    print(f"[PASS] Single-Seal License verified via public_seal.pem.")
    print(f"[GENESIS BINDING] Seal Digest: {digest}")
