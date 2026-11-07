"""
ViperCrest Contradiction Adjudication Full-Stack Investigation Test.
Tests whether contradictory evidence collapses via last-write-wins or is adjudicated
across the 4 architectural layers of the system:
1. Bare Convergence Engine (parse_recovery_data & execute_pass)
2. Domain Cartridge Layer (CourtForge & WMS Invariant Locks)
3. Financial / Settlement Gate (PolicyContradictionError Interception)
4. Embodied Kinetic Brainstem (Sensor Divergence & Physical Gate Clamping)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import pytest
from convergence_engine import ConvergenceEngine, SuccessorState
from reader_engine import parse_raw_stream
from financial_adapter import FinancialWireAdapter, PolicyContradictionError
from the_stem.stem_governor import StemGovernor, ActuationCommand, GovernorState
from the_stem.sensor_bridge import SensorReading
from the_stem.kinetic_gate import KineticTorqueGate, TorqueLimitConfig


def test_tier_1_bare_engine_contradiction_collapse():
    """
    Tier 1: Bare Convergence Engine.
    Examines Case 6:
      Record A: 'VERIFIED [S7]: secondary seal confirmed clean'
      Record B: 'VERIFIED [S7]: secondary seal confirmed failed'
    Evaluates whether raw convergence_engine detects conflicting assertions or
    collapses via last-write-wins in the resolved_seed_map.
    """
    engine = ConvergenceEngine(required_seeds=["S2", "S7"])
    initial_seed = "2026-11-03T14:00:00Z powershell.exe -enc execution_test unresponsive host on port 104"
    
    # Baseline state with S7 unresolved
    s0 = engine.execute_pass(
        predecessor=None,
        new_data=initial_seed,
        cartridge_key="security",
        custom_required_seeds=["S2", "S7"],
    )
    assert "T5_COMPOUNDING:S7" in [g.coordinate for g in s0.gaps]
    assert s0.status == "SUSPENDED"

    # Multi-record input containing contradictory assertions for S7
    contradictory_evidence = (
        "VERIFIED [S7]: secondary seal confirmed clean\n"
        "VERIFIED [S7]: secondary seal confirmed failed"
    )

    s1 = engine.execute_pass(
        predecessor=s0,
        new_data=contradictory_evidence,
        cartridge_key="security",
        custom_required_seeds=["S2", "S7"],
    )

    # In the bare engine:
    # 1. Resolutions dictionary overwrites Record A with Record B
    # 2. S7 is marked resolved by virtue of having a non-empty key in resolved_map
    # 3. Status advances to BOUNDED because no unclosed required seeds remain
    assert "S7" in s1.resolved_seed_map
    assert s1.resolved_seed_map["S7"] == "secondary seal confirmed failed"
    assert len(s1.gaps) == 0
    assert s1.status == "BOUNDED"
    print("\n[TIER 1 RESULT]: Bare Convergence Engine collapsed contradiction via dictionary overwrite -> BOUNDED")


def test_tier_2_domain_cartridge_contradiction_lock():
    """
    Tier 2: Domain Cartridge Layer.
    Examines whether domain parsers (e.g. CourtForge Legal or WMS Logistics)
    recognize conflicting evidence and isolate it into S4 (Contradictions) under F7/F8.
    """
    # Raw input with direct conflict between maintenance logs and physical telemetry
    contradictory_legal_input = (
        "2026-06-18 Landlord contractor log claims boiler valve repair completed verified clean.\n"
        "2026-06-19 Tenant thermal telemetry shows continuous boiler failure and overheating.\n"
        "Evidentiary contradiction between contractor claims and physical sensor recordings."
    )

    tms = parse_raw_stream(contradictory_legal_input, cartridge_key="courtforge_legal")
    center_space = tms.positions.get("T5_COMPOUNDING")
    assert center_space is not None

    s4_data = center_space.seeds.get("S4", {})
    # In CourtForge legal cartridge, S4 is "Contradictions & Irreconcilable Conflicts"
    assert s4_data.get("state") == "EVIDENTIARY_CONTRADICTION_FLAGGED"
    assert "contradicts telemetry" in s4_data.get("evidence", "")
    print(f"\n[TIER 2 RESULT]: CourtForge Legal Cartridge intercepted contradiction into S4: {s4_data.get('state')}")


def test_tier_3_financial_settlement_contradiction_gate():
    """
    Tier 3: Statutory & Financial Governance Adapter.
    Examines whether higher-layer policy governors detect conflicting assertions
    (e.g., approved beneficiary baseline followed by revocation or SDN sanctions match)
    and halt execution via PolicyContradictionError.
    """
    adapter = FinancialWireAdapter()

    # Step 1: Initial wire setup with unverified routing and missing secondary auth
    wire_instruction = {
        "amount": 500000.0,
        "currency": "USD",
        "authorization_A": "PRESENT",
        "authorization_B": "MISSING",
        "counterparty": "ACME_SUPPLY_CORP",
        "sanctions_check": "MISSING",
        "case_id": "CASE_WIRE_1001",
    }
    s0 = adapter.evaluate_initial_instruction(wire_instruction)
    assert s0.status == "SUSPENDED"

    # Step 2: Feed contradictory resolution (counterparty approved vs SDN match)
    contradictory_evidence = (
        "VERIFIED [S3]: Counterparty ACME_SUPPLY_CORP confirmed on verified vendor allowlist\n"
        "SANCTIONS_STATUS: BLOCKED (MATCH_SDN_LIST_ALERT for beneficiary ACME_SUPPLY_CORP)"
    )

    with pytest.raises(PolicyContradictionError) as exc_info:
        adapter.submit_recovery_evidence(s0, contradictory_evidence)

    assert "CONTRADICTION DETECTED" in str(exc_info.value)
    print(f"\n[TIER 3 RESULT]: Financial Adapter intercepted contradiction -> PolicyContradictionError: {exc_info.value}")


def test_tier_4_kinetic_governor_sensor_divergence_clamping():
    """
    Tier 4: Embodied Kinetic Governor / Physical Plant.
    Examines whether physical sensor contradictions (e.g. Optical motionless vs Encoder rotating,
    or Electrical Current vs Torque Transducer decoupling) trip the governor to FAIL-CLOSED (0.0 Nm).
    """
    # 4A: Multi-modal coupled sensor contradiction
    gov = StemGovernor("CONTRADICTION_JOINT")
    cmd = ActuationCommand(
        joint_id="CONTRADICTION_JOINT",
        target_torque_nm=35.0,
        target_velocity_rad_s=1.5,
        max_duration_ms=50,
        source_planner="VLA_ACTUATOR",
    )

    # Flatline / zero variance sensor injection (contradicting dynamic plant motion)
    contradictory_optical = SensorReading("CAM_01", "OPTICAL", value=0.0, variance=0.0, timestamp_ms=100)
    valid_encoder = SensorReading("ENC_01", "ENCODER", value=1.5, variance=0.05, timestamp_ms=100)

    state, torque, msg = gov.evaluate_cycle(
        command=cmd,
        optical_reading=contradictory_optical,
        encoder_reading=valid_encoder,
        measured_current_amps=15.35,
        measured_torque_sensor_nm=34.8,
        pos_rad=1.5,
        vel_rad_s=1.5,
        acc_rad_s2=0.5,
    )

    assert state == GovernorState.SUSPENDED
    assert torque == 0.0
    assert any("GAP_OPTICAL_FAULT" in g for g in gov.gap_set)

    # 4B: Electrical vs Transducer physical contradiction (Ia * Kt != Tau_sensor)
    torque_gate = KineticTorqueGate(TorqueLimitConfig(motor_id="CONTRADICTION_JOINT"))
    # Commanded 30 Nm, Current indicates ~35 Nm (15.35 A * 2.28 Kt = 35.0 Nm),
    # but torque sensor reports 5.0 Nm (severe physical decoupling or slipping)
    is_safe, permitted_torque, reason = torque_gate.evaluate_actuator_safety(
        commanded_torque_nm=30.0,
        measured_current_amps=15.35,
        measured_torque_sensor_nm=5.0,  # Contradicts 35.0 Nm electrical reading
    )

    assert not is_safe
    assert permitted_torque == 0.0
    assert "TRANSDUCER_CURRENT_DECOUPLING" in reason
    assert torque_gate.is_tripped

    print("\n[TIER 4 RESULT]: Physical Kinetic Gate detected sensor/transducer contradiction -> TRIPPED_FAIL_CLOSED (0.0 Nm)")


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-s"])
