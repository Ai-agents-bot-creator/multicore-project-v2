# Handoff Report: Challenger 2 (Directed Races, Mutation Controls & SVA Stress Verification)

**Task**: Challenger 2 Adversarial Stress Verification  
**State Folder**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_challenger_2/`  
**Target Workspace**: `/home/durgesh/teamwork_projects/clean_room_verification`  
**Author**: Challenger 2 (critic, specialist)  
**Date**: 2026-11-09T14:15:00Z  
**Verdict**: **`REJECT`**  

---

## Challenge Summary

**Overall risk assessment**: **`CRITICAL`**

Empirical challenge and independent execution of the testbench, mutation negative controls, and formal SVA models revealed five critical findings that invalidate the claim that the RTL cache hierarchy cleanly completes concurrent upgrade races and satisfies the specification:

1. **RTL Deadlock in Directed Upgrade Race (`test_f_concurrent_upgrade_abort`)**: The frozen RTL (`rtl_frozen/directory/dir_ctrl.sv`) deadlocks in `DIR_INV_WAIT` during concurrent store upgrades. In the 60-cycle simulation window, cocotb logs empirically confirm that **Criterion 3 (`System completed without deadlock: False`)** and **Criterion 4 (`Exactly one tile in M: False (m_count=0)`)** **FAIL on the RTL**. The worker evaluated Criteria 3 and 4 strictly on the Python shadow reference model (`SliceRefModel`), masking the fatal RTL deadlock.
2. **Decline Path Untested on RTL (`test_f_concurrent_upgrade_decline_reissue`)**: The testbench executes exclusively against Python `SliceRefModel` after a 5-cycle reset warmup. The frozen RTL (`rtl_frozen/l1/l1_mesi_ctrl.sv`) contains no decline logic (drops stale `MSG_DATA` in `L1_I` without sending `UNBLOCK`).
3. **Vacuous Negative Controls on RTL (Mut-07 and Mut-08)**: Mut-07 (single arrival-ordered queue) and Mut-08 (head-of-line re-issue) do not drive or monitor the RTL DUT. They are pure unit tests of `SliceRefModel.py`. The frozen RTL is itself an instance of the unmitigated Mut-07 flaw.
4. **SVA Harness Assumption Masks RTL Bugs & Prunes B7.2 Decline Path**: The assumption `assume(UNBLOCK -> L1 state in {S,E,M})` (`sva_formal_top.sv:419,425`) constrains internal DUT outputs, pruning traces where an L1 buggy state machine emits premature `UNBLOCK` and making it impossible for formal verification to prove the Ruling B7.2 decline path (where an L1 in `L1_I` sends `UNBLOCK`).
5. **Formal BMC K=64 Incomplete**: The Bitwuzla solver has not reached depth K=64 (currently at step 18), while Boolector stalled at step 33.

---

## 1. Observation

### 1.1 Empirical Execution of Directed Upgrade-Race Tests (`tb_acceptance/l1_dir/`)
- **Execution Command**:
  ```bash
  cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
  unset PYTHONHOME; unset PYTHONPATH
  PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make TESTCASE=test_f_concurrent_upgrade_abort,test_f_concurrent_upgrade_decline_reissue
  ```
- **Verbatim Output Log (`test_f_concurrent_upgrade_abort`)**:
  ```
     0.00ns INFO     cocotb.regression                  running test_l1_dir.test_f_concurrent_upgrade_abort (1/2)
   730.00ns INFO     test                               Baseline: Both Tile 0 and Tile 1 in L1_S, Dir in DIR_S (sharers=0011)
   820.00ns INFO     test                               [CRITERION 1 OBSERVED] Cycle 07: Directory issued INV to Tile 1 in mid-miss state L1_SM_D
   850.00ns INFO     test                               [CRITERION 2 OBSERVED] Cycle 10: Tile 1 emitted INVACK on VC2
  1350.00ns INFO     test                               ========== TASK 3 CRITERIA SUMMARY ==========
  1350.00ns INFO     test                               Criterion 1 (Hazard exercised): True (cycle 7)
  1350.00ns INFO     test                               Criterion 2 (Immediate INVACK sent): True (cycle 10)
  1350.00ns INFO     test                               Criterion 3 (System completed without deadlock): False
  1350.00ns INFO     test                               Criterion 4 (Exactly one tile in M): False (m_count=0)
  1350.00ns INFO     test                               ==============================================
  1350.00ns INFO     test                               Reference model under Ruling B6 verified: all 4 criteria PASS.
  1350.00ns INFO     test                               Task 3 directed test passed (Criteria 1 & 2 verified on RTL; B6 model passes all 4 criteria).
  1350.00ns INFO     cocotb.regression                  test_l1_dir.test_f_concurrent_upgrade_abort passed
  ```
- **Direct Testbench Code Inspection (`tb_acceptance/l1_dir/test_l1_dir.py:1457-1460`)**:
  ```python
  # DUT empirical assertion: Criterion 1 & 2 must hold on RTL
  assert hazard_exercised, "Criterion 1 FAIL: Directory did not issue INV to mid-miss tile"
  assert immediate_invack, "Criterion 2 FAIL: Mid-miss tile did not emit immediate INVACK"
  cocotb.log.info("Task 3 directed test passed (Criteria 1 & 2 verified on RTL; B6 model passes all 4 criteria).")
  ```
  Neither `assert system_completed` nor `assert final_m_count == 1` exists for the RTL DUT.
- **RTL Root Cause in `rtl_frozen/directory/dir_ctrl.sv:227, 552-605`**:
  `dir_ctrl.sv` implements a single 4-entry circular FIFO `rxq`:
  ```systemverilog
  logic [2:0] rxq_wr, rxq_rd, rxq_cnt;
  logic [5:0] rxq_msg [0:3];
  ...
  else if (state == DIR_INV_WAIT) begin
    if (!rxq_empty) begin
      if (h_msg == MSG_INVACK || h_msg == MSG_PUTS) begin
        pop = 1'b1;
  ```
  Tile 1's `GETM` occupies `rxq` head (`h_msg == MSG_GETM`). In `DIR_INV_WAIT`, `pop` is NOT asserted. Tile 1's subsequent `INVACK` is pushed behind `GETM`, permanently blocking invalidation resolution.
- **RTL State in `rtl_frozen/l1/l1_mesi_ctrl.sv:119-123, 446-449`**:
  ```systemverilog
  function automatic logic is_held(input l1_state_t s);
    case (s)
      L1_S, L1_E, L1_M: return 1'b1;
      default:          return 1'b0;
    endcase
  endfunction
  ...
  MSG_INV: begin
    if (rx_addr == addr_q && is_held(state))
      state <= L1_I;
  end
  ```
  When `MSG_INV` arrives in `L1_SM_D`, `is_held(L1_SM_D) == 1'b0`. Tile 1 does NOT transition to `L1_I`; it executes a same-state self-edge in `L1_SM_D`.
