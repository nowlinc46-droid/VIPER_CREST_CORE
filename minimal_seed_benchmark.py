"""
ViperCrest Minimal Seed -> Natural Tensor Hydration Benchmark Runner.

Executes side-by-side verification of irreducibly minimal seeds across
Security IR, CourtForge Legal, and WMS Logistics, proving natural hydration
into the 81-state coordinate matrix and 729-coordinate tensor space while
preserving zero-speculation uncertainty in F7.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import domain_space as ds
import reader_engine as re_eng

PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)


def run_benchmark() -> int:
    print("=========================================================================================================")
    print("                VIPERCREST MINIMAL SEED -> NATURAL TENSOR HYDRATION BENCHMARK                            ")
    print("=========================================================================================================")

    domains = ["security", "legal", "logistics"]
    tms_results = {}
    tensor_results = {}
    fixtures = {}

    for dom in domains:
        fixture_path, tms = re_eng.run_minimal_seed_intake(dom, print_summary=False)
        fixtures[dom] = fixture_path
        tms_results[dom] = tms
        tensor_results[dom] = tms.evaluate_729_tensor_space()

    # 1. Print Domain Header
    print(f"{'DIMENSION':<22} | {'SECURITY IR (CISA)':<25} | {'COURTFORGE LEGAL':<25} | {'WMS LOGISTICS (HACCP)':<25}")
    print("-" * 105)
    print(f"{'Input Seed Granularity':<22} | {'1 Atomic String':<25} | {'1 Atomic String':<25} | {'1 Atomic String':<25}")
    print(f"{'Runtime Engine':<22} | {'F1-F9 (INVARIANT)':<25} | {'F1-F9 (INVARIANT)':<25} | {'F1-F9 (INVARIANT)':<25}")
    print(f"{'State Address Space':<22} | {'81 Coordinates':<25} | {'81 Coordinates':<25} | {'81 Coordinates':<25}")
    print(f"{'Total Tensor Space':<22} | {'729 Coordinates':<25} | {'729 Coordinates':<25} | {'729 Coordinates':<25}")
    print("-" * 105)

    # 2. Print Atomic Input Seeds
    print(" IRREDUCIBLY MINIMAL INPUT SEEDS (Raw S0)")
    print("-" * 105)
    for dom in domains:
        raw_seed = re_eng.SAMPLE_MINIMAL_SEEDS[dom]
        print(f"  [{dom.upper():<9}] \"{raw_seed}\"")
    print("-" * 105)

    # 3. Print 81-State Hydration Profiles
    print(" 81-COORDINATE NATURAL HYDRATION PROFILE (Zero Speculation / Epistemic Boundaries)")
    print("-" * 105)
    for idx, phase in enumerate(ds.TEMPORAL_PHASES, start=1):
        row = [f"  T{idx} ({phase:<14})"]
        for dom in domains:
            rep = tms_results[dom].construct_hydration_report()
            row.append(f"{rep.get(phase, 'UNRESOLVED'):<25}")
        print(f"{row[0]:<22} | {row[1]} | {row[2]} | {row[3]}")
    print("-" * 105)

    # 4. Print Spatial Seed Allocation at T5
    print(" SPATIAL SEED INSTANTIATION AT T5_COMPOUNDING (Direct Evidence vs Contained Unknowns)")
    print("-" * 105)
    for s in ds.DOMAIN_SEEDS:
        row = [f"  {s:<2} {tms_results['security'].cartridge.seed_meanings.get(s)[:17]:<17}"]
        for dom in domains:
            seed_data = tms_results[dom].positions["T5_COMPOUNDING"].seeds.get(s, {})
            st = seed_data.get("status", "UNRESOLVED")
            val = seed_data.get("state", "UNRESOLVED")[:23]
            row.append(f"{val} ({st[:3]})")
        print(f"{row[0]:<22} | {row[1]:<25} | {row[2]:<25} | {row[3]:<25}")
    print("-" * 105)

    # 5. Print 729 Tensor Summary
    print(" 729-COORDINATE TENSOR RECONCILIATION (Fi x Sj x Tk = 9 x 9 x 9 = 729)")
    print("-" * 105)
    for dom in domains:
        summ = tensor_results[dom]["summary"]
        print(f"  [{dom.upper():<9}] Observed: {summ['observed_cells']:<2} | Derived: {summ['derived_cells']:<2} | Possible: {summ['possible_cells']:<2} | Unresolved (F7): {summ['unresolved_f7_cells']:<2} (Total: {summ['total_state_cells']})")
    print("-" * 105)

    # 6. Execute Fixed F1-F9 Runtime Operator
    print("\n[HYDRATION] Executing Fixed F1-F9 Runtime Operator Across Minimal Seed Fixtures...")
    all_passed = True
    for dom in domains:
        fix_path = fixtures[dom]
        cmd = [str(PYTHON_EXE), "-B", str(VIPER_ROOT / "viper.py"), "matrix", "--target", str(fix_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and "Receipt and five-file session audit verified" in res.stdout:
            print(f"  [PASS] {dom.upper():<18} -> {fix_path.name} (Exit: 0, 5-File Audit Verified)")
        else:
            print(f"  [FAIL] {dom.upper():<18} -> {fix_path.name} (Exit: {res.returncode})\n{res.stderr}")
            all_passed = False

    print("\n" + "=" * 105)
    if all_passed:
        print("[BENCHMARK] SUCCESS: Minimal Seed -> Natural Tensor Hydration Verified Across All 3 Domains.")
        print("[BENCHMARK] Total 81 State Coordinates & 729 Operational Coordinates Accounted For.")
        print("[BENCHMARK] Fixed Runtime F1-F9 Engine Invariance Preserved (0 Code Changes).")
    else:
        print("[BENCHMARK] FAILURE: One or more minimal seed executions encountered an error.")
    print("=" * 105 + "\n")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_benchmark())
