from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import re
import sqlite3
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import viper_core


class NetworkInputError(viper_core.IntentError):
    pass


def _host(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NetworkInputError("ALLOWED_HOSTS must contain exact hostnames only")
    try:
        host = value.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise NetworkInputError("Invalid authorized hostname") from None
    if len(host) > 253 or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in host.split(".")
    ):
        raise NetworkInputError("Authorized hosts cannot include URLs, wildcards, or ports")
    return host


@dataclass(frozen=True)
class NetworkConfig:
    network_enabled: bool = False
    allowed_hosts: tuple[str, ...] = ()
    allowed_methods: tuple[str, ...] = ("GET",)
    timeout_seconds: float = 10.0
    max_response_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if not isinstance(self.network_enabled, bool):
            raise NetworkInputError("NETWORK_ENABLED must be a boolean")
        if not isinstance(self.allowed_hosts, tuple):
            raise NetworkInputError("ALLOWED_HOSTS must be an array of exact hostnames")
        object.__setattr__(self, "allowed_hosts", tuple(_host(host) for host in self.allowed_hosts))
        if self.allowed_methods != ("GET",):
            raise NetworkInputError("ALLOWED_METHODS supports GET only")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise NetworkInputError("TIMEOUT_SECONDS must be a positive finite number")
        if (
            isinstance(self.max_response_bytes, bool)
            or not isinstance(self.max_response_bytes, int)
            or self.max_response_bytes <= 0
        ):
            raise NetworkInputError("MAX_RESPONSE_BYTES must be a positive integer")

    @classmethod
    def load(cls, path: Path | None = None) -> NetworkConfig:
        if path is None:
            return cls()
        data = viper_core.load_json(path)
        names = {
            "NETWORK_ENABLED", "ALLOWED_HOSTS", "ALLOWED_METHODS",
            "TIMEOUT_SECONDS", "MAX_RESPONSE_BYTES",
        }
        if not isinstance(data, dict) or set(data) - names:
            raise NetworkInputError("Network configuration contains unknown fields")
        hosts = data.get("ALLOWED_HOSTS", [])
        methods = data.get("ALLOWED_METHODS", ["GET"])
        if not isinstance(hosts, list) or not isinstance(methods, list):
            raise NetworkInputError("ALLOWED_HOSTS and ALLOWED_METHODS must be arrays")
        return cls(
            network_enabled=data.get("NETWORK_ENABLED", False),
            allowed_hosts=tuple(hosts),
            allowed_methods=tuple(methods),
            timeout_seconds=data.get("TIMEOUT_SECONDS", 10.0),
            max_response_bytes=data.get("MAX_RESPONSE_BYTES", 1_048_576),
        )


def _destination(url: str, config: NetworkConfig) -> tuple[str, str]:
    if not config.network_enabled:
        raise NetworkInputError("Network input is disabled (NETWORK_ENABLED=false)")
    if (
        not isinstance(url, str)
        or not url
        or any(ord(char) <= 32 or ord(char) >= 127 for char in url)
        or "\\" in url
        or "#" in url
    ):
        raise NetworkInputError("Source must be an ASCII HTTPS URL without whitespace or fragments")
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https":
            raise NetworkInputError("HTTPS is required")
        if parsed.username is not None or parsed.password is not None:
            raise NetworkInputError("URL credentials are not supported")
        if parsed.port not in (None, 443) or parsed.netloc.endswith(":"):
            raise NetworkInputError("Only the standard HTTPS port 443 is supported")
        host = _host(parsed.hostname)
    except ValueError as exc:
        if isinstance(exc, NetworkInputError):
            raise
        raise NetworkInputError("Invalid HTTPS destination") from None
    if host not in config.allowed_hosts:
        raise NetworkInputError("Destination is not explicitly authorized by ALLOWED_HOSTS")
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query
    return host, target


def _content_type(header: str) -> str:
    media_type = header.split(";", 1)[0].strip().lower()
    if media_type != "application/json" and not re.fullmatch(
        r"application/[a-z0-9!#$&^_.+-]+\+json", media_type
    ):
        raise NetworkInputError("Response must have a JSON content type")
    return media_type


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NetworkInputError("Response JSON contains duplicate object keys")
        result[key] = value
    return result


