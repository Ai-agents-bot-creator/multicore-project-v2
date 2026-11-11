# Adversarial Challenge & Edge Case Stress-Test Report

**Agent**: Challenger 1 (Adversarial Script & Edge Case Stressor)  
**Date**: 2026-11-09  
**Target Artifacts**:
- `white_papers/final/verify_srs.py` (Acceptance Verifier)
- `white_papers/final/SRS_final_v2.docx` (Elevated SRS Document)
- `white_papers/final/SRS_final.docx` (Baseline v0.2 SRS Document)

---

## Challenge Summary

**Overall Risk Assessment**: **MEDIUM-HIGH** (due to verifier sensitivity gaps, despite document correctness)

- **Target Document (`SRS_final_v2.docx`)**: **CLEAN / SOUND**. All 66 checks in `verify_srs.py` pass. Direct XML parsing independently proves that all 26 tables have `w:tblHeader` on row 0, all 250 rows have `w:cantSplit`, all 44 requirements are traced, and all PPA/protocol values match the normative whitepaper.
- **Upgraded Verifier (`verify_srs.py`)**: **VULNERABLE TO FALSE NEGATIVES**. While it catches 29/38 adversarial mutations (including structural requirement deletions, signal removals, code coverage stripping, and corrupted DOCX/XML files), empirical mutation stress testing exposed **7 distinct false negatives (blind spots)** where deliberate corruptions yielded `exit code 0` (PASS), plus **2 unverified architectural features** (`w:tblHeader` and `w:cantSplit`).
- **Baseline Regression (`SRS_final.docx --baseline`)**: **CLEAN**. Passes 41/41 baseline checks with exit code 0. Full 66-check suite correctly fails on `SRS_final.docx` (56/66 passed, 10 expected failures).

---

## Adversarial Mutation Stress Test Matrix (38 Empirical Tests)

A dedicated adversarial harness (`/tmp/srs_adversarial_test/run_mutations.py`) executed 35 semantic mutations across 13 requirement categories and 3 file-level corruption tests against `SRS_final_v2.docx`.

