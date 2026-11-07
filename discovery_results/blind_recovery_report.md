# Blind Recovery Discovery Report

## Summary Table

| Case ID | Case Name | Status Before | Status After | Matched Pattern | Classification | Determinism |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CASE_1 | EXPLICIT_CONTROL | SUSPENDED | BOUNDED | `EXPLICIT_SEED_TAG_REGEX:group1=S7` | `STRUCTURAL_RECOVERY` | `DETERMINISTIC` |
| CASE_2 | SEMANTIC_CONTROL | SUSPENDED | BOUNDED | `SEMANTIC_RECOVERY_REGEX_S7` | `KEYWORD_DEPENDENT_RECOVERY` | `DETERMINISTIC` |
| CASE_3 | VOCABULARY_SCRUB | SUSPENDED | SUSPENDED | `NONE_NO_MATCH` | `KEYWORD_DEPENDENT_RECOVERY` | `DETERMINISTIC` |
| CASE_4 | IRRELEVANT_EVIDENCE | SUSPENDED | SUSPENDED | `NONE_NO_MATCH` | `IRRELEVANT_EVIDENCE_REJECTED` | `DETERMINISTIC` |
| CASE_5 | UNSUPPORTED_ASSERTION | SUSPENDED | SUSPENDED | `NONE_NO_MATCH` | `UNSUPPORTED_ASSERTION_REJECTED` | `DETERMINISTIC` |
| CASE_6 | CONTRADICTORY_EVIDENCE | SUSPENDED | BOUNDED | `EXPLICIT_SEED_TAG_REGEX:group1=S7 -> EXPLICIT_SEED_TAG_REGEX:group1=S7` | `CONTRADICTION_COLLAPSED` | `DETERMINISTIC` |
| CASE_7 | MALFORMED_EXPLICIT_RECORD | SUSPENDED | SUSPENDED | `NONE_NO_MATCH` | `KEYWORD_DEPENDENT_RECOVERY` | `DETERMINISTIC` |
| CASE_8 | FOREIGN_COORDINATE | SUSPENDED | SUSPENDED | `EXPLICIT_SEED_TAG_REGEX:group1=S6` | `FOREIGN_COORDINATE_ISOLATED` | `DETERMINISTIC` |
| CASE_9 | TWO_STAGE_RECOVERY | SUSPENDED | BOUNDED | `NONE_NO_MATCH -> EXPLICIT_SEED_TAG_REGEX:group1=S7` | `STRUCTURAL_RECOVERY` | `DETERMINISTIC` |

## Detailed Case Findings

