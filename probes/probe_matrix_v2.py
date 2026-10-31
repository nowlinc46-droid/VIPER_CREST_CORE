"""Isolated behavioral tests of the user's revised matrix prototype."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

# Comments/formatting omitted; executable statements preserve the supplied revision.
PROTOTYPE = r'''
import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE_DIR = Path("C:/CrateEngine/ViperCrest")
STAGING_DIR = WORKSPACE_DIR / "staging"
SESSIONS_DIR = WORKSPACE_DIR / "sessions"

def initialize_workspace():
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(1, 10):
        (STAGING_DIR / f"v{i}_inbox").mkdir(parents=True, exist_ok=True)

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def build_icon_envelope(sector_id: int, target_payload: dict, parent_hash: str) -> dict:
    payload_bytes = json.dumps(target_payload, sort_keys=True).encode('utf-8')
    current_hash = compute_sha256(payload_bytes)
    return {
        "icon_uri": f"icon://sector/f{sector_id}/evaluate",
        "sector_id": f"F{sector_id}_SECTOR_NODE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state_provenance": {
            "parent_state_hash": parent_hash,
            "current_state_hash": current_hash
        },
        "target_payload": target_payload
    }

def execute_sector_evaluation(sector_id: int, envelope: dict) -> dict:
    status = "PASSED"
    reason = "Invariant and structural bounds verified successfully."
    variance_score = 0.0
    payload_str = json.dumps(envelope["target_payload"])
    if sector_id == 3:
        if "unauthorized" in payload_str.lower() or "patient_id" in payload_str.lower():
            if envelope["target_payload"].get("response_status") == 200:
                status = "FAILED"
                reason = "BOLA invariant violation: unauthorized cross-tenant record exposure with HTTP 200."
                variance_score = 0.95
    verdict_raw = f"{sector_id}:{status}:{reason}".encode('utf-8')
    output_hash = compute_sha256(verdict_raw)
    return {
        "icon_uri": f"icon://sector/f{sector_id}/verdict",
        "sector_id": f"F{sector_id}_SECTOR_NODE",
        "evaluation_result": {
            "status": status,
            "reason": reason,
            "variance_score": variance_score
        },
        "state_provenance": {
            "input_hash": envelope["state_provenance"]["current_state_hash"],
            "output_hash": output_hash
        },
        "signature": f"ed25519:sig_f{sector_id}_{output_hash[:32]}"
    }

def execute_matrix_sweep(target_file_path: str):
    initialize_workspace()
    target_path = Path(target_file_path)
    if not target_path.exists():
        print(f"[ERROR] Target fixture not found at {target_path}")
        sys.exit(1)
    try:
        target_data = json.loads(target_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"[ERROR] Malformed JSON target payload: {e}")
        sys.exit(1)
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    session_folder = SESSIONS_DIR / f"session_{session_id}"
    session_folder.mkdir(parents=True, exist_ok=True)
    print(f"[VIPER] Initializing 9-Sector Simultaneous Diamond Matrix Sweep [Session: {session_id}]")
    parent_hash = compute_sha256(json.dumps(target_data, sort_keys=True).encode('utf-8'))
    sector_verdicts = []
    execution_stack = []
    has_failure = False
    for i in range(1, 10):
        envelope = build_icon_envelope(i, target_data, parent_hash)
        inbox_dir = STAGING_DIR / f"v{i}_inbox" / session_id
        inbox_dir.mkdir(parents=True, exist_ok=True)
        inbox_path = inbox_dir / "payload.json"
        inbox_path.write_text(json.dumps(envelope, indent=2), encoding='utf-8')
        verdict = execute_sector_evaluation(i, envelope)
        sector_verdicts.append(verdict)
        execution_stack.append({
            "sector": f"F{i}",
            "status": verdict["evaluation_result"]["status"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if verdict["evaluation_result"]["status"] == "FAILED":
            has_failure = True
        print(f"  [F{i}] Evaluated -> Status: {verdict['evaluation_result']['status']}")
    consensus_root = compute_sha256(json.dumps(sector_verdicts, sort_keys=True).encode('utf-8'))
    (session_folder / "session_meta.json").write_text(json.dumps({
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "consensus_root_hash": consensus_root,
        "target_source": str(target_path.name)
    }, indent=2), encoding='utf-8')
    ndjson_content = "\n".join([json.dumps(item) for item in execution_stack])
    (session_folder / "execution_stack.ndjson").write_text(ndjson_content + "\n", encoding='utf-8')
    (session_folder / "state_delta.json").write_text(json.dumps({
        "parent_state_hash": parent_hash,
        "consensus_root_hash": consensus_root,
        "sector_provenance": [v["state_provenance"] for v in sector_verdicts]
    }, indent=2), encoding='utf-8')
    (session_folder / "receipts_audit.sig").write_text(json.dumps({
        "session_id": session_id,
        "consensus_root_hash": consensus_root,
        "verdicts": sector_verdicts
    }, indent=2), encoding='utf-8')
    csv_header = "sector_id,status,variance_score\n"
    csv_rows = [f"F{i+1},{v['evaluation_result']['status']},{v['evaluation_result']['variance_score']}" for i, v in enumerate(sector_verdicts)]
    (session_folder / "variance_metrics.csv").write_text(csv_header + "\n".join(csv_rows) + "\n", encoding='utf-8')
    print(f"[VIPER] Terminal Consensus Root Established: {consensus_root}")
    print(f"[VIPER] Session bundle fully compiled at: {session_folder}")
    execute_session_scrub(session_id)
    if has_failure:
        print("[VIPER] FAULT DETECTED: Matrix reported sector failure(s). Exiting with code 1.")
        sys.exit(1)
    else:
        print("[VIPER] SUCCESS: All sectors passed verification.")
        sys.exit(0)

def execute_session_scrub(session_id: str):
    print(f"[VIPER] Executing session-scoped cleanup for {session_id}...")
    for i in range(1, 10):
        session_inbox = STAGING_DIR / f"v{i}_inbox" / session_id
        if session_inbox.exists():
            shutil.rmtree(session_inbox, ignore_errors=True)
    pycache_dir = WORKSPACE_DIR / "__pycache__"
    if pycache_dir.exists():
        shutil.rmtree(pycache_dir, ignore_errors=True)
    print("[VIPER] Session scrub complete. Ephemeral staging cleared safely.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ViperCrest 9-Sector Matrix Execution Harness")
    parser.add_argument("--target", required=True, help="Path to target JSON payload fixture")
    args = parser.parse_args()
    execute_matrix_sweep(args.target)
'''


class RevisedMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="viper-matrix-v2-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        original = 'WORKSPACE_DIR = Path("C:/CrateEngine/ViperCrest")'
        self.assertEqual(PROTOTYPE.count(original), 1)
        self.source = PROTOTYPE.replace(
            original, f"WORKSPACE_DIR = Path({str(self.workspace)!r})"
        )
        self.module = {"__name__": "isolated_matrix_v2"}
        exec(compile(self.source, "<isolated-revision>", "exec"), self.module)
        self.output = io.StringIO()
        self.addCleanup(self.output.close)
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def fixture(self, payload):
        target = self.root / "target.json"
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target

    def run_sweep(self, payload, exit_code=0):
        with self.assertRaises(SystemExit) as caught:
            self.module["execute_matrix_sweep"](str(self.fixture(payload)))
        self.assertEqual(caught.exception.code, exit_code)

    def folders(self):
        return sorted((self.workspace / "sessions").glob("session_*"))

    def receipt(self):
        return json.loads(
            (self.folders()[0] / "receipts_audit.sig").read_text(encoding="utf-8")
        )

    def evaluate(self, payload, sector=3):
        envelope = self.module["build_icon_envelope"](sector, payload, "seed")
        return self.module["execute_sector_evaluation"](sector, envelope)

    def test_01_five_files_and_success_exit(self):
        """IMPROVED: normal execution creates exactly five named files and exits 0."""
        import session_router

        self.run_sweep({"message": "benign"})
        self.assertEqual(
            {path.name for path in self.folders()[0].iterdir()},
            session_router.SESSION_FILES,
        )
        self.assertEqual(len(self.receipt()["verdicts"]), 9)
        self.assertFalse(list((self.workspace / "staging").rglob("payload.json")))

    def test_02_failed_verdict_cli_exits_one(self):
        """FIXED: an F3 FAILED verdict now causes actual CLI exit 1."""
        target = self.fixture({"patient_id": "synthetic", "response_status": 200})
        result = subprocess.run(
            [sys.executable, "-B", "-c", self.source, "--target", str(target)],
            capture_output=True, text=True, timeout=20, cwd=self.root,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("[F3] Evaluated -> Status: FAILED", result.stdout)
        self.assertTrue((self.folders()[0] / "receipts_audit.sig").exists())

    def test_03_malformed_json_reported(self):
        """FIXED: malformed JSON prints an error and exits 1, without a JSON traceback."""
        target = self.root / "malformed.json"
        target.write_text("{", encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            self.module["execute_matrix_sweep"](str(target))
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("[ERROR] Malformed JSON", self.output.getvalue())

    def test_04_other_session_staging_survives(self):
        """FIXED: cleanup preserves other sessions' inbox files."""
        self.module["initialize_workspace"]()
        foreign = self.workspace / "staging" / "v1_inbox" / "other-session"
        foreign.mkdir()
        marker = foreign / "payload.json"
        marker.write_text("{}", encoding="utf-8")
        self.run_sweep({"test": "scoped staging"})
        self.assertTrue(marker.exists())

    def test_05_shared_cache_still_deleted(self):
        """REMAINS: session cleanup deletes the entire shared workspace cache."""
        cache = self.workspace / "__pycache__"
        cache.mkdir(parents=True)
        marker = cache / "other-session.pyc"
        marker.write_bytes(b"synthetic")
        self.run_sweep({"test": "cache"})
        self.assertFalse(marker.exists())

    def test_06_existing_patient_fixture_still_passes(self):
        """REMAINS: existing cross-tenant patient fixture gets nine passes."""
        payload = json.loads(
            (PROJECT / "fixtures" / "patient_records_bola.json")
            .read_text(encoding="utf-8")
        )
        self.assertNotIn("response_status", payload)
        cross_tenant = next(
            item for item in payload["observations"] if item["id"] == "cross-tenant-read"
        )
        self.assertEqual(cross_tenant["candidate"]["status_code"], 200)
        self.run_sweep(payload)
        self.assertTrue(all(
            verdict["evaluation_result"]["status"] == "PASSED"
            for verdict in self.receipt()["verdicts"]
        ))

    def test_07_legitimate_patient_read_fails(self):
        """REMAINS: allowed same-tenant patient read is labeled cross-tenant exposure."""
        verdict = self.evaluate({
            "patient_id": "synthetic-patient",
            "caller_tenant": "same",
            "patient_tenant": "same",
            "assigned": True,
            "response_status": 200,
        })
        self.assertEqual(verdict["evaluation_result"]["status"], "FAILED")

    def test_08_no_payload_bound_signature_or_state_evolution(self):
        """REMAINS: different payloads have identical output hashes and signatures."""
        first = self.evaluate({"tenant": "one"})
        second = self.evaluate({"tenant": "two"})
        self.assertNotEqual(
            first["state_provenance"]["input_hash"],
            second["state_provenance"]["input_hash"],
        )
        self.assertEqual(
            first["state_provenance"]["output_hash"],
            second["state_provenance"]["output_hash"],
        )
        self.assertEqual(first["signature"], second["signature"])

    def test_09_loader_rejects_identity_then_contents(self):
        """REMAINS: real ViperCrest loader rejects both ID and five-file contents."""
        import session_router

        self.run_sweep({"test": "integration"})
        folder = self.folders()[0]
        key = self.root / "never-read-key.pem"
        with self.assertRaisesRegex(ValueError, "Invalid session identifier"):
            session_router.load_session(
                folder.name, sessions_root=folder.parent, trusted_key_path=key
            )
        compatible_id = session_router.session_folder_name(
            "2026-10-26T12:00:00Z", "revision-probe"
        )
        renamed = folder.with_name(compatible_id)
        folder.rename(renamed)
        with self.assertRaisesRegex(ValueError, "expected data schema"):
            session_router.load_session(
                compatible_id, sessions_root=renamed.parent, trusted_key_path=key
            )
        meta = json.loads((renamed / "session_meta.json").read_text())
        self.assertFalse({"run_id", "created_at", "outcome"}.issubset(meta))
        delta = json.loads((renamed / "state_delta.json").read_text())
        self.assertNotIn("deltas", delta)
        self.assertNotIn("audit_signature_hex", self.receipt())
        rows = (renamed / "variance_metrics.csv").read_text().splitlines()
        self.assertEqual(len(rows), 10)
        self.assertNotIn("run_id", rows[0])

    def test_10_evaluator_exception_skips_cleanup_and_audit(self):
        """REMAINS: an evaluator exception leaves payloads and an empty session folder."""
        original = self.module["execute_sector_evaluation"]

        def fail(sector, envelope):
            if sector == 3:
                raise RuntimeError("injected evaluator failure")
            return original(sector, envelope)

        self.module["execute_sector_evaluation"] = fail
        with self.assertRaisesRegex(RuntimeError, "injected evaluator failure"):
            self.module["execute_matrix_sweep"](str(self.fixture({"test": "exception"})))
        self.assertEqual(len(list((self.workspace / "staging").rglob("payload.json"))), 3)
        self.assertEqual(list(self.folders()[0].iterdir()), [])

    def test_11_microseconds_improve_but_do_not_enforce_uniqueness(self):
        """REMAINS: repeated full timestamp reuses and overwrites a session."""
        class FixedDatetime:
            @staticmethod
            def now(tz):
                return datetime(2026, 10, 26, 12, 0, 0, 123456, tzinfo=timezone.utc)

        self.module["datetime"] = FixedDatetime
        self.run_sweep({"message": "first"})
        first = self.receipt()["consensus_root_hash"]
        self.run_sweep({"patient_id": "synthetic", "response_status": 200}, exit_code=1)
        self.assertEqual(len(self.folders()), 1)
        self.assertNotEqual(first, self.receipt()["consensus_root_hash"])

    def test_12_still_sequential_and_not_chained(self):
        """REMAINS: staging/evaluation is sequential and no sector consumes prior output."""
        original = self.module["execute_sector_evaluation"]
        counts, envelopes, verdicts = [], [], []

        def observe(sector, envelope):
            counts.append(len(list((self.workspace / "staging").rglob("payload.json"))))
            envelopes.append(envelope)
            verdict = original(sector, envelope)
            verdicts.append(verdict)
            return verdict

        self.module["execute_sector_evaluation"] = observe
        self.run_sweep({"test": "dispatch"})
        self.assertEqual(counts, list(range(1, 10)))
        self.assertEqual(
            len({item["state_provenance"]["parent_state_hash"] for item in envelopes}), 1
        )
        self.assertNotEqual(
            envelopes[1]["state_provenance"]["parent_state_hash"],
            verdicts[0]["state_provenance"]["output_hash"],
        )

    def test_13_non_object_input_can_pass_or_crash(self):
        """REMAINS: [1,2,3] passes; a list containing patient_id crashes at .get()."""
        self.run_sweep([1, 2, 3])
        with self.assertRaises(AttributeError):
            self.module["execute_matrix_sweep"](str(self.fixture(["patient_id"])))

    def test_14_scrub_failure_still_announces_success(self):
        """REMAINS: ignored deletion failures leave staged payloads but exit 0."""
        with patch.object(self.module["shutil"], "rmtree", return_value=None):
            self.run_sweep({"test": "deletion failure"})
        self.assertEqual(len(list((self.workspace / "staging").rglob("payload.json"))), 9)
        self.assertIn("Ephemeral staging cleared safely", self.output.getvalue())
        self.assertIn("SUCCESS", self.output.getvalue())

    def test_15_partial_session_on_write_failure(self):
        """REMAINS: receipt write failure leaves a partially published three-file bundle."""
        original = Path.write_text

        def fail_receipt(path, *args, **kwargs):
            if path.name == "receipts_audit.sig":
                raise OSError("injected receipt write failure")
            return original(path, *args, **kwargs)

        with patch.object(Path, "write_text", new=fail_receipt):
            with self.assertRaisesRegex(OSError, "injected receipt write failure"):
                self.module["execute_matrix_sweep"](
                    str(self.fixture({"test": "partial write"}))
                )
        self.assertEqual(
            {path.name for path in self.folders()[0].iterdir()},
            {"session_meta.json", "execution_stack.ndjson", "state_delta.json"},
        )
        self.assertEqual(len(list((self.workspace / "staging").rglob("payload.json"))), 9)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RevisedMatrixTests)
    cases = [
        {"test": test.id().rsplit(".", 1)[-1], "claim": test.shortDescription()}
        for test in suite
    ]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    failures = {
        test.id().rsplit(".", 1)[-1]: detail
        for test, detail in result.failures + result.errors
    }
    report = {
        "scope": "Disposable filesystem-isolated tests, not an OS security sandbox.",
        "source_adjustments": [
            "Comments/formatting omitted; executable logic preserved.",
            "Only WORKSPACE_DIR redirected to a temporary directory per test.",
        ],
        "project_changes": False,
        "tests_run": result.testsRun,
        "tests_passed": result.testsRun - len(failures),
        "interpretation": "Passing REMAINS checks confirm remaining defects.",
        "cases": [
            case | {
                "reproduced": case["test"] not in failures,
                **({"failure": failures[case["test"]]} if case["test"] in failures else {}),
            }
            for case in cases
        ],
    }
    destination = PROJECT / "runtime" / "probes" / "matrix_v2_sandbox_results.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {destination}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
