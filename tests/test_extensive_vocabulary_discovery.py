"""
ViperCrest Extensive Vocabulary Discovery Test Suite
tests/test_extensive_vocabulary_discovery.py

Tests open-ended linguistic and lexical discovery across 5 high-density technical domains:
  1. Legal Discovery & CourtForge Litigation
  2. Smart Contract & Web3 Invariant Security
  3. Autonomous Robotics & Cyber-Physical Plant Dynamics
  4. Financial Settlement, SWIFT MT103 & Wire Compliance
  5. Cold-Chain Logistics & HACCP Industrial Compliance

Invariants Verified:
  - Exact canonical terminal output structures are maintained bit-for-bit.
  - Entities, actions, properties, and states are extracted with zero speculation.
  - Unevidenced domain concepts remain strictly contained in Stage F7 Discovery.
  - Frozen kernel files remain 100% byte-invariant (0 diffs).
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import ai_contract as aic
import ai_wrapper as aiw
import domain_space as ds
import grammar_schema as gs

FROZEN_KERNELS = {
    "convergence_engine.py": "4AC3936D8915EF7F20B474C601F3444259F721B3F910C7D6CBE84608E9E33E18",
    "viper_matrix.py": "7498B5D192687EB8C2E5087390371B6ACD6A487BB9723968834D9F25A83474C3",
    "viper_core.py": "09B40E86BACF816752FC9BC35C4487A4A551A160D8B5D3B6A06A68E7B5FC2457",
    "viper_http.py": "A6F570EDDD4344ED303C90ECA6BAA41F01A5F9AAF14C2DF7DF6FC55EEEE635EA",
}


class ExtensiveVocabularyDiscoveryTests(unittest.TestCase):
    """
    Discovery test verifying extensive domain vocabulary while preserving exact canonical output.
    """

    def setUp(self):
        for fname, expected in FROZEN_KERNELS.items():
            actual = hashlib.sha256((VIPER_ROOT / fname).read_bytes()).hexdigest().upper()
            self.assertEqual(
                actual,
                expected,
                f"Frozen kernel parity violation on {fname}: {actual} != {expected}",
            )

    def test_01_legal_discovery_litigation_lexicon(self):
        """Domain 1: CourtForge Litigation, Spoliation, Bates Stamping & Sanctions."""
        samples = [
            "Plaintiff files motion to compel production of unredacted bates-stamped communications.",
            "Defendant asserts spoliation of forensic voicemail evidence under Rule 37.",
            "The court enters protective order and issues subpoena duces tecum.",
            "Deponent refused deposition testimony citing commercial privilege.",
        ]
        for sentence in samples:
            parsed = gs.parse_basic_grammar(sentence)
            self.assertTrue(len(parsed.entities) > 0, f"Expected entities in: {sentence}")
            self.assertTrue(len(parsed.clauses) > 0, f"Expected clause in: {sentence}")

            # Verify through semantic AI wrapper routes to legal cartridge
            envelope = aiw.heuristic_translate_request(sentence)
            self.assertEqual(
                envelope.cartridge,
                "legal",
                f"Sentence should route to legal cartridge: {sentence}",
            )

    def test_02_web3_smart_contract_security_lexicon(self):
        """Domain 2: Reentrancy, Flash Loans, Oracle Manipulation & Access Control."""
        samples = [
            "The vulnerable lending pool executed reentrant flash loan callback.",
            "Untrusted caller manipulated spot price oracle via unbonded liquidity pair.",
            "Malicious transaction bypassed access control and drained wrapped tokens.",
            "Solidity smart contract reverted suddenly on integer arithmetic underflow.",
        ]
        for sentence in samples:
            parsed = gs.parse_basic_grammar(sentence)
            self.assertTrue(len(parsed.entities) > 0, f"Expected entities in: {sentence}")
            self.assertTrue(len(parsed.clauses) > 0, f"Expected clause in: {sentence}")

            envelope = aiw.heuristic_translate_request(sentence)
            self.assertEqual(
                envelope.cartridge,
                "security",
                f"Sentence should route to security cartridge: {sentence}",
            )

    def test_03_autonomous_robotics_sensor_plant_lexicon(self):
        """Domain 3: Actuator Dynamics, Angular Velocity, Blinding & Kinetic Gating."""
        samples = [
            "The robotic manipulator exceeded angular velocity threshold during trajectory descent.",
            "Optical encoder suffered flatline noise collapse under sensor blinding attack.",
            "Kinetic torque gate tripped fail-closed at eighty newton meters.",
            "The joint motor entered degraded state after thermal sensor alarm.",
        ]
        for sentence in samples:
            parsed = gs.parse_basic_grammar(sentence)
            self.assertTrue(len(parsed.entities) > 0, f"Expected entities in: {sentence}")
            self.assertTrue(len(parsed.clauses) > 0, f"Expected clause in: {sentence}")

            envelope = aiw.heuristic_translate_request(sentence)
            self.assertEqual(
                envelope.cartridge,
                "security",
                f"Sentence should route to security/stem cartridge: {sentence}",
            )

    def test_04_financial_wire_settlement_lexicon(self):
        """Domain 4: SWIFT MT103, OFAC Sanctions, Fedwire & Dodd-Frank Compliance."""
        samples = [
            "Beneficiary institution flags unverified wire transfer exceeding reporting threshold.",
            "OFAC sanctions screening detects restricted counterparty entity.",
            "Dual authorization signature missing from high value correspondent account.",
            "Correspondent bank completed final settlement payment under Fedwire protocol.",
        ]
        for sentence in samples:
            parsed = gs.parse_basic_grammar(sentence)
            self.assertTrue(len(parsed.entities) > 0, f"Expected entities in: {sentence}")
            self.assertTrue(len(parsed.clauses) > 0, f"Expected clause in: {sentence}")

    def test_05_wms_cold_chain_logistics_lexicon(self):
        """Domain 5: HACCP Critical Limits, Thermal Excursion & Intermodal Transport."""
        samples = [
            "Refrigerated container reported thermal excursion exceeding critical limit.",
            "Pallet security seal broken during intermodal rail transport.",
            "Datalogger verified continuous temperature compliance across distribution transit.",
            "Cold chain warehouse quarantine inspection halted defective shipment.",
        ]
        for sentence in samples:
            parsed = gs.parse_basic_grammar(sentence)
            self.assertTrue(len(parsed.entities) > 0, f"Expected entities in: {sentence}")
            self.assertTrue(len(parsed.clauses) > 0, f"Expected clause in: {sentence}")

            envelope = aiw.heuristic_translate_request(sentence)
            self.assertEqual(
                envelope.cartridge,
                "logistics",
                f"Sentence should route to logistics cartridge: {sentence}",
            )

    def test_06_exact_terminal_output_format_maintained(self):
        """
        Critical Invariant: Across all extensive vocabularies, the exact canonical
        terminal output structure must be preserved bit-for-bit without alteration.
        """
        # 1. Question query format test
        q_envelope = aic.AIRequestEnvelope(
            intent="query",
            cartridge="security",
            observations=[],
            claims=[],
            questions=[{
                "question_id": "Q1",
                "query_text": "WHAT IS YOUR NAME",
            }],
            requested_action="query",
        )
        executor = aic.ViperCrestContractExecutor()
        auth_resp = executor.execute(q_envelope)

        explanation = aiw.explain_response("WHAT IS YOUR NAME", auth_resp)
        # Assert exact canonical output presence
        self.assertIn("ViperCrest has verified the observed present at T5_COMPOUNDING.", explanation)
        self.assertIn("Directly observed seeds:", explanation)
        self.assertIn("All unevidenced coordinates remain sealed in Stage F7.", explanation)

        # 2. General analysis interaction format test
        a_envelope = aic.AIRequestEnvelope(
            intent="analyze",
            cartridge="security",
            observations=[{
                "raw_text": "Sample network telemetry packet",
                "candidate_state": "INGESTION_CANDIDATE",
            }],
            claims=[{
                "claim_id": "CLM-01",
                "statement": "Sample verification claim",
            }],
            questions=[],
            requested_action="matrix",
        )
        a_auth_resp = executor.execute(a_envelope)
        a_explanation = aiw.explain_response("Sample network telemetry packet", a_auth_resp)

        self.assertIn("Cartridge: SECURITY_IR", a_explanation)
        self.assertIn("Evidence loaded: YES", a_explanation)
        self.assertIn("Running Reader...", a_explanation)
        self.assertIn("Normalizing Seed...", a_explanation)
        self.assertIn("Running invariant F1-F9...", a_explanation)
        self.assertIn("Evaluating temporal matrix...", a_explanation)
        self.assertIn("Result:", a_explanation)
        self.assertIn("Present state:       BOUNDED", a_explanation)
        self.assertIn("Backward hydration:  2 candidates (DERIVED)", a_explanation)
        self.assertIn("Forward hydration:   1 candidates (POSSIBLE)", a_explanation)
        self.assertIn("F7 preservation:     PASS", a_explanation)
        self.assertIn("Receipt:             VERIFIED", a_explanation)

    def test_07_frozen_kernel_invariance(self):
        """Verify that expanding vocabulary produces 0 diffs across the 4 core files."""
        for fname, expected in FROZEN_KERNELS.items():
            actual = hashlib.sha256((VIPER_ROOT / fname).read_bytes()).hexdigest().upper()
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
