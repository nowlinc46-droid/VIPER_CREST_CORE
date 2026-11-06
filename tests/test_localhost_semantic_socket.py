"""
MACHINE_SEMANTIC_SOCKET_002
tests/test_localhost_semantic_socket.py

ViperCrest 2.0 - Localhost TCP Socket Semantic Boundary Verification Harness

Mathematical & Architectural Principle:
  Can the canonical ViperCrest epistemic state survive serialization,
  actual localhost TCP transport, reception, validation, and reconstruction
  across real operating system process boundaries without epistemic mutation?

  PROCESS A / CLIENT
  Canonical ViperCrest State
          |
          v
       ENCODE
          |
          v
        bytes
          |
          v
  TCP socket -> 127.0.0.1:<ephemeral port> -> TCP socket
          |
          v
        bytes
          |
          v
       DECODE
          |
          v
  PROCESS B / SERVER
  Reconstructed ViperCrest State
          |
          v
  COMPARE WITH ORIGINAL

Crucial Invariant:
  semantic_difference(State_A, State_B) == 0
  Survives Windows TCP stream fragmentation without mutating UNKNOWN
  into NULL, ZERO, FALSE, or speculative guesses.

Test ID: MACHINE_SEMANTIC_SOCKET_002
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import socket
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

from tests.test_machine_semantic_roundtrip import (
    BoundaryError,
    ContradictoryStateError,
    ForgedEvidenceError,
    IntegrityError,
    MalformedPacketError,
    PredecessorMismatchError,
    SequenceReorderError,
    SimulatedComputerA,
    SimulatedComputerB,
    WireEpistemicState,
    compute_evidence_hash,
)


# ==============================================================================
# TCP Streaming Framing Utilities (Continuous Stream Handling)
# ==============================================================================

def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """
    Reads exactly `num_bytes` from a TCP socket stream, looping until
    the full byte quota is accumulated or the connection is severed.
    Handles TCP segment fragmentation natively.
    """
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            raise ConnectionResetError("TCP socket connection closed prematurely during stream recv")
        buf.extend(chunk)
    return bytes(buf)


def recv_wire_frame(sock: socket.socket) -> bytes:
    """
    Reads a complete VCW2 wire frame from the continuous TCP stream:
    [MAGIC 4B][LENGTH 4B][PAYLOAD_DIGEST 32B][PAYLOAD NB]
    Total header: 40 bytes.
    """
    header = recv_exact(sock, 40)
    magic = header[:4]
    if magic != b"VCW2":
        raise MalformedPacketError(f"Invalid frame magic header over TCP: {magic!r}")
    length = int.from_bytes(header[4:8], byteorder="big")
    payload = recv_exact(sock, length)
    return header + payload


def send_response(sock: socket.socket, resp: Dict[str, Any]) -> None:
    """Sends a framed response packet back over the TCP socket."""
    raw = json.dumps(resp, sort_keys=True, separators=(",", ":")).encode("utf-8")
    magic = b"VCR2" # ViperCrest Response v2
    length = len(raw).to_bytes(4, byteorder="big")
    digest = hashlib.sha256(raw).digest()
    sock.sendall(magic + length + digest + raw)


def recv_response(sock: socket.socket) -> Dict[str, Any]:
    """Reads and validates a framed response packet from the TCP socket."""
    header = recv_exact(sock, 40)
    magic = header[:4]
    if magic != b"VCR2":
        raise MalformedPacketError(f"Invalid response magic header: {magic!r}")
    length = int.from_bytes(header[4:8], byteorder="big")
    payload = recv_exact(sock, length)
    expected_digest = header[8:40]
    actual_digest = hashlib.sha256(payload).digest()
    if actual_digest != expected_digest:
        raise IntegrityError("TCP response checksum integrity verification failure")
    return json.loads(payload.decode("utf-8"))


# ==============================================================================
# Process B: Dedicated Localhost TCP Server Worker
# ==============================================================================

def run_tcp_server_worker(ready_queue: mp.Queue, shutdown_event: mp.Event, initial_predecessor: str) -> None:
    """
    Entry point for isolated Server Process B.
    Binds to 127.0.0.1 on an OS-assigned ephemeral port (port 0).
    Communicates strictly through TCP socket calls.
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(10)
    server_sock.settimeout(1.0)

    computer_b = SimulatedComputerB(
        node_id="PROCESS_B_SERVER",
        expected_predecessor=initial_predecessor
    )

    # Signal ready with assigned ephemeral port
    ready_queue.put(port)

    while not shutdown_event.is_set():
        try:
            conn, addr = server_sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break

        conn.settimeout(5.0)
        try:
            # Check for control packet or wire frame
            peek = conn.recv(8, socket.MSG_PEEK)
            if not peek:
                conn.close()
                continue
            if peek.startswith(b"VC_STOP"):
                conn.recv(7)
                conn.sendall(b"OK_STOPPED")
                conn.close()
                break

            # Read full framed transmission from TCP stream
            wire_frame = recv_wire_frame(conn)

            # Ingest through strict epistemic boundary
            try:
                state_b, status_msg = computer_b.decode_transmission(wire_frame)
                resp = {
                    "status": "SUCCESS",
                    "verdict": status_msg,
                    "state": state_b.to_dict(),
                    "expected_predecessor": computer_b.expected_predecessor,
                    "last_sequence_num": computer_b.last_sequence_num,
                }
            except BoundaryError as be:
                resp = {
                    "status": "ERROR",
                    "error_type": be.__class__.__name__,
                    "error_message": str(be),
                    "expected_predecessor": computer_b.expected_predecessor,
                    "last_sequence_num": computer_b.last_sequence_num,
                }

            # Return response over TCP
            send_response(conn, resp)
        except Exception as e:
            try:
                err_resp = {
                    "status": "ERROR",
                    "error_type": e.__class__.__name__,
                    "error_message": str(e),
                }
                send_response(conn, err_resp)
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    server_sock.close()


