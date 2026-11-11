# Changes Log: Verifier Hardening (Worker Verifier Hardener 1)

**Target Script:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py`  
**Date:** 2026-11-09  
**Objective:** Harden `verify_srs.py` to eliminate 8 false-negative blind spots discovered during adversarial mutation testing by Challenger 1, ensure full backward compatibility on baseline v0.2, and fix traceability requirement regex.

---

## 1. Summary of Changes Made to `verify_srs.py`

| Check ID | Area / Category | Original Flaw / Blind Spot | Applied Hardening Patch | Result on Mutant |
|---|---|---|---|---|
| **`T13`** | XML Table Formatting | Verifier did not check `w:tblHeader` or `w:cantSplit` attributes in OpenXML. Stripped XML passed 0. | Added check `T13`: iterates through `doc.tables`, asserts row 0 has `w:tblHeader` in `r._tr.xpath('./w:trPr/w:tblHeader')` and all rows have `w:cantSplit` in `r._tr.xpath('./w:trPr/w:cantSplit')`. | `MUT_34` and `MUT_35` cleanly CAUGHT (FAIL). |
| **`B1c`** | Message Direction | `row_with("PUTACK")` performed linear scan and grabbed Glossary (Table 2), ignoring Section 7.1 Message Table (Table 12). | Specifically locate the Message table (`rows[0][0].strip().lower() == "message"`) and assert that `PUTACK` direction (column 1) contains `dir -> l1` or `dir -> requester`. | `MUT_13` (reversed PUTACK direction) cleanly CAUGHT (FAIL). |
| **`N5b`** | Power Budget | Global substring search `"50 mw" in text.lower()` matched Table 1 revision history, ignoring Table 9 corruptions. | Specifically inspect `row_with("PWR-03")` target cell (column 2) to ensure it contains `<= 50` or `<= 50 mw`, and check `row_with("PWR-01")` target cell does not exceed 50 mW. | `MUT_17` (power corrupted to 500 mW) cleanly CAUGHT (FAIL). |
| **`T05`** | Flip-Flop Target | Tested `"25" in text`, which matched unrelated cells like `PWR-02` (25°C) or `PERF-02` (0.25 flits/cycle). | Check `row_with("AREA-04")` specifically and assert target cell (column 2) contains `25,000` or `25000`. | `mut_ff_60k` (FF target set to <= 60,000) cleanly CAUGHT (FAIL). |
| **`B4d`** | DSP Utilization | Regex `AREA-0[3-9][^\n]*\b0\b` matched ceiling column or notes even when target was set to 80. | Check `row_with("AREA-03")` specifically and assert that both target cell (`r[2]`) and ceiling cell (`r[3]`) equal `0`. | `MUT_16` (DSP target set to 80) cleanly CAUGHT (FAIL). |
| **`T11`** | Mentor Approval | Checked `any("mentor" in r[0] and "hemat" in r[1])` across all tables, satisfying check via Table 0 metadata rather than Table 25 Approval. | Locate Approval table specifically (`rows[0][0].strip().lower() == "role"` or contains `"mentor"`) and verify `Mr. Hemat` in the mentor row cell 1. | `MUT_27` (Mentor set to Dr. Smith in Approval table) cleanly CAUGHT (FAIL). |
| **`T03`** | Timing Rules | Used `any(...)` on global text for setup uncertainty, 0.2 ns, and WNS. Global text satisfied check even if timing section was empty. | Locate Section 7.4 Timing Budget table (`rows[0][0] == "parameter"` and `rows[0][1] == "value"`) and assert `setup uncertainty`, `0.2`, and `wns` all appear in this table. | `MUT_30` (timing rules stripped from Section 7.4) cleanly CAUGHT (FAIL). |
| **`T04`** | DMA Register Map | Checked global text for register names; satisfied by Table 13 Signal list notes even if Table 16 was deleted. | Locate DMA register table (`rows[0][1].strip().lower() == "name"` and `rows[0][0].strip().lower() in ("offset", "address")) and verify all 6 register names (`SRC_LO, DST_LO, LEN, CTRL, STATUS, COUNT`). | `MUT_29` (SRC_LO removed from Table 16) cleanly CAUGHT (FAIL). |
| **`T12`** | Metadata Group Name | Global regex `Group\s*[:|]\s*...` matched Table 25 `Prepared by (group)`. | Specifically inspect Table 0 Metadata table for `r[0].strip().lower() == "group"` and verify non-empty value. | `MUT_28` (Group blanked out) cleanly CAUGHT (FAIL). |
| **`B6c`** | Traceability Extraction | Regex `^((?:FR|PERF|PWR|AREA|FPGA)-\d+[a-z]?)` omitted `AC-\d+` (Assumptions and Constraints AC-01..AC-05). | Updated regex to `^((?:FR|AC|PERF|PWR|AREA|FPGA)-\d+[a-z]?)`. All 45 requirements are now extracted and verified against traceability matrix. | Traceability count correctly reports 45 total (was 40). |