| Mutation ID | Category | Deliberate Corruption Injected | Target Check | Verifier Exit Code | Checks Triggered | Verdict / Status |
|---|---|---|---|---|---|---|
| `MUT_01_DEL_PERF01_TRACE` | Traceability | Delete PERF-01 from Table 24 (Traceability Matrix) | `B6c` | 1 (FAIL) | `B6c` | **CAUGHT** (Expected) |
| `MUT_02_DEL_FR05_TRACE` | Traceability | Delete FR-05 from Table 24 (Traceability Matrix) | `B6b` | 1 (FAIL) | `B6b`, `B6c` | **CAUGHT** (Expected) |
| `MUT_03_REINTRO_TBD_PERF01` | Placeholders | Reintroduce `TBD` in PERF-01 clock target cell | `T01` | 1 (FAIL) | `T01` | **CAUGHT** (Expected) |
| `MUT_04_REINTRO_TBD_FPGA01` | Placeholders | Reintroduce `TBD` in FPGA-01 frequency target cell | `T02` | 1 (FAIL) | `T02` | **CAUGHT** (Expected) |
| `MUT_05_REINTRO_NAME_PLACEHOLDER` | Placeholders | Reintroduce `[Name]` in Document Metadata table | `T10` | 1 (FAIL) | `T10` | **CAUGHT** (Expected) |
| `MUT_06_REINTRO_TODO_PLACEHOLDER` | Placeholders | Reintroduce `TODO` in Approval table | `T10` | 1 (FAIL) | `T10` | **CAUGHT** (Expected) |
| `MUT_07_BREAK_CREDIT_IN_SIGNAL` | Signals | Rename `credit_in` to `credit_rx` in Table 13 | `T09` | 1 (FAIL) | `T09` | **CAUGHT** (Expected) |
| `MUT_08_BREAK_RESET_SIGNAL` | Signals | Delete `reset` row from Table 13 | `T09` | 1 (FAIL) | `T09` | **CAUGHT** (Expected) |
| `MUT_09_ADD_BARE_DMA_SIGNAL_2X2` | Signals | Add bare `dma_wr` to Table 13 (2x2 build signal list) | `B5a` | 1 (FAIL) | `B5a` | **CAUGHT** (Expected) |
| `MUT_10_DROP_CODE_COVERAGE_ROWS` | Coverage | Remove Statement & Branch rows from Table 18 | `M3c` | 1 (FAIL) | `M3c` | **CAUGHT** (Expected) |
| `MUT_11_DROP_ALL_COVERAGE_ROWS` | Coverage | Remove Statement, Branch, Toggle rows from Table 18 | `M3c` | 1 (FAIL) | `M3c` | **CAUGHT** (Expected) |
| `MUT_12_DEL_PUTACK_MSG_ROW` | Messages | Delete `PUTACK` row from Table 12 (Message Table) | `M1b` | 1 (FAIL) | `M1b` | **CAUGHT** (Expected) |
| `MUT_13_REVERSE_PUTACK_DIR` | Messages | Reverse PUTACK direction from `dir -> L1` to `L1 -> dir` in Table 12 | `B1c` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `MUT_14_CORRUPT_VC_MAPPING_AC03` | Protocols | Corrupt VC index order (`VC0=FWD, VC1=REQ`) in AC-03 | `B3a` | 1 (FAIL) | `B3e` | **CAUGHT** (Caught by B3e) |
| `MUT_15_VIOLATE_AREA_LUT_MAX` | Area | Set AREA-01 LUT target to `<= 55,000` | `B4a` | 1 (FAIL) | `B4a`, `B4b` | **CAUGHT** (Expected) |
| `MUT_16_VIOLATE_AREA_DSP` | Area | Set AREA-03 DSP target to `80` in Table 10 | `B4d` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `MUT_17_CORRUPT_POWER_BUDGET` | Power | Change PWR-01 / PWR-03 target from `<= 50 mW` to `500 mW` | `N5b` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `MUT_18_CORRUPT_FR01_MESI` | Normative FR | Remove `MESI` keyword from FR-01 text | `M2-01` | 1 (FAIL) | `M2-01` | **CAUGHT** (Expected) |
| `MUT_19_CORRUPT_FR02_XY` | Normative FR | Remove `XY` routing from FR-02 text | `M2-02` | 1 (FAIL) | `M2-02` | **CAUGHT** (Expected) |
| `MUT_20_CORRUPT_FR04_PRIO` | Normative FR | Remove `RESP` class priority from FR-04 text | `M2-04` | 1 (FAIL) | `M2-04` | **CAUGHT** (Expected) |
| `MUT_21_CORRUPT_FR06_UNBLOCK` | Normative FR | Remove `UNBLOCK` keyword from FR-06 text | `M2-06` | 1 (FAIL) | `M2-06` | **CAUGHT** (Expected) |
| `MUT_22_UNLINK_FV_TEST` | Verification | Unlink FV-01 in Table 23 by setting requirement ID to `-` | `M4c` | 1 (FAIL) | `M4c` | **CAUGHT** (Expected) |
| `MUT_23_DROP_SVA_CATEGORY` | Verification | Remove all references to SVA category `A7` | `T07` | 1 (FAIL) | `T07` | **CAUGHT** (Expected) |
| `MUT_24_DROP_NETWORK_INV` | Verification | Remove all references to Network Invariant `I7` | `T08` | 1 (FAIL) | `T08` | **CAUGHT** (Expected) |
| `MUT_25_DUPLICATE_ROW` | Table Hygiene | Duplicate entire row in Table 2 (Glossary) | `M6a` | 1 (FAIL) | `M6a`, `M6b` | **CAUGHT** (Expected) |
| `MUT_26_DUPLICATE_KEY_DIFF_VAL` | Table Hygiene | Duplicate key with conflicting definition in Table 2 | `M6b` | 1 (FAIL) | `M6b` | **CAUGHT** (Expected) |
| `MUT_27_CORRUPT_MENTOR_NAME` | Approval | Replace `Mr. Hemat` with `Dr. Smith` in Table 25 (Approval) | `T11` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `MUT_28_EMPTY_GROUP_METADATA` | Metadata | Blank out Group number in Table 0 (Document Metadata) | `T12` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `MUT_29_DROP_DMA_REGISTER` | DMA | Remove `SRC_LO` register from Table 16 (DMA Register Map) | `T04` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `MUT_30_DROP_TIMING_RULES` | Timing | Remove `0.2 ns` and `WNS` from Table 15 / Section 7.4 | `T03` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `MUT_31_REINTRO_PHANTOM_A13` | Regressions | Reintroduce phantom assertion ID `A13` into FR-02 evidence | `B2a` | 1 (FAIL) | `B2a`, `B2b`, `B6a` | **CAUGHT** (Expected) |
| `MUT_32_REINTRO_VIRTUAL_BUFFER` | Regressions | Inject banned phrase `"virtual buffer"` into Section 2 | `N1a` | 1 (FAIL) | `N1a` | **CAUGHT** (Expected) |
| `MUT_33_REINTRO_DIR_SUBSCRIBER` | Regressions | Inject banned phrase `"Directory-to-subscriber"` | `B1e` | 1 (FAIL) | `B1e` | **CAUGHT** (Expected) |
| `MUT_34_STRIP_TBL_HEADER_XML` | XML Structure | Strip `w:tblHeader` from row 0 of all 26 tables | None | 0 (PASS) | None | **UNCHECKED FEATURE** |
| `MUT_35_STRIP_CANTSPLIT_XML` | XML Structure | Strip `w:cantSplit` from all 250 table rows | None | 0 (PASS) | None | **UNCHECKED FEATURE** |
| `MUT_36_CORRUPT_FF_TARGET_60K` | Area/FPGA | Set AREA-04 and FPGA-04 FF limit to `<= 60,000` | `T05` | 0 (PASS) | None | **FALSE NEGATIVE / BLIND SPOT** |
| `CORRUPT_EMPTY_FILE` | Robustness | 0-byte file passed to `--srs` | CLI/Parser | 1 (CRASH) | Python Exception | **CAUGHT** (Handled via nonzero exit) |
| `CORRUPT_MALFORMED_ZIP` | Robustness | Non-ZIP payload passed to `--srs` | CLI/Parser | 1 (CRASH) | Python Exception | **CAUGHT** (Handled via nonzero exit) |
| `CORRUPT_XML_SYNTAX` | Robustness | Corrupt XML syntax injected in `word/document.xml` | CLI/Parser | 1 (CRASH) | Python Exception | **CAUGHT** (Handled via nonzero exit) |

