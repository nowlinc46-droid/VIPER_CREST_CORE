"""
ViperCrest Academic Distribution Ledger - Full Chain Verifier
Location: C:\\ViperCrest_Distribution\\tools\\verify_ledger_chain.py

Verifies the cryptographic and semantic integrity of the append-only ledger:
- Genesis validation
- Hash-chaining continuity
- Strict block index sequencing
- Non-negotiable legal restrictions
- Absence of forbidden financial/equity/token language
- Uniqueness of Copy IDs
- Synchronization with ledger_head.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DIST_ROOT = Path(__file__).resolve().parent.parent
LEDGER_FILE = DIST_ROOT / "registry" / "ledger.jsonl"
HEAD_FILE = DIST_ROOT / "registry" / "ledger_head.json"

EXPECTED_PUBLIC_KEY_FINGERPRINT = "bce4e2a249e2530a60557ca9aa19f5151941ef67914c60f110c8bb46844f711f"
GENESIS_PREV_HASH = "0" * 64

PROHIBITED_TERMS = [
    r"\bequity\b",
    r"\bcompany stock\b",
    r"\bshares\b",
    r"\bprofit sharing\b",
    r"\bprofit participation\b",
    r"\brevenue share\b",
    r"\binvestment contract\b",
    r"\bsecurity token\b",
    r"\bcryptocurrency\b",
    r"\btransferable token\b",
]


def canonical_json(data: Dict[str, Any]) -> str:
    """Canonical compact JSON string."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_block_hash(block: Dict[str, Any]) -> str:
    """Computes SHA-256 hash over canonical representation of the block (excluding block_hash)."""
    block_copy = {k: v for k, v in block.items() if k != "block_hash"}
    canonical = canonical_json(block_copy).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def check_prohibited_terms(text: str) -> List[str]:
    """Finds prohibited affirmative financial / equity / token claims in text.
    Explicit disclaimers (e.g. 'no equity', 'zero equity', 'no investment', 'no shares') are permitted.
    """
    found = []
    # If the text is the standard negation disclaimer, it is safe
    safe_disclaimer_patterns = [
        r"no\s+equity",
        r"zero\s+equity",
        r"no\s+investment",
        r"zero\s+investment",
        r"no\s+shares",
        r"zero\s+shares",
        r"no\s+profit",
        r"conveys\s+zero\s+equity",
    ]
    
    # Strip known safe disclaimer clauses before checking for affirmative claims
    cleaned = text.lower()
    for s_pat in safe_disclaimer_patterns:
        cleaned = re.sub(s_pat, " ", cleaned)

    for pat in PROHIBITED_TERMS:
        if re.search(pat, cleaned, re.IGNORECASE):
            found.append(pat)
    return found


