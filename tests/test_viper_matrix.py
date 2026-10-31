import contextlib
import copy
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import session_router
import viper_core
import viper_matrix
import viper_http


class MatrixTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.db = self.root / "state.db"
        self.key = self.root / "key.pem"
        self.key.write_bytes(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        self.fixture = json.loads(
            (viper_core.BUNDLED_FIXTURES / "patient_records_bola.json").read_text(encoding="utf-8")
        )

    def execute(self, fixture=None, **kwargs):
        target = self.root / "fixture.json"
        target.write_text(json.dumps(self.fixture if fixture is None else fixture), encoding="utf-8")
        return viper_matrix.execute_matrix_sweep(target, db_path=self.db, key_path=self.key, **kwargs)

    def load(self, report):
        folder = report["session_path"]
        return session_router.load_session(
            folder.name, sessions_root=folder.parent, trusted_key_path=self.key
        )

    def test_patient_fixture_fails_and_produces_verified_fault_session(self):
        report = self.execute()
        self.assertEqual(report["exit_code"], 1)
        session = self.load(report)
        self.assertTrue(session["audit_signature_valid"])
        self.assertEqual(session["meta"]["outcome"], "FAULT")
        self.assertEqual(
            {path.name for path in report["session_path"].iterdir()},
            session_router.SESSION_FILES,
        )
        self.assertTrue(viper_core.verify_run_receipt(report["run_id"], self.db))
        self.assertTrue(session["state_delta"]["deltas"])
        self.assertTrue(any(event["severity"] == "ERROR" for event in session["events"]))
        self.assertEqual(len(list((self.root / "staging").iterdir())), 0)

    def test_allowed_read_is_not_keyword_failure(self):
        allowed = next(
            item for item in self.fixture["observations"]
            if item["id"] == "same-tenant-assigned-read"
        )
        fixture = {"observations": [copy.deepcopy(allowed)]}
        fixture["note"] = "unauthorized patient_id response_status"
        report = self.execute(fixture)
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["policy_checks"][0]["status"], "PASSED")
        self.assertTrue(self.load(report)["audit_signature_valid"])

    def test_correct_denial_is_allowed_and_foreign_records_fail(self):
        cross = copy.deepcopy(self.fixture["observations"][0])
        cross["candidate"] = cross["baseline"]
        self.assertEqual(viper_matrix.evaluate_patient_observation(cross)["status"], "PASSED")
        allowed = copy.deepcopy(next(
            item for item in self.fixture["observations"]
            if item["id"] == "same-tenant-assigned-read"
        ))
        allowed["candidate"]["body"]["data"][0]["tenant_id"] = "foreign"
        self.assertEqual(
            viper_matrix.evaluate_patient_observation(allowed)["status"], "ERROR_PATIENT_POLICY"
        )

    def test_generic_fixture_reports_policy_not_applicable(self):
        fixture = {"observations": [{
            "id": "generic", "baseline": {"value": 1}, "candidate": {"value": 2},
        }]}
        report = self.execute(fixture)
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["policy_checks"][0]["status"], "NOT_APPLICABLE")
        self.assertEqual(report["status"], "human_review_required")
        self.assertFalse(report["vulnerability_confirmed"])

    def test_invalid_shapes_and_partial_policy_fail_before_persistence(self):
        partial = copy.deepcopy(self.fixture)
        del partial["observations"][0]["context"]["caller"]
        bad_context = copy.deepcopy(self.fixture)
        bad_context["observations"][0]["context"] = []
        for fixture in ([1, 2, 3], ["patient_id"], {}, {"observations": []}, partial, bad_context):
            with self.subTest(fixture=fixture), self.assertRaises(viper_core.IntentError):
                self.execute(fixture)
        self.assertFalse(self.db.exists())
        self.assertFalse((self.root / "staging").exists())

    def test_malformed_missing_target_and_missing_key_are_explicit_cli_errors(self):
        target = self.root / "invalid.json"
        for text in ("{", '{"observations": NaN}'):
            target.write_text(text, encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as error:
                code = viper_matrix.main([
                    "--target", str(target), "--db", str(self.db), "--key", str(self.key),
                ])
            self.assertEqual(code, 2)
            self.assertIn("[VIPER] ERROR:", error.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(viper_matrix.main(["--target", str(self.root / "missing.json")]), 2)
        self.assertIn("Cannot read valid JSON", error.getvalue())
        self.key.unlink()
        with self.assertRaisesRegex(viper_core.IntentError, "No signing key"):
            self.execute()

    def test_foreign_staging_and_cache_survive(self):
        foreign = self.root / "staging" / "other-session"
        foreign.mkdir(parents=True)
        marker = foreign / "payload.json"
        marker.write_text("{}", encoding="utf-8")
        cache = self.root / "__pycache__"
        cache.mkdir()
        cached = cache / "foreign.pyc"
        cached.write_bytes(b"synthetic")
        self.execute()
        self.assertTrue(marker.exists())
        self.assertTrue(cached.exists())
        self.assertEqual(list((self.root / "staging").iterdir()), [foreign])

    def test_identical_timestamp_runs_remain_distinct(self):
        with patch.object(viper_matrix, "datetime") as clock:
            clock.now.return_value.strftime.return_value = "20261026T120000000000Z"
            first = self.execute()
            second = self.execute()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertNotEqual(first["session_path"], second["session_path"])
        self.assertTrue(self.load(first)["audit_signature_valid"])
        self.assertTrue(self.load(second)["audit_signature_valid"])

    def test_stage_chain_binds_payload_and_every_preceding_transition(self):
        report = self.execute()
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            rows = connection.execute(
                "SELECT stage, content_json FROM artifacts WHERE run_id = ? ORDER BY stage",
                (report["run_id"],),
            ).fetchall()
        parent = viper_matrix._sha256(self.fixture)
        self.assertEqual(len(rows), 9)
        for stage, encoded in rows:
            content = json.loads(encoded)
            provenance = content.pop("state_provenance")
            receipt = content.pop("circuit_receipt")
            self.assertEqual(receipt["content"], content)
            self.assertEqual(provenance["input_hash"], parent)
            expected = viper_matrix._sha256({
                "input_hash": parent, "stage": stage, "content": content,
            })
            self.assertEqual(provenance["output_hash"], expected)
            parent = expected
        changed = copy.deepcopy(self.fixture)
        changed["metadata"]["description"] = "different seed"
        second = self.execute(changed)
        self.assertNotEqual(self.load(report)["meta"]["seed_sha256"], self.load(second)["meta"]["seed_sha256"])

    def test_session_and_database_tampering_are_detected(self):
        report = self.execute()
        session_path = report["session_path"]
        meta_path = session_path / "session_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["outcome"] = "SUCCESS"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        self.assertFalse(self.load(report)["audit_signature_valid"])
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            connection.execute(
                "UPDATE artifacts SET content_json = '{}' WHERE run_id = ?", (report["run_id"],)
            )
            connection.commit()
        self.assertFalse(viper_core.verify_run_receipt(report["run_id"], self.db))

    def test_write_failure_cleans_staging_and_never_publishes_partial_bundle(self):
        original = session_router._write_text

        def fail(path, content):
            if path.name == "receipts_audit.sig":
                raise OSError("injected audit write failure")
            original(path, content)

        with patch.object(session_router, "_write_text", side_effect=fail):
            with self.assertRaisesRegex(OSError, "injected audit write failure"):
                self.execute()
        self.assertEqual(list((self.root / "staging").iterdir()), [])
        self.assertEqual(list((self.root / "sessions").iterdir()), [])

    def test_staging_failure_is_not_silent_and_does_not_leave_own_payloads(self):
        with patch.object(viper_matrix, "save_run", side_effect=RuntimeError("injected failure")):
            with self.assertRaisesRegex(RuntimeError, "injected failure"):
                self.execute()
        self.assertEqual(list((self.root / "staging").iterdir()), [])

    def test_cleanup_failure_is_not_reported_as_success(self):
        with patch.object(viper_matrix.tempfile.TemporaryDirectory, "__exit__", side_effect=OSError("cleanup failed")):
            with self.assertRaisesRegex(OSError, "cleanup failed"):
                self.execute()

    def test_cli_policy_failure_returns_one(self):
        target = self.root / "patient.json"
        target.write_text(json.dumps(self.fixture), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = viper_matrix.main([
                "--target", str(target), "--db", str(self.db), "--key", str(self.key),
            ])
        self.assertEqual(code, 1)
        self.assertIn("FAULT_PATIENT_POLICY", output.getvalue())
        self.assertIn("audit verified", output.getvalue())

    def test_real_launcher_persists_verified_session_and_returns_one(self):
        target = self.root / "patient.json"
        target.write_text(json.dumps(self.fixture), encoding="utf-8")
        launcher = Path(viper_matrix.__file__).parent / "viper.py"
        process = subprocess.run(
            [
                sys.executable, "-B", str(launcher), "matrix",
                "--target", str(target), "--db", str(self.db), "--key", str(self.key),
            ],
            capture_output=True, text=True, timeout=30, cwd=self.root,
        )
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        self.assertIn("FAULT_PATIENT_POLICY", process.stdout)
        self.assertEqual(process.stderr, "")
        folders = list((self.root / "sessions").iterdir())
        self.assertEqual(len(folders), 1)
        session = session_router.load_session(
            folders[0].name, sessions_root=folders[0].parent, trusted_key_path=self.key
        )
        self.assertTrue(session["audit_signature_valid"])

    def test_http_evaluates_all_nine_sectors_and_preserves_policy_result(self):
        calls = []
        original = viper_matrix.evaluate_matrix_sector

        def observe(sector, envelope):
            calls.append(sector)
            return original(sector, envelope)

        with patch.object(viper_matrix, "evaluate_matrix_sector", side_effect=observe):
            report = self.execute(transport="http", http_port=0)
        self.assertEqual(calls, list(range(1, 10)))
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["transport"], "http")
        self.assertTrue(self.load(report)["audit_signature_valid"])
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            rows = connection.execute(
                "SELECT stage, content_json FROM artifacts WHERE run_id = ? ORDER BY stage",
                (report["run_id"],),
            ).fetchall()
        parent_hash = viper_http.digest(self.fixture)
        for stage, encoded in rows:
            artifact = json.loads(encoded)
            envelope = {
                "icon_uri": f"icon://sector/f{int(stage[1])}/evaluate",
                "run_id": report["run_id"],
                "case_id": report["case_id"],
                "sector_id": f"F{int(stage[1])}",
                "stage": stage,
                "input_hash": parent_hash,
                "target_payload": self.fixture,
                "fixture_name": "fixture.json",
                "database_name": self.db.name,
                "transport": "http",
            }
            key = viper_core._load_private_key(self.key)
            viper_http.verify_receipt(
                int(stage[1]), envelope, artifact["circuit_receipt"], key.public_key()
            )
            parent_hash = artifact["state_provenance"]["output_hash"]
        self.assertEqual(list((self.root / "staging").iterdir()), [])

    def test_http_failure_does_not_persist_or_leak_staging(self):
        with patch.object(viper_http.CircuitClient, "dispatch", side_effect=viper_core.IntentError("transport failed")):
            with self.assertRaisesRegex(viper_core.IntentError, "transport failed"):
                self.execute(transport="http", http_port=0)
        self.assertFalse(self.db.exists())
        self.assertEqual(list((self.root / "staging").iterdir()), [])

    def test_real_http_launcher(self):
        target = self.root / "patient.json"
        target.write_text(json.dumps(self.fixture), encoding="utf-8")
        process = subprocess.run(
            [
                sys.executable, "-B", str(Path(viper_matrix.__file__).parent / "viper.py"),
                "matrix", "--target", str(target), "--db", str(self.db), "--key", str(self.key),
                "--transport", "http", "--http-port", "0",
            ],
            capture_output=True, text=True, timeout=30, cwd=self.root,
        )
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        self.assertIn("FAULT_PATIENT_POLICY", process.stdout)
        self.assertIn("audit verified", process.stdout)

    def test_http_allowed_read_passes_without_policy_false_positive(self):
        allowed = copy.deepcopy(next(
            item for item in self.fixture["observations"]
            if item["id"] == "same-tenant-assigned-read"
        ))
        report = self.execute({"observations": [allowed]}, transport="http", http_port=0)
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["policy_checks"][0]["status"], "PASSED")
        self.assertTrue(self.load(report)["audit_signature_valid"])

    def test_http_bind_failure_is_cli_error_two_and_cleans_staging(self):
        key = viper_core._load_private_key(self.key)
        target = self.root / "patient.json"
        target.write_text(json.dumps(self.fixture), encoding="utf-8")
        with viper_http.local_circuit(viper_matrix.evaluate_matrix_sector, key, "occupied", port=0) as circuit:
            with contextlib.redirect_stderr(io.StringIO()) as error:
                code = viper_matrix.main([
                    "--target", str(target), "--db", str(self.db), "--key", str(self.key),
                    "--transport", "http", "--http-port", str(circuit.port),
                ])
        self.assertEqual(code, 2)
        self.assertIn("[VIPER] ERROR:", error.getvalue())
        self.assertFalse(self.db.exists())
        self.assertEqual(list((self.root / "staging").iterdir()), [])
