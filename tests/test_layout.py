import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import network_adapter
import session_router
import viper_core as core
import viper_matrix


class LayoutTests(unittest.TestCase):
    def test_active_root_is_not_a_link(self):
        self.assertFalse(core.ROOT.is_symlink())
        self.assertFalse(os.path.isjunction(core.ROOT) if hasattr(os.path, "isjunction") else
                         core.ROOT.stat().st_file_attributes & 0x400)

    def test_defaults_are_owned_by_active_runtime(self):
        for path in (core.STATE_DB, core.KEY_PATH, core.FIXTURES, core.DROPZONE,
                     session_router.SESSIONS_ROOT):
            self.assertTrue(path.is_relative_to(core.ROOT / "runtime"))

    def test_bundled_fixture_resolves_without_copying_into_runtime(self):
        self.assertEqual(
            core.resolve_fixture("example.json"),
            core.BUNDLED_FIXTURES / "example.json",
        )

    def test_missing_fixture_and_path_escape_are_errors(self):
        for name in ("..\\outside.json", "sub\\example.json", "C:\\outside.json"):
            with self.subTest(name=name), self.assertRaises(core.IntentError):
                core.resolve_fixture(name)
        with self.assertRaises(core.IntentError):
            core.load_json(core.resolve_fixture("missing-fixture.json"))

    def test_wal_is_enabled_on_fresh_state(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.db"
            core.initialize_state_db(database)
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_online_preserves_patient_context_for_matrix(self):
        fixture = json.loads(
            (core.BUNDLED_FIXTURES / "patient_records_bola.json").read_text(encoding="utf-8")
        )
        normalized = json.loads(network_adapter.normalize_fixture(json.dumps(fixture).encode()))
        self.assertEqual(normalized["observations"], fixture["observations"])
        self.assertTrue(any(
            viper_matrix.evaluate_patient_observation(item)["status"] == "ERROR_PATIENT_POLICY"
            for item in normalized["observations"]
        ))

    def test_installed_config_is_used_and_disabled_without_hosts(self):
        with patch.object(network_adapter, "run_online") as run:
            run.return_value = {"status": "test", "session_path": "test", "exit_code": 1}
            self.assertEqual(network_adapter.main([
                "--url", "https://authorized.invalid/fixture.json", "--case-id", "test",
            ]), 1)
        config = run.call_args.args[2]
        self.assertFalse(config.network_enabled)
        self.assertEqual(config.allowed_hosts, ())
