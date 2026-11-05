"""
ViperCrest Typed RPC Dispatcher (rpc_dispatcher.py).

Recognizes RPC methods (specifically eth_blockNumber), calls the local RPC endpoint
(e.g., Anvil, Geth, Reth on 127.0.0.1:8545), captures the response as cryptographically
bound evidence, and only then dispatches that evidence through the ViperCrest runtime engine.

Invariants Enforced:
1. Typed Recognition: Explicit schema validation for JSON-RPC methods and arguments.
2. Air-Gap Containment (V05): Enforces local loopback binding (127.0.0.1, localhost, ::1)
   to prevent unauthorized remote egress.
3. Resource Bounding (V06): Hard-bounded request/response payload limits (1MB default).
4. Evidence Provenance (V08/V09): Response captured with ISO timestamp, SHA-256 digest,
   and deterministic payload structure before entering ViperCrest.
5. Authority Partition: Does not self-classify epistemic states; submits as candidate
   evidence to ViperCrest for authoritative classification, evaluation, and receipt sealing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from ai_contract import (
    AIRequestEnvelope,
    AuthoritativeResponseEnvelope,
    ProtocolViolationError,
    ViperCrestContractExecutor,
)

DEFAULT_RPC_URL = "http://127.0.0.1:8545"
MAX_RPC_RESPONSE_BYTES = 1_048_576  # 1 MB boundary per Invariant V06
ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}


class RPCError(Exception):
    """Base exception for RPC dispatcher failures."""
    pass


class RPCConnectionError(RPCError):
    """Raised when the local RPC endpoint is unreachable or connection is refused."""
    pass


class RPCInvalidRequestError(RPCError):
    """Raised when an RPC request envelope is malformed or unauthorized."""
    pass


class RPCMethodNotSupportedError(RPCError):
    """Raised when an unhandled or unrecognized RPC method is supplied."""
    pass


class RPCMethod(str, Enum):
    ETH_BLOCK_NUMBER = "eth_blockNumber"
    ETH_GET_BLOCK_BY_NUMBER = "eth_getBlockByNumber"
    ETH_CHAIN_ID = "eth_chainId"
    NET_VERSION = "net_version"


@dataclass
class RPCRequest:
    """Typed JSON-RPC 2.0 Request Envelope."""
    method: str
    params: List[Any] = field(default_factory=list)
    jsonrpc: str = "2.0"
    id: int = 1
    endpoint: str = DEFAULT_RPC_URL

    def validate(self) -> None:
        if not self.method or not isinstance(self.method, str):
            raise RPCInvalidRequestError("RPC method must be a non-empty string.")
        
        # Enforce valid RPC identifier syntax
        if not re.fullmatch(r"[a-zA-Z0-9_]+", self.method):
            raise RPCInvalidRequestError(f"Invalid characters in RPC method: {self.method}")
        
        if not isinstance(self.params, list):
            raise RPCInvalidRequestError("RPC params must be a JSON array (list).")

        # Validate local loopback boundary for Air-Gap Containment (V05)
        parsed = urllib.parse.urlsplit(self.endpoint)
        if parsed.scheme not in {"http", "https"}:
            raise RPCInvalidRequestError(f"Unsupported endpoint scheme: {parsed.scheme}")
        hostname = (parsed.hostname or "").lower()
        if hostname not in ALLOWED_LOOPBACK_HOSTS:
            raise RPCInvalidRequestError(
                f"Air-Gap Containment Violation (V05): Endpoint '{self.endpoint}' is non-local. "
                f"Local dispatcher only permits loopback targets: {ALLOWED_LOOPBACK_HOSTS}"
            )

    def to_json_bytes(self) -> bytes:
        payload = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params,
        }
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")


@dataclass
class RPCEvidence:
    """
    Cryptographically captured evidence record obtained from local RPC query.
    Must be sealed into an evidence record prior to passing through ViperCrest.
    """
    evidence_id: str
    endpoint: str
    method: str
    params: List[Any]
    result: Any
    block_number: Optional[int]
    raw_response: Dict[str, Any]
    captured_at: str
    evidence_hash: str
    status: str = "CAPTURED"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_evidence_report(self) -> str:
        lines = [
            f"[VIPERCREST RPC EVIDENCE CAPTURE]",
            f"Evidence-ID: {self.evidence_id}",
            f"Method:      {self.method}",
            f"Endpoint:    {self.endpoint}",
            f"Captured-At: {self.captured_at}",
            f"SHA256:      {self.evidence_hash}",
            f"Status:      {self.status}",
        ]
        if self.block_number is not None:
            lines.append(f"Block-Height: {self.block_number} (Hex: {self.result})")
        else:
            lines.append(f"Result:       {json.dumps(self.result)}")
        if self.error_message:
            lines.append(f"RPC-Error:    {self.error_message}")
        return "\n".join(lines)


def is_rpc_input(user_input: Union[str, List[str], Dict[str, Any]]) -> bool:
    """Predicate to determine if input matches an RPC dispatch request."""
    if isinstance(user_input, dict):
        return "method" in user_input and user_input["method"] in {m.value for m in RPCMethod}

    if isinstance(user_input, list):
        user_input = " ".join(user_input)

    raw = user_input.strip()
    lowered = raw.lower()

    # Direct method match or method calls
    for m in RPCMethod:
        if m.value.lower() in lowered:
            return True

    # Common prefixes: "rpc eth_...", "call eth_...", "--rpc"
    if lowered.startswith("rpc ") or lowered.startswith("call ") or "--rpc" in lowered:
        return True

    return False


class TypedRPCDispatcher:
    """
    Typed RPC dispatcher for EVM node interactions.
    Recognizes eth_blockNumber, calls local RPC endpoint, captures evidence,
    and dispatches evidence through the ViperCrest sovereign runtime.
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_RPC_URL,
        timeout: float = 5.0,
        max_response_bytes: int = MAX_RPC_RESPONSE_BYTES,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes

    def recognizes(self, input_data: Union[str, List[str], Dict[str, Any]]) -> bool:
        """Determines if the given input is recognized by this typed dispatcher."""
        return is_rpc_input(input_data)

    def parse_request(
        self,
        input_data: Union[str, List[str], Dict[str, Any]],
        endpoint_override: Optional[str] = None,
    ) -> RPCRequest:
        """Parses and strictly validates raw input into a typed RPCRequest."""
        target_endpoint = endpoint_override or self.endpoint

        if isinstance(input_data, dict):
            method = input_data.get("method", "")
            params = input_data.get("params", [])
            req_id = input_data.get("id", 1)
            req = RPCRequest(method=method, params=params, id=req_id, endpoint=target_endpoint)
            req.validate()
            return req

        if isinstance(input_data, list):
            input_str = " ".join(input_data)
        else:
            input_str = str(input_data)

        clean = input_str.strip()

        # Check for endpoint overrides in CLI flags, e.g. --endpoint http://127.0.0.1:8545
        ep_match = re.search(r"--(?:endpoint|rpc-url)\s+([^\s]+)", clean)
        if ep_match:
            target_endpoint = ep_match.group(1)
            clean = re.sub(r"--(?:endpoint|rpc-url)\s+[^\s]+", "", clean).strip()

        # Clean out common command prefixes
        clean = re.sub(r"^(?:rpc|call|eval|run|vc-rpc)\s+", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"^--rpc\s*", "", clean).strip()

        # Extract method name
        tokens = clean.split()
        if not tokens:
            raise RPCInvalidRequestError("No RPC method supplied in request.")

        raw_method = tokens[0].rstrip("()")

        # Syntax check on method token
        if not re.fullmatch(r"[a-zA-Z0-9_]+", raw_method):
            raise RPCInvalidRequestError(f"Invalid characters in RPC method: {raw_method}")

        params: List[Any] = []

        if len(tokens) > 1:
            # Remaining tokens treated as parameters
            for tok in tokens[1:]:
                # If JSON formatted parameter
                if tok.startswith("[") or tok.startswith("{") or tok.isdigit() or tok in {"true", "false", "null"}:
                    try:
                        params.append(json.loads(tok))
                        continue
                    except Exception:
                        pass
                params.append(tok)

        # Match recognized method names
        matched_method = None
        for m in RPCMethod:
            if m.value.lower() == raw_method.lower():
                matched_method = m.value
                break

        if not matched_method:
            # Allow well-formed EVM methods
            if re.fullmatch(r"eth_[a-zA-Z0-9]+|net_[a-zA-Z0-9]+|web3_[a-zA-Z0-9]+", raw_method):
                matched_method = raw_method
            else:
                raise RPCMethodNotSupportedError(
                    f"Unsupported or unrecognized RPC method: '{raw_method}'. "
                    f"Supported methods include: {[m.value for m in RPCMethod]}"
                )

        request = RPCRequest(
            method=matched_method,
            params=params,
            endpoint=target_endpoint,
        )
        request.validate()
        return request

    def call_local_rpc(self, request: RPCRequest) -> RPCEvidence:
        """
        Executes HTTP JSON-RPC 2.0 query to the authorized local loopback endpoint.
        Captures the response, digests it with SHA-256, and returns a verified RPCEvidence record.
        """
        request.validate()
        payload_bytes = request.to_json_bytes()
        captured_at = datetime.now(timezone.utc).isoformat()
        evidence_id = str(uuid4())

        http_req = urllib.request.Request(
            request.endpoint,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ViperCrest-RPC-Dispatcher/2.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_req, timeout=self.timeout) as resp:
                resp_bytes = resp.read(self.max_response_bytes + 1)
                if len(resp_bytes) > self.max_response_bytes:
                    raise RPCError(
                        f"Resource Exhaustion Invariant (V06) violated: RPC response exceeded "
                        f"limit of {self.max_response_bytes} bytes."
                    )
                raw_json = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.URLError as err:
            raise RPCConnectionError(
                f"Failed to connect to local RPC endpoint at {request.endpoint}: {err.reason}. "
                "Ensure your local EVM node (e.g. Anvil, Hardhat, Geth) is running."
            ) from err
        except TimeoutError as err:
            raise RPCConnectionError(
                f"Local RPC endpoint at {request.endpoint} timed out after {self.timeout}s."
            ) from err
        except Exception as err:
            raise RPCError(f"Unexpected error calling local RPC: {err}") from err

        evidence_hash = hashlib.sha256(resp_bytes).hexdigest()

        if "error" in raw_json and raw_json["error"] is not None:
            err_obj = raw_json["error"]
            err_msg = err_obj.get("message") if isinstance(err_obj, dict) else str(err_obj)
            return RPCEvidence(
                evidence_id=evidence_id,
                endpoint=request.endpoint,
                method=request.method,
                params=request.params,
                result=None,
                block_number=None,
                raw_response=raw_json,
                captured_at=captured_at,
                evidence_hash=evidence_hash,
                status="RPC_ERROR",
                error_message=err_msg,
            )

        result = raw_json.get("result")
        block_number: Optional[int] = None

        if request.method == RPCMethod.ETH_BLOCK_NUMBER.value:
            if isinstance(result, str) and result.startswith("0x"):
                try:
                    block_number = int(result, 16)
                except ValueError:
                    block_number = None
            elif isinstance(result, int):
                block_number = result

        return RPCEvidence(
            evidence_id=evidence_id,
            endpoint=request.endpoint,
            method=request.method,
            params=request.params,
            result=result,
            block_number=block_number,
            raw_response=raw_json,
            captured_at=captured_at,
            evidence_hash=evidence_hash,
            status="CAPTURED",
            error_message=None,
        )

    def build_vipercrest_envelope(
        self,
        evidence: RPCEvidence,
        cartridge: str = "security",
    ) -> AIRequestEnvelope:
        """
        Transforms captured evidence into a strictly compliant AIRequestEnvelope.
        Enforces authority boundaries: does NOT self-classify epistemic states.
        """
        evidence_text = evidence.format_evidence_report()
        block_disp = f" (Block Height: {evidence.block_number})" if evidence.block_number is not None else ""

        observations = [
            {
                "raw_text": evidence_text,
                "candidate_state": "RPC_OBSERVATION_CAPTURED",
                "context": {
                    "method": evidence.method,
                    "endpoint": evidence.endpoint,
                    "evidence_hash": evidence.evidence_hash,
                    "block_number": evidence.block_number,
                },
                "metadata": {
                    "target_name": f"{evidence.method}.rpc",
                    "target_type": "RPC_EVIDENCE",
                    "evidence_hash": evidence.evidence_hash,
                },
            }
        ]

        claims = [
            {
                "claim_id": "CLM-RPC-01",
                "statement": (
                    f"Local RPC query {evidence.method}{block_disp} executed against {evidence.endpoint}. "
                    f"Evidence digest: {evidence.evidence_hash[:16]}..."
                ),
            }
        ]

        envelope = AIRequestEnvelope(
            intent="analyze",
            cartridge=cartridge,
            observations=observations,
            claims=claims,
            questions=[],
            requested_action="matrix",
        )
        envelope.validate()
        return envelope

    def dispatch(
        self,
        input_data: Union[str, List[str], Dict[str, Any]],
        endpoint_override: Optional[str] = None,
        cartridge: str = "security",
    ) -> Tuple[RPCEvidence, AuthoritativeResponseEnvelope]:
        """
        Complete end-to-end typed dispatch flow:
        1. Recognizes & validates RPC method (e.g. eth_blockNumber).
        2. Calls local RPC endpoint.
        3. Captures response as cryptographically bound RPCEvidence.
        4. ONLY THEN routes the evidence through ViperCrest runtime.
        5. Returns (RPCEvidence, AuthoritativeResponseEnvelope).
        """
        # Step 1: Typed Recognition & Parameter Parsing
        req = self.parse_request(input_data, endpoint_override=endpoint_override)

        # Step 2 & 3: Local Call & Evidence Capture
        evidence = self.call_local_rpc(req)

        # Fail-closed check if RPC returned an internal protocol error
        if evidence.status == "RPC_ERROR":
            raise RPCError(f"RPC endpoint returned protocol error: {evidence.error_message}")

        # Step 4: Dispatch Evidence to ViperCrest Sovereign Runtime
        envelope = self.build_vipercrest_envelope(evidence, cartridge=cartridge)
        executor = ViperCrestContractExecutor()
        auth_response = executor.execute(envelope)

        return evidence, auth_response


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for ViperCrest RPC Dispatcher."""
    parser = argparse.ArgumentParser(description="ViperCrest Typed RPC Dispatcher")
    parser.add_argument(
        "rpc_command",
        nargs="*",
        default=["eth_blockNumber"],
        help="RPC method or command (defaults to eth_blockNumber)",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_RPC_URL,
        help=f"Local RPC loopback endpoint URL (default: {DEFAULT_RPC_URL})",
    )
    parser.add_argument(
        "--cartridge",
        default="security",
        choices=["security", "legal", "logistics"],
        help="Target cartridge space for matrix evaluation",
    )
    args = parser.parse_args(argv)

    dispatcher = TypedRPCDispatcher(endpoint=args.endpoint)
    raw_command = " ".join(args.rpc_command)

    print(f"[*] ViperCrest RPC Dispatcher: evaluating '{raw_command}'...")
    print(f"[*] Target Endpoint: {args.endpoint}")

    try:
        evidence, auth_resp = dispatcher.dispatch(
            raw_command,
            endpoint_override=args.endpoint,
            cartridge=args.cartridge,
        )
    except RPCConnectionError as conn_err:
        print(f"\n[!] Connection Error: {conn_err}", file=sys.stderr)
        return 1
    except RPCError as rpc_err:
        print(f"\n[!] RPC Error: {rpc_err}", file=sys.stderr)
        return 1
    except ProtocolViolationError as proto_err:
        print(f"\n[!] Authority Protocol Breach: {proto_err}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"\n[!] Unexpected Error: {exc}", file=sys.stderr)
        return 2

    # Display evidence capture details
    print("\n" + "=" * 65)
    print("                 CAPTURED RPC EVIDENCE RECORD                     ")
    print("=" * 65)
    print(evidence.format_evidence_report())

    # Display authoritative ViperCrest runtime verification
    print("\n" + "=" * 65)
    print("            VIPERCREST AUTHORITATIVE RUNTIME SEAL                 ")
    print("=" * 65)
    print(f"Status:             {auth_resp.status}")
    print(f"Cartridge:          {auth_resp.cartridge_id}")
    print(f"Session ID:         {auth_resp.session_id}")
    print(f"Receipt Verified:   {auth_resp.session_receipt_verified}")
    print(f"F7 Uncertainty:     {'PRESERVED' if auth_resp.f7_uncertainty_preserved else 'RESOLVED'}")
    print(f"Epistemic Summary:  {auth_resp.epistemic_summary}")
    print("=" * 65)
    print("[+] RPC Evidence successfully routed and sealed through ViperCrest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
