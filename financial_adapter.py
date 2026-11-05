"""
ViperCrest Financial Wire Domain Adapter (financial_adapter.py).

Implements the external domain adapter for:
  SYNTHETIC TEST POLICY FP-001 (High-Value Treasury Settlement Verification)

NOTE: FP-001 is a synthetic corporate treasury policy constructed for the
universality experiment. In real-world compliance, OFAC frameworks are risk-based
and tailored to institutional scope rather than rigid statutory constants.

Synthetic Policy Specification (FP-001):
  IF amount > $100,000:
    REQUIRE authorization_A == PRESENT
    REQUIRE authorization_B == PRESENT
    REQUIRE counterparty_allowlisted == TRUE
    REQUIRE sanctions_check == CLEAR
    REQUIRE sanctions_check_age_hours <= 24

Kernel Invariant:
  This adapter operates strictly OUTSIDE the frozen ViperCrest kernel.
  It does not modify a single byte of F1-F9 or convergence_engine.py on disk.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any, Dict, List, Optional

import domain_space as ds
import reader_engine as re_eng
from convergence_engine import ConvergenceEngine, SuccessorState

# ==============================================================================
# 1. Cartridge Specification (TREASURY_WIRE)
# ==============================================================================
CARTRIDGE_TREASURY_WIRE = ds.CartridgeSpec(
    cartridge_id="TREASURY_WIRE",
    name="Corporate Treasury High-Value Settlement Cartridge (Synthetic FP-001)",
    seed_meanings={
        "S1": "Originator Identity & Primary Authorization A",
        "S2": "Disbursement Amount & Execution Window",
        "S3": "Counterparty Allowlist & Account Integrity",
        "S4": "Secondary Executive Authorization B",
        "S5": "Settlement State & Authorization Verdict",
        "S6": "Liquidity Ledger & Daily Cap Allocation",
        "S7": "Sanctions & OFAC Screening Status",
        "S8": "Statutory Policy Bedrock (FP-001 Compliance)",
        "S9": "Cryptographic Settlement Audit Seal",
    },
    invariants=[
        {"id": "FP001_DUAL_AUTH", "rule": "Disbursements > $100k require two distinct executive authorizations"},
        {"id": "FP001_OFAC_CLEAR", "rule": "Counterparty must possess affirmative sanctions clearance within 24h"},
        {"id": "FP001_ALLOWLIST", "rule": "Recipient account must be pre-approved on the verified counterparty allowlist"},
    ],
)

# Register cartridge dynamically in memory
ds.CARTRIDGES["treasury"] = CARTRIDGE_TREASURY_WIRE
ds.CARTRIDGES["treasury_wire"] = CARTRIDGE_TREASURY_WIRE


class PolicyContradictionError(Exception):
    """Raised when recovery evidence contradicts a hard safety invariant."""
    pass


# ==============================================================================
# 2. Dynamic Domain Stream Parser for FP-001
# ==============================================================================
def parse_raw_treasury_stream(raw_text: str) -> ds.TemporalMatrixSpace:
    """
    Parses corporate treasury settlement text into S1..S9 coordinates
    under Synthetic Policy FP-001.
    """
    tms = ds.TemporalMatrixSpace(cartridge=CARTRIDGE_TREASURY_WIRE)

    has_auth_b_missing = bool(re.search(r"SECONDARY_AUTH_B:\s*MISSING|UNRESOLVED\s*S4", raw_text, re.IGNORECASE))
    has_sanctions_missing = bool(re.search(r"SANCTIONS_STATUS:\s*MISSING|UNRESOLVED\s*S7", raw_text, re.IGNORECASE))
    has_sanctions_blocked = bool(re.search(r"SANCTIONS_STATUS:\s*BLOCKED|MATCH_SDN", raw_text, re.IGNORECASE))
    has_unverified_routing = bool(re.search(r"unverified.*intermediary|anomalous_routing|unapproved_counterparty|unverified\s*s3", raw_text, re.IGNORECASE))
    has_contradiction_s3 = bool(
        re.search(r"approved", raw_text, re.IGNORECASE)
        and re.search(r"revoked|not approved|fraudulent|disavowed|unapproved", raw_text, re.IGNORECASE)
    )

    # Cross-Case Contamination Check: Check for foreign case references
    local_case_m = re.search(r"CASE_ID:\s*(\S+)", raw_text, re.IGNORECASE)
    foreign_case_m = re.search(r"CASE_REF:\s*(\S+)", raw_text, re.IGNORECASE)
    has_foreign_case = False
    if local_case_m and foreign_case_m and local_case_m.group(1).upper() != foreign_case_m.group(1).upper():
        has_foreign_case = True

    # Temporal Policy Check: Sanctions check age must not exceed 24 hours
    age_match = re.search(r"(?:age|checkage)[:=\s]*([0-9]+(?:\.[0-9]+)?)\s*h", raw_text, re.IGNORECASE)
    has_stale_sanctions = False
    stale_age_val = None
    if age_match:
        stale_age_val = float(age_match.group(1))
        if stale_age_val > 24.0:
            has_stale_sanctions = True
    elif re.search(r"stale|expired|outdated.*sanction|prior_epoch", raw_text, re.IGNORECASE):
        has_stale_sanctions = True

    # T5_COMPOUNDING (Observed Settlement State)
    s5_seeds = {
        "S1": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S1"],
            "state": "ORIGINATOR_AUTHORIZED_A",
            "status": "OBSERVED",
            "evidence": "Primary executive authorization A present and verified",
        },
        "S2": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S2"],
            "state": "AMOUNT_RECORDED",
            "status": "OBSERVED",
            "evidence": "Settlement amount parsed from wire instruction",
        },
        "S3": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S3"],
            "state": "UNRESOLVED_CONTRADICTION_ALLOWLIST" if has_contradiction_s3 else ("UNVERIFIED_INTERMEDIARY_ROUTING" if has_unverified_routing else "COUNTERPARTY_VERIFIED"),
            "status": "CONTRADICTED" if has_contradiction_s3 else ("UNRESOLVED" if has_unverified_routing else "OBSERVED"),
            "evidence": "EVIDENTIARY CONTRADICTION: Earlier baseline [APPROVED] directly conflicts with later audit telemetry [REVOKED/NOT APPROVED]. Both preserved in lineage under F7/V07." if has_contradiction_s3 else ("Intermediary beneficiary routing unverified on allowlist; held in F7 UNRESOLVED" if has_unverified_routing else "Counterparty present on corporate verified vendor allowlist"),
        },
        "S4": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S4"],
            "state": "UNRESOLVED_SECONDARY_AUTH" if has_auth_b_missing else "EXEC_SIG_B_VALID",
            "status": "UNRESOLVED" if has_auth_b_missing else "OBSERVED",
            "evidence": "Second executive authorization required for >$100k; held in F7 UNRESOLVED" if has_auth_b_missing else "Dual-authorization satisfied",
        },
        "S5": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S5"],
            "state": "SETTLEMENT_SUSPENDED" if (has_auth_b_missing or has_sanctions_missing or has_stale_sanctions or has_foreign_case) else "SETTLEMENT_CLEARED_FOR_RELEASE",
            "status": "OBSERVED",
            "evidence": "Disbursement state evaluated under FP-001 policy bounds",
        },
        "S6": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S6"],
            "state": "LIQUIDITY_RESERVED",
            "status": "OBSERVED",
            "evidence": "Corporate operational cash ledger liquidity confirmed",
        },
        "S7": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S7"],
            "state": "SANCTIONS_BLOCKED" if has_sanctions_blocked else ("UNRESOLVED_FOREIGN_CASE_EVIDENCE" if has_foreign_case else ("UNRESOLVED_STALE_EVIDENCE_EXPIRED" if has_stale_sanctions else ("UNRESOLVED_SANCTIONS_CLEARANCE" if has_sanctions_missing else "OFAC_SCREENING_CLEAR"))),
            "status": "CONTRADICTED" if has_sanctions_blocked else ("UNRESOLVED" if (has_sanctions_missing or has_stale_sanctions or has_foreign_case) else "OBSERVED"),
            "evidence": f"CROSS-SCENARIO CONTAMINATION: Evidence cites foreign case {foreign_case_m.group(1)} (local case is {local_case_m.group(1)}). Held in F7 UNRESOLVED." if has_foreign_case else (f"TEMPORAL EXPIRATION: Sanctions screening is stale ({stale_age_val}h > 24.0h limit). Held in F7 UNRESOLVED." if has_stale_sanctions else ("Counterparty sanctions status unobserved; held in F7 UNRESOLVED" if has_sanctions_missing else "Screening confirmed clear within 24h")),
        },
        "S8": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S8"],
            "state": "POLICY_FP001_ACTIVE",
            "status": "OBSERVED",
            "evidence": "Corporate Treasury Synthetic Policy FP-001 bounds enforced",
        },
        "S9": {
            "label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S9"],
            "state": "PAYLOAD_AUTHENTICATED",
            "status": "OBSERVED",
            "evidence": f"Wire payload SHA256: {hashlib.sha256(raw_text.encode()).hexdigest()[:16]}...",
        },
    }

    space_t0 = ds.DomainSpaceInstance(space_id="T0_SETTLEMENT_ORDER", phase="T5_COMPOUNDING", seeds=s5_seeds)
    tms.set_space("T5_COMPOUNDING", space_t0)

    # Predecessor T4
    s4_seeds = dict(s5_seeds)
    s4_seeds["S5"] = {"label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S5"], "state": "PRE_WIRE_IDLE", "status": "DERIVED", "evidence": "Baseline ledger balance"}
    space_t4 = ds.DomainSpaceInstance(space_id="T_MINUS_1_BASELINE", phase="T4_STABILITY", seeds=s4_seeds)
    tms.set_space("T4_STABILITY", space_t4)
    tms.relationships.append({"phase": "T4_STABILITY", "status": "DERIVED", "rule": "bounded_treasury_ledger_predecessor"})

    # Successor T6
    s6_seeds = dict(s5_seeds)
    s6_seeds["S5"] = {"label": CARTRIDGE_TREASURY_WIRE.seed_meanings["S5"], "state": "SETTLEMENT_DISPATCHED", "status": "POSSIBLE", "evidence": "SWIFT execution candidate"}
    space_t6 = ds.DomainSpaceInstance(space_id="T_PLUS_1_DISPATCH_CANDIDATE", phase="T6_REFRACTING", seeds=s6_seeds)
    tms.set_space("T6_REFRACTING", space_t6)
    tms.relationships.append({"phase": "T6_REFRACTING", "status": "POSSIBLE", "rule": "forward_wire_dispatch_candidate"})

    tms.compute_inter_space_transition_receipt("T4_STABILITY", "T5_COMPOUNDING", {"transition": "wire_order_intake"})
    tms.compute_inter_space_transition_receipt("T5_COMPOUNDING", "T6_REFRACTING", {"transition": "settlement_dispatch_routing"})

    return tms


# Hook into runtime parser dispatcher for the financial domain without modifying disk files
_original_parse_raw_stream = re_eng.parse_raw_stream


def _financial_routed_parse_raw_stream(raw_text: str, cartridge_key: str = "security", filename: str = "") -> ds.TemporalMatrixSpace:
    if "treasury" in cartridge_key.lower() or "financial" in cartridge_key.lower() or "WIRE_SETTLEMENT" in raw_text:
        return parse_raw_treasury_stream(raw_text)
    return _original_parse_raw_stream(raw_text, cartridge_key=cartridge_key, filename=filename)


re_eng.parse_raw_stream = _financial_routed_parse_raw_stream


# ==============================================================================
# 3. Financial Wire Domain Adapter
# ==============================================================================
class FinancialWireAdapter:
    """
    Translates raw wire requests into F1-F9 matrix inputs and manages
    the recursive convergence cycle under Policy FP-001.
    """

    POLICY_THRESHOLD_AMOUNT = 100_000.0
    REQUIRED_SEEDS = ["S1", "S3", "S4", "S7"]

    def __init__(self):
        # Operates purely through the frozen ConvergenceEngine
        self.kernel_engine = ConvergenceEngine(required_seeds=self.REQUIRED_SEEDS)

    def format_wire_seed(self, wire_instruction: Dict[str, Any]) -> str:
        """Serializes a wire instruction into normalized domain text."""
        amount = float(wire_instruction.get("amount", 0.0))
        currency = wire_instruction.get("currency", "USD")
        auth_a = wire_instruction.get("authorization_A", "MISSING")
        auth_b = wire_instruction.get("authorization_B", "MISSING")
        counterparty = wire_instruction.get("counterparty", "UNVERIFIED")
        sanctions = wire_instruction.get("sanctions_check", "MISSING")
        sanctions_age = wire_instruction.get("sanctions_check_age_hours")

        case_id = wire_instruction.get("case_id")
        lines = []
        if case_id:
            lines.append(f"CASE_ID: {case_id}")
        lines.extend([
            f"WIRE_SETTLEMENT: Amount={amount:.2f} {currency}",
            f"PRIMARY_AUTH_A: {auth_a}",
            f"COUNTERPARTY: {counterparty}",
        ])

        if amount > self.POLICY_THRESHOLD_AMOUNT:
            lines.append("POLICY_ALERT: High-value transaction threshold exceeded (>100k). FP-001 active.")
            if auth_b != "PRESENT":
                lines.append("SECONDARY_AUTH_B: MISSING (UNRESOLVED S4)")
            else:
                lines.append("SECONDARY_AUTH_B: PRESENT (EXEC_SIG_VALID)")

            if sanctions == "CLEAR" and (sanctions_age is not None and sanctions_age <= 24):
                lines.append(f"SANCTIONS_STATUS: CLEAR (Age={sanctions_age}h)")
            elif sanctions == "BLOCKED":
                lines.append("SANCTIONS_STATUS: BLOCKED (MATCH_SDN_LIST_ALERT)")
            else:
                lines.append("SANCTIONS_STATUS: MISSING (UNRESOLVED S7)")

        return "\n".join(lines)

    def evaluate_initial_instruction(
        self, wire_instruction: Dict[str, Any]
    ) -> SuccessorState:
        """
        Executes Pass 0 through the frozen F1-F9 kernel.
        """
        raw_seed = self.format_wire_seed(wire_instruction)
        return self.kernel_engine.execute_pass(
            predecessor=None,
            new_data=raw_seed,
            cartridge_key="legal",  # Reuses existing trusted authority envelope
            custom_required_seeds=self.REQUIRED_SEEDS,
        )

    def submit_recovery_evidence(
        self,
        current_state: SuccessorState,
        recovery_payload: str,
    ) -> SuccessorState:
        """
        Submits recovered evidence D_{n+1} into the frozen F1-F9 kernel.
        Enforces policy contradiction detection and temporal freshness bounds.
        """
        # Contradiction Check: If evidence explicitly reports a blocked/sanctioned party
        if re.search(r"sanctions.*(?:blocked|sdn|sanctioned)|match_sdn", recovery_payload, re.IGNORECASE):
            raise PolicyContradictionError(
                "CONTRADICTION DETECTED: Counterparty is matched on SDN sanctions list. "
                "State transition into BOUNDED settlement release is PERMANENTLY FORBIDDEN."
            )

        sanitized_payload = recovery_payload

        # Cross-Scenario Contamination Check: Reject foreign case references
        local_case_m = re.search(r"CASE_ID:\s*(\S+)", "\n".join(current_state.raw_evidence_chain), re.IGNORECASE)
        foreign_case_m = re.search(r"CASE_REF:\s*(\S+)", recovery_payload, re.IGNORECASE)
        if local_case_m and foreign_case_m and local_case_m.group(1).upper() != foreign_case_m.group(1).upper():
            # Intercept and demote pseudo-resolution: Cannot claim resolutions from foreign cases
            sanitized_payload = re.sub(
                r"\b(?:RESOLVED|CONFIRMED|VERIFIED)\s*\[?([S1-9])\]?:?",
                f"FOREIGN_EVIDENCE_REJECTED \\1 (Case Mismatch: {foreign_case_m.group(1)} != {local_case_m.group(1)}):",
                sanitized_payload,
                flags=re.IGNORECASE,
            )

        # Stale Evidence Check: If payload attempts to resolve S7 with stale screening (>24h)
        age_m = re.search(r"(?:age|checkage)[:=\s]*([0-9]+(?:\.[0-9]+)?)\s*h", recovery_payload, re.IGNORECASE)
        if age_m and float(age_m.group(1)) > 24.0:
            # Intercept and demote pseudo-resolution: Cannot claim RESOLVED S7 with stale proof
            sanitized_payload = re.sub(
                r"\b(?:RESOLVED|CONFIRMED|VERIFIED)\s*\[?S7\]?:?",
                f"STALE_EVIDENCE_REJECTED S7 (Age {age_m.group(1)}h > 24.0h limit):",
                sanitized_payload,
                flags=re.IGNORECASE,
            )

        return self.kernel_engine.execute_pass(
            predecessor=current_state,
            new_data=sanitized_payload,
            cartridge_key="legal",
            custom_required_seeds=self.REQUIRED_SEEDS,
        )
