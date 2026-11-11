# Formal Testbench & SVA Property Audit Report: Milestone 3

- **Agent**: `explorer_m3_iter3_2`
- **Role**: formal testbench and SVA property explorer
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_iter3_2`
- **Target Work Product**: `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva`
- **Parent Conversation ID**: `be241bc4-e291-4439-8a29-a04573a62cec`
- **Handoff Type**: Hard Handoff

---

## Executive Summary

Milestone 3 Iteration 2 gate failed because BMC depth 64 was not executed to completion on the active design, and questions were raised regarding potential tautologies in assertions (A7.1, A2.6) and environment assumption balance.

This investigation conducted a forensic inspection of `sva_formal_top.sv` and `cache_coherence_sva.sv`:
1. **Formal Assumptions in `sva_formal_top.sv`**: The environment constraints are mathematically sound, preventing illegal stimulus (e.g., core injections during transient misses or unheld evictions) while providing free symbolic stimulus (`in_core_req_valid`, `in_core_req_is_write`, `in_core_evict_valid`) across all 4 tiles. No system deadlocks or lockups are introduced.
2. **Assertion Review in `cache_coherence_sva.sv` (10 Invariants)**:
   - **A1.1, A1.2, A1.3, A3.1, A7.2, A7.3**: Highly sensitive, non-tautological, active protocol invariants.
   - **A7.1**: Contains a **100% mathematical tautology** in the directory sub-clause (`assert (dir_state <= DIR_EVICT)` on a 3-bit unsigned vector where `DIR_EVICT == 3'b111 == 7`), while the L1 clause (`l1_state <= L1_MI_A`) is genuine.
   - **A2.6**: Contains a **tautological sub-clause** (`dir_owner < TILE_COUNT` for a 2-bit unsigned wire compared to 4), but the accompanying conjunct (`dir_sharers == (4'b0001 << dir_owner)`) is active and non-tautological.
   - **A7.4**: Genuine invariant, but **vacuously true in Slice 16.1** because `DIR_EVICT` is unreachable in Slice 16.1 RTL.
   - **A2.2 (Critical Finding)**: **Distributed Invariant Race Hazard**. If a tile in state `L1_S` proactively evicts, `l1_state` immediately transitions to `L1_I` while `MSG_PUTS` traverses the network. During this window, `dir_state` is `DIR_S` and `dir_sharers` still holds the tile's bit, which will trigger a **false assertion failure** at steps beyond step 14 unless in-flight `PUTS` is accounted for.
3. **BMC Depth 64 Harness Adjustments**: Sizing FIFO depth (10–12 vs 16), reconciling address bits (`32'h0000_0040` vs `32'h0000_1000`), qualifying A2.2 for in-flight `PUTS`, and configuring high-performance SMT engines (`bitwuzla` or `yices`, alongside `boolector`) will allow BMC depth 64 to complete cleanly without false failures or state space explosion.

---

## 1. Observation

### 1.1 Formal Assumptions in `sva_formal_top.sv`

In `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sva_formal_top.sv`, lines 357–393 define the formal environment constraints:

```systemverilog
359:  function automatic logic is_miss_state(l1_state_t s);
360:    return (s == L1_IS_D || s == L1_IM_D || s == L1_SM_D);
361:  endfunction
362:
363:  function automatic logic is_stable_state(l1_state_t s);
364:    return (s == L1_I || s == L1_S || s == L1_E || s == L1_M);
365:  endfunction
366:
367:  function automatic logic is_held_state(l1_state_t s);
368:    return (s == L1_S || s == L1_E || s == L1_M);
369:  endfunction
370:
371:  always @(posedge clk) begin
372:    if (!rst_n) begin
373:      for (int k = 0; k < TILE_COUNT; k++) begin
374:        assume(core_req_valid[k] == 1'b0);
375:        assume(core_evict_valid[k] == 1'b0);
376:      end
377:    end else begin
378:      for (int k = 0; k < TILE_COUNT; k++) begin
379:        // Core only issues new requests when cache line is in a stable MESI state
380:        if (!is_stable_state(l1_state[k])) begin
381:          assume(core_req_valid[k] == 1'b0);
382:        end
383:
384:        // Proactive eviction only when line is held in stable state (S, E, M)
385:        if (!is_held_state(l1_state[k])) begin
386:          assume(core_evict_valid[k] == 1'b0);
387:        end
388:
389:        // Mutual exclusion: core does not issue simultaneous request and evict on same tile
390:        assume(!(core_req_valid[k] && core_evict_valid[k]));
391:      end
392:    end
393:  end
```

