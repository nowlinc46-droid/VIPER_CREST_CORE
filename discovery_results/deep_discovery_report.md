# Deep Discovery Probes Report

## Summary Table

| Probe ID | Probe Description | Layer Tested | Status Progression | Classification |
| :--- | :--- | :--- | :--- | :--- |
| PROBE_1A | Contradiction Escalation (Bare Engine) | `ConvergenceEngine` | SUSPENDED -> BOUNDED | `CONTRADICTION_COLLAPSED` |
| PROBE_1B | Contradiction Escalation (Domain Layer) | `FinancialWireAdapter` | BOUNDED -> SUSPENDED | `CONTRADICTION_PRESERVED` |
| PROBE_1C | Contradiction Escalation (Statutory Gate) | `PolicyContradictionError` | EXCEPTION HALT | `CONTRADICTION_PRESERVED` |
| PROBE_2 | Multi-Seed Required Set (3 Seeds) | `FinancialWireAdapter` | 3 Gaps -> 2 -> 1 -> 0 (BOUNDED) | `STRUCTURAL_RECOVERY` |
| PROBE_3 | Novel Recovery Phrasing Battery (25 tests) | `parse_recovery_data` | 25/25 SUSPENDED (0% resolved) | `KEYWORD_DEPENDENT_RECOVERY` |
| PROBE_4 | Foreign + Overlapping Coordinates | `ConvergenceEngine` | S6 Isolated -> S7 Resolved | `FOREIGN_COORDINATE_ISOLATED` |
| PROBE_6 | Late-Arriving Resolver Dropzone | Multi-file Pipeline | Run 1: SUSPENDED -> Run 2: BOUNDED | `STRUCTURAL_RECOVERY` |

## Detailed Probe Findings

### Probe 1: Contradiction Escalation Findings
- **Bare Convergence Engine:** When given conflicting statements A ('clean') and B ('failed') for coordinate S7, B overwrote A in the dictionary. S7 was marked resolved, and status transitioned to `BOUNDED` (`CONTRADICTION_COLLAPSED`).
- **Domain Adapter Layer:** When conflicting statements arrived under `FinancialWireAdapter`, the adapter detected concurrent conflicting assertions, set coordinate S3 status to `CONTRADICTED`, and forced state transition into `SUSPENDED` (`CONTRADICTION_PRESERVED`).
- **Statutory Safety Gate:** When explicit sanctions blocked/SDN telemetry arrived, the adapter raised `PolicyContradictionError`, halting execution fail-closed (`CONTRADICTION_PRESERVED`).

### Probe 2: Multi-Seed Required Set Findings
- Required Seeds Tested: `['S1', 'S2', 'S3', 'S4', 'S7']`
- Pass 0: 3 gaps remaining (`S3`, `S4`, `S7`) -> `SUSPENDED`
- Pass 1: 2 gaps remaining (`S4`, `S7`) -> `SUSPENDED`
- Pass 2: 1 gap remaining (`S7`) -> `SUSPENDED`
- Pass 3: 0 gaps remaining -> `BOUNDED`
- Finding: The engine strictly enforces that all required seeds must be resolved before `BOUNDED` status is reachable (`STRUCTURAL_RECOVERY`).

### Probe 3: Novel Recovery Phrasing Battery Findings
- Total Natural Paraphrases Evaluated: 25
- Phrases Resolved: 0 (0.0%)
- Phrases Suspended: 25 (100.0%)
- Finding: The unaugmented parser does not infer semantic equivalence without explicit seed tags (`[S7]:`) or exact hardcoded keyword substrings (`KEYWORD_DEPENDENT_RECOVERY`).

### Probe 4: Foreign + Overlapping Coordinates Findings
- Stage 1: Resolving `S6` kept missing `S7` isolated in `SUSPENDED`.
- Stage 2: Concurrently resolving `S7` while altering `S6` data maintained independent tracking of both coordinates (`FOREIGN_COORDINATE_ISOLATED`).

### Probe 6: Late-Arriving Resolver Multi-File Findings
- Run 1 (Files 1 and 2 without resolver): State remained `SUSPENDED` with $S_7$ gap exposed.
- Run 2 (File 3 dropped with `VERIFIED [S7]: ...`): State transitioned to `BOUNDED`.
- Predecessor Hash Binding: State 2 bound State 1 hash (`STRUCTURAL_RECOVERY`).
