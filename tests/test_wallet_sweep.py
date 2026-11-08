"""Tests for wallet_sweep - the read-only crypto artifact search command.

Known-answer vectors are the canonical public ones: the BIP39 test mnemonic
("abandon" x11 + "about", zero-entropy vector), its published BIP44/BIP84
first receive addresses, the RIPEMD-160 reference digests, and the WIF string
for private key 1.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

VIPER_ROOT = Path(__file__).resolve().parent.parent
if str(VIPER_ROOT) not in sys.path:
    sys.path.insert(0, str(VIPER_ROOT))

import wallet_sweep as ws

TEST_MNEMONIC = ["abandon"] * 11 + ["about"]
TEST_PHRASE = " ".join(TEST_MNEMONIC)
BIP44_FIRST = "1LqBGSKuX5yYUonjxT5qGfpUsXKYYWeabA"
BIP84_FIRST = "bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu"
WIF_KEY_1 = "5HpHagT65TZzG1PH3CSu63k8DbpvD8s5ip4nEB3kEsreAnchuDf"
KEY1_COMPRESSED_ADDR = "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"


class Ripemd160VectorTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(ws._ripemd160(b"").hex(),
                         "9c1185a5c5e9fc54612808977ee8f548b2258d31")

    def test_abc(self):
        self.assertEqual(ws._ripemd160(b"abc").hex(),
                         "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc")


class MnemonicTests(unittest.TestCase):
    def test_checksum_valid_vector(self):
        self.assertTrue(ws.mnemonic_checksum_valid(TEST_MNEMONIC))

    def test_checksum_invalid(self):
        self.assertFalse(ws.mnemonic_checksum_valid(["abandon"] * 12))

    def test_nonstandard_length_rejected(self):
        self.assertFalse(ws.mnemonic_checksum_valid(["abandon"] * 11))

    def test_bip44_first_address(self):
        self.assertEqual(ws.derive_first_addresses(TEST_MNEMONIC, 1)["bip44_p2pkh"][0],
                         BIP44_FIRST)

    def test_bip84_first_address(self):
        self.assertEqual(ws.derive_first_addresses(TEST_MNEMONIC, 1)["bip84_p2wpkh"][0],
                         BIP84_FIRST)


class ValidatorTests(unittest.TestCase):
    def test_wif_key_1(self):
        self.assertTrue(ws.validate_wif(WIF_KEY_1))

    def test_wif_corrupted(self):
        self.assertFalse(ws.validate_wif(WIF_KEY_1[:-1] + "g"))

    def test_key1_compressed_address(self):
        self.assertEqual(ws._p2pkh_address((1).to_bytes(32, "big")), KEY1_COMPRESSED_ADDR)

    def test_legacy_address(self):
        self.assertTrue(ws.validate_legacy_address(BIP44_FIRST))
        self.assertFalse(ws.validate_legacy_address(BIP44_FIRST[:-1] + "B"))

    def test_bech32(self):
        self.assertTrue(ws._bech32_checksum_valid(BIP84_FIRST))
        self.assertFalse(ws._bech32_checksum_valid(BIP84_FIRST[:-1] + "x"))

    def test_xkey_form(self):
        payload = bytes.fromhex("0488ade4") + bytes(74)
        xprv_like = ws._b58check_encode(payload)
        self.assertTrue(ws.validate_xkey(xprv_like))
        mid = len(xprv_like) // 2
        corrupted = xprv_like[:mid] + ("1" if xprv_like[mid] != "1" else "2") + xprv_like[mid + 1:]
        self.assertFalse(ws.validate_xkey(corrupted))


class SweepEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "Bitcoin").mkdir()
        (root / "Bitcoin" / "wallet.dat").write_bytes(b"fake-wallet-bytes")
        (root / "keystore").mkdir()
        (root / "keystore" / "UTC--2020-01-01T00-00-00.000Z--abcdef0123").write_text("{}", encoding="utf-8")
        (root / "notes.txt").write_text(
            f"my recovery words are: {TEST_PHRASE} - keep safe", encoding="utf-8")
        (root / "badseed.txt").write_text(
            "abandon " * 12, encoding="utf-8")
        (root / "keys.txt").write_text(
            f"old key {WIF_KEY_1} and a hash {'a' * 64} for reference", encoding="utf-8")
        (root / "prose.txt").write_text(
            "The committee decided to postpone the picnic because of rain on Tuesday.", encoding="utf-8")
        self.root = root

    def tearDown(self):
        self.temp.cleanup()

    def test_sweep_record(self):
        record = ws.run_sweep(self.root, address_count=1)
        kinds = {a["kind"] for a in record["artifacts"]}
        self.assertIn("bitcoin_core_wallet", kinds)
        self.assertIn("ethereum_keystore", kinds)

        seed_entries = [v for v in record["verified"] if v["type"] == "bip39_seed_phrase"]
        self.assertEqual(len(seed_entries), 1)
        self.assertEqual(seed_entries[0]["checksum"], "valid")
        self.assertEqual(seed_entries[0]["derived_addresses"]["bip44_p2pkh"][0], BIP44_FIRST)

        wif_entries = [v for v in record["verified"] if v["type"] == "wif_private_key"]
        self.assertEqual(len(wif_entries), 1)

        bad = [c for c in record["candidates"]
               if c["type"] == "bip39_seed_phrase" and c.get("checksum") == "invalid"]
        self.assertEqual(len(bad), 1)
        hexes = [c for c in record["candidates"] if c["type"] == "hex_64_string"]
        self.assertEqual(len(hexes), 1)
        self.assertTrue(record["f7_register"])

    def test_record_never_contains_secrets(self):
        record = ws.run_sweep(self.root, address_count=1)
        blob = json.dumps(record)
        self.assertNotIn(TEST_PHRASE, blob)
        self.assertNotIn(WIF_KEY_1, blob)

    def test_cli_and_bad_target(self):
        out = self.root / "record.json"
        self.assertEqual(ws.main([str(self.root), "--out", str(out), "--addresses", "1"]), 0)
        self.assertTrue(out.exists())
        self.assertEqual(ws.main([str(self.root / "does-not-exist")]), 2)


if __name__ == "__main__":
    unittest.main()
