"""ViperCrest Scale-Invariant Open Ontological Discovery CLI (discovery_cli.py).

Operational CLI for real-time discovery and unmapped seed isolation (S10+).
Enforces zero-execution semantic decomposition:
  - Canonical 729-coordinate lattice (9x9x9) remains 100% frozen.
  - Novel dimensions are safely isolated in the F7 Discovery Gap Set G(S).
  - G(S) != empty forces involuntary fail-closed suspension (0.0 speculation).
  - Recovery evidence clears novel gaps and seals without code modifications.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import domain_space as ds
import reader_engine as re_eng
from convergence_engine import ConvergenceEngine, SuccessorState


def evaluate_discovery_payload(
    raw_payload: str,
    predecessor: Optional[SuccessorState] = None,
    cartridge_key: str = "security",
) -> SuccessorState:
    """Evaluates raw payload, discovers novel dimensions, and executes a convergence pass."""
    tms = re_eng.parse_raw_stream(raw_payload, cartridge_key=cartridge_key)
    engine = ConvergenceEngine()
    req_seeds = list(tms.active_seeds) if tms.active_seeds else ["S1", "S2", "S3", "S7"]

    state = engine.execute_pass(
        predecessor=predecessor,
        new_data=raw_payload,
        cartridge_key=cartridge_key,
        custom_required_seeds=req_seeds,
    )
    return state


def print_discovery_report(state: SuccessorState, raw_input: str):
    """Prints authoritative open-ontological discovery report."""
    print("=" * 72)
    print("       VIPERCREST SCALE-INVARIANT OPEN ONTOLOGICAL DISCOVERY")
    print("=" * 72)
    print("  Input Stream Snippet :")
    for line in raw_input.strip().splitlines()[:5]:
        print(f"    {line}")
    if len(raw_input.strip().splitlines()) > 5:
        print(f"    ... ({len(raw_input.strip().splitlines()) - 5} more lines)")
    print("-" * 72)

    # Distinguish canonical seeds vs novel S10+ dimensions
    canonical_resolved = {k: v for k, v in state.resolved_seed_map.items() if k in ds.DOMAIN_SEEDS}
    novel_resolved = {k: v for k, v in state.resolved_seed_map.items() if k not in ds.DOMAIN_SEEDS}

    canonical_gaps = [g for g in state.gaps if g.seed in ds.DOMAIN_SEEDS]
    novel_gaps = [g for g in state.gaps if g.seed not in ds.DOMAIN_SEEDS]

    print("  CANONICAL DOMAIN STATUS (S1..S9):")
    print(f"    - Resolved Seeds : {len(canonical_resolved)} / 9 ({', '.join(canonical_resolved.keys()) if canonical_resolved else 'None'})")
    print(f"    - Canonical Gaps : {len(canonical_gaps)}")
    for g in canonical_gaps:
        print(f"        * [{g.seed}] {g.meaning} (Coordinate: {g.coordinate})")

    print("\n  NOVEL DISCOVERED DIMENSIONS (S10+ OPEN EXPANSION):")
    if not novel_gaps and not novel_resolved:
        print("    - None detected in this stream (Input fits within canonical S1..S9)")
    else:
        if novel_resolved:
            print(f"    - Verified & Grounded Novel Dimensions: {len(novel_resolved)}")
            for k, v in novel_resolved.items():
                print(f"        * [{k}] Verified: {v}")
        if novel_gaps:
            print(f"    - Isolated Unmapped Dimensions (Held in Stage F7): {len(novel_gaps)}")
            for g in novel_gaps:
                print(f"        * [{g.seed}] {g.meaning}")
                print(f"          Directive : {g.recovery_directive}")

    print("-" * 72)
    print(f"  Operational State    : {state.status} ({'BOUNDED & SEALED' if state.is_bounded else 'FAIL-CLOSED SUSPENDED'})")
    print(f"  Actuation Permission : {'PERMITTED (SAFE)' if state.is_bounded else 'HALTED (Gaps Active)'}")
    print(f"  Cryptographic Hash   : {state.state_hash}")
    if state.predecessor_hash:
        print(f"  Predecessor Hash     : {state.predecessor_hash}")
    print(f"  Pass Index           : Pass {state.pass_index}")
    print("=" * 72)


def cmd_interactive():
    """Runs interactive discovery REPL."""
    current_state: Optional[SuccessorState] = None
    accumulated_data: List[str] = []

    print("=" * 72)
    print("  VIPERCREST OPEN ONTOLOGICAL DISCOVERY [LIVE REPL]")
    print("=" * 72)
    print("  Ingests novel telemetry, unstructured logs, or code.")
    print("  Type 'help' for commands, or paste input.\n")

    while True:
        try:
            status_tag = current_state.status if current_state else "IDLE"
            prompt = f"DISCOVERY [{status_tag}]> "
            line = input(prompt).strip()
            if not line:
                continue

            lowered = line.lower()
            if lowered in {"exit", "quit", "q"}:
                print("Exiting Open Discovery Engine.")
                break
            elif lowered in {"help", "?"}:
                print("\nCommands:")
                print("  ingest <telemetry_line>    : Ingest raw observation / novel dimension")
                print("  recover S<ID>: <evidence>  : Submit recovery proof for an isolated gap")
                print("  file <path>                : Ingest and evaluate an entire file")
                print("  status                     : Display active discovery state")
                print("  reset                      : Clear active session")
                print("  exit                       : Exit REPL\n")
                continue
            elif lowered == "reset":
                current_state = None
                accumulated_data.clear()
                print("[RESET] Discovery session cleared.")
                continue
            elif lowered == "status":
                if current_state:
                    print_discovery_report(current_state, "\n".join(accumulated_data))
                else:
                    print("[INFO] No active discovery session.")
                continue
            elif lowered.startswith("file"):
                parts = shlex.split(line)
                if len(parts) < 2:
                    print("[ERROR] Please provide a file path: file <path>")
                    continue
                fp = Path(parts[1])
                if not fp.exists():
                    print(f"[ERROR] File not found: {fp}")
                    continue
                content = fp.read_text(encoding="utf-8", errors="replace")
                accumulated_data.append(content)
                current_state = evaluate_discovery_payload(content, predecessor=current_state)
                print_discovery_report(current_state, content)
                continue
            elif lowered.startswith("recover"):
                if not current_state:
                    print("[ERROR] No active discovery state to recover. Ingest telemetry first.")
                    continue
                rec_evidence = line[len("recover"):].strip()
                engine = ConvergenceEngine()
                req_seeds = list(current_state.resolved_seed_map.keys()) + [g.seed for g in current_state.gaps]
                next_state = engine.execute_pass(
                    predecessor=current_state,
                    new_data=rec_evidence,
                    cartridge_key="security",
                    custom_required_seeds=req_seeds,
                )
                current_state = next_state
                accumulated_data.append(rec_evidence)
                print_discovery_report(current_state, rec_evidence)
                continue

            # Standard raw input line
            accumulated_data.append(line)
            current_state = evaluate_discovery_payload(line, predecessor=current_state)
            print_discovery_report(current_state, line)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting Open Discovery Engine.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")


def main():
    parser = argparse.ArgumentParser(description="ViperCrest Open Ontological Discovery CLI")
    parser.add_argument("input_or_file", nargs="?", default=None, help="File path or raw telemetry text")
    args = parser.parse_args()

    if not args.input_or_file:
        cmd_interactive()
        return 0

    target_path = Path(args.input_or_file)
    if target_path.exists() and target_path.is_file():
        content = target_path.read_text(encoding="utf-8", errors="replace")
    else:
        content = args.input_or_file

    state = evaluate_discovery_payload(content)
    print_discovery_report(state, content)
    return 0 if state.is_bounded else 1


if __name__ == "__main__":
    sys.exit(main())
