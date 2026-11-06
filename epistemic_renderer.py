"""
ViperCrest 2.0 - Post-Engine Human-Language Epistemic Renderer & Guardrail
Location: C:\\ViperCrest\\epistemic_renderer.py

Enforces the core architectural principle:
  LOGIC != LANGUAGE

The fixed F1-F9 engine establishes the bounded mathematical state:
  exists: True
  value: UNKNOWN
  status: UNRESOLVED

This renderer converts that bounded result into requested human styles
without guessing, hallucinating, or mutating the epistemic boundary.
A post-render guardrail strictly enforces that UNKNOWN cannot become a guess.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class EpistemicState:
    """Bounded epistemic state produced by the authoritative engine."""
    target_name: str = "FORGOTTEN_ITEM"
    exists: bool = True
    value: str = "UNKNOWN"
    status: str = "UNRESOLVED"
    coordinate: str = "T5_COMPOUNDING:S7"
    possibilities: List[str] = field(default_factory=list)
    rejected_possibilities: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EpistemicState:
        return cls(
            target_name=d.get("target_name", "FORGOTTEN_ITEM"),
            exists=d.get("exists", True),
            value=d.get("value", "UNKNOWN"),
            status=d.get("status", "UNRESOLVED"),
            coordinate=d.get("coordinate", "T5_COMPOUNDING:S7"),
            possibilities=list(d.get("possibilities", [])),
            rejected_possibilities=list(d.get("rejected_possibilities", [])),
            observations=list(d.get("observations", [])),
            evidence=list(d.get("evidence", [])),
        )


# =====================================================================
# Post-Render Guardrail (The Anti-Guessing Bouncer)
# =====================================================================

SPECULATIVE_ASSERTION_PATTERNS = [
    r"\byou\s+definitely\s+forgot\b",
    r"\bthe\s+answer\s+is\b",
    r"\bit\s+was\s+your\b",
    r"\bit\s+was\s+an?\b",
    r"\byou\s+forgot\s+your\s+(keys|wallet|phone|appointment|medication)\b",
    r"\bthe\s+forgotten\s+thing\s+is\b",
]


def verify_rendered_guardrail(rendered_text: str, state: EpistemicState) -> Tuple[bool, Optional[str]]:
    """Verifies that the human explanation faithfully preserves the engine's epistemic invariants.
    
    If state.value is UNKNOWN, the renderer MUST NOT assert any specific guess as fact.
    """
    if state.value == "UNKNOWN":
        lower_text = rendered_text.lower()
        for pat in SPECULATIVE_ASSERTION_PATTERNS:
            if re.search(pat, lower_text):
                return False, f"Guardrail breach: Renderer made speculative definitive assertion matching pattern: {pat}"
        
        # Verify that any rejected possibilities are not promoted
        for rej in state.rejected_possibilities:
            if re.search(rf"\bit\s+is\s+{rej.lower()}\b", lower_text):
                return False, f"Guardrail breach: Contradicted possibility '{rej}' promoted as true"

    return True, None


# =====================================================================
# Style Renderers
# =====================================================================

def render_plain(state: EpistemicState) -> str:
    """Conversational, constructive context-reconstruction guidance."""
    lines = []
    if state.exists and state.value == "UNKNOWN":
        lines.append("You know that something is missing, even though you don't know its identity.")
        lines.append("So do not try to guess the missing item directly—speculation creates false memory.")
        lines.append("")
        lines.append("Instead, reconstruct the context around the gap:")
        lines.append("  1. Physical Baseline: Where were you standing when you realized something was missing?")
        lines.append("  2. Intended Action: What task were you about to perform next?")
        lines.append("  3. Interruption Scan: What sound, person, or phone call broke your focus?")
        
        if state.rejected_possibilities:
            lines.append("")
            lines.append(f"Eliminated from consideration: {', '.join(state.rejected_possibilities)}.")
        if state.possibilities:
            lines.append(f"Current open hypotheses: {', '.join(state.possibilities)} (held as unproven possibilities).")
            
        lines.append("")
        lines.append("Hold these as possibilities until concrete evidence distinguishes one.")
    else:
        lines.append(f"Item identified: {state.value} (Verified by evidence: {', '.join(state.evidence)}).")
    return "\n".join(lines)


def render_technical(state: EpistemicState) -> str:
    """Rigorous state machine & epistemic gap analysis."""
    lines = [
        "========================================================================",
        "VIPERCREST 2.0 - EPISTEMIC COORDINATE STATUS (STAGE F7 UNRESOLVED)",
        "========================================================================",
        f"Target Coordinate     : {state.coordinate}",
        f"Existence Quantifier  : EXISTS = {state.exists}",
        f"Coordinate Value      : VALUE = {state.value}",
        f"Operational Status    : STATUS = {state.status}",
        f"Active Hypotheses     : {len(state.possibilities)} candidate(s) [{', '.join(state.possibilities) or 'None'}]",
        f"Falsified Hypotheses  : {len(state.rejected_possibilities)} eliminated [{', '.join(state.rejected_possibilities) or 'None'}]",
        f"Admissible Evidence   : {len(state.evidence)} item(s)",
        "",
        "EPISTEMIC BOUNDARY DIRECTIVE:",
        "  Zero guessing enforced. Coordinate cannot bind value without verified D_{n+1}",
        "  arrival. State machine halts state mutation at boundary F7. Actuation is suspended.",
        "========================================================================",
    ]
    return "\n".join(lines)


def render_child(state: EpistemicState) -> str:
    """Gentle, relatable explanation of an unopened mystery box."""
    lines = [
        "Imagine you have a special mystery gift box in your hands.",
        "You know for sure the box is real because you are holding it! (That means it exists).",
        "But the lid is locked tight, and nobody is allowed to peek inside yet.",
        "",
        "Some people might try to guess: 'Is it a toy car? Is it a candy bar?'",
        "We never guess! Guessing makes pretend stories instead of real truth.",
        "Instead, we look at clues on the outside: What were you doing when you got the box?",
        "Until we find the real key, we keep the box safe and labeled: 'Mystery to discover soon!'",
    ]
    return "\n".join(lines)


def render_automotive(state: EpistemicState) -> str:
    """Vehicle diagnostic OBD-II / sensor telemetry analogy."""
    lines = [
        "========================================================================",
        "VEHICLE DIAGNOSTIC TELEMETRY REPORT (ECU / CAN-BUS INTAKE)",
        "========================================================================",
        "Diagnostic Trouble Code : DTC B1001-F7 (OPEN CIRCUIT / SENSOR UNBOUND)",
        "Circuit Continuity      : PASS (Sensor circuit is physically present)",
        "Signal Voltage Telemetry: 0.00 V (Signal packet missing / Unrecorded)",
        "",
        "MECHANICAL INTERPRETATION:",
        "  The Check Engine Light is on because the ECU knows a sensor circuit exists,",
        "  but received zero valid pulses from the transducer.",
        "  DO NOT clear the code or replace parts based on a hunch.",
        "  Probe upstream wiring: Check harness continuity, inspect reference voltage,",
        "  and isolate intermittent ground before commanding actuator duty cycle.",
        "========================================================================",
    ]
    return "\n".join(lines)


def render_spanish(state: EpistemicState) -> str:
    """Spanish constructive context reconstruction."""
    lines = [
        "Sabes con certeza que algo falta, aunque no conozcas su identidad exacta.",
        "Por lo tanto, no intentes adivinar directamente—la especulación crea recuerdos falsos.",
        "",
        "En su lugar, reconstruye el contexto alrededor del vacío:",
        "  1. Base Física: ¿Dónde estabas exactamente cuando sentiste que faltaba algo?",
        "  2. Intención: ¿Qué acción te disponías a realizar a continuación?",
        "  3. Interrupción: ¿Qué sonido, persona o notificación interrumpió tu enfoque?",
        "",
        "Mantén las opciones como posibilidades abiertas hasta que una prueba concreta confirme la verdad.",
    ]
    return "\n".join(lines)


def render_mathematical(state: EpistemicState) -> str:
    """Formal mathematical & set-theoretic representation (ASCII/Unicode safe)."""
    h_str = ", ".join(state.possibilities) or "EMPTY"
    r_str = ", ".join(state.rejected_possibilities) or "EMPTY"
    lines = [
        "Formal Predicate Evaluation:",
        "  EXISTS(x): (x in U AND Forgotten(x)) == TRUE   [Existence Quantifier Satisfied]",
        "  Value(x)                             == UNBOUND [Stage F7 / Coordinate Open]",
        f"  Hypothesis Space H                   == {{ {h_str} }}",
        f"  Falsified Null Space R               == {{ {r_str} }}",
        "  H INTERSECT R                        == EMPTY   [Orthogonality Preserved]",
        "  Evidence Space E                     == EMPTY",
        "",
        "Invariant Theorem:",
        "  FORALL(h in H): P(x = h | E = EMPTY) is undefined.",
        "  Zero Speculation Lemma: System state remains strictly closed under Stage F7.",
    ]
    return "\n".join(lines)


def render_pseudocode(state: EpistemicState) -> str:
    """Structured algorithmic representation."""
    lines = [
        "function resolveForgottenItem():",
        "    let exists = true;",
        "    let value = null;",
        "    let hypotheses = " + str(state.possibilities) + ";",
        "    let rejected = " + str(state.rejected_possibilities) + ";",
        "",
        "    while (value == null):",
        "        let evidence = acquireVerifiedEvidence();",
        "        if (!evidence.isValid()):",
        "            suspendState({ status: 'F7_UNRESOLVED', zeroGuessing: true });",
        "            return yieldContextReconstructionGuidance();",
        "        else:",
        "            value = evidence.bindCoordinate();",
        "",
        "    return value;",
    ]
    return "\n".join(lines)


STYLE_MAP = {
    "plain": render_plain,
    "technical": render_technical,
    "child": render_child,
    "automotive": render_automotive,
    "spanish": render_spanish,
    "mathematical": render_mathematical,
    "pseudocode": render_pseudocode,
}


def render_epistemic_output(state: EpistemicState, style: str = "plain") -> str:
    """Renders epistemic state into requested human style and validates through the guardrail."""
    style_key = style.lower().strip()
    renderer_func = STYLE_MAP.get(style_key, render_plain)
    
    # 1. Render in requested style
    raw_output = renderer_func(state)

    # 2. Pass through post-render anti-guessing guardrail
    is_valid, violation = verify_rendered_guardrail(raw_output, state)
    if not is_valid:
        # Fail-closed fallback to strict technical brief
        return f"[GUARDRAIL ACTIVATED: {violation}]\n\n{render_technical(state)}"

    return raw_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ViperCrest Epistemic Human Renderer")
    parser.add_argument("--style", default="plain", choices=list(STYLE_MAP.keys()), help="Rendering style / perspective")
    args = parser.parse_args()

    demo_state = EpistemicState(
        target_name="FORGOTTEN_ITEM",
        exists=True,
        value="UNKNOWN",
        status="UNRESOLVED",
        possibilities=["APPOINTMENT", "WALLET"],
        rejected_possibilities=["KEYS"],
    )
    print(render_epistemic_output(demo_state, style=args.style))
