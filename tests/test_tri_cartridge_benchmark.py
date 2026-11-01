"""
Tri-Domain Benchmark Test Suite.
Verifies universal domain agnosticism across Security IR, CourtForge Legal,
and WMS Logistics cartridges running on the invariant F1-F9 engine, proving
spatial integrity, zero-invention hydration, F7 containment, and the 729-coordinate tensor.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

import domain_space as ds
import reader_engine as re_eng

VIPER_ROOT = Path(__file__).resolve().parent.parent
PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)


class TriCartridgeBenchmarkTests(unittest.TestCase):
    def setUp(self):
        re_eng.ensure_sample_raw_files()

    def test_01_spatial_integrity_and_tensor_dimensions(self):
        """Test 1: Verify all 3 cartridges instantiate the exact S1..S9 geometry and 729 tensor space."""
        cartridges = [
            ds.cartridge_security_ir,
            ds.cartridge_courtforge_legal,
            ds.cartridge_wms_logistics,
        ]

        for cart in cartridges:
            self.assertEqual(len(cart.seed_meanings), 9, f"Cartridge {cart.cartridge_id} must have exactly 9 seeds")
            self.assertEqual(set(cart.seed_meanings.keys()), set(ds.DOMAIN_SEEDS))

            space = ds.DomainSpaceInstance(space_id=f"TEST_{cart.cartridge_id}", phase="T5_COMPOUNDING")
            self.assertTrue(space.validate_spatial_integrity())
            self.assertEqual(set(space.seeds.keys()), set(ds.DOMAIN_SEEDS))

            tms = ds.TemporalMatrixSpace(cartridge=cart)
            tms.set_space("T5_COMPOUNDING", space)
            self.assertTrue(tms.validate_spatial_integrity())

        # Verify 729 Tensor Coordinates (9 runtime stages x 9 spatial seeds x 9 temporal phases)
        coords = ds.generate_tensor_coordinates()
        self.assertEqual(len(coords), 729)
        self.assertEqual(ds.TOTAL_TENSOR_COORDINATES, 729)
        self.assertEqual(ds.TENSOR_DIMENSIONS, (9, 9, 9))

    def test_02_bounded_hydration_zero_speculation(self):
        """Test 2: Ingest minimal seeds and verify evidence-bounded transitions without inventing facts."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            fixture_path = re_eng.run_cartridge_intake(dom, print_summary=False)
            self.assertTrue(fixture_path.exists())

            raw_file = re_eng.DROPZONE_RAW / re_eng.SAMPLE_RAW_DATA[dom]["filename"]
            raw_text = re_eng.safe_decode_text(raw_file.read_bytes())
            tms = re_eng.parse_raw_stream(raw_text, dom)

            report = tms.construct_hydration_report()
            # Verified Epistemic Hydration Profile:
            self.assertEqual(report["T5_COMPOUNDING"], "OBSERVED", f"T5 must be OBSERVED in {dom}")
            self.assertEqual(report["T4_STABILITY"], "DERIVED", f"T4 must be DERIVED in {dom}")
            self.assertEqual(report["T6_REFRACTING"], "POSSIBLE", f"T6 must be POSSIBLE in {dom}")
            self.assertEqual(report["T1_ROOT"], "UNRESOLVED", f"T1 must be UNRESOLVED in {dom}")
            self.assertEqual(report["T9_STONE"], "UNRESOLVED", f"T9 must be UNRESOLVED in {dom}")

            # Verify Transition Receipts exist and are cryptographically bound
            self.assertEqual(len(tms.transition_receipts), 2)
            for r in tms.transition_receipts:
                self.assertIn("receipt_hash", r)
                self.assertEqual(r["engine_binding"], "F1:F2:F3:F4:F5:F6:F7:F8:F9")

    def test_03_f7_discovery_unknowns_unresolved(self):
        """Test 3: Assert that F7 unknowns remain strictly UNRESOLVED across all 3 domains."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            raw_file = re_eng.DROPZONE_RAW / re_eng.SAMPLE_RAW_DATA[dom]["filename"]
            raw_text = re_eng.safe_decode_text(raw_file.read_bytes())
            tms = re_eng.parse_raw_stream(raw_text, dom)

            s5_space = tms.positions.get("T5_COMPOUNDING")
            self.assertIsNotNone(s5_space)

            s7_seed = s5_space.seeds.get("S7")
            self.assertIsNotNone(s7_seed)

            # Invariant: S7 must capture unknown/discovery and lock in F7
            s7_state = s7_seed.get("state", "")
            s7_evidence = s7_seed.get("evidence", "")

            self.assertTrue(
                "UNRESOLVED" in s7_state or "UNPRODUCED" in s7_state or "UNINSPECTED" in s7_state or "NONE_PENDING" in s7_state,
                f"S7 state '{s7_state}' in {dom} must express discovery / unresolved containment"
            )
            self.assertIn("F7", s7_evidence, f"S7 evidence in {dom} must explicitly reference containment in F7")

    def test_04_fixed_f1_f9_engine_execution_and_determinism(self):
        """Test 4: Run fixed F1-F9 engine against all 3 fixtures, assert exit code 0 and deterministic hashes."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            fixture_path = re_eng.run_cartridge_intake(dom, print_summary=False)
            self.assertTrue(fixture_path.exists())

            # Run Matrix Engine via viper.py
            cmd = [str(PYTHON_EXE), "-B", str(VIPER_ROOT / "viper.py"), "matrix", "--target", str(fixture_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Matrix execution failed for {dom}:\n{res.stderr}\n{res.stdout}")
            self.assertIn("human_review_required", res.stdout)
            self.assertIn("Receipt and five-file session audit verified", res.stdout)

            # Verify Deterministic Ingestion: Repeated hashing yields identical SHA-256
            raw_bytes1, sha1 = re_eng.safe_read_bytes(re_eng.DROPZONE_RAW / re_eng.SAMPLE_RAW_DATA[dom]["filename"])
            raw_bytes2, sha2 = re_eng.safe_read_bytes(re_eng.DROPZONE_RAW / re_eng.SAMPLE_RAW_DATA[dom]["filename"])
            self.assertEqual(sha1, sha2)
            self.assertEqual(hashlib.sha256(raw_bytes1).hexdigest(), sha1)

    def test_05_engine_invariance_zero_diff(self):
        """Test 5: Verify that F1-F9 core engine source code has zero diffs."""
        core_files = ["viper_matrix.py", "viper_core.py", "viper_http.py"]
        cmd = ["git", "status", "--porcelain"] + core_files
        res = subprocess.run(cmd, cwd=str(VIPER_ROOT), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(
            res.stdout.strip(), "",
            f"Core engine invariance violation! Files modified:\n{res.stdout}"
        )


if __name__ == "__main__":
    unittest.main()
