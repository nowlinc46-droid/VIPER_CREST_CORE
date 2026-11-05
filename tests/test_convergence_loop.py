"""
ViperCrest Convergence Loop Test Suite (tests/test_convergence_loop.py).

Validates the full recursive state-recovery loop:
  RECEIVE -> F1-F9 -> TEST -> BOUNDED?
  Yes -> SEAL
  No  -> SUSPEND -> EXPOSE GAP -> RECOVER -> RE-INGEST -> F1-F9 -> TEST AGAIN

Proves the 3 yellow status areas on the build map:
  [#7] UNRESOLVED -> EXACT GAP & RECOVERY REQUEST
  [#8] RECOVERED DATA -> AUTOMATIC RE-INGESTION
  [#9] PREDECESSOR -> SUCCESSOR STATE CHAIN (BOUNDED -> SEAL)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from convergence_engine import ConvergenceEngine, SuccessorState


class ConvergenceLoopTests(unittest.TestCase):

    def setUp(self):
        self.engine = ConvergenceEngine(required_seeds=["S2", "S7"])

    def test_01_single_pass_suspended_isolates_exact_gap(self):
        """Test 1: Incomplete initial seed halts in SUSPENDED and isolates exact missing coordinate."""
        # Supply seed that only satisfies S2 (powershell/execution) but leaves S7 unresolved
        initial_seed = "2026-11-03T14:00:00Z powershell.exe -enc execution_test unresponsive host on port 104"
        
        state_0 = self.engine.execute_pass(
            predecessor=None,
            new_data=initial_seed,
            cartridge_key="security",
            custom_required_seeds=["S2", "S7"],
        )

        self.assertEqual(state_0.pass_index, 0)
        self.assertIsNone(state_0.predecessor_hash)
        self.assertEqual(state_0.status, "SUSPENDED")
        self.assertFalse(state_0.is_bounded)

        # Gap analysis must isolate S7 exactly
        self.assertEqual(len(state_0.gaps), 1)
        gap = state_0.gaps[0]
        self.assertEqual(gap.seed, "S7")
        self.assertEqual(gap.coordinate, "T5_COMPOUNDING:S7")
        self.assertEqual(gap.status, "UNRESOLVED")
        self.assertIn("Coordinate T5_COMPOUNDING:S7", gap.recovery_directive)

    def test_02_two_pass_recursive_convergence_to_bounded_seal(self):
        """Test 2: Two-pass recursive loop chains predecessor hash and converges to BOUNDED."""
        # Pass 0: S2 provided, S7 missing -> SUSPENDED
        initial_seed = "2026-11-03T14:00:00Z powershell.exe -enc execution_test unresponsive host on port 104"
        state_0 = self.engine.execute_pass(
            predecessor=None,
            new_data=initial_seed,
            cartridge_key="security",
            custom_required_seeds=["S2", "S7"],
        )
        self.assertEqual(state_0.status, "SUSPENDED")
        self.assertEqual(len(state_0.gaps), 1)

        # Oracle generates recovered evidence D_1 satisfying S7 discovery
        recovery_d1 = "RESOLVED S7: Secondary seal verified clean and host heartbeat restored."

        # Pass 1: Ingest D_1 with predecessor=state_0
        state_1 = self.engine.execute_pass(
            predecessor=state_0,
            new_data=recovery_d1,
            cartridge_key="security",
            custom_required_seeds=["S2", "S7"],
        )

        # Invariant: Predecessor hash binding
        self.assertEqual(state_1.pass_index, 1)
        self.assertEqual(state_1.predecessor_hash, state_0.state_hash)
        self.assertNotEqual(state_1.state_hash, state_0.state_hash)

        # Invariant: Evidence accumulation
        self.assertEqual(len(state_1.raw_evidence_chain), 2)
        self.assertEqual(state_1.raw_evidence_chain[0], initial_seed)
        self.assertEqual(state_1.raw_evidence_chain[1], recovery_d1)

        # Invariant: Convergence to BOUNDED
        self.assertEqual(len(state_1.gaps), 0)
        self.assertEqual(state_1.status, "BOUNDED")
        self.assertTrue(state_1.is_bounded)
        self.assertTrue(state_1.receipt_verified)

    def test_03_automated_convergence_loop_with_recovery_oracle(self):
        """Test 3: Automated multi-pass convergence loop running to completion."""
        initial_seed = "2026-11-03T14:00:00Z powershell.exe anomalous process with unresponsive telemetry"

        def mock_recovery_oracle(state: SuccessorState) -> str | None:
            # Look at remaining gaps and supply corresponding telemetry
            unresolved_seeds = {g.seed for g in state.gaps}
            if "S7" in unresolved_seeds:
                return "RESOLVED S7: Threat intelligence feed verified artifact hash clean."
            return None

        final_state, history = self.engine.run_convergence_loop(
            initial_data=initial_seed,
            recovery_oracle=mock_recovery_oracle,
            cartridge_key="security",
            max_passes=3,
            required_seeds=["S2", "S7"],
        )

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].status, "SUSPENDED")
        self.assertEqual(history[1].status, "BOUNDED")
        self.assertEqual(final_state.status, "BOUNDED")
        self.assertEqual(final_state.pass_index, 1)
        self.assertEqual(final_state.predecessor_hash, history[0].state_hash)

    def test_04_courtforge_legal_cartridge_convergence(self):
        """Test 4: Recursive convergence applied to CourtForge legal claims cartridge."""
        # Initial complaint: Ingress claim filed, but witness testimony unproduced
        legal_seed_0 = "CASE-2026-991: Tenant Ingress filed claim for breach with unproduced discovery records."

        state_0 = self.engine.execute_pass(
            predecessor=None,
            new_data=legal_seed_0,
            cartridge_key="legal",
            custom_required_seeds=["S1", "S7"],
        )
        self.assertEqual(state_0.cartridge_id, "COURTFORGE_LEGAL")
        self.assertEqual(state_0.status, "SUSPENDED")
        self.assertEqual(len(state_0.gaps), 1)
        self.assertEqual(state_0.gaps[0].seed, "S7")

        # Recover missing discovery (S7)
        legal_recovery_d1 = "RESOLVED S7: Landlord inspection and dispatch tickets produced under subpoena."
        state_1 = self.engine.execute_pass(
            predecessor=state_0,
            new_data=legal_recovery_d1,
            cartridge_key="legal",
            custom_required_seeds=["S1", "S7"],
        )

        self.assertEqual(state_1.pass_index, 1)
        self.assertEqual(state_1.predecessor_hash, state_0.state_hash)
        self.assertEqual(state_1.status, "BOUNDED")
        self.assertTrue(state_1.is_bounded)
        self.assertTrue(state_1.receipt_verified)


if __name__ == "__main__":
    unittest.main()
