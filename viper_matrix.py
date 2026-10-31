from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
import tempfile
import uuid
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from session_router import ExecutionMeter, load_session
from viper_http import PORT, evaluate_envelope, local_circuit, verify_receipt
from viper_core import (
    KEY_PATH,
    CASE_ID_RE,
    REVIEW_SCORE_THRESHOLD,
    STATE_DB,
    IntentError,
    _load_private_key,
    _validate_fixture,
    bounded_variance_score,
    canonical_json,
    compare_observations,
    ensure_state_db,
    fixture_observations,
    load_json,
    save_run,
    verify_run_receipt,
)


def response_satisfies_read_policy(
    response: Any, caller: Any, patient: Any
) -> bool:
    """Evaluate the explicit offline tenant-and-assignment patient read policy."""
    if (
        not isinstance(caller, dict)
        or not isinstance(patient, dict)
        or any(
            not isinstance(value, str) or not value
            for value in (
                caller.get("tenant_id"),
                patient.get("tenant_id"),
                patient.get("patient_id"),
            )
        )
        or not isinstance(caller.get("assigned_patient_ids"), list)
        or any(
            not isinstance(item, str) or not item
            for item in caller["assigned_patient_ids"]
        )
        or not isinstance(response, dict)
        or type(response.get("status_code")) is not int
        or not 100 <= response["status_code"] <= 599
    ):
        raise IntentError("Patient policy requires valid caller, patient, and HTTP response data")
    if (
        caller["tenant_id"] != patient["tenant_id"]
        or patient["patient_id"] not in caller["assigned_patient_ids"]
    ):
        return response["status_code"] in {403, 404}
    if response["status_code"] != 200:
        return False
    body = response.get("body")
    if not isinstance(body, dict) or body.get("patient_id") != patient["patient_id"]:
        return False
    records = body.get("data")
    return isinstance(records, list) and all(
        isinstance(record, dict)
        and record.get("patient_id") == patient["patient_id"]
        and record.get("tenant_id") == patient["tenant_id"]
        for record in records
    )


def evaluate_patient_observation(observation: dict[str, Any]) -> dict[str, Any]:
    context = observation.get("context")
    result: dict[str, Any] = {"observation": observation["id"]}
    if context is not None and not isinstance(context, dict):
        raise IntentError("Observation context must be an object")
    if not isinstance(context, dict) or not (
        {"caller", "requested_patient"} & context.keys()
    ):
        return result | {
            "status": "NOT_APPLICABLE",
            "reason": "No explicit patient tenant-and-assignment policy context.",
        }
    allowed = response_satisfies_read_policy(
        observation["candidate"], context.get("caller"), context.get("requested_patient")
    )
    return result | {
        "status": "PASSED" if allowed else "ERROR_PATIENT_POLICY",
        "reason": "Candidate satisfies policy." if allowed else "Candidate violates patient read policy.",
        "state_diff": {
            "before": observation["baseline"],
            "after": observation["candidate"],
        },
    }


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


STAGES = (
    "v1_recon", "v2_enumerate", "v3_probe", "v4_validate", "v5_poc",
    "v6_sign", "v7_ledger", "v8_sandbox", "v9_archive",
)


def _assess_fixture(
    fixture: dict[str, Any], run_id: str, transport: str,
    case_id: str = "matrix-offline",
) -> dict[str, Any]:
    observations = fixture_observations(fixture)
    policies = [evaluate_patient_observation(item) for item in observations]
    diffs = compare_observations(observations)
    scores = [
        {
            "observation": item["id"],
            **bounded_variance_score(item["baseline"], item["candidate"]),
        }
        for item in observations
    ]
    failed = any(item["status"] == "ERROR_PATIENT_POLICY" for item in policies)
    review = any(item["score"] >= REVIEW_SCORE_THRESHOLD for item in scores)
    return {
        "domain": "matrix",
        "run_id": run_id,
        "case_id": case_id,
        "status": (
            "FAULT_PATIENT_POLICY" if failed else
            "human_review_required" if review else
            "low_variance_fixture_change" if diffs else "no_fixture_differences"
        ),
        "exit_code": 1 if failed else 0,
        "variance_score": sum(item["score"] for item in scores) / len(scores),
        "difference_count": len(diffs),
        "policy_checks": policies,
        "transport": transport,
        "vulnerability_confirmed": False,
        "limitations": [
            "Offline fixture evaluation only; no external network requests or live-system findings.",
            "Sequential dependent stages, not nine independent concurrent evaluators.",
            "Authorization checks apply only to explicit patient tenant-and-assignment context.",
            "Structural variance is a review signal, not a vulnerability probability.",
        ],
    }


