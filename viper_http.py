from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import logging
import math
import re
import secrets
import socket
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Iterator

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from viper_core import IntentError, canonical_json


HOST = "127.0.0.1"
PORT = 8787
MAX_BODY_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 5.0
LOGGER = logging.getLogger(__name__)
Evaluator = Callable[[int, dict[str, Any]], dict[str, Any]]


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def decode_document(data: bytes) -> dict[str, Any]:
    document = json.loads(data.decode("utf-8"), parse_constant=_reject_constant)
    if not isinstance(document, dict):
        raise ValueError("Circuit document must be a JSON object")
    return document


def evaluate_envelope(
    sector: int,
    envelope: dict[str, Any],
    evaluator: Evaluator,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if (
        type(sector) is not int or not 1 <= sector <= 9
        or envelope.get("sector_id") != f"F{sector}"
        or not isinstance(envelope.get("run_id"), str)
        or not envelope["run_id"]
        or not isinstance(envelope.get("input_hash"), str)
        or re.fullmatch(r"[0-9a-f]{64}", envelope["input_hash"]) is None
        or not isinstance(envelope.get("target_payload"), dict)
        or not isinstance(envelope.get("stage"), str)
    ):
        raise IntentError("Invalid circuit sector, run identity, payload, or input hash")
    content = evaluator(sector, envelope)
    transition = {
        "input_hash": envelope["input_hash"],
        "stage": envelope["stage"],
        "content": content,
    }
    receipt = {
        "icon_uri": f"icon://sector/f{sector}/verdict",
        "sector_id": f"F{sector}",
        "run_id": envelope["run_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_hash": digest(envelope),
        "content": content,
        "state_provenance": {
            "input_hash": envelope["input_hash"],
            "output_hash": digest(transition),
        },
        "signature_algorithm": "Ed25519",
    }
    return receipt | {"signature_hex": private_key.sign(canonical_json(receipt).encode("utf-8")).hex()}


def verify_receipt(
    sector: int,
    envelope: dict[str, Any],
    receipt: dict[str, Any],
    public_key: Ed25519PublicKey,
) -> None:
    unsigned = dict(receipt)
    signature = unsigned.pop("signature_hex", None)
    try:
        if not isinstance(signature, str):
            raise ValueError("Missing signature")
        public_key.verify(bytes.fromhex(signature), canonical_json(unsigned).encode("utf-8"))
        content = receipt.get("content")
        provenance = receipt.get("state_provenance")
        if (
            receipt.get("signature_algorithm") != "Ed25519"
            or receipt.get("sector_id") != f"F{sector}"
            or receipt.get("run_id") != envelope["run_id"]
            or receipt.get("request_hash") != digest(envelope)
            or not isinstance(content, dict)
            or provenance != {
                "input_hash": envelope["input_hash"],
                "output_hash": digest({
                    "input_hash": envelope["input_hash"],
                    "stage": envelope["stage"],
                    "content": content,
                }),
            }
        ):
            raise ValueError("Receipt does not match request or state transition")
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise IntentError(f"Circuit receipt verification failed for F{sector}: {exc}") from exc


class ViperCircuitHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: CircuitServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(TIMEOUT_SECONDS)

    def _reply(self, status: int, document: dict[str, Any]) -> None:
        body = canonical_json(document).encode("utf-8")
        if len(body) > MAX_BODY_BYTES:
            status = 413
            body = b'{"error":"Circuit response exceeds size limit"}'
        if status >= 400:
            LOGGER.warning("Loopback circuit rejected request: HTTP %s", status)
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        match = re.fullmatch(r"/sector/f([1-9])", self.path)
        if match is None:
            self._reply(404, {"error": "Unknown sector endpoint"})
            return
        authorization = self.headers.get("Authorization", "")
        if not authorization.isascii() or not hmac.compare_digest(
            authorization, f"Bearer {self.server.token}"
        ):
            self._reply(403, {"error": "Invalid circuit authorization"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") is not None or len(lengths) != 1:
            self._reply(400, {"error": "Exactly one Content-Length and no Transfer-Encoding required"})
            return
        if not lengths[0].isascii() or not lengths[0].isdigit():
            self._reply(400, {"error": "Invalid Content-Length"})
            return
        # Compare length before conversion so arbitrarily long integer strings stay bounded.
        if len(lengths[0]) > 8 or int(lengths[0]) > MAX_BODY_BYTES:
            self._reply(413, {"error": "Circuit request exceeds size limit"})
            return
        if self.headers.get_content_type() != "application/json":
            self._reply(415, {"error": "application/json required"})
            return
        try:
            size = int(lengths[0])
            data = self.rfile.read(size)
            if len(data) != size:
                raise ValueError("Incomplete circuit body")
            envelope = decode_document(data)
            if envelope.get("run_id") != self.server.run_id:
                raise ValueError("Envelope belongs to another run")
            receipt = evaluate_envelope(
                int(match[1]), envelope, self.server.evaluator, self.server.private_key
            )
        except (ValueError, UnicodeError, RecursionError) as exc:
            self._reply(400, {"error": str(exc)})
            return
        except OSError:
            LOGGER.exception("Circuit evaluation or read failed")
            self._reply(500, {"error": "Circuit evaluation or read failed"})
            return
        self._reply(200, receipt)

    def do_GET(self) -> None:
        self._reply(405, {"error": "POST required"})

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.debug(format, *args)


class CircuitServer(HTTPServer):
    allow_reuse_address = False

    def shutdown_request(self, request: socket.socket) -> None:
        # Windows can reset a rejected request with unread data before its reply arrives.
        try:
            request.shutdown(socket.SHUT_WR)
            deadline = time.monotonic() + 0.2
            remaining_bytes = MAX_BODY_BYTES + 1
            while remaining_bytes > 0:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    LOGGER.debug("Loopback peer drain deadline reached")
                    break
                request.settimeout(remaining_time)
                chunk = request.recv(min(65_536, remaining_bytes))
                if not chunk:
                    break
                remaining_bytes -= len(chunk)
        except (TimeoutError, ConnectionError) as exc:
            LOGGER.debug("Loopback peer closed or timed out during drain: %s", exc)
        finally:
            self.close_request(request)

    def server_bind(self) -> None:
        # Windows otherwise permits another SO_REUSEADDR listener on this port.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(
        self, port: int, evaluator: Evaluator, private_key: Ed25519PrivateKey, run_id: str
    ) -> None:
        self.evaluator = evaluator
        self.private_key = private_key
        self.run_id = run_id
        self.token = secrets.token_hex(32)
        super().__init__((HOST, port), ViperCircuitHandler)


class CircuitClient:
    def __init__(self, server: CircuitServer, timeout: float) -> None:
        self.port = server.server_port
        self.token = server.token
        self.public_key = server.private_key.public_key()
        self.timeout = timeout

    def dispatch(self, sector: int, envelope: dict[str, Any]) -> dict[str, Any]:
        body = canonical_json(envelope).encode("utf-8")
        if len(body) > MAX_BODY_BYTES:
            raise IntentError("Circuit request exceeds size limit")
        connection = http.client.HTTPConnection(HOST, self.port, timeout=self.timeout)
        try:
            connection.request(
                "POST", f"/sector/f{sector}", body=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise IntentError(f"Circuit F{sector} returned HTTP {response.status}")
            if response.getheader("Content-Type") != "application/json":
                raise IntentError("Circuit response is not application/json")
            length = response.getheader("Content-Length", "")
            if (
                response.getheader("Transfer-Encoding") is not None
                or not length.isascii() or not length.isdigit()
                or len(length) > 8 or int(length) > MAX_BODY_BYTES
            ):
                raise IntentError("Invalid circuit response framing or size")
            data = response.read(MAX_BODY_BYTES + 1)
            if len(data) != int(length):
                raise IntentError("Incomplete circuit response")
            receipt = decode_document(data)
            verify_receipt(sector, envelope, receipt, self.public_key)
            return receipt
        except (OSError, http.client.HTTPException, ValueError, UnicodeError, RecursionError) as exc:
            raise IntentError(f"Circuit F{sector} failed: {exc}") from exc
        finally:
            connection.close()


@contextmanager
def local_circuit(
    evaluator: Evaluator,
    private_key: Ed25519PrivateKey,
    run_id: str,
    *,
    port: int = PORT,
    timeout: float = TIMEOUT_SECONDS,
) -> Iterator[CircuitClient]:
    if type(port) is not int or not 0 <= port <= 65535:
        raise IntentError("Circuit port must be between 0 and 65535")
    if not math.isfinite(timeout) or timeout <= 0:
        raise IntentError("Circuit timeout must be positive and finite")
    with CircuitServer(port, evaluator, private_key, run_id) as server:
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.05},
            name="viper-loopback-circuit",
        )
        thread.start()
        try:
            yield CircuitClient(server, timeout)
        finally:
            server.shutdown()
            thread.join()