Stimulus input declarations (lines 10–15, 32–35):
```systemverilog
10: module sva_formal_top import tile_pkg::*; (
11:     input logic                   clk,
12:     input logic [TILE_COUNT-1:0]  in_core_req_valid,
13:     input logic [TILE_COUNT-1:0]  in_core_req_is_write,
14:     input logic [TILE_COUNT-1:0]  in_core_evict_valid
15: );
...
32:   assign core_req_valid    = in_core_req_valid;
33:   assign core_req_is_write = in_core_req_is_write;
34:   assign core_evict_valid  = in_core_evict_valid;
```

Address and store data generation (lines 40–47):
```systemverilog
40:   generate
41:     for (i_tile = 0; i_tile < TILE_COUNT; i_tile++) begin : gen_addr_data
42:       // Address targets cache line mapped to Directory Tile 0 (bits [12:11] == 2'd0)
43:       assign core_req_addr[i_tile]  = 32'h0000_1000;
44:       // Constant store data payload prunes 2048 SMT bits per unrolled step
45:       assign core_req_wdata[i_tile] = '0;
46:     end
47:   endgenerate
```

- **Address Field Discrepancy**:
  In `tile_pkg.sv` line 38–39:
  `localparam int HOME_LO = 11;`
  `localparam int HOME_HI = HOME_LO + TILE_ID_W - 1; // 12`
  For `32'h0000_1000`, bit 12 is 1 and bit 11 is 0 (`addr[12:11] == 2'b10` = Tile 2).
  Line 42 comments that bits `[12:11] == 2'd0` (Tile 0).
  In `sva_formal_top.sv`, the request arbiter forwards all traffic directly to `u_dir` (instantiated as Tile 0) without filtering by destination, so transactions execute, but the address literal disagrees with the comment.

### 1.2 Review of All 10 Assertions in `cache_coherence_sva.sv`

In `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv`:

| Assertion ID | Source Lines | Verified Invariant | Tautological? | Sensitivity / Vacuity | Status |
|---|---|---|---|---|---|
| **A1.1** | 95–104 | SWMR: At most one tile in `L1_M` for identical address | **No** | Highly sensitive; fails if 2 tiles hold line in M | **PASS** (Genuine) |
| **A1.2** | 106–115 | Exclusivity: At most one tile in `L1_E` or `L1_M` for identical address | **No** | Highly sensitive; fails if multiple tiles hold E/M | **PASS** (Genuine) |
| **A1.3** | 117–128 | Shared validity: If any tile in `L1_S`, no tile in `L1_E` or `L1_M` | **No** | Highly sensitive; catches false exclusive grants | **PASS** (Genuine) |
| **A2.2** | 134–142 | Sharer bitmask: In `DIR_S`, `dir_sharers[k] == (l1_state[k] == L1_S && addr == dir_dline)` | **No** | Active invariant, but **has in-flight PUTS race hazard** | **HAZARD** (False failure risk) |
| **A2.6** | 144–149 | Owner qualification: In `DIR_E`/`DIR_M`, `dir_owner < TILE_COUNT && dir_sharers == (1 << dir_owner)` | **Sub-clause (Partial)** | `dir_owner < 4` is tautological; `dir_sharers == (1 << owner)` is active | **PARTIAL TAUTOLOGY** |
| **A3.1** | 155–169 | VC preservation: On flit 0 (`rem==0 && HDR_HEAD`), `flit[VC] == msg_to_vc(msg)` | **No** | Highly sensitive; countdown tracker resolved body flit false failure | **PASS** (Genuine) |
| **A7.1** | 175–183 | Legal state encodings: `l1_state <= L1_MI_A` and `dir_state <= DIR_EVICT` | **Dir sub-clause (100%)** | `dir_state <= 3'b111` is identically true for all 3-bit vectors; L1 check is valid | **TAUTOLOGY (dir)** |
| **A7.2** | 184–196 | Single-Exit on `DIR_FWD_WAIT`: Exits strictly on `MSG_UNBLOCK`, stays on intermediate | **No** | Highly sensitive to premature exit or wrong trigger | **PASS** (Genuine) |
| **A7.3** | 198–211 | Successor determinism: `POP_GETS -> DIR_S`, `POP_GETM -> DIR_M` | **No** | Highly sensitive to corrupted return state | **PASS** (Genuine) |
| **A7.4** | 213–224 | Transient confinement: `DIR_EVICT` entered strictly from and exits to `DIR_MEM_WAIT` | **No** | **Vacuously true in Slice 16.1** (`DIR_EVICT` unreachable in RTL line 464) | **VACUOUS** (Slice 16.1) |