---

## 2. Test Execution Logs

### 2.1 Acceptance Run on Target Document (`SRS_final_v2.docx`)
```bash
$ python3 verify_srs.py --srs white_papers/final/SRS_final_v2.docx
RESULT: PASS - 67/67 SRS checks passed

[PASS] B1a      PUTS is described as L1 -> directory                                                                         ['PUTS', 'L1 -> directory release notification (clean line; no data)']
[PASS] B1b      PUTM is described as L1 -> directory                                                                         ['PUTM', 'L1 -> directory release notification (dirty line; carries the data)']
[PASS] B1c      PUTACK is described as directory -> L1                                                                       ['PUTACK', 'dir -> L1', 'RESP', 'VC2', '1']
[PASS] B1d      UNBLOCK is described as L1 -> directory                                                                      ['UNBLOCK', "L1 -> directory release event that selects the directory's successor state"]
[PASS] B1e      no 'Directory-to-subscriber' direction remains                                                               
[PASS] B2a      the phantom assertion id A13 is gone from the SRS                                                            
[PASS] B2b      FR-02 is verified by A8.x and/or I1                                                                          ['FR-02', 'The system shall deliver each message by XY deterministic routing (X then Y).', 'Must', 'A8.x / I1 / TC-02']
[PASS] B3a      AC-03 states VC0 = REQ                                                                                       ['AC-03', 'Four virtual channels with index order VC0 = REQ, VC1 = FWD, VC2 = RESP, VC3 = INV; escape priority order RESP > INV > FWD > REQ.']
[PASS] B3b      AC-03 states VC1 = FWD                                                                                       
[PASS] B3c      AC-03 states VC2 = RESP                                                                                      
[PASS] B3d      AC-03 states VC3 = INV                                                                                       
[PASS] B3e      the VC index order is stated as REQ, FWD, RESP, INV (not the priority order)                                 
[PASS] B4a      AREA-01's LUT target is a design target (<=20,000), not device capacity                                      ['AREA-01', 'FPGA LUT utilization (2x2)', '<= 20,000 (38 % of 53,200); estimate ~13,000-19,000', '<= 40,000 (75 %)', '2x2 build', 'Synthesis']
[PASS] B4b      AREA-01's LUT maximum is <= 40,000                                                                           ['AREA-01', 'FPGA LUT utilization (2x2)', '<= 20,000 (38 % of 53,200); estimate ~13,000-19,000', '<= 40,000 (75 %)', '2x2 build', 'Synthesis']
[PASS] B4c      AREA-02's BRAM target is <= 48 with a ceiling of 80                                                          ['AREA-02', 'FPGA BRAM36 utilization (2x2)', '<= 48; estimate 28 (favourable mapping)', '<= 80', '2x2 build', 'Synthesis']
[PASS] B4d      a DSP row exists with target 0                                                                               ['AREA-03', 'FPGA DSP utilization', '0', '0', '2x2 build - no multipliers inferred', 'Synthesis']
[PASS] B4e      FPGA-05 no longer asserts 80 DSP                                                                             [['FPGA-05a', 'BRAM36 utilization', '<= 48', '<= 80', 'Synthesis'], ['FPGA-05b', 'DSP utilization', '0', '0', 'Synthesis'], ['FPGA-05a', 'Synthesis', 'Implementation utilization report (BRAM36)', 'Planned'], ['FPGA-05b', 'Synthesis', 'Implementation utilization report (DSP)', 'Planned']]
[PASS] B5a      no bare DMA write signal appears in the signal list                                                          []
[PASS] B5b      the DMA interface is marked absent from the 2x2 build                                                        
[PASS] B6a      no requirement cites a finding id (A13/G*) or a ruling id (B*) as its evidence                               []
[PASS] B6b      every FR is traced in the traceability table                                                                 untraced: []
[PASS] M1a      all 12 core + 2 gated messages appear in the SRS                                                             missing: []
[PASS] M2-09    FR-09 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)                   
[PASS] M2-10    FR-10 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)                   
[PASS] M2-11    FR-11 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)                   
[PASS] M2-12    FR-12 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)                   
[PASS] M2-13    FR-13 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)                   
[PASS] M2-14    FR-14 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)                   
[PASS] M3a      coverage targets are numeric (at least three numeric targets)                                                numeric targets: 7
[PASS] M3b      the four WP coverage criteria are present                                                                    
[PASS] M4a      the directed test plan has at least 14 rows                                                                  17 rows
[PASS] M4b      the FPGA test plan has at least 14 rows                                                                      14 rows
[PASS] M5a      the proof parameters are marked proposed                                                                     
[PASS] M5b      both liveness bounds appear (2x2 and 4x4)                                                                    
[PASS] M6a      no table repeats an identical row                                                                            []
[PASS] M6b      no table repeats the same key with different values                                                          []
[PASS] N1a      the SRS says 'virtual channel', not 'virtual buffer'                                                         
[PASS] N2a      the conditional DMA tests are marked conditional                                                             
[PASS] N4a      the performance section states known latency figures                                                         
[PASS] N5a      power is explicitly scoped or flagged                                                                        
[PASS] N6a      the verification exit criteria mention zero waivers                                                          
[PASS] M2-01    FR-01 exists and defines directory-based MESI coherence                                                      FR-01 The system shall maintain directory-based ME
[PASS] M2-02    FR-02 exists and defines XY deterministic routing                                                            FR-02 The system shall deliver each message by XY 
[PASS] M2-03    FR-03 exists and defines credit-based flow control with depth 4                                              FR-03 The system shall use credit-based flow contr
[PASS] M2-04    FR-04 exists and defines arbitration priority and 13-round bound                                             FR-04 The system shall arbitrate VCs by class prio
[PASS] M2-05    FR-05 exists and defines non-silent eviction with PUTS/PUTM/PUTACK                                           FR-05 The system shall evict with PUTS/PUTM + PUTA
[PASS] M2-06    FR-06 exists and defines single-exit directory FSM via UNBLOCK                                               FR-06 The system shall implement single-exit direc
[PASS] M2-07    FR-07 exists and defines DMA write path gated to 4x4 simulation scope                                        FR-07 The system shall support the DMA write path 
[PASS] M2-08    FR-08 exists and defines 512-bit intra-tile line transfer                                                    FR-08 The system shall move a whole cache line in 
[PASS] B6c      Traceability matrix traces all defined requirements (45 total)                                               untraced: []
[PASS] M1b      Section 7.1 message table contains exactly 14 message rows                                                   14 rows
[PASS] M3c      Section 8.3 specifies code coverage targets (statement, branch, toggle)                                      found 3 rows
[PASS] M4c      All FPGA validation tests (FV) are linked to a requirement ID                                                unlinked: []
[PASS] N5b      Power requirement reflects WP 6.4 budget (total <= 50 mW)                                                    ['PWR-03', 'Total power', '<= 50 mW', '<= 75 mW', '100 MHz, full 2x2 operational workload', 'XPE pre-synthesis / report_power post-implementation (WP §6.4)']
[PASS] T01      PERF-01 specifies 100 MHz clock frequency (not TBD)                                                          100 MHz (10.0 ns)
[PASS] T02      FPGA-01 specifies 100 MHz on-board frequency (not TBD)                                                       100 MHz (10.0 ns)
[PASS] T03      Section 7.4 timing rules specify concrete WNS and setup/hold uncertainty                                     timing table: 10 rows
[PASS] T04      Section 7.5 enumerates the 6 DMA channel registers                                                           missing: set()
[PASS] T05      Section 6 specifies Flip-Flop (FF) utilization (<= 25,000)                                                   <= 25,000 (23.5 % of 106,400)
[PASS] T06      Section 6 explicitly defines PPA trade-off priority order                                                    
[PASS] T07      SRS references all 8 SVA categories (A1 through A8)                                                          
[PASS] T08      SRS references all 7 network invariants (I1 through I7)                                                      
[PASS] T09      Signal list contains core control and credit signals (clk, reset, credit_in, credit_out)                     missing: set()
[PASS] T10      No template placeholders ([Name], [Group...], TODO) remain                                                   found: []
[PASS] T11      Approval table lists Mr. Hemat as Group Mentor (not [Name])                                                  Mr. Hemat
[PASS] T12      Document metadata specifies valid, non-empty Group name                                                      Group 16 (PGCP VLSI)
[PASS] T13      All tables have repeating header (w:tblHeader) on row 0 and row split protection (w:cantSplit) on all rows   26 tables verified

Exit code: 0
```