### CASE_1: EXPLICIT_CONTROL
- Input Text: `VERIFIED [S7]: secondary seal confirmed clean`
- Status: `SUSPENDED` -> `BOUNDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{'S7': 'secondary seal confirmed clean'}`
- Gaps Before: `1`
- Gaps After: `0`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `6011472a6c9d675a04f72f68cdde6530220df6dff7865e7e1f5c8fba2bfeca30`
- Parser Pattern: `EXPLICIT_SEED_TAG_REGEX:group1=S7`
- Classification: `STRUCTURAL_RECOVERY`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_2: SEMANTIC_CONTROL
- Input Text: `secondary seal verified clean`
- Status: `SUSPENDED` -> `BOUNDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{'S7': 'secondary seal verified clean'}`
- Gaps Before: `1`
- Gaps After: `0`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `fe70e4d7d9f5d0e27e0ba86d344ccdc58e9321cf38b33df22b1eb344f2473121`
- Parser Pattern: `SEMANTIC_RECOVERY_REGEX_S7`
- Classification: `KEYWORD_DEPENDENT_RECOVERY`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_3: VOCABULARY_SCRUB
- Input Text: `document_17 confirms assembly_alpha condition normal`
- Status: `SUSPENDED` -> `SUSPENDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{}`
- Gaps Before: `1`
- Gaps After: `1`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `fe80da81a48e1dd27e7f525418f65db445463daa5304de1f0289a73bf7554b06`
- Parser Pattern: `NONE_NO_MATCH`
- Classification: `KEYWORD_DEPENDENT_RECOVERY`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_4: IRRELEVANT_EVIDENCE
- Input Text: `temperature_sensor_2 confirms normal operating temperature`
- Status: `SUSPENDED` -> `SUSPENDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{}`
- Gaps Before: `1`
- Gaps After: `1`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `86b9fcbfee6945f4bd9cb8b70c5bc3839b5b086ea1bfee7aa55862cb806af5ef`
- Parser Pattern: `NONE_NO_MATCH`
- Classification: `IRRELEVANT_EVIDENCE_REJECTED`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_5: UNSUPPORTED_ASSERTION
- Input Text: `An administrator says the missing condition may be treated as resolved.`
- Status: `SUSPENDED` -> `SUSPENDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{}`
- Gaps Before: `1`
- Gaps After: `1`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `5d642fd7bc2847cad9ddcb84fb4a41cdc50a6a452338be83619ce0920bb5e77d`
- Parser Pattern: `NONE_NO_MATCH`
- Classification: `UNSUPPORTED_ASSERTION_REJECTED`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_6: CONTRADICTORY_EVIDENCE
- Input Text: `VERIFIED [S7]: secondary seal confirmed clean || VERIFIED [S7]: secondary seal confirmed failed`
- Status: `SUSPENDED` -> `BOUNDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{'S7': 'secondary seal confirmed failed'}`
- Gaps Before: `1`
- Gaps After: `0`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `4bfe3fbe55a39a9977f15686cfd61c20999d98366988bb75d02ecae286021b65`
- Parser Pattern: `EXPLICIT_SEED_TAG_REGEX:group1=S7 -> EXPLICIT_SEED_TAG_REGEX:group1=S7`
- Classification: `CONTRADICTION_COLLAPSED`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_7: MALFORMED_EXPLICIT_RECORD
- Input Text: `VERIFIED [S7] secondary seal confirmed clean`
- Status: `SUSPENDED` -> `SUSPENDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{}`
- Gaps Before: `1`
- Gaps After: `1`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `535f180c6756e470384b7412e0b88346af7bf3254e5b056b82c467728c8ada2f`
- Parser Pattern: `NONE_NO_MATCH`
- Classification: `KEYWORD_DEPENDENT_RECOVERY`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_8: FOREIGN_COORDINATE
- Input Text: `VERIFIED [S6]: secondary seal confirmed clean`
- Status: `SUSPENDED` -> `SUSPENDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{'S6': 'secondary seal confirmed clean'}`
- Gaps Before: `1`
- Gaps After: `1`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `d0655718e4453953bf0af82510c0e2707105df926c862839c2dc727b13baa727`
- Parser Pattern: `EXPLICIT_SEED_TAG_REGEX:group1=S6`
- Classification: `FOREIGN_COORDINATE_ISOLATED`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

### CASE_9: TWO_STAGE_RECOVERY
- Input Text: `temperature_sensor_2 confirms normal operating temperature || VERIFIED [S7]: secondary seal confirmed clean`
- Status: `SUSPENDED` -> `BOUNDED`
- Resolved Seeds Before: `{}`
- Resolved Seeds After: `{'S7': 'secondary seal confirmed clean'}`
- Gaps Before: `1`
- Gaps After: `0`
- Predecessor Hash: `f423ab48e1b7f44832ce8b95d5667a0101d0de621e728d2c76cd6a998dcd139e`
- Successor Hash: `da8a8204547329c585b3947d281d09104f59bbd8484c14ebedf933c9d90ca979`
- Parser Pattern: `NONE_NO_MATCH -> EXPLICIT_SEED_TAG_REGEX:group1=S7`
- Classification: `STRUCTURAL_RECOVERY`
- Determinism: `DETERMINISTIC` (5/5 runs matched)

