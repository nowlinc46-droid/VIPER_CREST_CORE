"""
Minimal Seed -> Natural Tensor Hydration Test Suite.

Proves that the entire 81-coordinate state matrix and 729-coordinate tensor space
naturally hydrate from an irreducibly minimal seed across three unrelated domains
(Security IR, CourtForge Legal, WMS Logistics) without hallucination or speculation,
preserving uncertainty in F7, and executing deterministically through the fixed F1-F9 engine.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import domain_space as ds
import reader_engine as re_eng

PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)


class MinimalSeedTensorHydrationTests(unittest.TestCase):
    def test_01_atomic_seed_irreducibility(self):
        """Test 1: Assert input is an atomic, irreducible seed and maps to valid hash & root structure."""
        seeds = re_eng.SAMPLE_MINIMAL_SEEDS
        self.assertIn("security", seeds)
        self.assertIn("legal", seeds)
        self.assertIn("logistics", seeds)

        for domain, seed_text in seeds.items():
            self.assertEqual(len(seed_text.strip().splitlines()), 1, f"{domain} seed must be a single irreducible line")
            tms = ds.hydrate_from_minimal_seed(seed_text, domain)
            self.assertTrue(tms.validate_spatial_integrity())
            self.assertEqual(len(tms.transition_receipts), 2)

    def test_02_spatial_containment_and_zero_speculation(self):
        """Test 2: Assert only directly evidenced seeds are OBSERVED, S8 is pinned, S9 authenticated, and rest UNRESOLVED."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            seed_text = re_eng.SAMPLE_MINIMAL_SEEDS[dom]
            tms = ds.hydrate_from_minimal_seed(seed_text, dom)
            space_t5 = tms.positions["T5_COMPOUNDING"]
            self.assertIsNotNone(space_t5)

            # S8 must be pinned invariant rule
            self.assertIn("PINNED", space_t5.seeds["S8"]["state"] + space_t5.seeds["S8"]["evidence"])
            self.assertEqual(space_t5.seeds["S8"]["status"], "OBSERVED")

            # S9 must be authenticated hash
            self.assertEqual(space_t5.seeds["S9"]["status"], "OBSERVED")
            self.assertIn("SHA256", space_t5.seeds["S9"]["evidence"])

            # S7 must lock unobserved domain in F7
            self.assertEqual(space_t5.seeds["S7"]["status"], "UNRESOLVED")
            self.assertEqual(space_t5.seeds["S7"]["state"], "CONTAINED_IN_F7")

            # Unobserved coordinates must remain UNRESOLVED
            for s in ["S1", "S4", "S6"]:
                self.assertEqual(
                    space_t5.seeds[s]["status"],
                    "UNRESOLVED",
                    f"Seed {s} in {dom} must remain UNRESOLVED in minimal hydration",
                )

    def test_03_temporal_epistemic_profile(self):
        """Test 3: Assert T5=OBSERVED, T4=DERIVED, T6=POSSIBLE, and all distant phases UNRESOLVED."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            seed_text = re_eng.SAMPLE_MINIMAL_SEEDS[dom]
            tms = ds.hydrate_from_minimal_seed(seed_text, dom)
            report = tms.construct_hydration_report()

            # Center phase is OBSERVED
            self.assertEqual(report["T5_COMPOUNDING"], "OBSERVED")
            # Bounded predecessor is DERIVED
            self.assertEqual(report["T4_STABILITY"], "DERIVED")
            # Bounded successor is POSSIBLE
            self.assertEqual(report["T6_REFRACTING"], "POSSIBLE")

            # Distant temporal phases must remain strictly UNRESOLVED
            for distant_phase in ["T1_ROOT", "T2_VEIL", "T3_PATH_IN", "T7_FLAME", "T8_PATH_OUT", "T9_STONE"]:
                self.assertEqual(
                    report[distant_phase],
                    "UNRESOLVED",
                    f"Distant phase {distant_phase} in {dom} must remain UNRESOLVED",
                )

    def test_04_tensor_729_sweep_and_uncertainty_conservation(self):
        """Test 4: Sweep 729-coordinate tensor (9x9x9) and verify uncertainty conservation in F7."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            seed_text = re_eng.SAMPLE_MINIMAL_SEEDS[dom]
            tms = ds.hydrate_from_minimal_seed(seed_text, dom)
            tensor_eval = tms.evaluate_729_tensor_space()

            self.assertEqual(tensor_eval["total_tensor_coordinates"], 729)
            self.assertEqual(tensor_eval["dimensions"], (9, 9, 9))

            summary = tensor_eval["summary"]
            self.assertEqual(summary["total_state_cells"], 81)

            # Conservation of Uncertainty: Exactly 70 cells must remain UNRESOLVED in F7
            self.assertEqual(
                summary["unresolved_f7_cells"], 70,
                f"Minimal seed must leave exactly 70 of 81 cells UNRESOLVED in {dom}"
            )
            # Total sum of state positions must equal 81
            total_cells = (
                summary["observed_cells"]
                + summary["derived_cells"]
                + summary["possible_cells"]
                + summary["unresolved_f7_cells"]
            )
            self.assertEqual(total_cells, 81)

            # Verify that every tensor point has a valid runtime action
            for pt in tensor_eval["points"]:
                self.assertIn(pt["stage"], ds.RUNTIME_STAGES)
                self.assertIn(pt["phase"], ds.TEMPORAL_PHASES)
                self.assertIn(pt["seed"], ds.DOMAIN_SEEDS)
                self.assertIn(pt["epistemic_status"], ds.HYDRATION_STATES)

    def test_05_tri_domain_minimal_seed_matrix_execution(self):
        """Test 5: Run fixed F1-F9 engine against minimal seed fixtures across all 3 domains."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            fixture_path, tms = re_eng.run_minimal_seed_intake(dom, print_summary=False)
            self.assertTrue(fixture_path.exists())

            cmd = [str(PYTHON_EXE), "-B", str(VIPER_ROOT / "viper.py"), "matrix", "--target", str(fixture_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(
                res.returncode, 0,
                f"Minimal seed matrix execution failed for {dom}:\n{res.stderr}\n{res.stdout}"
            )
            self.assertIn("human_review_required", res.stdout)
            self.assertIn("Receipt and five-file session audit verified", res.stdout)

    def test_06_deterministic_convergence(self):
        """Test 6: Repeated minimal seed hydrations yield bit-identical hashes and receipts."""
        domains = ["security", "legal", "logistics"]

        for dom in domains:
            seed_text = re_eng.SAMPLE_MINIMAL_SEEDS[dom]
            tms_1 = ds.hydrate_from_minimal_seed(seed_text, dom)
            tms_2 = ds.hydrate_from_minimal_seed(seed_text, dom)

            # Compare Space hashes
            self.assertEqual(
                tms_1.positions["T5_COMPOUNDING"].provenance_hash,
                tms_2.positions["T5_COMPOUNDING"].provenance_hash,
            )
            self.assertEqual(
                tms_1.positions["T4_STABILITY"].provenance_hash,
                tms_2.positions["T4_STABILITY"].provenance_hash,
            )
            self.assertEqual(
                tms_1.positions["T6_REFRACTING"].provenance_hash,
                tms_2.positions["T6_REFRACTING"].provenance_hash,
            )

            # Compare Transition Receipts
            self.assertEqual(len(tms_1.transition_receipts), len(tms_2.transition_receipts))
            for r1, r2 in zip(tms_1.transition_receipts, tms_2.transition_receipts):
                self.assertEqual(r1["receipt_hash"], r2["receipt_hash"])

    def test_07_engine_invariance_zero_diff(self):
        """Test 7: Verify that F1-F9 core engine files remain byte-identical (0 diff)."""
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
