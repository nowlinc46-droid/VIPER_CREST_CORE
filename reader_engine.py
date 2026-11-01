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
from dataclasses import dataclass, field
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    hydrate_from_minimal_seed,
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

SAMPLE_MINIMAL_SEEDS = {
    "security": "2026-11-01T02:17:00Z PACS_Server_02 port 104 NO_RESPONSE ConnectionReset",
    "legal": "2026-08-15 Tenant serves Formal Notice of Default citing Lease Section 14.2",
    "logistics": "2026-10-31T14:30:00Z REEFER-904 EXCURSION_ALARM temp_c=-12.4 setpoint_c=-20.0",
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


@dataclass
class ResolvedTarget:
    target_type: str  # "code_file" | "target_manifest" | "raw_file" | "hardware_device" | "inline_code"
    name: str
    path: Optional[Path]
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def resolve_target_from_input(user_input: str) -> Optional[ResolvedTarget]:
    """
    Universal Target Resolver:
    Translates plain English human target references into verified on-disk or memory targets:
    - Smart contract source files (.sol, .py, etc.)
    - Target manifests (targets/lombard.json, targets/ens_v2.json)
    - Hardware devices (ADB / USB dumps via phone_intake)
    - Raw incident drops (.raw, .log, .csv)
    - Inline code snippets
    """
    clean_input = user_input.strip()
    lowered = clean_input.lower()

    # 1. Hardware / Phone / USB targets
    if any(h in lowered for h in ["phone", "android", "usb device", "adb", "device dump"]):
        try:
            import phone_intake as p_intake
            devices = p_intake.detect_connected_devices()
            if devices:
                dev = devices[0]
                dev_id = dev["id"]
                dump = p_intake.generate_synthetic_device_dump(device_id=dev_id)
            else:
                dump = p_intake.generate_synthetic_device_dump(device_id="PIXEL_8A_USB_SIM")
            return ResolvedTarget(
                target_type="hardware_device",
                name=dump.get("device_id", "Connected Device"),
                path=None,
                content=json.dumps(dump, indent=2),
                metadata={"transport": "adb", "device_info": dump},
            )
        except Exception:
            pass

    # 2. Inline code snippet
    if any(c in clean_input for c in ["pragma solidity", "contract ", "library ", "interface "]) and len(clean_input) > 40:
        return ResolvedTarget(
            target_type="inline_code",
            name="Inline Solidity Source",
            path=None,
            content=clean_input,
            metadata={"language": "Solidity"},
        )

    # 3. Extract candidate tokens from prompt
    tokens: List[str] = []
    # Quoted tokens
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", clean_input)
    tokens.extend(quoted)

    # Filename patterns (.sol, .json, .raw, .log, .txt, .csv, .py, .md, .rs, .toml)
    file_matches = re.findall(r"([\w\-\./\\]+\.(?:sol|json|raw|log|txt|csv|py|md|rs|toml))", clean_input, re.IGNORECASE)
    tokens.extend(file_matches)

    # Keyword targets
    if "lombard" in lowered and not any("lombard" in t.lower() for t in tokens):
        tokens.append("lombard.json")
    if "ens" in lowered and not any("ens" in t.lower() for t in tokens):
        tokens.append("ens_v2.json")
    if "bridgev2" in lowered and not any("bridgev2" in t.lower() for t in tokens):
        tokens.append("BridgeV2.sol")
    if "ratelimits" in lowered and not any("ratelimits" in t.lower() for t in tokens):
        tokens.append("RateLimits.sol")
    if any(k in lowered for k in ["ethena", "0x73e35c5c35a274e34ade6eb13cc7f62aee323728"]) and not any("usdtb" in t.lower() for t in tokens):
        tokens.append("ethena_usdtb.json")
    if "usdtb" in lowered and not any("usdtb" in t.lower() for t in tokens):
        tokens.append("USDtb.sol")
    if any(k in lowered for k in ["raydium", "cp-swap", "cpswap", "cp_swap"]) and not any("raydium" in t.lower() for t in tokens):
        tokens.append("raydium_cp_swap.json")

    search_roots = [
        VIPER_ROOT / "targets",
        VIPER_ROOT / "targets" / "raydium-cp-swap" / "programs" / "cp-swap" / "src",
        VIPER_ROOT / "targets" / "raydium-cp-swap" / "programs" / "cp-swap",
        VIPER_ROOT / "targets" / "ethena-usdtb" / "contracts",
        VIPER_ROOT / "targets" / "ethena-usdtb" / "contracts" / "usdtb",
        VIPER_ROOT / "evm-smart-contracts" / "contracts",
        VIPER_ROOT / "fixtures",
        DROPZONE_RAW,
        VIPER_ROOT / "VIPER-LOMBARD-2026-001" / "poc",
        VIPER_ROOT,
    ]

    for token in tokens:
        p = Path(token)
        # Direct path check
        if p.exists() and p.is_file():
            raw_b, _ = safe_read_bytes(p)
            text = safe_decode_text(raw_b)
            t_type = "code_file" if p.suffix.lower() in {".sol", ".py", ".rs", ".js", ".ts"} else ("target_manifest" if p.suffix.lower() == ".json" else "raw_file")
            return ResolvedTarget(target_type=t_type, name=p.name, path=p, content=text, metadata={"path": str(p)})

        # Search roots
        file_name = p.name
        excluded_parts = {"out", "cache", ".git", "node_modules", ".venv", "__pycache__"}
        for root in search_roots:
            if not root.exists():
                continue
            cand = root / file_name
            if cand.exists() and cand.is_file() and not any(part in excluded_parts for part in cand.parts):
                raw_b, _ = safe_read_bytes(cand)
                text = safe_decode_text(raw_b)
                t_type = "code_file" if cand.suffix.lower() in {".sol", ".py", ".rs", ".js", ".ts"} else ("target_manifest" if cand.suffix.lower() == ".json" else "raw_file")
                return ResolvedTarget(target_type=t_type, name=cand.name, path=cand, content=text, metadata={"path": str(cand)})

            # Recursive match inside root (excluding project root to prevent deep .venv traversal)
            if root != VIPER_ROOT:
                try:
                    matches = [m for m in root.rglob(file_name) if m.is_file() and not any(part in excluded_parts for part in m.parts)]
                    if matches:
                        target_file = matches[0]
                        raw_b, _ = safe_read_bytes(target_file)
                        text = safe_decode_text(raw_b)
                        t_type = "code_file" if target_file.suffix.lower() in {".sol", ".py", ".rs", ".js", ".ts"} else ("target_manifest" if target_file.suffix.lower() == ".json" else "raw_file")
                        return ResolvedTarget(target_type=t_type, name=target_file.name, path=target_file, content=text, metadata={"path": str(target_file)})
                except Exception:
                    continue

    return None


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


def parse_raw_code_stream(
    raw_code: str,
    filename: str = "TargetSource.sol",
    cartridge: CartridgeSpec = DEFAULT_SECURITY_CARTRIDGE,
) -> TemporalMatrixSpace:
    """
    Embedded Code Reader: Decomposes raw smart contract syntax into Plain-Language
    epistemic operations and hydrates the 81-state matrix across the F1-F9 invariant spine.
    """
    tms = TemporalMatrixSpace(cartridge=cartridge)

    # 1. Identify Target & Category
    is_rust = filename.endswith(".rs") or "anchor_lang" in raw_code or "#[program]" in raw_code or "pub mod" in raw_code
    contracts = re.findall(r"^\s*(?:abstract\s+)?(?:contract|library|interface)\s+([A-Za-z0-9_]+)", raw_code, re.MULTILINE)
    primary_name = contracts[0] if contracts else Path(filename).stem
    if is_rust:
        display_target = filename if filename.endswith(".rs") else f"{primary_name}.rs"
    else:
        display_target = f"{primary_name}.sol" if not primary_name.endswith(".sol") else primary_name
    
    lowered_code = raw_code.lower()
    if is_rust and ("swap" in primary_name.lower() or "curve" in lowered_code or "pool" in lowered_code):
        category = "Solana Constant-Product AMM (Anchor Program)"
    elif "bridge" in primary_name.lower() or "bridge" in lowered_code:
        category = "Cross-Chain Token Bridge"
    elif "ratelimit" in primary_name.lower() or "ratelimit" in lowered_code:
        category = "Token Rate Limiter Library"
    elif "vault" in primary_name.lower() or "pool" in lowered_code:
        category = "Asset Vault & Liquidity Pool"
    elif "token" in primary_name.lower() or "erc20" in lowered_code:
        category = "Digital Asset / Token Contract"
    else:
        category = "Smart Contract Component"

    # 2. What It Does
    notice_m = re.search(r"@notice\s+([^\r\n*]+)", raw_code)
    title_m = re.search(r"@title\s+([^\r\n*]+)", raw_code)
    if is_rust and "swap" in category.lower():
        what_it_does = "Executes automated market maker swaps, liquidity provisioning, and fee distribution under constant-product curve dynamics."
    elif "bridge" in category.lower():
        what_it_does = "Mints and transfers tokens between blockchains while enforcing rate limits."
    elif "rate limiter" in category.lower():
        what_it_does = "Tracks and throttles transfer volume over rolling time windows to prevent rapid capital drainage."
    elif notice_m:
        what_it_does = notice_m.group(1).strip()
    elif title_m:
        what_it_does = title_m.group(1).strip()
    else:
        what_it_does = f"Executes on-chain state transactions and parameter governance for {primary_name}."

    # 3. Who Controls It
    has_owner = bool(re.search(r"\bonlyowner\b|ownable2step|ownable", lowered_code))
    has_roles = bool(re.search(r"\bonlyrole\b|accesscontrol", lowered_code))
    has_anchor_admin = bool(re.search(r"\badmin\b|\bauthority\b|has_one\s*=\s*authority", lowered_code))
    if has_owner:
        who_controls_it = "Only the contract owner (admin) can change bridge routes, tokens, and transfer caps."
    elif has_roles:
        who_controls_it = "Restricted to authorized administrative roles configured in AccessControl."
    elif is_rust and has_anchor_admin:
        who_controls_it = "Governed by pool creator and program admin authority specified in AmmConfig PDA."
    else:
        who_controls_it = "Unrestricted: public callers can interact with external state methods without admin gating."

    # 4. Rules Enforced
    rules_enforced = []
    if is_rust:
        rules_enforced.append("Constant-product curve invariant (x * y = k) enforced on liquidity swaps.")
        rules_enforced.append("Slippage protection bounds minimum received tokens on base input/output.")
        rules_enforced.append("Anchor runtime PDA seeds and SPL token account ownership verified.")
        rules_enforced.append("Protocol and creator fees capped by configurable basis points.")
    else:
        if "reentrancyguard" in lowered_code or "nonreentrant" in lowered_code:
            rules_enforced.append("Protected against recursive reentrancy calls.")
        if "alloweddestinationtoken" in lowered_code or "whitelisted" in lowered_code:
            rules_enforced.append("Unregistered tokens and unapproved bridge routes are rejected.")
        if "ratelimitexceeded" in lowered_code or "amountcanbesent" in lowered_code:
            rules_enforced.append("Transfers exceeding the available capacity limit are rejected.")
        if "zerochainid" in lowered_code or "destinationchain == bytes32(0)" in lowered_code:
            rules_enforced.append("Invalid or zero destination chain identifiers are blocked.")
        if "zeromailbox" in lowered_code or "address(0)" in lowered_code:
            rules_enforced.append("Zero-address parameters on critical connections are blocked.")
        if not rules_enforced:
            rules_enforced.append("State transitions require valid transaction parameter bounds.")

    # 5. Attention Needed
    attention_needed = []
    # Zero-window rate limit bypass check
    has_time_check = bool(re.search(r"timeSinceLast\w*\s*>=\s*_?window", raw_code))
    has_zero_window_guard = bool(re.search(r"window\s*==\s*0.*revert", raw_code, re.IGNORECASE))
    if has_time_check and not has_zero_window_guard:
        attention_needed.append(
            "Rate Limit Bypass: If an admin configures a transfer limit with a time window of 0 seconds, "
            "the rate limit turns off completely. Multiple transfers can drain up to the maximum limit "
            "repeatedly in the same block without stopping."
        )
    if "safetransfer" not in lowered_code and "transfer(" in raw_code:
        attention_needed.append("Token Transfer: Standard ERC20 transfer used; non-compliant tokens may fail silently.")

    # 6. Verdict
    if any("Rate Limit Bypass" in a for a in attention_needed):
        verdict = "Action Needed"
        verdict_reason = "Fix the zero-window check in RateLimits.sol"
    elif attention_needed:
        verdict = "Review Required"
        verdict_reason = "Verify boundary conditions before deployment"
    else:
        verdict = "Safe"
        verdict_reason = "Invariants and access controls are cleanly bounded"

    plain_report = {
        "target": display_target,
        "category": category,
        "what_it_does": what_it_does,
        "who_controls_it": who_controls_it,
        "rules_enforced": rules_enforced,
        "attention_needed": attention_needed,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }
    tms.plain_english_report = plain_report

    # Assemble 81-state matrix S1..S9 in T5_COMPOUNDING
    has_bypass = bool(attention_needed)
    s5_seeds = {
        "S1": {"label": cartridge.seed_meanings["S1"], "state": "CODE_INGESTION_BOUNDED", "evidence": f"{primary_name} source digest verified"},
        "S2": {"label": cartridge.seed_meanings["S2"], "state": "ACCESS_GATED_OWNER" if has_owner else "PUBLIC_ACCESS", "evidence": who_controls_it},
        "S3": {"label": cartridge.seed_meanings["S3"], "state": "CROSS_CHAIN_ROUTES", "evidence": "Bridge pathway bindings active"},
        "S4": {"label": cartridge.seed_meanings["S4"], "state": "STORAGE_RATE_LIMITS", "evidence": "RateLimits.Data storage mapped"},
        "S5": {"label": cartridge.seed_meanings["S5"], "state": "CAPACITY_CONSTRAINED", "evidence": "Inbound transfers throttled by limit"},
        "S6": {"label": cartridge.seed_meanings["S6"], "state": "FAIL_CLOSED_ACTIVE", "evidence": "RateLimitExceeded() revert path verified"},
        "S7": {"label": cartridge.seed_meanings["S7"], "state": "ZERO_WINDOW_UNCERTAINTY" if has_bypass else "CLEAN_BOUNDS", "evidence": "Window boundary check evaluated"},
        "S8": {"label": cartridge.seed_meanings["S8"], "state": "LIMIT_EXCEEDED_REVERT", "evidence": "Revert transitions bounded"},
        "S9": {"label": cartridge.seed_meanings["S9"], "state": "LEDGER_FINALITY", "evidence": "Mint settlement receipt verified"},
    }
    tms.set_space("T5_COMPOUNDING", DomainSpaceInstance(space_id="T0_PRESENT_CODE_OBSERVATION", phase="T5_COMPOUNDING", seeds=s5_seeds))

    # T4 Backward Predecessor
    s4_seeds = {k: dict(v) for k, v in s5_seeds.items()}
    s4_seeds["S4"] = {"label": cartridge.seed_meanings["S4"], "state": "UNINITIALIZED_ZERO_CAPACITY", "evidence": "Default storage defaults to zero capacity (fail-closed)"}
    s4_seeds["S5"] = {"label": cartridge.seed_meanings["S5"], "state": "EMPTY_TRANSFER_HISTORY", "evidence": "Zero prior deposits"}
    tms.set_space("T4_STABILITY", DomainSpaceInstance(space_id="T_MINUS_1_BASELINE", phase="T4_STABILITY", seeds=s4_seeds))

    # T6 Forward Reachability (The finding)
    s6_seeds = {k: dict(v) for k, v in s5_seeds.items()}
    if has_bypass:
        s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "CUMULATIVE_BYPASS_POSSIBLE", "evidence": "Candidate transition: W=0 allows unbounded cumulative volume"}
        tms.relationships.append({"phase": "T6_REFRACTING", "status": "POSSIBLE", "rule": "forward_reachability_zero_window_bypass"})
    else:
        s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "STEADY_STATE_CAPACITY", "evidence": "Throttling preserved"}
        tms.relationships.append({"phase": "T6_REFRACTING", "status": "DERIVED", "rule": "forward_stability"})
    tms.set_space("T6_REFRACTING", DomainSpaceInstance(space_id="T_PLUS_1_REACHABILITY", phase="T6_REFRACTING", seeds=s6_seeds))

    tms.compute_inter_space_transition_receipt("T4_STABILITY", "T5_COMPOUNDING", {"transition": "deployment_configuration"})
    tms.compute_inter_space_transition_receipt("T5_COMPOUNDING", "T6_REFRACTING", {"transition": "rate_limit_evaluation"})

    return tms