# ==============================================================================
# MACHINE_SEMANTIC_SOCKET_002 Test Suite
# ==============================================================================

class LocalhostSemanticSocketTests(unittest.TestCase):
    """
    Test Suite: MACHINE_SEMANTIC_SOCKET_002
    Exercises the real localhost TCP networking boundary across two OS processes.
    """
    server_process: mp.Process
    server_port: int
    initial_predecessor: str = "a" * 64
    shutdown_event: mp.Event

    @classmethod
    def setUpClass(cls):
        ctx = mp.get_context("spawn")
        ready_queue = ctx.Queue()
        cls.shutdown_event = ctx.Event()

        cls.server_process = ctx.Process(
            target=run_tcp_server_worker,
            args=(ready_queue, cls.shutdown_event, cls.initial_predecessor),
            daemon=True
        )
        cls.server_process.start()

        # Wait for ephemeral port assignment
        try:
            cls.server_port = ready_queue.get(timeout=10.0)
        except Exception as e:
            cls.server_process.terminate()
            raise RuntimeError(f"Server process failed to bind and report port: {e}")

        # Initialize Client A
        cls.node_a = SimulatedComputerA(node_id="PROCESS_A_CLIENT")
        cls.current_predecessor = cls.initial_predecessor

    @classmethod
    def tearDownClass(cls):
        # Gracefully shut down server process
        cls.shutdown_event.set()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", cls.server_port))
            sock.sendall(b"VC_STOP")
            sock.close()
        except Exception:
            pass
        cls.server_process.join(timeout=3.0)
        if cls.server_process.is_alive():
            cls.server_process.terminate()

    def _send_over_tcp(self, raw_bytes: bytes) -> Dict[str, Any]:
        """Client helper: connects, transmits bytes, and receives framed response."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.server_port))
        try:
            sock.sendall(raw_bytes)
            resp = recv_response(sock)
            return resp
        finally:
            sock.close()

    def test_01_unknown_state_tcp_roundtrip(self):
        """
        [1] UNKNOWN state over TCP:
        A -> TCP socket -> 127.0.0.1 -> TCP socket -> B
        Verifies:
          EXISTS=TRUE
          VALUE=UNKNOWN
          STATUS=UNRESOLVED
          Zero semantic drift; value is not NULL/0/FALSE/guess.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            possibilities=("POSS_KEYS", "POSS_WALLET"),
            predecessor=self.current_predecessor,
            sequence_num=1,
        )

        wire_bytes = self.node_a.encode_transmission(state_a)
        resp = self._send_over_tcp(wire_bytes)

        self.assertEqual(resp["status"], "SUCCESS")
        self.assertEqual(resp["verdict"], "STATE_INGESTED_VERIFIED")

        state_b = resp["state"]
        self.assertTrue(state_b["exists"] is True)
        self.assertEqual(state_b["value"], "UNKNOWN")
        self.assertEqual(state_b["status"], "UNRESOLVED")
        self.assertEqual(state_b["coordinate"], "T5_COMPOUNDING:S7")
        self.assertEqual(state_b["evidence"], [])
        self.assertEqual(state_b["possibilities"], ["POSS_KEYS", "POSS_WALLET"])
        self.assertEqual(state_b["predecessor"], self.current_predecessor)

        # Invariant negative checks: UNKNOWN must not mutate to null/0/false
        self.assertIsNotNone(state_b["value"])
        self.assertNotEqual(state_b["value"], 0)
        self.assertNotEqual(state_b["value"], False)
        self.assertNotEqual(state_b["value"], "null")
        self.assertNotEqual(state_b["value"], "")

        # Advance local predecessor tracker to reflect server's lineage
        LocalhostSemanticSocketTests.current_predecessor = resp["expected_predecessor"]

    def test_02_known_state_tcp_roundtrip(self):
        """
        [2] KNOWN state over TCP:
        A -> TCP socket -> 127.0.0.1 -> TCP socket -> B
        Verifies exact value and cryptographic evidence are preserved.
        """
        state_a = WireEpistemicState(
            coordinate="T1_OBSERVED:S1",
            exists=True,
            value="EXHAUST_O2_SENSOR_BANK_1",
            status="RESOLVED",
            evidence=("VOLTAGE_MEASURED_0.45V", "HEATER_RESISTANCE_9_OHMS"),
            possibilities=(),
            predecessor=self.current_predecessor,
            sequence_num=2,
        )

        wire_bytes = self.node_a.encode_transmission(state_a)
        LocalhostSemanticSocketTests.last_valid_seq2_bytes = bytes(wire_bytes)
        resp = self._send_over_tcp(wire_bytes)

        self.assertEqual(resp["status"], "SUCCESS")
        self.assertEqual(resp["verdict"], "STATE_INGESTED_VERIFIED")

        state_b = resp["state"]
        self.assertEqual(state_b["value"], "EXHAUST_O2_SENSOR_BANK_1")
        self.assertEqual(state_b["status"], "RESOLVED")
        self.assertEqual(len(state_b["evidence"]), 2)
        self.assertIn("VOLTAGE_MEASURED_0.45V", state_b["evidence"])

        LocalhostSemanticSocketTests.current_predecessor = resp["expected_predecessor"]

    def test_03_integrity_corrupted_frame_rejected(self):
        """
        [3] Integrity over TCP:
        Corrupted frame byte must be detected and rejected fail-closed.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor=self.current_predecessor,
            sequence_num=3,
        )
        wire_bytes = bytearray(self.node_a.encode_transmission(state_a))

        # Flip a bit in the payload portion
        wire_bytes[45] ^= 0x01

        resp = self._send_over_tcp(bytes(wire_bytes))
        self.assertEqual(resp["status"], "ERROR")
        self.assertEqual(resp["error_type"], "IntegrityError")
        self.assertIn("checksum integrity failure", resp["error_message"].lower())

    def test_04_contradictory_state_rejected(self):
        """
        [4] Contradictory state over TCP:
        VALUE=UNKNOWN + STATUS=RESOLVED transmitted over TCP must be rejected.
        """
        bad_packet = {
            "protocol": "VIPERCREST_WIRE_V2",
            "sender": "PROCESS_A_CLIENT",
            "timestamp": int(time.time()),
            "state_digest": "dummy",
            "state_payload": {
                "coordinate": "T5:S7",
                "exists": True,
                "value": "UNKNOWN",
                "status": "RESOLVED",  # CONTRADICTION
                "evidence": [],
                "possibilities": [],
                "predecessor": self.current_predecessor,
                "sequence_num": 3,
            },
            "evidence_provenance": {},
        }
        raw_json = json.dumps(bad_packet, sort_keys=True).encode("utf-8")
        wire_frame = b"VCW2" + len(raw_json).to_bytes(4, "big") + hashlib.sha256(raw_json).digest() + raw_json

        resp = self._send_over_tcp(wire_frame)
        self.assertEqual(resp["status"], "ERROR")
        self.assertEqual(resp["error_type"], "ContradictoryStateError")
        self.assertIn("status is RESOLVED but value is UNKNOWN", resp["error_message"])

    def test_05_lineage_wrong_predecessor_rejected(self):
        """
        [5] Lineage over TCP:
        Payload with wrong predecessor hash breaks chain verification.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor="f" * 64,  # Wrong predecessor
            sequence_num=3,
        )
        wire_bytes = self.node_a.encode_transmission(state_a)

        resp = self._send_over_tcp(wire_bytes)
        self.assertEqual(resp["status"], "ERROR")
        self.assertEqual(resp["error_type"], "PredecessorMismatchError")
        self.assertIn("Lineage broken", resp["error_message"])

    def test_06_sequence_stale_and_idempotent_handling(self):
        """
        [6] Sequence & Idempotency over TCP:
        - Stale sequence number (seq 1 <= last seq 2) rejected with SequenceReorderError.
        - Exact duplicate transmission handled idempotently.
        """
        # Part A: Stale sequence
        stale_state = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            predecessor=self.current_predecessor,
            sequence_num=1,  # Stale: Server is at sequence 2
        )
        stale_bytes = self.node_a.encode_transmission(stale_state)
        resp_stale = self._send_over_tcp(stale_bytes)

        self.assertEqual(resp_stale["status"], "ERROR")
        self.assertEqual(resp_stale["error_type"], "SequenceReorderError")
        self.assertIn("Stale sequence detected", resp_stale["error_message"])

        # Part B: Duplicate transmission of the identical valid sequence 2 frame
        wire_seq2 = self.last_valid_seq2_bytes
        resp_dup = self._send_over_tcp(wire_seq2)

        self.assertEqual(resp_dup["status"], "SUCCESS")
        self.assertEqual(resp_dup["verdict"], "IDEMPOTENT_DUPLICATE_ACCEPTED")

    def test_07_fragmentation_stream_reconstruction(self):
        """
        [7] Fragmentation over TCP:
        Intentionally send one complete message using multiple fragmented socket writes
        (e.g., 7-byte chunks with sleep delays).
        Ensures Server B's stream reader reconstructs exactly one complete frame.
        """
        state_a = WireEpistemicState(
            coordinate="T5_COMPOUNDING:S7",
            exists=True,
            value="UNKNOWN",
            status="UNRESOLVED",
            evidence=(),
            possibilities=("POSS_FRAGMENTATION_TEST",),
            predecessor=self.current_predecessor,
            sequence_num=3,
        )

        wire_bytes = self.node_a.encode_transmission(state_a)

        # Open socket and fragment the transmission across multiple TCP writes
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(("127.0.0.1", self.server_port))
        try:
            chunk_size = 7
            for i in range(0, len(wire_bytes), chunk_size):
                chunk = wire_bytes[i:i + chunk_size]
                sock.sendall(chunk)
                time.sleep(0.001) # Force operating system TCP segment boundary

            # Read response from server
            resp = recv_response(sock)
        finally:
            sock.close()

        self.assertEqual(resp["status"], "SUCCESS")
        self.assertEqual(resp["verdict"], "STATE_INGESTED_VERIFIED")

        state_b = resp["state"]
        self.assertEqual(state_b["value"], "UNKNOWN")
        self.assertEqual(state_b["status"], "UNRESOLVED")
        self.assertEqual(state_b["possibilities"], ["POSS_FRAGMENTATION_TEST"])
        self.assertEqual(state_b["sequence_num"], 3)


