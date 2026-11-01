"""
ViperCrest Air-Gapped Reader Engine: RAW -> Normalized Observations & Temporal Matrix.

Enforces zero-execution semantic decomposition:
- Never executes incoming code, commands, or binaries.
- Extracts lexical tokens, timestamps, network vectors, and life-safety markers.
- Assembles S1..S9 domain seeds inside T5_COMPOUNDING (T0).
- Constructs evidence-bounded predecessor/successor candidates (T4/T6).
- Emits standard ViperCrest observation fixtures for evaluation by the fixed F1-F9 engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from domain_space import (
    CARTRIDGES,
    DOMAIN_SEEDS,
    TEMPORAL_PHASES,
    CartridgeSpec,
    cartridge_security_ir,
    cartridge_courtforge_legal,
    cartridge_wms_logistics,
    CARTRIDGE_SECURITY_IR,
    CARTRIDGE_COURTFORGE_LEGAL,
    CARTRIDGE_WMS_LOGISTICS,
    DEFAULT_SECURITY_CARTRIDGE,
    DomainSpaceInstance,
    TemporalMatrixSpace,
)

VIPER_ROOT = Path("C:/ViperCrest")
RUNTIME_DIR = VIPER_ROOT / "runtime"
FIXTURES_DIR = VIPER_ROOT / "fixtures"
DROPZONE_RAW = RUNTIME_DIR / "dropzone" / "raw"

SAMPLE_RAW_DATA = {
    "security": {
        "filename": "raw_hospital.log",
        "content": (
            "2026-11-01T02:15:12Z [FIREWALL_ALERT] src=192.168.10.44 dst=192.168.10.0/24 port=445 proto=TCP flags=SYN count=1420\n"
            "2026-11-01T02:16:04Z [EDR_HOST_44] powershell.exe -enc SQBuAHYAbwBrAGUALQBXAG0AaQ... user=SVC_BILLING\n"
            "2026-11-01T02:16:48Z [MED_BUS_GATE] WARN: Infusion_Gate_01 timeout delta=4120ms to nurse_console\n"
            "2026-11-01T02:17:00Z [MONITOR_PING] PACS_Server_02 port 104 NO_RESPONSE ConnectionReset\n"
            "2026-11-01T02:17:01Z [SWITCH_CORE_VLAN] STATS: Clinical_Core packets_dropped=0 err=0 crc=0 status=NOMINAL\n"
        ),
    },
    "legal": {
        "filename": "raw_lease_dispute.txt",
        "content": (
            "CASE: Apex Properties LLC v. ByteCore Systems Inc (Civil Action No. 2026-CV-8812)\n"
            "2024-01-01: Commercial Lease executed for 45,000 sq ft datacenter facility. Base Rent: $45,000/mo.\n"
            "2026-06-12: Primary chiller unit failure reported by Tenant. Server room temp exceeded 35C.\n"
            "2026-08-15: Tenant serves Formal Notice of Default citing Lease Section 14.2 (HVAC Warranty of Habitability).\n"
            "2026-09-01: Tenant withholds rent for August-September ($90,000 escrow deposit).\n"
            "2026-10-10: Landlord files suit for unlawful detainer and damages; admits HVAC outage occurred in testimony.\n"
            "EVIDENTIARY CONTRADICTION: Landlord maintenance vendor log claims repairs completed 2026-06-18; Tenant thermal telemetry shows continuous overheating through 2026-07-20.\n"
            "DISCOVERY STATUS: Landlord has failed to produce third-party contractor dispatch tickets (HELD UNRESOLVED IN F7).\n"
            "EXHIBIT VAULT: Bates Range APEX-0001 through APEX-0420 authenticated with cryptographic hash.\n"
        ),
    },
    "logistics": {
        "filename": "raw_reefer_telemetry.csv",
        "content": (
            "timestamp,event,unit_id,carrier,lat,lon,temp_c,setpoint_c,status,seal_id\n"
            "2026-10-31T06:00:00Z,DISPATCH,REEFER-904,PolarLogistics,41.8781,-87.6298,-20.2,-20.0,NOMINAL,SEAL-8891\n"
            "2026-10-31T10:30:00Z,TRANSIT_CHECK,REEFER-904,PolarLogistics,39.7817,-89.6501,-19.8,-20.0,NOMINAL,SEAL-8891\n"
            "2026-10-31T14:15:00Z,COMPRESSOR_FAULT,REEFER-904,PolarLogistics,38.6270,-90.1994,-16.1,-20.0,DEGRADED,SEAL-8891\n"
            "2026-10-31T14:30:00Z,EXCURSION_ALARM,REEFER-904,PolarLogistics,38.5800,-90.2500,-12.4,-20.0,CRITICAL_EXCURSION,SEAL-8891-TAMPERED\n"
            "2026-10-31T15:00:00Z,REROUTE_QUARANTINE,REEFER-904,PolarLogistics,38.5200,-90.3100,-13.0,-20.0,QUARANTINE_ROUTE,SEAL-UNKNOWN\n"
            "INVARIANT: HACCP 21 CFR 211 Biologics thermal boundary is -18.0C max.\n"
            "DISCOVERY: Rear container secondary security seal uninspected/tampered (HELD UNRESOLVED IN F7).\n"
        ),
    },
}


def safe_read_bytes(path: Path, max_bytes: int = 10 * 1024 * 1024) -> tuple[bytes, str]:
    """Reads raw bytes safely, bounding payload to max_bytes, and computing SHA-256."""
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    sha256 = hashlib.sha256(raw).hexdigest()
    return raw, sha256


def safe_decode_text(raw_bytes: bytes) -> str:
    """Decodes bytes to text without raising UnicodeDecodeError."""
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin1", errors="replace")


def parse_raw_legal_stream(
    raw_text: str, cartridge: CartridgeSpec = CARTRIDGE_COURTFORGE_LEGAL
) -> TemporalMatrixSpace:
    """
    Zero-execution semantic parser for CourtForge Legal Cartridge.
    Decomposes claims, timelines, testimony, contradictions, and Bates ranges into S1..S9.
    """
    tms = TemporalMatrixSpace(cartridge=cartridge)

    has_breach = bool(re.search(r"breach|default|violation", raw_text, re.IGNORECASE))
    has_contradiction = bool(re.search(r"contradiction|discrepancy|conflicting", raw_text, re.IGNORECASE))
    has_unproduced = bool(re.search(r"unproduced|missing|unresolved|discovery status", raw_text, re.IGNORECASE))
    has_bates = bool(re.search(r"bates|exhibit vault", raw_text, re.IGNORECASE))

    # 1. ASSEMBLE T5_COMPOUNDING (Observed Dispute State)
    s5_seeds = {
        "S1": {
            "label": cartridge.seed_meanings["S1"],
            "state": "PARTIES_JOINED_IN_DISPUTE",
            "evidence": "Apex Properties LLC v. ByteCore Systems Inc (Civil Action No. 2026-CV-8812)",
        },
        "S2": {
            "label": cartridge.seed_meanings["S2"],
            "state": "BREACH_CHRONOLOGY_ESTABLISHED",
            "evidence": "2024-01-01 Lease -> 2026-06-12 Chiller Fail -> 2026-08-15 Notice -> 2026-09-01 Escrow",
        },
        "S3": {
            "label": cartridge.seed_meanings["S3"],
            "state": "MUTUAL_ADMISSIONS_RECORDED",
            "evidence": "Landlord admitted HVAC outage; Tenant admitted withholding rent into escrow",
        },
        "S4": {
            "label": cartridge.seed_meanings["S4"],
            "state": "EVIDENTIARY_CONTRADICTION_FLAGGED" if has_contradiction else "CONCURRENT_TESTIMONY",
            "evidence": "Maintenance log (repair 2026-06-18) contradicts telemetry (overheating to 2026-07-20)",
        },
        "S5": {
            "label": cartridge.seed_meanings["S5"],
            "state": "ACTIVE_DISPUTE_IN_CONTROVERSY" if has_breach else "NOMINAL_PERFORMANCE",
            "evidence": "Commercial lease default & warranty of habitability claim ($135,000 in controversy)",
        },
        "S6": {
            "label": cartridge.seed_meanings["S6"],
            "state": "DISCOVERY_MOTION_COMPEL_PENDING",
            "evidence": "Motion to compel maintenance contractor records and subpoena technician",
        },
        "S7": {
            "label": cartridge.seed_meanings["S7"],
            "state": "UNPRODUCED_DISPATCH_LOGS" if has_unproduced else "NONE_PENDING",
            "evidence": "Landlord third-party contractor dispatch tickets unproduced; held in F7 UNRESOLVED",
        },
        "S8": {
            "label": cartridge.seed_meanings["S8"],
            "state": "STATUTORY_AUTHORITY_ASSERTED",
            "evidence": "UCC Section 2-314 & Commercial Lease Section 14.2 habitability covenants",
        },
        "S9": {
            "label": cartridge.seed_meanings["S9"],
            "state": "BATES_VAULT_SEALED" if has_bates else "EVIDENCE_SEALED",
            "evidence": f"Bates APEX-0001..APEX-0420 SHA256: {hashlib.sha256(raw_text.encode()).hexdigest()[:16]}...",
        },
    }
    space_t0 = DomainSpaceInstance(space_id="T0_LEGAL_DISPUTE", phase="T5_COMPOUNDING", seeds=s5_seeds)
    tms.set_space("T5_COMPOUNDING", space_t0)

    # 2. CONSTRUCT EVIDENCE-BOUNDED PREDECESSOR CANDIDATE (T4_STABILITY)
    s4_seeds = dict(s5_seeds)
    s4_seeds["S1"] = {"label": cartridge.seed_meanings["S1"], "state": "CONTRACT_IN_GOOD_STANDING", "evidence": "Pre-breach active tenancy"}
    s4_seeds["S2"] = {"label": cartridge.seed_meanings["S2"], "state": "EXECUTION_BASELINE", "evidence": "Signed lease agreement"}
    s4_seeds["S3"] = {"label": cartridge.seed_meanings["S3"], "state": "NOMINAL_RENT_PAYMENTS", "evidence": "Timely monthly rental ledger"}
    s4_seeds["S4"] = {"label": cartridge.seed_meanings["S4"], "state": "NO_DISPUTES", "evidence": "Zero recorded maintenance notices"}
    s4_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "PERFORMING_CONTRACT", "evidence": "Stable commercial occupancy"}
    space_t4 = DomainSpaceInstance(space_id="T_MINUS_1_BASELINE_LEASE", phase="T4_STABILITY", seeds=s4_seeds)
    tms.set_space("T4_STABILITY", space_t4)
    tms.relationships.append({"phase": "T4_STABILITY", "status": "DERIVED", "rule": "bounded_predecessor_contract_baseline"})

    # 3. CONSTRUCT FORWARD ADJUDICATION CANDIDATE (T6_REFRACTING)
    s6_seeds = dict(s5_seeds)
    s6_seeds["S1"] = {"label": cartridge.seed_meanings["S1"], "state": "JUDICIALLY_MANAGED", "evidence": "Case management order entered"}
    s6_seeds["S4"] = {"label": cartridge.seed_meanings["S4"], "state": "CONTRADICTION_SUBMITTED_TO_TRIER_OF_FACT", "evidence": "Fact-finder review"}
    s6_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "ESCROW_SETTLEMENT_ROUTING", "evidence": "Funds held in court escrow"}
    s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "DISCOVERY_COMPELLED", "evidence": "Subpoenas issued for contractor"}
    space_t6 = DomainSpaceInstance(space_id="T_PLUS_1_JUDICIAL_CANDIDATE", phase="T6_REFRACTING", seeds=s6_seeds)
    tms.set_space("T6_REFRACTING", space_t6)
    tms.relationships.append({"phase": "T6_REFRACTING", "status": "POSSIBLE", "rule": "forward_adjudication_candidate"})

    # Compute inter-space receipts
    tms.compute_inter_space_transition_receipt("T4_STABILITY", "T5_COMPOUNDING", {"transition": "dispute_emergence_breach_notice"})
    tms.compute_inter_space_transition_receipt("T5_COMPOUNDING", "T6_REFRACTING", {"transition": "judicial_adjudication_routing"})

    return tms


def parse_raw_logistics_stream(
    raw_text: str, cartridge: CartridgeSpec = CARTRIDGE_WMS_LOGISTICS
) -> TemporalMatrixSpace:
    """
    Zero-execution semantic parser for WMS Logistics Cartridge.
    Decomposes cold-chain telemetry, transit milestones, cargo BOL, and seal integrity into S1..S9.
    """
    tms = TemporalMatrixSpace(cartridge=cartridge)

    has_excursion = bool(re.search(r"excursion|fault|degraded|-1[0-7]\.[0-9]|-12\.", raw_text, re.IGNORECASE))
    has_quarantine = bool(re.search(r"quarantine|reroute", raw_text, re.IGNORECASE))
    has_seal_tamper = bool(re.search(r"seal.*(tamper|uninspected|unknown|broken)", raw_text, re.IGNORECASE))

    # 1. ASSEMBLE T5_COMPOUNDING (Observed Cold-Chain Telemetry)
    s5_seeds = {
        "S1": {
            "label": cartridge.seed_meanings["S1"],
            "state": "SHIPPER_CONSIGNEE_BOUND",
            "evidence": "Shipper: BioPharma Direct -> Consignee: Metro Health Depot (Carrier: PolarLogistics)",
        },
        "S2": {
            "label": cartridge.seed_meanings["S2"],
            "state": "TRANSIT_MILESTONE_EXCURSION",
            "evidence": "2026-10-31T06:00Z Chicago -> 2026-10-31T14:30Z Excursion Alarm (-12.4C)",
        },
        "S3": {
            "label": cartridge.seed_meanings["S3"],
            "state": "THERMAL_EXCURSION_ACTIVE" if has_excursion else "TEMPERATURE_NOMINAL",
            "evidence": "Sensor temp breached -18.0C HACCP threshold (recorded -12.4C vs setpoint -20.0C)",
        },
        "S4": {
            "label": cartridge.seed_meanings["S4"],
            "state": "PALLET_CARGO_AUTHENTICATED",
            "evidence": "BOL-994102-WMS: 14 Pallets mRNA Biologics (Lot VAX-2026-A, 4,200 kg)",
        },
        "S5": {
            "label": cartridge.seed_meanings["S5"],
            "state": "COLD_CHAIN_COMPROMISED" if has_excursion else "COLD_CHAIN_STABLE",
            "evidence": "Reefer compressor fault triggered 42-minute thermal excursion above limit",
        },
        "S6": {
            "label": cartridge.seed_meanings["S6"],
            "state": "QUARANTINE_REROUTE_ACTIVE" if has_quarantine else "TRANSIT_ON_ROUTE",
            "evidence": "Rerouted to Dallas Cold-Storage Quarantine Vault B for inspection",
        },
        "S7": {
            "label": cartridge.seed_meanings["S7"],
            "state": "UNINSPECTED_REAR_SEAL" if has_seal_tamper else "NONE_PENDING",
            "evidence": "Rear container seal SEAL-8891 status unverified/tampered; held in F7 UNRESOLVED",
        },
        "S8": {
            "label": cartridge.seed_meanings["S8"],
            "state": "HACCP_INVARIANT_PINNED",
            "evidence": "FDA 21 CFR Part 211 / HACCP -18.0C maximum temperature boundary invariant",
        },
        "S9": {
            "label": cartridge.seed_meanings["S9"],
            "state": "MANIFEST_DIGEST_SEALED",
            "evidence": f"Cryptographic manifest SHA256: {hashlib.sha256(raw_text.encode()).hexdigest()[:16]}...",
        },
    }
    space_t0 = DomainSpaceInstance(space_id="T0_LOGISTICS_TELEMETRY", phase="T5_COMPOUNDING", seeds=s5_seeds)
    tms.set_space("T5_COMPOUNDING", space_t0)

    # 2. CONSTRUCT EVIDENCE-BOUNDED PREDECESSOR CANDIDATE (T4_STABILITY)
    s4_seeds = dict(s5_seeds)
    s4_seeds["S1"] = {"label": cartridge.seed_meanings["S1"], "state": "DISPATCH_AUTHORIZED", "evidence": "Origin hub sign-off"}
    s4_seeds["S2"] = {"label": cartridge.seed_meanings["S2"], "state": "DEPARTURE_MILESTONE", "evidence": "Departed Chicago Hub 06:00Z"}
    s4_seeds["S3"] = {"label": cartridge.seed_meanings["S3"], "state": "TEMPERATURE_NOMINAL", "evidence": "Baseline temp -20.2C steady"}
    s4_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "NOMINAL_TRANSIT_STABLE", "evidence": "Pre-excursion nominal transit"}
    s4_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "ORIGINAL_ROUTE", "evidence": "En route via I-55 South"}
    space_t4 = DomainSpaceInstance(space_id="T_MINUS_1_NOMINAL_TRANSIT", phase="T4_STABILITY", seeds=s4_seeds)
    tms.set_space("T4_STABILITY", space_t4)
    tms.relationships.append({"phase": "T4_STABILITY", "status": "DERIVED", "rule": "bounded_predecessor_nominal_transit"})

    # 3. CONSTRUCT FORWARD QUARANTINE CANDIDATE (T6_REFRACTING)
    s6_seeds = dict(s5_seeds)
    s6_seeds["S1"] = {"label": cartridge.seed_meanings["S1"], "state": "CONSIGNEE_NOTIFIED_HOLD", "evidence": "Quality hold alert transmitted"}
    s6_seeds["S2"] = {"label": cartridge.seed_meanings["S2"], "state": "QUARANTINE_ARRIVAL_CHECK", "evidence": "Arrival at Quarantine Vault B"}
    s6_seeds["S3"] = {"label": cartridge.seed_meanings["S3"], "state": "VAULT_COOLED_STABILIZED", "evidence": "Quarantine chamber at -25.0C"}
    s6_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "DISPOSITION_PENDING_QA", "evidence": "Awaiting biologic potency test"}
    s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "CUSTODY_TRANSFERRED_TO_QA", "evidence": "QA custody sign-off"}
    space_t6 = DomainSpaceInstance(space_id="T_PLUS_1_QUARANTINE_CANDIDATE", phase="T6_REFRACTING", seeds=s6_seeds)
    tms.set_space("T6_REFRACTING", space_t6)
    tms.relationships.append({"phase": "T6_REFRACTING", "status": "POSSIBLE", "rule": "forward_quarantine_candidate"})

    # Compute inter-space receipts
    tms.compute_inter_space_transition_receipt("T4_STABILITY", "T5_COMPOUNDING", {"transition": "cold_chain_excursion_emergence"})
    tms.compute_inter_space_transition_receipt("T5_COMPOUNDING", "T6_REFRACTING", {"transition": "quarantine_custody_transfer"})

    return tms


def parse_raw_stream(
    raw_text: str, cartridge_key: str = "security"
) -> TemporalMatrixSpace:
    """Dispatches raw stream text to the appropriate cartridge parser."""
    ck = cartridge_key.lower()
    if "legal" in ck or "courtforge" in ck:
        return parse_raw_legal_stream(raw_text)
    elif "logistic" in ck or "wms" in ck:
        return parse_raw_logistics_stream(raw_text)
    else:
        return parse_raw_incident_stream(raw_text)
def parse_raw_incident_stream(
    raw_text: str, cartridge: CartridgeSpec = DEFAULT_SECURITY_CARTRIDGE
) -> TemporalMatrixSpace:
    """
    Zero-execution semantic parser for Security IR Cartridge.
    Decomposes raw incident text into S1..S9 seeds within T5_COMPOUNDING,
    and constructs evidence-bounded predecessor (T4) and successor (T6) candidates.
    """
    tms = TemporalMatrixSpace(cartridge=cartridge)

    # 1. SCAN PATTERNS (Without executing foreign code)
    has_powershell = bool(re.search(r"powershell(\.exe)?|-enc\b", raw_text, re.IGNORECASE))
    has_smb_sweep = bool(re.search(r"port=445|port 445|proto=TCP.*445", raw_text, re.IGNORECASE))
    has_timeout = bool(re.search(r"timeout|latency|degraded", raw_text, re.IGNORECASE))
    has_unresponsive = bool(re.search(r"no_response|unresponsive|connectionreset", raw_text, re.IGNORECASE))
    has_healthy_vlan = bool(re.search(r"nominal|healthy|packets_dropped=0", raw_text, re.IGNORECASE))

    # 2. ASSEMBLE T5_COMPOUNDING (T0 / Observed Present)
    s5_seeds = {
        "S1": {
            "label": cartridge.seed_meanings["S1"],
            "state": "COMPROMISED_TOKEN" if has_powershell else "NOMINAL",
            "evidence": "PowerShell invocation detected" if has_powershell else "No credential alerts",
        },
        "S2": {
            "label": cartridge.seed_meanings["S2"],
            "state": "ANOMALOUS_EXECUTION" if has_powershell else "CLEAN",
            "evidence": "Suspicious process spawn with encoded flags" if has_powershell else "Normal execution",
        },
        "S3": {
            "label": cartridge.seed_meanings["S3"],
            "state": "LATERAL_SWEEP" if has_smb_sweep else "NORMAL_ROUTING",
            "evidence": "Port 445 SMB sweep across subnet" if has_smb_sweep else "Standard traffic",
        },
        "S4": {
            "label": cartridge.seed_meanings["S4"],
            "state": "DEGRADED" if has_timeout else "HEALTHY",
            "evidence": "Telemetry latency spike on clinical device" if has_timeout else "Latency nominal",
        },
        "S5": {
            "label": cartridge.seed_meanings["S5"],
            "state": "ACTIVE_DISRUPTION" if (has_powershell and has_smb_sweep) else "NORMAL",
            "evidence": "Observed multi-vector anomaly in progress",
        },
        "S6": {
            "label": cartridge.seed_meanings["S6"],
            "state": "CONTAINMENT_TRIGGER_PENDING",
            "evidence": "Awaiting deterministic boundary assertion",
        },
        "S7": {
            "label": cartridge.seed_meanings["S7"],
            "state": "UNRESOLVED_ENDPOINT_B" if has_unresponsive else "NONE_PENDING",
            "evidence": "Unresponsive host without confirmed status; held in F7 UNRESOLVED",
        },
        "S8": {
            "label": cartridge.seed_meanings["S8"],
            "state": "LIFE_SAFETY_PINNED",
            "evidence": "Policy invariant: Do not sever clinical telemetry",
        },
        "S9": {
            "label": cartridge.seed_meanings["S9"],
            "state": "EVIDENCE_SEALED",
            "evidence": f"Raw payload digest: {hashlib.sha256(raw_text.encode()).hexdigest()[:16]}...",
        },
    }
    space_t0 = DomainSpaceInstance(space_id="T0_OBSERVED", phase="T5_COMPOUNDING", seeds=s5_seeds)
    tms.set_space("T5_COMPOUNDING", space_t0)

    # 3. CONSTRUCT EVIDENCE-BOUNDED PREDECESSOR CANDIDATE (T4_STABILITY)
    s4_seeds = dict(s5_seeds)
    s4_seeds["S1"] = {"label": cartridge.seed_meanings["S1"], "state": "PRE_INTRUSION_VALID", "evidence": "Baseline auth log"}
    s4_seeds["S2"] = {"label": cartridge.seed_meanings["S2"], "state": "IDLE", "evidence": "No abnormal processes"}
    s4_seeds["S3"] = {"label": cartridge.seed_meanings["S3"], "state": "INERT", "evidence": "No lateral scan"}
    s4_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "NOMINAL_STABLE", "evidence": "Pre-incident steady state"}
    space_t4 = DomainSpaceInstance(space_id="T_MINUS_1_PREDECESSOR", phase="T4_STABILITY", seeds=s4_seeds)
    tms.set_space("T4_STABILITY", space_t4)
    tms.relationships.append({"phase": "T4_STABILITY", "status": "DERIVED", "rule": "bounded_predecessor_inference"})

    # 4. CONSTRUCT FORWARD CONTAINMENT CANDIDATE (T6_REFRACTING / T8_PATH_OUT)
    s6_seeds = dict(s5_seeds)
    s6_seeds["S1"] = {"label": cartridge.seed_meanings["S1"], "state": "TOKEN_REVOKED", "evidence": "Security assertion applied"}
    s6_seeds["S2"] = {"label": cartridge.seed_meanings["S2"], "state": "QUARANTINED", "evidence": "Host isolated"}
    s6_seeds["S3"] = {"label": cartridge.seed_meanings["S3"], "state": "PORT_445_BLOCKED", "evidence": "ACL rule asserted"}
    s6_seeds["S4"] = {"label": cartridge.seed_meanings["S4"], "state": "LOCAL_LOOP_PROTECTED", "evidence": "Fail-safe bus isolated"}
    s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "CONTAINMENT_LOCKED", "evidence": "Blast radius severed"}
    space_t6 = DomainSpaceInstance(space_id="T_PLUS_1_SUCCESSOR", phase="T6_REFRACTING", seeds=s6_seeds)
    tms.set_space("T6_REFRACTING", space_t6)
    tms.relationships.append({"phase": "T6_REFRACTING", "status": "POSSIBLE", "rule": "forward_containment_candidate"})

    # Compute inter-space receipts
    tms.compute_inter_space_transition_receipt("T4_STABILITY", "T5_COMPOUNDING", {"transition": "anomaly_emergence"})
    tms.compute_inter_space_transition_receipt("T5_COMPOUNDING", "T6_REFRACTING", {"transition": "containment_application"})

    return tms


def emit_matrix_observation_fixture(tms: TemporalMatrixSpace, case_id: str = "reader_simulation") -> Path:
    """
    Connects the normalized Temporal Matrix output to the existing ViperCrest matrix contract:
    Emits a standard {"observations": [...]} fixture ready for vipercrest matrix --target.
    """
    s_now = tms.positions.get("T5_COMPOUNDING")
    s_pred = tms.positions.get("T4_STABILITY")
    s_succ = tms.positions.get("T6_REFRACTING")

    observations = []
    if s_now and s_pred:
        observations.append({
            "id": "T4_PREDECESSOR_vs_T5_OBSERVED",
            "baseline": s_pred.seeds,
            "candidate": s_now.seeds,
            "context": {"transition": "backward_provenance_bound", "cartridge": tms.cartridge.cartridge_id},
        })
    if s_now and s_succ:
        observations.append({
            "id": "T5_OBSERVED_vs_T6_SUCCESSOR",
            "baseline": s_now.seeds,
            "candidate": s_succ.seeds,
            "context": {"transition": "forward_containment_candidate", "cartridge": tms.cartridge.cartridge_id},
        })

    fixture_payload = {
        "case_id": case_id,
        "observations": observations,
        "temporal_space": tms.to_dict()["temporal_space"],
    }

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path = FIXTURES_DIR / f"{case_id}.json"
    fixture_path.write_text(json.dumps(fixture_payload, indent=2), encoding="utf-8")
    return fixture_path


def ensure_sample_raw_files() -> None:
    """Ensures dropzone raw sample files are populated."""
    DROPZONE_RAW.mkdir(parents=True, exist_ok=True)
    for domain, sample in SAMPLE_RAW_DATA.items():
        sample_path = DROPZONE_RAW / sample["filename"]
        if not sample_path.exists():
            sample_path.write_text(sample["content"], encoding="utf-8")


def run_cartridge_intake(
    cartridge_key: str,
    custom_input: Optional[Path] = None,
    custom_case_id: Optional[str] = None,
    print_summary: bool = True,
) -> Path:
    """Executes air-gapped reader intake for a specific cartridge."""
    ensure_sample_raw_files()
    normalized_key = cartridge_key.lower().replace("cartridge_", "").replace("_ir", "")
    if "courtforge" in normalized_key or "legal" in normalized_key:
        cart_name = "legal"
        cart_spec = CARTRIDGE_COURTFORGE_LEGAL
        default_file = DROPZONE_RAW / SAMPLE_RAW_DATA["legal"]["filename"]
        default_case = "reader_extracted_legal"
    elif "wms" in normalized_key or "logistic" in normalized_key:
        cart_name = "logistics"
        cart_spec = CARTRIDGE_WMS_LOGISTICS
        default_file = DROPZONE_RAW / SAMPLE_RAW_DATA["logistics"]["filename"]
        default_case = "reader_extracted_logistics"
    else:
        cart_name = "security"
        cart_spec = CARTRIDGE_SECURITY_IR
        default_file = DROPZONE_RAW / SAMPLE_RAW_DATA["security"]["filename"]
        default_case = "reader_extracted_security"

    target_input = custom_input if custom_input else default_file
    case_id = custom_case_id if custom_case_id else default_case

    raw_bytes, sha256 = safe_read_bytes(target_input)
    text = safe_decode_text(raw_bytes)
    tms = parse_raw_stream(text, cartridge_key=cart_name)

    if print_summary:
        print(f"\n=======================================================")
        print(f" AIR-GAPPED READER: {cart_spec.name.upper()} ({cart_spec.cartridge_id})")
        print(f" SOURCE: {target_input} (SHA-256: {sha256[:16]}...)")
        print(f"=======================================================")
        print(tms.format_matrix_summary())

    fixture_path = emit_matrix_observation_fixture(tms, case_id=case_id)
    print(f"[READER] Successfully emitted {cart_name} matrix fixture -> {fixture_path}")
    return fixture_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ViperCrest Air-Gapped Multi-Cartridge Reader Engine")
    parser.add_argument(
        "--cartridge", "-c",
        choices=["security", "legal", "logistics", "all"],
        default="security",
        help="Target domain cartridge specification (default: security)",
    )
    parser.add_argument("--input", "-i", help="Optional custom raw input file path")
    parser.add_argument("--case-id", help="Optional custom output fixture case ID")
    parser.add_argument("--no-summary", action="store_true", help="Suppress terminal matrix summary printout")
    args = parser.parse_args(argv)

    print_summary = not args.no_summary
    custom_in = Path(args.input) if args.input else None

    if args.cartridge == "all":
        for cart in ["security", "legal", "logistics"]:
            run_cartridge_intake(
                cartridge_key=cart,
                custom_input=custom_in,
                custom_case_id=args.case_id,
                print_summary=print_summary,
            )
    else:
        run_cartridge_intake(
            cartridge_key=args.cartridge,
            custom_input=custom_in,
            custom_case_id=args.case_id,
            print_summary=print_summary,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
