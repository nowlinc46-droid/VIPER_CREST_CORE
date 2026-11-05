import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import phone_intake
import viper_core


class PhoneIntakeTests(unittest.TestCase):
    def test_synthetic_device_dump_generation(self):
        for scenario in ("security_anomaly", "app_db_audit", "telemetry"):
            with self.subTest(scenario=scenario):
                dump = phone_intake.generate_synthetic_device_dump("TEST_DEV_01", scenario)
                self.assertIn("observations", dump)
                self.assertEqual(len(dump["observations"]), 1)
                obs = dump["observations"][0]
                self.assertIn("baseline", obs)
                self.assertIn("candidate", obs)
                self.assertIn("provenance", obs)
                self.assertEqual(obs["provenance"]["device_id"], "TEST_DEV_01")

    def test_stage_to_dropzone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dropzone = Path(tmpdir) / "dropzone"
            tmp_dropzone.mkdir()
            with patch.object(phone_intake, "DROPZONE", tmp_dropzone):
                payload = {"observations": [{"id": "test-obs", "baseline": {}, "candidate": {}}]}
                target = phone_intake.stage_to_dropzone(payload, "test_device.json")
                self.assertTrue(target.exists())
                data = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(data, payload)

    def test_main_simulation_and_matrix_invocation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            tmp_dropzone = tmp_root / "dropzone"
            tmp_fixtures = tmp_root / "fixtures"
            tmp_dropzone.mkdir()
            tmp_fixtures.mkdir()
            tmp_db = tmp_root / "test_state.db"

            with patch.object(phone_intake, "DROPZONE", tmp_dropzone), patch.object(
                phone_intake, "FIXTURES", tmp_fixtures
            ), patch.object(phone_intake, "STATE_DB", tmp_db), patch.object(
                viper_core, "DROPZONE", tmp_dropzone
            ), patch.object(
                viper_core, "FIXTURES", tmp_fixtures
            ), patch.object(
                viper_core, "STATE_DB", tmp_db
            ), patch.object(
                phone_intake, "detect_connected_devices", return_value=[]
            ), patch.object(
                phone_intake.subprocess, "run"
            ) as mock_subproc:
                mock_subproc.return_value = MagicMock(returncode=0)
                rc = phone_intake.main(["--simulate", "--scenario", "telemetry", "--device-id", "DEV_UNITTEST"])
                self.assertEqual(rc, 0)
                mock_subproc.assert_called_once()
                # Verify dropzone staging file is unlinked after ingestion
                staged_files = list(tmp_dropzone.iterdir())
                self.assertEqual(len(staged_files), 0)
                # Verify fixture was copied to fixtures
                fixture_files = list(tmp_fixtures.iterdir())
                self.assertEqual(len(fixture_files), 1)


if __name__ == "__main__":
    unittest.main()
