"""
ViperCrest Recursive Convergence Engine (convergence_engine.py).

Implements the universal state-recovery loop:
  RECEIVE -> F1-F9 -> TEST -> BOUNDED?
  Yes -> SEAL
  No  -> SUSPEND -> EXPOSE GAP -> RECOVER -> RE-INGEST -> F1-F9 -> TEST AGAIN

Formal Recurrence:
  S_n = F1_F9(S_{n-1}, D_n)
  G_n = GAPS(S_n)

  If G_n != empty_set:
    State = SUSPENDED (a legitimate, first-class state, NOT a failure)
    Recovery request generated from G_n.
  If G_n == empty_set:
    State = BOUNDED -> SEALED (Ed25519 signature + chained receipt)

Core Invariants Enforced:
1. One fixed F1-F9 kernel (zero modifications to underlying engine).
2. S_{n-1} is never discarded; its hash is bound as predecessor_hash in S_n.
3. Zero guessing: unobserved coordinates remain in F7 UNRESOLVED until D_{n+1} is supplied.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import ai_contract as aic
import domain_space as ds
import reader_engine as re_eng
from viper_core import canonical_json


@dataclass
class Gap:
    """Represents a specific unresolved coordinate preventing advancement."""
    coordinate: str               # e.g. "T5_COMPOUNDING:S7"
    phase: str                    # e.g. "T5_COMPOUNDING"
    seed: str                     # e.g. "S7"
    meaning: str                  # Domain label (e.g. "Unknown / Discovery")
    status: str                   # "UNRESOLVED"
    evidence: str                 # Reason for gap
    recovery_directive: str       # Actionable prompt for recovering D_{n+1}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SuccessorState:
    """An immutable snapshot of a state pass in the convergence chain."""
    pass_index: int
    state_id: str
    state_hash: str
    predecessor_hash: Optional[str]
    cartridge_id: str
    status: str                   # "SUSPENDED" | "BOUNDED" | "SEALED"
    gaps: List[Gap] = field(default_factory=list)
    raw_evidence_chain: List[str] = field(default_factory=list)
    resolved_seed_map: Dict[str, str] = field(default_factory=dict)
    latest_delta: str = ""
    epistemic_summary: Dict[str, int] = field(default_factory=dict)
    coordinates_81: List[Dict[str, Any]] = field(default_factory=list)
    session_id: Optional[str] = None
    receipt_verified: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_bounded(self) -> bool:
        return len(self.gaps) == 0 and self.status in {"BOUNDED", "SEALED"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pass_index": self.pass_index,
            "state_id": self.state_id,
            "state_hash": self.state_hash,
            "predecessor_hash": self.predecessor_hash,
            "cartridge_id": self.cartridge_id,
            "status": self.status,
            "gap_count": len(self.gaps),
            "gaps": [g.to_dict() for g in self.gaps],
            "resolved_seeds": list(self.resolved_seed_map.keys()),
            "latest_delta": self.latest_delta,
            "epistemic_summary": self.epistemic_summary,
            "session_id": self.session_id,
            "receipt_verified": self.receipt_verified,
            "timestamp": self.timestamp,
        }


class ConvergenceEngine:
    """
    Orchestrates the recursive state traversal without mutating the invariant F1-F9 kernel.
    """

    def __init__(self, required_seeds: Optional[List[str]] = None):
        """
        Args:
            required_seeds: Specific seeds that must be resolved for the state to reach BOUNDED.
                            Default is ["S1", "S2", "S7"].
        """
        self.executor = aic.ViperCrestContractExecutor()
        self.required_seeds = required_seeds or ["S1", "S2", "S7"]

    def is_coordinate_unresolved(self, coord_info: Dict[str, Any]) -> bool:
        """Determines if a coordinate represents an unresolved gap."""
        status = coord_info.get("status", "")
        state = str(coord_info.get("state", ""))
        evidence = str(coord_info.get("evidence", ""))

        if status == "UNRESOLVED":
            return True
        if state.startswith("UNRESOLVED") or state.startswith("UNPRODUCED"):
            return True
        if "HELD IN F7 UNRESOLVED" in evidence.upper() and state not in {"NONE_PENDING", "RESOLVED", "VERIFIED_CLEAN"}:
            return True
        return False

    def extract_gaps(
        self,
        tms: ds.TemporalMatrixSpace,
        required_seeds: Optional[List[str]] = None,
        resolved_overrides: Optional[Dict[str, str]] = None,
    ) -> List[Gap]:
        """
        Derives the gap set G_n = GAPS(S_n).
        Inspects the present observation slice (T5_COMPOUNDING) for UNRESOLVED states.
        """
        req = required_seeds or self.required_seeds
        overrides = resolved_overrides or {}
        gaps: List[Gap] = []
        center_phase = tms.center

        for seed in req:
            # If explicit recovery evidence has resolved this seed, it is not a gap
            if seed in overrides:
                continue

            coord_info = tms.get_coordinate_state(center_phase, seed)
            if self.is_coordinate_unresolved(coord_info):
                meaning = coord_info.get("meaning") or tms.cartridge.seed_meanings.get(seed, seed)
                evidence = coord_info.get("evidence", "Missing observation")
                directive = (
                    f"Coordinate {center_phase}:{seed} ({meaning}) is UNRESOLVED. "
                    f"Provide physical telemetry, event record, or documentary evidence for {meaning} to advance."
                )
                gaps.append(
                    Gap(
                        coordinate=f"{center_phase}:{seed}",
                        phase=center_phase,
                        seed=seed,
                        meaning=meaning,
                        status="UNRESOLVED",
                        evidence=evidence,
                        recovery_directive=directive,
                    )
                )
        return gaps

    def parse_recovery_data(self, data: str) -> Dict[str, str]:
        """
        Extracts resolved seed assertions from recovered evidence.
        Recognizes patterns like:
          - 'RESOLVED S7: ...'
          - 'DISCOVERY S7: ...'
          - 'S7 verified: ...'
          - Or semantic discovery matches (subpoena, tickets produced, seal verified clean)
        """
        resolutions: Dict[str, str] = {}
        for line in data.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            # Explicit seed tag: e.g. "RESOLVED S7: ..." or "[S7] ..."
            m = re.search(r"\b(?:RESOLVED|DISCOVERY|CONFIRMED|VERIFIED)\s*\[?(S[1-9])\]?:\s*(.+)", line_str, re.IGNORECASE)
            if m:
                seed_id = m.group(1).upper()
                resolutions[seed_id] = m.group(2).strip()
            elif re.search(r"secondary seal verified clean|threat intelligence.*clean|dispatch ticket.*produced|tickets produced", line_str, re.IGNORECASE):
                # Standard semantic recovery for S7
                resolutions["S7"] = line_str
            elif re.search(r"contractor records produced|subpoena.*produced", line_str, re.IGNORECASE):
                resolutions["S7"] = line_str
        return resolutions

    def execute_pass(
        self,
        predecessor: Optional[SuccessorState],
        new_data: str,
        cartridge_key: str = "security",
        custom_required_seeds: Optional[List[str]] = None,
    ) -> SuccessorState:
        """
        Executes a single traversal S_n = F1-F9(S_{n-1}, D_n).
        """
        pass_idx = 0 if predecessor is None else predecessor.pass_index + 1
        predecessor_hash = predecessor.state_hash if predecessor else None

        # 1. Accumulate evidence chain & resolved seed mappings
        resolved_map = dict(predecessor.resolved_seed_map) if predecessor else {}
        evidence_chain = list(predecessor.raw_evidence_chain) if predecessor else []
        evidence_chain.append(new_data)

        # Parse any explicit recovery resolutions from new_data
        new_resolutions = self.parse_recovery_data(new_data)
        resolved_map.update(new_resolutions)

        combined_input = "\n".join(evidence_chain)

        # 2. Build AI Request Envelope (Unverified Input)
        envelope = aic.AIRequestEnvelope(
            intent="analyze",
            cartridge=cartridge_key,
            observations=[{"raw_text": combined_input}],
            requested_action="matrix",
        )

        # 3. Dispatch into ViperCrest Invariant Contract Executor (runs F1-F9)
        response = self.executor.execute(envelope)

        # 4. Parse domain space using the cartridge's parser
        tms = re_eng.parse_raw_stream(combined_input, cartridge_key=cartridge_key)

        # 5. Extract G_n = GAPS(S_n) considering resolved overrides
        gaps = self.extract_gaps(
            tms,
            required_seeds=custom_required_seeds,
            resolved_overrides=resolved_map,
        )

        # 6. Determine state boundary status
        if not gaps:
            status = "BOUNDED"
        else:
            status = "SUSPENDED"

        # 7. Compute cryptographic state hash binding predecessor
        state_id = f"state_pass_{pass_idx}_{uuid.uuid4().hex[:8]}"
        state_payload = {
            "pass_index": pass_idx,
            "predecessor_hash": predecessor_hash,
            "evidence_digest": hashlib.sha256(combined_input.encode("utf-8")).hexdigest(),
            "status": status,
            "gaps": [g.coordinate for g in gaps],
            "resolved_seeds": sorted(list(resolved_map.keys())),
            "cartridge": tms.cartridge.cartridge_id,
        }
        state_hash = hashlib.sha256(canonical_json(state_payload).encode("utf-8")).hexdigest()

        return SuccessorState(
            pass_index=pass_idx,
            state_id=state_id,
            state_hash=state_hash,
            predecessor_hash=predecessor_hash,
            cartridge_id=tms.cartridge.cartridge_id,
            status=status,
            gaps=gaps,
            raw_evidence_chain=evidence_chain,
            resolved_seed_map=resolved_map,
            latest_delta=new_data,
            epistemic_summary=response.epistemic_summary,
            coordinates_81=response.coordinates_81,
            session_id=response.session_id,
            receipt_verified=response.session_receipt_verified,
        )

    def run_convergence_loop(
        self,
        initial_data: str,
        recovery_oracle: Callable[[SuccessorState], Optional[str]],
        cartridge_key: str = "security",
        max_passes: int = 5,
        required_seeds: Optional[List[str]] = None,
    ) -> Tuple[SuccessorState, List[SuccessorState]]:
        """
        Executes the full automated convergence loop:
          S_0 -> F1..9 -> G_0 -> D_1 -> S_1 -> ... -> BOUNDED -> SEAL
        """
        history: List[SuccessorState] = []
        current: Optional[SuccessorState] = None
        next_data = initial_data

        for _ in range(max_passes):
            current = self.execute_pass(
                predecessor=current,
                new_data=next_data,
                cartridge_key=cartridge_key,
                custom_required_seeds=required_seeds,
            )
            history.append(current)

            if current.is_bounded:
                break

            # State is SUSPENDED -> invoke recovery oracle for D_{n+1}
            recovered = recovery_oracle(current)
            if not recovered:
                # No more data can be recovered; halts legitimately in SUSPENDED
                break
            next_data = recovered

        return current, history
