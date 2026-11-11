# Forensic Audit Report: Milestone 2 Deliverables

- **Auditor:** `auditor_m2_1` (Forensic Auditor)
- **Target Work Product:** Milestone 2 (`tb_acceptance/l1_dir/test_l1_dir.py`, `tb_acceptance/l1_dir/l1_dir_tb_wrapper.sv`, `tb_acceptance/ref_model/slice_ref_model.py`) in `~/teamwork_projects/clean_room_verification`
- **Integrity Enforcement Mode:** Demo Mode (per `ORIGINAL_REQUEST.md`)
- **Final Verdict:** **CLEAN**

---

## 1. Observation

### 1.1 RTL Snapshot Preservation & Checksums
- **Check Command 1:**
  ```bash
  cd /mnt/Code/visualstudio/Design-arch_multi-core && md5sum -c rtl_frozen/FROZEN.md5
  ```
  *Output Verbatim:*
  ```
  rtl_frozen/pkg/tile_pkg.sv: OK
  rtl_frozen/l1/l1_mesi_ctrl.sv: OK
  rtl_frozen/directory/dir_ctrl.sv: OK
  ```
- **Check Command 2:**
  ```bash
  cd ~/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5
  ```
  *Output Verbatim:*
  ```
  rtl_frozen/pkg/tile_pkg.sv: OK
  rtl_frozen/l1/l1_mesi_ctrl.sv: OK
  rtl_frozen/directory/dir_ctrl.sv: OK
  ```
- Git status check in main repository: `git status --porcelain rtl_frozen/` reports `?? rtl_frozen/` (untracked, unmodified snapshot). Zero lines of frozen RTL code were touched or patched.

### 1.2 Clean-Room Isolation & AST / Text Similarity Analysis
Comparative analysis between quarantined self-test files (`tb_self_test/l1_dir/*`, `tb/ref_model/*`) and clean-room acceptance files (`tb_acceptance/l1_dir/*`, `tb_acceptance/ref_model/*`):

- **Python difflib / SequenceMatcher similarity analysis:**
  - `test_l1_dir.py` (647 lines) vs `tb_common.py`: similarity ratio = **0.0097**, longest match block = **1 line**
  - `test_l1_dir.py` vs `test_f1_forward.py`: similarity ratio = **0.0118**, longest match block = **1 line**
  - `test_l1_dir.py` vs `test_f2_f8.py`: similarity ratio = **0.0109**, longest match block = **1 line**
  - `test_l1_dir.py` vs `tb_l1_dir.sv`: similarity ratio = **0.0000**, longest match block = **0 lines**
  - `test_l1_dir.py` vs `shadow_l1_dir.py`: similarity ratio = **0.0023**, longest match block = **1 line**
  - `l1_dir_tb_wrapper.sv` (513 lines) vs `tb_l1_dir.sv`: similarity ratio = **0.1014** (standard SystemVerilog port types from `tile_pkg.sv`), longest match block = **2 lines**
  - `slice_ref_model.py` (485 lines) vs `shadow_l1_dir.py`: similarity ratio = **0.0167**, longest match block = **1 line**
- **Structural differences:**
  - `tb_l1_dir.sv` was a 2-core testbench (`core0`, `core1`). `l1_dir_tb_wrapper.sv` is a full 4-tile testbench (`t0`, `t1`, `t2`, `t3`) instantiating four `l1_mesi_ctrl` instances (`u_l1_0` to `u_l1_3`) and one `dir_ctrl` (`u_dir_0`), with 32-entry wormhole packet FIFOs, multi-flit length counters, packet arbiter, response demux, and a 256-line synchronous L2 bank backing store.
  - `shadow_l1_dir.py` was a 2-core dynamic tap listener using string states (`"I"`, `"S"`, `"E"`, `"M"`) with known deferral bugs (e.g. line 98 eagerly committing sharers). `slice_ref_model.py` is a 4-tile typed reference model strictly implementing Slice 16.1 Rules 1–11 with formal deferral semantics, comprehensive mismatch logging, and dual-mode comparison scoreboards.
- **Forbidden file check:**
  - `find ~/teamwork_projects/clean_room_verification -type f` confirmed that zero files from `tb_self_test/` or `tb/` were copied into the clean-room workspace.

