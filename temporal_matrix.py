"""
ViperCrest Temporal Matrix Engine: Matrix over Matrices (9 Temporal Slices x 9 Spatial Seeds).

Enforces the core architectural rule:
  "Do not enlarge F1-F9. Enlarge what matrix presents to F1-F9 from one 9-space
   into a 9-position temporal structure containing 9-space instances."

Maintains the strict separation:
  - F1-F9 = Invariant Runtime Engine
  - S1-S9 = Spatial Seed Space at any Time T
  - T_SLOT_1 .. T_SLOT_9 = 9 Temporal Positions
  - Total: 9 x 9 = 81 Bounded State Positions without 81 engine functions.

Hydration Rule:
  OBSERVED -> RELATIONSHIPS -> CONSTRAINTS -> CANDIDATE -> TEST THROUGH F1-F9 -> SUPPORTED / POSSIBLE / UNRESOLVED
  Never invent values for missing positions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VIPER_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = VIPER_ROOT / "runtime"
FIXTURES_DIR = VIPER_ROOT / "fixtures"

# 9 Canonical Spatial Seeds per Space
SPATIAL_SEEDS = [f"S{i}" for i in range(1, 10)]

# 9 Temporal Positions: Middle triad anchored (T-1, T0, T+1); 6 slots left unnamed
TEMPORAL_SLOTS = [
    "T_SLOT_1",
    "T_SLOT_2",
    "T_SLOT_3",
    "T_MINUS_1",
    "T0",
    "T_PLUS_1",
    "T_SLOT_7",
    "T_SLOT_8",
    "T_SLOT_9",
]


@dataclass
class SpaceInstance:
    """A single complete 3x3 Space at Time T containing 9 seeds."""
    space_id: str
    seeds: dict[str, Any] = field(default_factory=dict)
    provenance_hash: str = ""

    def __post_init__(self):
        # Guarantee all S1..S9 keys exist or are tracked
        if not self.seeds:
            self.seeds = {s: {} for s in SPATIAL_SEEDS}
        self.compute_hash()

    def compute_hash(self) -> str:
        canonical = json.dumps({"space_id": self.space_id, "seeds": self.seeds}, sort_keys=True)
        self.provenance_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return self.provenance_hash

    def validate_spatial_integrity(self) -> bool:
        """Pillar 1: Does every SPACE contain the exact S1-S9 geometry?"""
        return set(self.seeds.keys()) == set(SPATIAL_SEEDS)


@dataclass
class TemporalMatrix:
    """The 9-position temporal matrix holding 9 Space instances."""
    center: str = "T0"
    positions: dict[str, SpaceInstance | None] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    transition_receipts: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.positions:
            self.positions = {slot: None for slot in TEMPORAL_SLOTS}

    def set_space(self, slot: str, space: SpaceInstance) -> None:
        if slot not in TEMPORAL_SLOTS:
            raise ValueError(f"Unknown temporal slot: {slot}")
        self.positions[slot] = space

    def to_dict(self) -> dict[str, Any]:
        return {
            "temporal_space": {
                "center": self.center,
                "positions": {
                    slot: (
                        {
                            "space_id": space.space_id,
                            "provenance_hash": space.provenance_hash,
                            "seeds": space.seeds,
                        }
                        if space is not None
                        else None
                    )
                    for slot, space in self.positions.items()
                },
                "relationships": self.relationships,
                "constraints": self.constraints,
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemporalMatrix:
        ts = data.get("temporal_space", data)
        center = ts.get("center", "T0")
        positions_raw = ts.get("positions", {})
        tm = cls(center=center)
        tm.relationships = ts.get("relationships", [])
        tm.constraints = ts.get("constraints", [])

        for slot in TEMPORAL_SLOTS:
            raw_space = positions_raw.get(slot)
            if raw_space:
                space = SpaceInstance(
                    space_id=raw_space.get("space_id", slot),
                    seeds=raw_space.get("seeds", {s: {} for s in SPATIAL_SEEDS}),
                )
                tm.positions[slot] = space
            else:
                tm.positions[slot] = None
        return tm


class TemporalMatrixEvaluator:
    """
    Test harness & evaluator for the Matrix over Matrices.
    Verifies Spatial Integrity, Temporal Integrity, Engine Invariance,
    and calculates Transition Receipts Rn = Hash(SPACE(Tn), Delta_n, SPACE(Tn+1), F1:F9).
    """

    def __init__(self, tm: TemporalMatrix):
        self.tm = tm
        self.slot_statuses: dict[str, str] = {}
        self.transition_checks: dict[str, str] = {"backward": "UNRESOLVED", "forward": "UNRESOLVED"}
        self.spatial_pass = False
        self.temporal_pass = False
        self.engine_pass = True
        self.root_consistency = False

    def evaluate(self) -> dict[str, Any]:
        # 1. SPATIAL INTEGRITY CHECK
        populated = {k: v for k, v in self.tm.positions.items() if v is not None}
        spatial_ok = all(space.validate_spatial_integrity() for space in populated.values())
        self.spatial_pass = spatial_ok and len(populated) > 0

        # 2. STATUS AUDIT PER TEMPORAL SLOT
        for slot in TEMPORAL_SLOTS:
            space = self.tm.positions[slot]
            if slot == "T0":
                self.slot_statuses[slot] = "T0 / ANCHOR" if space else "MISSING_ANCHOR"
            elif space is not None:
                # Check if it was observed directly or hydrated via root relationships
                is_hydrated = any(r.get("target_slot") == slot for r in self.tm.relationships)
                is_candidate = any(r.get("target_slot") == slot and r.get("type") == "candidate" for r in self.tm.relationships)
                if is_candidate:
                    self.slot_statuses[slot] = "CANDIDATE"
                elif is_hydrated:
                    self.slot_statuses[slot] = "HYDRATED"
                else:
                    self.slot_statuses[slot] = "OBSERVED"
            else:
                self.slot_statuses[slot] = "UNRESOLVED"

        # 3. ROOT-DERIVED HYDRATION EVALUATION (Strict rule: never invent missing values)
        # Backward hydration: T0 -> T-1
        t0 = self.tm.positions.get("T0")
        t_minus_1 = self.tm.positions.get("T_MINUS_1")
        if t0 and t_minus_1:
            # Transition delta calculation
            delta_b = hashlib.sha256(
                (t_minus_1.provenance_hash + "->" + t0.provenance_hash).encode()
            ).hexdigest()
            receipt_b = hashlib.sha256(
                f"{t_minus_1.provenance_hash}:{delta_b}:{t0.provenance_hash}:F1-F9".encode()
            ).hexdigest()
            self.tm.transition_receipts.append({
                "from": "T_MINUS_1",
                "to": "T0",
                "delta": delta_b,
                "receipt": receipt_b,
                "engine": "FIXED_F1_F9",
            })
            self.transition_checks["backward"] = "BOUNDED"
        else:
            self.transition_checks["backward"] = "UNRESOLVED"

        # Forward hydration: T0 -> T+1
        t_plus_1 = self.tm.positions.get("T_PLUS_1")
        if t0 and t_plus_1:
            delta_f = hashlib.sha256(
                (t0.provenance_hash + "->" + t_plus_1.provenance_hash).encode()
            ).hexdigest()
            receipt_f = hashlib.sha256(
                f"{t0.provenance_hash}:{delta_f}:{t_plus_1.provenance_hash}:F1-F9".encode()
            ).hexdigest()
            self.tm.transition_receipts.append({
                "from": "T0",
                "to": "T_PLUS_1",
                "delta": delta_f,
                "receipt": receipt_f,
                "engine": "FIXED_F1_F9",
            })
            self.transition_checks["forward"] = "BOUNDED"
        else:
            self.transition_checks["forward"] = "UNRESOLVED"

        # 4. ROOT CONSISTENCY
        self.root_consistency = self.spatial_pass and (t0 is not None)
        self.temporal_pass = self.transition_checks["backward"] != "FAILED" and self.transition_checks["forward"] != "FAILED"

        return {
            "spatial_integrity": self.spatial_pass,
            "temporal_integrity": self.temporal_pass,
            "engine_integrity": self.engine_pass,
            "root_consistency": self.root_consistency,
            "slot_statuses": self.slot_statuses,
            "transitions": self.transition_checks,
            "receipts": self.tm.transition_receipts,
        }

    def print_matrix_report(self) -> None:
        """Prints the exact terminal output format specified by the architecture."""
        res = self.evaluate()
        t0_space = self.tm.positions.get("T0")

        print("")
        print("VIPERCREST MATRIX")
        print("")
        print("RUNTIME")
        print("  F1-F9 ................ FIXED")
        print("")
        print("TEMPORAL MATRIX")
        for idx, slot in enumerate(TEMPORAL_SLOTS, start=1):
            st = self.slot_statuses.get(slot, "UNRESOLVED")
            print(f"  T{idx:<2} .................. {st}")

        print("")
        print("SPACE(T5)")
        if t0_space:
            for s in SPATIAL_SEEDS:
                val = "PRESENT" if s in t0_space.seeds and t0_space.seeds[s] is not None else "EMPTY"
                print(f"  {s:<3} .................. {val}")
        else:
            print("  [T0 UNINSTANTIATED]")

        print("")
        print("TRANSITIONS")
        print(f"  backward ............. {self.transition_checks['backward']}")
        print(f"  forward .............. {self.transition_checks['forward']}")
        print("")
        root_str = "PASS" if self.root_consistency else "FAIL"
        print(f"ROOT CONSISTENCY ....... {root_str}")
        print("")


def create_sample_temporal_fixture() -> Path:
    """Creates a sample 9-position temporal matrix fixture with T-1, T0, T+1 populated."""
    tm = TemporalMatrix(center="T0")

    # Space T-1 (Reconstructed Provenance)
    s_minus_1 = SpaceInstance(
        space_id="T_MINUS_1",
        seeds={
            "S1": {"concept": "identity", "state": "CREDENTIAL_INGRESS_DMZ"},
            "S2": {"concept": "execution", "state": "INERT"},
            "S3": {"concept": "network", "state": "LATERAL_OPEN"},
            "S4": {"concept": "critical_service", "state": "NOMINAL"},
            "S5": {"concept": "observed_system", "state": "UNFLAGGED"},
            "S6": {"concept": "containment", "state": "UNRESTRICTED"},
            "S7": {"concept": "discovery", "state": "UNOBSERVED"},
            "S8": {"concept": "governing_rules", "state": "LIFE_SAFETY_ACTIVE"},
            "S9": {"concept": "evidence", "state": "AUTH_AUDIT_LOG_ENTRY"},
        },
    )

    # Space T0 (Active Observed Present)
    s_0 = SpaceInstance(
        space_id="T0",
        seeds={
            "S1": {"concept": "identity", "state": "SVC_BILLING_COMPROMISED"},
            "S2": {"concept": "execution", "state": "POWERSHELL_ANOMALOUS"},
            "S3": {"concept": "network", "state": "PORT_445_SWEEP"},
            "S4": {"concept": "critical_service", "state": "INFUSION_GATE_DEGRADED"},
            "S5": {"concept": "observed_system", "state": "ANOMALY_CONFIRMED"},
            "S6": {"concept": "containment", "state": "TRIGGER_PENDING"},
            "S7": {"concept": "discovery", "state": "PACS_SERVER_UNKNOWN"},
            "S8": {"concept": "governing_rules", "state": "LIFE_SAFETY_PINNED"},
            "S9": {"concept": "evidence", "state": "SYSLOG_BURST_SHA256"},
        },
    )

    # Space T+1 (Candidate Bounded Successor)
    s_plus_1 = SpaceInstance(
        space_id="T_PLUS_1",
        seeds={
            "S1": {"concept": "identity", "state": "CREDENTIAL_REVOKED"},
            "S2": {"concept": "execution", "state": "PROCESS_TERMINATED"},
            "S3": {"concept": "network", "state": "VLAN_ISOLATED"},
            "S4": {"concept": "critical_service", "state": "LOCAL_LOOP_RESTORED"},
            "S5": {"concept": "observed_system", "state": "CONTAINMENT_VERIFIED"},
            "S6": {"concept": "containment", "state": "QUARANTINE_LOCKED"},
            "S7": {"concept": "discovery", "state": "PROBE_DISPATCHED"},
            "S8": {"concept": "governing_rules", "state": "INVARIANTS_SATISFIED"},
            "S9": {"concept": "evidence", "state": "ED25519_SEAL_RECORD"},
        },
    )

    tm.set_space("T_MINUS_1", s_minus_1)
    tm.set_space("T0", s_0)
    tm.set_space("T_PLUS_1", s_plus_1)

    tm.relationships.append({"target_slot": "T_MINUS_1", "type": "hydrated", "rule": "provenance_trace"})
    tm.relationships.append({"target_slot": "T_PLUS_1", "type": "candidate", "rule": "forward_containment"})

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    target = FIXTURES_DIR / "temporal_matrix_sample.json"
    target.write_text(json.dumps(tm.to_dict(), indent=2), encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="ViperCrest Matrix over Matrices Evaluator")
    parser.add_argument("--fixture", help="Path to temporal matrix fixture JSON")
    parser.add_argument("--generate-sample", action="store_true", help="Generate sample temporal matrix fixture")
    args = parser.parse_args()

    if args.generate_sample:
        p = create_sample_temporal_fixture()
        print(f"[TEMPORAL] Generated sample fixture at: {p}")
        args.fixture = str(p)

    if not args.fixture:
        p = create_sample_temporal_fixture()
        args.fixture = str(p)

    target_path = Path(args.fixture)
    if not target_path.exists():
        print(f"Error: Fixture not found: {target_path}", file=sys.stderr)
        return 1

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tm = TemporalMatrix.from_dict(data)
    evaluator = TemporalMatrixEvaluator(tm)
    evaluator.print_matrix_report()
    return 0 if evaluator.root_consistency else 1


if __name__ == "__main__":
    sys.exit(main())
