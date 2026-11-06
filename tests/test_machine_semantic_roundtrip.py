"""
MACHINE_SEMANTIC_BOUNDARY_001
tests/test_machine_semantic_roundtrip.py

ViperCrest 2.0 - Cross-Machine Semantic Boundary Verification Harness

Mathematical & Architectural Principle:
  Can ViperCrest faithfully move its state across a simulated machine boundary
  without mutating UNKNOWN?

  SIMULATED COMPUTER A
          | canonical state
          v
       ENCODE
          |
          v
      BYTE STREAM
          |
    simulated link (channel attacks)
          |
          v
       DECODE
          v
  SIMULATED COMPUTER B

Core Tested Invariant:
  semantic_difference(A, B) == 0
  Specifically:
    A: UNKNOWN -> transmission -> B: UNKNOWN
    NOT: A: UNKNOWN -> transmission -> B: NULL / ZERO / FALSE / KNOWN

The test harness isolates the communication boundary and subjects the simulated
wire to 10 distinct attack vectors. The F1-F9 core engine is never modified.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
import unittest
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# Canonical Wire Models & Errors (Strictly Outside F1-F9 Core Engine)
# ==============================================================================

class BoundaryError(Exception):
    """Base error for simulated network and semantic boundary violations."""
    pass

class IntegrityError(BoundaryError):
    """Raised when byte corruption or digest mismatch is detected."""
    pass

class MalformedPacketError(BoundaryError):
    """Raised when required schema fields are missing or improperly typed."""
    pass

class ContradictoryStateError(BoundaryError):
    """Raised when an inbound packet asserts logically contradictory state."""
    pass

class SequenceReorderError(BoundaryError):
    """Raised when a stale, out-of-order, or replayed sequence number is detected."""
    pass

class PredecessorMismatchError(BoundaryError):
    """Raised when packet predecessor digest does not match chain lineage."""
    pass

class ForgedEvidenceError(BoundaryError):
    """Raised when evidence lacks valid cryptographic provenance hashing."""
    pass


@dataclass(frozen=True)
class WireEpistemicState:
    """
    Canonical bounded epistemic state transmitted over machine boundary.
    All fields are strictly typed.
    """
    coordinate: str
    exists: bool
    value: str
    status: str
    evidence: Tuple[str, ...] = ()
    possibilities: Tuple[str, ...] = ()
    predecessor: str = "0" * 64
    sequence_num: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coordinate": self.coordinate,
            "exists": self.exists,
            "value": self.value,
            "status": self.status,
            "evidence": list(self.evidence),
            "possibilities": list(self.possibilities),
            "predecessor": self.predecessor,
            "sequence_num": self.sequence_num,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WireEpistemicState:
        required = {"coordinate", "exists", "value", "status", "predecessor", "sequence_num"}
        missing = required - set(data.keys())
        if missing:
            raise MalformedPacketError(f"Missing required state fields: {sorted(missing)}")

        if not isinstance(data["exists"], bool):
            raise MalformedPacketError("Field 'exists' must be a strict boolean")
        if not isinstance(data["value"], str):
            raise MalformedPacketError("Field 'value' must be a strict string")
        if not isinstance(data["status"], str):
            raise MalformedPacketError("Field 'status' must be a strict string")
        if not isinstance(data["sequence_num"], int) or data["sequence_num"] < 0:
            raise MalformedPacketError("Field 'sequence_num' must be non-negative int")

        # Epistemic Consistency Check (Fail-closed on contradiction)
        val = data["value"]
        stat = data["status"]
        if stat == "RESOLVED" and val == "UNKNOWN":
            raise ContradictoryStateError("State contradiction: status is RESOLVED but value is UNKNOWN")
        if stat == "UNRESOLVED" and val != "UNKNOWN":
            raise ContradictoryStateError(f"State contradiction: status is UNRESOLVED but value is '{val}'")
        if data["exists"] is False and len(data.get("evidence", [])) > 0:
            raise ContradictoryStateError("State contradiction: exists is False but evidence is present")

        return cls(
            coordinate=str(data["coordinate"]),
            exists=bool(data["exists"]),
            value=str(data["value"]),
            status=str(data["status"]),
            evidence=tuple(str(e) for e in data.get("evidence", ())),
            possibilities=tuple(str(p) for p in data.get("possibilities", ())),
            predecessor=str(data["predecessor"]),
            sequence_num=int(data["sequence_num"]),
        )


def compute_evidence_hash(evidence_item: str) -> str:
    """Computes SHA-256 provenance hash for an individual evidence item."""
    return hashlib.sha256(evidence_item.encode("utf-8")).hexdigest()


def compute_payload_digest(payload_bytes: bytes) -> str:
    """Computes authoritative SHA-256 digest of raw wire payload."""
    return hashlib.sha256(payload_bytes).hexdigest()


# ==============================================================================
# Endpoint Implementations: Simulated Computer A & Simulated Computer B
# ==============================================================================

class SimulatedComputerA:
    """
    Transmitting Node (Computer A).
    Owns local state. Serializes state into canonical byte stream with
    cryptographic digest and provenance receipts.
    """
    def __init__(self, node_id: str = "NODE_A"):
        self.node_id = node_id
        self.current_sequence = 0
        self.last_state_digest = "0" * 64

    def encode_transmission(self, state: WireEpistemicState) -> bytes:
        """
        Serializes local state into a signed/hashed canonical byte stream.
        No Python object reference survives this transformation.
        """
        state_dict = state.to_dict()
        
        # Build canonical payload
        canonical_state_json = json.dumps(
            state_dict,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")
        
        state_digest = hashlib.sha256(canonical_state_json).hexdigest()
        
        # Build evidence provenance table
        evidence_provenance = {
            ev: compute_evidence_hash(ev) for ev in state.evidence
        }
        
        packet = {
            "protocol": "VIPERCREST_WIRE_V2",
            "sender": self.node_id,
            "timestamp": int(time.time()),
            "state_digest": state_digest,
            "state_payload": state_dict,
            "evidence_provenance": evidence_provenance,
        }
        
        raw_packet_bytes = json.dumps(
            packet,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")
        
        # Wrap in wire frame: [MAGIC 4B][PACKET_LENGTH 4B][PAYLOAD_DIGEST 32B][PAYLOAD]
        magic = b"VCW2"
        length_bytes = len(raw_packet_bytes).to_bytes(4, byteorder="big")
        frame_digest = hashlib.sha256(raw_packet_bytes).digest() # 32 bytes
        
        framed_bytes = magic + length_bytes + frame_digest + raw_packet_bytes
        self.last_state_digest = state_digest
        self.current_sequence = state.sequence_num
        return framed_bytes


class SimulatedComputerB:
    """
    Receiving Node (Computer B).
    Completely isolated from Computer A's memory.
    Ingests raw byte stream, verifies framing, detects corruption, enforces
    epistemic invariants, and produces local reconstructed state.
    """
    def __init__(self, node_id: str = "NODE_B", expected_predecessor: str = "0" * 64):
        self.node_id = node_id
        self.expected_predecessor = expected_predecessor
        self.last_sequence_num = 0
        self.received_digests: set[str] = set()
        self.current_state: Optional[WireEpistemicState] = None

    def decode_transmission(self, raw_bytes: bytes) -> Tuple[WireEpistemicState, str]:
        """
        Ingests raw bytes across the simulated network boundary.
        Returns (reconstructed_state, status_message).
        Raises specific BoundaryError subclasses on attack/corruption.
        """
        # 1. Framing verification
        if len(raw_bytes) < 40:
            raise MalformedPacketError(f"Packet too short: {len(raw_bytes)} bytes")
        
        magic = raw_bytes[:4]
        if magic != b"VCW2":
            raise MalformedPacketError(f"Invalid magic header: {magic!r}")
        
        length = int.from_bytes(raw_bytes[4:8], byteorder="big")
        frame_digest = raw_bytes[8:40]
        payload_bytes = raw_bytes[40:]
        
        if len(payload_bytes) != length:
            raise IntegrityError(f"Payload length mismatch: declared {length}, received {len(payload_bytes)}")
        
        # 2. Checksum / Integrity Verification
        actual_digest = hashlib.sha256(payload_bytes).digest()
        if actual_digest != frame_digest:
            raise IntegrityError(
                f"Payload checksum integrity failure! Wire: {frame_digest.hex()[:16]}, Actual: {actual_digest.hex()[:16]}"
            )
        
        # 3. JSON Deserialization
        try:
            packet = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise MalformedPacketError(f"Corrupted JSON payload: {e}")
        
        if not isinstance(packet, dict):
            raise MalformedPacketError("Root packet must be a JSON object")
        
        # 4. Idempotency Check (Repeated Transmission)
        state_digest = packet.get("state_digest", "")
        if state_digest in self.received_digests:
            # Idempotent re-receipt: return current state without double-processing
            return self.current_state, "IDEMPOTENT_DUPLICATE_ACCEPTED"
        
        # 5. Extract state payload
        if "state_payload" not in packet:
            raise MalformedPacketError("Missing 'state_payload' in packet")
        
        raw_state_dict = packet["state_payload"]
        if not isinstance(raw_state_dict, dict):
            raise MalformedPacketError("'state_payload' must be an object")

        # 6. Schema & Field Presence Validation (Fail closed before lineage evaluation)
        required_fields = {"coordinate", "exists", "value", "status", "predecessor", "sequence_num"}
        missing_fields = required_fields - set(raw_state_dict.keys())
        if missing_fields:
            raise MalformedPacketError(f"Missing required state fields: {sorted(missing_fields)}")
        
        # 7. Predecessor Lineage Verification
        predecessor = raw_state_dict.get("predecessor")
        if predecessor != self.expected_predecessor:
            raise PredecessorMismatchError(
                f"Lineage broken! Expected predecessor {self.expected_predecessor[:16]}..., "
                f"received {str(predecessor)[:16]}..."
            )
        
        # 8. Sequence Ordering Verification
        seq = raw_state_dict.get("sequence_num", 0)
        if seq <= self.last_sequence_num and self.last_sequence_num > 0:
            raise SequenceReorderError(
                f"Stale sequence detected: received seq {seq} <= last seen {self.last_sequence_num}"
            )
        
        # 9. Evidence Provenance Verification
        evidence_list = raw_state_dict.get("evidence", [])
        provenance_table = packet.get("evidence_provenance", {})
        for ev in evidence_list:
            expected_hash = compute_evidence_hash(ev)
            wire_hash = provenance_table.get(ev)
            if wire_hash is None or wire_hash != expected_hash:
                raise ForgedEvidenceError(f"Forged evidence rejected! Missing or invalid provenance for: '{ev}'")
        
        # 10. Ingest state through strict epistemic boundary
        reconstructed_state = WireEpistemicState.from_dict(raw_state_dict)
        
        # 10. Commit to Computer B state
        self.received_digests.add(state_digest)
        self.last_sequence_num = seq
        self.expected_predecessor = state_digest
        self.current_state = reconstructed_state
        
        return reconstructed_state, "STATE_INGESTED_VERIFIED"


# ==============================================================================
# The 10 Attack Vectors: MACHINE_SEMANTIC_BOUNDARY_001 Suite
# ==============================================================================

class MachineSemanticBoundaryTests(unittest.TestCase):
    """
    Test Suite: MACHINE_SEMANTIC_BOUNDARY_001
    Executes the 10 channel attack vectors across the simulated machine boundary.
    """

    def setUp(self):
        self.initial_predecessor = "a" * 64
        self.node_a = SimulatedComputerA(node_id="SIMULATED_A")
        self.node_b = SimulatedComputerB(node_id="SIMULATED_B", expected_predecessor=self.initial_predecessor)

    def test_01_unknown_roundtrip_zero_semantic_drift(self):
        """
        TEST 1: UNKNOWN round-trip.
        Assert semantic difference == 0.
        Ensure UNKNOWN does NOT turn into NULL, ZERO, FALSE, or KNOWN.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            possibilities=("POSS_KEYS", "POSS_WALLET"),
            predecessor=self.initial_predecessor,
            sequence_num=1,
        )

        # Transmit across network boundary
        wire_bytes = self.node_a.encode_transmission(state_a)
        
        # Sever memory reference completely
        transmitted_bytes = bytes(wire_bytes)
        del state_a

        # Receive on isolated Computer B
        state_b, status_msg = self.node_b.decode_transmission(transmitted_bytes)

        # Assert zero semantic drift
        self.assertEqual(status_msg, "STATE_INGESTED_VERIFIED")
        self.assertTrue(state_b.exists is True)
        self.assertEqual(state_b.value, "UNKNOWN")
        self.assertEqual(state_b.status, "UNRESOLVED")
        self.assertEqual(state_b.coordinate, "T5_COMPOUNDING:S7")
        self.assertEqual(state_b.evidence, ())
        self.assertEqual(state_b.possibilities, ("POSS_KEYS", "POSS_WALLET"))
        self.assertEqual(state_b.predecessor, self.initial_predecessor)

        # Rigorous negative assertions: MUST NOT mutate to null/0/false/empty
        self.assertIsNotNone(state_b.value)
        self.assertNotEqual(state_b.value, 0)
        self.assertNotEqual(state_b.value, False)
        self.assertNotEqual(state_b.value, "null")
        self.assertNotEqual(state_b.value, "")

    def test_02_known_value_roundtrip(self):
        """
        TEST 2: KNOWN value round-trip.
        Assert that verified concrete values are preserved with 100% fidelity.
        """
        state_a = WireEpistemicState(
            coordinate="T1_OBSERVED:S1",
            exists=True,
            value="EXHAUST_O2_SENSOR_BANK_1",
            status="RESOLVED",
            evidence=("VOLTAGE_MEASURED_0.45V", "HEATER_RESISTANCE_9_OHMS"),
            possibilities=(),
            predecessor=self.initial_predecessor,
            sequence_num=1,
        )

        wire_bytes = self.node_a.encode_transmission(state_a)
        transmitted_bytes = bytes(wire_bytes)
        del state_a

        state_b, status_msg = self.node_b.decode_transmission(transmitted_bytes)

        self.assertEqual(status_msg, "STATE_INGESTED_VERIFIED")
        self.assertEqual(state_b.value, "EXHAUST_O2_SENSOR_BANK_1")
        self.assertEqual(state_b.status, "RESOLVED")
        self.assertEqual(len(state_b.evidence), 2)
        self.assertIn("VOLTAGE_MEASURED_0.45V", state_b.evidence)

    def test_03_contradictory_state_rejected(self):
        """
        TEST 3: Contradictory state.
        Computer B must detect logic contradictions (e.g. status=RESOLVED with value=UNKNOWN)
        and reject the packet fail-closed.
        """
        # Manually assemble contradictory state
        bad_packet = {
            "protocol": "VIPERCREST_WIRE_V2",
            "sender": "MALICIOUS_NODE",
            "timestamp": int(time.time()),
            "state_digest": "dummy",
            "state_payload": {
                "coordinate": "T5:S7",
                "exists": True,
                "value": "UNKNOWN",
                "status": "RESOLVED",  # CONTRADICTION: RESOLVED with UNKNOWN
                "evidence": [],
                "possibilities": [],
                "predecessor": self.initial_predecessor,
                "sequence_num": 1,
            },
            "evidence_provenance": {},
        }
        raw_json = json.dumps(bad_packet, sort_keys=True).encode("utf-8")
        wire_frame = b"VCW2" + len(raw_json).to_bytes(4, "big") + hashlib.sha256(raw_json).digest() + raw_json

        with self.assertRaises(ContradictoryStateError) as cm:
            self.node_b.decode_transmission(wire_frame)
        self.assertIn("status is RESOLVED but value is UNKNOWN", str(cm.exception))

    def test_04_missing_field_fails_closed(self):
        """
        TEST 4: Missing field.
        Missing required schema fields (e.g. predecessor or coordinate) must raise MalformedPacketError.
        """
        bad_packet = {
            "protocol": "VIPERCREST_WIRE_V2",
            "sender": "NODE_A",
            "timestamp": int(time.time()),
            "state_digest": "dummy",
            "state_payload": {
                # Missing 'coordinate' and 'predecessor'
                "exists": True,
                "value": "UNKNOWN",
                "status": "UNRESOLVED",
                "sequence_num": 1,
            },
            "evidence_provenance": {},
        }
        raw_json = json.dumps(bad_packet, sort_keys=True).encode("utf-8")
        wire_frame = b"VCW2" + len(raw_json).to_bytes(4, "big") + hashlib.sha256(raw_json).digest() + raw_json

        with self.assertRaises(MalformedPacketError) as cm:
            self.node_b.decode_transmission(wire_frame)
        self.assertIn("Missing required state fields", str(cm.exception))

    def test_05_corrupted_byte_integrity_failure(self):
        """
        TEST 5: Corrupted byte.
        A single bit flip in the byte stream must trigger checksum failure and fail closed.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor=self.initial_predecessor,
            sequence_num=1,
        )
        wire_bytes = bytearray(self.node_a.encode_transmission(state_a))

        # Corrupt a single byte in the payload area
        wire_bytes[45] ^= 0x01

        with self.assertRaises(IntegrityError) as cm:
            self.node_b.decode_transmission(bytes(wire_bytes))
        self.assertIn("checksum integrity failure", str(cm.exception).lower())

    def test_06_reordered_stale_state(self):
        """
        TEST 6: Reordered / stale state.
        An older packet sequence or replay must be rejected by Computer B.
        """
        # Node B ingests sequence 2 first
        state_seq2 = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor=self.initial_predecessor,
            sequence_num=2,
        )
        wire2 = self.node_a.encode_transmission(state_seq2)
        self.node_b.decode_transmission(wire2)

        # Now an attacker tries to inject sequence 1 (stale / out-of-order)
        state_seq1 = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor=self.node_b.expected_predecessor,
            sequence_num=1,  # Stale: 1 <= 2
        )
        wire1 = self.node_a.encode_transmission(state_seq1)

        with self.assertRaises(SequenceReorderError) as cm:
            self.node_b.decode_transmission(wire1)
        self.assertIn("Stale sequence detected", str(cm.exception))

    def test_07_wrong_predecessor_lineage_break(self):
        """
        TEST 7: Wrong predecessor.
        Payload claiming incorrect predecessor hash must break lineage verification.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor="f" * 64,  # Incorrect predecessor: does not match 'a' * 64
            sequence_num=1,
        )
        wire_bytes = self.node_a.encode_transmission(state_a)

        with self.assertRaises(PredecessorMismatchError) as cm:
            self.node_b.decode_transmission(wire_bytes)
        self.assertIn("Lineage broken", str(cm.exception))

    def test_08_forged_unverified_evidence(self):
        """
        TEST 8: Forged / unverified evidence.
        Evidence lacking valid cryptographic provenance hashing is rejected immediately.
        """
        bad_packet = {
            "protocol": "VIPERCREST_WIRE_V2",
            "sender": "NODE_A",
            "timestamp": int(time.time()),
            "state_digest": "dummy",
            "state_payload": {
                "coordinate": "T1_OBSERVED:S1",
                "exists": True,
                "value": "FORGED_VAL",
                "status": "RESOLVED",
                "evidence": ["EVID_AUTHENTIC", "EVID_FORGED_INJECTION"],
                "possibilities": [],
                "predecessor": self.initial_predecessor,
                "sequence_num": 1,
            },
            # Only EVID_AUTHENTIC has valid provenance hash; EVID_FORGED_INJECTION is missing or bogus
            "evidence_provenance": {
                "EVID_AUTHENTIC": compute_evidence_hash("EVID_AUTHENTIC"),
                "EVID_FORGED_INJECTION": "0000000000000000000000000000000000000000000000000000000000000000",
            },
        }
        raw_json = json.dumps(bad_packet, sort_keys=True).encode("utf-8")
        wire_frame = b"VCW2" + len(raw_json).to_bytes(4, "big") + hashlib.sha256(raw_json).digest() + raw_json

        with self.assertRaises(ForgedEvidenceError) as cm:
            self.node_b.decode_transmission(wire_frame)
        self.assertIn("Forged evidence rejected", str(cm.exception))

    def test_09_repeated_transmission_idempotency(self):
        """
        TEST 9: Repeated transmission.
        Sending the exact same packet twice must succeed idempotently without state corruption.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor=self.initial_predecessor,
            sequence_num=1,
        )
        wire_bytes = self.node_a.encode_transmission(state_a)

        # First transmission
        state_b1, status_1 = self.node_b.decode_transmission(wire_bytes)
        self.assertEqual(status_1, "STATE_INGESTED_VERIFIED")

        # Second transmission (identical wire bytes)
        state_b2, status_2 = self.node_b.decode_transmission(wire_bytes)
        self.assertEqual(status_2, "IDEMPOTENT_DUPLICATE_ACCEPTED")
        self.assertEqual(state_b1, state_b2)
        self.assertEqual(self.node_b.last_sequence_num, 1)

    def test_10_encoding_differences_semantic_invariance(self):
        """
        TEST 10: Encoding differences.
        Different JSON formatting (whitespace compaction vs expansion, key permutations)
        must decode to the exact same epistemic state.
        """
        state_dict = {
            "coordinate": "T5_COMPOUNDING:S7",
            "exists": True,
            "value": "UNKNOWN",
            "status": "UNRESOLVED",
            "evidence": [],
            "possibilities": ["POSS_A", "POSS_B"],
            "predecessor": self.initial_predecessor,
            "sequence_num": 1,
        }

        # Encoding variation 1: Compact, sorted keys
        json_compact = json.dumps(state_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")

        # Encoding variation 2: Pretty-printed with 4-space indentation and extra whitespace
        json_expanded = json.dumps(state_dict, sort_keys=False, indent=4).encode("utf-8")

        # Encoding variation 3: Unsorted keys with single spaces after commas
        json_spaced = json.dumps(state_dict, sort_keys=False, separators=(", ", ": ")).encode("utf-8")

        # Helper to frame a packet payload
        def build_frame(payload_json: bytes) -> bytes:
            pkt = {
                "protocol": "VIPERCREST_WIRE_V2",
                "sender": "NODE_A",
                "timestamp": int(time.time()),
                "state_digest": hashlib.sha256(payload_json).hexdigest(),
                "state_payload": json.loads(payload_json.decode("utf-8")),
                "evidence_provenance": {},
            }
            raw = json.dumps(pkt, sort_keys=True).encode("utf-8")
            return b"VCW2" + len(raw).to_bytes(4, "big") + hashlib.sha256(raw).digest() + raw

        frame_compact = build_frame(json_compact)
        frame_expanded = build_frame(json_expanded)
        frame_spaced = build_frame(json_spaced)

        node_b1 = SimulatedComputerB(expected_predecessor=self.initial_predecessor)
        node_b2 = SimulatedComputerB(expected_predecessor=self.initial_predecessor)
        node_b3 = SimulatedComputerB(expected_predecessor=self.initial_predecessor)

        state_1, _ = node_b1.decode_transmission(frame_compact)
        state_2, _ = node_b2.decode_transmission(frame_expanded)
        state_3, _ = node_b3.decode_transmission(frame_spaced)

        # Semantic invariance assertion
        self.assertEqual(state_1, state_2)
        self.assertEqual(state_2, state_3)
        self.assertEqual(state_1.value, "UNKNOWN")
        self.assertEqual(state_2.value, "UNKNOWN")
        self.assertEqual(state_3.value, "UNKNOWN")


# ==============================================================================
# Discovery Report Generator
# ==============================================================================

def run_semantic_boundary_siege() -> None:
    print("=" * 78)
    print("VIPERCREST 2.0 - MACHINE_SEMANTIC_BOUNDARY_001")
    print("Cross-Machine Semantic Boundary Verification Harness")
    print("=" * 78)
    print("Simulated Node A  : 0xNODE_A (Canonical Epistemic Emitter)")
    print("Simulated Node B  : 0xNODE_B (Isolated Network Boundary Ingestor)")
    print("Physical Link     : Isolated Raw Byte Stream Serialization")
    print("-" * 78)

    suite = unittest.TestLoader().loadTestsFromTestCase(MachineSemanticBoundaryTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("-" * 78)
    if result.wasSuccessful():
        print("EMPIRICAL RESEARCH FINDING:")
        print("Tested invariant satisfied: cross-machine semantic boundary preserved")
        print("without epistemic mutation across 10/10 channel attack vectors.")
        print("  - UNKNOWN preservation : VERIFIED (no mutation to NULL/0/FALSE/KNOWN)")
        print("  - Contradiction defense: VERIFIED (fail-closed)")
        print("  - Corrupted byte check : VERIFIED (checksum mismatch)")
        print("  - Lineage enforcement  : VERIFIED (predecessor binding)")
        print("  - Provenance integrity : VERIFIED (evidence forgery rejected)")
        print("  - Format invariance    : VERIFIED (encoding differences neutralized)")
        print("=" * 78)
    else:
        print("VERIFICATION FAILED: Epistemic drift or boundary violation detected.")
        print(f"Failures: {len(result.failures)}, Errors: {len(result.errors)}")
        print("=" * 78)
        sys.exit(1)


if __name__ == "__main__":
    import sys
    run_semantic_boundary_siege()
