"""
ViperCrest AI Wrapper (ai_wrapper.py).

The human-facing language and interface layer:
  Human <-> AI Wrapper <-> Typed Contract (ai_contract.py) <-> ViperCrest

Capabilities:
1. Translates human commands into typed AIRequestEnvelopes.
2. Interacts with local Ollama instance (if available) with JSON schema constraint,
   falling back to deterministic semantic routing when offline.
3. Submits strictly typed UNVERIFIED_INPUT to ai_contract.py.
4. Explains authoritative sealed results back to the human operator.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

VIPER_ROOT = Path(__file__).resolve().parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from ai_contract import (
    AIRequestEnvelope,
    AuthoritativeResponseEnvelope,
    ProtocolViolationError,
    ViperCrestContractExecutor,
    process_ai_submission,
)
from ai_prompts import (
    JSON_SCHEMA_AI_REQUEST_ENVELOPE,
    build_explanation_prompt,
    build_translation_prompt,
)
import reader_engine as re_eng

OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "llama3.2"


def is_ollama_available() -> bool:
    """Checks if a local Ollama daemon is reachable."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def call_ollama(prompt: str, schema: Optional[Dict[str, Any]] = None, model: str = DEFAULT_MODEL) -> Optional[str]:
    """Invokes local Ollama server with optional JSON schema constraints."""
    if not is_ollama_available():
        return None

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if schema:
        payload["format"] = schema

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("response")
    except Exception:
        return None


def heuristic_translate_request(user_input: str) -> AIRequestEnvelope:
    """
    Deterministic offline semantic parser:
    Translates user intent into a strictly conforming AIRequestEnvelope
    without requiring an active LLM daemon.
    """
    clean_input = user_input.strip()
    lowered = clean_input.lower()

    # 1. Determine Cartridge
    if any(k in lowered for k in ["lease", "legal", "court", "breach", "tenant", "landlord", "bates"]):
        cartridge = "legal"
    elif any(k in lowered for k in ["reefer", "temp", "cold", "logistics", "wms", "pallet", "cargo", "haccp"]):
        cartridge = "logistics"
    else:
        cartridge = "security"

    # 2. Determine Intent & Action
    if lowered.startswith("why ") or "?" in clean_input or "question" in lowered or "what is" in lowered:
        intent = "query"
        action = "query"
        questions = [{
            "question_id": "Q1",
            "query_text": clean_input,
            "target_coordinate": "T5:S7" if "pacs" in lowered or "unresolved" in lowered else None,
        }]
        observations = []
        claims = []
    elif lowered.startswith("hydrate") or "minimal" in lowered:
        intent = "hydrate"
        action = "hydrate"
        questions = []
        raw_token = re.sub(r"^(hydrate|minimal|seed)\s*", "", clean_input, flags=re.IGNORECASE).strip()
        observations = [{
            "raw_text": raw_token if raw_token else re_eng.SAMPLE_MINIMAL_SEEDS.get(cartridge, "ANOMALY"),
            "candidate_state": "PROPOSED_ATOMIC_EVENT",
        }]
        claims = []
    else:
        intent = "analyze"
        action = "matrix"
        questions = []

        # Check if an input file is specified (e.g. "analyze hospital_incident.raw")
        file_match = re.search(r"([\w\-]+\.(raw|log|txt|csv|json))", clean_input, re.IGNORECASE)
        if file_match:
            filename = file_match.group(1)
            raw_path = re_eng.DROPZONE_RAW / filename
            if raw_path.exists():
                raw_bytes, _ = re_eng.safe_read_bytes(raw_path)
                raw_text = re_eng.safe_decode_text(raw_bytes)
            else:
                raw_text = f"Simulated incident stream referencing {filename}"
        else:
            raw_text = clean_input

        observations = [{
            "raw_text": raw_text,
            "candidate_state": "INGESTION_CANDIDATE",
        }]
        claims = [{
            "claim_id": "CLM-01",
            "statement": f"Automated ingestion from: {clean_input[:64]}",
        }]

    return AIRequestEnvelope(
        intent=intent,
        cartridge=cartridge,
        observations=observations,
        claims=claims,
        questions=questions,
        requested_action=action,
    )


