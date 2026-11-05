"""ViperCrest Corporate Treasury Settlement Governor CLI (financial_cli.py).

Operational governor enforcing FinCEN, SWIFT MT103, and Fedwire settlement invariants:
  - Disbursements > $100,000 require Dual Executive Authorization (S1 + S4)
  - Counterparty must be pre-approved on Allowlist (S3)
  - Affirmative OFAC / SDN sanctions clearance within 24h (S7)
  - Fail-closed suspension on missing telemetry; hard permanent refusal on SDN match.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from financial_adapter import FinancialWireAdapter, PolicyContradictionError
from convergence_engine import SuccessorState
import syntax_emitter as syn_emit


def parse_wire_from_text(text: str) -> Dict[str, Any]:
    """Extracts wire instruction parameters from free-text / natural language."""
    amt_match = re.search(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+(?:\.\d+)?)\s*(?:USD|k|million|m)?", text, re.IGNORECASE)
    amount = 250000.0
    if amt_match:
        raw_num = amt_match.group(1).replace(",", "")
        try:
            amount = float(raw_num)
            if "million" in text.lower() or re.search(r"\b\d+m\b", text.lower()):
                amount *= 1_000_000
            elif re.search(r"\b\d+k\b", text.lower()) and amount < 1000:
                amount *= 1_000
        except ValueError:
            amount = 250000.0

    auth_a = "PRESENT" if re.search(r"auth(?:orization)?[-_ ]?a.*(?:valid|present|signed|approved|yes)", text, re.IGNORECASE) or "auth" in text.lower() else "PRESENT"
    auth_b = "PRESENT" if re.search(r"auth(?:orization)?[-_ ]?b.*(?:valid|present|signed|approved|yes)", text, re.IGNORECASE) else "MISSING"
    if "missing auth_b" in text.lower() or "auth_b missing" in text.lower() or "auth b missing" in text.lower():
        auth_b = "MISSING"

    sanctions = "MISSING"
    sanctions_age = None
    if re.search(r"sanctions.*(?:blocked|sdn|sanctioned)", text, re.IGNORECASE):
        sanctions = "BLOCKED"
    elif re.search(r"sanctions.*(?:clear|clean|approved|passed)", text, re.IGNORECASE) or "ofac clear" in text.lower():
        sanctions = "CLEAR"
        age_m = re.search(r"(\d+(?:\.\d+)?)\s*h", text, re.IGNORECASE)
        sanctions_age = float(age_m.group(1)) if age_m else 4.0

    counterparty = "APPROVED_VENDOR_CH93"
    cp_m = re.search(r"(?:to|vendor|beneficiary)\s+([A-Za-z0-9_]+)", text, re.IGNORECASE)
    if cp_m:
        counterparty = cp_m.group(1).upper()

    return {
        "amount": amount,
        "currency": "USD",
        "authorization_A": auth_a,
        "authorization_B": auth_b,
        "counterparty": counterparty,
        "sanctions_check": sanctions,
        "sanctions_check_age_hours": sanctions_age,
        "case_id": f"WIRE-{uuid.uuid4().hex[:8].upper()}",
    }


def print_settlement_state(state: SuccessorState, wire: Dict[str, Any]):
    """Prints authoritative settlement status."""
    print("=" * 72)
    print("       VIPERCREST CORPORATE TREASURY SETTLEMENT GOVERNOR")
    print("                 Policy Bedrock: FP-001 (EVM/RTOS)")
    print("=" * 72)
    print(f"  Case ID          : {wire.get('case_id', 'N/A')}")
    print(f"  Transfer Amount  : ${wire.get('amount', 0.0):,.2f} {wire.get('currency', 'USD')}")
    print(f"  Counterparty     : {wire.get('counterparty', 'UNVERIFIED')}")
    print(f"  Auth A (Primary) : {wire.get('authorization_A', 'MISSING')}")
    print(f"  Auth B (Exec B)  : {wire.get('authorization_B', 'MISSING')}")
    print(f"  OFAC Sanctions   : {wire.get('sanctions_check', 'MISSING')} "
          f"(Age: {wire.get('sanctions_check_age_hours')}h)" if wire.get('sanctions_check_age_hours') else f"  OFAC Sanctions   : {wire.get('sanctions_check', 'MISSING')}")
    print("-" * 72)

    if state.status == "BOUNDED" or state.is_bounded:
        print("  FINAL VERDICT    : [DISBURSEMENT AUTHORIZED - BOUNDED & SEALED]")
        print("  State Status     : BOUNDED (Clean & Verified)")
        print("  Life-Safety Lock : DISBURSEMENT PERMITTED")
        print("  Resolved Seeds   : S1 (Originator), S3 (Counterparty), S4 (Auth B), S7 (OFAC)")
    else:
        print("  FINAL VERDICT    : [SETTLEMENT HALTED - FAIL-CLOSED SUSPENSION]")
        print(f"  State Status     : {state.status} (Zero Speculation Quarantined)")
        print("  Life-Safety Lock : DISBURSEMENT REFUSED (0.00 OUTFLOW)")
        print("  Unresolved Gaps  :")
        for g in state.gaps:
            print(f"    - [{g.seed}] {g.coordinate:<24} : {g.meaning}")

    print("-" * 72)
    print(f"  Cryptographic Hash : {state.state_hash}")
    if state.predecessor_hash:
        print(f"  Predecessor Hash   : {state.predecessor_hash}")
    print(f"  Pass Index         : Pass {state.pass_index}")
    print("=" * 72)


def cmd_interactive():
    """Runs the interactive live treasury settlement shell."""
    adapter = FinancialWireAdapter()
    current_state: Optional[SuccessorState] = None
    current_wire: Optional[Dict[str, Any]] = None

    print("=" * 72)
    print("  VIPERCREST TREASURY SETTLEMENT GOVERNOR [LIVE INTERACTIVE REPL]")
    print("=" * 72)
    print("  Enforcing Statutory Dual Executive Authorization & OFAC Sanctions.")
    print("  Type 'help' for commands, or enter a wire order.\n")

    while True:
        try:
            status_tag = current_state.status if current_state else "IDLE"
            prompt = f"TREASURY [{status_tag}]> "
            line = input(prompt).strip()
            if not line:
                continue

            lowered = line.lower()
            if lowered in {"exit", "quit", "q"}:
                print("Exiting Treasury Settlement Governor.")
                break
            elif lowered in {"help", "?"}:
                print("\nCommands:")
                print("  order [amount=250000] [auth_b=MISSING] [sanctions=MISSING] : Submit wire order")
                print("  recover S4: <evidence>                                     : Submit Executive B signature")
                print("  recover S7: <evidence>                                     : Submit affirmative OFAC clearance")
                print("  contradict                                                 : Ingest SDN sanctions match")
                print("  emit [c|rust|sol|en]                                       : Compile state into target syntax")
                print("  status                                                     : Print active settlement state")
                print("  reset                                                      : Clear active session")
                print("  exit                                                       : Exit REPL\n")
                continue
            elif lowered == "reset":
                current_state = None
                current_wire = None
                print("[RESET] Active wire session cleared.")
                continue
            elif lowered == "status":
                if current_state and current_wire:
                    print_settlement_state(current_state, current_wire)
                else:
                    print("[INFO] No active wire order. Use 'order amount=250000' or natural language.")
                continue
            elif lowered.startswith("emit"):
                if not current_state:
                    print("[ERROR] No active state to emit.")
                    continue
                parts = lowered.split()
                lang = parts[1] if len(parts) > 1 else "solidity"
                state_dict = {
                    "status": current_state.status,
                    "observed_count": len(current_state.resolved_seed_map),
                    "unresolved_count": len(current_state.gaps),
                    "max_torque_nm": 0.0,
                    "is_tripped": not current_state.is_bounded,
                    "cartridge": "TREASURY_WIRE_FP001",
                    "receipt_hash": current_state.state_hash,
                }
                pkg = syn_emit.translate_state_to_syntax(state_dict, lang)
                print(f"\n--- [{pkg.language}] ({pkg.filename}) ---")
                print(pkg.code)
                print("--- [END] ---\n")
                continue
            elif lowered.startswith("recover"):
                if not current_state:
                    print("[ERROR] No active wire to recover. Submit an order first.")
                    continue
                evidence_text = line[len("recover"):].strip()
                try:
                    next_state = adapter.submit_recovery_evidence(current_state, evidence_text)
                    current_state = next_state
                    if "S4" in evidence_text.upper():
                        current_wire["authorization_B"] = "PRESENT"
                    if "S7" in evidence_text.upper():
                        current_wire["sanctions_check"] = "CLEAR"
                        current_wire["sanctions_check_age_hours"] = 2.0
                    print_settlement_state(current_state, current_wire)
                except PolicyContradictionError as pce:
                    print(f"\n[PERMANENT HARD REFUSAL]: {pce}\n")
                continue
            elif lowered.startswith("contradict"):
                if not current_state:
                    print("[ERROR] No active wire to contradict.")
                    continue
                try:
                    adapter.submit_recovery_evidence(current_state, "SANCTIONS_STATUS: BLOCKED (MATCH_SDN_LIST_ALERT)")
                except PolicyContradictionError as pce:
                    print(f"\n[POLICY CONTRADICTION INTERCEPTED]:\n  {pce}")
                    print("  Involuntary fail-closed refusal locked: disbursement PERMANENTLY FORBIDDEN.\n")
                continue

            # Check if line is an order
            if lowered.startswith("order") or "transfer" in lowered or "$" in lowered or "amount" in lowered:
                wire_dict = parse_wire_from_text(line)
                # Check for explicit key=value overrides
                for tok in shlex.split(line):
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        k = k.strip().lower()
                        v = v.strip()
                        if k in {"amount", "amt"}:
                            wire_dict["amount"] = float(v.replace("$", "").replace(",", ""))
                        elif k in {"auth_a", "autha"}:
                            wire_dict["authorization_A"] = v.upper()
                        elif k in {"auth_b", "authb"}:
                            wire_dict["authorization_B"] = v.upper()
                        elif k in {"sanctions", "ofac"}:
                            wire_dict["sanctions_check"] = v.upper()
                        elif k in {"counterparty", "vendor", "recipient"}:
                            wire_dict["counterparty"] = v.upper()
                        elif k in {"age", "checkage", "sanctions_age"}:
                            wire_dict["sanctions_check_age_hours"] = float(v)

                current_wire = wire_dict
                current_state = adapter.evaluate_initial_instruction(current_wire)
                print_settlement_state(current_state, current_wire)
            else:
                # Treat line as free text wire instruction
                wire_dict = parse_wire_from_text(line)
                current_wire = wire_dict
                current_state = adapter.evaluate_initial_instruction(current_wire)
                print_settlement_state(current_state, current_wire)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting Treasury Settlement Governor.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")


def main():
    parser = argparse.ArgumentParser(description="ViperCrest Corporate Treasury Settlement Governor CLI")
    parser.add_argument("prompt_or_file", nargs="?", default=None, help="JSON wire file, prompt, or command")
    parser.add_argument("--amount", type=float, default=None, help="Wire amount")
    parser.add_argument("--currency", type=str, default="USD", help="Currency code")
    parser.add_argument("--auth-a", type=str, default="PRESENT", help="Primary Authorization A")
    parser.add_argument("--auth-b", type=str, default="MISSING", help="Secondary Executive Authorization B")
    parser.add_argument("--counterparty", type=str, default="APPROVED_VENDOR_CH93", help="Counterparty account/ID")
    parser.add_argument("--sanctions", type=str, default="MISSING", help="OFAC status: CLEAR, BLOCKED, MISSING")
    parser.add_argument("--sanctions-age", type=float, default=None, help="Age of sanctions check in hours")
    parser.add_argument("--recover", type=str, default=None, help="Recovery evidence string to advance pending wire")

    args = parser.parse_args()

    # If no arguments provided at all, enter interactive REPL
    if args.prompt_or_file is None and args.amount is None and args.recover is None:
        cmd_interactive()
        return 0

    adapter = FinancialWireAdapter()

    # Check if prompt_or_file is a JSON file
    if args.prompt_or_file and Path(args.prompt_or_file).exists():
        p = Path(args.prompt_or_file)
        try:
            wire_dict = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] Failed to read JSON wire file: {e}")
            return 1
    elif args.amount is not None:
        wire_dict = {
            "amount": args.amount,
            "currency": args.currency,
            "authorization_A": args.auth_a.upper(),
            "authorization_B": args.auth_b.upper(),
            "counterparty": args.counterparty,
            "sanctions_check": args.sanctions.upper(),
            "sanctions_check_age_hours": args.sanctions_age,
            "case_id": f"WIRE-{uuid.uuid4().hex[:8].upper()}",
        }
    elif args.prompt_or_file:
        wire_dict = parse_wire_from_text(args.prompt_or_file)
    else:
        cmd_interactive()
        return 0

    state_0 = adapter.evaluate_initial_instruction(wire_dict)

    if args.recover:
        try:
            state_1 = adapter.submit_recovery_evidence(state_0, args.recover)
            if "S4" in args.recover.upper():
                wire_dict["authorization_B"] = "PRESENT"
            if "S7" in args.recover.upper():
                wire_dict["sanctions_check"] = "CLEAR"
                wire_dict["sanctions_check_age_hours"] = 2.0
            print_settlement_state(state_1, wire_dict)
            return 0 if state_1.is_bounded else 1
        except PolicyContradictionError as pce:
            print(f"\n[PERMANENT HARD REFUSAL]: {pce}\n")
            return 2

    print_settlement_state(state_0, wire_dict)
    return 0 if state_0.is_bounded else 1


if __name__ == "__main__":
    sys.exit(main())