**Stress Test Summary**:
- Total Tests Executed: **39**
- Defect Caught by Verifier: **30** (76.9%)
- Confirmed Blind Spots / False Negatives: **7** (17.9%)
- Unchecked Architectural Features: **2** (5.1%)

---

## Detailed Challenge Findings (The 8 Verifier Blind Spots)

### [High Risk] Challenge 1: Unverified XML Table Formatting (`w:tblHeader` and `w:cantSplit`)
- **Assumption Challenged**: The verifier validates compliance with Project Feature 8 ("Professional XML Table Formatting: Set `w:tblHeader` on row 0 and `w:cantSplit` on all rows across all 23+ tables").
- **Attack Scenario**: Stripping `w:tblHeader` from all 26 tables (`MUT_34`) and `w:cantSplit` from all 250 rows (`MUT_35`).
- **Empirical Observation**: `verify_srs.py` does not inspect `w:trPr` or any XML node attributes. It extracts tables using `doc.element.body` child tags (`w:tbl`), returning plain text strings. Both mutations exited with code 0 (all 66 checks passed).
- **Blast Radius**: A document completely lacking page-break repeating headers or row split prevention passes verification, leading to unformatted or degraded output in Microsoft Word / PDF printing.
- **Recommended Mitigation**: Add a check `T13` that iterates over `doc.tables` and verifies `trPr.findall('{...}tblHeader')` on row 0, and `trPr.findall('{...}cantSplit')` on all rows.

### [High Risk] Challenge 2: Table Order Ambiguity in Message Direction Check `B1c`
- **Assumption Challenged**: `B1c` verifies message directions in Section 7.1's normative message table.
- **Attack Scenario**: Inverting PUTACK direction in Table 12 (Section 7.1) from `dir -> L1` to `L1 -> dir` (`MUT_13`).
- **Empirical Observation**: `row_with("PUTACK")` performs a linear search over all tables and returns the FIRST matching row. In `SRS_final_v2.docx`, Table 2 is the Glossary, which contains a `PUTACK` row that precedes Table 12. `B1c` inspects Table 2's description, while Table 12's direction column is never validated. `M1b` only checks `len(msg_rows) == 14`, completely ignoring message directions!
- **Blast Radius**: Inverted or illegal message directions in the normative architectural interface table pass verification undetected.
- **Recommended Mitigation**: Specifically locate the message table (`rows[0][0] == "Message"`) and validate the `Direction` column (index 1) for all core messages.

