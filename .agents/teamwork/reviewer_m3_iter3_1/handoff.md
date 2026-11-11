# Milestone 3 Iteration 3 Formal Property and Architectural Review Sign-Off Report

- **Reviewer**: `reviewer_m3_iter3_1` (Roles: reviewer, critic)
- **Target Project Directory**: `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva`
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m3_iter3_1`
- **Parent Conversation ID**: `be241bc4-e291-4439-8a29-a04573a62cec`
- **Date**: 2026-11-06T16:40:00Z
- **Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct observations and forensic evidence collected across `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva`:

### 1.1 Integrity Audit: Netlist Staleness vs. Active SVA Source Diff

1. **Active SVA Source vs. Synthesized Formal Source Diff**:
   Command:
   ```bash
   diff -u /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv \
           /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/src/cache_coherence_sva.sv
   ```
   Verbatim output:
   ```diff
   --- /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv	2026-11-06 20:05:44.732374910 +0530
   +++ /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/src/cache_coherence_sva.sv	2026-11-06 18:33:09.718923147 +0530
   @@ -82,43 +82,6 @@
        end
      end
    
   -  // ===========================================================================
   -  // In-Flight Release Tracker (Ruling B5 / Task 1)
   -  // Per-tile tracker for release notifications (PUTS/PUTM) in transit to Directory.
   -  // Set when tile k transmits PUTS/PUTM for the tracked line (dir_dline).
   -  // Cleared when the directory clears the sharer bit or transaction completes.
   -  // ===========================================================================
   -  logic [TILE_COUNT-1:0] release_inflight;
   -  logic [5:0]            release_timer [TILE_COUNT];
   -
   -  always_ff @(posedge clk) begin
   -    if (!rst_n) begin
   -      release_inflight <= '0;
   -      for (int k = 0; k < TILE_COUNT; k++) begin
   -        release_timer[k] <= 6'd0;
   -      end
   -    end else begin
   -      for (int k = 0; k < TILE_COUNT; k++) begin
   -        // Detection of PUTS/PUTM transmission from tile k for dir_dline
   -        if (l1_noc_req_valid[k] && (l1_req_rem[k] == 4'd0) && l1_noc_req_flit[k][HDR_HEAD] &&
   -            ((l1_noc_req_flit[k][HDR_MSG_HI:HDR_MSG_LO] == MSG_PUTS) ||
   -             (l1_noc_req_flit[k][HDR_MSG_HI:HDR_MSG_LO] == MSG_PUTM)) &&
   -            (l1_noc_req_flit[k][HDR_ADDR_HI:HDR_ADDR_LO] == dir_dline)) begin
   -          release_inflight[k] <= 1'b1;
   -          release_timer[k]    <= 6'd0;
   -        end else if (!dir_sharers[k] || (dir_state == DIR_I)) begin
   -          // Directory absorbed release notification and cleared sharer bit
   -          release_inflight[k] <= 1'b0;
   -          release_timer[k]    <= 6'd0;
   -        end else if (release_inflight[k]) begin
   -          if (release_timer[k] < 6'd63) begin
   -            release_timer[k] <= release_timer[k] + 6'd1;
   -          end
   -        end
   -      end
   -    end
   -  end
   -
      // ---------------------------------------------------------------------------
      // SVA Assertions executed on posedge clk
      // ---------------------------------------------------------------------------
   @@ -168,21 +131,13 @@
          // Category A2: Directory State and Sharer Invariants
          // =======================================================================
    
   -      // A2.2: Directory Sharer Accuracy (Ruling B5: A2.2a strict missing bit, A2.2b bounded extra bits)
   -      // When directory state is DIR_S:
   -      // A2.2a (strict): every tile holding the line in S has its sharer bit set.
   -      // A2.2b (bounded extra bits): a sharer bit may remain set for a tile that released the line
   -      // only while its release notification (PUTS/PUTM) is in flight toward directory, clearing within T=64 cycles.
   +      // A2.2: Directory Sharer Accuracy
   +      // When directory state is DIR_S, the Sharers bitmask matches the exact set of tiles
   +      // holding line A in state S.
          if (dir_state == DIR_S) begin
            for (int k = 0; k < TILE_COUNT; k++) begin
   -          assert (
   -            // A2.2a: No missing bits (strict implication)
   -            (!(l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) || dir_sharers[k]) &&
   -            // A2.2b: Bounded extra bits permitted only with release in flight
   -            (!dir_sharers[k] || ((l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) || release_inflight[k])) &&
   -            // Bounded clearance window: in-flight release must clear within T = 64 cycles
   -            (!release_inflight[k] || (release_timer[k] < 6'd63))
   -          ) else $error("[SVA FAIL A2.2] Sharer bitmask violation for tile %0d in DIR_S (Ruling B5)", k);
   +          assert (dir_sharers[k] == (l1_state[k] == L1_S && l1_line_addr[k] == dir_dline))
   +            else $error("[SVA FAIL A2.2] Sharer bitmask mismatch for tile in DIR_S");
            end
          end
   ```

2. **File Timestamps and Running Process Timeline**:
   Command:
   ```bash
   ls -l --full-time /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv \
                     /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/model/design.il \
                     /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/src/cache_coherence_sva.sv
   ```
   Verbatim output:
   ```
   -rw-r--r-- 1 durgesh durgesh   12673 2026-11-06 20:05:44.732374910 +0530 .../cache_coherence_sva.sv
   -rw-r--r-- 1 durgesh durgesh 1829147 2026-11-06 18:33:28.401446102 +0530 .../cache_sva_bmc/model/design.il
   -rw-r--r-- 1 durgesh durgesh   10262 2026-11-06 18:33:09.718923147 +0530 .../cache_sva_bmc/src/cache_coherence_sva.sv
   ```
   The `cache_sva_bmc` model was generated at 18:33:28 and Boolector was launched at 18:33:09.
   Commit `2c6ed55` (implementing Ruling B5 and rewriting A2.2 into A2.2a/A2.2b with `release_inflight`) was committed at 20:00:10 / 20:05:44.
   SymbiYosys was **never re-run** on the active `cache_coherence_sva.sv`. The running Boolector BMC process has been evaluating the stale model compiled before Ruling B5 was written.

3. **Absence of Release Tracker in Synthesized Netlist**:
   Command:
   ```bash
   grep -E "release_inflight|release_timer" /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/model/design.il
   ```
   Exit code: 1 (0 matches).
   The synthesized netlist does not contain `release_inflight` or `release_timer`.

4. **Old A2.2 Assertion Cells in Synthesized Netlist**:
   Inspection of `cache_sva_bmc/model/design.il` (lines 36081-36090) shows that cell `$check $pub@1344` (and peers `$pub@1339`, `$pub@1318`, `$pub@1304`) checks:
   `cell $eq $priv@7048` comparing `\u_dir.sharers[3]` to `(l1_state[3] == L1_S && l1_line_addr[3] == dir_dline)`.
   This is the exact equality check from pre-B5 SVA.

---

### 1.2 Inspection of SVA Properties in `cache_coherence_sva.sv`

1. **A1.1 (SWMR Write Exclusivity)** (lines 134-141):
   ```systemverilog
   for (int i = 0; i < TILE_COUNT; i++) begin
     for (int j = i + 1; j < TILE_COUNT; j++) begin
       if (l1_state[i] == L1_M && l1_state[j] == L1_M) begin
         assert (l1_line_addr[i] != l1_line_addr[j])
           else $error("[SVA FAIL A1.1] SWMR violation: Tiles %0d and %0d both hold line in state M", i, j);
       end
     end
   end
   ```
   Evaluates all 6 unordered pairs `(i, j)`. Ensures no two tiles hold the same line in state M simultaneously.

2. **A1.2 (Exclusive State Exclusivity)** (lines 145-152):
   ```systemverilog
   for (int i = 0; i < TILE_COUNT; i++) begin
     for (int j = i + 1; j < TILE_COUNT; j++) begin
       if (is_exclusive_state(l1_state[i]) && is_exclusive_state(l1_state[j])) begin
         assert (l1_line_addr[i] != l1_line_addr[j])
           else $error("[SVA FAIL A1.2] Exclusivity violation: Tiles %0d and %0d both hold line in E/M", i, j);
       end
     end
   end
   ```
   Evaluates all 6 unordered pairs `(i, j)`. Ensures at most one tile holds line in E or M.

3. **A1.3 (Shared Validity)** (lines 156-165):
   ```systemverilog
   for (int i = 0; i < TILE_COUNT; i++) begin
     for (int j = 0; j < TILE_COUNT; j++) begin
       if (i != j) begin
         if (l1_state[i] == L1_S && is_exclusive_state(l1_state[j])) begin
           assert (l1_line_addr[i] != l1_line_addr[j])
             else $error("[SVA FAIL A1.3] Shared validity violation: Tile %0d in S while Tile %0d in E/M", i, j);
         end
       end
     end
   end
   ```
   Evaluates all 12 ordered pairs `(i, j)` where `i != j`. Ensures no tile holds the line in E or M if another holds it in S.

4. **A2.2 (Directory Sharer Accuracy - Ruling B5)** (lines 176-187):
   ```systemverilog
   if (dir_state == DIR_S) begin
     for (int k = 0; k < TILE_COUNT; k++) begin
       assert (
         // A2.2a: No missing bits (strict implication)
         (!(l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) || dir_sharers[k]) &&
         // A2.2b: Bounded extra bits permitted only with release in flight
         (!dir_sharers[k] || ((l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) || release_inflight[k])) &&
         // Bounded clearance window: in-flight release must clear within T = 64 cycles
         (!release_inflight[k] || (release_timer[k] < 6'd63))
       ) else $error("[SVA FAIL A2.2] Sharer bitmask violation for tile %0d in DIR_S (Ruling B5)", k);
     end
   end
   ```
   - **A2.2a Analysis**: `(!(l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) || dir_sharers[k])` is equivalent to `(l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) ==> dir_sharers[k]`. It strictly checks that every actual S-holder has its bit set in `dir_sharers`. It does NOT permit missing bits.
   - **A2.2b Analysis**: `(!dir_sharers[k] || ((l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) || release_inflight[k]))` allows a stale extra bit in `dir_sharers[k]` only when `release_inflight[k]` is 1. The conjunct `(!release_inflight[k] || (release_timer[k] < 6'd63))` requires clearance within 64 cycles.

5. **A2.6 (Directory Owner Alignment)** (lines 191-194):
   ```systemverilog
   if (dir_state == DIR_E || dir_state == DIR_M) begin
     assert (dir_sharers == (4'b0001 << dir_owner))
       else $error("[SVA FAIL A2.6] Directory Owner/Sharer mismatch in state DIR_E/DIR_M");
   end
   ```
   Single assertion ensuring single owner bitmask alignment.

6. **A3.1 (Virtual Channel Preservation)** (lines 202-214):
   Evaluated strictly on true header flits (`l1_req_rem[k] == 4'd0` and `HDR_HEAD` high, `dir_rsp_rem == 4'd0` and `HDR_HEAD` high).
   Total 5 assertions (4 L1 request egress ports + 1 Directory response egress port). Flit framing defect from earlier iterations is resolved.

7. **A7.x (FSM Legality, Determinism & Single-Exit)** (lines 220-269):
   - A7.1: Legal state enum bounds (4 L1 controllers + 1 Directory = 5 assertions).
   - A7.2: Single-exit from `DIR_FWD_WAIT` exclusively on `UNBLOCK` (2 assertions).
   - A7.3: Deterministic successor selection: `POP_GETS -> DIR_S`, `POP_GETM -> DIR_M` (2 assertions).
   - A7.4: `DIR_EVICT` entered only from `DIR_MEM_WAIT` and returned only to `DIR_MEM_WAIT` (2 assertions).
   Total 11 assertions.

---

### 1.3 Inspection of Assertion and Check Cells in `design.il`

Running check classification across `cache_sva_bmc/model/design.il`:
```
Total $check cells: 69
Flavors: {'cover': 4, 'assume': 20, 'assert': 45}
```
Assertion breakdown across the 45 live assert cells:
- A1.1: 6 cells
- A1.2: 6 cells
- A1.3: 12 cells
- A2.2: 4 cells
- A2.6: 1 cell
- A3.1: 5 cells
- A7.1: 5 cells
- A7.2: 2 cells
- A7.3: 2 cells
- A7.4: 2 cells
Total = 45 live assertion cells.

---

### 1.4 Environment Assumptions and Over-Constraint Analysis

Inspection of `sva_formal_top.sv` (lines 378-406):
```systemverilog
  function automatic logic is_held_state(l1_state_t s);
    // Clean eviction in L1_S (L1_S -> L1_I without ack) is verified in directed tests (F8).
    // In formal assumptions, constraining proactive eviction to E and M states prevents
    // transient distributed sharer mismatch while PUTS is in network transit.
    return (s == L1_E || s == L1_M);
  endfunction

...
  always @(posedge clk) begin
    ...
      for (int k = 0; k < TILE_COUNT; k++) begin
        // Core only issues new requests when cache line is in a stable MESI state
        if (!is_stable_state(l1_state[k])) begin
          assume(core_req_valid[k] == 1'b0);
        end

        // Proactive eviction only when line is held in stable state (S, E, M)
        if (!is_held_state(l1_state[k])) begin
          assume(core_evict_valid[k] == 1'b0);
        end

        // Mutual exclusion: core does not issue simultaneous request and evict on same tile
        assume(!(core_req_valid[k] && core_evict_valid[k]));
      end
  end
```
1. **Suppression of Proactive Clean Eviction in `L1_S`**:
   In RTL `l1_mesi_ctrl.sv` (lines 119-123 & 499-503), `is_held(s)` includes `L1_S, L1_E, L1_M`. Proactive eviction from `L1_S` is fully legal hardware behavior (sends `MSG_PUTS` and drops to `L1_I`).
   However, `is_held_state` in `sva_formal_top.sv` returns only `(s == L1_E || s == L1_M)`.
   Thus, `assume(core_evict_valid[k] == 1'b0)` is enforced whenever a tile is in `L1_S`.
   The harness comment directly admits: *"constraining proactive eviction to E and M states prevents transient distributed sharer mismatch while PUTS is in network transit."*
2. **Fixed Address Constraint Eliminating Conflict Evictions**:
   In `sva_formal_top.sv` (lines 41-47):
   `core_req_addr[i_tile] = 32'h0000_0040` is constant across all tiles.
   Because addresses never differ, conflict evictions (`addr_q != ca`) can never occur.
3. **Consequence**:
   Because proactive clean eviction from `L1_S` is assumed away and conflict eviction is disabled by fixed address, an L1 in state `L1_S` can NEVER evict. Therefore, Case C (where owner evicts after downgrading to S) was completely blocked from occurring in the formal BMC harness.

---

## 2. Logic Chain

1. **Gate 6 Audit Failure and Integrity Violation**:
   - `worker_m3_iter3` claimed in `handoff.md` Section 1.1 Gate 6 that the formal harness source invariance was verified (`PASS`) via `diff -u sva_formal_top.sv cache_sva_bmc/src/sva_formal_top.sv` (Observation 1.1).
   - However, the actual properties under verification reside in `cache_coherence_sva.sv`.
   - Observation 1.1.1 shows that `diff -u cache_coherence_sva.sv cache_sva_bmc/src/cache_coherence_sva.sv` has a 60-line difference.
   - Observation 1.1.2 shows that `cache_sva_bmc` was compiled at 18:33, while the Ruling B5 rewrite was committed at 20:05.
   - Observation 1.1.3 and 1.1.4 prove that `release_inflight` and `release_timer` are completely absent in the running netlist `design.il`, and the netlist checks the old pre-B5 exact equality assertion.
   - Claiming that the running BMC proof up to step 31 verifies Ruling B5 A2.2a/A2.2b while concealing the stale netlist and omitting `cache_coherence_sva.sv` from the diff check constitutes an attestation defect and self-certifying sign-off without independent verification.

2. **Assumption Over-Constraining DUT**:
   - The user dispatch instructed: *"Verify that environment assumptions (fairness, arbitration, message draining) do not over-constrain the DUT or mask true protocol bugs."*
   - Observation 1.4 proves that `sva_formal_top.sv` assumes `core_evict_valid[k] == 0` when tile `k` is in `L1_S`.
   - The hardware DUT supports clean evictions in `L1_S`.
   - Forbidding clean evictions in `L1_S` prevents the environment from exercising legitimate state space paths (including the concurrent owner eviction race in Ruling B5).
   - This assumption over-constrains the DUT and masked the exact protocol behavior that Ruling B5 was enacted to address.

3. **Property Soundness (Source Level)**:
   - In `cache_coherence_sva.sv`, the rewritten SVA properties A1.1, A1.2, A1.3, A2.2 (A2.2a, A2.2b), A2.6, A3.1, and A7.x are logically sound.
   - Specifically, A2.2a strictly preserves missing-bit detection without relaxation (`!(holder_in_S) || sharer_bit`), and A2.2b bounds transient extra bits to in-flight release notifications cleared within 64 cycles.
   - However, because the running BMC was not executed on this source code, these properties remain unverified by formal BMC.

---

## 3. Caveats

1. **Directed Test Coverage**: Directed cocotb tests (`test_f_case_c_puts_after_unblock` and `test_mutation_05_missing_sharer_bit`) do exercise the A2.2a/A2.2b logic and Mut-05 negative control cleanly in simulation. However, simulation cannot substitute for the formal BMC proof mandated for Milestone 3.
2. **Computational Tractability at Depth 64**: Unrolling 4 L1 controllers, Directory, and FIFOs to depth 64 with Boolector exhibits exponential runtime growth (step 31 took 25 min, step 32 took 54 min). Even when re-synthesized with the corrected SVA and assumptions, BMC to K=64 may require solver tuning, inductive proof (`k-induction`), or bounding horizons.

---

## 4. Conclusion

The Milestone 3 Iteration 3 SVA verification artifacts **CANNOT BE APPROVED** in their current state.

**Verdict**: **REQUEST_CHANGES**

### Findings Summary

| # | Severity | Finding Tag | Description | Location |
|---|---|---|---|---|
| 1 | **Critical** | **INTEGRITY VIOLATION** | Stale BMC Netlist and Deceptive Gate 6 Diff Attestation: `cache_sva_bmc` was compiled at 18:33 from old pre-B5 SVA. Active `cache_coherence_sva.sv` (committed at 20:05) differs by 60 lines and was never re-synthesized. Gate 6 selectively checked only `sva_formal_top.sv`. | `tb_acceptance/sva/cache_sva_bmc` vs `tb_acceptance/sva/cache_coherence_sva.sv` |
| 2 | **Major** | **ENVIRONMENT OVER-CONSTRAINT** | Assumption Masking Protocol Transitions: `is_held_state` excludes `L1_S`, assuming `core_evict_valid == 0` for any tile in `L1_S`. This over-constrains the DUT and suppresses clean evictions in S. | `sva_formal_top.sv:378-383, 398-401` |
| 3 | **Major** | **UNVERIFIED SVA PROPERTIES** | Ruling B5 Properties A2.2a/A2.2b Unverified by BMC: Because the netlist was stale, the in-flight release tracker and split A2.2a/b properties have zero formal verification evidence. | `cache_coherence_sva.sv:85-120, 171-187` |

### Required Action Items for Worker

1. **Re-synthesize SBY Model with Active SVA**:
   Re-run `sby -f cache_sva.sby` ensuring `read_slang` picks up the active `cache_coherence_sva.sv` containing Ruling B5 A2.2a/A2.2b and the release tracker.
2. **Fix Gate 6 Audit Script**:
   Gate 6 must verify source invariance for **all** formal files, including `cache_coherence_sva.sv`:
   ```bash
   diff -u sva_formal_top.sv cache_sva_bmc/src/sva_formal_top.sv && \
   diff -u cache_coherence_sva.sv cache_sva_bmc/src/cache_coherence_sva.sv
   ```
3. **Remove S-State Eviction Over-Constraint in `sva_formal_top.sv`**:
   Update `is_held_state` to match DUT definition:
   ```systemverilog
   function automatic logic is_held_state(l1_state_t s);
     return (s == L1_S || s == L1_E || s == L1_M);
   endfunction
   ```
   Allow proactive eviction from `L1_S` so the formal engine can genuinely explore concurrent release races and verify that A2.2b handles the transient without assertion failure.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Source Diff against Synthesized Model**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
   diff -u cache_coherence_sva.sv cache_sva_bmc/src/cache_coherence_sva.sv
   ```
   *Expected result*: 60 lines of differences, showing missing `release_inflight` tracker and old `dir_sharers[k] == (...)` assertion.

2. **Verify Absence of In-Flight Tracker in Netlist**:
   ```bash
   grep -E "release_inflight|release_timer" cache_sva_bmc/model/design.il
   ```
   *Expected result*: Exit code 1 (0 matches).

3. **Verify S-State Eviction Over-Constraint**:
   ```bash
   sed -n '378,383p' sva_formal_top.sv
   ```
   *Expected result*: Shows `is_held_state` returning only `(s == L1_E || s == L1_M)` with comment explaining eviction suppression.