### 2.2 Backward Compatibility Run on Baseline Document (`SRS_final.docx --baseline`)
```bash
$ python3 verify_srs.py --srs white_papers/final/SRS_final.docx --baseline
RESULT: PASS - 41/41 SRS checks passed

[PASS] B1a      PUTS is described as L1 -> directory                                                         ['PUTS', 'L1 -> directory release notification (clean line; no data)']
[PASS] B1b      PUTM is described as L1 -> directory                                                         ['PUTM', 'L1 -> directory release notification (dirty line; carries the data)']
[PASS] B1c      PUTACK is described as directory -> L1                                                       ['PUTACK', 'dir -> L1', 'RESP', 'VC2', '1']
[PASS] B1d      UNBLOCK is described as L1 -> directory                                                      ['UNBLOCK', "L1 -> directory release event that selects the directory's successor state"]
[PASS] B1e      no 'Directory-to-subscriber' direction remains                                               
[PASS] B2a      the phantom assertion id A13 is gone from the SRS                                            
[PASS] B2b      FR-02 is verified by A8.x and/or I1                                                          ['FR-02', 'The system shall deliver each message by XY deterministic routing (X then Y).', 'Must', 'A8.x / I1 / TC-02']
[PASS] B3a      AC-03 states VC0 = REQ                                                                       ['AC-03', 'Four virtual channels per port, indexed at the source and never altered by a router: VC0 = REQ (GETS, GETM, PUTS, PUTM, DMA_WRITE*), VC1 = FWD (FWD_GETS, FWD_GETM), VC2 = RESP (DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, DMA_ACK*), VC3 = INV (INV). Arbitration priority across classes is fixed: RESP > INV > FWD > REQ, with the age escape.']
[PASS] B3b      AC-03 states VC1 = FWD                                                                       
[PASS] B3c      AC-03 states VC2 = RESP                                                                      
[PASS] B3d      AC-03 states VC3 = INV                                                                       
[PASS] B3e      the VC index order is stated as REQ, FWD, RESP, INV (not the priority order)                 
[PASS] B4a      AREA-01's LUT target is a design target (<=20,000), not device capacity                      ['AREA-01', 'FPGA LUT utilization (2x2)', '<= 20,000 (38 % of 53,200); estimate ~13,000-19,000', '<= 40,000 (75 %)', '2x2 build', 'Synthesis']
[PASS] B4b      AREA-01's LUT maximum is <= 40,000                                                           ['AREA-01', 'FPGA LUT utilization (2x2)', '<= 20,000 (38 % of 53,200); estimate ~13,000-19,000', '<= 40,000 (75 %)', '2x2 build', 'Synthesis']
[PASS] B4c      AREA-02's BRAM target is <= 48 with a ceiling of 80                                          ['AREA-02', 'FPGA BRAM36 utilization (2x2)', '<= 48; estimate 28 (favourable mapping)', '<= 80', '2x2 build', 'Synthesis']
[PASS] B4d      a DSP row exists with target 0                                                               ['AREA-03', 'FPGA DSP utilization', '0', '0', '2x2 build - no multipliers inferred', 'Synthesis']
[PASS] B4e      FPGA-05 no longer asserts 80 DSP                                                             [['FPGA-05a', 'BRAM36 utilization', '<= 48', '<= 80', 'Synthesis'], ['FPGA-05b', 'DSP utilization', '0', '0', 'Synthesis']]
[PASS] B5a      no bare DMA write signal appears in the signal list                                          []
[PASS] B5b      the DMA interface is marked absent from the 2x2 build                                        
[PASS] B6a      no requirement cites a finding id (A13/G*) or a ruling id (B*) as its evidence               []
[PASS] B6b      every FR is traced in the traceability table                                                 untraced: []
[PASS] M1a      all 12 core + 2 gated messages appear in the SRS                                             missing: []
[PASS] M2-09    FR-09 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)   
[PASS] M2-10    FR-10 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)   
[PASS] M2-11    FR-11 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)   
[PASS] M2-12    FR-12 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)   
[PASS] M2-13    FR-13 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)   
[PASS] M2-14    FR-14 exists (forward release, exclusive bit, L2 word, dirty bit, write-back, receptivity)   
[PASS] M3a      coverage targets are numeric (at least three numeric targets)                                numeric targets: 5
[PASS] M3b      the four WP coverage criteria are present                                                    
[PASS] M4a      the directed test plan has at least 14 rows                                                  14 rows
[PASS] M4b      the FPGA test plan has at least 14 rows                                                      14 rows
[PASS] M5a      the proof parameters are marked proposed                                                     
[PASS] M5b      both liveness bounds appear (2x2 and 4x4)                                                    
[PASS] M6a      no table repeats an identical row                                                            []
[PASS] M6b      no table repeats the same key with different values                                          []
[PASS] N1a      the SRS says 'virtual channel', not 'virtual buffer'                                         
[PASS] N2a      the conditional DMA tests are marked conditional                                             
[PASS] N4a      the performance section states known latency figures                                         
[PASS] N5a      power is explicitly scoped or flagged                                                        
[PASS] N6a      the verification exit criteria mention zero waivers                                          

Exit code: 0
```

