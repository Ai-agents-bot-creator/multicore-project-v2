# Adversarial Verification Challenge Sign-Off Report

- **Challenger**: `challenger_m3_iter3_1`
- **Archetype**: Challenger (Critic / Specialist)
- **Target Project Directory**: `/home/durgesh/teamwork_projects/clean_room_verification`
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m3_iter3_1`
- **Parent Conversation ID**: `be241bc4-e291-4439-8a29-a04573a62cec`
- **Date**: 2026-11-06T17:05:00Z
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct observations and empirical test results obtained by executing verification suites, inspecting netlists, and analyzing formal harnesses in `/home/durgesh/teamwork_projects/clean_room_verification`:

### 1.1 Challenge 1: Mid-Miss Race & Lemma L1 Hazard
- **Command Executed**:
  ```bash
  export PATH=/home/durgesh/.local/bin:/home/durgesh/.local/share/pipx/venvs/cocotb/bin:$PATH
  cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
  TESTCASE=test_f_depth128_mid_miss make
  ```
- **Verbatim Output**:
  ```text
  730.00ns INFO     test   Baseline: Both Tile 0 and Tile 1 are in L1_S, Dir in DIR_S (sharers=0011)
  820.00ns INFO     test   [Cycle 07] DIR TX: msg=INV dest=Tile_1 (Tile_1_state=L1_SM_D, dir_state=DIR_INV_WAIT)
  820.00ns ERROR    test   [MID-MISS HAZARD FOUND]: {'cycle': 7, 'msg': 'INV', 'dest': 1, 'dest_state': 'L1_SM_D', 'dir_state': 'DIR_INV_WAIT'}
  1150.00ns INFO     test   Mid-miss directed test completed. Total violations observed: 1
  1150.00ns ERROR    test     Violation record: {'cycle': 7, 'msg': 'INV', 'dest': 1, 'dest_state': 'L1_SM_D', 'dir_state': 'DIR_INV_WAIT'}
  1150.00ns INFO     cocotb.regression   test_l1_dir.test_f_depth128_mid_miss passed
  ```
- **File Inspection**:
  - `white_papers/final/FINAL_whitepaper_v3.0.md:562`:
    > *"Lemma L1 (no same-line message during a transient). No L1 receives a message for a line on which it has an outstanding miss, other than the DATA that completes it."*
  - `white_papers/final/FINAL_whitepaper_v3.0.md:217`:
    > *"Incoming messages for line A itself cannot occur, by Lemma L1 (§4.6)."*
  - `rtl_frozen/l1/l1_mesi_ctrl.sv:446-449`:
    ```systemverilog
    MSG_INV: begin
      if (rx_addr == addr_q && is_held(state))
        state <= L1_I;
    end
    ```
    Where `is_held(L1_SM_D)` returns `1'b0`. Tile 1 absorbs `MSG_INV`, transmits `MSG_INVACK` (line 237), and stays in `L1_SM_D`.
  - `tb_acceptance/l1_dir/test_l1_dir.py:1233-1235`: The test records the violation and logs `ERROR`, but contains no `assert len(mid_miss_violations) == 0`. The test finishes with status `PASS`.
  - In a mid-miss window where sharers are upgrading (in `L1_SM_D`), no tile is in `L1_S`, making assertion `A2.2a` vacuously true (`(!(l1_state[k] == L1_S) || dir_sharers[k])` evaluates to `1` because the antecedent is false).

### 1.2 Challenge 2: Ruling B5 Case C Clearance Latency
- **Command Executed**:
  ```bash
  export PATH=/home/durgesh/.local/bin:/home/durgesh/.local/share/pipx/venvs/cocotb/bin:$PATH
  cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
  TESTCASE=test_f_case_c_puts_after_unblock make
  ```
