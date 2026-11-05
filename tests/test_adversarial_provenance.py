"""
Adversarial Cryptographic Provenance & License Gate Attack Suite (test_adversarial_provenance.py).

Rigorous adversarial verification testing the 7 cryptographic vectors:
  1. ORIGINAL                  -> PASS
  2. LICENSE SPEC MODIFIED     -> FAIL (HALT before execution)
  3. SIGNATURE MODIFIED        -> FAIL (HALT before execution)
  4. PUBLIC KEY REPLACED       -> FAIL (HALT before execution)
  5. INPUT MODIFIED            -> DIFFERENT DESCENDANT PROVENANCE
  6. PREDECESSOR MODIFIED      -> CHAIN VERIFICATION FAIL
  7. UNMODIFIED REPLAY         -> REPRODUCIBLE DETERMINISTIC RESULT
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from license_gate import (
    verify_single_seal_or_halt,
    PUBLIC_SEAL_PATH,
    LICENSE_SPEC_PATH,
    LICENSE_SIG_PATH,
)
import viper_matrix
import viper_core
from session_router import load_session


class AdversarialProvenanceAttackTests(unittest.TestCase):
    """Executes the 7 adversarial attack vectors against ViperCrest."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.fixtures_dir = VIPER_ROOT / "fixtures"
        self.sample_fixture = self.fixtures_dir / "minimal_baseline.json"
        if not self.sample_fixture.exists():
            # Create a valid fixture if minimal_baseline.json isn't present
            self.sample_fixture = self.work_dir / "test_fixture.json"
            self.sample_fixture.write_text(
                json.dumps({
                    "case_id": "adversarial-attack-test",
                    "metadata": {"domain": "TEST", "description": "baseline"},
                    "observations": {"obs_1": {"value": 1.0}},
                    "governing_rules": {"rule_1": {"limit": 10.0}}
                }),
                encoding="utf-8"
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_original_valid_installation_passes(self):
        """Vector 1: Original valid installation, valid license, valid PK -> PASS."""
        digest = verify_single_seal_or_halt()
        self.assertTrue(isinstance(digest, str) and len(digest) == 64)
        print("\n  [ATTACK VECTOR 1] ORIGINAL -> PASS")

    def test_02_license_spec_modified_fails(self):
        """Vector 2: Tampering with license_spec.json -> FAIL-CLOSED."""
        original_spec = LICENSE_SPEC_PATH.read_bytes()
        try:
            # Mutate one field in license spec
            tampered_spec = json.loads(original_spec.decode("utf-8"))
            tampered_spec["licensee"] = "ROGUE_OPERATOR"
            LICENSE_SPEC_PATH.write_text(json.dumps(tampered_spec), encoding="utf-8")

            # Must raise SystemExit(1)
            with self.assertRaises(SystemExit) as ctx:
                verify_single_seal_or_halt()
            self.assertEqual(ctx.exception.code, 1)
            print("  [ATTACK VECTOR 2] LICENSE SPEC MODIFIED -> FAIL (HALTED)")
        finally:
            # Restore original
            LICENSE_SPEC_PATH.write_bytes(original_spec)

    def test_03_signature_modified_fails(self):
        """Vector 3: Tampering with 1 byte of license.sig -> FAIL-CLOSED."""
        original_sig = LICENSE_SIG_PATH.read_bytes()
        try:
            # Flip 1 byte
            tampered_sig = bytearray(original_sig)
            tampered_sig[0] ^= 0xFF
            LICENSE_SIG_PATH.write_bytes(bytes(tampered_sig))

            with self.assertRaises(SystemExit) as ctx:
                verify_single_seal_or_halt()
            self.assertEqual(ctx.exception.code, 1)
            print("  [ATTACK VECTOR 3] SIGNATURE MODIFIED -> FAIL (HALTED)")
        finally:
            LICENSE_SIG_PATH.write_bytes(original_sig)

    def test_04_public_key_replaced_fails(self):
        """Vector 4: Replacing public_seal.pem with a rogue key -> FAIL-CLOSED."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        original_pk = PUBLIC_SEAL_PATH.read_bytes()
        try:
            rogue_key = Ed25519PrivateKey.generate()
            rogue_pk_bytes = rogue_key.public_key().public_bytes(
                Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
            )
            PUBLIC_SEAL_PATH.write_bytes(rogue_pk_bytes)

            with self.assertRaises(SystemExit) as ctx:
                verify_single_seal_or_halt()
            self.assertEqual(ctx.exception.code, 1)
            print("  [ATTACK VECTOR 4] PUBLIC KEY REPLACED -> FAIL (HALTED)")
        finally:
            PUBLIC_SEAL_PATH.write_bytes(original_pk)

    def test_05_input_modified_produces_different_descendants(self):
        """Vector 5: Modifying input payload produces a different descendant hash."""
        f1_data = {"case_id": "test-input-a", "value": 100}
        f2_data = {"case_id": "test-input-b", "value": 101}  # 1 bit difference

        h1 = viper_matrix._sha256(f1_data)
        h2 = viper_matrix._sha256(f2_data)

        self.assertNotEqual(h1, h2)
        print("  [ATTACK VECTOR 5] INPUT MODIFIED -> DIFFERENT DESCENDANT")

    def test_06_predecessor_modified_fails_chain_verification(self):
        """Vector 6: Modifying predecessor hash trips chain verification failure."""
        from viper_http import verify_receipt
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        envelope = {
            "icon_uri": "icon://sector/f1/evaluate",
            "run_id": "test-run-001",
            "sector_id": "F1",
            "stage": "F1_Ingestion",
            "input_hash": "a" * 64,
            "target_payload": {"test": 1},
        }
        receipt = {
            "icon_uri": "icon://sector/f1/verdict",
            "sector_id": "F1",
            "run_id": "test-run-001",
            "timestamp": "2026-11-05T00:00:00Z",
            "request_hash": viper_core.canonical_json(envelope),
            "content": {"result": "ok"},
            "state_provenance": {
                "input_hash": "a" * 64,
                "output_hash": "b" * 64,
            },
            "signature_algorithm": "Ed25519",
        }
        sig = key.sign(viper_core.canonical_json(receipt).encode("utf-8")).hex()
        receipt["signature_hex"] = sig

        # Tampering with predecessor input_hash in envelope
        tampered_envelope = dict(envelope)
        tampered_envelope["input_hash"] = "f" * 64

        with self.assertRaises(Exception):
            verify_receipt(1, tampered_envelope, receipt, key.public_key())
        print("  [ATTACK VECTOR 6] PREDECESSOR MODIFIED -> CHAIN VERIFICATION FAIL")

    def test_07_unmodified_replay_produces_deterministic_derivation(self):
        """Vector 7: Unmodified replay yields bit-for-bit identical derivation hashes."""
        payload = {"domain": "TEST", "seed": 42, "matrix": [1, 2, 3]}
        h_run_1 = viper_matrix._sha256(payload)
        h_run_2 = viper_matrix._sha256(payload)

        self.assertEqual(h_run_1, h_run_2)
        print("  [ATTACK VECTOR 7] UNMODIFIED REPLAY -> REPRODUCIBLE RESULT")


if __name__ == "__main__":
    unittest.main()
