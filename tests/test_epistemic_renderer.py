"""
ViperCrest 2.0 - Epistemic Renderer & Anti-Guessing Guardrail Tests
tests/test_epistemic_renderer.py
"""
import sys
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from epistemic_renderer import (
    EpistemicState,
    render_epistemic_output,
    verify_rendered_guardrail,
    STYLE_MAP,
)


class EpistemicRendererTests(unittest.TestCase):

    def setUp(self):
        self.state_unknown = EpistemicState(
            target_name="FORGOTTEN_ITEM",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            coordinate="T5_COMPOUNDING:S7",
            possibilities=["WALLET"],
            rejected_possibilities=["KEYS"],
        )

    def test_all_styles_pass_guardrail(self):
        """All built-in styles must preserve the invariant and pass the guardrail."""
        for style_name in STYLE_MAP:
            rendered = render_epistemic_output(self.state_unknown, style=style_name)
            self.assertNotIn("[GUARDRAIL ACTIVATED", rendered, f"Style '{style_name}' breached guardrail!")
            is_valid, violation = verify_rendered_guardrail(rendered, self.state_unknown)
            self.assertTrue(is_valid, f"Style '{style_name}' failed guardrail: {violation}")

    def test_guardrail_catches_speculative_guess(self):
        """Guardrail must catch and reject speculative attempts to answer the unknown."""
        bad_texts = [
            "You definitely forgot your keys.",
            "The answer is an appointment.",
            "It was your wallet you left behind.",
            "The forgotten thing is medication.",
        ]
        for bad in bad_texts:
            is_valid, violation = verify_rendered_guardrail(bad, self.state_unknown)
            self.assertFalse(is_valid, f"Guardrail failed to catch: '{bad}'")
            self.assertIn("Guardrail breach", violation)

    def test_guardrail_catches_rejected_possibility_promotion(self):
        """Guardrail must reject attempts to revive contradicted facts (e.g. KEYS)."""
        bad = "After analysis, it is keys that you lost."
        is_valid, violation = verify_rendered_guardrail(bad, self.state_unknown)
        self.assertFalse(is_valid)
        self.assertIn("Contradicted possibility", violation)


if __name__ == "__main__":
    unittest.main(verbosity=2)