### [High Risk] Challenge 3: Global Substring Match for Power Budget in `N5b`
- **Assumption Challenged**: `N5b` enforces that the SRS power requirements comply with White Paper §6.4 (<= 50 mW).
- **Attack Scenario**: Corrupting `PWR-01` and `PWR-03` in Table 9 from `<= 50 mW` to `<= 500 mW` (`MUT_17`).
- **Empirical Observation**: `N5b` tests `"50 mw" in text.lower() or "50mw" in text.lower()`. This substring check evaluates over the entire document text. Even when Table 9 is corrupted to 500 mW, `"50 mW"` remains in Table 1 (Revision History notes) and narrative Section 6. `verify_srs.py` exits 0!
- **Blast Radius**: A 10x power budget violation in the actual requirements table is masked by historical text.
- **Recommended Mitigation**: Check `row_with("PWR-03")` specifically and assert that `row[2]` contains `<= 50 mW`.

### [High Risk] Challenge 4: False Negative in Flip-Flop Target Check `T05`
- **Assumption Challenged**: `T05` validates that Flip-Flop utilization is constrained to `<= 25,000`.
- **Attack Scenario**: Changing `AREA-04` and `FPGA-04` FF limits to `<= 60,000` (`MUT_36`).
- **Empirical Observation**: `T05` is implemented as:
  ```python
  check("T05", "Section 6 specifies Flip-Flop (FF) utilization (<= 25,000)",
        re.search(r"FPGA[^\n]*FF|Flip-Flop", text, re.I) and "25" in text, "")
  ```
  The substring `"25"` appears in unrelated rows: `PWR-02` (quiescent at 25°C), `PERF-02` (0.25 flits/cycle), etc. Consequently, `"25" in text` is perpetually True. The test passed with exit code 0 despite a 140% resource overrun!
- **Blast Radius**: Catastrophic FPGA resource over-allocation passes acceptance testing.
- **Recommended Mitigation**: Check `row_with("AREA-04")` and assert `re.search(r"25[,.]?000", row[2])`.

### [Medium Risk] Challenge 5: Loose Regex in DSP Target Check `B4d`
- **Assumption Challenged**: `B4d` ensures no DSP blocks are inferred (target = 0).
- **Attack Scenario**: Changing AREA-03 DSP design target in Table 10 from `0` to `80` (`MUT_16`).
- **Empirical Observation**: `B4d` checks:
  ```python
  re.search(r"AREA-0[3-9][^\n]*DSP", text) and re.search(r"AREA-0[3-9][^\n]*\b0\b", text)
  ```
  Because Column 3 (Ceiling) contains `0` and Column 4 (Notes) contains `"no multipliers"`, `\b0\b` matches the line even when Column 2 (Target) is set to `80`.
- **Blast Radius**: Inadvertent hardware multiplier synthesis passes acceptance check.
- **Recommended Mitigation**: Inspect `row_with("AREA-03")` columns 2 and 3 specifically: `r[2].strip() == "0" and r[3].strip() == "0"`.

### [Medium Risk] Challenge 6: Scope Ambiguity in Mentor Verification `T11`
- **Assumption Challenged**: `T11` ensures the Group Mentor is resolved to `Mr. Hemat` in the Approval Table (Table 25).
- **Attack Scenario**: Replacing `Mr. Hemat` with `Dr. Smith` in Table 25 (`MUT_27`).
- **Empirical Observation**: `T11` checks `any("mentor" in r[0].lower() and "hemat" in r[1].lower() for rows in tables for r in rows)`. Because Table 0 (Document Metadata) also contains a row `['Group Mentor', 'Mr. Hemat']`, corrupting Table 25 has no effect; `T11` still passes.
- **Blast Radius**: An unapproved or corrupted sign-off approval block is undetected.
- **Recommended Mitigation**: Filter for the Approval Table (`rows[0][0] == "Role"` or `rows[0][1] == "Name"`) and verify cell 1.