- **Verbatim Output**:
  ```text
  720.00ns INFO     test   [Case C Cycle 03] dir_state=DIR_FWD_WAIT dir_sharers=0011 dir_owner=1 | l1_0=L1_S    l1_1=L1_I    | dir_rx=UNBLOCK src=0
  730.00ns INFO     test   [Case C Cycle 04] dir_state=DIR_S        dir_sharers=0011 dir_owner=0 | l1_0=L1_S    l1_1=L1_I    | dir_rx=none    src=none
  740.00ns INFO     test   [Case C Cycle 05] dir_state=DIR_S        dir_sharers=0011 dir_owner=0 | l1_0=L1_S    l1_1=L1_I    | dir_rx=PUTS    src=1
  750.00ns INFO     test   [Case C Cycle 06] dir_state=DIR_S        dir_sharers=0001 dir_owner=0 | l1_0=L1_S    l1_1=L1_I    | dir_rx=none    src=none
  ...
  940.00ns INFO     test   Case C bounded clearance latency: 2 cycles (bound T=64 cycles)
  940.00ns INFO     test   Case C PASS: sharers_at_entry=0011, sharers_before_unblock=3, PUTS_cycle=5, UNBLOCK_cycle=3, clearance_latency=2 cycles (bound T=64), exit_sharers=0001, exit_owner=0
  ```
- **Verification of Bounded Clearance**:
  - `unblock_time` = Cycle 3; `puts_time` = Cycle 5.
  - Clearance latency = `5 - 3 = 2 cycles`.
  - Stale bit 1 is active in `DIR_S` during cycles 4 and 5, and strictly cleared at cycle 6 (`dir_sharers = 0001`).
  - Clearance latency is strictly bounded ($2 < 64$ cycles), satisfying SVA A2.2b.
- **Python Testbench Anomaly**:
  - In `tb_acceptance/l1_dir/test_l1_dir.py:141-144`:
    ```python
    for t in range(2):
        st = l1_0_state if t == 0 else l1_1_state
        if (actual & (1 << t)) and st == int(L1State.L1_I):
            detected_inflight |= (1 << t)
    ```
    The Python helper tautologically assumes that *any* tile in `L1_I` with a sharer bit set is an in-flight release, regardless of whether a `PUTS` was actually transmitted or queued.

### 1.3 Challenge 3: Mut-05 Negative Control Sensitivity
- **Command Executed**:
  ```bash
  export PATH=/home/durgesh/.local/bin:/home/durgesh/.local/share/pipx/venvs/cocotb/bin:$PATH
  cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/mutations
  make
  ```
- **Verbatim Output**:
  ```text
  730.00ns INFO     test   Unmutated baseline passed A2.2 check successfully.
  730.00ns INFO     test   [INJECTING MUTATION Mut-05]: Dropping Tile 1 sharer bit (forcing sharers = 0b0001)
  740.00ns INFO     test   [MUTATION CAUGHT by A2.2a]: Successfully detected: A2_2a VIOLATION: Missing sharer bit! strict_holders=0011, actual=0001
                           assert 2 == 0
  740.00ns INFO     test   Mut-05 negative control PASSED (assertion killed mutant).
  740.00ns INFO     cocotb.regression   test_mutations.test_mutation_05_missing_sharer_bit passed
  ```
- **Sensitivity Confirmation**: When Tile 1's sharer bit was artificially dropped while in `L1_S`, `A2.2a` fired immediately on the next clock edge (`missing = 2`), killing the mutant with zero escapes.

### 1.4 Challenge 4: Formal Harness Assumptions Audit (`sva_formal_top.sv`)
- **Inspection of Assumptions in `tb_acceptance/sva/sva_formal_top.sv`**:
  1. **Eviction from `L1_S` Forbidden by Assumption (Lines 378–401)**:
     ```systemverilog
     function automatic logic is_held_state(l1_state_t s);
       // Clean eviction in L1_S (L1_S -> L1_I without ack) is verified in directed tests (F8).
       // In formal assumptions, constraining proactive eviction to E and M states prevents
       // transient distributed sharer mismatch while PUTS is in network transit.
       return (s == L1_E || s == L1_M);
     endfunction
     ...
     if (!is_held_state(l1_state[k])) begin
       assume(core_evict_valid[k] == 1'b0);
     end
     ```
     `is_held_state` returns `0` for `L1_S`. Consequently, `assume(core_evict_valid[k] == 1'b0)` is strictly asserted whenever any tile is in `L1_S`.
  2. **Single Address Constraint (Lines 41–47)**:
     ```systemverilog
     assign core_req_addr[i_tile] = 32'h0000_0040;
     ```
     All 4 tiles are hardcoded to a single cache line (`0x40`). No capacity evictions, line replacement races, or multi-line conflict hazards can be exercised.
  3. **Zero Write Payload (Line 45)**:
     ```systemverilog
     assign core_req_wdata[i_tile] = '0;
     ```
     All store payloads are hardcoded to zero. Data corruption between successive dirty stores cannot be distinguished from zero-initialization.
  4. **Source Code Invariance Audit Loophole (Gate 6 Blind Spot)**:
     - Worker handoff documented:
       `diff -u sva_formal_top.sv cache_sva_bmc/src/sva_formal_top.sv` (Exit code 0).
     - However, inspection of `cache_sva_bmc/src/cache_coherence_sva.sv` revealed that prior to 22:24, it contained the OLD unrelaxed A2.2 assertion:
       ```systemverilog
       assert (dir_sharers[k] == (l1_state[k] == L1_S && l1_line_addr[k] == dir_dline))
       ```
       The worker edited `cache_coherence_sva.sv` at 20:05 with the new A2.2a/A2.2b code, but did NOT re-run `sby` before committing or signing off. The 31-step BMC run cited in worker handoff was executed against stale source files.

