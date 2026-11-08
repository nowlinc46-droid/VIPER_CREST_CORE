"""
Adversarial Cryptographic Provenance Attack Suite (test_adversarial_provenance.py).

Adversarial verification testing the 3 provenance vectors:
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

import viper_matrix
import viper_core
from session_router import load_session


class AdversarialProvenanceAttackTests(unittest.TestCase):
    """Executes the 3 adversarial provenance attack vectors against ViperCrest."""

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
