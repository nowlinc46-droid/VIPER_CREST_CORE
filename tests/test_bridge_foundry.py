import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import bridge_foundry


class BridgeFoundryTests(unittest.TestCase):
    def test_scenarios_have_required_structure(self):
        for scenario_name, scenario in bridge_foundry.SIMULATION_SCENARIOS.items():
            with self.subTest(scenario=scenario_name):
                self.assertIn("id", scenario)
                self.assertIn("baseline", scenario)
                self.assertIn("candidate", scenario)
                self.assertIsInstance(scenario["baseline"], dict)
                self.assertIsInstance(scenario["candidate"], dict)

    def test_create_observation_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.object(bridge_foundry, "FIXTURES_DIR", tmp_path):
                target = bridge_foundry.create_observation_fixture(
                    "test_fixture.json",
                    [{"id": "obs1", "baseline": {"k": 1}, "candidate": {"k": 2}}],
                )
                self.assertTrue(target.exists())
                data = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(len(data["observations"]), 1)
                self.assertEqual(data["observations"][0]["id"], "obs1")

    def test_main_dispatch_scenario(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.object(bridge_foundry, "FIXTURES_DIR", tmp_path), patch.object(
                bridge_foundry, "run_vipercrest_matrix", return_value=0
            ) as mock_matrix:
                rc = bridge_foundry.main(["--scenario", "reentrancy", "--name", "reentrancy_test.json"])
                self.assertEqual(rc, 0)
                mock_matrix.assert_called_once()
                staged_file = tmp_path / "reentrancy_test.json"
                self.assertTrue(staged_file.exists())
                content = json.loads(staged_file.read_text(encoding="utf-8"))
                self.assertEqual(content["observations"][0]["id"], "v03-reentrancy-vault-drain")

    def test_main_dispatch_all_scenarios(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch.object(bridge_foundry, "FIXTURES_DIR", tmp_path), patch.object(
                bridge_foundry, "run_vipercrest_matrix", return_value=0
            ) as mock_matrix:
                rc = bridge_foundry.main(["--scenario", "all", "--name", "all_scenarios.json"])
                self.assertEqual(rc, 0)
                mock_matrix.assert_called_once()
                staged_file = tmp_path / "all_scenarios.json"
                self.assertTrue(staged_file.exists())
                content = json.loads(staged_file.read_text(encoding="utf-8"))
                self.assertEqual(len(content["observations"]), len(bridge_foundry.SIMULATION_SCENARIOS))


if __name__ == "__main__":
    unittest.main()