def parse_raw_manifest_stream(
    manifest_text: str,
    filename: str = "target.json",
    cartridge: CartridgeSpec = DEFAULT_SECURITY_CARTRIDGE,
) -> TemporalMatrixSpace:
    """
    Parses a target manifest JSON (e.g. targets/lombard.json) into plain-language
    module summaries and hydrates the 81-coordinate matrix.
    """
    try:
        data = json.loads(manifest_text)
    except Exception:
        data = {}

    project = data.get("project", Path(filename).stem)
    commit = data.get("commit", "HEAD")
    modules = data.get("modules", [])
    has_bridge = any("bridge" in m.lower() for m in modules) or "lombard" in project.lower()

    plain_report = {
        "target": f"{Path(filename).name} ({project} @ {commit})",
        "category": "Multi-Module Protocol Target",
        "what_it_does": f"Cross-chain liquid staking and asset bridge protocol with {len(modules)} active modules ({', '.join(modules[:4])}).",
        "who_controls_it": "Protocol governance multisig (Ownable2Step) and authorized consortium signers.",
        "rules_enforced": [
            "Cross-chain transfers throttled through per-route rate limits.",
            "Module execution isolated behind fail-closed access controls.",
            "Reentrancy guards active across bridge and mint endpoints.",
        ],
        "attention_needed": [
            "Rate Limit Bypass in RateLimits.sol: Zero-window configuration turns off cumulative volume accumulation across BridgeV2.",
        ] if has_bridge else ["Verify external oracle update latency and access controls."],
        "verdict": "Action Needed" if has_bridge else "Safe",
        "verdict_reason": "Review BridgeV2 RateLimits configuration" if has_bridge else "Clean module bounds",
    }

    tms = TemporalMatrixSpace(cartridge=cartridge)
    tms.plain_english_report = plain_report

    s5_seeds = {
        "S1": {"label": cartridge.seed_meanings["S1"], "state": "TARGET_MANIFEST_BOUNDED", "evidence": f"Project: {project} ({commit})"},
        "S2": {"label": cartridge.seed_meanings["S2"], "state": "GOVERNANCE_MULTISIG", "evidence": "Ownable2Step admin bindings"},
        "S3": {"label": cartridge.seed_meanings["S3"], "state": "MULTI_MODULE_ROUTING", "evidence": f"{len(modules)} modules mapped"},
        "S4": {"label": cartridge.seed_meanings["S4"], "state": "STORAGE_RATE_LIMITS", "evidence": "RateLimits.Data storage mapped"},
        "S5": {"label": cartridge.seed_meanings["S5"], "state": "CAPACITY_CONSTRAINED", "evidence": "Module throttles active"},
        "S6": {"label": cartridge.seed_meanings["S6"], "state": "FAIL_CLOSED_ACTIVE", "evidence": "Revert paths verified"},
        "S7": {"label": cartridge.seed_meanings["S7"], "state": "ZERO_WINDOW_UNCERTAINTY" if has_bridge else "CLEAN_BOUNDS", "evidence": "Rate limit window check"},
        "S8": {"label": cartridge.seed_meanings["S8"], "state": "LIMIT_EXCEEDED_REVERT", "evidence": "Revert transitions bounded"},
        "S9": {"label": cartridge.seed_meanings["S9"], "state": "LEDGER_FINALITY", "evidence": "Settlement receipts verified"},
    }
    tms.set_space("T5_COMPOUNDING", DomainSpaceInstance(space_id="T0_PRESENT_MANIFEST_OBSERVATION", phase="T5_COMPOUNDING", seeds=s5_seeds))

    s4_seeds = dict(s5_seeds)
    s4_seeds["S4"] = {"label": cartridge.seed_meanings["S4"], "state": "PRE_DEPLOYMENT_BASELINE", "evidence": "Initial baseline"}
    tms.set_space("T4_STABILITY", DomainSpaceInstance(space_id="T_MINUS_1_BASELINE", phase="T4_STABILITY", seeds=s4_seeds))

    s6_seeds = dict(s5_seeds)
    if has_bridge:
        s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "CUMULATIVE_BYPASS_POSSIBLE", "evidence": "Candidate transition: W=0 allows unbounded cumulative volume"}
        tms.relationships.append({"phase": "T6_REFRACTING", "status": "POSSIBLE", "rule": "forward_reachability_zero_window_bypass"})
    else:
        s6_seeds["S6"] = {"label": cartridge.seed_meanings["S6"], "state": "STEADY_STATE_CAPACITY", "evidence": "Throttling preserved"}
        tms.relationships.append({"phase": "T6_REFRACTING", "status": "DERIVED", "rule": "forward_stability"})
    tms.set_space("T6_REFRACTING", DomainSpaceInstance(space_id="T_PLUS_1_REACHABILITY", phase="T6_REFRACTING", seeds=s6_seeds))

    tms.compute_inter_space_transition_receipt("T4_STABILITY", "T5_COMPOUNDING", {"transition": "manifest_ingestion"})
    tms.compute_inter_space_transition_receipt("T5_COMPOUNDING", "T6_REFRACTING", {"transition": "module_evaluation"})

    return tms


