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

VIPER_ROOT = Path(__file__).resolve().parent
FIXTURES_DIR = VIPER_ROOT / "fixtures"
PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)
VIPERCREST_CMD = VIPER_ROOT / "vipercrest.cmd"


SIMULATION_SCENARIOS = {
    "default": {
        "id": "smart-contract-state-transition",
        "description": "Standard PAS_Configurator rate limit update and token distribution",
        "baseline": {
            "contract": "PAS_Configurator",
            "rate_limits": {"hop": 86400, "maxChange": 1000},
            "balances": {"treasury": 1000000, "user": 0},
            "owner": "0x1111111111111111111111111111111111111111",
        },
        "candidate": {
            "contract": "PAS_Configurator",
            "rate_limits": {"hop": 86400, "maxChange": 5000},
            "balances": {"treasury": 950000, "user": 50000},
            "owner": "0x1111111111111111111111111111111111111111",
        },
    },
    "reentrancy": {
        "id": "v03-reentrancy-vault-drain",
        "description": "Immunefi V03/V07: External contract reentrant callback draining vault funds",
        "baseline": {
            "contract": "YieldVault_v2",
            "storage_slots": {"0x0": "0x1000000000000000000", "0x1": "0x0"},
            "vault_eth_balance": 1000.0,
            "attacker_eth_balance": 1.0,
            "shares": {"attacker": 1.0, "total": 1000.0},
            "reentrancy_guard_locked": False,
        },
        "candidate": {
            "contract": "YieldVault_v2",
            "storage_slots": {"0x0": "0x0", "0x1": "0x1"},
            "vault_eth_balance": 0.0,
            "attacker_eth_balance": 1001.0,
            "shares": {"attacker": 0.0, "total": 0.0},
            "reentrancy_guard_locked": True,
        },
    },
    "oracle_manipulation": {
        "id": "v05-oracle-flash-manipulation",
        "description": "Immunefi V05/V02: AMM spot price manipulation distorting liquidation threshold",
        "baseline": {
            "contract": "LendingPool_Core",
            "oracle_feed": {"source": "Chainlink_Aggregator", "price_usd": 3000.0, "staleness_sec": 30},
            "collateral_ratio": 1.5,
            "health_factor": 1.85,
            "liquidations_triggered": 0,
        },
        "candidate": {
            "contract": "LendingPool_Core",
            "oracle_feed": {"source": "Uniswap_Spot_Pool", "price_usd": 120.0, "staleness_sec": 0},
            "collateral_ratio": 0.06,
            "health_factor": 0.12,
            "liquidations_triggered": 42,
        },
    },
    "unauthorized_config": {
        "id": "v04-access-control-override",
        "description": "Immunefi V04/V01: Unprivileged caller bypassing authorization to alter admin parameters",
        "baseline": {
            "contract": "BridgeRouter_Permissions",
            "admin": "0xAAAA00000000000000000000000000000000AAAA",
            "fee_rate_bps": 25,
            "paused": False,
            "whitelisted_callers": ["0xAAAA00000000000000000000000000000000AAAA"],
        },
        "candidate": {
            "contract": "BridgeRouter_Permissions",
            "admin": "0xDEAD00000000000000000000000000000000DEAD",
            "fee_rate_bps": 5000,
            "paused": True,
            "whitelisted_callers": ["0xDEAD00000000000000000000000000000000DEAD"],
        },
    },
    "storage_collision": {
        "id": "v10-proxy-storage-collision",
        "description": "Immunefi V10: Unaligned storage slots in upgraded implementation overwriting logic pointer",
        "baseline": {
            "contract": "ERC1967_Proxy",
            "implementation_slot_0x3608": "0x1234567890abcdef1234567890abcdef12345678",
            "admin_slot_0xb531": "0xfeeeddccbbaa99887766554433221100ffeeddcc",
            "contract_version": 1,
        },
        "candidate": {
            "contract": "ERC1967_Proxy",
            "implementation_slot_0x3608": "0xbadc0de00000000000000000000000000000badc",
            "admin_slot_0xb531": "0x0000000000000000000000000000000000000000",
            "contract_version": 2,
        },
    },
}


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Foundry to ViperCrest Simulation Bridge")
    parser.add_argument("--name", default="foundry_simulation_diff.json", help="Output fixture name")
    parser.add_argument(
        "--scenario",
        choices=list(SIMULATION_SCENARIOS.keys()) + ["all"],
        default="default",
        help="Simulate a specific Immunefi invariant break scenario",
    )
    parser.add_argument("--trace-file", help="Path to raw JSON trace or state diff file to ingest")
    parser.add_argument("--run-forge", action="store_true", help="Run forge test before bridging")
    parser.add_argument("--target-dir", default=r"C:\Users\nowli\Downloads\contracts-v2\contracts", help="Foundry project dir")
    parser.add_argument("--match-path", default="", help="Optional forge test --match-path filter")
    args = parser.parse_args(argv)

    observations = []

    if args.trace_file:
        trace_path = Path(args.trace_file)
        if not trace_path.exists():
            print(f"[BRIDGE] Error: Trace file not found: {trace_path}")
            return 1
        print(f"[BRIDGE] Ingesting external trace: {trace_path}")
        raw_data = json.loads(trace_path.read_text(encoding="utf-8"))
        if isinstance(raw_data, list):
            for idx, item in enumerate(raw_data):
                obs_id = item.get("id", f"trace-item-{idx+1}")
                baseline = item.get("baseline", item.get("before", {}))
                candidate = item.get("candidate", item.get("after", {}))
                observations.append(build_diff_observation(obs_id, baseline, candidate))
        elif isinstance(raw_data, dict) and "observations" in raw_data:
            observations.extend(raw_data["observations"])
        elif isinstance(raw_data, dict):
            observations.append(
                build_diff_observation(
                    "custom-trace-state",
                    raw_data.get("baseline", raw_data.get("before", {})),
                    raw_data.get("candidate", raw_data.get("after", raw_data)),
                )
            )
    elif args.run_forge:
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
    elif args.scenario == "all":
        for scen_name, scen_data in SIMULATION_SCENARIOS.items():
            observations.append(
                build_diff_observation(
                    scen_data["id"],
                    baseline_state=scen_data["baseline"],
                    candidate_state=scen_data["candidate"],
                )
            )
    else:
        scen_data = SIMULATION_SCENARIOS.get(args.scenario, SIMULATION_SCENARIOS["default"])
        observations.append(
            build_diff_observation(
                scen_data["id"],
                baseline_state=scen_data["baseline"],
                candidate_state=scen_data["candidate"],
            )
        )

    fixture_file = create_observation_fixture(args.name, observations)
    print(f"[BRIDGE] Generated fixture: {fixture_file} ({len(observations)} observations)")
    rc = run_vipercrest_matrix(fixture_file)
    return rc


if __name__ == "__main__":
    sys.exit(main())
