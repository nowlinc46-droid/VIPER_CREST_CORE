"""The Stem: Autonomous Physical Self-Grounding (physical_grounding.py).

Implements autonomous physical grounding with ZERO OS APIs:
Direct continuous plant quantization from raw physics phase space:
  (position_rad, velocity_rad_s, acceleration_rad_s2) -> discrete lattice coordinates.

ZERO PII.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PlantState:
    joint_name: str
    position_rad: float
    velocity_rad_s: float
    acceleration_rad_s2: float
    quantized_bin: int
    is_stable: bool
    state_digest: str


class PhysicalPlantQuantizer:
    """Quantizes continuous kinematic state into discrete invariant coordinates."""

    def __init__(self, position_bins: int = 100, max_angle_rad: float = math.pi):
        self.bins = position_bins
        self.max_angle = max_angle_rad
        self.bin_width = (2.0 * max_angle_rad) / position_bins

    def quantize_state(
        self,
        joint_name: str,
        pos_rad: float,
        vel_rad_s: float,
        acc_rad_s2: float,
    ) -> PlantState:
        # Clamping to physical range [-pi, +pi]
        clamped_pos = max(-self.max_angle, min(self.max_angle, pos_rad))
        bin_idx = int((clamped_pos + self.max_angle) / self.bin_width)
        bin_idx = min(self.bins - 1, max(0, bin_idx))

        # Stability criteria: acceleration within normal kinetic envelope
        is_stable = abs(acc_rad_s2) < 250.0 and abs(vel_rad_s) < 15.0

        now_utc = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(
            f"{joint_name}:{bin_idx}:{clamped_pos}:{vel_rad_s}:{acc_rad_s2}:{now_utc}".encode("utf-8")
        ).hexdigest()

        return PlantState(
            joint_name=joint_name,
            position_rad=clamped_pos,
            velocity_rad_s=vel_rad_s,
            acceleration_rad_s2=acc_rad_s2,
            quantized_bin=bin_idx,
            is_stable=is_stable,
            state_digest=digest,
        )