### 2.3 Adversarial Mutation Suite Run (`run_mutations.py` across 38 tests)
```bash
$ python3 /tmp/srs_adversarial_test/run_mutations.py
Executing 35 semantic mutations + 3 robustness corruptions...
[SUCCESS_CAUGHT] MUT_01_DEL_PERF01_TRACE: Cleanly caught by ['B6c']
[SUCCESS_CAUGHT] MUT_02_DEL_FR05_TRACE: Cleanly caught by ['B6b', 'B6c']
[SUCCESS_CAUGHT] MUT_03_REINTRO_TBD_PERF01: Cleanly caught by ['T01']
[SUCCESS_CAUGHT] MUT_04_REINTRO_TBD_FPGA01: Cleanly caught by ['T02']
[SUCCESS_CAUGHT] MUT_05_REINTRO_NAME_PLACEHOLDER: Cleanly caught by ['T10', 'T12']
[SUCCESS_CAUGHT] MUT_06_REINTRO_TODO_PLACEHOLDER: Cleanly caught by ['T10']
[SUCCESS_CAUGHT] MUT_07_BREAK_CREDIT_IN_SIGNAL: Cleanly caught by ['T09']
[SUCCESS_CAUGHT] MUT_08_BREAK_RESET_SIGNAL: Cleanly caught by ['T09']
[SUCCESS_CAUGHT] MUT_09_ADD_BARE_DMA_SIGNAL_2X2: Cleanly caught by ['B5a', 'T13']
[SUCCESS_CAUGHT] MUT_10_DROP_CODE_COVERAGE_ROWS: Cleanly caught by ['M3c']
[SUCCESS_CAUGHT] MUT_11_DROP_ALL_COVERAGE_ROWS: Cleanly caught by ['M3c']
[SUCCESS_CAUGHT] MUT_12_DEL_PUTACK_MSG_ROW: Cleanly caught by ['B1c', 'M1b']
[SUCCESS_CAUGHT] MUT_13_REVERSE_PUTACK_DIR: Cleanly caught by ['B1c']
[CAUGHT_DIFFERENT_CHECK] MUT_14_CORRUPT_VC_MAPPING_AC03: Caught by ['B3e'] instead of expected B3a
[SUCCESS_CAUGHT] MUT_15_VIOLATE_AREA_LUT_MAX: Cleanly caught by ['B4a', 'B4b']
[SUCCESS_CAUGHT] MUT_16_VIOLATE_AREA_DSP: Cleanly caught by ['B4d']
[SUCCESS_CAUGHT] MUT_17_CORRUPT_POWER_BUDGET: Cleanly caught by ['N5b']
[SUCCESS_CAUGHT] MUT_18_CORRUPT_FR01_MESI: Cleanly caught by ['M2-01']
[SUCCESS_CAUGHT] MUT_19_CORRUPT_FR02_XY: Cleanly caught by ['M2-02']
[SUCCESS_CAUGHT] MUT_20_CORRUPT_FR04_PRIO: Cleanly caught by ['M2-04']
[SUCCESS_CAUGHT] MUT_21_CORRUPT_FR06_UNBLOCK: Cleanly caught by ['M2-06']
[SUCCESS_CAUGHT] MUT_22_UNLINK_FV_TEST: Cleanly caught by ['M4c']
[SUCCESS_CAUGHT] MUT_23_DROP_SVA_CATEGORY: Cleanly caught by ['T07']
[SUCCESS_CAUGHT] MUT_24_DROP_NETWORK_INV: Cleanly caught by ['T08']
[SUCCESS_CAUGHT] MUT_25_DUPLICATE_ROW: Cleanly caught by ['M6a', 'M6b', 'T13']
[SUCCESS_CAUGHT] MUT_26_DUPLICATE_KEY_DIFF_VAL: Cleanly caught by ['M6b', 'T13']
[SUCCESS_CAUGHT] MUT_27_CORRUPT_MENTOR_NAME: Cleanly caught by ['T11']
[SUCCESS_CAUGHT] MUT_28_EMPTY_GROUP_METADATA: Cleanly caught by ['T12']
[SUCCESS_CAUGHT] MUT_29_DROP_DMA_REGISTER: Cleanly caught by ['T04']
[SUCCESS_CAUGHT] MUT_30_DROP_TIMING_RULES: Cleanly caught by ['T03']
[SUCCESS_CAUGHT] MUT_31_REINTRO_PHANTOM_A13: Cleanly caught by ['B2a', 'B2b', 'B6a']
[SUCCESS_CAUGHT] MUT_32_REINTRO_VIRTUAL_BUFFER: Cleanly caught by ['N1a']
[SUCCESS_CAUGHT] MUT_33_REINTRO_DIR_SUBSCRIBER: Cleanly caught by ['B1e']
[SURPRISE_FAILURE] MUT_34_STRIP_TBL_HEADER_XML: Unexpectedly failed on ['T13']
[SURPRISE_FAILURE] MUT_35_STRIP_CANTSPLIT_XML: Unexpectedly failed on ['T13']
[CAUGHT_EXCEPTION] CORRUPT_EMPTY_FILE: Returncode 1, stderr: Traceback (most recent call last)...
[CAUGHT_EXCEPTION] CORRUPT_MALFORMED_ZIP: Returncode 1, stderr: Traceback (most recent call last)...
[CAUGHT_EXCEPTION] CORRUPT_XML_SYNTAX: Returncode 1, stderr: Traceback (most recent call last)...

================================================================================
MUTATION STRESS TEST SUMMARY: Total=38, Caught=36, Blind Spots/Unchecked=0
================================================================================
```
Note: In the harness, `MUT_34` and `MUT_35` were registered with `expected_to_fail=False` because they were previously unverified features; catching them with `T13` resulted in `[SURPRISE_FAILURE]`, proving both XML mutations are now actively caught.

### 2.4 Targeted Verification of `mut_ff_60k.docx`
```bash
$ python3 verify_srs.py --srs /tmp/srs_adversarial_test/mut_ff_60k.docx
RESULT: FAIL - 66/67 SRS checks passed
[FAIL] T05      Section 6 specifies Flip-Flop (FF) utilization (<= 25,000)                                   <= 60,000 (23.5 % of 106,400)
Exit code: 1
```
Targeted mutation for Flip-Flop budget violation is cleanly detected by hardened `T05`.
