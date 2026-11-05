from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
import re
import tempfile
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)


ROOT = Path(__file__).resolve().parent
SESSIONS_ROOT = ROOT / "runtime" / "sessions"
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
SESSION_ID = re.compile(
    r"^session_(\d{8}T\d{12}Z)_([A-Za-z0-9][A-Za-z0-9_.-]{0,159})$"
)
SESSION_FILES = {
    "session_meta.json",
    "execution_stack.ndjson",
    "state_delta.json",
    "receipts_audit.sig",
    "variance_metrics.csv",
}
MAX_SESSION_FILE_BYTES = 2 * 1024 * 1024
MAX_STACK_TRACE_CHARS = 2000


class ExecutionMeter:
    def __init__(self) -> None:
        self._started_at = 0.0
        self._owns_tracing = False
        self._finished = False
        self._metrics: dict[str, float | int | None] | None = None

    def start(self) -> None:
        self._started_at = time.perf_counter()
        self._owns_tracing = not tracemalloc.is_tracing()
        if self._owns_tracing:
            tracemalloc.start()

    def finish(self) -> dict[str, float | int | None]:
        if self._finished and self._metrics is not None:
            return self._metrics
        elapsed = max(0.0, time.perf_counter() - self._started_at)
        peak_delta: int | None = None
        if self._owns_tracing and tracemalloc.is_tracing():
            _, peak = tracemalloc.get_traced_memory()
            peak_delta = max(0, peak)
            tracemalloc.stop()
        self._metrics = {
            "duration_seconds": elapsed,
            "peak_memory_delta_bytes": peak_delta,
        }
        self._finished = True
        return self._metrics


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _session_timestamp(created_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Run timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("Run timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def session_folder_name(created_at: str, run_id: str) -> str:
    if not isinstance(run_id, str) or not SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError("Run identifier is not safe for session routing")
    return f"session_{_session_timestamp(created_at)}_{run_id}"


def outcome_for_report(report: dict[str, Any], receipt_valid: bool) -> str:
    if not receipt_valid:
        return "FAULT"
    status = report.get("status")
    if isinstance(status, str) and (
        status.upper() in {"FAULT", "ERROR", "FATAL"}
        or status.upper().startswith(("FAULT_", "ERROR_", "FATAL_"))
    ):
        return "FAULT"
    if status in {
        "MVP_PROOF_SECURED",
        "human_review_required",
        "low_variance_fixture_change",
    }:
        return "DRIFT_DETECTED"
    return "SUCCESS"


def _artifact_statuses(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for artifact in artifacts:
        if artifact["stage"] != "v3_probe":
            continue
        content = artifact["content"]
        pending = [content]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                status = item.get("status")
                if isinstance(status, str):
                    evidence.append(item)
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
    return evidence


def _filtered_events(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for item in _artifact_statuses(artifacts):
        status = item["status"]
        if status.startswith(("403_", "404_", "401_")):
            severity = "WARN"
        elif status.startswith(("FATAL_", "FATAL")):
            severity = "FATAL"
        elif status.startswith(("ERROR_", "ERROR", "500_")):
            severity = "ERROR"
        else:
            continue
        stack = item.get("stack_trace", "")
        if isinstance(stack, list):
            stack = "\n".join(str(frame) for frame in stack)
        if not isinstance(stack, str):
            stack = ""
        identifier = next(
            (
                item[key]
                for key in ("request_id", "instruction_id", "call_id", "command_id")
                if isinstance(item.get(key), (str, int))
            ),
            None,
        )
        events.append(
            {
                "severity": severity,
                "status": status,
                "event_id": identifier,
                "stack_trace": stack[:MAX_STACK_TRACE_CHARS],
            }
        )
    for artifact in artifacts:
        content = artifact.get("content")
        if (
            artifact["stage"] != "v3_probe"
            or not isinstance(content, dict)
            or content.get("evidence_type") != "minimum_viable_proof"
            or not isinstance(content.get("proof"), dict)
        ):
            continue
        proof = content["proof"]
        step = proof.get("step", {})
        result = proof.get("result", {})
        if not isinstance(step, dict):
            step = {}
        result_pair = {"status": result.get("status")} if isinstance(result, dict) else {}
        if isinstance(result, dict) and isinstance(result.get("state_diff"), dict):
            result_pair["state_diff"] = result["state_diff"]
        identifier = next(
            (
                step[key]
                for key in ("request_id", "instruction_id", "call_id", "command_id")
                if isinstance(step, dict) and isinstance(step.get(key), (str, int))
            ),
            None,
        )
        events.append(
            {
                "severity": "WARN",
                "status": "MVP_BOUNDARY_BYPASS",
                "event_id": identifier,
                "stack_trace": "",
                "expected_status": step.get("expected_status"),
                "observed_status": (
                    result.get("status") if isinstance(result, dict) else None
                ),
                "triggering_pair": {
                    "request": step,
                    "observed": result_pair,
                },
            }
        )
    return events


def _walk_state_diffs(value: Any):
    if isinstance(value, dict):
        diff = value.get("state_diff")
        if isinstance(diff, dict):
            yield value, diff
        for nested in value.values():
            yield from _walk_state_diffs(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_state_diffs(nested)


def _state_deltas(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deltas = []
    for artifact in artifacts:
        if artifact["stage"] != "v3_probe":
            continue
        for event, diff in _walk_state_diffs(artifact["content"]):
            identifier = next(
                (
                    event[key]
                    for key in ("request_id", "instruction_id", "call_id", "command_id")
                    if isinstance(event.get(key), (str, int))
                ),
                None,
            )
            base_key = ".".join(
                str(diff[key])
                for key in ("device_id", "pubkey", "register", "slot")
                if diff.get(key) is not None
            )
            if "before" in diff and "after" in diff and diff["before"] != diff["after"]:
                key = base_key or "state"
                before = diff["before"]
                after = diff["after"]
                deltas.append(
                    {
                        "event_id": identifier,
                        "key": key,
                        "before": before,
                        "after": after,
                        "before_sha256": _sha256(canonical_json(before).encode("utf-8")),
                        "after_sha256": _sha256(canonical_json(after).encode("utf-8")),
                    }
                )
            for name, before in diff.items():
                if not name.endswith("_before"):
                    continue
                after_name = name[:-7] + "_after"
                if after_name not in diff or before == diff[after_name]:
                    continue
                key = f"{base_key}.{name[:-7]}" if base_key else name[:-7]
                after = diff[after_name]
                deltas.append(
                    {
                        "event_id": identifier,
                        "key": key,
                        "before": before,
                        "after": after,
                        "before_sha256": _sha256(canonical_json(before).encode("utf-8")),
                        "after_sha256": _sha256(canonical_json(after).encode("utf-8")),
                    }
                )
    return deltas


def _merkle_root(hashes: list[str]) -> str:
    level = [bytes.fromhex(value) for value in hashes]
    if not level:
        return _sha256(b"")
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[index] + level[index + 1]).digest()
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()


def _seed_hash(artifacts: list[dict[str, Any]]) -> str:
    for artifact in artifacts:
        if artifact["stage"] == "v1_recon":
            content = artifact["content"]
            if isinstance(content, dict) and isinstance(content.get("fixture_sha256"), str):
                return content["fixture_sha256"]
    artifact_hashes = sorted(artifact["sha256"] for artifact in artifacts)
    return _sha256(canonical_json(artifact_hashes).encode("utf-8"))


def _write_text(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(content)


def route_session(
    *,
    run: dict[str, Any],
    report: dict[str, Any],
    artifacts: list[dict[str, Any]],
    signed_payload: str,
    receipt_signature_hex: str,
    public_key_pem: str,
    private_key: Ed25519PrivateKey,
    receipt_valid: bool,
    duration_seconds: float | None,
    peak_memory_delta_bytes: int | None,
    sessions_root: Path = SESSIONS_ROOT,
) -> Path:
    """Atomically write exactly the five allowlisted diagnostic files."""
    folder_name = session_folder_name(run["created_at"], run["run_id"])
    if sessions_root.is_symlink():
        raise ValueError("Session root symlinks are not allowed")
    sessions_root.mkdir(parents=True, exist_ok=True)
    resolved_root = sessions_root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError("Session root must be a directory")
    destination = resolved_root / folder_name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Session folder already exists: {destination.name}")

    artifact_hashes = sorted(
        (
            {
                "stage": artifact["stage"],
                "sha256": artifact["sha256"],
            }
            for artifact in artifacts
        ),
        key=lambda item: item["stage"],
    )
    outcome = outcome_for_report(report, receipt_valid)
    meta = {
        "run_id": run["run_id"],
        "case_id": run["case_id"],
        "domain": report.get("domain", run["case_id"].split("-", 1)[0]),
        "created_at": run["created_at"],
        "seed_sha256": _seed_hash(artifacts),
        "exit_status": report.get("status", outcome),
        "outcome": outcome,
        "receipt_valid": receipt_valid,
    }
    events = _filtered_events(artifacts)
    deltas = _state_deltas(artifacts)
    audit_payload = {
        "run_id": run["run_id"],
        "payload_sha256": _sha256(signed_payload.encode("utf-8")),
        "receipt_signature_sha256": _sha256(bytes.fromhex(receipt_signature_hex)),
        "artifact_hashes": artifact_hashes,
        "merkle_root": _merkle_root([item["sha256"] for item in artifact_hashes]),
        "receipt_verification": "VALID" if receipt_valid else "TAMPERED",
        "signature_algorithm": "Ed25519",
        "trusted_public_key_pem": public_key_pem,
    }
    session_file_contents = {
        "session_meta.json": json.dumps(
            meta, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        "execution_stack.ndjson": "".join(
            canonical_json(event) + "\n" for event in events
        ),
        "state_delta.json": json.dumps(
            {"deltas": deltas}, indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        "variance_metrics.csv": "",
    }
    audit_payload["session_files_sha256"] = {
        name: _sha256(content.encode("utf-8"))
        for name, content in session_file_contents.items()
        if name != "variance_metrics.csv"
    }
    csv_buffer = StringIO(newline="")
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=(
            "run_id",
            "duration_seconds",
            "peak_memory_delta_bytes",
            "variance_score",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerow(
        {
            "run_id": run["run_id"],
            "duration_seconds": duration_seconds,
            "peak_memory_delta_bytes": peak_memory_delta_bytes,
            "variance_score": report.get("variance_score"),
        }
    )
    session_file_contents["variance_metrics.csv"] = csv_buffer.getvalue()
    audit_payload["session_files_sha256"]["variance_metrics.csv"] = _sha256(
        session_file_contents["variance_metrics.csv"].encode("utf-8")
    )
    audit_signature = private_key.sign(
        canonical_json(audit_payload).encode("utf-8")
    ).hex()
    audit = audit_payload | {"audit_signature_hex": audit_signature}
    with tempfile.TemporaryDirectory(prefix=".session-", dir=resolved_root) as temporary:
        temporary_folder = Path(temporary) / folder_name
        temporary_folder.mkdir()
        for filename in (
            "session_meta.json",
            "execution_stack.ndjson",
            "state_delta.json",
        ):
            _write_text(
                temporary_folder / filename,
                session_file_contents[filename],
            )
        _write_text(
            temporary_folder / "receipts_audit.sig",
            json.dumps(audit, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        )
        _write_text(
            temporary_folder / "variance_metrics.csv",
            session_file_contents["variance_metrics.csv"],
        )
        if {path.name for path in temporary_folder.iterdir()} != SESSION_FILES:
            raise RuntimeError("Session output did not match the five-file schema")
        temporary_folder.rename(destination)
    return destination


def load_session(
    session_id: str,
    *,
    sessions_root: Path = SESSIONS_ROOT,
    trusted_key_path: Path,
) -> dict[str, Any]:
    if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
        raise ValueError("Invalid session identifier")
    if sessions_root.is_symlink():
        raise ValueError("Session root symlinks are not allowed")
    root = sessions_root.resolve(strict=True)
    folder = root / session_id
    if folder.is_symlink():
        raise ValueError("Session folder symlinks are not allowed")
    resolved_folder = folder.resolve(strict=True)
    if resolved_folder.parent != root or not resolved_folder.is_dir():
        raise ValueError("Session folder is outside the configured session root")
    entries = list(resolved_folder.iterdir())
    if (
        any(path.is_symlink() or not path.is_file() for path in entries)
        or {path.name for path in entries} != SESSION_FILES
    ):
        raise ValueError("Session folder does not match the exact five-file schema")
    contents: dict[str, bytes] = {}
    for name in SESSION_FILES:
        path = resolved_folder / name
        if path.stat().st_size > MAX_SESSION_FILE_BYTES:
            raise ValueError(f"Session file exceeds size limit: {name}")
        contents[name] = path.read_bytes()

    try:
        meta = json.loads(contents["session_meta.json"])
        raw_events = contents["execution_stack.ndjson"].decode("utf-8")
        events = [json.loads(line) for line in raw_events.splitlines() if line]
        state_delta = json.loads(contents["state_delta.json"])
        audit = json.loads(contents["receipts_audit.sig"])
        metrics_rows = list(
            csv.DictReader(contents["variance_metrics.csv"].decode("utf-8").splitlines())
        )
    except (UnicodeDecodeError, json.JSONDecodeError, csv.Error) as exc:
        raise ValueError(f"Session bundle contains malformed data: {exc}") from exc

    if (
        not isinstance(meta, dict)
        or not isinstance(state_delta, dict)
        or not isinstance(state_delta.get("deltas"), list)
        or not isinstance(audit, dict)
        or not isinstance(events, list)
        or any(
            not isinstance(event, dict)
            or event.get("severity") not in {"WARN", "ERROR", "FATAL"}
            for event in events
        )
        or len(metrics_rows) != 1
        or metrics_rows[0].get("run_id") != meta.get("run_id")
    ):
        raise ValueError("Session files do not match the expected data schema")
    expected_folder_name = session_folder_name(meta.get("created_at"), meta.get("run_id"))
    if expected_folder_name != session_id:
        raise ValueError("Session metadata does not match its folder identity")
    signature_hex = audit.pop("audit_signature_hex", None)
    if not isinstance(signature_hex, str):
        audit_signature_valid = False
    else:
        try:
            private_key_bytes = trusted_key_path.read_bytes()
            trusted_private_key = serialization.load_pem_private_key(
                private_key_bytes, password=None
            )
            if not isinstance(trusted_private_key, Ed25519PrivateKey):
                audit_signature_valid = False
            else:
                trusted_public_key = trusted_private_key.public_key()
                expected_public_pem = trusted_public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                ).decode("ascii")
                embedded_key = audit.get("trusted_public_key_pem")
                if embedded_key != expected_public_pem:
                    audit_signature_valid = False
                else:
                    trusted_public_key.verify(
                        bytes.fromhex(signature_hex),
                        canonical_json(audit).encode("utf-8"),
                    )
                    audit_signature_valid = True
        except (OSError, ValueError, TypeError, UnicodeDecodeError, InvalidSignature):
            audit_signature_valid = False
    audit["audit_signature_hex"] = signature_hex
    metrics = metrics_rows[0] if len(metrics_rows) == 1 else None
    file_hashes = audit.get("session_files_sha256")
    files_valid = isinstance(file_hashes, dict) and all(
        file_hashes.get(name) == _sha256(contents[name])
        for name in SESSION_FILES - {"receipts_audit.sig"}
    )
    return {
        "session_id": session_id,
        "folder": resolved_folder,
        "meta": meta,
        "events": events,
        "mvp_proof": next(
            (
                event["triggering_pair"]
                for event in events
                if isinstance(event.get("triggering_pair"), dict)
            ),
            None,
        ),
        "state_delta": state_delta,
        "audit": audit,
        "audit_signature_valid": audit_signature_valid and files_valid,
        "metrics": metrics,
    }
