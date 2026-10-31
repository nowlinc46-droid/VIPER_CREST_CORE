"""
Smart Contract Simulation Bridge for Foundry -> ViperCrest F1-F9 Runtime Engine.
Ingests transaction diffs and test results from Foundry (`forge test --json` or state diffs)
and formats them into ViperCrest observation fixtures, triggering F1-F9 matrix execution.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

VIPER_ROOT = Path("C:/ViperCrest")
FIXTURES_DIR = VIPER_ROOT / "fixtures"
PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"
VIPERCREST_CMD = VIPER_ROOT / "vipercrest.cmd"


def create_observation_fixture(
    fixture_name: str,
    observations: list[dict[str, Any]],
) -> Path:
    if not fixture_name.endswith(".json"):
        fixture_name += ".json"
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    target_path = FIXTURES_DIR / fixture_name
    data = {"observations": observations}
    target_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return target_path


def build_diff_observation(
    observation_id: str,
    baseline_state: dict[str, Any],
    candidate_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": observation_id,
        "baseline": baseline_state,
        "candidate": candidate_state,
    }


def run_vipercrest_matrix(fixture_path: Path) -> int:
    cmd = [str(PYTHON_EXE), "-B", str(VIPER_ROOT / "viper.py"), "matrix", "--target", str(fixture_path)]
    print(f"[BRIDGE] Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Foundry to ViperCrest Simulation Bridge")
    parser.add_argument("--name", default="foundry_simulation_diff.json", help="Output fixture name")
    parser.add_argument("--run-forge", action="store_true", help="Run forge test before bridging")
    parser.add_argument("--target-dir", default=r"C:\Users\nowli\Downloads\contracts-v2\contracts", help="Foundry project dir")
    parser.add_argument("--match-path", default="", help="Optional forge test --match-path filter")
    args = parser.parse_args()

    observations = []

    if args.run_forge:
        print(f"[BRIDGE] Running forge test in {args.target_dir}...")
        default_forge = Path.home() / ".foundry" / "bin" / "forge.exe"
        forge_bin = str(default_forge) if default_forge.exists() else "forge"
        forge_cmd = [forge_bin, "test", "--offline", "--json"]
        if args.match_path:
            forge_cmd.extend(["--match-path", args.match_path])
        proc = subprocess.run(forge_cmd, cwd=args.target_dir, capture_output=True, text=True)
        try:
            test_results = json.loads(proc.stdout)
            observations.append(
                build_diff_observation(
                    "foundry-test-suite-execution",
                    baseline_state={"status": "expected_pass", "failures": 0},
                    candidate_state={"status": "executed", "exit_code": proc.returncode, "summary": test_results},
                )
            )
        except Exception:
            observations.append(
                build_diff_observation(
                    "foundry-test-suite-execution",
                    baseline_state={"status": "expected_pass", "failures": 0},
                    candidate_state={"status": "executed", "exit_code": proc.returncode, "raw_output": proc.stdout[-1000:] if proc.stdout else ""},
                )
            )
    else:
        # Default smart contract state diff observation template
        observations.append(
            build_diff_observation(
                "smart-contract-state-transition",
                baseline_state={
                    "contract": "PAS_Configurator",
                    "rate_limits": {"hop": 86400, "maxChange": 1000},
                    "balances": {"treasury": 1000000, "user": 0},
                },
                candidate_state={
                    "contract": "PAS_Configurator",
                    "rate_limits": {"hop": 86400, "maxChange": 5000},
                    "balances": {"treasury": 950000, "user": 50000},
                },
            )
        )

    fixture_file = create_observation_fixture(args.name, observations)
    print(f"[BRIDGE] Generated fixture: {fixture_file}")
    rc = run_vipercrest_matrix(fixture_file)
    sys.exit(rc)


if __name__ == "__main__":
    main()
