"""
Material Matrix Validation Test Suite (tests/test_material_matrix_validation.py).

Traces the complete causal spine from ViperCrest temporal candidates to concrete Solidity constructs:
  Candidate -> F-Position -> Source Observation -> Specific Solidity Construct -> Invariant -> Independent Test -> PASS / FAIL

Verifies that the engine's derived candidates have empirical predictive value:
1. Candidate 1 (Backward DERIVED - Predecessor Baseline at T4:S2/S5)
2. Candidate 2 (Forward POSSIBLE - Predictive Containment Circuit Breaker at T6:S6)
3. Independent Foundry verification test execution (Solc 0.8.24 EVM runtime)
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

FORGE_BIN = Path.home() / ".foundry" / "bin" / "forge.exe"
FOUNDRY_PROJECT_DIR = VIPER_ROOT / "runtime" / "foundry_validation"


class MaterialMatrixValidationTests(unittest.TestCase):
    def test_01_causal_spine_trace_and_solidity_construct(self):
        """
        Test 1: Trace the causal spine from generated candidate to Solidity construct.
        Candidate (Forward POSSIBLE T6:S6) -> F5/F8 -> RateLimits.updateLimit() -> Invariant V06/V07
        """
        # 1. Inspect Source Observation in Lombard fixture
        fixture_path = VIPER_ROOT / "fixtures" / "lombard_lbtc_bridge.json"
        self.assertTrue(fixture_path.exists(), "Lombard bridge fixture must exist")

        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        obs_map = {o["id"]: o for o in data["observations"]}

        rate_limit_obs = obs_map.get("F2::M_Solidity::libs/RateLimits.sol")
        self.assertIsNotNone(rate_limit_obs, "RateLimits.sol observation must be present")
        self.assertEqual(rate_limit_obs["candidate"]["syntax_family"], "Solidity")

        # 2. Verify Concrete Solidity Construct
        solidity_file = VIPER_ROOT / "evm-smart-contracts" / "contracts" / "libs" / "RateLimits.sol"
        self.assertTrue(solidity_file.exists(), "Source Solidity file must exist")
        sol_text = solidity_file.read_text(encoding="utf-8")

        self.assertIn("error RateLimitExceeded()", sol_text)
        self.assertIn("function updateLimit", sol_text)
        self.assertIn("function availableAmountToSend", sol_text)

        # 3. Verify Associated Bridge Construct
        bridge_file = VIPER_ROOT / "evm-smart-contracts" / "contracts" / "bridge" / "BridgeV2.sol"
        self.assertTrue(bridge_file.exists(), "BridgeV2.sol must exist")
        bridge_text = bridge_file.read_text(encoding="utf-8")

        self.assertIn("RateLimits.updateLimit(rl, amount);", bridge_text)
        self.assertIn("function setTokenRateLimits", bridge_text)

    def test_02_independent_foundry_evm_execution(self):
        """
        Test 2: Execute independent Foundry test suite compiled with Solc 0.8.24.
        Confirms or falsifies the backward baseline and forward containment candidates.
        """
        if not FORGE_BIN.exists():
            self.skipTest(f"Foundry forge binary not found at {FORGE_BIN}")

        cmd = [str(FORGE_BIN), "test", "--root", str(FOUNDRY_PROJECT_DIR), "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            res.returncode, 0,
            f"Foundry test execution failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )

        test_data = json.loads(res.stdout)
        suite = test_data.get("test/RateLimitsValidationTest.t.sol:RateLimitsValidationTest", {})
        test_results = suite.get("test_results", {})

        # Assert all independent test cases PASSED
        backward_test = test_results.get("test_BackwardHydration_PredecessorBaselineDerived()")
        self.assertIsNotNone(backward_test)
        self.assertEqual(backward_test.get("status"), "Success", "Backward hydration baseline test must PASS")

        forward_test = test_results.get("test_ForwardCandidate_PredictiveContainment_RateLimitExceeded()")
        self.assertIsNotNone(forward_test)
        self.assertEqual(forward_test.get("status"), "Success", "Forward containment candidate test must PASS")

        revert_preserve_test = test_results.get("test_ForwardCandidate_RevertPreservesState()")
        self.assertIsNotNone(revert_preserve_test)
        self.assertEqual(revert_preserve_test.get("status"), "Success", "State preservation after revert must PASS")

        zero_limit_test = test_results.get("test_ZeroLimitConfiguration_AcceptedOrRejected()")
        self.assertIsNotNone(zero_limit_test)
        self.assertEqual(zero_limit_test.get("status"), "Success", "Zero limit acceptance test must PASS")

        zero_window_test = test_results.get("test_ZeroWindowConfiguration_AcceptedOrRejected()")
        self.assertIsNotNone(zero_window_test)
        self.assertEqual(zero_window_test.get("status"), "Success", "Zero window execution test must PASS")

        bypass_test = test_results.get("test_ZeroWindow_SilentlyBypassesRateLimiting()")
        self.assertIsNotNone(bypass_test)
        self.assertEqual(bypass_test.get("status"), "Success", "Zero window rate limit bypass proof must PASS")

        present_test = test_results.get("test_PresentState_NominalTransfer_Succeeds()")
        self.assertIsNotNone(present_test)
        self.assertEqual(present_test.get("status"), "Success", "Present nominal transfer test must PASS")

    def test_03_python_native_evm_arithmetic_verification(self):
        """
        Test 3: Pure Python mathematical replication of Lombard's RateLimits decay formula.
        Tests whether the predictive candidate holds under varying time windows and amounts.
        """
        # Solidity implementation replication:
        # uint256 timeSinceLastDeposit = block.timestamp - _lastUpdated;
        # if (timeSinceLastDeposit >= _window) { currentAmountInFlight = 0; amountCanBeSent = _limit; }
        # else { uint256 decay = (_limit * timeSinceLastDeposit) / _window; ... }

        limit = 1000 * 10**18
        window = 86400

        def available_amount_to_send(amount_in_flight: int, last_updated: int, current_time: int) -> tuple[int, int]:
            time_since = current_time - last_updated
            if time_since >= window:
                cur = 0
                can_send = limit
            else:
                decay = (limit * time_since) // window
                cur = 0 if amount_in_flight <= decay else amount_in_flight - decay
                can_send = 0 if limit <= cur else limit - cur
            return cur, can_send

        # Baseline (T4): at t0 with 0 in-flight
        t0 = 1000000
        cur_t4, can_t4 = available_amount_to_send(0, t0, t0)
        self.assertEqual(cur_t4, 0, "Candidate 1 (DERIVED T4): inFlight must be strictly 0")
        self.assertEqual(can_t4, limit, "Candidate 1 (DERIVED T4): capacity must equal limit")

        # Nominal Transfer (T5): spend 400
        spent = 400 * 10**18
        cur_t5 = spent
        last_up_t5 = t0

        # Immediate follow-up attempt: 700 (Total = 1100 > 1000 limit)
        cur_imm, can_imm = available_amount_to_send(cur_t5, last_up_t5, t0)
        self.assertEqual(can_imm, 600 * 10**18)
        self.assertTrue(
            700 * 10**18 > can_imm,
            "Candidate 2 (POSSIBLE T6): Excess spend must exceed capacity and trigger containment",
        )

        # Decay over 12 hours (half window): decay = 1000 * 43200 // 86400 = 500
        # Since amount_in_flight (400) <= decay (500), in-flight decays to 0!
        t_half = t0 + 43200
        cur_decay, can_decay = available_amount_to_send(cur_t5, last_up_t5, t_half)
        self.assertEqual(cur_decay, 0)
        self.assertEqual(can_decay, limit)

    def test_04_ai_contract_explains_predictive_candidate(self):
        """
        Test 4: Verify that the AI Contract gateway queries and explains the candidate
        strictly based on authoritative ViperCrest state without guessing.
        """
        executor = aic.ViperCrestContractExecutor()
        envelope = aic.AIRequestEnvelope(
            intent="query",
            cartridge="security",
            questions=[
                {
                    "question_id": "Q_CONTAINMENT",
                    "query_text": "What is the forward reachability candidate for Lombard Bridge?",
                    "target_coordinate": "T6_REFRACTING:S6",
                }
            ],
            requested_action="query",
        )
        response = executor.execute(envelope)
        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(len(response.question_answers), 1)

        ans = response.question_answers[0]["authoritative_answer"]
        self.assertEqual(ans["epistemic_status"], "POSSIBLE")
        self.assertIn("T6_REFRACTING:S6", ans["coordinate"])


if __name__ == "__main__":
    unittest.main()
