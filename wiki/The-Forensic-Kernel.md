# ⚖️ The Forensic Kernel (F1–F9 Engine)

The computational core of ViperCrest is the **fixed $F_1 \text{--} F_9$ Logical Engine**. 

Unlike conventional AI, the engine's reasoning mechanism never mutates when the domain changes. Application context, mapping, data, interface, and output may vary; the engine does not.

---

## 🏛️ The 9 Invariant Structural Slots

Every record entering ViperCrest is deterministically mapped across the 9 canonical sectors:

| Sector | Title | Operational Question | Invariant Role |
| :---: | :--- | :--- | :--- |
| **$F_1$** | **Identity / Intake** | *What entered?* | Primitive ingestion, AST extraction, deterministic hashing. |
| **$F_2$** | **Chronology / Scope** | *When did it change?* | Timestamps, ordering, scoping, flow control boundaries. |
| **$F_3$** | **Support / Evidence** | *What supports it?* | Verified empirical facts, unit tests, closures, proofs. |
| **$F_4$** | **Direct Artifacts** | *What material exists?* | Raw documents, exhibits, contracts, data schemas. |
| **$F_5$** | **Governing Rules** | *What constrains it?* | Policy rules, security invariants, error architecture, admissibility. |
| **$F_6$** | **Correspondence** | *What was exchanged?* | Messages, telemetry, network events, interface mappings. |
| **$F_7$** | **Discovery / Unknown** | *What is missing?* | **Epistemic gap containment (Quarantines unevidenced data).** |
| **$F_8$** | **Opposing / Transition** | *What contradicts it?* | Opposing hypotheses, conflict diffs, dialectical trial. |
| **$F_9$** | **Ledger / Result** | *What bounded state was reached?* | Sealed output, terminal state, cryptographic proof. |

---

## 🔒 The F7 Discovery Quarantine Invariant

The fundamental flaw in modern AI is **confabulation**: when asked about missing data, neural networks guess.

ViperCrest treats ignorance as an active mathematical coordinate:
$$\mathcal{G}(S) = \text{GAPS}(S)$$
$$\mathcal{G}(S) \neq \emptyset \implies \mathbf{SUSPENDED}$$
$$\mathcal{G}(S) = \emptyset \iff \mathbf{BOUNDED} \longrightarrow \mathbf{SEALED}$$

* **Preservation of Legitimate Uncertainty:** If evidence is absent, unobserved, or ambiguous, the coordinate is held strictly in **$F_7$ UNRESOLVED**.
* **Zero Synthetic Interpolation:** The system never guesses or fills gaps with synthetic assumptions.
* **Autonomous Active Inference:** When in `SUSPENDED`, ViperCrest isolates the exact missing coordinate and formulates an actionable directive specifying the required physical telemetry or evidence needed to advance.

---

## 🚫 Epistemic Authority Separation (AI Partition)

In ViperCrest, **AI interfaces are legally and programmatically barred from assigning truth states**:
* AI components may only submit unverified observations and hypotheses.
* If an incoming AI payload contains fields like `"status": "OBSERVED"` or `"epistemic_status": "VERIFIED"`, [`ai_contract.py`](file:///C:/ViperCrest/ai_contract.py) immediately throws an `AI Authority Breach` protocol violation.
* Only ViperCrest’s deterministic evaluation engine holds the authority to classify coordinates into the 5 mutually exclusive hydration states:
  $$\text{State} \in \{\mathbf{OBSERVED}, \mathbf{DERIVED}, \mathbf{POSSIBLE}, \mathbf{CONTRADICTED}, \mathbf{UNRESOLVED}\}$$
