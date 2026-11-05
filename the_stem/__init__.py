"""The Stem: Deterministic Epistemic Brainstem for Embodied AI (Standalone Tool).

Positioned between the probabilistic neural cortex (LLM / VLA / Planner) and physical actuators.
Enforces fail-closed kinetic gating:
  G(S) != empty => SUSPENDED (Zero Motor Torque)

ZERO PII. FAIL-CLOSED INVARIANT EXECUTION.
"""
from __future__ import annotations

from .stem_governor import StemGovernor, GovernorState, ActuationCommand
from .physical_grounding import PhysicalPlantQuantizer, PlantState
from .sensor_bridge import SensorSubstitutionEngine, SensorReading
from .kinetic_gate import KineticTorqueGate
from .automotive_bridge import (
    AndroidAutomotiveStemBridge,
    AutomotiveState,
    AutomotiveActuatorCommand,
    AutomotiveTelemetryFrame,
    VehiclePropertyId,
)

__all__ = [
    "StemGovernor",
    "GovernorState",
    "ActuationCommand",
    "PhysicalPlantQuantizer",
    "PlantState",
    "SensorSubstitutionEngine",
    "SensorReading",
    "KineticTorqueGate",
    "AndroidAutomotiveStemBridge",
    "AutomotiveState",
    "AutomotiveActuatorCommand",
    "AutomotiveTelemetryFrame",
    "VehiclePropertyId",
]