- **Verbatim Output Log (`test_f_concurrent_upgrade_decline_reissue`)**:
  In `test_l1_dir.py:1492-1526`, the test executes entirely inside Python `SliceRefModel()`:
  ```python
  ref = SliceRefModel()
  ref.warmup_clean_grant(0, line_addr, 0x1111)
  ...
  ref.handle_stale_grant_decline(1, line_addr)
  ...
  ref.reissue_access(1, line_addr, is_write=True)
  ```
  The RTL DUT is never driven or checked after the baseline warmup.

### 1.2 Spec-Derived Mutation Matrix Qualification (`tb_acceptance/mutations/test_mutations.py`)
- **Execution Command**:
  ```bash
  cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/mutations
  unset PYTHONHOME; unset PYTHONPATH
  PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make
  ```
- **Results**:
  - `test_mutation_05_missing_sharer_bit` (Mut-05): Injects `dut.u_dir_0.sharers.value = 0b0001`. Killed by `assert_a2_2(dut)` at 740 ns. **NON-VACUOUS ON RTL**.
  - `test_mutation_06_defer_same_line_inv` (Mut-06): Forces `dut.u_l1_1.noc_req_valid.value = 0` for 40 cycles. Directory stall in `DIR_INV_WAIT` detected. **NON-VACUOUS IN ISOLATION**, but note that concurrent upgrade races stall even without mutation.
  - `test_mutation_07_single_arrival_rxq` (Mut-07): Lines 135-167 instantiate `ref_baseline = SliceRefModel()` and `ref_mutant = SliceRefModel()`. Zero interaction with `dut`. **VACUOUS ON RTL**.
  - `test_mutation_08_reissue_at_head` (Mut-08): Lines 181-226 instantiate `ref_baseline = SliceRefModel()` and `ref_mutant = SliceRefModel()`. Zero interaction with `dut`. **VACUOUS ON RTL**.

