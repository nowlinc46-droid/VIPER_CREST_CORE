"""
ViperCrest AI Prompt Templates and Structured Output Schemas (ai_prompts.py).

Guarantees that local AI models (such as Ollama) conform to the typed
AIRequestEnvelope contract and never attempt to usurp ViperCrest authority.
"""
from __future__ import annotations

import json
from typing import Any, Dict

# Ollama JSON-Schema-Constrained Structured Output Schema
JSON_SCHEMA_AI_REQUEST_ENVELOPE: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["analyze", "hydrate", "query", "explain"],
        },
        "cartridge": {
            "type": "string",
            "enum": ["security", "legal", "logistics"],
        },
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "seed_key": {"type": ["string", "null"]},
                    "raw_text": {"type": "string"},
                    "candidate_state": {"type": "string"},
                },
                "required": ["raw_text"],
            },
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "statement": {"type": "string"},
                    "source_reference": {"type": ["string", "null"]},
                },
                "required": ["claim_id", "statement"],
            },
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "query_text": {"type": "string"},
                    "target_coordinate": {"type": ["string", "null"]},
                },
                "required": ["question_id", "query_text"],
            },
        },
        "requested_action": {
            "type": "string",
            "enum": ["matrix", "hydrate", "query", "explain"],
        },
    },
    "required": ["intent", "cartridge", "requested_action"],
}


SYSTEM_PROMPT_STRUCTURED_INPUT = """You are the ViperCrest AI Interface Assistant.
Your sole responsibility is to translate human requests into a strictly validated JSON AIRequestEnvelope.

STRICT PROTOCOL BOUNDARIES:
1. You may ONLY propose raw claims, observation candidates, and questions.
2. You must NEVER self-assign or claim epistemic status (e.g., you CANNOT declare anything as OBSERVED, DERIVED, POSSIBLE, CONTRADICTED, or UNRESOLVED).
3. All authoritative state classification and mathematical hydration are performed exclusively by ViperCrest.
4. Output ONLY valid JSON conforming to the schema. Do not add conversational text or markdown code fences outside JSON.
"""

SYSTEM_PROMPT_EXPLAIN_SEALED_RESULTS = """You are the ViperCrest AI Explainer.
Your job is to read the authoritative, sealed verification output from ViperCrest and explain it to the human operator in clear, professional language.

ABSOLUTE TRUTH INVARIANTS:
1. Ground truth is established solely by ViperCrest's cryptographic receipt and F1-F9 execution.
2. If a coordinate is marked UNRESOLVED in F7, explain that ViperCrest strictly refuses to speculate or invent missing facts without physical evidence.
3. Distinguish clearly between:
   - OBSERVED: Directly verified by physical telemetry/record.
   - DERIVED: Causally bounded predecessor baselines.
   - POSSIBLE: Non-factual reachability candidate.
   - UNRESOLVED: Preserved under Stage F7 uncertainty.
4. Never promise or assert facts that are not present in the sealed output.
"""


def build_translation_prompt(user_text: str, default_cartridge: str = "security") -> str:
    """Constructs prompt for translating user text into an AIRequestEnvelope."""
    return f"""{SYSTEM_PROMPT_STRUCTURED_INPUT}

User Input:
"{user_text}"

Suggested Cartridge: {default_cartridge}

Return ONLY the JSON envelope conforming to the schema."""


def build_explanation_prompt(user_query: str, authoritative_response: Dict[str, Any]) -> str:
    """Constructs prompt for explaining authoritative ViperCrest results to the user."""
    return f"""{SYSTEM_PROMPT_EXPLAIN_SEALED_RESULTS}

Human Question:
"{user_query}"

Authoritative ViperCrest Response:
{json.dumps(authoritative_response, indent=2)}

Explain the result clearly and concisely:"""
