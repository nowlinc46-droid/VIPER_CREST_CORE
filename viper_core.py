from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"
BUNDLED_FIXTURES = ROOT / "fixtures"
FIXTURES = RUNTIME / "fixtures"
DROPZONE = RUNTIME / "dropzone"
STATE_DB = RUNTIME / "viper_state.db"
KEY_PATH = RUNTIME / "signing_key.pem"
CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
DEFAULT_WEIGHTS = {
    "headers": 0.25,
    "content_length": 0.25,
    "json_schema": 0.25,
    "content": 0.25,
}
REVIEW_SCORE_THRESHOLD = 0.05


class IntentError(ValueError):
    pass


def _reject_json_constant(token: str) -> None:
    raise ValueError(f"Invalid JSON constant: {token}")


def canonical_json(data: Any) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise IntentError(f"Cannot read valid JSON from {path}: {exc}") from exc


def resolve_fixture(fixture_name: Any) -> Path:
    if not isinstance(fixture_name, str) or not fixture_name.endswith(".json"):
        raise IntentError("'fixture' must name a JSON file in fixtures or runtime/fixtures")
    if Path(fixture_name).name != fixture_name:
        raise IntentError("'fixture' must be a filename, not a path")
    fixture_root = FIXTURES
    if not (FIXTURES / fixture_name).exists() and (BUNDLED_FIXTURES / fixture_name).exists():
        fixture_root = BUNDLED_FIXTURES
    source_path = fixture_root / fixture_name
    if source_path.is_symlink():
        raise IntentError("Fixture symlinks are not allowed")
    fixture_path = source_path.resolve()
    if fixture_path.parent != fixture_root.resolve():
        raise IntentError("'fixture' must be a filename, not a path")
    return fixture_path


def flatten(value: Any, prefix: str = "$") -> dict[str, Any]:
    if isinstance(value, dict):
        if not value:
            return {prefix: {}}
        result: dict[str, Any] = {}
        for key in sorted(value):
            result.update(flatten(value[key], f"{prefix}.{key}"))
        return result
    if isinstance(value, list):
        if not value:
            return {prefix: []}
        result = {}
        for index, item in enumerate(value):
            result.update(flatten(item, f"{prefix}[{index}]"))
        return result
    return {prefix: value}


def compare_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diffs = []
    for observation in observations:
        name = observation["id"]
        baseline = flatten(observation["baseline"])
        candidate = flatten(observation["candidate"])
        for path in sorted(set(baseline) | set(candidate)):
            before = baseline.get(path, "<missing>")
            after = candidate.get(path, "<missing>")
            if before != after:
                diffs.append(
                    {
                        "observation": name,
                        "path": path,
                        "baseline": before,
                        "candidate": after,
                    }
                )
    return diffs


def json_schema(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: json_schema(child)
            for key, child in sorted(value.items())
        }
    if isinstance(value, list):
        schemas = {canonical_json(json_schema(child)) for child in value}
        return {"[]": [json.loads(schema) for schema in sorted(schemas)]}
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _headers(value: Any) -> dict[str, str]:
    headers = value.get("headers", {}) if isinstance(value, dict) else {}
    if not isinstance(headers, dict):
        return {}
    return {str(key).casefold(): str(item) for key, item in headers.items()}


def _body(value: Any) -> Any:
    return value.get("body", value) if isinstance(value, dict) else value


def _body_length(value: Any) -> int:
    body = _body(value)
    if isinstance(body, str):
        return len(body.encode("utf-8"))
    return len(canonical_json(body).encode("utf-8"))


def _content_length(value: Any) -> int:
    if isinstance(value, dict) and "content_length" in value:
        length = value["content_length"]
        if isinstance(length, bool) or not isinstance(length, (int, float)) or length < 0:
            raise IntentError("content_length must be a non-negative number")
        return int(length)
    return _body_length(value)


def _ratio_delta(before: Any, after: Any) -> float:
    paths = set(before) | set(after)
    changed = sum(before.get(path) != after.get(path) for path in paths)
    return changed / max(len(paths), 1)


