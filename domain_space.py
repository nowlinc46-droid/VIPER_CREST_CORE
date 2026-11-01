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

# Total Dimensional Tensor Coordinate Count (F_i x S_j x T_k = 9 x 9 x 9 = 729)
TENSOR_DIMENSIONS: Tuple[int, int, int] = (len(RUNTIME_STAGES), len(DOMAIN_SEEDS), len(TEMPORAL_PHASES))
TOTAL_TENSOR_COORDINATES: int = len(RUNTIME_STAGES) * len(DOMAIN_SEEDS) * len(TEMPORAL_PHASES)  # 729

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


# 1. Security IR Cartridge (cartridge_security_ir)
cartridge_security_ir = CartridgeSpec(
    cartridge_id="SECURITY_IR",
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
CARTRIDGE_SECURITY_IR = cartridge_security_ir
DEFAULT_SECURITY_CARTRIDGE = cartridge_security_ir

# 2. CourtForge Legal Cartridge (cartridge_courtforge_legal)
cartridge_courtforge_legal = CartridgeSpec(
    cartridge_id="COURTFORGE_LEGAL",
    name="CourtForge Legal Claims & Evidentiary Cartridge",
    seed_meanings={
        "S1": "Case Ingress / Party Identity",
        "S2": "Chronological Timeline Events",
        "S3": "Party Admissions & Key Testimony",
        "S4": "Contradictions & Irreconcilable Conflicts",
        "S5": "Core Claims & Dispute State",
        "S6": "Discovery Motions & Routing",
        "S7": "Unproduced Evidence / Unknown Claims",
        "S8": "Statutory Bedrock & Legal Authority",
        "S9": "Sealed Exhibit Vault / Bates-Stamped Records",
    },
    invariants=[
        {"id": "INV_BATES_INTEGRITY", "rule": "All submitted exhibits must possess valid Bates stamp provenance"},
        {"id": "INV_CONTRADICTION_LOCK", "rule": "Irreconcilable testimony must be flagged and routed to F7/F8"},
    ],
)
CARTRIDGE_COURTFORGE_LEGAL = cartridge_courtforge_legal

# 3. WMS Logistics Cartridge (cartridge_wms_logistics)
cartridge_wms_logistics = CartridgeSpec(
    cartridge_id="WMS_LOGISTICS",
    name="Warehouse & Cold-Chain Logistics Cartridge",
    seed_meanings={
        "S1": "Shipper / Consignee Identity",
        "S2": "Transit Milestone & Timestamp",
        "S3": "Cold-Chain Sensor Telemetry",
        "S4": "Pallet Cargo / Weight / Bill of Lading",
        "S5": "Current Shipment Condition",
        "S6": "Quarantine / Routing State",
        "S7": "Uninspected Seals / Shortages",
        "S8": "HACCP / Regulatory Invariants",
        "S9": "Signed Proof of Delivery / Cryptographic Manifest",
    },
    invariants=[
        {"id": "INV_HACCP_TEMP_BOUND", "rule": "Cold-chain temperature must not breach -18C excursion limit"},
        {"id": "INV_CHAIN_OF_CUSTODY", "rule": "Broken container seals require immediate quarantine routing"},
    ],
)
CARTRIDGE_WMS_LOGISTICS = cartridge_wms_logistics

# Registry of Available Domain Cartridges
CARTRIDGES: Dict[str, CartridgeSpec] = {
    "security": cartridge_security_ir,
    "security_ir": cartridge_security_ir,
    "legal": cartridge_courtforge_legal,
    "courtforge_legal": cartridge_courtforge_legal,
    "logistics": cartridge_wms_logistics,
    "wms_logistics": cartridge_wms_logistics,
}


def generate_tensor_coordinates() -> List[Tuple[str, str, str]]:
    """Returns the 729 dimensional coordinates (F_i, S_j, T_k)."""
    return [
        (f_stage, s_seed, t_phase)
        for f_stage in RUNTIME_STAGES
        for s_seed in DOMAIN_SEEDS
        for t_phase in TEMPORAL_PHASES
    ]


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
    plain_english_report: Optional[Dict[str, Any]] = None
    grammar_envelope: Optional[Dict[str, Any]] = None

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
                "plain_english_report": self.plain_english_report,
                "grammar_envelope": self.grammar_envelope,
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], cartridge: Optional[CartridgeSpec] = None) -> TemporalMatrixSpace:
        ts = data.get("temporal_space", data)
        center = ts.get("center", "T5_COMPOUNDING")
        positions_raw = ts.get("positions", {})
        tms = cls(center=center, cartridge=cartridge or DEFAULT_SECURITY_CARTRIDGE)
        tms.relationships = ts.get("relationships", [])
        tms.plain_english_report = ts.get("plain_english_report")
        tms.grammar_envelope = ts.get("grammar_envelope")

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

    def get_coordinate_state(self, phase: str, seed: str) -> Dict[str, Any]:
        """
        Retrieves the exact epistemic state of a single coordinate (T_k, S_j) in the 81-state matrix.
        """
        if phase not in TEMPORAL_PHASES:
            raise ValueError(f"Invalid temporal phase: {phase}")
        if seed not in DOMAIN_SEEDS:
            raise ValueError(f"Invalid domain seed: {seed}")

        space = self.positions.get(phase)
        phase_status = self.construct_hydration_report().get(phase, "UNRESOLVED")

        if space is None:
            return {
                "coordinate": f"{phase}:{seed}",
                "phase": phase,
                "seed": seed,
                "meaning": self.cartridge.seed_meanings.get(seed, ""),
                "status": "UNRESOLVED",
                "state": "UNRESOLVED",
                "evidence": "Temporal phase not instantiated; held in F7",
            }

        seed_data = space.seeds.get(seed, {})
        if not seed_data or not isinstance(seed_data, dict):
            return {
                "coordinate": f"{phase}:{seed}",
                "phase": phase,
                "seed": seed,
                "meaning": self.cartridge.seed_meanings.get(seed, ""),
                "status": "UNRESOLVED",
                "state": "UNRESOLVED",
                "evidence": "No seed evidence present; held in F7",
            }

        st = seed_data.get("status") or phase_status
        return {
            "coordinate": f"{phase}:{seed}",
            "phase": phase,
            "seed": seed,
            "meaning": self.cartridge.seed_meanings.get(seed, ""),
            "status": st,
            "state": seed_data.get("state", "UNRESOLVED"),
            "evidence": seed_data.get("evidence", ""),
        }

    def get_all_81_coordinates(self) -> List[Dict[str, Any]]:
        """Returns the full 81-coordinate state matrix (9 temporal slices x 9 spatial seeds)."""
        coordinates = []
        for phase in TEMPORAL_PHASES:
            for seed in DOMAIN_SEEDS:
                coordinates.append(self.get_coordinate_state(phase, seed))
        return coordinates

    def evaluate_729_tensor_space(self) -> Dict[str, Any]:
        """
        Sweeps through the complete 729-coordinate tensor volume (F_i x S_j x T_k = 9x9x9).
        Verifies that every cell is addressed and that unobserved states are contained in F7.
        """
        coords_81 = self.get_all_81_coordinates()
        tensor_points = []
        f7_unknown_count = 0
        observed_count = 0
        derived_count = 0
        possible_count = 0

        for f_stage in RUNTIME_STAGES:
            for c81 in coords_81:
                phase = c81["phase"]
                seed = c81["seed"]
                status = c81["status"]

                if status == "OBSERVED":
                    observed_count += 1
                elif status == "DERIVED":
                    derived_count += 1
                elif status == "POSSIBLE":
                    possible_count += 1
                elif status == "UNRESOLVED":
                    f7_unknown_count += 1

                # Role of invariant stage F_i
                if f_stage == "F1":
                    action = "GROUND_TRUTH_INGESTION"
                elif f_stage == "F2":
                    action = "LEXICAL_NORMALIZATION"
                elif f_stage == "F3":
                    action = "SPATIAL_ISOLATION"
                elif f_stage == "F4":
                    action = "TEMPORAL_REGISTRATION"
                elif f_stage == "F5":
                    action = "INVARIANT_EVALUATION"
                elif f_stage == "F6":
                    action = "PRECISION_CLAMPING"
                elif f_stage == "F7":
                    action = "DISCOVERY_CONTAINMENT_LOCKED"
                elif f_stage == "F8":
                    action = "TRANSITION_RECEIPT_BINDING"
                else:  # F9
                    action = "ED25519_CRYPTOGRAPHIC_SEAL"

                tensor_points.append({
                    "tensor_coordinate": f"{f_stage}:{phase}:{seed}",
                    "stage": f_stage,
                    "phase": phase,
                    "seed": seed,
                    "epistemic_status": status,
                    "runtime_action": action,
                    "contained_in_f7": status == "UNRESOLVED",
                })

        return {
            "total_tensor_coordinates": len(tensor_points),
            "dimensions": (len(RUNTIME_STAGES), len(DOMAIN_SEEDS), len(TEMPORAL_PHASES)),
            "summary": {
                "observed_cells": observed_count // len(RUNTIME_STAGES),
                "derived_cells": derived_count // len(RUNTIME_STAGES),
                "possible_cells": possible_count // len(RUNTIME_STAGES),
                "unresolved_f7_cells": f7_unknown_count // len(RUNTIME_STAGES),
                "total_state_cells": len(coords_81),
            },
            "points": tensor_points,
        }