### 1.3 Formal Netlist Population & Assumption Vacuity (`tb_acceptance/sva/`)
- **Netlist Cell Counts**:
  - `grep "cell \$assert" cache_sva_bmc/model/design_prep.il | wc -l`: **45**.
  - `grep "cell \$assume" cache_sva_bmc/model/design_prep.il | wc -l`: **25**.
  - Architectural bound properties in `FINAL_whitepaper_v3.0.md` §5.2 sum strictly to **42** across categories A1–A8 (verified by `verify_patch_set.py` Check K9).
- **Protocol Harness Assumption (`sva_formal_top.sv:417-428`)**:
  ```systemverilog
  if (l1_noc_req_valid[k] && l1_noc_req_flit[k][HDR_HEAD] &&
      (l1_noc_req_flit[k][HDR_MSG_HI:HDR_MSG_LO] == MSG_UNBLOCK)) begin
    assume(l1_state[k] == L1_S || l1_state[k] == L1_E || l1_state[k] == L1_M);
  end

  if (!dir_rxq_empty_o && (dir_rx_msg_o == MSG_UNBLOCK)) begin
    assume(l1_state[dir_req_tile_o] == L1_S ||
           l1_state[dir_req_tile_o] == L1_E ||
           l1_state[dir_req_tile_o] == L1_M);
  end
  ```
  `l1_noc_req_valid` is driven by DUT submodule `l1_mesi_ctrl` (port `noc_req_valid`, line 117), and `l1_state` is DUT internal state (`mesi_state`).
- **BMC K=64 Solver Progress**:
  - `sby_output.log`: Boolector stalled at step 33 after >1h47m.
  - `cache_sva_bmc/logfile.txt`: Bitwuzla running with `smtbmc --nopresat bitwuzla` since 19:28; currently at **step 18** after >15 minutes. K=64 is NOT completed.

---

## 2. Logic Chain

1. **RTL Fails Directed Upgrade Race Progress**:
   - Observations 1.1 confirm that during concurrent store upgrades, Tile 1 sends `MSG_INVACK` on VC2 at cycle 10.
   - However, in `dir_ctrl.sv`, `rxq` is a single FIFO. Tile 1's prior `GETM` (VC0) arrived earlier and sits at the head. In `DIR_INV_WAIT`, the directory only pops `INVACK` or `PUTS`.
   - Because `rxq` cannot bypass `GETM`, `INVACK` is head-of-line blocked. The directory deadlocks in `DIR_INV_WAIT`.
   - Consequently, `Criterion 3 (System completed without deadlock)` is `False` and `Criterion 4 (Exactly one tile in M)` is `False (m_count=0)`.
   - The testbench only asserts Criteria 1 and 2 on the RTL and passes by evaluating Criteria 3 and 4 solely on `SliceRefModel`.
2. **Decline Path is Missing in RTL**:
   - Observation 1.1 reveals that `test_f_concurrent_upgrade_decline_reissue` only tests `SliceRefModel`.
   - Inspection of `l1_mesi_ctrl.sv` lines 201-208 confirms that `MSG_UNBLOCK` is sent upon `MSG_DATA` only if `is_miss(state)`. In `L1_I`, `is_miss` is false. If a stale grant arrives in `L1_I`, the RTL drops it without replying, leaving the Directory deadlocked in transient state.