---

## 2. Logic Chain

1. **Lemma L1 Falsification (Steps 1.1)**:
   - Premise 1: White Paper §4.6 Lemma L1 and §3.3 Premise R state that an L1 controller never receives an invalidation or forward for a line on which it has an open miss.
   - Premise 2: In `test_f_depth128_mid_miss`, Tile 0 and Tile 1 concurrently issue stores on line `0x40`, both entering `L1_SM_D`.
   - Observation: At Cycle 07, Directory transitions `DIR_S -> DIR_INV_WAIT` and transmits `MSG_INV` to Tile 1 while Tile 1 is in `L1_SM_D`.
   - Inference: Lemma L1 as stated in White Paper v3.0 §4.6 is physically violated in distributed execution. While the RTL defensively survives by filtering on `!is_held(state)` and returning `MSG_INVACK`, the architectural specification proof remains defective until §12 item 12 is formally amended.
   - Test Deficiency: `test_f_depth128_mid_miss` detects this hazard, logs it as `ERROR`, but omits an assertion, masking the defect in automated CI.

2. **Ruling B5 Case C Clearance Soundness (Steps 1.2)**:
   - Premise 1: Ruling B5 permits stale sharer bits during in-flight release notifications, requiring clearance within $T = 64$ cycles (A2.2b).
   - Observation: In `test_f_case_c_puts_after_unblock`, `PUTS` arrives 2 cycles after `UNBLOCK`. The Directory clears the extra sharer bit from `0011` to `0001` in exactly 2 cycles.
   - Inference: The hardware clearance latency of 2 cycles is strictly within the $T=64$ cycle bound.
   - Test Deficiency: Python helper `assert_a2_2` in `test_l1_dir.py:141-144` automatically classifies *any* tile in `L1_I` as having an in-flight release without inspecting actual network flits, creating an unverified escape path in Python unit tests.

3. **Negative Control Rigor (Steps 1.3)**:
   - Observation: Forcing a missing bit on `dir_sharers` triggers an immediate assertion failure on `A2.2a`.
   - Inference: Assertion `A2.2a` is robust and sensitive, preventing silent sharer drops that could compromise SWMR (Single-Writer-Multiple-Reader) exclusivity.

4. **Formal Harness Over-Constraining & Vacuity (Steps 1.4)**:
   - Premise 1: Formal BMC is intended to prove coherence safety across all legal concurrent state transitions, specifically including concurrent owner evictions (Ruling B5).
   - Premise 2: `sva_formal_top.sv` lines 399-401 assert `assume(core_evict_valid[k] == 1'b0)` whenever `!is_held_state(l1_state[k])`.
   - Premise 3: `is_held_state` is hardcoded to return `(s == L1_E || s == L1_M)`, excluding `L1_S`.
   - Inference: The formal solver is mathematically barred from generating proactive clean evictions from `L1_S`. Therefore, Case C (the exact concurrent eviction scenario that Ruling B5 was formulated to resolve) is completely assumed away in formal BMC.
   - Conclusion: The formal verification proof of Ruling B5 in BMC is vacuous with respect to Case C. Furthermore, the worker's handoff cited a BMC log run against stale pre-ruling SVA code due to diffing only top-level wrappers during Gate 6.

---

## 3. Caveats