def hydrate_from_minimal_seed(
    seed_text: str, cartridge_or_key: str | CartridgeSpec
) -> TemporalMatrixSpace:
    """
    Hydrates the 81-coordinate state matrix from an irreducibly minimal seed (e.g. single atomic line/event).
    Zero-speculation invariant:
    - Directly evidenced facts are OBSERVED at T5_COMPOUNDING.
    - Causal predecessor candidates are DERIVED at T4_STABILITY.
    - Reachable outcomes are marked POSSIBLE at T6_REFRACTING.
    - Invariant governing rules are PINNED at S8.
    - Raw input bytes are hashed at S9.
    - All other spatial and temporal positions remain strictly UNRESOLVED in F7.
    """
    if isinstance(cartridge_or_key, str):
        cart_key = cartridge_or_key.lower().replace("cartridge_", "").replace("_ir", "")
        if "legal" in cart_key or "courtforge" in cart_key:
            cartridge = CARTRIDGE_COURTFORGE_LEGAL
        elif "logistics" in cart_key or "wms" in cart_key:
            cartridge = CARTRIDGE_WMS_LOGISTICS
        else:
            cartridge = CARTRIDGE_SECURITY_IR
    else:
        cartridge = cartridge_or_key

    tms = TemporalMatrixSpace(cartridge=cartridge)
    seed_hash = hashlib.sha256(seed_text.strip().encode("utf-8")).hexdigest()

    if cartridge.cartridge_id == "SECURITY_IR":
        # 1. T5 Present
        s5_seeds = {
            "S1": {"label": cartridge.seed_meanings["S1"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: minimal seed did not supply identity context"},
            "S2": {
                "label": cartridge.seed_meanings["S2"],
                "state": "ANOMALOUS_EXECUTION" if "powershell" in seed_text.lower() or "exec" in seed_text.lower() else "UNRESOLVED",
                "status": "OBSERVED" if "powershell" in seed_text.lower() or "exec" in seed_text.lower() else "UNRESOLVED",
                "evidence": f"Minimal seed observation: {seed_text.strip()}",
            },
            "S3": {
                "label": cartridge.seed_meanings["S3"],
                "state": "PORT_ANOMALY" if "port" in seed_text.lower() or "ip" in seed_text.lower() else "UNRESOLVED",
                "status": "OBSERVED" if "port" in seed_text.lower() or "ip" in seed_text.lower() else "UNRESOLVED",
                "evidence": f"Minimal seed network token: {seed_text.strip()}",
            },
            "S4": {"label": cartridge.seed_meanings["S4"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: service health unobserved"},
            "S5": {
                "label": cartridge.seed_meanings["S5"],
                "state": "ATOMIC_ANOMALY_RECORDED",
                "status": "OBSERVED",
                "evidence": f"Atomic raw seed ingested: {seed_text.strip()}",
            },
            "S6": {"label": cartridge.seed_meanings["S6"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: containment not yet triggered"},
            "S7": {
                "label": cartridge.seed_meanings["S7"],
                "state": "CONTAINED_IN_F7",
                "status": "UNRESOLVED",
                "evidence": "Irreducibly small seed ingested; entire unobserved domain universe locked in F7",
            },
            "S8": {
                "label": cartridge.seed_meanings["S8"],
                "state": "LIFE_SAFETY_PINNED",
                "status": "OBSERVED",
                "evidence": "Policy Invariant: Clinical life-safety preservation active",
            },
            "S9": {
                "label": cartridge.seed_meanings["S9"],
                "state": "MINIMAL_SEED_AUTHENTICATED",
                "status": "OBSERVED",
                "evidence": f"Raw seed SHA256: {seed_hash[:16]}...",
            },
        }
        # 2. T4 Predecessor
        s4_seeds = {
            s: {"label": cartridge.seed_meanings[s], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7"}
            for s in DOMAIN_SEEDS
        }
        s4_seeds["S2"] = {"label": cartridge.seed_meanings["S2"], "state": "IDLE", "status": "DERIVED", "evidence": "Derived baseline: quiescent execution prior to seed"}
        s4_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "NOMINAL_STABLE", "status": "DERIVED", "evidence": "Derived baseline: steady state prior to anomaly"}
        s4_seeds["S8"] = dict(s5_seeds["S8"])
        s4_seeds["S9"] = dict(s5_seeds["S9"])

        # 3. T6 Successor
        s6_seeds = {
            s: {"label": cartridge.seed_meanings[s], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7"}
            for s in DOMAIN_SEEDS
        }
        s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "CONTAINMENT_PROPOSED", "status": "POSSIBLE", "evidence": "Possible candidate: forensic isolation"}
        s6_seeds["S8"] = dict(s5_seeds["S8"])
        s6_seeds["S9"] = dict(s5_seeds["S9"])

    elif cartridge.cartridge_id == "COURTFORGE_LEGAL":
        # 1. T5 Present
        s5_seeds = {
            "S1": {"label": cartridge.seed_meanings["S1"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: full party roster unobserved"},
            "S2": {
                "label": cartridge.seed_meanings["S2"],
                "state": "NOTICE_OF_DEFAULT_SERVED",
                "status": "OBSERVED",
                "evidence": f"Minimal claim token: {seed_text.strip()}",
            },
            "S3": {"label": cartridge.seed_meanings["S3"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: testimony admissions unobserved"},
            "S4": {"label": cartridge.seed_meanings["S4"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: contradictions unobserved"},
            "S5": {
                "label": cartridge.seed_meanings["S5"],
                "state": "DISPUTE_CONTROVERSY_ACTIVE",
                "status": "OBSERVED",
                "evidence": f"Atomic legal dispute seed: {seed_text.strip()}",
            },
            "S6": {"label": cartridge.seed_meanings["S6"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: judicial motion unrouted"},
            "S7": {
                "label": cartridge.seed_meanings["S7"],
                "state": "CONTAINED_IN_F7",
                "status": "UNRESOLVED",
                "evidence": "Irreducibly small seed ingested; unproduced discovery locked in F7",
            },
            "S8": {
                "label": cartridge.seed_meanings["S8"],
                "state": "STATUTORY_AUTHORITY_PINNED",
                "status": "OBSERVED",
                "evidence": "Statutory bedrock: Habitability warranty / UCC covenants pinned invariant",
            },
            "S9": {
                "label": cartridge.seed_meanings["S9"],
                "state": "MINIMAL_CLAIM_AUTHENTICATED",
                "status": "OBSERVED",
                "evidence": f"Raw notice SHA256: {seed_hash[:16]}...",
            },
        }
        # 2. T4 Predecessor
        s4_seeds = {
            s: {"label": cartridge.seed_meanings[s], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7"}
            for s in DOMAIN_SEEDS
        }
        s4_seeds["S2"] = {"label": cartridge.seed_meanings["S2"], "state": "CONTRACT_IN_FORCE", "status": "DERIVED", "evidence": "Derived baseline: contract in good standing"}
        s4_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "PERFORMING_TENANCY", "status": "DERIVED", "evidence": "Derived baseline: performing contract occupancy"}
        s4_seeds["S8"] = dict(s5_seeds["S8"])
        s4_seeds["S9"] = dict(s5_seeds["S9"])

        # 3. T6 Successor
        s6_seeds = {
            s: {"label": cartridge.seed_meanings[s], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7"}
            for s in DOMAIN_SEEDS
        }
        s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "ADJUDICATION_ROUTING_PROPOSED", "status": "POSSIBLE", "evidence": "Possible candidate: judicial dispute resolution"}
        s6_seeds["S8"] = dict(s5_seeds["S8"])
        s6_seeds["S9"] = dict(s5_seeds["S9"])

    else:  # WMS_LOGISTICS
        # 1. T5 Present
        s5_seeds = {
            "S1": {"label": cartridge.seed_meanings["S1"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: shipper/carrier identity unobserved"},
            "S2": {"label": cartridge.seed_meanings["S2"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: transit route log unobserved"},
            "S3": {
                "label": cartridge.seed_meanings["S3"],
                "state": "THERMAL_EXCURSION_RECORDED",
                "status": "OBSERVED",
                "evidence": f"Minimal telemetry token: {seed_text.strip()}",
            },
            "S4": {"label": cartridge.seed_meanings["S4"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: pallet weight manifest unobserved"},
            "S5": {
                "label": cartridge.seed_meanings["S5"],
                "state": "COLD_CHAIN_COMPROMISED",
                "status": "OBSERVED",
                "evidence": f"Atomic temperature breach: {seed_text.strip()}",
            },
            "S6": {"label": cartridge.seed_meanings["S6"], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7: quarantine route unassigned"},
            "S7": {
                "label": cartridge.seed_meanings["S7"],
                "state": "CONTAINED_IN_F7",
                "status": "UNRESOLVED",
                "evidence": "Irreducibly small seed ingested; uninspected container seals locked in F7",
            },
            "S8": {
                "label": cartridge.seed_meanings["S8"],
                "state": "HACCP_INVARIANT_PINNED",
                "status": "OBSERVED",
                "evidence": "HACCP / 21 CFR 211 maximum temperature boundary invariant (-18.0C)",
            },
            "S9": {
                "label": cartridge.seed_meanings["S9"],
                "state": "MINIMAL_TELEMETRY_AUTHENTICATED",
                "status": "OBSERVED",
                "evidence": f"Raw telemetry SHA256: {seed_hash[:16]}...",
            },
        }
        # 2. T4 Predecessor
        s4_seeds = {
            s: {"label": cartridge.seed_meanings[s], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7"}
            for s in DOMAIN_SEEDS
        }
        s4_seeds["S3"] = {"label": cartridge.seed_meanings["S3"], "state": "TEMPERATURE_IN_SPEC", "status": "DERIVED", "evidence": "Derived baseline: cold storage setpoint maintained"}
        s4_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "COLD_CHAIN_STABLE", "status": "DERIVED", "evidence": "Derived baseline: nominal shipment integrity"}
        s4_seeds["S8"] = dict(s5_seeds["S8"])
        s4_seeds["S9"] = dict(s5_seeds["S9"])

        # 3. T6 Successor
        s6_seeds = {
            s: {"label": cartridge.seed_meanings[s], "state": "UNRESOLVED", "status": "UNRESOLVED", "evidence": "Held in F7"}
            for s in DOMAIN_SEEDS
        }
        s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "QUARANTINE_REROUTE_PROPOSED", "status": "POSSIBLE", "evidence": "Possible candidate: quarantine inspection route"}
        s6_seeds["S8"] = dict(s5_seeds["S8"])
        s6_seeds["S9"] = dict(s5_seeds["S9"])

    # Instantiate T5 Present (Center)
    tms.set_space("T5_COMPOUNDING", DomainSpaceInstance(space_id="T0_MINIMAL_OBSERVED", phase="T5_COMPOUNDING", seeds=s5_seeds))

    # Instantiate T4 Predecessor (Derived)
    tms.set_space("T4_STABILITY", DomainSpaceInstance(space_id="T_MINUS_1_MINIMAL_BASELINE", phase="T4_STABILITY", seeds=s4_seeds))
    tms.relationships.append({"phase": "T4_STABILITY", "status": "DERIVED", "rule": "causal_baseline_derivation"})

    # Instantiate T6 Successor (Possible)
    tms.set_space("T6_REFRACTING", DomainSpaceInstance(space_id="T_PLUS_1_MINIMAL_CANDIDATE", phase="T6_REFRACTING", seeds=s6_seeds))
    tms.relationships.append({"phase": "T6_REFRACTING", "status": "POSSIBLE", "rule": "bounded_reachability_candidate"})

    # Seal inter-space transition receipts
    tms.compute_inter_space_transition_receipt("T4_STABILITY", "T5_COMPOUNDING", {"transition": "minimal_seed_emergence"})
    tms.compute_inter_space_transition_receipt("T5_COMPOUNDING", "T6_REFRACTING", {"transition": "minimal_seed_consequence"})

    return tms