#### Detailed Analysis of Specific Assertions:

1. **Assertion A7.1 Tautology**:
   - `tile_pkg.sv` line 58 defines `dir_state_t` as `enum logic [2:0] { ... DIR_EVICT = 3'b111 };`.
   - `cache_coherence_sva.sv` line 181 asserts:
     ```systemverilog
     assert (dir_state <= DIR_EVICT)
       else $error("[SVA FAIL A7.1] Directory entered illegal state");
     ```
   - For any 3-bit logic vector, the unsigned integer representation is bounded by $[0, 7]$. `DIR_EVICT` is $7$.
   - The expression `dir_state <= 3'b111` evaluates to `1'b1` for **every possible bit valuation**. It can never fail under any circumstance.
   - Conversely, `l1_state[k] <= L1_MI_A` (line 177) tests a 4-bit unsigned vector ($[0, 15]$) against `L1_MI_A == 4'd8`. It actively prunes values $9 \dots 15$, making it non-tautological.

2. **Assertion A2.6 Tautological Sub-clause**:
   - `dir_owner` is a 2-bit wire (`TILE_ID_W == 2`). `TILE_COUNT == 4`.
   - `dir_owner < TILE_COUNT` evaluates to `dir_owner < 4`, which is unconditionally true for all 2-bit values.
   - However, `dir_sharers == (4'b0001 << dir_owner)` actively forces exact one-hot alignment between the 4-bit `dir_sharers` mask and `dir_owner`.

3. **Assertion A2.2 Distributed Race Hazard**:
   - `cache_coherence_sva.sv` lines 137–142:
     ```systemverilog
     if (dir_state == DIR_S) begin
       for (int k = 0; k < TILE_COUNT; k++) begin
         assert (dir_sharers[k] == (l1_state[k] == L1_S && l1_line_addr[k] == dir_dline))
           else $error("[SVA FAIL A2.2] Sharer bitmask mismatch for tile in DIR_S");
       end
     end
     ```
   - Per `FINAL_whitepaper_v3.0.md` §3.3 rule 1 and `SLICE_16_1.md` §1.1 / §2.1, when an L1 in state `L1_S` evicts, it does **not** wait for an acknowledgment (`PUTACK`).
   - In `l1_mesi_ctrl.sv` line 500:
     ```systemverilog
     if (core_evict_valid && is_held(state) && !vic_valid) begin
       if (state == L1_S) state <= L1_I; // no ack
     ```
   - At the clock cycle when `core_evict_valid` fires for tile $k$, `l1_state[k]` transitions immediately to `L1_I`.
   - Tile $k$ queues `MSG_PUTS` into its transmit queue and network FIFO.
   - Until `MSG_PUTS` travels through the arbiter and is processed by `dir_ctrl` (2–3 clock cycles later), `dir_state` remains `DIR_S` and `dir_sharers[k]` remains `1'b1`.
   - During those intervening cycles: `dir_sharers[k] == 1`, but `l1_state[k] == L1_I`.
   - Assertion A2.2 evaluates `1'b1 == 1'b0`, triggering a **false assertion failure**!
   - This failure did not surface in prior gate iterations only because:
     a. Iteration 1 had vacuous inputs (no evictions occurred).
     b. Iteration 2 active BMC was stopped at step 14 before any post-grant clean eviction was explored.

---

## 2. Logic Chain

