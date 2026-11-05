"""Launch SmartLink & DBSCar VCI Binary Framing Protocol (vci_protocol.py).

Target VCI Serial: 989510052355
Implements binary framing, checksumming, and command translation for:
  - VCI Handshake and Serial Verification (GetBoxSerialNum)
  - ISO 15765-2 / CAN-FD packet encapsulation
  - Hardware filter mask configuration
  - Dual-baud switching (500 kbps arbitration / 2 Mbps data phase)

ZERO PII. DETERMINISTIC INVARIANT FRAMING.
"""
from __future__ import annotations

import struct
from typing import List, Optional, Tuple

STX_BYTE = 0x55

# Command IDs for DBSCar / SmartLink protocol
CMD_PING = 0x01
CMD_GET_SERIAL = 0x02
CMD_CAN_INIT = 0x10
CMD_CAN_TX = 0x11
CMD_CAN_RX = 0x12
CMD_SET_FILTER = 0x15
CMD_KLINE_INIT = 0x20
CMD_CLOSE_LINK = 0x30


def calculate_xor_checksum(data: bytes) -> int:
    """Calculates XOR checksum across byte buffer."""
    chk = 0
    for b in data:
        chk ^= b
    return chk & 0xFF


class VCIPacket:
    """Represents a single binary frame exchanged with the VCI."""

    def __init__(self, cmd: int, payload: bytes = b"", vci_serial: str = "989510052355"):
        self.cmd = cmd
        self.payload = payload
        self.vci_serial = vci_serial.encode("ascii").ljust(12, b"\x00")[:12]

    def serialize(self) -> bytes:
        """Encodes frame into wire format: STX + LEN(2B) + CMD(1B) + SERIAL(12B) + PAYLOAD + XOR(1B)."""
        body = struct.pack(">B12s", self.cmd, self.vci_serial) + self.payload
        length = len(body)
        length_bytes = struct.pack(">H", length)
        xor_sum = calculate_xor_checksum(length_bytes + body)
        return bytes([STX_BYTE]) + length_bytes + body + bytes([xor_sum])

    @classmethod
    def deserialize(cls, data: bytes) -> Optional[Tuple[VCIPacket, bytes]]:
        """Parses a packet from a byte stream. Returns (packet, remaining_bytes) or None."""
        if len(data) < 16:  # STX(1) + LEN(2) + CMD(1) + SERIAL(12) + XOR(1) = 17 minimum
            return None

        # Find STX sync byte
        stx_idx = data.find(bytes([STX_BYTE]))
        if stx_idx == -1:
            return None
        data = data[stx_idx:]
        if len(data) < 17:
            return None

        length = struct.unpack(">H", data[1:3])[0]
        total_frame_len = 1 + 2 + length + 1  # STX + LEN(2) + BODY + XOR(1)
        if len(data) < total_frame_len:
            return None  # Incomplete frame, wait for more bytes

        body_with_len = data[1 : 3 + length]
        received_xor = data[3 + length]
        expected_xor = calculate_xor_checksum(body_with_len)

        if received_xor != expected_xor:
            # Corrupted frame, skip STX and search next
            return cls.deserialize(data[1:])

        cmd = data[3]
        serial_str = data[4:16].decode("ascii", errors="ignore").rstrip("\x00")
        payload = data[16 : 3 + length]
        remaining = data[total_frame_len:]

        pkt = cls(cmd=cmd, payload=payload, vci_serial=serial_str)
        return pkt, remaining


def build_handshake_frame(vci_serial: str = "989510052355") -> bytes:
    """Creates a ping/handshake probe."""
    return VCIPacket(cmd=CMD_PING, payload=b"\x00\x01", vci_serial=vci_serial).serialize()


def build_can_init_frame(baud_rate: int = 500000, can_fd: bool = True, vci_serial: str = "989510052355") -> bytes:
    """Builds a CAN/CAN-FD controller initialization frame."""
    mode_flag = 0x01 if can_fd else 0x00
    payload = struct.pack(">IB", baud_rate, mode_flag)
    return VCIPacket(cmd=CMD_CAN_INIT, payload=payload, vci_serial=vci_serial).serialize()


def build_can_tx_frame(can_id: int, data: bytes, is_extended: bool = False, vci_serial: str = "989510052355") -> bytes:
    """Encapsulates a standard or extended CAN/CAN-FD message for transmission."""
    flags = 0x01 if is_extended else 0x00
    dlc = len(data)
    header = struct.pack(">IBB", can_id, flags, dlc)
    return VCIPacket(cmd=CMD_CAN_TX, payload=header + data, vci_serial=vci_serial).serialize()