def evaluate_matrix_sector(sector: int, envelope: dict[str, Any]) -> dict[str, Any]:
    if (
        envelope.get("stage") != STAGES[sector - 1]
        or envelope.get("transport") not in {"direct", "http"}
        or any(
            not isinstance(envelope.get(field), str) or not envelope[field]
            for field in ("fixture_name", "database_name")
        )
    ):
        raise IntentError("Invalid circuit stage or fixture metadata")
    fixture = _validate_fixture(envelope["target_payload"])
    observations = fixture_observations(fixture)
    if sector == 1:
        content: dict[str, Any] = {
            "fixture": envelope["fixture_name"],
            "fixture_sha256": _sha256(fixture),
            "hash_basis": "canonical_json",
            "external_network_access": False,
        }
        if "input_provenance" in envelope:
            from network_adapter import validate_provenance

            validate_provenance(
                envelope["input_provenance"], canonical_json(fixture).encode("utf-8")
            )
            content["input_provenance"] = envelope["input_provenance"]
        return content
    if sector == 2:
        return {"observation_ids": [item["id"] for item in observations]}
    if sector == 3:
        return {
            "differences": compare_observations(observations),
            "policy_checks": [evaluate_patient_observation(item) for item in observations],
        }
    if sector == 4:
        scores = [
            {
                "observation": item["id"],
                **bounded_variance_score(item["baseline"], item["candidate"]),
            }
            for item in observations
        ]
        return {
            "scores": scores,
            "review_required": any(item["score"] >= REVIEW_SCORE_THRESHOLD for item in scores),
        }
    if sector == 5:
        return {"execution": "not_executed", "evidence": "offline fixture only"}
    if sector == 6:
        return {
            "signature_algorithm": "Ed25519",
            "checkpoint_input_hash": envelope["input_hash"],
            "final_manifest_signing": "performed by save_run after F9",
        }
    if sector == 7:
        return _assess_fixture(
            fixture, envelope["run_id"], envelope["transport"],
            envelope.get("case_id", "matrix-offline"),
        )
    if sector == 8:
        return {
            "external_network_requests": 0,
            "loopback_sector_requests": 9 if envelope["transport"] == "http" else 0,
            "execution_mode": "sequential",
        }
    return {"storage": "sqlite", "database": envelope["database_name"]}


def execute_matrix_sweep(
    target_path: Path,
    *,
    db_path: Path = STATE_DB,
    key_path: Path = KEY_PATH,
    transport: str = "direct",
    http_port: int = PORT,
    case_id: str = "matrix-offline",
    input_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate each dependent stage locally or over a held loopback HTTP request."""
    if transport not in {"direct", "http"}:
        raise IntentError("Matrix transport must be direct or http")
    if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
        raise IntentError("'case_id' must be 1-80 safe filename characters")
    fixture = _validate_fixture(load_json(target_path))
    if input_provenance is not None:
        from network_adapter import validate_provenance

        validate_provenance(input_provenance, canonical_json(fixture).encode("utf-8"))
    run_id = f"matrix-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex}"
    # Reject invalid policy/score inputs before starting a listener or persisting anything.
    _assess_fixture(fixture, run_id, transport)
    private_key = _load_private_key(key_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    staging_root = db_path.parent / "staging"
    if staging_root.is_symlink():
        raise IntentError("Matrix staging root symlinks are not allowed")
    staging_root.mkdir(exist_ok=True)
    meter = ExecutionMeter()
    meter.start()
    try:
        circuit_context = (
            local_circuit(evaluate_matrix_sector, private_key, run_id, port=http_port)
            if transport == "http" else nullcontext(None)
        )
        with tempfile.TemporaryDirectory(prefix=f"{run_id}-", dir=staging_root) as temporary, circuit_context as circuit:
            parent_hash = _sha256(fixture)
            artifacts = []
            report: dict[str, Any] = {}
            for sector, stage in enumerate(STAGES, 1):
                envelope = {
                    "icon_uri": f"icon://sector/f{sector}/evaluate",
                    "run_id": run_id,
                    "case_id": case_id,
                    "sector_id": f"F{sector}",
                    "stage": stage,
                    "input_hash": parent_hash,
                    "target_payload": fixture,
                    "fixture_name": target_path.name,
                    "database_name": db_path.name,
                    "transport": transport,
                }
                if input_provenance is not None:
                    envelope["input_provenance"] = input_provenance
                (Path(temporary) / f"{stage}.json").write_text(
                    canonical_json(envelope), encoding="utf-8"
                )
                receipt = (
                    circuit.dispatch(sector, envelope) if circuit is not None
                    else evaluate_envelope(sector, envelope, evaluate_matrix_sector, private_key)
                )
                verify_receipt(sector, envelope, receipt, private_key.public_key())
                content = receipt["content"]
                if sector == 7:
                    report = content
                artifacts.append({
                    "stage": stage,
                    "artifact_name": f"{run_id}.json",
                    "content": content | {
                        "state_provenance": receipt["state_provenance"],
                        "circuit_receipt": receipt,
                    },
                })
                parent_hash = receipt["state_provenance"]["output_hash"]
            ensure_state_db(db_path)
            session_path = save_run(
                run_id, report["case_id"], target_path.name, report,
                artifacts, private_key, db_path, session_metrics=meter.finish(),
            )
            if not verify_run_receipt(run_id, db_path):
                raise IntentError(f"Matrix receipt verification failed for {run_id}")
            session = load_session(
                session_path.name, sessions_root=session_path.parent,
                trusted_key_path=key_path,
            )
            if not session["audit_signature_valid"]:
                raise IntentError(f"Matrix session verification failed for {run_id}")
    finally:
        meter.finish()
    return report | {"session_path": session_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sequential offline ViperCrest matrix harness")
    parser.add_argument("--target", required=True, type=Path, help="Local baseline/candidate JSON fixture")
    parser.add_argument("--db", type=Path, default=STATE_DB)
    parser.add_argument("--key", type=Path, default=KEY_PATH)
    parser.add_argument("--transport", choices=("direct", "http"), default="direct")
    parser.add_argument("--http-port", type=int, default=PORT, help="Loopback port; 0 selects a free port")
    args = parser.parse_args(argv)
    try:
        report = execute_matrix_sweep(
            args.target, db_path=args.db, key_path=args.key,
            transport=args.transport, http_port=args.http_port,
        )
    except (IntentError, OSError, ValueError, sqlite3.Error) as exc:
        print(f"[VIPER] ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"[VIPER] {report['status']}: {report['session_path']}")
    print("[VIPER] Receipt and five-file session audit verified. No live-system verification claimed.")
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
