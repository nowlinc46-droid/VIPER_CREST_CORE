"""Run the supplied prototype exclusively against disposable workspace paths."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch


sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

# Executable logic from the supplied snippet; only the inline prose is removed.
PROTOTYPE = r'''
import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

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
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "state_provenance": {
            "parent_state_hash": parent_hash,
            "current_state_hash": current_hash
        },
        "target_payload": target_payload
    }

def simulate_sector_evaluation(sector_id: int, envelope: dict) -> dict:
    status = "PASSED"
    reason = "Invariant and structural bounds verified successfully."
    if sector_id == 3:
        payload_str = json.dumps(envelope["target_payload"])
        if "unauthorized" in payload_str.lower():
            status = "FAILED"
            reason = "BOLA invariant violation: unauthorized tenant access pattern detected."
    return {
        "icon_uri": f"icon://sector/f{sector_id}/verdict",
        "sector_id": f"F{sector_id}_SECTOR_NODE",
        "evaluation_result": {
            "status": status,
            "reason": reason,
            "variance_score": 0.0 if status == "PASSED" else 0.95
        },
        "signature": f"ed25519:mock_sig_f{sector_id}_{compute_sha256(bytes(status, 'utf-8'))[:32]}"
    }

def execute_matrix_sweep(target_file_path: str):
    initialize_workspace()
    target_path = Path(target_file_path)
    if not target_path.exists():
        print(f"[ERROR] Target fixture not found at {target_path}")
        sys.exit(1)
    target_data = json.loads(target_path.read_text(encoding='utf-8'))
    session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_folder = SESSIONS_DIR / f"session_{session_id}"
    session_folder.mkdir(parents=True, exist_ok=True)
    print(f"[VIPER] Initializing 9-Sector Simultaneous Diamond Matrix Sweep [Session: {session_id}]")
    parent_hash = compute_sha256(json.dumps(target_data, sort_keys=True).encode('utf-8'))
    sector_verdicts = []
    for i in range(1, 10):
        envelope = build_icon_envelope(i, target_data, parent_hash)
        inbox_path = STAGING_DIR / f"v{i}_inbox" / f"payload_{session_id}.json"
        inbox_path.write_text(json.dumps(envelope, indent=2), encoding='utf-8')
        verdict = simulate_sector_evaluation(i, envelope)
        sector_verdicts.append(verdict)
        print(f"  [F{i}] Evaluated -> Status: {verdict['evaluation_result']['status']}")
    consensus_root = compute_sha256(json.dumps(sector_verdicts, sort_keys=True).encode('utf-8'))
    audit_receipt = {
        "session_id": session_id,
        "consensus_root_hash": consensus_root,
        "verdicts": sector_verdicts
    }
    (session_folder / "receipts_audit.sig").write_text(json.dumps(audit_receipt, indent=2), encoding='utf-8')
    print(f"[VIPER] Terminal Consensus Root Established: {consensus_root}")
    execute_self_scrub(session_id)

def execute_self_scrub(session_id: str):
    print(f"[VIPER] Executing automated self-scrubbing sweep for session {session_id}...")
    for i in range(1, 10):
        inbox_dir = STAGING_DIR / f"v{i}_inbox"
        if inbox_dir.exists():
            shutil.rmtree(inbox_dir, ignore_errors=True)
            inbox_dir.mkdir(parents=True, exist_ok=True)
    pycache_dir = WORKSPACE_DIR / "__pycache__"
    if pycache_dir.exists():
        shutil.rmtree(pycache_dir, ignore_errors=True)
    print("[VIPER] Self-scrub complete. Ephemeral staging cleared. Immutable audit logs preserved.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ViperCrest 9-Sector Matrix Execution Harness")
    parser.add_argument("--target", required=True, help="Path to target JSON payload fixture")
    args = parser.parse_args()
    execute_matrix_sweep(args.target)
'''


class MatrixSandboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="viper-matrix-probe-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        original = 'WORKSPACE_DIR = Path("C:/CrateEngine/ViperCrest")'
        self.assertEqual(PROTOTYPE.count(original), 1)
        self.source = PROTOTYPE.replace(
            original, f"WORKSPACE_DIR = Path({str(self.workspace)!r})"
        )
        self.module = {"__name__": "isolated_matrix"}
        exec(compile(self.source, "<isolated-prototype>", "exec"), self.module)
        self.output = io.StringIO()
        self.addCleanup(self.output.close)
        self.stdout = contextlib.redirect_stdout(self.output)
        self.stdout.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)

    def fixture(self, payload):
        target = self.root / "target.json"
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target

    def run_sweep(self, payload):
        return self.module["execute_matrix_sweep"](str(self.fixture(payload)))

    def receipts(self):
        return sorted((self.workspace / "sessions").glob("*\\receipts_audit.sig"))

    def receipt(self):
        return json.loads(self.receipts()[0].read_text(encoding="utf-8"))

    def evaluate(self, payload, sector=3):
        envelope = self.module["build_icon_envelope"](sector, payload, "seed")
        return self.module["simulate_sector_evaluation"](sector, envelope)

    def test_01_inline_prose_is_a_syntax_error(self):
        """CONFIRMED: the literal pasted prose prevents compilation."""
        broken = self.source.replace(
            'print(f"[VIPER] Terminal Consensus Root Established: {consensus_root}")',
            'print(f"[VIPER] Terminal Consensus Root Established: {consensus_root}")      tell me what you think',
        )
        with self.assertRaises(SyntaxError):
            compile(broken, "<literal-paste>", "exec")

    def test_02_happy_path_writes_receipt_and_clears_staging(self):
        """WORKS: nine mock verdicts, one receipt, and empty inboxes."""
        self.run_sweep({"message": "synthetic benign payload"})
        self.assertEqual(len(self.receipts()), 1)
        self.assertEqual(len(self.receipt()["verdicts"]), 9)
        self.assertEqual(
            len(list((self.workspace / "staging").glob("v*_inbox"))), 9
        )
        self.assertFalse(list((self.workspace / "staging").rglob("*.json")))

    def test_03_failed_sector_still_exits_zero(self):
        """CONFIRMED: CLI exits 0 even when F3 reports FAILED."""
        target = self.fixture({"message": "unauthorized"})
        result = subprocess.run(
            [sys.executable, "-B", "-c", self.source, "--target", str(target)],
            capture_output=True, text=True, timeout=20, cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[F3] Evaluated -> Status: FAILED", result.stdout)
        self.assertIn("Terminal Consensus Root Established", result.stdout)
        self.assertEqual(
            self.receipt()["verdicts"][2]["evaluation_result"]["status"], "FAILED"
        )
        self.assertEqual(
            set(self.receipt()), {"session_id", "consensus_root_hash", "verdicts"}
        )

    def test_04_keyword_false_positive(self):
        """CONFIRMED: describing correctly denied access causes a failure."""
        verdict = self.evaluate({"note": "Unauthorized requests were correctly rejected."})
        self.assertEqual(verdict["evaluation_result"]["status"], "FAILED")

    def test_05_real_fixture_false_negative(self):
        """CONFIRMED: existing cross-tenant patient fixture gets nine passes."""
        fixture = json.loads(
            (PROJECT / "fixtures" / "patient_records_bola.json")
            .read_text(encoding="utf-8")
        )
        case = next(
            item for item in fixture["observations"] if item["id"] == "cross-tenant-read"
        )
        self.assertNotEqual(
            case["context"]["caller"]["tenant_id"],
            case["context"]["requested_patient"]["tenant_id"],
        )
        self.assertEqual(case["candidate"]["status_code"], 200)
        self.run_sweep(fixture)
        self.assertTrue(all(
            item["evaluation_result"]["status"] == "PASSED"
            for item in self.receipt()["verdicts"]
        ))

    def test_06_signature_ignores_payload_and_reason(self):
        """CONFIRMED: different payloads share the same mock signature."""
        first = self.evaluate({"tenant": "one"})
        second = self.evaluate({"tenant": "two"})
        self.assertEqual(first["signature"], second["signature"])
        before = first["signature"]
        first["evaluation_result"]["reason"] = "Modified after evaluation"
        self.assertEqual(first["signature"], before)
        self.assertTrue(before.startswith("ed25519:mock_sig_"))

    def test_07_cleanup_removes_other_session_data(self):
        """CONFIRMED: scrub deletes another run's inbox file and shared cache."""
        self.module["initialize_workspace"]()
        foreign = self.workspace / "staging" / "v1_inbox" / "other-session.json"
        foreign.write_text("{}", encoding="utf-8")
        cache = self.workspace / "__pycache__"
        cache.mkdir()
        (cache / "other-session.pyc").write_bytes(b"synthetic")
        self.module["execute_self_scrub"]("only-this-session")
        self.assertFalse(foreign.exists())
        self.assertFalse(cache.exists())

    def test_08_exception_leaves_staging_without_audit(self):
        """CONFIRMED: evaluator exception leaves payloads and no audit receipt."""
        original = self.module["simulate_sector_evaluation"]

        def fail_third(sector_id, envelope):
            if sector_id == 3:
                raise RuntimeError("injected evaluator failure")
            return original(sector_id, envelope)

        self.module["simulate_sector_evaluation"] = fail_third
        with self.assertRaisesRegex(RuntimeError, "injected evaluator failure"):
            self.run_sweep({"test": "interrupted"})
        self.assertEqual(len(list((self.workspace / "staging").rglob("*.json"))), 3)
        self.assertEqual(self.receipts(), [])

    def test_09_same_second_overwrites_receipt(self):
        """CONFIRMED: two same-second runs overwrite a single session receipt."""
        class FrozenDatetime:
            @staticmethod
            def utcnow():
                return datetime(2026, 10, 26, 12, 0, 0)

        self.module["datetime"] = FrozenDatetime
        self.run_sweep({"message": "benign"})
        first = self.receipt()
        self.run_sweep({"message": "unauthorized"})
        second = self.receipt()
        self.assertEqual(len(self.receipts()), 1)
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertNotEqual(first["consensus_root_hash"], second["consensus_root_hash"])

    def test_10_dispatch_is_sequential_not_broadcast(self):
        """CONFIRMED: F1 evaluates before the F2-F9 payloads are staged."""
        original = self.module["simulate_sector_evaluation"]
        files_at_evaluation = []

        def observe(sector_id, envelope):
            files_at_evaluation.append(
                len(list((self.workspace / "staging").rglob("*.json")))
            )
            return original(sector_id, envelope)

        self.module["simulate_sector_evaluation"] = observe
        self.run_sweep({"test": "dispatch"})
        self.assertEqual(files_at_evaluation, list(range(1, 10)))

    def test_11_no_input_schema_validation(self):
        """CONFIRMED: a top-level JSON list passes every sector."""
        self.run_sweep([1, 2, 3])
        self.assertTrue(all(
            item["evaluation_result"]["status"] == "PASSED"
            for item in self.receipt()["verdicts"]
        ))

    def test_12_malformed_input_has_no_structured_audit(self):
        """CONFIRMED: malformed JSON raises directly with no audit."""
        target = self.root / "bad.json"
        target.write_text("{", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            self.module["execute_matrix_sweep"](str(target))
        self.assertTrue((self.workspace / "staging").exists())
        self.assertEqual(self.receipts(), [])

    def test_13_not_compatible_with_vipercrest_session_loader(self):
        """CONFIRMED: actual ViperCrest loader rejects both identity and file schema."""
        import session_router

        self.run_sweep({"test": "compatibility"})
        folder = self.receipts()[0].parent
        missing_test_key = self.root / "never-read-key.pem"
        with self.assertRaisesRegex(ValueError, "Invalid session identifier"):
            session_router.load_session(
                folder.name, sessions_root=folder.parent,
                trusted_key_path=missing_test_key,
            )
        compatible_id = session_router.session_folder_name(
            "2026-10-26T12:00:00Z", "sandbox-probe"
        )
        renamed = folder.with_name(compatible_id)
        folder.rename(renamed)
        with self.assertRaisesRegex(ValueError, "exact five-file schema"):
            session_router.load_session(
                compatible_id, sessions_root=renamed.parent,
                trusted_key_path=missing_test_key,
            )

    def test_14_cleanup_can_report_success_without_deleting(self):
        """CONFIRMED: ignored deletion failure still prints self-scrub complete."""
        self.module["initialize_workspace"]()
        marker = self.workspace / "staging" / "v1_inbox" / "residual.json"
        marker.write_text("{}", encoding="utf-8")
        with patch.object(self.module["shutil"], "rmtree", return_value=None):
            self.module["execute_self_scrub"]("test")
        self.assertTrue(marker.exists())
        self.assertIn("Self-scrub complete", self.output.getvalue())

    def test_15_parent_and_current_hash_are_identical(self):
        """CONFIRMED: parent/current provenance hashes describe the same payload."""
        original = self.module["simulate_sector_evaluation"]
        seen = []

        def observe(sector_id, envelope):
            seen.append(envelope["state_provenance"])
            return original(sector_id, envelope)

        self.module["simulate_sector_evaluation"] = observe
        self.run_sweep({"test": "provenance"})
        self.assertEqual(len(seen), 9)
        self.assertTrue(all(
            item["parent_state_hash"] == item["current_state_hash"] for item in seen
        ))

    def test_16_missing_target_exits_one(self):
        """WORKS: a missing target causes exit status 1."""
        with self.assertRaises(SystemExit) as caught:
            self.module["execute_matrix_sweep"](str(self.root / "missing.json"))
        self.assertEqual(caught.exception.code, 1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MatrixSandboxTests)
    cases = [
        {"test": test.id().rsplit(".", 1)[-1], "claim": test.shortDescription()}
        for test in suite
    ]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    failed = {
        test.id().rsplit(".", 1)[-1]: detail
        for test, detail in result.failures + result.errors
    }
    report = {
        "scope": "Disposable local simulation, not an OS security sandbox.",
        "source_adjustments": [
            "Removed inline user prose to allow compilation.",
            "Redirected WORKSPACE_DIR to a fresh temporary directory for every test.",
            "No assessment, signing, dispatch, or cleanup logic was corrected.",
        ],
        "project_changes": False,
        "tests_run": result.testsRun,
        "tests_passed": result.testsRun - len(failed),
        "interpretation": "Passing CONFIRMED tests reproduce defects, not production readiness.",
        "cases": [
            case | {
                "reproduced": case["test"] not in failed,
                **({"failure": failed[case["test"]]} if case["test"] in failed else {}),
            }
            for case in cases
        ],
    }
    report_path = PROJECT / "runtime" / "probes" / "matrix_sandbox_results.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {report_path}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