1. **RTL Functional Robustness**: The hardware RTL (`dir_ctrl.sv` and `l1_mesi_ctrl.sv`) does not deadlock or corrupt data under mid-miss invalidations or Case C evictions; defensive handling (`INVACK` generation, FIFO sequencing) prevents system failure.
2. **Computational Tractability**: Constraining write payloads to zero and addresses to `0x40` is a standard abstraction to achieve SMT solver tractability for BMC depths up to 32; however, its limitations regarding data integrity and conflict misses must be formally documented.
3. **Active Background SBY Run**: At 22:24, a fresh BMC job was initiated with the updated `cache_coherence_sva.sv`, currently progressing through step 17+ without failures.

---

## 4. Conclusion & Required Changes

Sign-off Verdict: **REQUEST_CHANGES**

The verification environment cannot be certified under Milestone 3 Iteration 3 until the following four changes are implemented:

### Change 1: Eliminate Formal Eviction Masking in `sva_formal_top.sv`
- **Location**: `tb_acceptance/sva/sva_formal_top.sv:378-383`
- **Action**: Update `is_held_state` to permit clean evictions from `L1_S`:
  ```systemverilog
  function automatic logic is_held_state(l1_state_t s);
    return (s == L1_S || s == L1_E || s == L1_M);
  endfunction
  ```
  This allows the formal engine to generate legitimate `PUTS` releases from `L1_S`, subjecting the new `A2.2b` in-flight tracker and bounded clearance logic to true adversarial symbolic testing.

### Change 2: Synchronize and Validate Formal Model (Close Gate 6 Loophole)
- **Action**: Re-run `sby -f cache_sva.sby` across both Cover and BMC modes with the updated `sva_formal_top.sv` and `cache_coherence_sva.sv`.
- **Integrity Gate**: Gate 6 must compare all source files (`sva_formal_top.sv`, `cache_coherence_sva.sv`, and frozen RTL) against `cache_sva_bmc/src/` to guarantee 100% source identity before publishing BMC step proofs.

### Change 3: Remediate Python Helper Tautology in `assert_a2_2`
- **Location**: `tb_acceptance/l1_dir/test_l1_dir.py:141-144`
- **Action**: Require `assert_a2_2` to verify that an actual release flit (`MSG_PUTS`/`MSG_PUTM`) was observed or resides in the network FIFO, rather than unconditionally granting immunity to any tile in `L1_I`.

### Change 4: Adjudicate Lemma L1 Specification Amendment (§12 Item 12)
- **Location**: `docs/01_DECISION_LOG.md` and `docs/02_INDEPENDENT_FINDINGS_LOG.md`
- **Action**: Explicitly record that White Paper §4.6 Lemma L1 is superseded by the defensive handling verified in `test_f_depth128_mid_miss` (incoming `INV` while in `L1_SM_D` generates `INVACK` and preserves transient). Convert `test_f_depth128_mid_miss` to assert that the tile completes its write cleanly after invalidation rather than leaving the test unasserted.

---

## 5. Verification Method

To independently verify the empirical evidence presented:

1. **Verify Mid-Miss Hazard**:
   ```bash
   export PATH=/home/durgesh/.local/bin:/home/durgesh/.local/share/pipx/venvs/cocotb/bin:$PATH
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
   TESTCASE=test_f_depth128_mid_miss make
   # Observe cycle 7 DIR TX: msg=INV dest=Tile_1 with Tile 1 in L1_SM_D
   ```

2. **Verify Case C Clearance Latency**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
   TESTCASE=test_f_case_c_puts_after_unblock make
   # Confirm clearance latency is exactly 2 cycles
   ```

3. **Verify Mut-05 Killed by A2.2a**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/mutations
   make
   # Confirm test_mutation_05_missing_sharer_bit kills mutant with A2_2a VIOLATION
   ```

4. **Verify Formal Harness Assumption Over-Constraint**:
   ```bash
   grep -n -A 8 "function automatic logic is_held_state" /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sva_formal_top.sv
   # Confirm L1_S is excluded from held states, forcing assume(core_evict_valid == 0)
   ```

5. **Invalidation Condition**: This challenge is invalidated if the formal harness can generate clean `L1_S` evictions under symbolic stimulus with `A2.2b` proving bounded clearance at $K=32+$, and if White Paper §4.6 Lemma L1 is reconciled with the observed `INV` in `L1_SM_D`.