### 1.3 Static Code Analysis & Facade Detection
- **RTL Stimulus & Observation:**
  - `l1_dir_tb_wrapper.sv` directly maps ports of the four `l1_mesi_ctrl` modules and `dir_ctrl` module to top-level signals (`t0_l1_state`, `t1_l1_state`, `dir_state_o`, `dir_owner_o`, `dir_sharers_o`, `bank_dirty_o`).
  - `test_l1_dir.py` uses `wait_until_cond` (lines 107–113) which polls simulation cycles waiting for RTL signals to change. If the RTL fails to make the transition, a `TimeoutError` is thrown.
  - Every single test F1 through F8 asserts against live DUT values:
    - F1: lines 144–147, 170–174, 183 (`assert rep["mismatch_count"] == 0`)
    - F2: lines 210–212, 230–235, 244 (`assert rep["mismatch_count"] == 0`)
    - F3: lines 270–271, 287–291, 300 (`assert rep["mismatch_count"] == 0`)
    - F4: lines 327–328, 344–349, 358 (`assert rep["mismatch_count"] == 0`)
    - F5: lines 386–387, 393–394, 409–413, 421 (`assert rep["mismatch_count"] == 0`)
    - F6: lines 450–451, 470–474, 483 (`assert rep["mismatch_count"] == 0`)
    - F7: lines 513–514, 533–538, 547 (`assert rep["mismatch_count"] == 0`)
    - F8: lines 573, 587, 590, 608, 631, 634, 647 (`assert rep["mismatch_count"] == 0`)
  - No dummy pass, no `assert True`, and no hardcoded outputs bypassing simulation.

### 1.4 Behavioral Verification & Independent Execution
- **Fresh Simulation Execution:**
  ```bash
  export PATH="/home/durgesh/.local/share/pipx/venvs/cocotb/bin:/usr/bin:/home/durgesh/.local/oss-cad-suite/bin:$PATH"
  cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
  make clean && make
  ```
  - `make clean` removed `results.xml` and `sim_build`.
  - `iverilog` successfully compiled `rtl_frozen/pkg/tile_pkg.sv`, `rtl_frozen/l1/l1_mesi_ctrl.sv`, `rtl_frozen/directory/dir_ctrl.sv`, and `l1_dir_tb_wrapper.sv` into `sim_build/sim.vvp`.
  - Cocotb 2.1.0 executed all 8 testcases against `sim.vvp`:
    ```
    **************************************************************************************************************
    ** TEST                                                  STATUS  SIM TIME (ns)  REAL TIME (s)  RATIO (ns/s) **
    **************************************************************************************************************
    ** test_l1_dir.test_f1_forward_clean_owner                PASS         780.00           0.02      42439.68  **
    ** test_l1_dir.test_f2_forward_dirty_owner                PASS         790.00           0.01      98935.74  **
    ** test_l1_dir.test_f3_forward_gets_from_dir_m            PASS         790.00           0.01      81403.94  **
    ** test_l1_dir.test_f4_forward_getm_from_dir_e            PASS         790.00           0.01     105407.84  **
    ** test_l1_dir.test_f5_silent_upgrade_then_eviction       PASS         580.00           0.01      90982.68  **
    ** test_l1_dir.test_f6_evict_during_forward_clean_owner   PASS         670.00           0.01      94582.64  **
    ** test_l1_dir.test_f7_evict_during_forward_dirty_owner   PASS         750.00           0.01      90103.62  **
    ** test_l1_dir.test_f8_exclusive_bit_correctness          PASS        1820.00           0.02      92187.67  **
    **************************************************************************************************************
    ** TESTS=8 PASS=8 FAIL=0 SKIP=0                                       6970.01           0.09      78925.95  **
    **************************************************************************************************************
    ```
  - Newly generated `results.xml` attests: `timestamp="2026-11-05T18:37:32.782648+00:00" tests="8" errors="0" failures="0" skipped="0"`.

### 1.5 Adversarial Scoreboard Stress Testing & Fault Injection
- Executed negative fault injection on `SliceRefModel`:
  - When matching data is supplied: `report()` returns `status: PASS, mismatch_count: 0`.
  - When corrupting L1 state: flagged mismatch `[SCOREBOARD MISMATCH] Tile 0 L1 State: Expected=L1_E(2), Actual=L1_M(3)`, `status: FAIL`.
  - When corrupting Directory state: flagged mismatch `[SCOREBOARD MISMATCH] Directory State: Expected=DIR_E(2), Actual=DIR_S(1)`, `status: FAIL`.
  - When corrupting Bank dirty bit: flagged mismatch `[SCOREBOARD MISMATCH] Bank Dirty for line 0x00000040: Expected=0, Actual=1`, `status: FAIL`.
