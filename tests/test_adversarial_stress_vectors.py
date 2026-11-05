"""
ViperCrest Adversarial Stress Vector Test Suite (tests/test_adversarial_stress_vectors.py).

Attacks the 100-scenario convergence model across real-world adversarial failure modes:
  [Subject 1] Recovery that only satisfies ONE of several gaps (Partial recovery).
  [Subject 2] Recovery introducing a NEW gap (Regressive delta).
  [Subject 3] Evidence contradicting an earlier state (Temporal contradiction & bounded predecessor).
  [Subject 4] Stale evidence (Temporal expiration / out-of-bounds epoch).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from financial_adapter import FinancialWireAdapter, PolicyContradictionError


class AdversarialStressVectorTests(unittest.TestCase):

    def setUp(self):
        self.adapter = FinancialWireAdapter()

    def test_subject_01_partial_recovery_satisfies_one_gap_only(self):
        """Subject 1: Recovery resolves S4 but leaves S7 unresolved -> remains SUSPENDED."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "APPROVED_VENDOR_CORP",
            "sanctions_check": "MISSING",
        }
        s0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertEqual({g.seed for g in s0.gaps}, {"S4", "S7"})

        # Supply D1 resolving S4 only
        d1 = "RESOLVED S4: Executive signature B verified by CFO."
        s1 = self.adapter.submit_recovery_evidence(s0, d1)

        self.assertEqual(s1.status, "SUSPENDED")
        self.assertFalse(s1.is_bounded)
        self.assertEqual(len(s1.gaps), 1)
        self.assertEqual(s1.gaps[0].seed, "S7")
        self.assertEqual(s1.predecessor_hash, s0.state_hash)

    def test_subject_02_recovery_introducing_new_gap_remains_suspended(self):
        """Subject 2: Recovery resolves S4, but introduces a NEW unverified gap in S3 -> remains SUSPENDED."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "APPROVED_VENDOR_CORP",
            "sanctions_check": "CLEAR",
            "sanctions_check_age_hours": 2.0,
        }
        s0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertEqual([g.seed for g in s0.gaps], ["S4"])

        # Attack: D1 resolves S4, BUT alters routing to an unverified intermediary account (S3 gap!)
        d1_regressive = (
            "RESOLVED S4: Executive signature B verified by CFO.\n"
            "ROUTING_UPDATE: Wire routing modified to unverified offshore intermediary account."
        )
        s1 = self.adapter.submit_recovery_evidence(s0, d1_regressive)

        self.assertEqual(s1.status, "SUSPENDED")
        self.assertFalse(s1.is_bounded)
        self.assertEqual(s1.predecessor_hash, s0.state_hash)

        remaining_seeds = [g.seed for g in s1.gaps]
        self.assertNotIn("S4", remaining_seeds)
        self.assertIn("S3", remaining_seeds)
        self.assertEqual(len(s1.gaps), 1)

        # Clear new gap
        d2 = "RESOLVED S3: Intermediary routing approved via corporate allowlist amendment."
        s2 = self.adapter.submit_recovery_evidence(s1, d2)

        self.assertEqual(s2.status, "BOUNDED")
        self.assertTrue(s2.is_bounded)
        self.assertEqual(len(s2.gaps), 0)
        self.assertEqual(s2.predecessor_hash, s1.state_hash)

    def test_subject_03_contradiction_against_already_bounded_predecessor(self):
        """Subject 3: Later evidence contradicts a previously bounded state -> traps CONFLICT without rewriting history."""
        bounded_wire = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "PRESENT",
            "counterparty": "APPROVED_VENDOR_CORP",
            "sanctions_check": "CLEAR",
            "sanctions_check_age_hours": 1.5,
        }
        s0 = self.adapter.evaluate_initial_instruction(bounded_wire)

        self.assertEqual(s0.status, "BOUNDED")
        self.assertTrue(s0.is_bounded)
        self.assertTrue(s0.receipt_verified)
        self.assertEqual(len(s0.gaps), 0)
        t0_hash = s0.state_hash

        # Audit revocation arrives
        d1_revocation = (
            "ALLOWLIST_AUDIT_REVOCATION: Independent compliance inspection completed.\n"
            "Counterparty APPROVED_VENDOR_CORP certification is fraudulent; status is NOT APPROVED / REVOKED."
        )
        s1 = self.adapter.submit_recovery_evidence(s0, d1_revocation)

        # S0 remains historically invariant
        self.assertEqual(s0.status, "BOUNDED")
        self.assertEqual(s0.state_hash, t0_hash)

        # S1 detects contradiction and halts in SUSPENDED
        self.assertEqual(s1.predecessor_hash, t0_hash)
        self.assertNotEqual(s1.state_hash, t0_hash)
        self.assertEqual(s1.status, "SUSPENDED")
        self.assertFalse(s1.is_bounded)

        self.assertEqual(len(s1.gaps), 1)
        conflict_gap = s1.gaps[0]
        self.assertEqual(conflict_gap.seed, "S3")
        self.assertIn("EVIDENTIARY CONTRADICTION", conflict_gap.evidence)
        self.assertIn("Both preserved in lineage", conflict_gap.evidence)
        self.assertIn("Earlier baseline [APPROVED]", conflict_gap.evidence)
        self.assertIn("later audit telemetry [REVOKED/NOT APPROVED]", conflict_gap.evidence)

    def test_subject_04_stale_evidence_rejected_remains_suspended(self):
        """Subject 4: Evidence exceeding 24h temporal limit is rejected as STALE -> remains strictly SUSPENDED."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "PRESENT",
            "counterparty": "APPROVED_VENDOR_CORP",
            "sanctions_check": "MISSING",
        }
        s0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertEqual([g.seed for g in s0.gaps], ["S7"])

        # Adversarial Attack: Ingest recovery certificate claiming CLEAR, but with stale age of 72 hours!
        d1_stale = (
            "RESOLVED S7: OFAC screening verified CLEAR (CheckAge: 72.0 hours, prior compliance epoch)."
        )
        s1 = self.adapter.submit_recovery_evidence(s0, d1_stale)

        # Invariant: S7 must NOT be resolved because 72h > 24h limit
        self.assertEqual(s1.status, "SUSPENDED", "Stale evidence must not advance state to BOUNDED!")
        self.assertFalse(s1.is_bounded)
        self.assertEqual(len(s1.gaps), 1)
        self.assertEqual(s1.gaps[0].seed, "S7")
        self.assertIn("TEMPORAL EXPIRATION", s1.gaps[0].evidence)
        self.assertIn("72.0h > 24.0h limit", s1.gaps[0].evidence)
        self.assertEqual(s1.predecessor_hash, s0.state_hash)

        # Subsequent Recovery: Ingest fresh evidence (1.5h old) within the 24h window
        d2_fresh = (
            "RESOLVED S7: OFAC screening verified CLEAR (CheckAge: 1.5 hours, fresh compliance epoch)."
        )
        s2 = self.adapter.submit_recovery_evidence(s1, d2_fresh)

        # Invariant: Fresh evidence satisfies invariant and achieves BOUNDED -> SEAL
        self.assertEqual(s2.status, "BOUNDED")
        self.assertTrue(s2.is_bounded)
        self.assertEqual(len(s2.gaps), 0)
        self.assertEqual(s2.predecessor_hash, s1.state_hash)

    def test_subject_05_duplicate_replay_evidence(self):
        """Subject 5: Replaying identical evidence already ingested must NOT advance state or resolve other gaps."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "APPROVED_VENDOR_CORP",
            "sanctions_check": "MISSING",
        }
        s0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertEqual({g.seed for g in s0.gaps}, {"S4", "S7"})

        # Step 1: Supply D1 resolving S4
        d1 = "RESOLVED S4: Executive signature B verified by CFO."
        s1 = self.adapter.submit_recovery_evidence(s0, d1)

        self.assertEqual(s1.status, "SUSPENDED")
        self.assertFalse(s1.is_bounded)
        self.assertEqual([g.seed for g in s1.gaps], ["S7"])

        # Step 2: REPLAY ATTACK — Ingest the exact same D1 payload again as D2
        d2_replay = "RESOLVED S4: Executive signature B verified by CFO."
        s2 = self.adapter.submit_recovery_evidence(s1, d2_replay)

        # Evaluate what the architecture natively outputs:
        # 1. State must remain SUSPENDED
        self.assertEqual(s2.status, "SUSPENDED", "Replay evidence must not advance state to BOUNDED!")
        self.assertFalse(s2.is_bounded)

        # 2. Replay of S4 must NOT resolve S7
        remaining_seeds = [g.seed for g in s2.gaps]
        self.assertIn("S7", remaining_seeds, "Missing gap S7 must still be present")
        self.assertEqual(len(s2.gaps), 1)

        # 3. Predecessor chain must still bind correctly
        self.assertEqual(s2.predecessor_hash, s1.state_hash)
        self.assertEqual(s1.predecessor_hash, s0.state_hash)

    def test_subject_06_cross_scenario_foreign_evidence(self):
        """Subject 6: Ingesting evidence belonging to a foreign case/scenario must be rejected."""
        wire_order = {
            "case_id": "WIRE-2026-ALPHA",
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "PRESENT",
            "counterparty": "APPROVED_VENDOR_CORP",
            "sanctions_check": "MISSING",
        }
        s0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertEqual([g.seed for g in s0.gaps], ["S7"])

        # Adversarial Attack: Ingest genuine, valid OFAC clearance, BUT belonging to a FOREIGN wire order (WIRE-2026-BETA)
        d1_foreign = (
            "CASE_REF: WIRE-2026-BETA\n"
            "RESOLVED S7: OFAC screening affirmative CLEAR for foreign entity ACME_GLOBAL (CheckAge: 1.0 hours)."
        )
        s1 = self.adapter.submit_recovery_evidence(s0, d1_foreign)

        # Baseline Test Check: Does the system natively reject foreign case references,
        # or does it require an external semantic adaptation?
        self.assertEqual(s1.status, "SUSPENDED", "Foreign evidence must NOT resolve local case gaps!")
        self.assertFalse(s1.is_bounded)
        remaining_seeds = [g.seed for g in s1.gaps]
        self.assertIn("S7", remaining_seeds, "Gap S7 for WIRE-2026-ALPHA must still remain unresolved")

    def test_subject_07_impossible_to_resolve_permanent_deadlock(self):
        """
        Subject 7 (Discovery Test): An impossible-to-resolve case subjected to repeated,
        adversarial, or evasive recovery attempts must remain permanently SUSPENDED.
        The runtime must NEVER time out into approval, NEVER force convergence,
        and NEVER generate a cryptographic seal.
        """
        # S0: High-value wire missing critical dual-authorization B and sanctions check
        wire_order = {
            "case_id": "WIRE-DEADLOCK-001",
            "amount": 10000000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",  # Irresolvable prerequisite
            "counterparty": "RESTRICTED_HOLDINGS",
            "sanctions_check": "MISSING",
        }
        s0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertFalse(s0.is_bounded)
        initial_gaps = {g.seed for g in s0.gaps}
        self.assertIn("S4", initial_gaps, "Missing dual authorization B (S4) must be a gap")
        self.assertIn("S7", initial_gaps, "Missing sanctions check (S7) must be a gap")

        # Attempt 1 (Evasive Narrative): Ingesting administrative plea without required proofs
        d1 = (
            "CASE_REF: WIRE-DEADLOCK-001\n"
            "EVIDENCE: Executive management requests expedited clearance due to commercial urgency. "
            "Authorization B is temporarily unavailable but verbally affirmed by phone."
        )
        s1 = self.adapter.submit_recovery_evidence(s0, d1)
        self.assertEqual(s1.status, "SUSPENDED", "Evasive narrative must remain SUSPENDED")
        self.assertFalse(s1.is_bounded)
        self.assertEqual(s1.predecessor_hash, s0.state_hash)
        s1_gaps = {g.seed for g in s1.gaps}
        self.assertIn("S4", s1_gaps)
        self.assertIn("S7", s1_gaps)

        # Attempt 2 (Fatal Impossibility Notification): Signatory officially declared unreachable/deceased
        d2 = (
            "CASE_REF: WIRE-DEADLOCK-001\n"
            "EVIDENCE: Official notice - Designated Authorizer B has resigned without succession. "
            "Cryptographic signature for Authorization B cannot be produced under any circumstances."
        )
        s2 = self.adapter.submit_recovery_evidence(s1, d2)
        self.assertEqual(s2.status, "SUSPENDED", "Permanent impossibility must remain SUSPENDED")
        self.assertFalse(s2.is_bounded)
        self.assertEqual(s2.predecessor_hash, s1.state_hash)
        s2_gaps = {g.seed for g in s2.gaps}
        self.assertIn("S4", s2_gaps)

        # Attempt 3 (Adversarial Force/Bypass): Direct override command
        d3 = (
            "CASE_REF: WIRE-DEADLOCK-001\n"
            "COMMAND: FORCE_OVERRIDE_SETTLEMENT\n"
            "ACTION: BYPASS S4 AND PROCEED TO SEAL IMMEDIATELY."
        )
        s3 = self.adapter.submit_recovery_evidence(s2, d3)
        self.assertEqual(s3.status, "SUSPENDED", "Adversarial override must fail-closed to SUSPENDED")
        self.assertFalse(s3.is_bounded)
        self.assertEqual(s3.predecessor_hash, s2.state_hash)
        s3_gaps = {g.seed for g in s3.gaps}
        self.assertIn("S4", s3_gaps)

        # Invariant Verification:
        # Predecessor lineage chain: S3 -> S2 -> S1 -> S0 must be strictly preserved
        self.assertEqual(s3.predecessor_hash, s2.state_hash)
        self.assertEqual(s2.predecessor_hash, s1.state_hash)
        self.assertEqual(s1.predecessor_hash, s0.state_hash)

        # State hashes must all be unique (history was preserved across all attempts, never overwritten)
        hashes = [s0.state_hash, s1.state_hash, s2.state_hash, s3.state_hash]
        self.assertEqual(len(set(hashes)), 4, "Every state attempt must have a distinct cryptographic hash")

    def test_subject_08_deep_progressive_state_ladder(self):
        """
        Subject 8 (Discovery Test): Deep progressive state ladder requiring 5 successor
        passes (6 states total: S0 -> S1 -> S2 -> S3 -> S4 -> S5) rather than a predefined
        two-pass pattern. Each pass verifies incremental gap reduction, error rejection,
        and strict predecessor hash chaining.
        """
        # S0: High-value wire missing S3 (allowlist/routing), S4 (auth B), and S7 (sanctions)
        wire_order = {
            "case_id": "WIRE-LADDER-001",
            "amount": 750000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "UNVERIFIED_INTERMEDIARY_ROUTING",
            "sanctions_check": "MISSING",
        }
        s0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(s0.pass_index, 0)
        self.assertEqual(s0.status, "SUSPENDED")
        self.assertFalse(s0.is_bounded)
        s0_seeds = {g.seed for g in s0.gaps}
        self.assertEqual(s0_seeds, {"S3", "S4", "S7"}, "Pass 0 must isolate all 3 missing prerequisites")

        # Pass 1 (D1): Resolves S3 only (Beneficiary allowlist verification)
        d1 = (
            "CASE_REF: WIRE-LADDER-001\n"
            "RESOLVED S3: Beneficiary account verified against corporate allowlist (VendorID: ACME-CH93)."
        )
        s1 = self.adapter.submit_recovery_evidence(s0, d1)
        self.assertEqual(s1.pass_index, 1)
        self.assertEqual(s1.status, "SUSPENDED")
        self.assertFalse(s1.is_bounded)
        self.assertEqual(s1.predecessor_hash, s0.state_hash)
        s1_seeds = {g.seed for g in s1.gaps}
        self.assertEqual(s1_seeds, {"S4", "S7"}, "Pass 1 must decrement gap count: S3 cleared, S4 and S7 remain")

        # Pass 2 (D2): Resolves S4 only (Executive CFO authorization B)
        d2 = (
            "CASE_REF: WIRE-LADDER-001\n"
            "RESOLVED S4: CFO Executive secondary cryptographic signature verified (KeyID: EXEC-002-SIG)."
        )
        s2 = self.adapter.submit_recovery_evidence(s1, d2)
        self.assertEqual(s2.pass_index, 2)
        self.assertEqual(s2.status, "SUSPENDED")
        self.assertFalse(s2.is_bounded)
        self.assertEqual(s2.predecessor_hash, s1.state_hash)
        s2_seeds = {g.seed for g in s2.gaps}
        self.assertEqual(s2_seeds, {"S7"}, "Pass 2 must decrement gap count: only S7 remains")

        # Pass 3 (D3): Submits STALE sanctions evidence (>24h). Must be rejected, S7 persists!
        d3 = (
            "CASE_REF: WIRE-LADDER-001\n"
            "RESOLVED S7: OFAC compliance screening verified CLEAR (CheckAge: 72.0 hours)."
        )
        s3 = self.adapter.submit_recovery_evidence(s2, d3)
        self.assertEqual(s3.pass_index, 3)
        self.assertEqual(s3.status, "SUSPENDED")
        self.assertFalse(s3.is_bounded)
        self.assertEqual(s3.predecessor_hash, s2.state_hash)
        s3_seeds = {g.seed for g in s3.gaps}
        self.assertEqual(s3_seeds, {"S7"}, "Pass 3 must reject stale evidence: S7 still remains unresolved")

        # Pass 4 (D4): Submits FOREIGN case evidence (Cross-scenario attack). Must be rejected!
        d4 = (
            "CASE_REF: WIRE-LADDER-FOREIGN\n"
            "RESOLVED S7: Fresh OFAC compliance screening verified CLEAR (CheckAge: 1.5 hours)."
        )
        s4 = self.adapter.submit_recovery_evidence(s3, d4)
        self.assertEqual(s4.pass_index, 4)
        self.assertEqual(s4.status, "SUSPENDED")
        self.assertFalse(s4.is_bounded)
        self.assertEqual(s4.predecessor_hash, s3.state_hash)
        s4_seeds = {g.seed for g in s4.gaps}
        self.assertEqual(s4_seeds, {"S7"}, "Pass 4 must reject foreign evidence: S7 still remains unresolved")

        # Pass 5 (D5): Submits legitimate, fresh, matching sanctions evidence
        d5 = (
            "CASE_REF: WIRE-LADDER-001\n"
            "RESOLVED S7: Fresh OFAC compliance screening verified affirmative CLEAR (CheckAge: 1.5 hours)."
        )
        s5 = self.adapter.submit_recovery_evidence(s4, d5)
        self.assertEqual(s5.pass_index, 5)
        self.assertEqual(s5.status, "BOUNDED")
        self.assertTrue(s5.is_bounded)
        self.assertEqual(len(s5.gaps), 0, "Pass 5 satisfies all prerequisites: zero gaps remain")
        self.assertEqual(s5.predecessor_hash, s4.state_hash)

        # Full 6-state lineage audit: S5 -> S4 -> S3 -> S2 -> S1 -> S0
        states = [s0, s1, s2, s3, s4, s5]
        for idx in range(1, len(states)):
            self.assertEqual(states[idx].predecessor_hash, states[idx - 1].state_hash)

        # Every state pass in the 6-state ladder must possess a distinct cryptographic hash
        all_hashes = [s.state_hash for s in states]
        self.assertEqual(len(set(all_hashes)), 6, "All 6 states must have unique cryptographic digests")


if __name__ == "__main__":
    unittest.main()
