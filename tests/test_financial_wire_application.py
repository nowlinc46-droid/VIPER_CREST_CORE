"""
ViperCrest Third-Domain Universality Proof: Corporate Treasury Settlement (FP-001).

Validates that the FROZEN ViperCrest kernel (fixed F1-F9, receipts, WAL, convergence loop)
governs an entirely new, non-cybersecurity, non-legal domain without modifying a single
byte of the kernel code.

Tests:
1. Pass 0: Dual-gap suspension (S4 Second Auth + S7 OFAC Clearance).
2. Valid Recovery: Successor state binds S0 hash, clears G0, converges to BOUNDED -> SEAL.
3. Negative Recovery: Invalid/irrelevant evidence keeps state in SUSPENDED.
4. Contradictory Recovery: Sanctions BLOCKED triggers hard refusal / contradiction error.
5. Cryptographic Attestation: Kernel files SHA-256 remain bit-for-bit invariant.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from financial_adapter import FinancialWireAdapter, PolicyContradictionError

# Baseline SHA-256 hashes of the frozen kernel components
FROZEN_KERNEL_HASHES = {
    "convergence_engine.py": "4AC3936D8915EF7F20B474C601F3444259F721B3F910C7D6CBE84608E9E33E18",
    "viper_matrix.py": "7498B5D192687EB8C2E5087390371B6ACD6A487BB9723968834D9F25A83474C3",
    "viper_core.py": "09B40E86BACF816752FC9BC35C4487A4A551A160D8B5D3B6A06A68E7B5FC2457",
    "viper_http.py": "A6F570EDDD4344ED303C90ECA6BAA41F01A5F9AAF14C2DF7DF6FC55EEEE635EA",
}


def compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class FinancialWireUniversalityTests(unittest.TestCase):

    def setUp(self):
        self.adapter = FinancialWireAdapter()

    def test_01_pass0_high_value_wire_suspends_and_isolates_exact_gaps(self):
        """Test 1: $250k wire with 1 signature and no OFAC halts in SUSPENDED with G0 = {S4, S7}."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "APPROVED_VENDOR_CORP_IBAN_CH93",
            "sanctions_check": "MISSING",
            "sanctions_check_age_hours": None,
        }

        state_0 = self.adapter.evaluate_initial_instruction(wire_order)

        self.assertEqual(state_0.pass_index, 0)
        self.assertIsNone(state_0.predecessor_hash)
        self.assertEqual(state_0.status, "SUSPENDED")
        self.assertFalse(state_0.is_bounded)

        # Invariant: Must isolate exactly S4 (Secondary Auth) and S7 (Sanctions)
        isolated_seeds = {g.seed for g in state_0.gaps}
        self.assertEqual(isolated_seeds, {"S4", "S7"})

        for gap in state_0.gaps:
            self.assertEqual(gap.status, "UNRESOLVED")
            self.assertIn("UNRESOLVED", gap.recovery_directive)

    def test_02_valid_recovery_converges_to_bounded_settlement_seal(self):
        """Test 2: Submitting D1 satisfying S4 and S7 chains predecessor hash and seals settlement."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "APPROVED_VENDOR_CORP_IBAN_CH93",
            "sanctions_check": "MISSING",
        }
        state_0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(state_0.status, "SUSPENDED")

        # Supply recovery evidence D1 satisfying both S4 and S7
        d1_evidence = (
            "RESOLVED S4: CFO Executive secondary cryptographic signature verified (KeyID: EXEC-002-SIG)\n"
            "RESOLVED S7: OFAC DowJones compliance screening verified CLEAR (CheckAge: 2.1 hours)"
        )

        state_1 = self.adapter.submit_recovery_evidence(state_0, d1_evidence)

        # Invariant: Predecessor hash binding S0 -> S1
        self.assertEqual(state_1.pass_index, 1)
        self.assertEqual(state_1.predecessor_hash, state_0.state_hash)
        self.assertNotEqual(state_1.state_hash, state_0.state_hash)

        # Invariant: G1 = empty set -> BOUNDED -> SEAL
        self.assertEqual(len(state_1.gaps), 0)
        self.assertEqual(state_1.status, "BOUNDED")
        self.assertTrue(state_1.is_bounded)
        self.assertTrue(state_1.receipt_verified)

    def test_03_negative_recovery_with_wrong_evidence_remains_suspended(self):
        """Test 3: Submitting invalid/irrelevant evidence does not resolve gaps; state stays SUSPENDED."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "APPROVED_VENDOR_CORP_IBAN_CH93",
            "sanctions_check": "MISSING",
        }
        state_0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(state_0.status, "SUSPENDED")

        # Supply irrelevant data (weather report / network ping)
        irrelevant_d1 = (
            "SYSTEM_LOG: Chicago data center temperature nominal at 68F.\n"
            "PING_TELEMETRY: SWIFT gateway latency is 14ms."
        )

        state_1 = self.adapter.submit_recovery_evidence(state_0, irrelevant_d1)

        # Invariant: Predecessor bound, but gaps STILL unresolved
        self.assertEqual(state_1.pass_index, 1)
        self.assertEqual(state_1.predecessor_hash, state_0.state_hash)
        self.assertEqual(state_1.status, "SUSPENDED")
        self.assertFalse(state_1.is_bounded)
        self.assertEqual(len(state_1.gaps), 2)

    def test_04_contradictory_recovery_sanctions_blocked_refuses_settlement(self):
        """Test 4: When sanctions check reports BLOCKED, engine detects contradiction and rejects release."""
        wire_order = {
            "amount": 250000.00,
            "currency": "USD",
            "authorization_A": "PRESENT",
            "authorization_B": "MISSING",
            "counterparty": "SUSPICIOUS_OFFSHORE_ENTITY",
            "sanctions_check": "MISSING",
        }
        state_0 = self.adapter.evaluate_initial_instruction(wire_order)
        self.assertEqual(state_0.status, "SUSPENDED")

        # Supply evidence reporting counterparty is matched on SDN list (BLOCKED)
        blocked_evidence = (
            "SANCTIONS_STATUS: BLOCKED - Entity matched on OFAC SDN Sanctions List. Wire frozen."
        )

        with self.assertRaises(PolicyContradictionError) as ctx:
            self.adapter.submit_recovery_evidence(state_0, blocked_evidence)

        self.assertIn("SDN sanctions list", str(ctx.exception))
        self.assertIn("PERMANENTLY FORBIDDEN", str(ctx.exception))

    def test_05_cryptographic_attestation_frozen_kernel_invariance(self):
        """Test 5: Verify that the frozen kernel files have not changed by a single bit."""
        for filename, expected_sha256 in FROZEN_KERNEL_HASHES.items():
            current_path = VIPER_ROOT / filename
            current_sha256 = compute_file_sha256(current_path)
            self.assertEqual(
                current_sha256,
                expected_sha256,
                f"KERNEL INVARIANT VIOLATION: {filename} was modified during financial experiment!",
            )


if __name__ == "__main__":
    unittest.main()
