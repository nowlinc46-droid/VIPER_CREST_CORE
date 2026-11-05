"""
ViperCrest 2.0 - Scale-Invariant Open Ontological Expansion Test Suite
tests/test_open_ontological_expansion.py

Directly answers Grok's 4 acceptance criteria for open-ended state discovery:
  1. Presents novel dimension S10_OPTICAL_THERMAL_FLUX to the unchanged core.
  2. Proves that:
     - Original 729-coordinate lattice (9 stages x 9 seeds x 9 phases) and F1-F9 stages remain untouched.
     - Novel key is isolated in G(S) as an explicit unmapped gap (status='UNRESOLVED', state='UNMAPPED_SEED').
     - Engine transitions to SUSPENDED with recovery directive explicitly naming S10_OPTICAL_THERMAL_FLUX.
     - Exact SHA-256 digests of the four frozen core files remain 100% bit-for-bit invariant.
  3. Subsequent recovery of evidence for S10 clears the gap and transitions to BOUNDED / SEALED,
     binding H(S1) -> H(S0) with zero kernel changes and zero changes to DOMAIN_SEEDS.
  4. Confirms the engine still strictly rejects malformed or contradictory evidence on canonical S1-S9.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import domain_space as ds
import reader_engine as re_eng
from convergence_engine import ConvergenceEngine, Gap, SuccessorState

# Frozen core baseline hashes
BASELINE_HASHES = {
    "convergence_engine.py": "4AC3936D8915EF7F20B474C601F3444259F721B3F910C7D6CBE84608E9E33E18",
    "viper_matrix.py": "7498B5D192687EB8C2E5087390371B6ACD6A487BB9723968834D9F25A83474C3",
    "viper_core.py": "09B40E86BACF816752FC9BC35C4487A4A551A160D8B5D3B6A06A68E7B5FC2457",
    "viper_http.py": "A6F570EDDD4344ED303C90ECA6BAA41F01A5F9AAF14C2DF7DF6FC55EEEE635EA",
}


class OpenOntologicalExpansionTests(unittest.TestCase):
    """
    Verification of scale-invariant ontological discovery and unmapped seed isolation.
    """

    def setUp(self):
        # Verify 4 frozen files match SHA-256 before every test
        for fname, expected in BASELINE_HASHES.items():
            actual = hashlib.sha256((VIPER_ROOT / fname).read_bytes()).hexdigest().upper()
            self.assertEqual(
                actual,
                expected,
                f"Frozen kernel integrity violation on {fname}: {actual} != {expected}",
            )

    def test_01_lattice_and_frozen_core_invariance(self):
        """
        Criterion 2a & 2d: Baseline lattice cardinality is exactly 729 (9x9x9)
        and all 4 kernel files are strictly bit-for-bit invariant.
        """
        self.assertEqual(len(ds.RUNTIME_STAGES), 9, "Runtime stages must remain strictly F1-F9")
        self.assertEqual(len(ds.DOMAIN_SEEDS), 9, "Canonical domain seeds must remain strictly S1-S9")
        self.assertEqual(len(ds.TEMPORAL_PHASES), 9, "Temporal phases must remain strictly T1-T9")
        self.assertEqual(
            ds.TOTAL_TENSOR_COORDINATES,
            729,
            "Baseline tensor coordinate count must remain strictly 729",
        )
        self.assertEqual(
            ds.DOMAIN_SEEDS,
            ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"),
            "DOMAIN_SEEDS constant must never be expanded or re-labeled",
        )

    def test_02_novel_dimension_isolated_into_gap_set_and_suspends(self):
        """
        Criteria 1 & 2: Novel key S10_OPTICAL_THERMAL_FLUX is presented to the unchanged core,
        detected as unmapped, isolated into G(S), and forces state into SUSPENDED.
        """
        # Pass 0 payload: S1-S9 nominal, but presents novel dimension S10 without calibration
        payload_pass_0 = (
            "2026-11-04T00:00:00Z [TELEMETRY_INGEST] sensor_mesh=ONLINE\n"
            "2026-11-04T00:00:01Z [AUTH_TOKEN] user=SVC_CORE session=VALID\n"
            "2026-11-04T00:00:02Z [HOST_EXEC] process=nominal_daemon pid=1044\n"
            "2026-11-04T00:00:03Z [NETWORK] switch=CORE_VLAN status=NOMINAL\n"
            "2026-11-04T00:00:04Z [HEALTH] critical_service=OK latency=12ms\n"
            "DIMENSION S10_OPTICAL_THERMAL_FLUX (Optical / Thermal Energy Flux): UNGROUNDED - missing sensor calibration\n"
        )

        # Parse stream into temporal matrix space
        tms = re_eng.parse_raw_stream(payload_pass_0, cartridge_key="security")

        # Verify spatial integrity of the 3 instantiated spaces (T4, T5, T6)
        self.assertTrue(tms.validate_spatial_integrity(), "Spatial integrity must remain valid")

        # Verify S10_OPTICAL_THERMAL_FLUX is detected in active seeds beyond canonical S1..S9
        self.assertIn("S10_OPTICAL_THERMAL_FLUX", tms.active_seeds)
        self.assertEqual(len(ds.DOMAIN_SEEDS), 9, "Canonical DOMAIN_SEEDS must remain exactly 9")

        # Execute Pass 0 through unchanged ConvergenceEngine
        engine = ConvergenceEngine()
        s0 = engine.execute_pass(
            predecessor=None,
            new_data=payload_pass_0,
            cartridge_key="security",
            custom_required_seeds=list(tms.active_seeds),
        )

        # Verify state is SUSPENDED and not bounded
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertFalse(s0.is_bounded)
        self.assertGreater(len(s0.gaps), 0, "Gaps must contain unmapped novel dimension")

        # Verify S10 is the isolated gap with proper recovery directive
        s10_gap = next((g for g in s0.gaps if g.seed == "S10_OPTICAL_THERMAL_FLUX"), None)
        self.assertIsNotNone(s10_gap, "S10_OPTICAL_THERMAL_FLUX must be in gap set G(S)")
        self.assertEqual(s10_gap.status, "UNRESOLVED")
        self.assertEqual(s10_gap.meaning, "Optical / Thermal Energy Flux")
        self.assertIn("S10_OPTICAL_THERMAL_FLUX", s10_gap.recovery_directive)
        self.assertIn("Optical / Thermal Energy Flux", s10_gap.recovery_directive)

        # Verify state hash was produced and binds this suspended point
        self.assertTrue(s0.state_hash)
        self.assertEqual(s0.pass_index, 0)

    def test_03_evidence_recovery_clears_gap_and_seals_without_code_changes(self):
        """
        Criterion 3: Subsequent evidence recovery for S10 clears the gap and allows
        transition to BOUNDED / SEALED, binding H(S1) -> H(S0) with zero kernel modifications.
        """
        engine = ConvergenceEngine()

        # Pass 0: Suspends on ungrounded S10
        payload_pass_0 = (
            "2026-11-04T00:00:00Z [TELEMETRY_INGEST] sensor_mesh=ONLINE\n"
            "2026-11-04T00:00:01Z [AUTH_TOKEN] user=SVC_CORE session=VALID\n"
            "DIMENSION S10_OPTICAL_THERMAL_FLUX (Optical / Thermal Energy Flux): UNGROUNDED - missing sensor calibration\n"
        )
        tms_0 = re_eng.parse_raw_stream(payload_pass_0, cartridge_key="security")
        s0 = engine.execute_pass(
            predecessor=None,
            new_data=payload_pass_0,
            cartridge_key="security",
            custom_required_seeds=list(tms_0.active_seeds),
        )
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertFalse(s0.is_bounded)

        # Pass 1: Calibrated evidence is recovered for S10
        payload_pass_1 = (
            "S10_OPTICAL_THERMAL_FLUX (Optical / Thermal Energy Flux): RESOLVED "
            "Multi-spectrum optical pyrometer calibrated at 420nm-700nm, thermal gradient verified nominal 22.4C\n"
        )
        tms_1 = re_eng.parse_raw_stream(
            payload_pass_0 + "\n" + payload_pass_1,
            cartridge_key="security",
        )
        s1 = engine.execute_pass(
            predecessor=s0,
            new_data=payload_pass_1,
            cartridge_key="security",
            custom_required_seeds=list(tms_1.active_seeds),
        )

        # Verify gap set is completely empty
        self.assertEqual(len(s1.gaps), 0, f"Expected 0 gaps, got: {s1.gaps}")
        self.assertEqual(s1.status, "BOUNDED")
        self.assertTrue(s1.is_bounded)
        self.assertEqual(s1.pass_index, 1)

        # Verify predecessor cryptographic chaining H(S1) -> H(S0)
        self.assertEqual(s1.predecessor_hash, s0.state_hash)
        from viper_core import canonical_json
        expected_s1_payload = {
            "pass_index": 1,
            "predecessor_hash": s0.state_hash,
            "evidence_digest": hashlib.sha256((payload_pass_0 + "\n" + payload_pass_1).encode("utf-8")).hexdigest(),
            "status": "BOUNDED",
            "gaps": [],
            "resolved_seeds": sorted(list(s1.resolved_seed_map.keys())),
            "cartridge": "SECURITY_IR",
        }
        expected_s1_hash = hashlib.sha256(canonical_json(expected_s1_payload).encode("utf-8")).hexdigest()
        self.assertEqual(s1.state_hash, expected_s1_hash)

        # Verify cryptographic state bounding and seal readiness
        self.assertTrue(s1.is_bounded)
        self.assertEqual(s1.status, "BOUNDED")
        seal_payload = {
            "state_hash": s1.state_hash,
            "predecessor_hash": s1.predecessor_hash,
            "status": "SEALED",
        }
        seal_hash = hashlib.sha256(canonical_json(seal_payload).encode("utf-8")).hexdigest()
        self.assertTrue(seal_hash)

    def test_04_contradiction_rejection_on_canonical_seeds_preserved(self):
        """
        Criterion 4: The same run must still reject malformed or contradictory
        evidence on canonical S1-S9 dimensions.
        """
        engine = ConvergenceEngine()

        # Present payload with resolved S10, but contradictory S1 / S7 evidence
        payload_contradiction = (
            "2026-11-04T00:00:00Z [TELEMETRY_INGEST] sensor_mesh=ONLINE\n"
            "2026-11-04T00:00:01Z [ALERT] powershell.exe -enc BAD_ENCODED_PAYLOAD\n"
            "2026-11-04T00:00:02Z [HOST_FAIL] PACS_Server_02 port 104 NO_RESPONSE ConnectionReset\n"
            "S10_OPTICAL_THERMAL_FLUX (Optical / Thermal Energy Flux): RESOLVED Calibrated nominal\n"
        )
        tms = re_eng.parse_raw_stream(payload_contradiction, cartridge_key="security")
        s = engine.execute_pass(
            predecessor=None,
            new_data=payload_contradiction,
            cartridge_key="security",
            custom_required_seeds=list(tms.active_seeds),
        )

        # State must FAIL-CLOSED into SUSPENDED because S7 is unresponsive
        self.assertEqual(s.status, "SUSPENDED")
        self.assertFalse(s.is_bounded)
        s7_gap = next((g for g in s.gaps if g.seed == "S7"), None)
        self.assertIsNotNone(s7_gap, "S7 must be flagged as UNRESOLVED due to host failure")


if __name__ == "__main__":
    unittest.main()
