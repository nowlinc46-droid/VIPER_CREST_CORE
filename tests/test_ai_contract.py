"""
ViperCrest AI Typed Contract Test Suite (tests/test_ai_contract.py).

Validates the strict authority boundary:
  AI proposes coordinates and claims; ViperCrest assigns state and authority.

Tests:
1. Canonical epistemic vocabulary & authority partition.
2. Rejection of AI self-assigned epistemic statuses (ProtocolViolationError).
3. Valid unverified submission types (RAW_CLAIM, OBSERVATION_CANDIDATE, QUESTION, REQUESTED_ACTION).
4. Authoritative execution through the fixed F1-F9 engine and 5-file receipt verification.
5. F7 uncertainty preservation and coordinate-directed question resolution.
6. Persistence of request/response audit envelopes.
7. Core engine byte-invariance (0 modifications to viper_matrix.py, viper_core.py, viper_http.py).
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import ai_contract as aic
import domain_space as ds


class AIContractBoundaryTests(unittest.TestCase):
    def test_01_canonical_vocabulary_and_authority_partition(self):
        """Test 1: Verify authority partition and canonical epistemic constants."""
        self.assertEqual(
            aic.AI_AUTHORITY,
            {
                "translate_input",
                "select_cartridge",
                "request_runtime_evaluation",
                "query_coordinates",
                "explain_sealed_results",
            },
        )
        self.assertEqual(
            aic.VIPERCREST_AUTHORITY,
            {
                "classify_epistemic_state",
                "derive_coordinates",
                "bound_transitions",
                "preserve_f7_uncertainty",
                "seal_results",
            },
        )
        # Disjoint authorities
        self.assertTrue(aic.AI_AUTHORITY.isdisjoint(aic.VIPERCREST_AUTHORITY))

        # Vocabulary matches domain_space
        self.assertEqual(
            ds.HYDRATION_STATES,
            {"OBSERVED", "DERIVED", "POSSIBLE", "CONTRADICTED", "UNRESOLVED"},
        )

    def test_02_rejection_of_ai_self_assigned_epistemic_status(self):
        """Test 2: Rejection of any AI attempt to pre-classify or self-assign epistemic status."""
        # 1. AI attempts to submit observation with explicit status: "OBSERVED"
        bad_envelope_data = {
            "intent": "analyze",
            "cartridge": "security",
            "observations": [
                {
                    "raw_text": "powershell.exe -enc ...",
                    "status": "OBSERVED",  # FORBIDDEN!
                }
            ],
            "requested_action": "matrix",
        }
        with self.assertRaises(aic.ProtocolViolationError) as ctx:
            aic.AIRequestEnvelope.from_dict(bad_envelope_data)
        self.assertIn("AI Authority Breach", str(ctx.exception))

        # 2. AI attempts to smuggle epistemic status in context: "DERIVED"
        bad_context_data = {
            "intent": "analyze",
            "cartridge": "security",
            "observations": [
                {
                    "raw_text": "powershell.exe -enc ...",
                    "context": {"epistemic_state": "DERIVED"},  # FORBIDDEN!
                }
            ],
            "requested_action": "matrix",
        }
        with self.assertRaises(aic.ProtocolViolationError) as ctx:
            aic.AIRequestEnvelope.from_dict(bad_context_data)
        self.assertIn("AI Authority Breach", str(ctx.exception))

        # 3. AI attempts to submit claim with explicit status
        bad_claim_data = {
            "intent": "analyze",
            "cartridge": "security",
            "claims": [
                {
                    "claim_id": "C1",
                    "statement": "Lateral movement confirmed",
                    "status": "OBSERVED",  # FORBIDDEN!
                }
            ],
            "requested_action": "matrix",
        }
        with self.assertRaises(aic.ProtocolViolationError) as ctx:
            aic.AIRequestEnvelope.from_dict(bad_claim_data)
        self.assertIn("AI Authority Breach", str(ctx.exception))

    def test_03_valid_unverified_submission_types(self):
        """Test 3: Valid AI submission containing only permitted unverified types."""
        valid_envelope = aic.AIRequestEnvelope(
            intent="analyze",
            cartridge="security",
            observations=[
                {"raw_text": "2026-11-01T02:17:00Z PACS port 104 NO_RESPONSE", "candidate_state": "PORT_TIMEOUT"}
            ],
            claims=[
                {"claim_id": "CLM-101", "statement": "PACS imaging server failed heartbeat"}
            ],
            questions=[
                {"question_id": "Q-01", "query_text": "Is PACS status resolved or held in F7?", "target_coordinate": "T5:S7"}
            ],
            requested_action="matrix",
        )
        valid_envelope.validate()
        self.assertEqual(valid_envelope.intent, "analyze")
        self.assertEqual(valid_envelope.cartridge, "security")
        self.assertEqual(len(valid_envelope.observations), 1)
        self.assertEqual(len(valid_envelope.claims), 1)
        self.assertEqual(len(valid_envelope.questions), 1)

    def test_04_execution_and_authoritative_classification(self):
        """Test 4: Execute valid envelope; verify ViperCrest assigns epistemic state and verifies receipt."""
        executor = aic.ViperCrestContractExecutor()
        envelope = aic.AIRequestEnvelope(
            intent="analyze",
            cartridge="security",
            observations=[
                {"raw_text": "2026-11-01T02:17:00Z PACS_Server_02 port 104 NO_RESPONSE"}
            ],
            requested_action="matrix",
        )
        response = executor.execute(envelope)

        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(response.cartridge_id, "SECURITY_IR")
        self.assertTrue(response.session_receipt_verified)
        self.assertTrue(response.f7_uncertainty_preserved)

        # Epistemic summary must reflect authoritative classification
        summ = response.epistemic_summary
        self.assertEqual(summ["total_state_cells"], 81)
        self.assertGreater(summ["observed_cells"], 0)
        self.assertGreater(summ["unresolved_f7_cells"], 0)

        # Verify coordinates list
        self.assertEqual(len(response.coordinates_81), 81)
        # S7 at T5 must be UNRESOLVED
        s7_coord = next(c for c in response.coordinates_81 if c["coordinate"] == "T5_COMPOUNDING:S7")
        self.assertEqual(s7_coord["status"], "UNRESOLVED")
        self.assertTrue(s7_coord["contained_in_f7"])

    def test_05_f7_preservation_and_question_resolution(self):
        """Test 5: Submit question about F7 / PACS; verify authoritative explanation."""
        executor = aic.ViperCrestContractExecutor()
        envelope = aic.AIRequestEnvelope(
            intent="query",
            cartridge="security",
            questions=[
                {
                    "question_id": "Q_PACS",
                    "query_text": "Why is PACS unresolved?",
                    "target_coordinate": "T5:S7",
                }
            ],
            requested_action="query",
        )
        response = executor.execute(envelope)

        self.assertEqual(len(response.question_answers), 1)
        qa = response.question_answers[0]
        self.assertEqual(qa["question_id"], "Q_PACS")
        ans = qa["authoritative_answer"]
        self.assertEqual(ans["epistemic_status"], "UNRESOLVED")
        self.assertIn("UNRESOLVED", ans["explanation"])

    def test_06_tamper_evident_request_and_response_logging(self):
        """Test 6: Verify request and response envelopes are persisted to runtime/ai."""
        executor = aic.ViperCrestContractExecutor()
        envelope = aic.AIRequestEnvelope(
            intent="hydrate",
            cartridge="legal",
            observations=[
                {"raw_text": "2026-08-15 Tenant serves Notice of Default citing Section 14.2"}
            ],
            requested_action="hydrate",
        )
        response = executor.execute(envelope)

        req_file = aic.AI_REQUESTS_DIR / f"request_{envelope.request_id}.json"
        resp_file = aic.AI_RESPONSES_DIR / f"response_{envelope.request_id}.json"

        self.assertTrue(req_file.exists(), "Request envelope must be persisted")
        self.assertTrue(resp_file.exists(), "Response envelope must be persisted")

        req_data = json.loads(req_file.read_text(encoding="utf-8"))
        resp_data = json.loads(resp_file.read_text(encoding="utf-8"))

        self.assertEqual(req_data["request_id"], envelope.request_id)
        self.assertEqual(resp_data["request_id"], envelope.request_id)
        self.assertEqual(resp_data["cartridge_id"], "COURTFORGE_LEGAL")

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