### [Medium Risk] Challenge 7: Disjunction Weakness in Section 7.4 Timing Rules `T03`
- **Assumption Challenged**: `T03` ensures timing margins (WNS, setup/hold uncertainty) are explicitly defined.
- **Attack Scenario**: Stripping setup/hold uncertainty and WNS from Section 7.4 / Table 15 (`MUT_30`).
- **Empirical Observation**: `T03` uses `any(k in text.lower() for k in ("setup uncertainty", "0.2 ns", "wns"))`. First, `any` requires only 1 of 3 matches. Second, `"wns"` appears in Table 1, narrative Section 6, Table 21 (FPGA-02), and Table 24. Even if Section 7.4 is empty, `T03` passes.
- **Blast Radius**: Omission of interface timing budget constraints in Section 7.4 goes undetected.
- **Recommended Mitigation**: Require `all` key timing terms (`"setup uncertainty"`, `"0.200 ns"` or `"0.2 ns"`, `"wns"`) to be present in the timing section / Table 15.

### [Low Risk] Challenge 8: Substring Matching on DMA Registers `T04`
- **Assumption Challenged**: `T04` ensures Section 7.5 enumerates all 6 DMA registers.
- **Attack Scenario**: Removing `SRC_LO` from Table 16 (`MUT_29`).
- **Empirical Observation**: `T04` tests `all(reg in text for reg in dma_regs)`. Table 13 (Signal List notes) contains `DMA_SRC_LO`. Thus `"SRC_LO" in text` is satisfied by Table 13 notes even if Table 16 is deleted.
- **Blast Radius**: Incomplete register map table passes verification.
- **Recommended Mitigation**: Locate the DMA register table directly (`rows[0][1] == "Name"`) and check `{r[1] for r in rows[1:]}`.

---

## Evaluation of Baseline Regression (`SRS_final.docx --baseline`)

We executed:
```bash
python3 verify_srs.py --srs white_papers/final/SRS_final.docx --baseline
```
- **Exit Code**: `0`
- **Result**: `RESULT: PASS - 41/41 SRS checks passed`
- **Finding**: Backwards compatibility of `verify_srs.py` on the baseline v0.2 artifact is fully preserved.

When executed WITHOUT `--baseline` on `SRS_final.docx`:
- **Exit Code**: `1`
- **Result**: `RESULT: FAIL - 56/66 SRS checks passed`
- **Failures Detected**:
  1. `B6c`: Untraced requirements in baseline (18 non-FR requirements untraced)
  2. `M3c`: Missing code coverage targets
  3. `M4c`: Unlinked FPGA validation tests (`FV-13`, `FV-14`)
  4. `N5b`: Power requirement <= 50 mW missing
  5. `T01`: PERF-01 clock frequency was `TBD`
  6. `T02`: FPGA-01 frequency was `TBD`
  7. `T06`: PPA priority order missing
  8. `T08`: Network invariants I1-I7 missing
  9. `T10`: Placeholder `[Name]` present in Table 22
  10. `T11`: Mentor was `[Name]`, not `Mr. Hemat`

This proves that `verify_srs.py` successfully discriminates between the baseline and elevated documents across all major feature areas.

---

## Verdict and Recommendations

### Verdict: **CONDITIONAL APPROVAL (Document APPROVE / Verifier REJECT Pending Hardening)**

1. **`SRS_final_v2.docx`**: **APPROVED**.
   - Conforms to IEEE 830 / ISO/IEC/IEEE 29148 structure.
   - All 26 tables have `w:tblHeader` on row 0.
   - All 250 rows have `w:cantSplit`.
   - Full 44-row bidirectional traceability matrix.
   - PPA numbers, timing closures (100 MHz, WNS>=0, <=50 mW), message directions, and pin assignments are 100% compliant with white paper ground truth.

2. **`verify_srs.py`**: **REJECTED (Hardening Required)**.
   - The verifier must be updated to address the 8 identified false negatives and blind spots.
   - Specifically:
     - Replace global `"in text"` checks with table-scoped cell assertions.
     - Add XML property checks for `w:tblHeader` and `w:cantSplit`.
     - Remove dead CLI arguments (`--wp`, `--spec`, `--dir`) or implement actual cross-file verification.
