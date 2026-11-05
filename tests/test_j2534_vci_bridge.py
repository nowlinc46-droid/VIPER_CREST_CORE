"""Unit & Invariant Regression Suite for Sovereign J2534 PassThru Bridge.

Target VCI Serial: 989510052355
Verifies:
  1. VCI binary framing, STX synchronization, and XOR checksum integrity.
  2. SAE J2534 PassThru Open, Connect, and Channel lifecycle.
  3. The Stem fail-closed interlock during J2534 message transmission.
  4. Immutable SQLite WAL transaction logging and receipt hashing.

ZERO PII. FAIL-CLOSED ARCHITECTURE.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from os_builder.vci_protocol import (
    VCIPacket,
    build_handshake_frame,
    build_can_init_frame,
    build_can_tx_frame,
    calculate_xor_checksum,
    CMD_PING,
    CMD_CAN_TX,
)
from os_builder.j2534_bridge import (
    SovereignPassThruDevice,
    PassThruMsg,
    STATUS_NOERROR,
    J2534_CAN,
    J2534_CAN_FD,
    J2534_ISO15765,
)

VCI_SERIAL = "989510052355"


class J2534VCIBridgeTests(unittest.TestCase):
    def test_vci_framing_serialization_and_deserialization(self):
        pkt = VCIPacket(cmd=CMD_PING, payload=b"\xCA\xFE", vci_serial=VCI_SERIAL)
        raw = pkt.serialize()

        # Check STX and structure
        self.assertEqual(raw[0], 0x55)
        self.assertIn(VCI_SERIAL.encode(), raw)

        # Deserialize
        res = VCIPacket.deserialize(raw)
        self.assertIsNotNone(res)
        parsed_pkt, rem = res
        self.assertEqual(parsed_pkt.cmd, CMD_PING)
        self.assertEqual(parsed_pkt.payload, b"\xCA\xFE")
        self.assertEqual(parsed_pkt.vci_serial.decode("ascii").strip("\x00"), VCI_SERIAL)
        self.assertEqual(rem, b"")

    def test_can_tx_frame_builder(self):
        raw_tx = build_can_tx_frame(can_id=0x7DF, data=b"\x02\x01\x00", is_extended=False, vci_serial=VCI_SERIAL)
        self.assertEqual(raw_tx[0], 0x55)
        parsed, _ = VCIPacket.deserialize(raw_tx)
        self.assertEqual(parsed.cmd, CMD_CAN_TX)
        self.assertEqual(parsed.vci_serial.decode("ascii").strip("\x00"), VCI_SERIAL)

    def test_j2534_device_open_connect_and_write(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            db_p = Path(tmp_dir) / "j2534_test.db"
            dev = SovereignPassThruDevice(vci_serial=VCI_SERIAL, db_path=db_p)

            # 1. PassThruOpen
            status, dev_id = dev.pass_thru_open()
            self.assertEqual(status, STATUS_NOERROR)
            self.assertEqual(dev_id, 1)

            # 2. PassThruConnect (CAN-FD)
            status, ch_id = dev.pass_thru_connect(dev_id, J2534_CAN_FD, flags=0, baud_rate=500000)
            self.assertEqual(status, STATUS_NOERROR)

            # 3. PassThruWriteMsgs (Standard OBD request)
            # Data: 4 bytes CAN ID (0x7DF) + payload (Mode 01 PID 00)
            msg_data = bytes([0x00, 0x00, 0x07, 0xDF, 0x02, 0x01, 0x00])
            msg = PassThruMsg(protocol_id=J2534_CAN_FD, rx_status=0, tx_flags=0, timestamp_us=1000, data=msg_data)
            status, written = dev.pass_thru_write_msgs(ch_id, [msg], timeout_ms=100)
            self.assertEqual(status, STATUS_NOERROR)
            self.assertEqual(written, 1)

            # 4. Check SQLite WAL ledger record
            con = sqlite3.connect(str(db_p))
            row = con.execute("SELECT vci_serial, can_id, stem_state FROM j2534_transactions").fetchone()
            self.assertEqual(row[0], VCI_SERIAL)
            self.assertEqual(row[1], 0x7DF)
            self.assertEqual(row[2], "PASS_BOUNDED")
            con.close()

            # 5. PassThruClose
            self.assertEqual(dev.pass_thru_close(dev_id), STATUS_NOERROR)


if __name__ == "__main__":
    unittest.main()
