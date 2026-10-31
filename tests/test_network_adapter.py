from __future__ import annotations

import hashlib
import io
import json
import ssl
import tempfile
import unittest
from contextlib import ExitStack, closing, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import viper_core as core
import network_adapter as adapter
import viper_matrix


FIXTURE = {"observations": [{"id": "recorded", "baseline": {"value": 1}, "candidate": {"value": 2}}]}
RAW = json.dumps(FIXTURE).encode()


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.config = adapter.NetworkConfig(network_enabled=True, allowed_hosts=("authorized.invalid",))
        self.url = "https://authorized.invalid/fixture.json"
        self.connection = MagicMock()
        self.response = MagicMock()
        self.connection.getresponse.return_value.__enter__.return_value = self.response
        self.factory = self.enterContext(patch.object(
            adapter.http.client, "HTTPSConnection", return_value=self.connection,
        ))
        self.reply()

    def reply(self, raw=RAW, *, status=200, headers=None):
        values = {"Content-Type": "application/json", "Content-Length": str(len(raw))}
        if headers:
            values.update(headers)
        self.response.status = status
        self.response.getheader.side_effect = lambda name, default=None: values.get(name, default)
        body = io.BytesIO(raw)
        self.response.read1.side_effect = body.read1

    def test_disabled_is_default_and_never_connects(self):
        with self.assertRaisesRegex(adapter.NetworkInputError, "disabled"):
            adapter.receive_fixture(self.url, adapter.NetworkConfig.load())
        self.factory.assert_not_called()

    def test_authorized_get_tls_and_provenance(self):
        normalized, provenance = adapter.receive_fixture(self.url + "?token=not-recorded", self.config)
        self.assertEqual(json.loads(normalized), FIXTURE)
        args = self.factory.call_args
        self.assertEqual(args.args, ("authorized.invalid",))
        self.assertEqual(args.kwargs["port"], 443)
        self.assertEqual(args.kwargs["timeout"], 10.0)
        context = args.kwargs["context"]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(self.connection.request.call_args.args[:2], ("GET", "/fixture.json?token=not-recorded"))
        self.assertEqual(provenance["authorized_source"], "https://authorized.invalid")
        self.assertEqual(provenance["raw_sha256"], hashlib.sha256(RAW).hexdigest())
        self.assertEqual(provenance["normalized_fixture_sha256"], hashlib.sha256(normalized).hexdigest())
        self.assertNotIn("token", json.dumps(provenance))
        self.connection.close.assert_called_once()

    def test_unauthorized_http_credentials_ports_and_destination_changes_rejected(self):
        for url in (
            "https://unauthorized.invalid/x", "https://authorized.invalid.evil/x",
            "http://authorized.invalid/x", "https://user:password@authorized.invalid/x",
            "https://authorized.invalid:8443/x", "https://authorized.invalid:/x",
            "https://authorized.invalid/x#fragment", "https://authorized.invalid\\@evil/x",
            "https://authorized.invalid/\r\nheader", "https://authorized.invalid./x",
        ):
            with self.subTest(url=url), self.assertRaises(adapter.NetworkInputError):
                adapter.receive_fixture(url, self.config)
        self.factory.assert_not_called()

    def test_post_and_all_redirects_rejected_without_second_request(self):
        with self.assertRaises(adapter.NetworkInputError):
            adapter.receive_fixture(self.url, self.config, method="POST")
        self.factory.assert_not_called()
        for location in ("https://unauthorized.invalid", "/same-host"):
            self.reply(status=302, headers={"Location": location})
            with self.assertRaisesRegex(adapter.NetworkInputError, "Redirects"):
                adapter.receive_fixture(self.url, self.config)
        self.assertEqual(self.connection.request.call_count, 2)

    def test_timeout_tls_and_transport_errors_are_explicit_and_close(self):
        for error, message in (
            (TimeoutError("secret"), "timed out"),
            (ssl.SSLError("secret"), "TLS"),
            (ConnectionRefusedError("secret"), "connection"),
        ):
            with self.subTest(error=type(error).__name__):
                self.connection.connect.side_effect = error
                with self.assertRaisesRegex(adapter.NetworkInputError, message) as raised:
                    adapter.receive_fixture(self.url, self.config)
                self.assertNotIn("secret", str(raised.exception))
        self.assertEqual(self.connection.close.call_count, 3)

    def test_read_timeout_and_total_deadline(self):
        self.response.read1.side_effect = TimeoutError()
        with self.assertRaisesRegex(adapter.NetworkInputError, "timed out"):
            adapter.receive_fixture(self.url, self.config)
        self.reply()
        with patch.object(adapter.time, "monotonic", side_effect=[0, 11]):
            with self.assertRaisesRegex(adapter.NetworkInputError, "timed out"):
                adapter.receive_fixture(self.url, self.config)

    def test_body_socket_keeps_timeout_when_connection_closes(self):
        sock = self.connection.sock

        def getresponse():
            self.connection.sock = None
            return self.response

        self.connection.getresponse.side_effect = getresponse
        self.response.__enter__.return_value = self.response
        adapter.receive_fixture(self.url, self.config)
        self.assertGreaterEqual(sock.settimeout.call_count, 3)

    def test_oversized_declared_and_streamed_responses(self):
        config = adapter.NetworkConfig(network_enabled=True, allowed_hosts=("authorized.invalid",), max_response_bytes=20)
        with self.assertRaisesRegex(adapter.NetworkInputError, "MAX_RESPONSE_BYTES"):
            adapter.receive_fixture(self.url, config)
        self.response.read1.assert_not_called()
        self.reply(headers={"Content-Length": None})
        with self.assertRaisesRegex(adapter.NetworkInputError, "MAX_RESPONSE_BYTES"):
            adapter.receive_fixture(self.url, config)

    def test_invalid_status_type_encoding_length_and_json(self):
        for raw, status, headers in (
            (RAW, 404, {}),
            (RAW, 200, {"Content-Type": "text/html"}),
            (RAW, 200, {"Content-Encoding": "gzip"}),
            (RAW, 200, {"Content-Length": "invalid"}),
            (RAW, 200, {"Content-Length": str(len(RAW) + 1)}),
            (b"not json", 200, {}),
            (b"\xff", 200, {}),
            (b'{"observations":[]}', 200, {}),
            (b'{"observations":[],"observations":[]}', 200, {}),
            (b'{"observations":[{"id":"x","baseline":NaN,"candidate":1}]}', 200, {}),
        ):
            with self.subTest(raw=raw, status=status, headers=headers):
                self.reply(raw, status=status, headers=headers)
                with self.assertRaises(adapter.NetworkInputError):
                    adapter.receive_fixture(self.url, self.config)

    def test_sector_normalization_discards_untrusted_metadata(self):
        sector = {
            "id": "sector", "timestamp": "2026-10-26T00:00:00Z",
            "metadata": {"input_provenance": "untrusted"},
            "sectors": [{"name": "recorded", "payload": {"baseline": {"value": 1}, "candidate": {"value": 2}}}],
        }
        self.assertEqual(json.loads(adapter.normalize_fixture(json.dumps(sector).encode())), FIXTURE)

    def test_configuration_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for data in (
                {"NETWORK_ENABLED": "false"}, {"ALLOWED_METHODS": ["POST"]},
                {"ALLOWED_HOSTS": ["*.invalid"]}, {"ALLOWED_HOSTS": "host"},
                {"TIMEOUT_SECONDS": 0}, {"MAX_RESPONSE_BYTES": True}, {"UNKNOWN": 1},
            ):
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.subTest(data=data), self.assertRaises(adapter.NetworkInputError):
                    adapter.NetworkConfig.load(path)
            path.write_text(json.dumps({"NETWORK_ENABLED": True, "ALLOWED_HOSTS": ["AUTHORIZED.invalid"]}))
            self.assertEqual(adapter.NetworkConfig.load(path).allowed_hosts, ("authorized.invalid",))

    def test_provenance_integrity_rejects_tampering_and_extra_secret_fields(self):
        normalized, provenance = adapter.receive_fixture(self.url, self.config)
        with self.assertRaises(adapter.NetworkInputError):
            adapter.validate_provenance(provenance, normalized + b" ")
        for changes in (
            {"raw_sha256": "bad"}, {"authorized_source": "https://authorized.invalid/path"},
            {"authorization": "secret"}, {"retrieval_status": 200.0}, {"retrieved_at": "bad"},
        ):
            with self.subTest(changes=changes), self.assertRaises(adapter.NetworkInputError):
                adapter.validate_provenance({**provenance, **changes}, normalized)

    def test_online_same_engine_signed_provenance_and_offline_replay(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            fixtures = root / "fixtures"
            fixtures.mkdir()
            for name, value in (("ROOT", root), ("RUNTIME", root), ("FIXTURES", fixtures)):
                stack.enter_context(patch.object(core, name, value))
            stack.enter_context(redirect_stdout(io.StringIO()))
            key = Ed25519PrivateKey.generate()
            key_path = root / "key.pem"
            key_path.write_bytes(key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ))
            db = root / "state.db"
            with patch.object(viper_matrix, "execute_matrix_sweep", wraps=viper_matrix.execute_matrix_sweep) as execute:
                report = adapter.run_online(self.url, "online-test", self.config, db_path=db, key_path=key_path)
                execute.assert_called_once()
            run_id = report["run_id"]
            self.assertEqual(report["case_id"], "online-test")
            self.assertTrue(core.verify_run_receipt(run_id, db))
            intent_path = next((root / "intents").iterdir())
            intent = json.loads(intent_path.read_text())
            with closing(core.connect_state_db(db)) as connection:
                content = json.loads(connection.execute(
                    "SELECT content_json FROM artifacts WHERE run_id=? AND stage='v1_recon'", (run_id,),
                ).fetchone()[0])
                self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(content["input_provenance"], intent["input_provenance"])
            self.assertEqual(content["fixture_sha256"], intent["input_provenance"]["normalized_fixture_sha256"])
            self.assertFalse(content["external_network_access"])
            self.factory.reset_mock()
            replay = core.execute(intent_path, db_path=db, key_path=key_path)
            self.assertTrue(core.verify_run_receipt(replay, db))
            self.factory.assert_not_called()
            intent["input_provenance"]["normalized_fixture_sha256"] = "0" * 64
            intent_path.write_text(json.dumps(intent))
            with self.assertRaises(adapter.NetworkInputError):
                core.load_inputs(intent_path)

    def test_online_patient_violation_survives_intake_and_signed_matrix(self):
        fixture = json.loads(
            (core.BUNDLED_FIXTURES / "patient_records_bola.json").read_text(encoding="utf-8")
        )
        self.reply(json.dumps(fixture).encode())
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            stack.enter_context(patch.object(core, "RUNTIME", root))
            stack.enter_context(patch.object(core, "FIXTURES", root / "fixtures"))
            key = Ed25519PrivateKey.generate()
            key_path = root / "key.pem"
            key_path.write_bytes(key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ))
            database = root / "state.db"
            report = adapter.run_online(
                self.url, "patient-online", self.config, db_path=database, key_path=key_path,
            )
            self.assertEqual(report["exit_code"], 1)
            self.assertEqual(report["status"], "FAULT_PATIENT_POLICY")
            self.assertTrue(core.verify_run_receipt(report["run_id"], database))
            with closing(core.connect_state_db(database)) as connection:
                rows = connection.execute(
                    "SELECT stage, content_json FROM artifacts WHERE run_id=? ORDER BY stage",
                    (report["run_id"],),
                ).fetchall()
            self.assertEqual(len(rows), 9)
            content = json.loads(rows[0]["content_json"])
            self.assertEqual(content["input_provenance"]["source_mode"], "online")
            self.assertEqual(
                content["input_provenance"]["normalized_fixture_sha256"],
                content["fixture_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