def normalize_fixture(raw: bytes) -> bytes:
    try:
        fixture = json.loads(
            raw.decode("utf-8"),
            parse_constant=viper_core._reject_json_constant,
            object_pairs_hook=_unique_object,
        )
        viper_core._validate_fixture(fixture, "Network response")
        observations = viper_core.fixture_observations(fixture)
        normalized = {
            "observations": [
                {
                    key: observation[key]
                    for key in ("id", "baseline", "candidate", "context")
                    if key in observation
                }
                for observation in observations
            ]
        }
        return viper_core.canonical_json(normalized).encode("utf-8")
    except (UnicodeError, ValueError, RecursionError):
        # Do not echo remote JSON, keys, or decoder messages into diagnostics.
        raise NetworkInputError("Response is not a valid scoreable UTF-8 JSON fixture") from None


def validate_provenance(provenance: dict[str, Any], normalized: bytes) -> None:
    fields = {
        "source_mode", "authorized_source", "retrieval_status", "content_type",
        "retrieved_at", "raw_sha256", "normalized_fixture_sha256",
    }
    if not isinstance(provenance, dict) or set(provenance) != fields:
        raise NetworkInputError("Invalid network provenance fields")
    if (
        provenance["source_mode"] != "online"
        or type(provenance["retrieval_status"]) is not int
        or provenance["retrieval_status"] != 200
    ):
        raise NetworkInputError("Invalid network provenance mode or retrieval status")
    origin = provenance["authorized_source"]
    if not isinstance(origin, str) or not origin.startswith("https://"):
        raise NetworkInputError("Invalid authorized source in network provenance")
    host = _host(origin[len("https://"):])
    if origin != f"https://{host}":
        raise NetworkInputError("Network provenance must contain only a canonical HTTPS origin")
    media_type = provenance["content_type"]
    if not isinstance(media_type, str) or _content_type(media_type) != media_type:
        raise NetworkInputError("Invalid content type in network provenance")
    try:
        timestamp = datetime.fromisoformat(provenance["retrieved_at"])
    except (TypeError, ValueError):
        raise NetworkInputError("Invalid network retrieval timestamp") from None
    if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
        raise NetworkInputError("Network retrieval timestamp must be UTC")
    for name in ("raw_sha256", "normalized_fixture_sha256"):
        if not isinstance(provenance[name], str) or not re.fullmatch(r"[0-9a-f]{64}", provenance[name]):
            raise NetworkInputError("Invalid SHA-256 digest in network provenance")
    if provenance["normalized_fixture_sha256"] != hashlib.sha256(normalized).hexdigest():
        raise NetworkInputError("Normalized fixture does not match its network provenance")


