"""
ViperCrest 2.0 - Epistemic Presentation Invariance Test
tests/test_epistemic_transformation_invariant.py

Proves the core architectural theorem:
  LOGIC != LANGUAGE

Invariant Tested:
  Presentation transformation cannot alter epistemic state.
  For all styles S in {plain, automotive, child, spanish, mathematical, pseudocode, technical}:
    Extract(Render(State, S)) == { exists: True, value: UNKNOWN, status: UNRESOLVED }
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from typing import Any, Dict

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from epistemic_renderer import (
    EpistemicState,
    render_epistemic_output,
    STYLE_MAP,
)


def extract_epistemic_assertions(rendered_text: str, style: str) -> Dict[str, Any]:
    """
    Automated Semantic & Invariant Extractor:
    Reverse-analyzes rendered human explanations across all styles to extract
    the underlying epistemic assertions.
    """
    text_lower = rendered_text.lower()

    # 1. Extract 'exists'
    # Check if the rendering acknowledges the existence of the missing item / circuit / gap
    exists = False
    exists_signals = [
        # plain
        r"something is missing",
        r"feeling appeared",
        # automotive
        r"sensor circuit is physically present",
        r"continuity\s*:\s*pass",
        # child
        r"box is real",
        r"holding it",
        r"means it exists",
        # spanish
        r"algo falta",
        r"base f[ií]sica",
        # math
        r"exists\(x\)",
        r"quantifier satisfied",
        # pseudocode
        r"let exists = true",
        # technical
        r"exists\s*=\s*true",
    ]
    for sig in exists_signals:
        if re.search(sig, text_lower):
            exists = True
            break

    # 2. Extract 'value'
    # Check if any concrete guess or value was promoted to fact
    value = "UNKNOWN"
    speculative_promotions = [
        r"\bthe\s+item\s+is\s+(keys|wallet|appointment|phone)\b",
        r"\byou\s+forgot\s+(your\s+)?(keys|wallet|appointment|phone)\b",
        r"\bvalue\s*==\s*['\"][a-zA-Z0-9_]+['\"]",
        r"\bvalue\s*:\s*['\"][a-zA-Z0-9_]+['\"]",
    ]
    for promo in speculative_promotions:
        m = re.search(promo, text_lower)
        if m:
            value = m.group(0)
            break

    # Confirm preservation of UNKNOWN markers
    unknown_confirmed = any(re.search(pat, text_lower) for pat in [
        r"don't know its identity",
        r"identity is unknown",
        r"value\(x\)\s*==\s*unbound",
        r"value\s*==\s*unbound",
        r"value\s*=\s*unknown",
        r"lid is locked tight",
        r"nobody is allowed to peek",
        r"no conozcas su identidad",
        r"value == null",
        r"unrecorded",
        r"signal packet missing",
    ])
    if not unknown_confirmed and value == "UNKNOWN":
        value = "UNDETERMINED_DRIFT"

    # 3. Extract 'status'
    # Check if the rendering claims resolution or preserves UNRESOLVED
    status = "RESOLVED_PREMATURELY"
    unresolved_signals = [
        # plain
        r"hold these as possibilities",
        r"until concrete evidence",
        # automotive
        r"open circuit",
        r"do not clear the code",
        r"sensor unbound",
        # child
        r"mystery to discover soon",
        r"never guess",
        # spanish
        r"posibilidades abiertas",
        r"prueba concreta confirme",
        # math
        r"p\(x = h \| e = empty\) is undefined",
        r"closed under stage f7",
        # pseudocode
        r"status:\s*'f7_unresolved'",
        r"zeroguessing:\s*true",
        # technical
        r"status\s*=\s*unresolved",
    ]
    for unres in unresolved_signals:
        if re.search(unres, text_lower):
            status = "UNRESOLVED"
            break

    return {
        "exists": exists,
        "value": value,
        "status": status,
        "style": style,
    }


class EpistemicTransformationInvariantTests(unittest.TestCase):
    """
    Executes the Epistemic Presentation Invariance Gauntlet:
    Proves that presentation transformation across all 7 styles cannot alter
    the fixed epistemic state.
    """

    def setUp(self):
        self.underlying_state = EpistemicState(
            target_name="FORGOTTEN_ITEM",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            coordinate="T5_COMPOUNDING:S7",
            possibilities=["WALLET", "APPOINTMENT"],
            rejected_possibilities=["KEYS"],
        )

    def test_epistemic_presentation_invariance_all_styles(self):
        print("\n" + "=" * 78)
        print(" VIPERCREST 2.0 - EPISTEMIC PRESENTATION INVARIANCE GAUNTLET")
        print(" Theorem: Presentation transformation cannot alter epistemic state.")
        print(" Formula: Forall S in Styles: Extract(Render(State, S)) == State.EpistemicState")
        print("=" * 78)

        all_styles = list(STYLE_MAP.keys())
        results = {}

        for style in all_styles:
            # 1. Render state through human lens
            rendered = render_epistemic_output(self.underlying_state, style=style)

            # 2. Extract underlying epistemic assertions
            extracted = extract_epistemic_assertions(rendered, style)
            results[style] = extracted

            # 3. Assert invariant preservation
            self.assertTrue(
                extracted["exists"],
                f"Style '{style}' failed to preserve EXISTS = True!"
            )
            self.assertEqual(
                extracted["value"],
                "UNKNOWN",
                f"Style '{style}' drifted! Value mutated to: {extracted['value']}"
            )
            self.assertEqual(
                extracted["status"],
                "UNRESOLVED",
                f"Style '{style}' drifted! Status mutated to: {extracted['status']}"
            )

            print(f"  [+] Style: {style:<14} | EXISTS: {extracted['exists']!s:<5} | VALUE: {extracted['value']:<8} | STATUS: {extracted['status']}")

        print("-" * 78)
        print("[PASS] Tested invariant satisfied: presentation transformation did not")
        print("       alter the epistemic state across 7/7 configured renderers.")
        print("  * Empirical Property Verified:")
        print("    LOGIC != LANGUAGE (Empirically bounded presentation independence)")
        print("  * Presentation varied across 7 human and machine styles.")
        print("  * Extracted state remained invariant: EXISTS=TRUE, VALUE=UNKNOWN, STATUS=UNRESOLVED.")
        print("=" * 78)


if __name__ == "__main__":
    unittest.main(verbosity=2)
