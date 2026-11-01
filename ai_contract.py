"""
ViperCrest AI Typed Boundary Contract (ai_contract.py).

Enforces the absolute separation of authorities:
  AI proposes coordinates and claims; ViperCrest assigns state and authority.

Core Invariants:
1. Canonical Epistemic Vocabulary (imported from domain_space.py):
   - OBSERVED: Requires cryptographic provenance.
   - DERIVED: Requires supporting coordinate references.
   - POSSIBLE: Must remain non-factual / candidate status.
   - CONTRADICTED: Requires conflicting evidence references.
   - UNRESOLVED: Preserved in F7; CANNOT be promoted by AI.

2. Authority Partition:
   AI_AUTHORITY:
     - translate_input
     - select_cartridge
     - request_runtime_evaluation
     - query_coordinates
     - explain_sealed_results

   VIPERCREST_AUTHORITY:
     - classify_epistemic_state
     - derive_coordinates
     - bound_transitions
     - preserve_f7_uncertainty
     - seal_results

3. Input Typing & Anti-Tampering:
   AI inputs are strictly typed as UNVERIFIED_INPUT.
   Any AI submission attempting to pre-classify its own data as OBSERVED,
   DERIVED, POSSIBLE, or CONTRADICTED is REJECTED with ProtocolViolationError.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

# Import canonical constants from domain_space.py
from domain_space import (
    CARTRIDGES,
    DOMAIN_SEEDS,
    HYDRATION_STATES,
    RUNTIME_STAGES,
    TEMPORAL_PHASES,
    CartridgeSpec,
    TemporalMatrixSpace,
    hydrate_from_minimal_seed,
)
import reader_engine as re_eng

AI_DIR = VIPER_ROOT / "runtime" / "ai"
AI_REQUESTS_DIR = AI_DIR / "requests"
AI_RESPONSES_DIR = AI_DIR / "responses"

PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

# Authority Boundary Sets
AI_AUTHORITY: Set[str] = {
    "translate_input",
    "select_cartridge",
    "request_runtime_evaluation",
    "query_coordinates",
    "explain_sealed_results",
}

VIPERCREST_AUTHORITY: Set[str] = {
    "classify_epistemic_state",
    "derive_coordinates",
    "bound_transitions",
    "preserve_f7_uncertainty",
    "seal_results",
}


class ProtocolViolationError(ValueError):
    """Raised when an AI submission breaches the authority boundary."""
    pass


class AISubmissionType(str, Enum):
    RAW_CLAIM = "raw_claim"
    OBSERVATION_CANDIDATE = "observation_candidate"
    QUESTION = "question"
    REQUESTED_ACTION = "requested_action"


class AIIntent(str, Enum):
    ANALYZE = "analyze"
    HYDRATE = "hydrate"
    QUERY = "query"
    EXPLAIN = "explain"


class AIAction(str, Enum):
    MATRIX = "matrix"
    HYDRATE = "hydrate"
    QUERY = "query"
    EXPLAIN = "explain"


@dataclass
class ObservationCandidate:
    """An unverified observation candidate submitted by AI."""
    seed_key: Optional[str] = None  # e.g. "S2", "S3", "S5", or None
    raw_text: str = ""
    candidate_state: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.raw_text and not self.candidate_state:
            raise ProtocolViolationError("ObservationCandidate requires non-empty raw_text or candidate_state")
        # Enforce rule: AI CANNOT self-classify epistemic state
        forbidden = HYDRATION_STATES | {"STATUS", "EPISTEMIC_STATE", "STATE_CLASSIFICATION"}
        for k, v in self.context.items():
            if k.upper() in forbidden or (isinstance(v, str) and v.upper() in HYDRATION_STATES):
                raise ProtocolViolationError(
                    f"AI Authority Breach: AI cannot assign epistemic state '{v}' in observation context. "
                    "Only ViperCrest may assign epistemic states."
                )


@dataclass
class RawClaim:
    """An unverified raw factual or narrative claim proposed by AI."""
    claim_id: str
    statement: str
    source_reference: Optional[str] = None


@dataclass
class AIQuestion:
    """A natural language or coordinate-directed query from human/AI."""
    question_id: str
    query_text: str
    target_coordinate: Optional[str] = None  # e.g. "T5:S7" or "F7:T5:S7"


@dataclass
class AIRequestEnvelope:
    """
    The strictly validated request contract handed from AI Wrapper to ViperCrest.
    All inputs are treated as UNVERIFIED_INPUT until processed by ViperCrest.
    """
    intent: str
    cartridge: str
    observations: List[Dict[str, Any]] = field(default_factory=list)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    questions: List[Dict[str, Any]] = field(default_factory=list)
    requested_action: str = "matrix"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        """Enforces schema integrity and authority constraints."""
        # Validate intent
        valid_intents = {e.value for e in AIIntent}
        if self.intent not in valid_intents:
            raise ProtocolViolationError(f"Invalid intent '{self.intent}'. Must be one of {valid_intents}")

        # Validate cartridge
        cart_key = self.cartridge.lower().replace("cartridge_", "").replace("_ir", "")
        if cart_key not in {"security", "legal", "courtforge", "courtforge_legal", "logistics", "wms", "wms_logistics"}:
            raise ProtocolViolationError(f"Unknown cartridge '{self.cartridge}'. Available: security, legal, logistics")

        # Validate requested_action
        valid_actions = {e.value for e in AIAction}
        if self.requested_action not in valid_actions:
            raise ProtocolViolationError(f"Invalid requested_action '{self.requested_action}'. Must be one of {valid_actions}")

        # Validate that AI does not usurp ViperCrest authority
        for obs in self.observations:
            candidate = ObservationCandidate(
                seed_key=obs.get("seed_key"),
                raw_text=obs.get("raw_text", ""),
                candidate_state=obs.get("candidate_state", ""),
                context=obs.get("context", {}),
            )
            candidate.validate()
            # AI cannot submit explicit authoritative statuses
            if "status" in obs or "epistemic_status" in obs:
                raise ProtocolViolationError(
                    "AI Authority Breach: 'status' or 'epistemic_status' supplied by AI. "
                    "AI may propose raw claims; ViperCrest assigns state and authority."
                )

        for clm in self.claims:
            if "status" in clm or "epistemic_status" in clm:
                raise ProtocolViolationError("AI Authority Breach: Claims cannot contain pre-assigned epistemic status.")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AIRequestEnvelope:
        envelope = cls(
            intent=data.get("intent", "analyze"),
            cartridge=data.get("cartridge", "security"),
            observations=data.get("observations", []),
            claims=data.get("claims", []),
            questions=data.get("questions", []),
            requested_action=data.get("requested_action", "matrix"),
            request_id=data.get("request_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
        envelope.validate()
        return envelope


@dataclass
class AuthoritativeCoordinateResult:
    """An authoritative state coordinate classified strictly by ViperCrest."""
    coordinate: str
    phase: str
    seed: str
    meaning: str
    status: str  # OBSERVED | DERIVED | POSSIBLE | CONTRADICTED | UNRESOLVED
    state: str
    evidence: str
    contained_in_f7: bool


@dataclass
class AuthoritativeResponseEnvelope:
    """The authoritative response sealed by ViperCrest returned to AI Wrapper."""
    request_id: str
    intent: str
    cartridge_id: str
    status: str  # SUCCESS | ERROR_PATIENT_POLICY | PROTOCOL_ERROR
    epistemic_summary: Dict[str, int]
    coordinates_81: List[Dict[str, Any]]
    tensor_dimensions: Tuple[int, int, int]
    session_id: Optional[str]
    session_receipt_verified: bool
    f7_uncertainty_preserved: bool
    question_answers: List[Dict[str, Any]] = field(default_factory=list)
    plain_english_report: Optional[Dict[str, Any]] = None
    grammar_envelope: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ViperCrestContractExecutor:
    """
    The secure gateway executing validated AIRequestEnvelopes through ViperCrest.
    All classification, derivation, transition bounding, and cryptographic sealing
    occur exclusively under VIPERCREST_AUTHORITY.
    """

    def __init__(self):
        AI_REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
        AI_RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

    def execute(self, envelope: AIRequestEnvelope) -> AuthoritativeResponseEnvelope:
        """Validates envelope, enforces boundaries, and executes through ViperCrest."""
        envelope.validate()

        # Persist unverified AI request
        req_path = AI_REQUESTS_DIR / f"request_{envelope.request_id}.json"
        req_path.write_text(json.dumps(envelope.to_dict(), indent=2), encoding="utf-8")

        cart_name = envelope.cartridge.lower().replace("cartridge_", "").replace("_ir", "")
        if "legal" in cart_name or "courtforge" in cart_name:
            cart_spec = CARTRIDGES["legal"]
            cart_key = "legal"
        elif "logistics" in cart_name or "wms" in cart_name:
            cart_spec = CARTRIDGES["logistics"]
            cart_key = "logistics"
        else:
            cart_spec = CARTRIDGES["security"]
            cart_key = "security"

        # 1. Synthesize Minimal / Raw Input from Observations or Claims
        if envelope.observations and envelope.observations[0].get("raw_text"):
            combined_seed = envelope.observations[0]["raw_text"]
        else:
            raw_seed_candidates = []
            for obs in envelope.observations:
                raw_seed_candidates.append(obs.get("raw_text") or obs.get("candidate_state", ""))
            for clm in envelope.claims:
                raw_seed_candidates.append(clm.get("statement", ""))

            if raw_seed_candidates:
                combined_seed = "\n".join(c for c in raw_seed_candidates if c)
            else:
                combined_seed = re_eng.SAMPLE_MINIMAL_SEEDS.get(cart_key, "ANOMALY_DETECTED")

        target_filename = None
        for obs in envelope.observations:
            meta = obs.get("metadata", {})
            if meta.get("target_name"):
                target_filename = meta["target_name"]
                break

        # 2. ViperCrest Natural Hydration (VIPERCREST_AUTHORITY)
        is_code = (
            bool(re.search(r"pragma solidity|\bcontract\b|\blibrary\b|\binterface\b|\bpub fn\b|\buse anchor_lang\b|#\[program\]", combined_seed, re.IGNORECASE))
            or (bool(target_filename) and any(target_filename.endswith(ext) for ext in [".sol", ".rs", ".py"]))
        )
        is_manifest = (bool(target_filename) and target_filename.endswith(".json")) and '"project"' in combined_seed
        if is_code:
            tms = re_eng.parse_raw_code_stream(combined_seed, filename=target_filename or "TargetSource.sol", cartridge=cart_spec)
        elif is_manifest:
            tms = re_eng.parse_raw_manifest_stream(combined_seed, filename=target_filename or "target.json", cartridge=cart_spec)
        else:
            tms = hydrate_from_minimal_seed(combined_seed, cart_spec)

        import grammar_schema as gs
        grammar_env = getattr(tms, "grammar_envelope", None)
        if not grammar_env:
            try:
                grammar_env = gs.parse_basic_grammar(combined_seed).to_dict()
                tms.grammar_envelope = grammar_env
            except Exception:
                grammar_env = None

        plain_report = getattr(tms, "plain_english_report", None)
        coords_81 = tms.get_all_81_coordinates()
        for c in coords_81:
            c["contained_in_f7"] = (c.get("status") == "UNRESOLVED")
        tensor_eval = tms.evaluate_729_tensor_space()

        # 3. Emit Matrix Fixture & Run Fixed Invariant F1-F9 Engine
        fixture_case_id = f"ai_contract_{cart_key}_{envelope.request_id[:8]}"
        fixture_path = re_eng.emit_matrix_observation_fixture(tms, case_id=fixture_case_id)

        session_id = None
        session_verified = False
        exec_status = "SUCCESS"
        error_msg = None

        if envelope.requested_action in {"matrix", "hydrate"}:
            cmd = [str(PYTHON_EXE), "-B", str(VIPER_ROOT / "viper.py"), "matrix", "--target", str(fixture_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and "Receipt and five-file session audit verified" in res.stdout:
                session_verified = True
                # Extract session path if present
                for line in res.stdout.splitlines():
                    if "session_" in line:
                        session_id = line.strip().split()[-1]
            else:
                exec_status = "ERROR_RUNTIME_EXECUTION"
                error_msg = res.stderr or res.stdout

        # 4. Resolve Questions Authoritatively (explaining F7 and coordinates)
        question_answers = []
        for q in envelope.questions:
            q_id = q.get("question_id", "Q1")
            q_text = q.get("query_text", "")
            q_coord = q.get("target_coordinate")

            answer = self._resolve_question(q_text, q_coord, coords_81, tms)
            question_answers.append({
                "question_id": q_id,
                "query_text": q_text,
                "target_coordinate": q_coord,
                "authoritative_answer": answer,
            })

        # 5. Build Authoritative Response Envelope
        response = AuthoritativeResponseEnvelope(
            request_id=envelope.request_id,
            intent=envelope.intent,
            cartridge_id=cart_spec.cartridge_id,
            status=exec_status,
            epistemic_summary=tensor_eval["summary"],
            coordinates_81=coords_81,
            tensor_dimensions=tensor_eval["dimensions"],
            session_id=session_id,
            session_receipt_verified=session_verified,
            f7_uncertainty_preserved=tensor_eval["summary"]["unresolved_f7_cells"] > 0,
            question_answers=question_answers,
            plain_english_report=plain_report,
            grammar_envelope=grammar_env,
            error_message=error_msg,
        )

        # Persist authoritative response
        resp_path = AI_RESPONSES_DIR / f"response_{envelope.request_id}.json"
        resp_path.write_text(json.dumps(response.to_dict(), indent=2), encoding="utf-8")

        return response

    def _resolve_question(
        self,
        query_text: str,
        target_coordinate: Optional[str],
        coords_81: List[Dict[str, Any]],
        tms: TemporalMatrixSpace,
    ) -> Dict[str, Any]:
        """Resolves coordinate questions strictly against authoritative ViperCrest state."""
        q_lower = query_text.lower()

        # Check for specific coordinate lookup
        if target_coordinate:
            # Handle e.g. "T5:S7" or "F7:T5:S7"
            tokens = target_coordinate.split(":")
            phase = tokens[-2] if len(tokens) >= 2 else "T5_COMPOUNDING"
            seed = tokens[-1] if len(tokens) >= 1 else "S7"

            # Normalize phase
            matched_phase = next((p for p in TEMPORAL_PHASES if phase.upper() in p), "T5_COMPOUNDING")
            coord_info = tms.get_coordinate_state(matched_phase, seed.upper())
            return {
                "coordinate": target_coordinate,
                "epistemic_status": coord_info["status"],
                "explanation": (
                    f"Coordinate {coord_info['coordinate']} ({coord_info['meaning']}) has status "
                    f"'{coord_info['status']}'. Reason: {coord_info['evidence']}"
                ),
            }

        # Check for unresolved query (e.g., "Why is PACS unresolved?")
        if "why" in q_lower and ("unresolved" in q_lower or "pacs" in q_lower or "unknown" in q_lower):
            s7_info = tms.get_coordinate_state("T5_COMPOUNDING", "S7")
            return {
                "subject": "F7_UNCERTAINTY_PRESERVATION",
                "epistemic_status": "UNRESOLVED",
                "explanation": (
                    "ViperCrest strictly forbids inventing or guessing unobserved facts. "
                    f"At T5:S7 ({s7_info['meaning']}), status is locked in F7 as UNRESOLVED "
                    f"because: {s7_info['evidence']}"
                ),
            }

        # General inquiry about present state
        t5_rep = tms.positions.get("T5_COMPOUNDING")
        observed_seeds = [
            f"{s}: {data.get('state')}"
            for s, data in (t5_rep.seeds.items() if t5_rep else [])
            if data.get("status") == "OBSERVED"
        ]
        return {
            "subject": "OBSERVED_PRESENT_STATE",
            "epistemic_status": "OBSERVED",
            "explanation": (
                f"ViperCrest has verified the observed present at T5_COMPOUNDING. "
                f"Directly observed seeds: {', '.join(observed_seeds)}. "
                "All unevidenced coordinates remain sealed in Stage F7."
            ),
        }


def process_ai_submission(raw_envelope_json: str | Dict[str, Any]) -> AuthoritativeResponseEnvelope:
    """Convenience entry point for parsing, validating, and executing an AI envelope."""
    if isinstance(raw_envelope_json, str):
        data = json.loads(raw_envelope_json)
    else:
        data = raw_envelope_json

    envelope = AIRequestEnvelope.from_dict(data)
    executor = ViperCrestContractExecutor()
    return executor.execute(envelope)
