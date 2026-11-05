# 🎯 Adversarial Attack Vectors & Fail-Closed Testing

ViperCrest includes an independent, automated adversarial attack suite designed to test, probe, and attempt to falsify its cryptographic provenance claims: [`tests/test_adversarial_provenance.py`](file:///C:/ViperCrest/tests/test_adversarial_provenance.py).

---

## ⚡ The 7 Attack Vectors

To prove that the architecture is tamper-evident and fail-closed, the test suite executes seven distinct attacks:

```text
======================================================================
 VIPERCREST ADVERSARIAL PROVENANCE & LICENSE ATTACK SUITE
======================================================================
Ran 7 tests in 0.056s

OK

  [ATTACK VECTOR 1] ORIGINAL                  -> PASS
  [ATTACK VECTOR 2] LICENSE SPEC MODIFIED     -> FAIL (HALTED)
  [ATTACK VECTOR 3] SIGNATURE MODIFIED        -> FAIL (HALTED)
  [ATTACK VECTOR 4] PUBLIC KEY REPLACED       -> FAIL (HALTED)
  [ATTACK VECTOR 5] INPUT MODIFIED            -> DIFFERENT DESCENDANT
  [ATTACK VECTOR 6] PREDECESSOR MODIFIED      -> CHAIN VERIFICATION FAIL
  [ATTACK VECTOR 7] UNMODIFIED REPLAY         -> REPRODUCIBLE RESULT
```

---

### Detailed Attack Analysis

#### Vector 1: `ORIGINAL → PASS`
* **Test:** Evaluates a clean installation with matching `license_spec.json`, valid Ed25519 `license.sig`, and authentic `public_seal.pem`.
* **Result:** Verification succeeds (`Verify == TRUE`). The SHA-256 digest of the seal (`195fcfdc414d...`) is bound into Genesis.

#### Vector 2: `LICENSE SPEC MODIFIED → FAIL (HALTED)`
* **Attack:** Ingests a valid license, then mutates one property in `license_spec.json` (e.g. `"licensee": "ROGUE_OPERATOR"`).
* **Reaction:** `license_gate.py` detects signature mismatch and immediately trips **fail-closed (`exit code 1`) before Stage $F_1$ intake**.

#### Vector 3: `SIGNATURE MODIFIED → FAIL (HALTED)`
* **Attack:** Flips a single bit in the binary signature file `license.sig` (`tampered_sig[0] ^= 0xFF`).
* **Reaction:** Ed25519 verification throws `InvalidSignature` and halts immediately (`exit code 1`).

#### Vector 4: `PUBLIC KEY REPLACED → FAIL (HALTED)`
* **Attack:** Generates a brand-new rogue Ed25519 keypair and replaces `runtime/public_seal.pem` with the rogue public key.
* **Reaction:** Signature validation fails because the in-repo verification key no longer matches the Licensor's offline master signature. Halts immediately (`exit code 1`).

#### Vector 5: `INPUT MODIFIED → DIFFERENT DESCENDANT`
* **Attack:** Evaluates two fixtures differing by only 1 character (`value: 100` vs `value: 101`).
* **Reaction:** The initial input digests diverge. Because the sector chain ($F_1 \to F_9$) binds each stage's output hash into the next stage's input hash, every single intermediate sector receipt and the final terminal state hash diverged.

#### Vector 6: `PREDECESSOR MODIFIED → CHAIN VERIFICATION FAIL`
* **Attack:** In an active sector transition ($F_1 \to F_2$), mutates the predecessor `input_hash` by a single character.
* **Reaction:** `verify_receipt()` cross-references the transition document against the signed envelope and throws an immediate `IntentError` / validation failure.

#### Vector 7: `UNMODIFIED REPLAY → REPRODUCIBLE RESULT`
* **Attack:** Replays the exact same payload through the deterministic derivation pipeline.
* **Reaction:** Bit-for-bit identical hashes from genesis through sector transitions.

---

## 🏃 Running the Attack Suite

```powershell
python tests/test_adversarial_provenance.py
```
*Expected Execution Time: < 0.1s*  
*Expected Output: `Ran 7 tests ... OK`*