def bounded_variance_score(
    baseline: Any,
    candidate: Any,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return a bounded structural-difference signal, not vulnerability probability."""
    selected_weights = dict(weights or DEFAULT_WEIGHTS)
    if set(selected_weights) != set(DEFAULT_WEIGHTS):
        raise ValueError(
            "weights must define headers, content_length, json_schema, and content"
        )
    if any(
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not math.isfinite(weight)
        or weight < 0
        for weight in selected_weights.values()
    ):
        raise ValueError("weights must be finite and non-negative")
    weight_total = sum(selected_weights.values())
    if weight_total <= 0:
        raise ValueError("at least one weight must be positive")

    before_headers = _headers(baseline)
    after_headers = _headers(candidate)
    header_keys = set(before_headers) | set(after_headers)
    changed_headers = sum(
        before_headers.get(key) != after_headers.get(key) for key in header_keys
    )
    header_delta = changed_headers / max(len(header_keys), 1)

    before_length = _content_length(baseline)
    after_length = _content_length(candidate)
    length_delta = abs(after_length - before_length) / max(before_length, after_length, 1)

    before_schema = json_schema(_body(baseline))
    after_schema = json_schema(_body(candidate))
    schema_delta = _ratio_delta(
        flatten(before_schema),
        flatten(after_schema),
    )
    before_content = flatten(_body(baseline))
    after_content = flatten(_body(candidate))
    content_delta = _ratio_delta(before_content, after_content)
    components = {
        "headers": min(max(header_delta, 0.0), 1.0),
        "content_length": min(max(length_delta, 0.0), 1.0),
        "json_schema": min(max(schema_delta, 0.0), 1.0),
        "content": min(max(content_delta, 0.0), 1.0),
    }
    score = sum(
        components[name] * selected_weights[name] for name in components
    ) / weight_total
    score = min(max(score, 0.0), 1.0)
    return {
        "score": score,
        "components": components,
        "interpretation": "bounded fixture-difference heuristic; not a probability or vulnerability verdict",
    }


def _fixture_schema_valid(data: Any) -> bool:
    if not isinstance(data, dict):
        return False

    if {"id", "timestamp", "sectors", "metadata"}.issubset(data):
        if (
            not isinstance(data["id"], str)
            or not data["id"].strip()
            or not isinstance(data["timestamp"], str)
            or not data["timestamp"].strip()
            or not isinstance(data["metadata"], dict)
            or not isinstance(data["sectors"], list)
        ):
            return False
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            return False
        return all(
            isinstance(sector, dict)
            and isinstance(sector.get("name"), str)
            and bool(sector["name"].strip())
            and isinstance(sector.get("payload"), dict)
            for sector in data["sectors"]
        )

    observations = data.get("observations")
    if not isinstance(observations, list):
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and bool(item["id"])
        and "baseline" in item
        and "candidate" in item
        for item in observations
    )


def validate_fixture_schema(fixture_path: Path) -> bool:
    """Validate supported fixture JSON formats confined to the local fixture directory."""
    if not isinstance(fixture_path, Path):
        return False
    try:
        resolved_path = fixture_path.resolve(strict=True)
        if (
            fixture_path.is_symlink()
            or resolved_path.parent not in {FIXTURES.resolve(), BUNDLED_FIXTURES.resolve()}
            or resolved_path.suffix.casefold() != ".json"
        ):
            return False
        data = json.loads(
            resolved_path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        KeyError,
        ValueError,
    ):
        return False
    return _fixture_schema_valid(data)


def _validate_fixture(fixture: Any, label: str = "Fixture") -> dict[str, Any]:
    if not _fixture_schema_valid(fixture):
        raise IntentError(
            f"{label} does not match the offline observations or sector fixture schema"
        )
    return fixture


def fixture_observations(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    if "observations" in fixture:
        observations = fixture["observations"]
    else:
        observations = []
        for sector in fixture["sectors"]:
            payload = sector["payload"]
            if isinstance(payload.get("observations"), list):
                observations.extend(payload["observations"])
            elif "baseline" in payload and "candidate" in payload:
                observations.append(
                    {
                        "id": payload.get("id", sector["name"]),
                        "baseline": payload["baseline"],
                        "candidate": payload["candidate"],
                    }
                )
    if not observations or any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not item["id"]
        or "baseline" not in item
        or "candidate" not in item
        for item in observations
    ):
        raise IntentError("Fixture contains no scoreable baseline/candidate observations")
    return observations


def load_inputs(intent_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    intent = load_json(intent_path.resolve())
    if not isinstance(intent, dict):
        raise IntentError("Intent must be a JSON object")
    case_id = intent.get("case_id")
    if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
        raise IntentError("'case_id' must be 1-80 safe filename characters")
    fixture_path = resolve_fixture(intent.get("fixture"))
    if not validate_fixture_schema(fixture_path):
        raise IntentError(f"Fixture schema validation failed: {fixture_path.name}")
    fixture = _validate_fixture(load_json(fixture_path))
    if "input_provenance" in intent:
        from network_adapter import validate_provenance

        validate_provenance(intent["input_provenance"], fixture_path.read_bytes())
    return intent, fixture, fixture_path


def initialize_state_db(db_path: Path = STATE_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                fixture_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                report_json TEXT NOT NULL,
                variance_score REAL,
                outcome TEXT NOT NULL DEFAULT 'SUCCESS',
                execution_duration_seconds REAL,
                peak_memory_delta_bytes INTEGER
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                stage TEXT NOT NULL,
                artifact_name TEXT NOT NULL,
                content_json TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                PRIMARY KEY (run_id, stage)
            );
            CREATE TABLE IF NOT EXISTS receipts (
                run_id TEXT PRIMARY KEY REFERENCES runs(run_id),
                algorithm TEXT NOT NULL,
                signed_payload TEXT NOT NULL,
                signature_hex TEXT NOT NULL,
                public_key_pem TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dropzone_intake (
                source_name TEXT PRIMARY KEY,
                fixture_name TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        run_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(runs)")
        }
        migrations = {
            "variance_score": "REAL",
            "outcome": "TEXT NOT NULL DEFAULT 'SUCCESS'",
            "execution_duration_seconds": "REAL",
            "peak_memory_delta_bytes": "INTEGER",
        }
        for column, declaration in migrations.items():
            if column not in run_columns:
                connection.execute(
                    f"ALTER TABLE runs ADD COLUMN {column} {declaration}"
                )
        connection.execute(
            """
            UPDATE runs
            SET outcome = CASE
                WHEN status IN ('MVP_PROOF_SECURED', 'human_review_required',
                                'low_variance_fixture_change')
                    THEN 'DRIFT_DETECTED'
                WHEN status IN ('FAULT', 'ERROR', 'FATAL')
                    THEN 'FAULT'
                ELSE 'SUCCESS'
            END
            WHERE outcome = 'SUCCESS'
              AND status IN ('MVP_PROOF_SECURED', 'human_review_required',
                             'low_variance_fixture_change', 'FAULT', 'ERROR', 'FATAL')
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS runs_created_at_idx ON runs(created_at)"
        )
        connection.commit()
    finally:
        connection.close()