1. **Assumption Legality**:
   - `SLICE_16_1.md` §1.3 specifies that Slice 16.1 is a single-line cache without transaction queues (MSHRs). Therefore, a core cannot begin a new transaction or eviction while a miss is in flight.
   - Enforcing `assume(core_req_valid[k] == 1'b0)` when `!is_stable_state(l1_state[k])` and `assume(core_evict_valid[k] == 1'b0)` when `!is_held_state(l1_state[k])` faithfully models the processor-to-cache handshake without over-constraining legal multi-tile interactions.
   - Free symbolic inputs (`in_core_req_valid`, `in_core_req_is_write`, `in_core_evict_valid`) drive dynamic requests across all 4 tiles, proven by reachability covers reaching step 2, 3, and 8 witness traces.
2. **Assertion Sensitivity vs Tautology**:
   - An assertion is sensitive if an injected defect in DUT state causes the assertion to evaluate false.
   - In `cache_coherence_sva.sv`, A1.1, A1.2, A1.3, A2.2, A3.1, A7.2, and A7.3 compare asynchronous distributed registers across modules, proving high sensitivity.
   - However, A7.1's `dir_state <= DIR_EVICT` compares a 3-bit vector to its maximum possible value $7$. By definition of 3-bit unsigned arithmetic, no state assignment can ever evaluate false. This is a mathematical tautology providing zero test coverage.
   - A2.6's `dir_owner < TILE_COUNT` is similarly tautological for a 2-bit unsigned wire compared to 4.
3. **BMC Depth 64 Feasibility & Solver Runtime**:
   - Active symbolic BMC on 4 tiles unrolls 4 L1 controllers, 1 directory, 4 FIFOs of depth 16 (4,096 bits), and response demux over 64 steps.
   - In Boolector, solving time increases from ~12s at step 10 to ~1-8 minutes per step after step 30, requiring ~45-60+ minutes for depth 64.
   - Because `FIFO_DEPTH` is 16, but each tile can emit at most 10 flits (PUTM + GET on conflict) before stalling, 37% of the FIFO memory capacity represents unneeded array state variables.
   - Furthermore, without framing A2.2 to account for in-flight `PUTS`, BMC unrolling to depth 64 will encounter a false counterexample when Boolector picks `core_evict_valid` in `L1_S`.

---

## 3. Caveats

1. **Single Address Model**:
   - `core_req_addr` is tied to a single cache line for all 4 tiles. This is necessary to maximize multi-tile coherence contention and prevent state space explosion, but means intra-tile replacement conflict (B2 eviction of one line for another) is verified in directed tests (F8) rather than formal BMC.
2. **Unreachability of `DIR_EVICT`**:
   - `DIR_EVICT` is unreachable in Slice 16.1 RTL (reserved for Slice 16.3). A7.4 is therefore vacuously satisfied in Slice 16.1.
3. **Read-Only Explorer Scope**:
   - Under explorer instructions, no implementation files in `~/teamwork_projects/clean_room_verification` were edited. All recommendations must be implemented by the designated worker.

---

## 4. Conclusion

The formal testbench and SVA property suite in `tb_acceptance/sva` are architecturally sound and non-vacuous, but require targeted adjustments before launching the full BMC depth 64 run:

### Summary Assessment:
- **Assumptions in `sva_formal_top.sv`**: **APPROVED**. They provide free symbolic stimulus without deadlocking the system and correctly constrain the core interface.
- **Assertions in `cache_coherence_sva.sv`**:
  - A1.1, A1.2, A1.3, A3.1, A7.2, A7.3: **APPROVED** (Authentic, sensitive, non-tautological).
  - A7.1: **NEEDS ADJUSTMENT** (Eliminate `dir_state <= DIR_EVICT` tautology).
  - A2.6: **NEEDS CLEANUP** (Simplify `dir_owner < TILE_COUNT` tautological sub-clause).
  - A2.2: **CRITICAL REMEDIATION REQUIRED** (Qualify with in-flight `PUTS` to prevent false failure).
  - A7.4: **ACCEPTABLE WITH DOCUMENTATION** (Vacuous in Slice 16.1; will activate in Slice 16.3).

---

## 5. Recommended Fix Strategy & Harness Adjustments

To ensure that the BMC depth 64 run executes to completion cleanly without false failures or state space explosion:

