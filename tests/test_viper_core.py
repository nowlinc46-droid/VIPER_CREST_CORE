import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import viper_core


class FixtureAnalysisTests(unittest.TestCase):
    def test_flatten_and_compare_are_deterministic(self):
        observations = [
            {
                "id": "sample",
                "baseline": {"z": [1, 2], "a": True},
                "candidate": {"z": [1, 3], "a": True},
            }
        ]

        first = viper_core.compare_observations(observations)
        second = viper_core.compare_observations(observations)

        self.assertEqual(first, second)
        self.assertEqual(first[0]["path"], "$.z[1]")
        self.assertEqual(first[0]["baseline"], 2)
        self.assertEqual(first[0]["candidate"], 3)

    def test_fixture_path_rejects_traversal(self):
        with self.assertRaises(viper_core.IntentError):
            viper_core.resolve_fixture("..\\outside.json")

    def test_fixture_path_requires_json_filename(self):
        with self.assertRaises(viper_core.IntentError):
            viper_core.resolve_fixture("https://example.invalid")

    def test_legacy_fixture_schema_remains_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            fixture_path = fixture_root / "legacy.json"
            fixture_path.write_text(
                json.dumps(
                    {
                        "observations": [
                            {
                                "id": "legacy",
                                "baseline": {"body": {"value": 1}},
                                "candidate": {"body": {"value": 2}},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(viper_core, "FIXTURES", fixture_root):
                self.assertTrue(viper_core.validate_fixture_schema(fixture_path))

    def test_sector_fixture_schema_maps_payloads_to_observations(self):
        fixture = {
            "id": "sector-fixture",
            "timestamp": "2026-10-23T18:00:00Z",
            "metadata": {"source": "offline"},
            "sectors": [
                {
                    "name": "recorded-response",
                    "payload": {
                        "baseline": {"body": {"value": 1}},
                        "candidate": {"body": {"value": 2}},
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            fixture_path = fixture_root / "sector.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            with patch.object(viper_core, "FIXTURES", fixture_root):
                self.assertTrue(viper_core.validate_fixture_schema(fixture_path))
            observations = viper_core.fixture_observations(fixture)
        self.assertEqual(observations[0]["id"], "recorded-response")
        self.assertEqual(len(viper_core.compare_observations(observations)), 1)

    def test_sector_fixture_schema_rejects_invalid_structure(self):
        invalid_fixtures = [
            {},
            {
                "id": "missing-sector-keys",
                "timestamp": "2026-10-23T18:00:00Z",
                "metadata": {},
                "sectors": [{"name": "sector", "payload": []}],
            },
            {
                "id": "bad-time",
                "timestamp": "not-a-timestamp",
                "metadata": {},
                "sectors": [],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            for index, fixture in enumerate(invalid_fixtures):
                fixture_path = fixture_root / f"invalid-{index}.json"
                fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
                with patch.object(viper_core, "FIXTURES", fixture_root):
                    self.assertFalse(viper_core.validate_fixture_schema(fixture_path))

    def test_fixture_schema_rejects_non_fixture_and_malformed_json_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_root = root / "fixtures"
            fixture_root.mkdir()
            outside_path = root / "outside.json"
            outside_path.write_text(
                json.dumps({"observations": []}),
                encoding="utf-8",
            )
            malformed_path = fixture_root / "malformed.json"
            malformed_path.write_text("{", encoding="utf-8")
            with patch.object(viper_core, "FIXTURES", fixture_root):
                self.assertFalse(viper_core.validate_fixture_schema(outside_path))
                self.assertFalse(viper_core.validate_fixture_schema(malformed_path))

    def test_bounded_variance_is_deterministic_and_clamped(self):
        baseline = {
            "headers": {"content-type": "application/json"},
            "content_length": 100,
            "body": {"user": {"id": 1}},
        }
        identical = viper_core.bounded_variance_score(baseline, baseline)
        changed = viper_core.bounded_variance_score(
            baseline,
            {
                "headers": {"content-type": "text/plain", "x-new": "yes"},
                "content_length": 250,
                "body": {"user": {"id": "one", "name": "example"}},
            },
        )

        self.assertEqual(identical["score"], 0)
        self.assertEqual(changed, viper_core.bounded_variance_score(
            baseline,
            {
                "headers": {"content-type": "text/plain", "x-new": "yes"},
                "content_length": 250,
                "body": {"user": {"id": "one", "name": "example"}},
            },
        ))
        self.assertGreater(changed["score"], 0)
        self.assertLessEqual(changed["score"], 1)
        self.assertEqual(changed["components"]["json_schema"], 1)

    def test_bounded_variance_rejects_invalid_weights(self):
        with self.assertRaises(ValueError):
            viper_core.bounded_variance_score(
                {},
                {},
                {
                    "headers": float("nan"),
                    "content_length": 0.3,
                    "json_schema": 0.4,
                    "content": 0.1,
                },
            )

    def test_project_storage_is_local_and_outside_onedrive(self):
        self.assertEqual(viper_core.ROOT.drive.casefold(), "c:")
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            self.assertFalse(
                viper_core.ROOT.is_relative_to(Path(onedrive).resolve())
            )


class PersistenceAndIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "viper_state.db"
        self.key = Ed25519PrivateKey.generate()
        viper_core.initialize_state_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def save_one(self, run_id):
        content = {"case_id": run_id, "observed": ["$.value"]}
        variance_score = {
            "run-one": 0.2,
            "run-two": 0.4,
        }.get(run_id, 0.1)
        viper_core.save_run(
            run_id=run_id,
            case_id=run_id,
            fixture_name="fixture.json",
            report={
                "status": "human_review_required",
                "variance_score": variance_score,
            },
            artifacts=[
                {
                    "stage": "v4_validate",
                    "artifact_name": f"{run_id}.json",
                    "content": content,
                }
            ],
            private_key=self.key,
            db_path=self.db_path,
        )

    def test_database_uses_wal_and_persists_atomically(self):
        self.save_one("run-one")

        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            run_count = connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            artifact_count = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            receipt_count = connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]

        self.assertEqual(journal_mode.casefold(), "wal")
        self.assertEqual((run_count, artifact_count, receipt_count), (1, 1, 1))
        self.assertTrue(viper_core.verify_run_receipt("run-one", self.db_path))

    def test_analytics_reports_totals_daily_trends_and_average_score(self):
        self.save_one("run-one")
        self.save_one("run-two")

        analytics = viper_core.query_run_analytics(self.db_path)

        self.assertEqual(analytics["total_runs"], 2)
        self.assertAlmostEqual(analytics["average_variance_score"], 0.3)
        self.assertEqual(len(analytics["daily_trends"]), 1)
        self.assertEqual(analytics["daily_trends"][0]["total_runs"], 2)
        self.assertAlmostEqual(
            analytics["daily_trends"][0]["average_variance_score"], 0.3
        )

    def test_analytics_rejects_invalid_limit_and_missing_database(self):
        with self.assertRaises(ValueError):
            viper_core.query_run_analytics(self.db_path, limit=0)
        with self.assertRaises(FileNotFoundError):
            viper_core.query_run_analytics(self.db_path.parent / "missing.db")

    def test_existing_runs_table_is_migrated_with_variance_column(self):
        legacy_db = self.db_path.parent / "legacy.db"
        with closing(sqlite3.connect(legacy_db)) as connection, connection:
            connection.execute(
                """
                CREATE TABLE runs (
                    run_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    fixture_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )
        viper_core.initialize_state_db(legacy_db)
        with closing(sqlite3.connect(legacy_db)) as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(runs)")
            }
        self.assertIn("variance_score", columns)

    def test_concurrent_writers_keep_all_runs_and_receipts(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(self.save_one, [f"run-{index}" for index in range(4)]))

        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            counts = (
                connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],
            )
        self.assertEqual(counts, (4, 4, 4))
        self.assertTrue(
            all(
                viper_core.verify_run_receipt(f"run-{index}", self.db_path)
                for index in range(4)
            )
        )

    def test_receipt_detects_artifact_tampering(self):
        self.save_one("run-tamper")
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute(
                "UPDATE artifacts SET content_json = ? WHERE run_id = ?",
                (json.dumps({"changed": True}), "run-tamper"),
            )
        self.assertFalse(viper_core.verify_run_receipt("run-tamper", self.db_path))

    def test_receipt_detects_run_metadata_tampering(self):
        self.save_one("run-metadata")
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute(
                "UPDATE runs SET fixture_name = ? WHERE run_id = ?",
                ("changed.json", "run-metadata"),
            )
        self.assertFalse(viper_core.verify_run_receipt("run-metadata", self.db_path))

    def test_receipt_rejects_malformed_public_key(self):
        self.save_one("run-bad-key")
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute(
                "UPDATE receipts SET public_key_pem = ? WHERE run_id = ?",
                ("not a public key", "run-bad-key"),
            )
        self.assertFalse(viper_core.verify_run_receipt("run-bad-key", self.db_path))

    def test_failed_duplicate_run_does_not_append_partial_records(self):
        self.save_one("run-duplicate")
        with self.assertRaises(sqlite3.IntegrityError):
            self.save_one("run-duplicate")
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            counts = (
                connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],
            )
        self.assertEqual(counts, (1, 1, 1))


class DropzoneTests(unittest.TestCase):
    def test_dropzone_ingests_only_valid_offline_fixture_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dropzone = root / "dropzone"
            fixtures = root / "fixtures"
            dropzone.mkdir()
            fixture_data = {
                "observations": [
                    {
                        "id": "offline-case",
                        "baseline": {"body": {"value": 1}},
                        "candidate": {"body": {"value": 2}},
                    }
                ]
            }
            (dropzone / "offline.json").write_text(json.dumps(fixture_data), encoding="utf-8")
            with patch.object(viper_core, "DROPZONE", dropzone), patch.object(
                viper_core, "FIXTURES", fixtures
            ):
                self.assertEqual(
                    viper_core.ingest_dropzone(root / "state.db"),
                    ["offline.json"],
                )
            self.assertEqual(
                json.loads((fixtures / "offline.json").read_text(encoding="utf-8")),
                fixture_data,
            )

    def test_dropzone_rejects_non_json_target_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dropzone = root / "dropzone"
            dropzone.mkdir()
            (dropzone / "targets.txt").write_text("example.invalid", encoding="utf-8")
            with patch.object(viper_core, "DROPZONE", dropzone), patch.object(
                viper_core, "FIXTURES", root / "fixtures"
            ):
                with self.assertRaises(viper_core.IntentError):
                    viper_core.ingest_dropzone(root / "state.db")


if __name__ == "__main__":
    unittest.main()
