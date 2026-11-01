"""
ViperCrest Basic Grammar Schema v0.1 (grammar_schema.py).

The universal receiving grammar schema for ViperCrest:
- Positioned as a pure receiving schema, NOT an alteration to fixed F1-F9.
- Reduces ordinary language into entities, actions, properties, relationships,
  state, and time that ViperCrest can position across the 81-state matrix.
- Preserves full traceability (source_text, character offset position).
- Golden Invariant: "Grammar identifies what was expressed. It does not
  determine what that expression means or what the system should conclude."
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PrimitiveWordClass(str, Enum):
    NOUN = "NOUN"              # thing, person, place, concept -> ENTITY
    VERB = "VERB"              # action, occurrence, state     -> ACTION
    ADJECTIVE = "ADJECTIVE"    # property of an entity         -> PROPERTY
    ADVERB = "ADVERB"          # property of an action/prop    -> MODIFIER
    PRONOUN = "PRONOUN"        # reference to an entity        -> REFERENCE
    PREPOSITION = "PREPOSITION"# relationship between elements -> RELATION
    DETERMINER = "DETERMINER"  # specifies/qualifies an entity -> QUALIFIER
    CONJUNCTION = "CONJUNCTION"# connects elements             -> COMPOSITION
    NUMBER = "NUMBER"          # quantity/value                -> VALUE
    NEGATION = "NEGATION"      # reverses/asserts absence      -> POLARITY


class GrammarType(str, Enum):
    ENTITY = "ENTITY"
    ACTION = "ACTION"
    PROPERTY = "PROPERTY"
    RELATION = "RELATION"
    MODIFIER = "MODIFIER"
    VALUE = "VALUE"
    REFERENCE = "REFERENCE"
    POLARITY = "POLARITY"
    STATE = "STATE"
    TIME = "TIME"
    QUALIFIER = "QUALIFIER"


# Mapping from Primitive Word Class to Normalized Machine Vocabulary
WORD_CLASS_TO_GRAMMAR_TYPE: Dict[PrimitiveWordClass, GrammarType] = {
    PrimitiveWordClass.NOUN: GrammarType.ENTITY,
    PrimitiveWordClass.VERB: GrammarType.ACTION,
    PrimitiveWordClass.ADJECTIVE: GrammarType.PROPERTY,
    PrimitiveWordClass.ADVERB: GrammarType.MODIFIER,
    PrimitiveWordClass.PRONOUN: GrammarType.REFERENCE,
    PrimitiveWordClass.PREPOSITION: GrammarType.RELATION,
    PrimitiveWordClass.DETERMINER: GrammarType.QUALIFIER,
    PrimitiveWordClass.NUMBER: GrammarType.VALUE,
    PrimitiveWordClass.NEGATION: GrammarType.POLARITY,
}


@dataclass
class GrammarElement:
    """Traceable extracted grammar element carrying its exact source and offset."""
    type: str  # GrammarType
    value: str
    source_text: str
    position: int
    word_class: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "type": self.type,
            "value": self.value,
            "source_text": self.source_text,
            "position": self.position,
        }
        if self.word_class:
            d["word_class"] = self.word_class
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class GrammarRelation:
    """Directed relationship between extracted grammar elements."""
    source: str
    relation_type: str  # PROPERTY | PERFORMS | AFFECTS | RELATION | MODIFIER | VALUE | DESTINATION | DIRECTION
    target: str
    source_element: Optional[GrammarElement] = None
    target_element: Optional[GrammarElement] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "relation_type": self.relation_type,
            "target": self.target,
        }


@dataclass
class GrammarClause:
    """Single universal clause: [QUALIFIER] [PROPERTY] SUBJECT [ACTION] [MODIFIER] [OBJECT] [RELATION] [VALUE]."""
    subject: Optional[GrammarElement] = None
    predicate: Optional[GrammarElement] = None
    object: Optional[GrammarElement] = None
    qualifier: Optional[GrammarElement] = None
    property: Optional[GrammarElement] = None
    modifier: Optional[GrammarElement] = None
    relation: Optional[GrammarElement] = None
    value: Optional[GrammarElement] = None
    state: Optional[GrammarElement] = None
    time: Optional[GrammarElement] = None
    polarity: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        if self.subject:
            res["subject"] = self.subject.to_dict()
        if self.predicate:
            res["predicate"] = self.predicate.to_dict()
        if self.object:
            res["object"] = self.object.to_dict()
        if self.qualifier:
            res["qualifier"] = self.qualifier.to_dict()
        if self.property:
            res["property"] = self.property.to_dict()
        if self.modifier:
            res["modifier"] = self.modifier.to_dict()
        if self.relation:
            res["relation"] = self.relation.to_dict()
        if self.value:
            res["value"] = self.value.to_dict()
        if self.state:
            res["state"] = self.state.to_dict()
        if self.time:
            res["time"] = self.time.to_dict()
        if self.polarity:
            res["polarity"] = self.polarity
        return res


@dataclass
class StateTransitionPair:
    """Language as state transition data: T0 -> T+1."""
    entity: str
    t0_state: Optional[str]
    t1_state: Optional[str]
    action: Optional[str] = None
    direction: Optional[str] = None
    time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "t0_state": self.t0_state,
            "t1_state": self.t1_state,
            "action": self.action,
            "direction": self.direction,
            "time": self.time,
        }


@dataclass
class GrammarEnvelope:
    """Complete Basic Schema v0.1 container."""
    entities: List[GrammarElement] = field(default_factory=list)
    actions: List[GrammarElement] = field(default_factory=list)
    properties: List[GrammarElement] = field(default_factory=list)
    relations: List[GrammarRelation] = field(default_factory=list)
    modifiers: List[GrammarElement] = field(default_factory=list)
    values: List[GrammarElement] = field(default_factory=list)
    references: List[GrammarElement] = field(default_factory=list)
    qualifiers: List[GrammarElement] = field(default_factory=list)
    polarity: Optional[str] = None
    time: Optional[str] = None
    state: Optional[str] = None
    clauses: List[GrammarClause] = field(default_factory=list)
    transitions: List[StateTransitionPair] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grammar": {
                "entities": [e.to_dict() for e in self.entities],
                "actions": [a.to_dict() for a in self.actions],
                "properties": [p.to_dict() for p in self.properties],
                "relations": [r.to_dict() for r in self.relations],
                "modifiers": [m.to_dict() for m in self.modifiers],
                "values": [v.to_dict() for v in self.values],
                "references": [ref.to_dict() for ref in self.references],
                "qualifiers": [q.to_dict() for q in self.qualifiers],
                "polarity": self.polarity,
                "time": self.time,
                "state": self.state,
                "clauses": [c.to_dict() for c in self.clauses],
                "transitions": [t.to_dict() for t in self.transitions],
            }
        }


# =====================================================================
# DETERMINISTIC OFFLINE LEXICAL & GRAMMAR RESOLVER
# Zero-dependency, air-gapped tokenizer and parser
# =====================================================================

DETERMINERS = {"the", "a", "an", "this", "that", "these", "those", "every", "each", "all", "some", "any"}
PRONOUNS = {"it", "he", "she", "they", "we", "i", "you", "its", "their", "his", "her", "which", "what"}
PREPOSITIONS = {"in", "into", "to", "towards", "from", "at", "by", "for", "with", "about", "against", "between", "through", "during", "before", "after", "above", "below", "on", "off", "over", "under"}
CONJUNCTIONS = {"and", "but", "or", "nor", "so", "yet", "although", "because", "while", "if"}
NEGATIONS = {"not", "no", "never", "none", "neither", "n't", "without"}
TEMPORAL_WORDS = {"now", "today", "yesterday", "tomorrow", "before", "after", "soon", "later", "current", "currently", "immediately", "simultaneously"}
STATE_WORDS = {"nearby", "away", "open", "closed", "locked", "unlocked", "active", "idle", "degraded", "nominal", "failed", "offline", "online", "breached", "sealed"}

COMMON_ADJECTIVES = {
    "vulnerable", "secure", "critical", "compromised", "broken", "empty", "full",
    "unauthorized", "suspicious", "anomalous", "valid", "invalid", "safe", "unsafe",
    "external", "internal", "primary", "secondary", "large", "small", "high", "low",
    "zero", "unbounded", "cold", "warm", "hot", "tampered", "healthy", "clean",
}

COMMON_VERBS = {
    "failed", "fail", "fails",
    "entered", "enter", "enters",
    "opened", "open", "opens",
    "closed", "close", "closes",
    "moved", "move", "moves",
    "transferred", "transfer", "transfers",
    "breached", "breach", "breaches",
    "sent", "send", "sends",
    "received", "receive", "receives",
    "dropped", "drop", "drops",
    "started", "start", "starts",
    "stopped", "stop", "stops",
    "updated", "update", "updates",
    "exceeded", "exceed", "exceeds",
    "reverted", "revert", "reverts",
    "minted", "mint", "mints",
    "locked", "lock", "locks",
    "is", "was", "are", "were", "been", "being",
}

VERB_LEMMAS = {
    "failed": "fail", "fails": "fail", "failing": "fail",
    "entered": "enter", "enters": "enter", "entering": "enter",
    "opened": "open", "opens": "open", "opening": "open",
    "closed": "close", "closes": "close", "closing": "close",
    "moved": "move", "moves": "move", "moving": "move",
    "transferred": "transfer", "transfers": "transfer",
    "breached": "breach", "breaches": "breach",
    "sent": "send", "sends": "send", "sending": "send",
    "received": "receive", "receives": "receive",
    "dropped": "drop", "drops": "drop",
    "started": "start", "starts": "start",
    "stopped": "stop", "stops": "stop",
    "updated": "update", "updates": "update",
    "exceeded": "exceed", "exceeds": "exceed",
    "reverted": "revert", "reverts": "revert",
    "minted": "mint", "mints": "mint",
    "locked": "lock", "locks": "lock",
    "is": "be", "was": "be", "are": "be", "were": "be",
}

ADVERB_SUFFIXES = ("ly", "ward", "wards", "wise")


def classify_word(token: str) -> Tuple[PrimitiveWordClass, str]:
    """Classifies a word into its PrimitiveWordClass and produces its canonical lemma/value."""
    lowered = token.lower()

    if lowered in NEGATIONS:
        return PrimitiveWordClass.NEGATION, "NEGATIVE"
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", token) or re.fullmatch(r"0x[0-9a-fA-F]+", token):
        return PrimitiveWordClass.NUMBER, token
    if lowered in DETERMINERS:
        return PrimitiveWordClass.DETERMINER, lowered
    if lowered in PRONOUNS:
        return PrimitiveWordClass.PRONOUN, lowered
    if lowered in PREPOSITIONS:
        return PrimitiveWordClass.PREPOSITION, lowered
    if lowered in CONJUNCTIONS:
        return PrimitiveWordClass.CONJUNCTION, lowered
    if lowered in COMMON_ADJECTIVES or lowered.endswith("able") or lowered.endswith("ible") or lowered.endswith("ous"):
        return PrimitiveWordClass.ADJECTIVE, lowered
    if lowered in COMMON_VERBS or lowered in VERB_LEMMAS:
        return PrimitiveWordClass.VERB, VERB_LEMMAS.get(lowered, lowered)
    if any(lowered.endswith(sfx) for sfx in ADVERB_SUFFIXES) and len(lowered) > 3:
        return PrimitiveWordClass.ADVERB, lowered
    if lowered.endswith("ed") and len(lowered) > 4:
        # Probable past verb
        stem = lowered[:-2] if not lowered.endswith("eed") else lowered[:-1]
        return PrimitiveWordClass.VERB, stem

    # Default fallback: noun
    return PrimitiveWordClass.NOUN, lowered


def parse_basic_grammar(text: str) -> GrammarEnvelope:
    """
    Parses natural language text into the ViperCrest Basic Grammar Schema v0.1.
    Preserves element provenance, character offsets, relationships, and state transitions.
    """
    clean_text = text.strip()
    envelope = GrammarEnvelope()

    # Split into raw token spans with exact start positions
    token_spans: List[Tuple[str, int]] = []
    for match in re.finditer(r"\b[\w'\-\.]+\b", clean_text):
        token_spans.append((match.group(0), match.start()))

    if not token_spans:
        return envelope

    # 1. First Pass: Tag Primitive Word Classes & Normalize
    tagged_tokens: List[Tuple[GrammarElement, PrimitiveWordClass]] = []
    for word, pos in token_spans:
        word_class, lemma = classify_word(word)
        g_type = WORD_CLASS_TO_GRAMMAR_TYPE.get(word_class, GrammarType.ENTITY)
        
        # Check special temporal or state overrides
        lowered = word.lower()
        if lowered in TEMPORAL_WORDS:
            g_type = GrammarType.TIME
            envelope.time = lowered
        elif lowered in STATE_WORDS and word_class != PrimitiveWordClass.VERB:
            g_type = GrammarType.STATE
            envelope.state = lowered
        elif word_class == PrimitiveWordClass.NEGATION:
            envelope.polarity = "NEGATIVE"

        elem = GrammarElement(
            type=g_type.value,
            value=lemma,
            source_text=word,
            position=pos,
            word_class=word_class.value,
        )
        tagged_tokens.append((elem, word_class))

        # Add to categorical collections
        if g_type == GrammarType.ENTITY:
            envelope.entities.append(elem)
        elif g_type == GrammarType.ACTION:
            envelope.actions.append(elem)
        elif g_type == GrammarType.PROPERTY:
            envelope.properties.append(elem)
        elif g_type == GrammarType.MODIFIER:
            envelope.modifiers.append(elem)
        elif g_type == GrammarType.VALUE:
            envelope.values.append(elem)
        elif g_type == GrammarType.REFERENCE:
            envelope.references.append(elem)
        elif g_type == GrammarType.QUALIFIER:
            envelope.qualifiers.append(elem)

    # 2. Second Pass: Extract Structural Relationships
    # ENTITY --PROPERTY--> PROPERTY
    for prop in envelope.properties:
        # Find closest subsequent or preceding entity
        closest_entity = _find_closest(prop, envelope.entities)
        if closest_entity:
            envelope.relations.append(GrammarRelation(
                source=closest_entity.value,
                relation_type="PROPERTY",
                target=prop.value,
                source_element=closest_entity,
                target_element=prop,
            ))

    # ENTITY --PERFORMS--> ACTION
    # ACTION --AFFECTS--> ENTITY (OBJECT)
    # ACTION --MODIFIER--> MODIFIER
    for act in envelope.actions:
        preceding_entities = [e for e in envelope.entities if e.position < act.position]
        following_entities = [e for e in envelope.entities if e.position > act.position]

        if preceding_entities:
            subject_ent = preceding_entities[-1]
            envelope.relations.append(GrammarRelation(
                source=subject_ent.value,
                relation_type="PERFORMS",
                target=act.value,
                source_element=subject_ent,
                target_element=act,
            ))

        MOTION_VERBS = {"enter", "reach", "arrive", "exit", "approach", "leave"}
        if following_entities:
            object_ent = following_entities[0]
            rel_type = "DESTINATION" if act.value in MOTION_VERBS else "AFFECTS"
            envelope.relations.append(GrammarRelation(
                source=act.value,
                relation_type=rel_type,
                target=object_ent.value,
                source_element=act,
                target_element=object_ent,
            ))

        # Check for destination / prepositional relation
        for elem, w_cls in tagged_tokens:
            if w_cls == PrimitiveWordClass.PREPOSITION and elem.position > act.position:
                prep_following_ents = [e for e in envelope.entities if e.position > elem.position]
                if prep_following_ents:
                    dest_ent = prep_following_ents[0]
                    envelope.relations.append(GrammarRelation(
                        source=act.value,
                        relation_type="DESTINATION",
                        target=dest_ent.value,
                        source_element=act,
                        target_element=dest_ent,
                    ))

        # ACTION --MODIFIER--> MODIFIER
        closest_modifier = _find_closest(act, envelope.modifiers)
        if closest_modifier:
            envelope.relations.append(GrammarRelation(
                source=act.value,
                relation_type="MODIFIER",
                target=closest_modifier.value,
                source_element=act,
                target_element=closest_modifier,
            ))

    # 3. Third Pass: Assemble Clauses: [QUALIFIER] [PROPERTY] SUBJECT [ACTION] [MODIFIER] [OBJECT] [RELATION] [VALUE]
    clause = GrammarClause()
    if envelope.entities:
        clause.subject = envelope.entities[0]
        if len(envelope.entities) > 1:
            clause.object = envelope.entities[1]
    if envelope.actions:
        clause.predicate = envelope.actions[0]
    if envelope.qualifiers:
        clause.qualifier = envelope.qualifiers[0]
    if envelope.properties:
        clause.property = envelope.properties[0]
    if envelope.modifiers:
        clause.modifier = envelope.modifiers[0]
    if envelope.values:
        clause.value = envelope.values[0]
    if envelope.polarity:
        clause.polarity = envelope.polarity
    if envelope.time:
        for elem, _ in tagged_tokens:
            if elem.type == GrammarType.TIME.value:
                clause.time = elem
                break
    if envelope.state:
        for elem, _ in tagged_tokens:
            if elem.type == GrammarType.STATE.value:
                clause.state = elem
                break
    envelope.clauses.append(clause)

    # 4. Fourth Pass: State and Time Transitions (Language -> State Transition Data)
    # Check for motion / direction / temporal transitions (e.g. "The phone moved away" or "is nearby now")
    if envelope.entities:
        main_ent = envelope.entities[0].value
        lowered_text = clean_text.lower()
        if "nearby" in lowered_text and ("now" in lowered_text or "is" in lowered_text):
            envelope.state = "nearby"
            envelope.time = "now"
            envelope.transitions.append(StateTransitionPair(
                entity=main_ent,
                t0_state="nearby",
                t1_state="nearby",
                action=None,
                time="now",
            ))
        elif "moved" in lowered_text or "away" in lowered_text:
            envelope.transitions.append(StateTransitionPair(
                entity=main_ent,
                t0_state="nearby",
                t1_state="away",
                action="move",
                direction="away",
            ))

    return envelope


def _find_closest(target: GrammarElement, candidates: List[GrammarElement]) -> Optional[GrammarElement]:
    """Finds the nearest element by character offset."""
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(c.position - target.position))