def ensure_state_db(db_path: Path = STATE_DB) -> None:
    if not db_path.is_file():
        initialize_state_db(db_path)
        return

    connection = sqlite3.connect(db_path, timeout=30)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        columns = (
            {row[1] for row in connection.execute("PRAGMA table_info(runs)")}
            if "runs" in tables
            else set()
        )
    finally:
        connection.close()
    if not {
        "variance_score",
        "outcome",
        "execution_duration_seconds",
        "peak_memory_delta_bytes",
    }.issubset(columns):
        initialize_state_db(db_path)


def connect_state_db(db_path: Path = STATE_DB) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA synchronous = FULL")
    return connection


def query_run_analytics(db_path: Path = STATE_DB, limit: int = 30) -> dict[str, Any]:
    """Return local aggregate run counts, daily trends, and average variance."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 366:
        raise ValueError("limit must be an integer between 1 and 366")
    if not db_path.is_file():
        raise FileNotFoundError(f"State database does not exist: {db_path}")
    ensure_state_db(db_path)

    connection = connect_state_db(db_path)
    try:
        totals = connection.execute(
            """
            SELECT COUNT(*) AS total_runs,
                   AVG(variance_score) AS average_variance_score
            FROM runs
            """
        ).fetchone()
        trends = connection.execute(
            """
            SELECT substr(created_at, 1, 10) AS run_date,
                   COUNT(*) AS total_runs,
                   AVG(variance_score) AS average_variance_score,
                   SUM(CASE WHEN status = 'human_review_required' THEN 1 ELSE 0 END)
                       AS human_review_required
            FROM runs
            GROUP BY substr(created_at, 1, 10)
            ORDER BY run_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return {
            "total_runs": totals["total_runs"],
            "average_variance_score": totals["average_variance_score"],
            "daily_trends": [dict(row) for row in reversed(trends)],
        }
    finally:
        connection.close()


