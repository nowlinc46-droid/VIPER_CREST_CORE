"""
Unit tests for Domain Space, Matrix over Matrices, and Bounded Hydration.
Verifies spatial integrity, temporal phase coordinates, transition receipts,
and zero-invention epistemic boundaries.
"""
import unittest
from pathlib import Path

import domain_space as ds
import reader_engine as re_eng


class DomainSpaceHydrationTests(unittest.TestCase):
    def test_runtime_stages_invariant(self):
        """F1-F9 runtime stages must remain untouched and invariant."""
        self.assertEqual(
            ds.RUNTIME_STAGES,
            ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9")
        )

    def test_temporal_phases_coordinates(self):
        """Temporal continuum must contain exactly the 9 recovered phases."""
        self.assertEqual(
            ds.TEMPORAL_PHASES,
            (
                "T1_ROOT",
                "T2_VEIL",
                "T3_PATH_IN",
                "T4_STABILITY",
                "T5_COMPOUNDING",
                "T6_REFRACTING",
                "T7_FLAME",
                "T8_PATH_OUT",
                "T9_STONE",
            )
        )

    def test_spatial_integrity(self):
        """Every Space instance must strictly contain S1..S9."""
        space = ds.DomainSpaceInstance(space_id="T0_TEST", phase="T5_COMPOUNDING")
        self.assertTrue(space.validate_spatial_integrity())
        self.assertEqual(set(space.seeds.keys()), set(ds.DOMAIN_SEEDS))

    def test_epistemic_hydration_states(self):
        """Hydration must distinguish OBSERVED, DERIVED, POSSIBLE, CONTRADICTED, UNRESOLVED."""
        tms = ds.TemporalMatrixSpace()
        s5 = ds.DomainSpaceInstance(space_id="T0", phase="T5_COMPOUNDING")
        tms.set_space("T5_COMPOUNDING", s5)

        s4 = ds.DomainSpaceInstance(space_id="T_MINUS_1", phase="T4_STABILITY")
        tms.set_space("T4_STABILITY", s4)
        tms.relationships.append({"phase": "T4_STABILITY", "status": "DERIVED"})

        s6 = ds.DomainSpaceInstance(space_id="T_PLUS_1", phase="T6_REFRACTING")
        tms.set_space("T6_REFRACTING", s6)
        # s6 has no relationship, should be POSSIBLE

        report = tms.construct_hydration_report()
        self.assertEqual(report["T5_COMPOUNDING"], "OBSERVED")
        self.assertEqual(report["T4_STABILITY"], "DERIVED")
        self.assertEqual(report["T6_REFRACTING"], "POSSIBLE")
        self.assertEqual(report["T1_ROOT"], "UNRESOLVED")
        self.assertEqual(report["T9_STONE"], "UNRESOLVED")

    def test_inter_space_transition_receipts(self):
        """Rn = Hash( SPACE(Tn), Delta_n, SPACE(Tn+1), F1:F9 )"""
        tms = ds.TemporalMatrixSpace()
        s4 = ds.DomainSpaceInstance(space_id="T4", phase="T4_STABILITY")
        s5 = ds.DomainSpaceInstance(space_id="T5", phase="T5_COMPOUNDING")
        tms.set_space("T4_STABILITY", s4)
        tms.set_space("T5_COMPOUNDING", s5)

        receipt = tms.compute_inter_space_transition_receipt(
            "T4_STABILITY", "T5_COMPOUNDING", {"delta": "test_transition"}
        )
        self.assertIn("receipt_hash", receipt)
        self.assertEqual(receipt["engine_binding"], "F1:F2:F3:F4:F5:F6:F7:F8:F9")
        self.assertEqual(len(tms.transition_receipts), 1)

    def test_reader_engine_pipeline(self):
        """Air-Gapped Reader parses raw text without execution and emits valid fixture."""
        raw_stream = (
            "2026-11-01T02:16:04Z [EDR] powershell.exe -enc XYZ user=SVC_TEST\n"
            "2026-11-01T02:16:48Z [MED] timeout on Infusion_Gate\n"
            "2026-11-01T02:17:00Z [PING] port 104 NO_RESPONSE\n"
        )
        tms = re_eng.parse_raw_incident_stream(raw_stream)
        self.assertTrue(tms.validate_spatial_integrity())
        self.assertEqual(tms.positions["T5_COMPOUNDING"].seeds["S1"]["state"], "COMPROMISED_TOKEN")
        self.assertEqual(tms.positions["T5_COMPOUNDING"].seeds["S4"]["state"], "DEGRADED")
        self.assertEqual(tms.positions["T5_COMPOUNDING"].seeds["S7"]["state"], "UNRESOLVED_ENDPOINT_B")

        fixture_path = re_eng.emit_matrix_observation_fixture(tms, case_id="test_unit_reader")
        self.assertTrue(fixture_path.exists())


if __name__ == "__main__":
    unittest.main()
