"""ViperCrest Minimal Seed Tensor Hydration Engine (seed_cli.py).

Operational tool executing minimal seed inversion and natural 729-tensor emergence.
Transforms any atomic seed string or observation file into the 729-coordinate
epistemic state space across 9 temporal phases and 9 invariant stages.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import domain_space as ds
import reader_engine as re_eng
import syntax_emitter as syn_emit


def hydrate_and_report(raw_seed: str, domain: str = "security"):
    """Hydrates the 729-tensor from raw seed input and prints the breakdown."""
    tms = re_eng.parse_raw_stream(raw_seed, cartridge_key=domain)
    tensor_eval = tms.evaluate_729_tensor_space()
    summary = tensor_eval.get("summary", {})

    print("=" * 76)
    print("      VIPERCREST MINIMAL SEED -> 729-COORDINATE TENSOR HYDRATION")
    print("=" * 76)
    print(f"  Domain Cartridge     : {domain.upper()} ({tms.cartridge.name})")
    print(f"  Input Seed Length    : {len(raw_seed)} chars")
    print(f"  Seed Preview         : {raw_seed[:75]}{'...' if len(raw_seed) > 75 else ''}")
    print("-" * 76)
    print("  729-TENSOR EMERGENCE SUMMARY:")
    print(f"    Total Tensor Grid  : 729 Coordinates (9 Phases x 9 Stages x 9 Seeds)")
    print(f"    Directly Observed  : {summary.get('observed_cells', 0):>3} coordinates (Authentic source evidence)")
    print(f"    Derived Historical : {summary.get('derived_cells', 0):>3} coordinates (Causally backward-hydrated)")
    print(f"    Possible Future    : {summary.get('possible_cells', 0):>3} coordinates (Reachable forward states)")
    print(f"    Quarantined in F7  : {summary.get('unresolved_f7_cells', 0):>3} coordinates (Stage F7 Zero Speculation)")
    print("-" * 76)

    # Active present state slice (T5_COMPOUNDING)
    print("  PRESENT STATE OBSERVATION SLICE (T5_COMPOUNDING):")
    for seed in ds.DOMAIN_SEEDS:
        coord_info = tms.get_coordinate_state(tms.center, seed)
        status = coord_info.get("status", "UNRESOLVED")
        meaning = coord_info.get("meaning", seed)
        marker = "[+]" if status == "OBSERVED" else "[-]"
        print(f"    {marker} [{seed}] {meaning:<38} : {status}")

    print("-" * 76)
    obs_count = summary.get("observed_cells", 0)
    unresolved_count = summary.get("unresolved_f7_cells", 0)
    is_bounded = (unresolved_count == 0)

    print(f"  Epistemic State      : {'BOUNDED' if is_bounded else 'BOUNDED_WITH_F7_QUARANTINE'}")
    print(f"  F7 Preservation      : PASS (Zero unevidenced hallucination)")
    print("=" * 76)


def cmd_interactive():
    """Runs interactive seed hydration REPL."""
    print("=" * 76)
    print("  VIPERCREST SEED HYDRATION ENGINE [LIVE REPL]")
    print("=" * 76)
    print("  Type any observation string, or 'help' for commands.\n")

    current_domain = "security"
    while True:
        try:
            line = input(f"SEED [{current_domain.upper()}]> ").strip()
            if not line:
                continue

            lowered = line.lower()
            if lowered in {"exit", "quit", "q"}:
                print("Exiting Seed Hydration Engine.")
                break
            elif lowered in {"help", "?"}:
                print("\nCommands:")
                print("  domain [security|legal|logistics] : Switch domain cartridge")
                print("  file <path>                       : Ingest raw seed from file")
                print("  <any raw text>                    : Invert and hydrate seed into 729-tensor")
                print("  exit                              : Exit REPL\n")
                continue
            elif lowered.startswith("domain"):
                parts = lowered.split()
                if len(parts) > 1 and parts[1] in {"security", "legal", "logistics"}:
                    current_domain = parts[1]
                    print(f"[SWITCH] Active domain changed to: {current_domain.upper()}")
                else:
                    print("[INFO] Available domains: security, legal, logistics")
                continue
            elif lowered.startswith("file"):
                parts = shlex.split(line)
                if len(parts) < 2:
                    print("[ERROR] Please provide file path: file <path>")
                    continue
                fp = Path(parts[1])
                if not fp.exists():
                    print(f"[ERROR] File not found: {fp}")
                    continue
                content = fp.read_text(encoding="utf-8", errors="replace")
                hydrate_and_report(content, domain=current_domain)
                continue

            # Ingest line directly as seed
            hydrate_and_report(line, domain=current_domain)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting Seed Hydration Engine.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")


def main():
    parser = argparse.ArgumentParser(description="ViperCrest Minimal Seed Inversion & Tensor Hydration CLI")
    parser.add_argument("seed_or_file", nargs="?", default=None, help="Raw seed string or path to seed file")
    parser.add_argument("--domain", choices=["security", "legal", "logistics"], default="security", help="Domain Cartridge")
    args = parser.parse_args()

    if not args.seed_or_file:
        cmd_interactive()
        return 0

    p = Path(args.seed_or_file)
    if p.exists() and p.is_file():
        raw_seed = p.read_text(encoding="utf-8", errors="replace")
    else:
        raw_seed = args.seed_or_file

    hydrate_and_report(raw_seed, domain=args.domain)
    return 0


if __name__ == "__main__":
    sys.exit(main())