def ingest_dropzone(db_path: Path = STATE_DB) -> list[str]:
    DROPZONE.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    ensure_state_db(db_path)
    items = sorted(
        path for path in DROPZONE.iterdir()
        if (path.is_file() or path.is_symlink())
        and not (
            path.name == ".keep" and not path.is_symlink()
            and path.is_file() and path.stat().st_size == 0
        )
    )
    linked = [path.name for path in items if path.is_symlink()]
    if linked:
        raise IntentError("Dropzone does not accept symbolic links: " + ", ".join(linked))
    rejected = [path.name for path in items if path.suffix.casefold() != ".json"]
    if rejected:
        raise IntentError(
            "Dropzone accepts inert JSON fixture files only; rejected: "
            + ", ".join(rejected)
        )

    ingested = []
    copied_fixtures = []
    connection = connect_state_db(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            for source in items:
                fixture = _validate_fixture(load_json(source), f"Dropzone file {source.name}")
                fixture_name = source.name
                destination = (FIXTURES / fixture_name).resolve()
                if destination.parent != FIXTURES:
                    raise IntentError("Dropzone filename resolves outside the fixture directory")
                raw = source.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                existing = destination.read_bytes() if destination.exists() else None
                if existing is not None and existing != raw:
                    raise IntentError(f"Fixture already exists with different content: {fixture_name}")
                if existing is None:
                    shutil.copyfile(source, destination)
                    copied_fixtures.append(destination)
                connection.execute(
                    """
                    INSERT INTO dropzone_intake(source_name, fixture_name, sha256, ingested_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(source_name) DO UPDATE SET
                        fixture_name=excluded.fixture_name,
                        sha256=excluded.sha256,
                        ingested_at=excluded.ingested_at
                    """,
                    (
                        source.name,
                        fixture_name,
                        digest,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                ingested.append(fixture_name)
            connection.commit()
        except (IntentError, OSError, sqlite3.Error):
            connection.rollback()
            for destination in copied_fixtures:
                destination.unlink(missing_ok=True)
            raise
    finally:
        connection.close()
    return ingested


def init_signing_key() -> None:
    if KEY_PATH.exists():
        raise IntentError(f"Signing key already exists: {KEY_PATH}")
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    KEY_PATH.write_bytes(pem)
    print(f"Created local Ed25519 signing key: {KEY_PATH}")


def _load_private_key(key_path: Path = KEY_PATH) -> Ed25519PrivateKey:
    if not key_path.is_file():
        raise IntentError(
            "No signing key found. Run `python viper_core.py --init-signing-key` first."
        )
    try:
        private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except (OSError, ValueError) as exc:
        raise IntentError(f"Cannot load Ed25519 signing key: {exc}") from exc
    if not isinstance(private_key, Ed25519PrivateKey):
        raise IntentError("The local signing key is not Ed25519")
    return private_key


def save_run(
    run_id: str,
    case_id: str,
    fixture_name: str,
    report: dict[str, Any],
    artifacts: list[dict[str, Any]],
    private_key: Ed25519PrivateKey,
    db_path: Path = STATE_DB,
    session_metrics: dict[str, Any] | None = None,
) -> Path:
    from session_router import outcome_for_report, route_session

    prepared = []
    for artifact in artifacts:
        content_json = canonical_json(artifact["content"])
        prepared.append(
            {
                "stage": artifact["stage"],
                "artifact_name": artifact["artifact_name"],
                "content": artifact["content"],
                "content_json": content_json,
                "sha256": hashlib.sha256(content_json.encode("utf-8")).hexdigest(),
            }
        )
    manifest = [
        {
            "stage": artifact["stage"],
            "artifact_name": artifact["artifact_name"],
            "sha256": artifact["sha256"],
        }
        for artifact in prepared
    ]
    created_at = datetime.now(timezone.utc).isoformat()
    report_json = canonical_json(report)
    variance_score = report.get("variance_score")
    duration_seconds = (
        session_metrics.get("duration_seconds")
        if session_metrics is not None
        else None
    )
    peak_memory_delta_bytes = (
        session_metrics.get("peak_memory_delta_bytes")
        if session_metrics is not None
        else None
    )
    if duration_seconds is not None and (
        isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, (int, float))
        or duration_seconds < 0
    ):
        raise ValueError("duration_seconds must be a non-negative number or None")
    if peak_memory_delta_bytes is not None and (
        isinstance(peak_memory_delta_bytes, bool)
        or not isinstance(peak_memory_delta_bytes, int)
        or peak_memory_delta_bytes < 0
    ):
        raise ValueError("peak_memory_delta_bytes must be a non-negative integer or None")
    outcome = outcome_for_report(report, True)
    signed_run = {
        "run_id": run_id,
        "case_id": case_id,
        "fixture_name": fixture_name,
        "created_at": created_at,
        "status": report["status"],
        "variance_score": variance_score,
        "report_sha256": hashlib.sha256(report_json.encode("utf-8")).hexdigest(),
    }
    signed_payload = canonical_json({"run": signed_run, "artifacts": manifest})
    signature = private_key.sign(signed_payload.encode("utf-8")).hex()
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    connection = connect_state_db(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO runs(
                run_id, case_id, fixture_name, created_at, status, report_json,
                variance_score, outcome, execution_duration_seconds,
                peak_memory_delta_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                case_id,
                fixture_name,
                created_at,
                report["status"],
                report_json,
                variance_score,
                outcome,
                duration_seconds,
                peak_memory_delta_bytes,
            ),
        )
        connection.executemany(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    artifact["stage"],
                    artifact["artifact_name"],
                    artifact["content_json"],
                    artifact["sha256"],
                )
                for artifact in prepared
            ],
        )
        connection.execute(
            "INSERT INTO receipts VALUES (?, ?, ?, ?, ?)",
            (run_id, "Ed25519", signed_payload, signature, public_key_pem),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    receipt_valid = verify_run_receipt(run_id, db_path)
    if not receipt_valid:
        connection = connect_state_db(db_path)
        try:
            connection.execute(
                "UPDATE runs SET outcome = 'FAULT' WHERE run_id = ?", (run_id,)
            )
            connection.commit()
        finally:
            connection.close()
    session_dir = route_session(
        run={
            "run_id": run_id,
            "case_id": case_id,
            "fixture_name": fixture_name,
            "created_at": created_at,
            "status": report["status"],
            "variance_score": variance_score,
            "outcome": outcome_for_report(report, receipt_valid),
            "execution_duration_seconds": duration_seconds,
            "peak_memory_delta_bytes": peak_memory_delta_bytes,
        },
        report=report,
        artifacts=prepared,
        signed_payload=signed_payload,
        receipt_signature_hex=signature,
        public_key_pem=public_key_pem,
        private_key=private_key,
        receipt_valid=receipt_valid,
        duration_seconds=duration_seconds,
        peak_memory_delta_bytes=peak_memory_delta_bytes,
        sessions_root=db_path.absolute().parent / "sessions",
    )
    return session_dir


def verify_run_receipt(run_id: str, db_path: Path = STATE_DB) -> bool:
    if not db_path.is_file():
        return False
    ensure_state_db(db_path)
    connection = connect_state_db(db_path)
    try:
        receipt = connection.execute(
            "SELECT * FROM receipts WHERE run_id = ?", (run_id,)
        ).fetchone()
        run = connection.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        artifacts = connection.execute(
            "SELECT stage, artifact_name, content_json, sha256 FROM artifacts "
            "WHERE run_id = ? ORDER BY stage",
            (run_id,),
        ).fetchall()
        if receipt is None or run is None:
            return False
        manifest = []
        for artifact in artifacts:
            actual_digest = hashlib.sha256(
                artifact["content_json"].encode("utf-8")
            ).hexdigest()
            if actual_digest != artifact["sha256"]:
                return False
            manifest.append(
                {
                    "stage": artifact["stage"],
                    "artifact_name": artifact["artifact_name"],
                    "sha256": actual_digest,
                }
            )
        try:
            signed_document = json.loads(receipt["signed_payload"])
        except json.JSONDecodeError:
            return False
        actual_run = {
            "run_id": run["run_id"],
            "case_id": run["case_id"],
            "fixture_name": run["fixture_name"],
            "created_at": run["created_at"],
            "status": run["status"],
            "variance_score": run["variance_score"],
            "report_sha256": hashlib.sha256(
                run["report_json"].encode("utf-8")
            ).hexdigest(),
        }
        if signed_document != {"run": actual_run, "artifacts": manifest}:
            return False
        signed_payload = canonical_json(signed_document)
        try:
            public_key = serialization.load_pem_public_key(
                receipt["public_key_pem"].encode("ascii")
            )
        except (UnicodeEncodeError, ValueError, TypeError):
            return False
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        try:
            public_key.verify(
                bytes.fromhex(receipt["signature_hex"]),
                signed_payload.encode("utf-8"),
            )
        except (InvalidSignature, ValueError):
            return False
        return True
    finally:
        connection.close()


def execute(
    intent_path: Path,
    db_path: Path = STATE_DB,
    key_path: Path = KEY_PATH,
) -> str:
    from session_router import ExecutionMeter

    meter = ExecutionMeter()
    meter.start()
    try:
        return _execute_with_meter(intent_path, db_path, key_path, meter)
    finally:
        meter.finish()


def _execute_with_meter(
    intent_path: Path,
    db_path: Path,
    key_path: Path,
    meter: Any,
) -> str:
    ensure_state_db(db_path)
    intent, fixture, fixture_path = load_inputs(intent_path)
    observations = fixture_observations(fixture)
    diffs = compare_observations(observations)
    observed_paths = sorted({diff["path"] for diff in diffs})
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    case_id = intent["case_id"]
    scores = [
        {
            "observation": observation["id"],
            **bounded_variance_score(observation["baseline"], observation["candidate"]),
        }
        for observation in observations
    ]
    variance_score = sum(score["score"] for score in scores) / len(scores)
    requires_review = any(
        score["score"] >= REVIEW_SCORE_THRESHOLD for score in scores
    )

    report = {
        "case_id": case_id,
        "run_id": run_id,
        "status": (
            "human_review_required"
            if requires_review
            else "low_variance_fixture_change"
            if diffs
            else "no_fixture_differences"
        ),
        "vulnerability_confirmed": False,
        "difference_count": len(diffs),
        "variance_score": variance_score,
        "review_score_threshold": REVIEW_SCORE_THRESHOLD,
        "observed_difference_paths": observed_paths,
        "scores": scores,
        "limitations": [
            "Offline JSON fixtures only.",
            "Differences and scores are observations, not vulnerability findings.",
            "No live requests, endpoint discovery, or executable PoCs are performed.",
        ],
    }
    artifact_name = f"{run_id}.json"
    evidence = [
        (
            "v1_recon",
            {
                "case_id": case_id,
                "scope_type": "local_json_fixture",
                "fixture": fixture_path.name,
                "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
                "external_targets_allowed": False,
                "network_access": False,
            },
        ),
        (
            "v2_enumerate",
            {
                "case_id": case_id,
                "observation_ids": [item["id"] for item in observations],
                "changed_paths": observed_paths,
                "source": "offline fixture comparison",
            },
        ),
        ("v3_probe", {"case_id": case_id, "differences": diffs}),
        (
            "v4_validate",
            {
                "case_id": case_id,
                "observed_difference_paths": observed_paths,
                "scores": scores,
                "review_score_threshold": REVIEW_SCORE_THRESHOLD,
                "review_required": requires_review,
                "interpretation": "Bounded structural variance is heuristic and does not confirm vulnerabilities.",
            },
        ),
        (
            "v5_poc",
            {
                "case_id": case_id,
                "format": "offline-fixture-evidence-v1",
                "execution": "not_executed",
                "fixture": fixture_path.name,
                "differences": diffs,
                "safety": "Recorded JSON evidence only; no executable PoC or network actions.",
            },
        ),
        ("v7_ledger", report),
        (
            "v8_sandbox",
            {
                "case_id": case_id,
                "run_id": run_id,
                "network_requests": 0,
                "fixture": fixture_path.name,
                "rate_limit": "not_applicable_no_requests",
            },
        ),
    ]
    if "input_provenance" in intent:
        evidence[0][1]["input_provenance"] = dict(intent["input_provenance"])
    artifacts = [
        {
            "stage": stage,
            "artifact_name": artifact_name,
            "content": content,
        }
        for stage, content in evidence
    ]
    archive_content = {
        "case_id": case_id,
        "run_id": run_id,
        "archived_stages": [artifact["stage"] for artifact in artifacts],
        "storage": "sqlite",
        "database": db_path.name,
    }
    artifacts.append(
        {
            "stage": "v9_archive",
            "artifact_name": artifact_name,
            "content": archive_content,
        }
    )
    save_run(
        run_id,
        case_id,
        fixture_path.name,
        report,
        artifacts,
        _load_private_key(key_path),
        db_path,
        session_metrics=meter.finish(),
    )
    print(f"Completed offline fixture analysis in {db_path}: {run_id}")
    return run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze local JSON fixtures only; this tool never contacts targets."
    )
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--intent", type=Path, help="Path to a JSON intent file")
    actions.add_argument(
        "--init-signing-key",
        action="store_true",
        help="Create a local Ed25519 key in runtime",
    )
    actions.add_argument(
        "--init-state-db",
        action="store_true",
        help="Initialize the local SQLite WAL state database",
    )
    actions.add_argument(
        "--ingest-dropzone",
        action="store_true",
        help="Ingest inert fixture JSON files from runtime/dropzone",
    )
    actions.add_argument(
        "--analytics",
        action="store_true",
        help="Print local historical run aggregates from the SQLite WAL database",
    )
    args = parser.parse_args(argv)
    try:
        if args.init_signing_key:
            init_signing_key()
        elif args.init_state_db:
            initialize_state_db()
            print(f"Initialized SQLite WAL database: {STATE_DB}")
        elif args.ingest_dropzone:
            for fixture_name in ingest_dropzone():
                print(f"Ingested local fixture: {fixture_name}")
        elif args.analytics:
            print(json.dumps(query_run_analytics(), indent=2, sort_keys=True))
        else:
            execute(args.intent)
    except (IntentError, OSError, sqlite3.Error) as exc:
        print(f"ViperCrest error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

