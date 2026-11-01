"""
Unit Tests for ViperCrest Basic Grammar Schema v0.1 (grammar_schema.py).

Verifies:
1. Primitive word classes collapse into normalized machine vocabulary.
2. The vulnerable bridge failed suddenly (Entity, Property, Action, Modifier).
3. The phone entered the room (Entity, Action, Destination Relation).
4. Minimal observation clause: Door opened.
5. State and time transitions:
   - The phone is nearby now (Entity, State, Time).
   - The phone moved away (State transition T0 -> T+1).
6. Traceability: exact source_text and character position preserved.
7. Complete basic schema envelope JSON output structure.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import grammar_schema as gs


class GrammarSchemaTests(unittest.TestCase):
    def test_01_primitive_classes_and_vocabulary_mapping(self):
        """Test 1: Verify primitive word classes map cleanly to normalized vocabulary."""
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.NOUN], gs.GrammarType.ENTITY)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.VERB], gs.GrammarType.ACTION)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.ADJECTIVE], gs.GrammarType.PROPERTY)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.ADVERB], gs.GrammarType.MODIFIER)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.PRONOUN], gs.GrammarType.REFERENCE)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.PREPOSITION], gs.GrammarType.RELATION)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.DETERMINER], gs.GrammarType.QUALIFIER)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.NUMBER], gs.GrammarType.VALUE)
        self.assertEqual(gs.WORD_CLASS_TO_GRAMMAR_TYPE[gs.PrimitiveWordClass.NEGATION], gs.GrammarType.POLARITY)

    def test_02_vulnerable_bridge_failed_suddenly(self):
        """Test 2: 'The vulnerable bridge failed suddenly.' produces exact entities and relations."""
        text = "The vulnerable bridge failed suddenly."
        envelope = gs.parse_basic_grammar(text)

        # Elements
        entity_values = [e.value for e in envelope.entities]
        self.assertIn("bridge", entity_values)

        prop_values = [p.value for p in envelope.properties]
        self.assertIn("vulnerable", prop_values)

        action_values = [a.value for a in envelope.actions]
        self.assertIn("fail", action_values)

        mod_values = [m.value for m in envelope.modifiers]
        self.assertIn("suddenly", mod_values)

        # Relationships
        rel_signatures = {(r.source, r.relation_type, r.target) for r in envelope.relations}
        self.assertIn(("bridge", "PROPERTY", "vulnerable"), rel_signatures)
        self.assertIn(("bridge", "PERFORMS", "fail"), rel_signatures)
        self.assertIn(("fail", "MODIFIER", "suddenly"), rel_signatures)

    def test_03_phone_entered_room(self):
        """Test 3: 'The phone entered the room.' extracts entities, action, and destination."""
        text = "The phone entered the room."
        envelope = gs.parse_basic_grammar(text)

        entity_vals = [e.value for e in envelope.entities]
        self.assertIn("phone", entity_vals)
        self.assertIn("room", entity_vals)

        action_vals = [a.value for a in envelope.actions]
        self.assertIn("enter", action_vals)

        rel_signatures = {(r.source, r.relation_type, r.target) for r in envelope.relations}
        self.assertIn(("phone", "PERFORMS", "enter"), rel_signatures)
        self.assertIn(("enter", "DESTINATION", "room"), rel_signatures)

    def test_04_minimal_clause_door_opened(self):
        """Test 4: 'Door opened.' parses as minimal subject + predicate clause."""
        text = "Door opened."
        envelope = gs.parse_basic_grammar(text)

        self.assertEqual(len(envelope.clauses), 1)
        clause = envelope.clauses[0]
        self.assertIsNotNone(clause.subject)
        self.assertIsNotNone(clause.predicate)

        self.assertEqual(clause.subject.type, "ENTITY")
        self.assertEqual(clause.subject.value, "door")
        self.assertEqual(clause.predicate.type, "ACTION")
        self.assertEqual(clause.predicate.value, "open")

    def test_05_state_and_time_nearby_now(self):
        """Test 5: 'The phone is nearby now.' extracts state and time."""
        text = "The phone is nearby now."
        envelope = gs.parse_basic_grammar(text)

        self.assertEqual(envelope.state, "nearby")
        self.assertEqual(envelope.time, "now")
        entity_vals = [e.value for e in envelope.entities]
        self.assertIn("phone", entity_vals)

        self.assertEqual(len(envelope.transitions), 1)
        tr = envelope.transitions[0]
        self.assertEqual(tr.entity, "phone")
        self.assertEqual(tr.t0_state, "nearby")
        self.assertEqual(tr.time, "now")

    def test_06_state_transition_moved_away(self):
        """Test 6: 'The phone moved away.' converts language into state transition data."""
        text = "The phone moved away."
        envelope = gs.parse_basic_grammar(text)

        self.assertEqual(len(envelope.transitions), 1)
        tr = envelope.transitions[0]
        self.assertEqual(tr.entity, "phone")
        self.assertEqual(tr.t0_state, "nearby")
        self.assertEqual(tr.t1_state, "away")
        self.assertEqual(tr.action, "move")
        self.assertEqual(tr.direction, "away")

    def test_07_traceability_source_offsets(self):
        """Test 7: Verify character offset positions and source_text are preserved."""
        text = "The bridge failed suddenly."
        envelope = gs.parse_basic_grammar(text)

        bridge_elem = next(e for e in envelope.entities if e.value == "bridge")
        self.assertEqual(bridge_elem.source_text, "bridge")
        self.assertEqual(bridge_elem.position, 4)

        fail_elem = next(a for a in envelope.actions if a.value == "fail")
        self.assertEqual(fail_elem.source_text, "failed")
        self.assertEqual(fail_elem.position, 11)

    def test_08_schema_json_envelope_format(self):
        """Test 8: Verify to_dict() conforms to the exact frozen v0.1 schema structure."""
        text = "The vulnerable bridge failed suddenly."
        envelope = gs.parse_basic_grammar(text)
        d = envelope.to_dict()

        self.assertIn("grammar", d)
        g = d["grammar"]
        self.assertIn("entities", g)
        self.assertIn("actions", g)
        self.assertIn("properties", g)
        self.assertIn("relations", g)
        self.assertIn("modifiers", g)
        self.assertIn("values", g)
        self.assertIn("references", g)
        self.assertIn("qualifiers", g)
        self.assertIn("polarity", g)
        self.assertIn("time", g)
        self.assertIn("state", g)
        self.assertIn("clauses", g)
        self.assertIn("transitions", g)


if __name__ == "__main__":
    unittest.main()
