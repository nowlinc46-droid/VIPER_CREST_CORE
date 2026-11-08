# 🎯 Adversarial Attack Vectors & Fail-Closed Testing

ViperCrest includes an independent, automated adversarial attack suite designed to test, probe, and attempt to falsify its cryptographic provenance claims: [`tests/test_adversarial_provenance.py`](file:///C:/ViperCrest/tests/test_adversarial_provenance.py).

---

## ⚡ The 3 Attack Vectors

To prove that the architecture is tamper-evident and fail-closed, the test suite executes three distinct attacks:

```text
======================================================================
 VIPERCREST ADVERSARIAL PROVENANCE ATTACK SUITE
======================================================================
Ran 3 tests in 0.056s

OK

  [ATTACK VECTOR 5] INPUT MODIFIED            -> DIFFERENT DESCENDANT
  [ATTACK VECTOR 6] PREDECESSOR MODIFIED      -> CHAIN VERIFICATION FAIL
  [ATTACK VECTOR 7] UNMODIFIED REPLAY         -> REPRODUCIBLE RESULT
```

---

### Detailed Attack Analysis

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
*Expected Output: `Ran 3 tests ... OK`*