def verify_ledger(ledger_path: Path, head_path: Optional[Path] = None) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """Performs deep cryptographic audit on ledger.jsonl."""
    errors: List[str] = []
    blocks: List[Dict[str, Any]] = []

    if not ledger_path.exists():
        return False, [f"Ledger file not found: {ledger_path}"], []

    with open(ledger_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                b = json.loads(line)
                blocks.append(b)
            except Exception as e:
                errors.append(f"Line {line_no}: Failed to parse JSON block: {e}")

    if not blocks:
        return False, ["Ledger is empty. No Genesis block found."], []

    # 1. Verify Genesis Block (Block 0)
    genesis = blocks[0]
    if genesis.get("block_index") != 0:
        errors.append(f"Block 0 index invalid: got {genesis.get('block_index')}, expected 0")
    if genesis.get("copy_id") != "VC-ACADEMIC-GENESIS":
        errors.append(f"Block 0 Copy ID invalid: got {genesis.get('copy_id')}, expected VC-ACADEMIC-GENESIS")
    if genesis.get("previous_block_hash") != GENESIS_PREV_HASH:
        errors.append(f"Genesis previous_block_hash invalid: got {genesis.get('previous_block_hash')}")

    # 2. Iterate through chain
    seen_copy_ids = set()
    prev_hash = GENESIS_PREV_HASH

    for idx, b in enumerate(blocks):
        b_idx = b.get("block_index")
        copy_id = b.get("copy_id")

        # Check block indexing continuity
        if b_idx != idx:
            errors.append(f"Block sequence error at position {idx}: expected index {idx}, got {b_idx}")

        # Check Copy ID uniqueness
        if copy_id in seen_copy_ids:
            errors.append(f"Duplicate Copy ID detected: {copy_id} at Block {idx}")
        seen_copy_ids.add(copy_id)

        # Check previous block hash linkage
        if idx > 0:
            if b.get("previous_block_hash") != prev_hash:
                errors.append(
                    f"Hash link broken at Block {idx} ({copy_id}): "
                    f"previous_block_hash is {b.get('previous_block_hash')}, expected {prev_hash}"
                )

        # Check current block hash validity
        calc_hash = compute_block_hash(b)
        recorded_hash = b.get("block_hash")
        if recorded_hash != calc_hash:
            errors.append(
                f"Block {idx} hash invalid: recorded {recorded_hash}, calculated {calc_hash}"
            )

        # Check non-negotiable legal invariants
        if b.get("commercial_rights") is not False:
            errors.append(f"Block {idx} violation: commercial_rights must be False")
        if b.get("equity_rights") is not False:
            errors.append(f"Block {idx} violation: equity_rights must be False")
        if b.get("profit_rights") is not False:
            errors.append(f"Block {idx} violation: profit_rights must be False")
        if b.get("transferable") is not False:
            errors.append(f"Block {idx} violation: transferable must be False")
        if b.get("issuance_authority") is not False:
            errors.append(f"Block {idx} violation: issuance_authority must be False")
        if b.get("donation_price_usd") != 0:
            errors.append(f"Block {idx} violation: donation_price_usd must be 0")

        # Check public key fingerprint
        fp = b.get("public_key_fingerprint", "").lower()
        if fp != EXPECTED_PUBLIC_KEY_FINGERPRINT:
            errors.append(f"Block {idx} public_key_fingerprint mismatch: got {fp}")

        # Scan notes / descriptions for prohibited terminology
        notes = b.get("notes", "")
        prohibited_found = check_prohibited_terms(notes)
        if prohibited_found:
            errors.append(f"Block {idx} contains prohibited terminology in notes: {prohibited_found}")

        prev_hash = recorded_hash or calc_hash

    # 3. Verify ledger_head.json sync
    if head_path and head_path.exists():
        try:
            with open(head_path, "r", encoding="utf-8") as f:
                head_data = json.load(f)
            last_block = blocks[-1]
            if head_data.get("head_block_index") != last_block.get("block_index"):
                errors.append(
                    f"ledger_head.json desynchronized on index: "
                    f"head has {head_data.get('head_block_index')}, ledger has {last_block.get('block_index')}"
                )
            if head_data.get("head_block_hash") != last_block.get("block_hash"):
                errors.append("ledger_head.json desynchronized on head block hash")
        except Exception as e:
            errors.append(f"Failed to read ledger_head.json: {e}")

    return len(errors) == 0, errors, blocks


def run_audit(ledger_path: Path, head_path: Optional[Path] = None) -> bool:
    print("=" * 70)
    print("VIPERCREST ACADEMIC DISTRIBUTION LEDGER AUDIT")
    print(f"Ledger: {ledger_path}")
    print("=" * 70)

    is_valid, errors, blocks = verify_ledger(ledger_path, head_path)

    print(f"Total Blocks Scanned: {len(blocks)}")
    for b in blocks:
        status_tag = f"[{b.get('issuer_status', 'UNKNOWN')}]"
        print(f"  Block #{b.get('block_index'):02d} | {b.get('copy_id'):<20} | {status_tag:<24} | Hash: {b.get('block_hash', '')[:16]}...")

    print("-" * 70)
    if is_valid:
        print("[PASS] LEDGER CHAIN FULLY VERIFIED. NO TAMPERING DETECTED.")
        print("  - Cryptographic Hash Chain: INTACT")
        print("  - Sequence Continuity:      INTACT")
        print("  - Zero Equity Invariants:   ENFORCED")
        print("  - Genesis Anchor:           CONFIRMED")
        print("=" * 70)
        return True
    else:
        print(f"[FAIL] LEDGER VERIFICATION FAILED WITH {len(errors)} ERRORS:")
        for err in errors:
            print(f"  - {err}")
        print("=" * 70)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify ViperCrest Academic Ledger Chain")
    parser.add_argument("--ledger", default=str(LEDGER_FILE), help="Path to ledger.jsonl")
    parser.add_argument("--head", default=str(HEAD_FILE), help="Path to ledger_head.json")
    args = parser.parse_args()

    success = run_audit(Path(args.ledger), Path(args.head))
    sys.exit(0 if success else 1)