- Ran peer challenger suite (`python3 /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/test_slice_ref_model_challenge.py`):
  - 39 independent unit tests covering all 11 Slice rules, boundary conditions, and corruptions: **39/39 PASSED in 0.003s**.

---

## 2. Logic Chain

1. **RTL Integrity:**
   - From Observation 1.1, `md5sum -c rtl_frozen/FROZEN.md5` evaluated identically and successfully in both workspaces.
   - Therefore, the RTL under test is the untouched, authentic frozen baseline.

2. **Clean-Room Compliance:**
   - From Observation 1.2, line-by-line and AST diff comparisons against `tb_self_test/l1_dir/` and `tb/ref_model/` show zero shared code blocks (longest matching sequence is 1 line, attributable to generic imports).
   - The test wrapper, test runner, and reference model exhibit completely distinct architecture (4 tiles vs 2 tiles, wormhole FIFO packet arbitration, typed Python Enums, slice-rule-specific methods).
   - Therefore, the implementation was independently derived strictly from the authorized specifications (`SLICE_16_1.md`, `FINAL_whitepaper_v3.0.md`) without copying or porting from quarantined self-tests.

3. **Absence of Facade or Hardcoding:**
   - From Observation 1.3 and 1.4, testcases issue actual core stimuli to the DUT and actively poll DUT wires for state transitions (`t0_l1_state`, `dir_state_o`, `bank_dirty_o`, etc.).
   - If the RTL does not respond or provides incorrect data, `wait_until_cond` times out or assertions fail.
   - From Observation 1.5, the reference model was proven via empirical fault injection to detect and record mismatches whenever DUT signals deviate from expected behavior.
   - Therefore, neither the testbench wrapper nor the reference model is a facade or dummy placeholder.

4. **Authenticity of Verification Outputs:**
   - From Observation 1.4, the test suite was freshly compiled and executed by this auditor; `results.xml` was recreated from scratch with zero errors and zero failures.
   - Therefore, test results are fully authentic and unmanipulated.

---

## 3. Caveats

- **Scope Delimitation:** Milestone 2 covers directed tests F1 through F8 and the Python reference model. Formal BMC verification (F9 / SVA A1, A2, A7) is assigned to Milestone 3, and mutation testing is assigned to Milestone 4.
- **Single-entry Directory Scaffold:** As documented in `dir_ctrl.sv`, the directory controller scaffold manages one active line entry. Directed tests operate cleanly within this specification.
- No other caveats.

---

## 4. Conclusion

The Milestone 2 deliverables (`test_l1_dir.py`, `l1_dir_tb_wrapper.sv`, `slice_ref_model.py`) meet all integrity and clean-room requirements without exception:
1. Frozen RTL was completely preserved and unmodified.
2. Clean-room separation was strictly maintained with zero code copied or ported from quarantined self-tests.
3. Test stimulation and monitoring genuinely exercise the RTL, with no hardcoding or facade implementations.
4. Independent execution confirmed 8/8 passing tests and 0 reference model mismatches.

**Final Verdict:** **CLEAN**

---

## 5. Verification Method

To independently reproduce this forensic audit:

1. **Verify Frozen RTL MD5:**
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core && md5sum -c rtl_frozen/FROZEN.md5
   cd ~/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5
   ```
   *Expected:* All three files report `OK`.

2. **Verify Clean-Room Non-Overlap:**
   ```bash
   python3 -c "
   import difflib
   q = open('/mnt/Code/visualstudio/Design-arch_multi-core/tb_self_test/l1_dir/test_f1_forward.py').readlines()
   c = open('/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/test_l1_dir.py').readlines()
   print('Diff ratio:', difflib.SequenceMatcher(None, q, c).ratio())
   "
   ```
   *Expected:* Diff ratio < 0.02.

3. **Recompile and Run Acceptance Tests:**
   ```bash
   export PATH="/home/durgesh/.local/share/pipx/venvs/cocotb/bin:/usr/bin:/home/durgesh/.local/oss-cad-suite/bin:$PATH"
   cd ~/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
   make clean && make
   ```
   *Expected:* All 8 tests pass with `TESTS=8 PASS=8 FAIL=0 SKIP=0` and 0 scoreboard mismatches.
