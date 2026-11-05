"""
ViperCrest Typed RPC Dispatcher Test Suite (tests/test_rpc_dispatcher.py).

Verifies the typed RPC dispatcher implementation gap:
1. Typed recognition of eth_blockNumber (and related EVM RPC methods).
2. Loopback air-gap containment (V05 invariant: rejects unauthorized remote endpoints).
3. Local RPC calling and capturing responses as cryptographically bound evidence.
4. Routing captured evidence through ViperCrest sovereign runtime and 5-file receipt verification.
5. Fail-closed behavior on connection error or JSON-RPC protocol error.
6. Integration with ai_wrapper and CLI launcher.
7. Core engine byte-invariance.
"""
from __future__ import annotations

import http.server
import json
import socket
import subprocess
import sys
import threading
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import ai_contract as aic
import ai_wrapper as aiw
import rpc_dispatcher as rpc
import viper


class MockRPCServer(http.server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, response_payload):
        super().__init__(server_address, RequestHandlerClass)
        self.response_payload = response_payload
        self.received_requests = []


class MockRPCHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.server.received_requests.append(json.loads(body.decode("utf-8")))

        resp_bytes = json.dumps(self.server.response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def log_message(self, format, *args):
        # Suppress server stderr output in tests
        pass


def run_mock_rpc_server(response_payload: dict) -> tuple[MockRPCServer, threading.Thread, str]:
    server = MockRPCServer(("127.0.0.1", 0), MockRPCHandler, response_payload)
    port = server.server_port
    endpoint = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, endpoint


class RPCDispatcherTests(unittest.TestCase):

    def test_01_recognition_of_eth_blocknumber(self):
        """Test 1: Verify typed dispatcher recognizes eth_blockNumber across various formats."""
        dispatcher = rpc.TypedRPCDispatcher()

        # Direct calls
        self.assertTrue(dispatcher.recognizes("eth_blockNumber"))
        self.assertTrue(dispatcher.recognizes("eth_blocknumber"))
        self.assertTrue(dispatcher.recognizes("eth_blockNumber()"))
        self.assertTrue(dispatcher.recognizes("rpc eth_blockNumber"))
        self.assertTrue(dispatcher.recognizes("call eth_blockNumber"))
        self.assertTrue(dispatcher.recognizes(["eth_blockNumber"]))
        self.assertTrue(dispatcher.recognizes({"method": "eth_blockNumber"}))

        # Rejects unrelated non-RPC inputs
        self.assertFalse(dispatcher.recognizes("analyze incident.raw"))
        self.assertFalse(dispatcher.recognizes("hydrate S2"))
        self.assertFalse(dispatcher.recognizes("why is T5 unresolved?"))
        self.assertFalse(dispatcher.recognizes("what is PACS?"))

    def test_02_loopback_containment_and_airgap_v05(self):
        """Test 2: Enforce Invariant V05 air-gap containment (reject non-loopback endpoints)."""
        dispatcher = rpc.TypedRPCDispatcher()

        # Permitted loopback endpoints
        req_local = dispatcher.parse_request("eth_blockNumber", endpoint_override="http://127.0.0.1:8545")
        self.assertEqual(req_local.endpoint, "http://127.0.0.1:8545")

        req_lh = dispatcher.parse_request("eth_blockNumber", endpoint_override="http://localhost:8545")
        self.assertEqual(req_lh.endpoint, "http://localhost:8545")

        # Non-loopback / remote targets must be rejected
        with self.assertRaises(rpc.RPCInvalidRequestError) as ctx:
            dispatcher.parse_request("eth_blockNumber", endpoint_override="https://mainnet.infura.io/v3/secret")
        self.assertIn("Air-Gap Containment Violation (V05)", str(ctx.exception))

        with self.assertRaises(rpc.RPCInvalidRequestError) as ctx2:
            dispatcher.parse_request("eth_blockNumber", endpoint_override="http://192.168.1.100:8545")
        self.assertIn("Air-Gap Containment Violation (V05)", str(ctx2.exception))

    def test_03_request_validation_and_parameter_parsing(self):
        """Test 3: Typed request creation, parameter parsing, and serialization."""
        dispatcher = rpc.TypedRPCDispatcher()

        # Parse request with parameters
        req = dispatcher.parse_request("eth_getBlockByNumber 0x100 false")
        self.assertEqual(req.method, "eth_getBlockByNumber")
        self.assertEqual(req.params, ["0x100", False])
        self.assertEqual(req.jsonrpc, "2.0")

        # Reject malformed method names with invalid characters
        with self.assertRaises(rpc.RPCInvalidRequestError):
            dispatcher.parse_request("../injection/method")

        with self.assertRaises(rpc.RPCMethodNotSupportedError):
            dispatcher.parse_request("invalidMethodName")

    def test_04_call_local_rpc_and_evidence_capture(self):
        """Test 4: Call local RPC endpoint, capture response, digest SHA-256 evidence record."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0x10d",  # Block height 269
        }
        server, thread, endpoint = run_mock_rpc_server(mock_response)
        try:
            dispatcher = rpc.TypedRPCDispatcher(endpoint=endpoint)
            req = dispatcher.parse_request("eth_blockNumber")
            evidence = dispatcher.call_local_rpc(req)

            # Assert request received by server
            self.assertEqual(len(server.received_requests), 1)
            self.assertEqual(server.received_requests[0]["method"], "eth_blockNumber")

            # Assert evidence properties
            self.assertEqual(evidence.method, "eth_blockNumber")
            self.assertEqual(evidence.result, "0x10d")
            self.assertEqual(evidence.block_number, 269)
            self.assertEqual(evidence.status, "CAPTURED")
            self.assertIsNotNone(evidence.captured_at)
            self.assertIsNone(evidence.error_message)

            # Assert SHA-256 evidence hash
            expected_hash = rpc.hashlib.sha256(json.dumps(mock_response).encode("utf-8")).hexdigest()
            self.assertEqual(evidence.evidence_hash, expected_hash)
        finally:
            server.shutdown()
            server.server_close()

    def test_05_evidence_routing_through_vipercrest_runtime(self):
        """Test 5: Capture evidence FIRST, then route through ViperCrest with verified session receipt."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0x400",  # Block height 1024
        }
        server, thread, endpoint = run_mock_rpc_server(mock_response)
        try:
            dispatcher = rpc.TypedRPCDispatcher(endpoint=endpoint)
            evidence, auth_resp = dispatcher.dispatch("eth_blockNumber")

            # 1. Assert Evidence Captured First
            self.assertEqual(evidence.method, "eth_blockNumber")
            self.assertEqual(evidence.block_number, 1024)
            self.assertEqual(evidence.status, "CAPTURED")

            # 2. Assert ViperCrest Sovereign Execution
            self.assertEqual(auth_resp.status, "SUCCESS")
            self.assertTrue(auth_resp.session_receipt_verified)
            self.assertTrue(auth_resp.f7_uncertainty_preserved)
            self.assertEqual(auth_resp.cartridge_id, "SECURITY_IR")
            self.assertIsNotNone(auth_resp.session_id)

            # Check that request was logged in runtime/ai/requests
            req_file = aic.AI_REQUESTS_DIR / f"request_{auth_resp.request_id}.json"
            self.assertTrue(req_file.exists(), "AI Request Envelope must be persisted")
        finally:
            server.shutdown()
            server.server_close()

    def test_06_fail_closed_on_connection_error_and_rpc_error(self):
        """Test 6: Assert fail-closed behavior when node is unreachable or returns RPC error."""
        # Unoccupied port for connection refusal test
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]

        dead_endpoint = f"http://127.0.0.1:{free_port}"
        dispatcher = rpc.TypedRPCDispatcher(endpoint=dead_endpoint, timeout=0.5)

        with self.assertRaises(rpc.RPCConnectionError) as ctx:
            dispatcher.dispatch("eth_blockNumber")
        self.assertIn("Failed to connect to local RPC endpoint", str(ctx.exception))

        # Server returning JSON-RPC error
        mock_error_resp = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method eth_blockNumber not supported"},
        }
        server, thread, endpoint = run_mock_rpc_server(mock_error_resp)
        try:
            dispatcher_err = rpc.TypedRPCDispatcher(endpoint=endpoint)
            with self.assertRaises(rpc.RPCError) as err_ctx:
                dispatcher_err.dispatch("eth_blockNumber")
            self.assertIn("Method eth_blockNumber not supported", str(err_ctx.exception))
        finally:
            server.shutdown()
            server.server_close()

    def test_07_ai_wrapper_rpc_routing_integration(self):
        """Test 7: Verify ai_wrapper.py routes eth_blockNumber through typed dispatcher."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0x200",  # Block height 512
        }
        server, thread, endpoint = run_mock_rpc_server(mock_response)
        try:
            # Override default endpoint in rpc_dispatcher temporarily for test
            orig_default = rpc.DEFAULT_RPC_URL
            rpc.DEFAULT_RPC_URL = endpoint
            try:
                # Execute through ai_wrapper
                cmd = f"eth_blockNumber --endpoint {endpoint}"
                rc = aiw.run_single_interaction(cmd)
                self.assertEqual(rc, 0)
                self.assertEqual(len(server.received_requests), 1)
            finally:
                rpc.DEFAULT_RPC_URL = orig_default
        finally:
            server.shutdown()
            server.server_close()

    def test_08_core_engine_invariance_zero_diff(self):
        """Test 8: Verify that F1-F9 core engine files remain strictly unmodified (0 diff)."""
        core_files = ["viper_matrix.py", "viper_core.py", "viper_http.py"]
        cmd = ["git", "status", "--porcelain"] + core_files
        res = subprocess.run(cmd, cwd=str(VIPER_ROOT), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(
            res.stdout.strip(), "",
            f"Core engine invariance violation! Files modified:\n{res.stdout}"
        )


if __name__ == "__main__":
    unittest.main()