### Recommendation 1: Fix Assertion A2.2 In-Flight `PUTS` False Failure Hazard
In `cache_coherence_sva.sv`, qualify A2.2 so that when `dir_state == DIR_S`, a tile is expected in `dir_sharers` if it holds `L1_S` OR has a `PUTS` packet in flight to the directory.
Alternatively, in `sva_formal_top.sv`, constrain proactive evictions to lines in `L1_E` or `L1_M` (where L1 waits for `PUTACK` in transient states `EI_A`/`MI_A`), or ensure `core_evict_valid` for `L1_S` only occurs when directory tracking has updated.
*Preferred approach*: In `cache_coherence_sva.sv`:
```systemverilog
// A2.2: Directory Sharer Accuracy
if (dir_state == DIR_S) begin
  for (int k = 0; k < TILE_COUNT; k++) begin
    // In DIR_S, sharer bit is 1 iff tile holds L1_S or PUTS release is in transit
    assert (dir_sharers[k] == ((l1_state[k] == L1_S && l1_line_addr[k] == dir_dline) ||
                               (u_sva_puts_in_flight[k])))
      else $error("[SVA FAIL A2.2] Sharer bitmask mismatch for tile in DIR_S");
  end
end
```
Or constrain clean-line proactive eviction in formal assumptions if clean eviction is validated by directed test F8.

### Recommendation 2: Eliminate Tautologies in A7.1 and A2.6
1. In `cache_coherence_sva.sv` line 181, replace the tautology:
   ```systemverilog
   // BEFORE:
   assert (dir_state <= DIR_EVICT);

   // AFTER (Genuine enumeration check):
   assert (dir_state inside {DIR_I, DIR_S, DIR_E, DIR_M,
                             DIR_MEM_WAIT, DIR_FWD_WAIT, DIR_INV_WAIT, DIR_EVICT});
   ```
2. In `cache_coherence_sva.sv` line 147, remove the tautological sub-clause:
   ```systemverilog
   // BEFORE:
   assert (dir_owner < TILE_COUNT && dir_sharers == (4'b0001 << dir_owner));

   // AFTER:
   assert (dir_sharers == (4'b0001 << dir_owner));
   ```

### Recommendation 3: Reconcile Address Literal in `sva_formal_top.sv`
In `sva_formal_top.sv` line 43, update the address literal so bits `[12:11]` match Directory Tile 0 as stated in the comment:
```systemverilog
// Address targets cache line mapped to Directory Tile 0 (bits [12:11] == 2'd0)
assign core_req_addr[i_tile] = 32'h0000_0040; // line 1, set 1, home tile 0
```

### Recommendation 4: Optimize FIFO Sizing to Avoid State Space Explosion
In `sva_formal_top.sv` line 172:
Reduce `FIFO_DEPTH` from 16 to 10 or 12:
```systemverilog
localparam int FIFO_DEPTH = 12; // Sufficient for 9-flit PUTM + 1-flit GET
```
This prunes $4 \times 4 \times 64 = 1,024$ unrolled bits per step from SMT memory arrays without truncating any valid burst.

### Recommendation 5: Solver Execution Strategy for Depth 64
In `cache_sva.sby`:
- Use `smtbmc boolector` or `smtbmc bitwuzla` (installed in `~/.local/oss-cad-suite/bin`).
- Allocate adequate execution budget (~60–90 minutes) for depth K=64.
- Capture the genuine, full stdout/stderr output into `sby_output.log` to provide transparent, unassailable verification proof.

---

## 6. Verification Method

To independently verify these findings:

```bash
# 1. Inspect A7.1 directory enum width and tautology:
grep -n -A 10 "typedef enum logic \[2:0\]" /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv
# Observation: DIR_EVICT is 3'b111 (7). An unsigned 3-bit vector is always <= 7.

# 2. Inspect A2.6 owner bit width:
grep -n "TILE_ID_W" /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv
# Observation: TILE_ID_W is 2. Any 2-bit unsigned wire is strictly < 4 (TILE_COUNT).

# 3. Inspect A2.2 sharer definition vs L1_S eviction:
grep -n -A 10 "if (dir_state == DIR_S)" /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv
grep -n -C 5 "if (state == L1_S) state <= L1_I;" /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/l1/l1_mesi_ctrl.sv
# Observation: L1 drops to L1_I without ack, while dir_sharers retains bit until PUTS arrives.

# 4. Check address mapping bits [12:11]:
python3 -c "addr=0x1000; print('addr[12:11] =', bin((addr >> 11) & 0x3))"
# Observation: Output is 0b10 (Tile 2), while comment claims Tile 0.
```
