import copy
import http.client
import json
import socket
import threading
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import viper_http
import viper_matrix
from viper_core import IntentError, canonical_json


class CircuitTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.fixture = {"observations": [{
            "id": "generic", "baseline": {"value": 1}, "candidate": {"value": 2},
        }]}
        self.envelope = {
            "sector_id": "F1",
            "stage": "v1_recon",
            "run_id": "http-test",
            "input_hash": viper_http.digest(self.fixture),
            "target_payload": self.fixture,
            "fixture_name": "fixture.json",
            "database_name": "state.db",
            "transport": "http",
        }

    def circuit(self, evaluator=viper_matrix.evaluate_matrix_sector):
        return viper_http.local_circuit(evaluator, self.key, "http-test", port=0)

    def request(self, client, body, path="/sector/f1", headers=None):
        connection = http.client.HTTPConnection(viper_http.HOST, client.port, timeout=2)
        try:
            connection.request(
                "POST", path, body=body,
                headers=headers if headers is not None else {
                    "Authorization": f"Bearer {client.token}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_real_round_trip_ignores_proxy_environment_and_verifies_receipt(self):
        with patch.dict("os.environ", {
            "HTTP_PROXY": "http://192.0.2.1:1",
            "http_proxy": "http://192.0.2.1:1", "NO_PROXY": "", "no_proxy": "",
        }):
            with self.circuit() as client:
                receipt = client.dispatch(1, self.envelope)
        self.assertEqual(receipt["content"]["fixture_sha256"], viper_http.digest(self.fixture))
        viper_http.verify_receipt(1, self.envelope, receipt, self.key.public_key())

    def test_evaluation_holds_and_signed_reply_returns_on_same_tcp_socket(self):
        entered = threading.Event()
        release = threading.Event()

        def evaluator(sector, envelope):
            entered.set()
            if not release.wait(2):
                raise IntentError("Test evaluation was not released")
            return viper_matrix.evaluate_matrix_sector(sector, envelope)

        with self.circuit(evaluator) as client:
            try:
                with socket.create_connection((viper_http.HOST, client.port), timeout=2) as wire:
                    body = canonical_json(self.envelope).encode("utf-8")
                    headers = (
                        "POST /sector/f1 HTTP/1.1\r\n"
                        f"Host: 127.0.0.1:{client.port}\r\n"
                        f"Authorization: Bearer {client.token}\r\n"
                        "Content-Type: application/json\r\n"
                        f"Content-Length: {len(body)}\r\n\r\n"
                    ).encode("ascii")
                    wire.sendall(headers + body)
                    self.assertTrue(entered.wait(2))
                    wire.settimeout(0.05)
                    with self.assertRaises(TimeoutError):
                        wire.recv(1)
                    release.set()
                    wire.settimeout(2)
                    response = http.client.HTTPResponse(wire)
                    response.begin()
                    self.assertEqual(response.status, 200)
                    receipt = json.loads(response.read())
                    viper_http.verify_receipt(1, self.envelope, receipt, self.key.public_key())
            finally:
                release.set()

    def test_server_rejects_invalid_routes_authorization_and_json(self):
        with self.circuit() as client:
            for path in ("/sector/f0", "/sector/f10", "/wrong/f1", "/sector/f1?x=1"):
                with self.subTest(path=path):
                    self.assertEqual(self.request(client, b"{}", path)[0], 404)
            self.assertEqual(self.request(client, b"{}", headers={})[0], 403)
            for body in (b"{", b"[]", b'{"x":NaN}', b"\xff", b"{}"):
                with self.subTest(body=body):
                    self.assertEqual(self.request(client, body)[0], 400)
            different_run = self.envelope | {"run_id": "other-run"}
            self.assertEqual(self.request(client, canonical_json(different_run).encode())[0], 400)
            self.assertEqual(
                self.request(client, canonical_json(self.envelope).encode(), "/sector/f2")[0], 400
            )

    def test_server_enforces_length_and_media_type(self):
        with self.circuit() as client:
            base = {"Authorization": f"Bearer {client.token}", "Content-Type": "application/json"}
            cases = [
                ({"Content-Length": "-1"}, 400),
                ({"Content-Length": "invalid"}, 400),
                ({"Content-Length": str(viper_http.MAX_BODY_BYTES + 1)}, 413),
                ({"Content-Length": "9" * 100}, 413),
                ({"Transfer-Encoding": "chunked"}, 400),
                ({"Content-Type": "text/plain"}, 415),
            ]
            for extra, expected in cases:
                with self.subTest(extra=extra):
                    self.assertEqual(self.request(client, b"{}", headers=base | extra)[0], expected)

    def test_signature_tampering_replay_wrong_sector_and_wrong_key_fail(self):
        receipt = viper_http.evaluate_envelope(
            1, self.envelope, viper_matrix.evaluate_matrix_sector, self.key
        )
        altered = copy.deepcopy(receipt)
        altered["content"]["fixture_sha256"] = "0" * 64
        for document, envelope, sector, key in (
            (altered, self.envelope, 1, self.key.public_key()),
            (receipt, self.envelope | {"input_hash": "0" * 64}, 1, self.key.public_key()),
            (receipt, self.envelope | {"run_id": "replay"}, 1, self.key.public_key()),
            (receipt, self.envelope, 2, self.key.public_key()),
            (receipt, self.envelope, 1, Ed25519PrivateKey.generate().public_key()),
        ):
            with self.subTest(sector=sector), self.assertRaises(IntentError):
                viper_http.verify_receipt(sector, envelope, document, key)

    def test_client_rejects_tampered_response_before_advancing(self):
        original = viper_http.evaluate_envelope

        def tamper(*args):
            receipt = original(*args)
            receipt["state_provenance"]["output_hash"] = "0" * 64
            return receipt

        with self.circuit() as client, patch.object(viper_http, "evaluate_envelope", side_effect=tamper):
            with self.assertRaisesRegex(IntentError, "receipt verification failed"):
                client.dispatch(1, self.envelope)

    def test_timeout_is_explicit_and_listener_is_closed(self):
        def evaluator(sector, envelope):
            release.wait(0.15)
            return viper_matrix.evaluate_matrix_sector(sector, envelope)

        release = threading.Event()
        # The peer may close on timeout, so suppress only the expected server socket-write log.
        with patch.object(viper_http.CircuitServer, "handle_error"):
            with self.circuit(evaluator) as client:
                client.timeout = 0.02
                port = client.port
                with self.assertRaisesRegex(IntentError, "Circuit F1 failed"):
                    client.dispatch(1, self.envelope)
                release.set()
        with self.assertRaises(OSError):
            socket.create_connection((viper_http.HOST, port), timeout=0.2)

    def test_oversized_request_and_occupied_port_fail(self):
        with self.circuit() as client:
            oversized = self.envelope | {"padding": "x" * viper_http.MAX_BODY_BYTES}
            with self.assertRaisesRegex(IntentError, "size limit"):
                client.dispatch(1, oversized)
            with self.assertRaises(OSError):
                with viper_http.local_circuit(
                    viper_matrix.evaluate_matrix_sector, self.key, "http-test", port=client.port
                ):
                    self.fail("Occupied port must not bind")

    def test_no_redirect_following(self):
        def redirect(handler):
            handler._reply(302, {"error": "redirect not allowed"})

        with self.circuit() as client, patch.object(viper_http.ViperCircuitHandler, "do_POST", redirect):
            with self.assertRaisesRegex(IntentError, "HTTP 302"):
                client.dispatch(1, self.envelope)

    def test_client_rejects_invalid_response_framing_json_and_media_type(self):
        cases = [
            ("application/json", str(viper_http.MAX_BODY_BYTES + 1), b"{}", "framing or size"),
            ("text/plain", "2", b"{}", "not application/json"),
            ("application/json", "1", b"{", "Circuit F1 failed"),
            ("application/json", "2", b"[]", "Circuit F1 failed"),
            ("application/json", "20", b"{}", "Incomplete circuit response"),
        ]
        for media_type, length, body, expected in cases:
            def reply(handler):
                handler.close_connection = True
                handler.send_response(200)
                handler.send_header("Content-Type", media_type)
                handler.send_header("Content-Length", length)
                handler.send_header("Connection", "close")
                handler.end_headers()
                handler.wfile.write(body)

            with self.subTest(expected=expected), self.circuit() as client:
                with patch.object(viper_http.ViperCircuitHandler, "do_POST", reply):
                    with self.assertRaisesRegex(IntentError, expected):
                        client.dispatch(1, self.envelope)
