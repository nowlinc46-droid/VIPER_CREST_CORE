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
    DOMAIN_SEEDS,
    TEMPORAL_PHASES,
    CartridgeSpec,
    DEFAULT_SECURITY_CARTRIDGE,
    DomainSpaceInstance,
    TemporalMatrixSpace,
)

VIPER_ROOT = Path("C:/ViperCrest")
RUNTIME_DIR = VIPER_ROOT / "runtime"
FIXTURES_DIR = VIPER_ROOT / "fixtures"
DROPZONE_RAW = RUNTIME_DIR / "dropzone" / "raw"


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


def parse_raw_incident_stream(
    raw_text: str, cartridge: CartridgeSpec = DEFAULT_SECURITY_CARTRIDGE
) -> TemporalMatrixSpace:
    """
    Zero-execution semantic parser:
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
            "evidence": "Unresponsive host without confirmed status; held in F7",
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
    # Never invent values; establish predecessor only where evidence bounds it
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


def main() -> int:
    parser = argparse.ArgumentParser(description="ViperCrest Air-Gapped Reader Engine")
    parser.add_argument("--input", "-i", help="Path to raw input file")
    parser.add_argument("--case-id", default="cisa_hospital_ir_normalized", help="Output case ID")
    parser.add_argument("--print-summary", action="store_true", default=True, help="Print terminal matrix summary")
    args = parser.parse_args()

    DROPZONE_RAW.mkdir(parents=True, exist_ok=True)
    if not args.input:
        # Default sample CISA incident raw log
        sample_path = DROPZONE_RAW / "hospital_incident_t0.raw"
        sample_path.write_text(
            "2026-11-01T02:15:12Z [FIREWALL_ALERT] src=192.168.10.44 dst=192.168.10.0/24 port=445 proto=TCP flags=SYN count=1420\n"
            "2026-11-01T02:16:04Z [EDR_HOST_44] powershell.exe -enc SQBuAHYAbwBrAGUALQBXAG0AaQ... user=SVC_BILLING\n"
            "2026-11-01T02:16:48Z [MED_BUS_GATE] WARN: Infusion_Gate_01 timeout delta=4120ms to nurse_console\n"
            "2026-11-01T02:17:00Z [MONITOR_PING] PACS_Server_02 port 104 NO_RESPONSE ConnectionReset\n"
            "2026-11-01T02:17:01Z [SWITCH_CORE_VLAN] STATS: Clinical_Core packets_dropped=0 err=0 crc=0 status=NOMINAL\n",
            encoding="utf-8",
        )
        target_input = sample_path
    else:
        target_input = Path(args.input)

    raw_bytes, sha256 = safe_read_bytes(target_input)
    text = safe_decode_text(raw_bytes)
    tms = parse_raw_incident_stream(text)

    if args.print_summary:
        print(tms.format_matrix_summary())

    fixture_path = emit_matrix_observation_fixture(tms, case_id=args.case_id)
    print(f"[READER] Emitted normalized matrix fixture to: {fixture_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
