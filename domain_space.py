"""
ViperCrest Domain Space & Temporal Matrix (9 Temporal Slices x 9 Domain Seeds = 81 Coordinates).

Enforces the three structural controls:
1. F1-F9 remains untouched and invariant.
2. Root -> Stone is the recovered temporal-position vocabulary, not a replacement engine.
3. Hydration produces evidence-bounded candidates, never invented history.

Backward hydration is explicitly defined as:
  'constructing evidence-bounded predecessor candidates'
Distinguishing:
  - OBSERVED
  - DERIVED
  - POSSIBLE
  - CONTRADICTED
  - UNRESOLVED
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Required Invariant: The Fixed F1-F9 Runtime Stages
RUNTIME_STAGES: Tuple[str, ...] = (
    "F1", "F2", "F3", "F4", "F5",
    "F6", "F7", "F8", "F9",
)

# Assertion confirming the invariant runtime stages
assert RUNTIME_STAGES == (
    "F1", "F2", "F3", "F4", "F5",
    "F6", "F7", "F8", "F9"
), "Invariant Violation: Runtime stages must remain strictly F1-F9"

# The 9 Temporal Phases (Recovered Lineage from Root to Stone)
TEMPORAL_PHASES: Tuple[str, ...] = (
    "T1_ROOT",
    "T2_VEIL",
    "T3_PATH_IN",
    "T4_STABILITY",
    "T5_COMPOUNDING",
    "T6_REFRACTING",
    "T7_FLAME",
    "T8_PATH_OUT",
    "T9_STONE",
)

# 9 Canonical Domain Seeds per Space Instance
DOMAIN_SEEDS: Tuple[str, ...] = (
    "S1", "S2", "S3", "S4", "S5",
    "S6", "S7", "S8", "S9",
)

# Valid Epistemic Hydration States
HYDRATION_STATES = {
    "OBSERVED",
    "DERIVED",
    "POSSIBLE",
    "CONTRADICTED",
    "UNRESOLVED",
}


@dataclass
class CartridgeSpec:
    """Assigns domain-specific meaning, labels, and constraints to S1..S9."""
    cartridge_id: str
    name: str
    seed_meanings: Dict[str, str] = field(default_factory=dict)
    invariants: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        # Guarantee mappings for S1..S9 if omitted
        for s in DOMAIN_SEEDS:
            if s not in self.seed_meanings:
                self.seed_meanings[s] = f"seed_{s.lower()}"


# Predefined Default Security IR Cartridge
DEFAULT_SECURITY_CARTRIDGE = CartridgeSpec(
    cartridge_id="SECURITY_IR_DEFAULT",
    name="CISA-Aligned Security Incident Response Cartridge",
    seed_meanings={
        "S1": "Identity / Credentials",
        "S2": "Endpoint Execution",
        "S3": "Network Movement",
        "S4": "Critical-Service Condition",
        "S5": "Current Observed System State",
        "S6": "Containment State",
        "S7": "Unknown / Discovery",
        "S8": "Safety / Governing Constraints",
        "S9": "Evidence / Provenance",
    },
    invariants=[
        {"id": "INV_LIFE_SAFETY", "rule": "Critical services marked life-safety must not be severed"},
        {"id": "INV_CONTAIN_MALICIOUS", "rule": "Endpoints with confirmed anomaly must have containment asserted"},
    ],
)


@dataclass
class DomainSpaceInstance:
    """A single complete 3x3 Space at Time T containing 9 domain seeds."""
    space_id: str
    phase: str
    seeds: Dict[str, Any] = field(default_factory=dict)
    provenance_hash: str = ""

    def __post_init__(self):
        if not self.seeds:
            self.seeds = {s: {} for s in DOMAIN_SEEDS}
        self.compute_hash()

    def compute_hash(self) -> str:
        canonical = json.dumps(
            {"space_id": self.space_id, "phase": self.phase, "seeds": self.seeds},
            sort_keys=True,
            separators=(",", ":"),
        )
        self.provenance_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return self.provenance_hash

    def validate_spatial_integrity(self) -> bool:
        """Pillar 1: Does every SPACE contain the exact S1-S9 geometry?"""
        return set(self.seeds.keys()) == set(DOMAIN_SEEDS)


@dataclass
class TemporalMatrixSpace:
    """
    The 9-position temporal matrix holding 9 complete 3x3 Space instances.
    Total state address space = 9 temporal positions x 9 domain seeds = 81 coordinates.
    """
    center: str = "T5_COMPOUNDING"
    positions: Dict[str, Optional[DomainSpaceInstance]] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    cartridge: CartridgeSpec = field(default_factory=lambda: DEFAULT_SECURITY_CARTRIDGE)
    transition_receipts: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.positions:
            self.positions = {phase: None for phase in TEMPORAL_PHASES}

    def set_space(self, phase: str, space: DomainSpaceInstance) -> None:
        if phase not in TEMPORAL_PHASES:
            raise ValueError(f"Unknown temporal phase: {phase}. Must be one of {TEMPORAL_PHASES}")
        self.positions[phase] = space

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temporal_space": {
                "center": self.center,
                "cartridge_id": self.cartridge.cartridge_id,
                "positions": {
                    phase: (
                        {
                            "space_id": space.space_id,
                            "phase": space.phase,
                            "provenance_hash": space.provenance_hash,
                            "seeds": space.seeds,
                        }
                        if space is not None
                        else None
                    )
                    for phase, space in self.positions.items()
                },
                "relationships": self.relationships,
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], cartridge: Optional[CartridgeSpec] = None) -> TemporalMatrixSpace:
        ts = data.get("temporal_space", data)
        center = ts.get("center", "T5_COMPOUNDING")
        positions_raw = ts.get("positions", {})
        tms = cls(center=center, cartridge=cartridge or DEFAULT_SECURITY_CARTRIDGE)
        tms.relationships = ts.get("relationships", [])

        for phase in TEMPORAL_PHASES:
            raw_space = positions_raw.get(phase)
            if raw_space:
                space = DomainSpaceInstance(
                    space_id=raw_space.get("space_id", phase),
                    phase=phase,
                    seeds=raw_space.get("seeds", {s: {} for s in DOMAIN_SEEDS}),
                )
                tms.positions[phase] = space
            else:
                tms.positions[phase] = None
        return tms

    def validate_spatial_integrity(self) -> bool:
        """Verifies that all populated positions have the exact S1..S9 geometry."""
        populated = [s for s in self.positions.values() if s is not None]
        if not populated:
            return False
        return all(s.validate_spatial_integrity() for s in populated)

    def construct_hydration_report(self) -> Dict[str, str]:
        """
        Evaluates the epistemic hydration status of each of the 9 temporal phases.
        Distinguishes: OBSERVED, DERIVED, POSSIBLE, CONTRADICTED, UNRESOLVED.
        """
        report = {}
        for phase in TEMPORAL_PHASES:
            space = self.positions.get(phase)
            if space is None:
                report[phase] = "UNRESOLVED"
            elif phase == self.center:
                report[phase] = "OBSERVED"
            else:
                # Check relationship links
                rel = next((r for r in self.relationships if r.get("phase") == phase), None)
                if rel:
                    status = rel.get("status", "DERIVED").upper()
                    report[phase] = status if status in HYDRATION_STATES else "DERIVED"
                else:
                    report[phase] = "POSSIBLE"
        return report

    def compute_inter_space_transition_receipt(
        self, from_phase: str, to_phase: str, delta_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates inter-space transition receipt:
        Rn = Hash( SPACE(Tn), Delta_n, SPACE(Tn+1), F1:F9 )
        """
        space_from = self.positions.get(from_phase)
        space_to = self.positions.get(to_phase)
        if not space_from or not space_to:
            raise ValueError(f"Cannot seal transition between uninstantiated spaces: {from_phase} -> {to_phase}")

        h_from = space_from.provenance_hash
        h_to = space_to.provenance_hash
        h_delta = hashlib.sha256(json.dumps(delta_meta, sort_keys=True).encode("utf-8")).hexdigest()
        engine_binding = ":".join(RUNTIME_STAGES)

        canonical_receipt_payload = f"{h_from}:{h_delta}:{h_to}:{engine_binding}"
        receipt_hash = hashlib.sha256(canonical_receipt_payload.encode("utf-8")).hexdigest()

        receipt_entry = {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "from_hash": h_from,
            "to_hash": h_to,
            "delta_hash": h_delta,
            "engine_binding": engine_binding,
            "receipt_hash": receipt_hash,
        }
        self.transition_receipts.append(receipt_entry)
        return receipt_entry

    def format_matrix_summary(self) -> str:
        """Returns the canonical terminal printout string."""
        hyd_report = self.construct_hydration_report()
        center_space = self.positions.get(self.center)

        lines = [
            "",
            "VIPERCREST MATRIX",
            "",
            "RUNTIME",
            "  F1-F9 ................ FIXED",
            "",
            "TEMPORAL MATRIX",
        ]
        for idx, phase in enumerate(TEMPORAL_PHASES, start=1):
            st = hyd_report.get(phase, "UNRESOLVED")
            lines.append(f"  T{idx:<2} ({phase:<14}) .. {st}")

        lines.extend([
            "",
            f"SPACE({self.center})",
        ])
        if center_space:
            for s in DOMAIN_SEEDS:
                val = "PRESENT" if s in center_space.seeds and center_space.seeds[s] is not None else "EMPTY"
                meaning = self.cartridge.seed_meanings.get(s, "")
                lines.append(f"  {s:<3} ({meaning:<26}) .. {val}")
        else:
            lines.append("  [CENTER UNINSTANTIATED]")

        has_backward = any(r.get("to_phase") == self.center for r in self.transition_receipts)
        has_forward = any(r.get("from_phase") == self.center for r in self.transition_receipts)

        lines.extend([
            "",
            "TRANSITIONS",
            f"  backward ............. {'BOUNDED' if has_backward else 'UNRESOLVED'}",
            f"  forward .............. {'BOUNDED' if has_forward else 'UNRESOLVED'}",
            "",
            f"ROOT CONSISTENCY ....... {'PASS' if self.validate_spatial_integrity() else 'FAIL'}",
            "",
        ])
        return "\n".join(lines)