def receive_fixture(
    url: str, config: NetworkConfig, *, method: str = "GET"
) -> tuple[bytes, dict[str, Any]]:
    host, target = _destination(url, config)
    if method != "GET" or method not in config.allowed_methods:
        raise NetworkInputError("Only explicitly allowed GET retrievals are supported")
    context = ssl.create_default_context()
    connection = http.client.HTTPSConnection(
        host, port=443, timeout=config.timeout_seconds, context=context
    )
    deadline = time.monotonic() + config.timeout_seconds
    try:
        connection.connect()
        response_socket = connection.sock

        def remaining_timeout() -> None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise NetworkInputError("Network retrieval timed out")
            if response_socket is not None:
                response_socket.settimeout(remaining)

        remaining_timeout()
        connection.request(
            method, target,
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
        )
        remaining_timeout()
        with connection.getresponse() as response:
            if 300 <= response.status < 400:
                raise NetworkInputError("Redirects are not allowed")
            if response.status != 200:
                raise NetworkInputError("Retrieval requires HTTP status 200")
            media_type = _content_type(response.getheader("Content-Type", ""))
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise NetworkInputError("Compressed response bodies are not supported")
            length = response.getheader("Content-Length")
            expected = None
            if length is not None:
                if not re.fullmatch(r"[0-9]{1,20}", length):
                    raise NetworkInputError("Invalid response Content-Length")
                expected = int(length)
                if expected > config.max_response_bytes:
                    raise NetworkInputError("Response exceeds MAX_RESPONSE_BYTES")
            raw = bytearray()
            while True:
                # getresponse may clear connection.sock for Connection: close.
                remaining_timeout()
                chunk = response.read1(min(65_536, config.max_response_bytes - len(raw) + 1))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > config.max_response_bytes:
                    raise NetworkInputError("Response exceeds MAX_RESPONSE_BYTES")
            remaining_timeout()
            if expected is not None and len(raw) != expected:
                raise NetworkInputError("Response body does not match Content-Length")
    except TimeoutError:
        raise NetworkInputError("Network connection/read timed out") from None
    except ssl.SSLError:
        raise NetworkInputError("HTTPS TLS verification or handshake failed") from None
    except (OSError, http.client.HTTPException):
        raise NetworkInputError("HTTPS connection or response failed") from None
    finally:
        connection.close()
    normalized = normalize_fixture(bytes(raw))
    if len(normalized) > config.max_response_bytes:
        raise NetworkInputError("Normalized fixture exceeds MAX_RESPONSE_BYTES")
    provenance = {
        "source_mode": "online",
        "authorized_source": f"https://{host}",
        "retrieval_status": 200,
        "content_type": media_type,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_fixture_sha256": hashlib.sha256(normalized).hexdigest(),
    }
    validate_provenance(provenance, normalized)
    return normalized, provenance


def run_online(
    url: str,
    case_id: str,
    config: NetworkConfig,
    *,
    db_path: Path = viper_core.STATE_DB,
    key_path: Path = viper_core.KEY_PATH,
) -> dict[str, Any]:
    from viper_matrix import execute_matrix_sweep

    _destination(url, config)
    if not isinstance(case_id, str) or not viper_core.CASE_ID_RE.fullmatch(case_id):
        raise NetworkInputError("'case_id' must be 1-80 safe filename characters")
    viper_core._load_private_key(key_path)
    intent_root = viper_core.RUNTIME / "intents"
    if intent_root.is_symlink():
        raise NetworkInputError("Intent directory symlinks are not allowed")
    normalized, provenance = receive_fixture(url, config)
    fixture_name = f"online_{provenance['normalized_fixture_sha256']}.json"
    fixture_path = viper_core.resolve_fixture(fixture_name)
    viper_core.FIXTURES.mkdir(parents=True, exist_ok=True)
    try:
        with fixture_path.open("xb") as stream:
            stream.write(normalized)
    except FileExistsError:
        if fixture_path.is_symlink() or fixture_path.read_bytes() != normalized:
            raise NetworkInputError("Normalized fixture destination contains different content") from None
    intent_root.mkdir(parents=True, exist_ok=True)
    intent_path = intent_root / f"online_{uuid4().hex}.json"
    with intent_path.open("x", encoding="utf-8") as stream:
        stream.write(viper_core.canonical_json({
            "case_id": case_id, "fixture": fixture_name, "input_provenance": provenance,
        }))
    return execute_matrix_sweep(
        fixture_path, db_path=db_path, key_path=key_path,
        case_id=case_id, input_provenance=provenance,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Receive one authorized HTTPS JSON fixture into the existing ViperCrest engine."
    )
    parser.add_argument("--url", required=True, help="Explicit authorized HTTPS fixture URL")
    parser.add_argument("--case-id", required=True, help="Local case identifier")
    parser.add_argument(
        "--config", type=Path, default=viper_core.ROOT / "network_config.json",
        help="Local JSON configuration; defaults to the installed network_config.json",
    )
    args = parser.parse_args(argv)
    try:
        report = run_online(args.url, args.case_id, NetworkConfig.load(args.config))
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"ViperCrest input error: {exc}", file=sys.stderr)
        return 2
    print(f"[VIPER] {report['status']}: {report['session_path']}")
    print("[VIPER] HTTPS intake and signed matrix evidence verified; no live-system security verdict.")
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