# ==============================================================================
# Discovery Report Generator
# ==============================================================================

def run_localhost_socket_siege() -> None:
    print("=" * 78)
    print("VIPERCREST 2.0 - MACHINE_SEMANTIC_SOCKET_002")
    print("Localhost TCP Socket Semantic Boundary Verification Harness")
    print("=" * 78)
    print("Process A (Client) : Canonical ViperCrest Emitter (Independent OS Process)")
    print("Process B (Server) : Isolated TCP Server Worker (Independent OS Process)")
    print("Network Transport  : Windows Localhost TCP Stack (127.0.0.1:<ephemeral>)")
    print("-" * 78)

    suite = unittest.TestLoader().loadTestsFromTestCase(LocalhostSemanticSocketTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("-" * 78)
    if result.wasSuccessful():
        print("EMPIRICAL RESEARCH FINDING:")
        print("The canonical ViperCrest epistemic state survived serialization, actual")
        print("localhost TCP transport, reception, validation, and reconstruction")
        print("under the tested conditions across 7/7 criteria:")
        print("  [1] UNKNOWN state roundtrip : VERIFIED (no mutation to NULL/0/FALSE/guess)")
        print("  [2] KNOWN state roundtrip   : VERIFIED (exact value + evidence preserved)")
        print("  [3] Integrity failure check : VERIFIED (corrupted frame rejected fail-closed)")
        print("  [4] Contradiction defense   : VERIFIED (RESOLVED+UNKNOWN rejected)")
        print("  [5] Chain lineage check     : VERIFIED (predecessor binding enforced)")
        print("  [6] Sequence & Idempotency  : VERIFIED (stale rejected, duplicate idempotent)")
        print("  [7] Stream Fragmentation    : VERIFIED (reassembled across TCP segment boundaries)")
        print("=" * 78)
    else:
        print("VERIFICATION FAILED: Epistemic drift or TCP boundary violation detected.")
        print(f"Failures: {len(result.failures)}, Errors: {len(result.errors)}")
        print("=" * 78)
        sys.exit(1)


if __name__ == "__main__":
    run_localhost_socket_siege()