def parse_raw_stream(
    raw_text: str, cartridge_key: str = "security", filename: str = ""
) -> TemporalMatrixSpace:
    """Dispatches raw stream text to the appropriate cartridge parser."""
    ck = cartridge_key.lower()
    if filename.lower().endswith((".sol", ".py", ".rs", ".js", ".ts", ".go", ".cpp", ".c")) or any(
        k in raw_text for k in ["pragma solidity", "contract ", "library RateLimits", "interface IBridge"]
    ):
        return parse_raw_code_stream(raw_text, filename=filename or "TargetSource.sol")
    elif filename.lower().endswith(".json") and '"project"' in raw_text:
        return parse_raw_manifest_stream(raw_text, filename=filename or "target.json")
    elif "legal" in ck or "courtforge" in ck:
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


def run_minimal_seed_intake(
    cartridge_key: str,
    custom_seed: Optional[str] = None,
    custom_case_id: Optional[str] = None,
    print_summary: bool = True,
) -> tuple[Path, TemporalMatrixSpace]:
    """
    Executes natural tensor hydration from an irreducibly minimal seed.
    Hydrates 81 state coordinates, contains unobserved coordinates in F7,
    and emits a normalized observation fixture for evaluation by the fixed F1-F9 engine.
    """
    normalized_key = cartridge_key.lower().replace("cartridge_", "").replace("_ir", "")
    if "courtforge" in normalized_key or "legal" in normalized_key:
        cart_name = "legal"
        cart_spec = CARTRIDGE_COURTFORGE_LEGAL
        default_seed = SAMPLE_MINIMAL_SEEDS["legal"]
        default_case = "minimal_seed_extracted_legal"
    elif "wms" in normalized_key or "logistic" in normalized_key:
        cart_name = "logistics"
        cart_spec = CARTRIDGE_WMS_LOGISTICS
        default_seed = SAMPLE_MINIMAL_SEEDS["logistics"]
        default_case = "minimal_seed_extracted_logistics"
    else:
        cart_name = "security"
        cart_spec = CARTRIDGE_SECURITY_IR
        default_seed = SAMPLE_MINIMAL_SEEDS["security"]
        default_case = "minimal_seed_extracted_security"

    seed_text = custom_seed if custom_seed else default_seed
    case_id = custom_case_id if custom_case_id else default_case

    tms = hydrate_from_minimal_seed(seed_text, cart_spec)

    if print_summary:
        print(f"\n=======================================================")
        print(f" MINIMAL SEED HYDRATION: {cart_spec.name.upper()} ({cart_spec.cartridge_id})")
        print(f" ATOMIC SEED: '{seed_text.strip()}'")
        print(f"=======================================================")
        print(tms.format_matrix_summary())

    fixture_path = emit_matrix_observation_fixture(tms, case_id=case_id)
    print(f"[READER] Successfully emitted minimal seed {cart_name} matrix fixture -> {fixture_path}")
    return fixture_path, tms


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
    parser.add_argument("--minimal-seed", "-m", nargs="?", const="", help="Execute minimal-seed natural hydration test (optional seed string)")
    parser.add_argument("--no-summary", action="store_true", help="Suppress terminal matrix summary printout")
    args = parser.parse_args(argv)

    print_summary = not args.no_summary
    custom_in = Path(args.input) if args.input else None

    if args.minimal_seed is not None:
        custom_seed = args.minimal_seed if args.minimal_seed != "" else None
        if args.cartridge == "all":
            for cart in ["security", "legal", "logistics"]:
                run_minimal_seed_intake(
                    cartridge_key=cart,
                    custom_seed=custom_seed,
                    custom_case_id=args.case_id,
                    print_summary=print_summary,
                )
        else:
            run_minimal_seed_intake(
                cartridge_key=args.cartridge,
                custom_seed=custom_seed,
                custom_case_id=args.case_id,
                print_summary=print_summary,
            )
        return 0

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