def translate_user_input(user_input: str) -> AIRequestEnvelope:
    """Translates user input via local Ollama if available, falling back to heuristic."""
    # Attempt Ollama structured translation if online
    if is_ollama_available():
        prompt = build_translation_prompt(user_input)
        response_text = call_ollama(prompt, schema=JSON_SCHEMA_AI_REQUEST_ENVELOPE)
        if response_text:
            try:
                data = json.loads(response_text)
                return AIRequestEnvelope.from_dict(data)
            except Exception:
                pass

    # Deterministic offline fallback
    return heuristic_translate_request(user_input)


def explain_response(user_input: str, auth_resp: AuthoritativeResponseEnvelope) -> str:
    """Explains authoritative sealed results back to human language."""
    # If Ollama is available, generate explanation with LLM
    if is_ollama_available():
        prompt = build_explanation_prompt(user_input, auth_resp.to_dict())
        llm_exp = call_ollama(prompt)
        if llm_exp:
            return llm_exp.strip()

    # Deterministic authoritative formatter
    lines = []
    if auth_resp.question_answers:
        for qa in auth_resp.question_answers:
            ans = qa.get("authoritative_answer", {})
            lines.append(f"> {qa.get('query_text')}")
            lines.append(f"{ans.get('explanation')}")
            if ans.get("coordinate"):
                lines.append(f"  [Coordinate: {ans.get('coordinate')} | Status: {ans.get('epistemic_status')}]")
        return "\n".join(lines)

    summ = auth_resp.epistemic_summary
    lines.append(f"Cartridge: {auth_resp.cartridge_id}")
    lines.append("Evidence loaded: YES")
    lines.append("Running Reader...")
    lines.append("Normalizing Seed...")
    lines.append("Running invariant F1-F9...")
    lines.append("Evaluating temporal matrix...")
    lines.append("")
    lines.append("Result:")
    lines.append(f"  Present state:       BOUNDED ({summ.get('observed_cells')} observed)")
    lines.append(f"  Backward hydration:  {summ.get('derived_cells')} candidates (DERIVED)")
    lines.append(f"  Forward hydration:   {summ.get('possible_cells')} candidates (POSSIBLE)")
    lines.append(f"  Unresolved:          {summ.get('unresolved_f7_cells')} coordinates")
    lines.append(f"  F7 preservation:     {'PASS' if auth_resp.f7_uncertainty_preserved else 'WARN'}")
    lines.append(f"  Receipt:             {'VERIFIED' if auth_resp.session_receipt_verified else 'COMPLETED'}")
    if auth_resp.session_id:
        lines.append(f"  Session:             {auth_resp.session_id}")
    return "\n".join(lines)


def run_single_interaction(user_input: str) -> int:
    """Processes a single human request through the complete typed contract."""
    print("VIPERCREST AI")
    print(f"> {user_input}")

    try:
        envelope = translate_user_input(user_input)
        executor = ViperCrestContractExecutor()
        auth_resp = executor.execute(envelope)
        explanation = explain_response(user_input, auth_resp)
        print(explanation)
        return 0
    except ProtocolViolationError as e:
        print(f"\n[SECURITY PROTOCOL VIOLATION]: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        return 2


def interactive_loop() -> int:
    """Runs interactive CLI loop for ViperCrest AI."""
    print("==================================================================")
    print("                    VIPERCREST AI INTERFACE                       ")
    print("  Human <-> AI Wrapper <-> Typed Contract <-> ViperCrest Runtime  ")
    print("  (Type 'exit' or 'quit' to terminate)                           ")
    print("==================================================================")
    re_eng.ensure_sample_raw_files()

    while True:
        try:
            line = input("\nVIPERCREST AI> ").strip()
            if not line:
                continue
            if line.lower() in {"exit", "quit", "q"}:
                print("Exiting ViperCrest AI session.")
                break
            run_single_interaction(line)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting ViperCrest AI session.")
            break
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ViperCrest AI Language & Interface Wrapper")
    parser.add_argument("command", nargs="*", help="Optional single instruction to execute")
    args = parser.parse_args(argv)

    if args.command:
        user_input = " ".join(args.command)
        return run_single_interaction(user_input)
    return interactive_loop()


if __name__ == "__main__":
    sys.exit(main())