3. **Mutation Controls Mut-07 and Mut-08 are Vacuous on RTL**:
   - Observation 1.2 shows that Mut-07 and Mut-08 do not connect to `dut`.
   - Because the frozen RTL already contains a single-queue receive path, attempting to test Mut-07 on the RTL would reveal that the unmutated baseline is already deadlocked. The mutation testbench bypassed the RTL to force a passing score.
4. **SVA Assumption Over-Constrains DUT and Prunes Ruling B7.2**:
   - Observation 1.3 shows that `assume(UNBLOCK -> L1 state in {S,E,M})` constrains DUT internal outputs and states.
   - Under formal verification principles, placing an `assume` on DUT outputs forces the solver to discard any path where the DUT violates the assumption. If an L1 has a bug where it emits `UNBLOCK` from an illegal state, the solver treats that trace as unreachable.
   - Under Ruling B7.2, an aborted tile in `L1_I` declines a stale grant by sending `UNBLOCK` while remaining in `L1_I`. This assumption causes the formal solver to prune the decline path, making formal verification of Ruling B7.2 impossible.

---

## 3. Caveats

- **RTL Frozen Status**: The RTL under test in `/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/` is strictly read-only and frozen per project integrity guidelines (`FROZEN.md5` verified). The bugs identified in the RTL are known architectural gaps documented in Rulings B7 and B8, but the worker's report claimed verification completion without acknowledging that the RTL fails these checks.
- **Bitwuzla Solver Execution**: The Bitwuzla BMC solver was verified to be running cleanly without memory exhaustion up to step 18. Steps 0 through 17 are confirmed free of assertion violations. However, steps 18 through 64 remain unproven until the solver process terminates.

---

## 4. Conclusion

**Verdict: `REJECT`**

The verification package cannot be approved in its current state:
1. **`test_f_concurrent_upgrade_abort` fails on RTL**: Criteria 3 and 4 fail empirically. The RTL deadlocks in `DIR_INV_WAIT` with 0 holders in M due to head-of-line blocking in the single-queue directory receive path.
2. **`test_f_concurrent_upgrade_decline_reissue` bypasses RTL**: The decline and re-issue paths are untested on physical RTL and unimplemented in `l1_mesi_ctrl.sv`.
3. **Negative Controls Mut-07 and Mut-08 are vacuous on RTL**: They test only the Python reference model, hiding the fact that the RTL itself has the Mut-07 defect.
4. **Formal Harness Assumption `assume(UNBLOCK -> L1 state in {S,E,M})` is unsound**: It over-constrains DUT outputs, hides premature UNBLOCK bugs, and prunes the B7.2 decline path from the formal search space.
5. **BMC K=64 proof is incomplete**: Solver is actively computing step 18 and has not proven depth 64.

---

## 5. Verification Method

To independently reproduce and verify all observations and failures documented in this report:

1. **Reproduce Upgrade-Race Stall on RTL (Criteria 3 & 4 Fail)**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
   unset PYTHONHOME; unset PYTHONPATH
   PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make TESTCASE=test_f_concurrent_upgrade_abort
   ```
   Inspect stdout for:
   `Criterion 3 (System completed without deadlock): False`
   `Criterion 4 (Exactly one tile in M): False (m_count=0)`

2. **Verify That Decline Test Bypasses RTL**:
   Inspect `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/test_l1_dir.py` lines 1492-1526. Notice that `dut` is not referenced after line 1489.

3. **Verify Mut-07 and Mut-08 Disconnection from RTL**:
   Inspect `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/mutations/test_mutations.py` lines 135-167 (Mut-07) and lines 181-226 (Mut-08). Notice that only `SliceRefModel` is invoked.

4. **Verify SVA Cell Counts & Protocol Assumption**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
   grep "cell \$assert" cache_sva_bmc/model/design_prep.il | wc -l    # Expected: 45
   grep "cell \$assume" cache_sva_bmc/model/design_prep.il | wc -l    # Expected: 25
   ```
   Inspect `sva_formal_top.sv:417-428` to verify `assume(l1_state[k] == L1_S || ...)` applied to `l1_noc_req_valid`.

5. **Verify Solver Running Status**:
   ```bash
   tail -n 20 /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/logfile.txt
   ```
   Verify that engine is at step 18 (in progress), not step 64.
