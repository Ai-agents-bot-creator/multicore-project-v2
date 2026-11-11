# Handoff Report: Explorer M3 Fix 1 (Stimulus Architecture & Non-Vacuity Explorer)

**Role:** Explorer M3 Fix 1 (Stimulus Architecture & Non-Vacuity Explorer)  
**Milestone:** Milestone 3 Remediation (SVA Formal Verification & Bounded Model Checking K=64)  
**Target Work Product:** `~/teamwork_projects/clean_room_verification/tb_acceptance/sva`  
**Parent Agent:** `b25d00b4-87e5-4b35-8417-bffe75bad4d9`  
**Status:** Hard Handoff (Investigation & Strategy Design Complete)

---

## 1. Observation

### 1.1 Root Cause of Testbench Vacuity in `sva_formal_top.sv`
In `~/teamwork_projects/clean_room_verification/tb_acceptance/sva/sva_formal_top.sv` (lines 10–12 and 25–30):
```systemverilog
module sva_formal_top import tile_pkg::*; (
    input logic clk
);

// Core Stimulus Inputs (constrained by formal assumptions)
logic        core_req_valid   [TILE_COUNT];
logic        core_req_is_write[TILE_COUNT];
logic [ADDR_W-1:0] core_req_addr [TILE_COUNT];
logic [LINE_BITS-1:0] core_req_wdata [TILE_COUNT];
logic        core_evict_valid [TILE_COUNT];
```
And in lines 349–355:
```systemverilog
always @(posedge clk) begin
  if (!rst_n) begin
    for (int k = 0; k < TILE_COUNT; k++) begin
      assume(core_req_valid[k] == 1'b0);
      assume(core_evict_valid[k] == 1'b0);
    end
  end else begin
```
When synthesized with Yosys (`read_slang`), inspect the generated RTLIL netlist in `cache_sva/model/design.il` (lines 12042–12185):
```il
cell $mem_v2 $pub@1059  # \core_req_wdata
  parameter \WIDTH 512
  parameter \SIZE 4
  parameter \WR_PORTS 0
  connect \WR_EN { }

cell $mem_v2 $pub@1056  # \core_req_valid
  parameter \WIDTH 1
  parameter \SIZE 4
  parameter \WR_PORTS 0
  connect \WR_EN { }

cell $mem_v2 $pub@1057  # \core_req_is_write
  parameter \WIDTH 1
  parameter \SIZE 4
  parameter \WR_PORTS 0
  connect \WR_EN { }

cell $mem_v2 $pub@1058  # \core_req_addr
  parameter \WIDTH 32
  parameter \SIZE 4
  parameter \WR_PORTS 0
  connect \WR_EN { }

cell $mem_v2 $pub@1060  # \core_evict_valid
  parameter \WIDTH 1
  parameter \SIZE 4
  parameter \WR_PORTS 0
  connect \WR_EN { }
```
And in the unrolled SMT2 translation `cache_sva/model/design_smt2.smt2` (lines 7394–7397):
```smt2
(= (|sva_formal_top#537#0| state) (|sva_formal_top#537#0| next_state)) ; core_req_valid
(= (|sva_formal_top#551#0| state) (|sva_formal_top#551#0| next_state)) ; core_evict_valid
```
Because `core_req_valid` and `core_evict_valid` were declared as unpacked arrays without procedural drivers or input ports, Slang and Yosys elaborated them into unwritten read-only memory cells (`rom: true`, `WR_PORTS=0`).
Because `assume(core_req_valid[k] == 0)` was asserted during reset at cycle 0, and the memory cell has no write port, the SMT solver mathematically forced `core_req_valid` to `0` across **all cycles $t \in [0, 63]$**.
Empirically, all L1 caches remained in `L1_I` and the Directory in `DIR_I` across all 64 steps, resulting in 100% vacuous assertion passes.

### 1.2 Synthesis Verification of Top-Level Stimulus Ports
In an isolated verification sandbox (`/tmp/explorer_m3_sandbox/`), `sva_formal_top.sv` was modified to expose primary input ports:
```systemverilog
module sva_formal_top import tile_pkg::*; (
    input logic clk,
    input logic [TILE_COUNT-1:0] in_core_req_valid,
    input logic [TILE_COUNT-1:0] in_core_req_is_write,
    input logic [TILE_COUNT-1:0] in_core_evict_valid
);
```
With packed bitvector assignments and constant continuous drivers for addresses and write data:
```systemverilog
  logic [TILE_COUNT-1:0] core_req_valid;
  logic [TILE_COUNT-1:0] core_req_is_write;
  logic [TILE_COUNT-1:0] core_evict_valid;

  assign core_req_valid    = in_core_req_valid;
  assign core_req_is_write = in_core_req_is_write;
  assign core_evict_valid  = in_core_evict_valid;

  logic [ADDR_W-1:0]    core_req_addr [TILE_COUNT];
  logic [LINE_BITS-1:0] core_req_wdata [TILE_COUNT];

  genvar i_tile;
  generate
    for (i_tile = 0; i_tile < TILE_COUNT; i_tile++) begin : gen_addr_data
      assign core_req_addr[i_tile]  = 32'h0000_1000;
      assign core_req_wdata[i_tile] = '0;
    end
  endgenerate
```
Synthesizing this via `read_slang ...; prep -top sva_formal_top; write_rtlil test_out.il` produced:
```il
6271:  attribute \hdlname "in_core_req_valid"
6272:  wire width 4 input 2 $pub@1055  # \in_core_req_valid
6274:  attribute \hdlname "in_core_req_is_write"
6275:  wire width 4 input 3 $pub@1056  # \in_core_req_is_write

39617: connect \gen_l1[3].u_l1.core_req_addr 4096
39651: connect \gen_l1[2].u_l1.core_req_addr 4096
39685: connect \gen_l1[1].u_l1.core_req_addr 4096
39719: connect \gen_l1[0].u_l1.core_req_addr 4096

39616: connect \gen_l1[3].u_l1.core_req_wdata 512'0
39650: connect \gen_l1[2].u_l1.core_req_wdata 512'0
39684: connect \gen_l1[1].u_l1.core_req_wdata 512'0
39718: connect \gen_l1[0].u_l1.core_req_wdata 512'0
```
- **Verification Result**: `grep -n "\$mem_v2.*core" test_out.il` returned 0 matches (`Exit code: 1`).
- **Memory ROM Elimination**: Zero unwritten memory cells remain.
- **SMT Complexity Reduction**: Replacing the 512-bit `core_req_wdata` unpacked memory with a continuous assignment of 0 eliminated 2,048 bits of unconstrained SMT state per unrolled step.

### 1.3 Empirical Non-Vacuity Verification via SymbiYosys Cover Mode
In the sandbox, four cover properties were embedded:
```systemverilog
cov_req_0:   cover (core_req_valid[0]);
cov_l1_is_d: cover (l1_state[0] == L1_IS_D);
cov_l1_im_d: cover (l1_state[0] == L1_IM_D);
cov_dir_mem: cover (dir_state_o == DIR_MEM_WAIT);
```
Executing SymbiYosys in `mode cover` with `depth 10` (`sby -f test_cover.sby`):
```
SBY summary: engine_0 (smtbmc boolector) returned pass
SBY summary: cover trace: test_cover/engine_0/trace0.vcd
SBY summary:   reached cover statement sva_formal_top.cov_req_0 at sva_formal_top.sv step 2
SBY summary: cover trace: test_cover/engine_0/trace1.vcd
SBY summary:   reached cover statement sva_formal_top.cov_l1_is_d at sva_formal_top.sv step 3
SBY summary: cover trace: test_cover/engine_0/trace2.vcd
SBY summary:   reached cover statement sva_formal_top.cov_l1_im_d at sva_formal_top.sv step 3
SBY summary: cover trace: test_cover/engine_0/trace3.vcd
SBY summary:   reached cover statement sva_formal_top.cov_dir_mem at sva_formal_top.sv step 8
SBY DONE (PASS, rc=0)
```
Elapsed clock time was **27 seconds**. All four cover statements were reached, generating full VCD traces (`trace0.vcd` through `trace3.vcd`) and witness files (`.yw`), mathematically proving that transactions are active and states are reached.

### 1.4 Latent Defect Uncovered in A3.1 Flit Header Assertion
When running BMC depth 15 with active stimulus, Boolector failed at step 12:
```
Assert failed in sva_formal_top: cache_coherence_sva.sv:121.9-123.69 (_witness_.check_3954)
failed assertion sva_formal_top._witness_.check_3954 at cache_coherence_sva.sv:121.9-123.69 step 12
```
In `cache_coherence_sva.sv` lines 120–124:
```systemverilog
if (dir_noc_rsp_valid && dir_noc_rsp_flit[HDR_HEAD]) begin
  assert (dir_noc_rsp_flit[HDR_VC_HI:HDR_VC_LO] ==
          msg_to_vc(msg_type_t'(dir_noc_rsp_flit[HDR_MSG_HI:HDR_MSG_LO])))
```
On a 9-flit DATA packet, flits 1..8 contain raw 64-bit cache line data (`bank_storage = {8{64'hA0A1A2A3A4A5A6A0}}`). In data byte `0xA2` (`8'b1010_0010`), bit 41 is 1. The assertion erroneously treated body data flits as packet headers and failed.
When flit sequence trackers were added to ensure A3.1 only evaluates on flit 0 (`!dir_rsp_in_pkt`), the step 12 assertion failure completely vanished.

---

## 2. Logic Chain

1. In SystemVerilog, unpacked arrays (`logic x [N]`) without procedural assignment drivers are synthesized by Yosys / Slang AST passes as `$mem_v2` memory cells with `WR_PORTS=0`.
2. When Yosys exports the design to SMT2 for Boolector, memory arrays without write ports are unrolled with state equality constraints: `(= state next_state)`.
3. The reset assumption `assume(core_req_valid[k] == 1'b0)` at cycle 0 initializes the memory to 0. Because next state equals state, `core_req_valid` is permanently 0 for all $t \ge 0$.
4. Zero requests reach the L1 controllers; all L1s remain in `L1_I` and the Directory in `DIR_I`. All coherence assertions pass vacuously because their trigger guards are never reached.
5. Declaring `in_core_req_valid`, `in_core_req_is_write`, and `in_core_evict_valid` as top-level input ports on `sva_formal_top` forces Yosys to elaborate them as primary input bitvectors (`wire width 4 input`).
6. In formal BMC, primary inputs are free symbolic variables at each cycle $t \ge 1$, subject only to assumptions evaluated in cycle $t$.
7. Declaring `assign core_req_addr[t] = 32'h0000_1000` and `assign core_req_wdata[t] = '0` replaces undriven 512-bit unpacked arrays with constant bitvectors, eliminating all memory cells from the stimulus interface and pruning 2,048 bits of state variables per SMT step.
8. Under this active stimulus, formal reachability checks in SymbiYosys cover mode prove that core requests trigger at cycle 2, L1 transitions to `L1_IS_D`/`L1_IM_D` at cycle 3, and Directory transitions to `DIR_MEM_WAIT` at cycle 8.
9. Therefore, the top-level port stimulus architecture provides genuine, non-vacuous formal verification while maintaining minimal SMT complexity.

---

## 3. Caveats

- **Clean-Room Isolation**: All investigations, tests, and verifications were conducted strictly on `tb_acceptance/sva/` and isolated `/tmp/explorer_m3_sandbox/`. Zero quarantined files from `tb/self_test/` or `tb/l1_dir/` were inspected or copied.
- **Frozen RTL Integrity**: RTL in `rtl_frozen/` was treated strictly as a read-only black box.
- **Coordination with Explorer M3 Fix 2**: Explorer Fix 2 is specifically analyzing property semantics and assertion framing for A3.1. The flit tracker sandbox test in this report was performed strictly to confirm that the active stimulus architecture can achieve step 12+ BMC depth without assertion blockage.

---

## 4. Conclusion & Recommended Remediation Strategy for Worker M3

### Action Item 1: Update Top-Level Ports in `tb_acceptance/sva/sva_formal_top.sv`
Replace the `sva_formal_top` module port declaration:
```systemverilog
// sva_formal_top.sv
module sva_formal_top import tile_pkg::*; (
    input logic                   clk,
    input logic [TILE_COUNT-1:0]  in_core_req_valid,
    input logic [TILE_COUNT-1:0]  in_core_req_is_write,
    input logic [TILE_COUNT-1:0]  in_core_evict_valid
);
```

### Action Item 2: Replace Unpacked Stimulus Declarations with Packed Stimulus Wires
In `sva_formal_top.sv`, replace lines 25–30 with:
```systemverilog
  // ---------------------------------------------------------------------------
  // Core Stimulus Inputs (driven by top-level formal symbolic inputs)
  // ---------------------------------------------------------------------------
  logic [TILE_COUNT-1:0] core_req_valid;
  logic [TILE_COUNT-1:0] core_req_is_write;
  logic [TILE_COUNT-1:0] core_evict_valid;

  assign core_req_valid    = in_core_req_valid;
  assign core_req_is_write = in_core_req_is_write;
  assign core_evict_valid  = in_core_evict_valid;

  logic [ADDR_W-1:0]    core_req_addr [TILE_COUNT];
  logic [LINE_BITS-1:0] core_req_wdata [TILE_COUNT];

  genvar i_tile;
  generate
    for (i_tile = 0; i_tile < TILE_COUNT; i_tile++) begin : gen_addr_data
      // Address targets cache line mapped to Directory Tile 0 (bits [12:11] == 2'd0)
      assign core_req_addr[i_tile]  = 32'h0000_1000;
      // Constant store data payload prunes 2048 SMT bits per unrolled step
      assign core_req_wdata[i_tile] = '0;
    end
  endgenerate
```

### Action Item 3: Update Formal Environment Assumptions
In `sva_formal_top.sv`, refine the environment assumptions:
```systemverilog
  function automatic logic is_miss_state(l1_state_t s);
    return (s == L1_IS_D || s == L1_IM_D || s == L1_SM_D);
  endfunction

  function automatic logic is_stable_state(l1_state_t s);
    return (s == L1_I || s == L1_S || s == L1_E || s == L1_M);
  endfunction

  function automatic logic is_held_state(l1_state_t s);
    return (s == L1_S || s == L1_E || s == L1_M);
  endfunction

  always @(posedge clk) begin
    if (!rst_n) begin
      for (int k = 0; k < TILE_COUNT; k++) begin
        assume(core_req_valid[k] == 1'b0);
        assume(core_evict_valid[k] == 1'b0);
      end
    end else begin
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
  end
```

### Action Item 4: Add Formal Reachability & Non-Vacuity Cover Properties
Add cover properties directly inside `sva_formal_top.sv` (or in a dedicated verification block) to prove reachability:
```systemverilog
  // ---------------------------------------------------------------------------
  // Non-Vacuity Reachability Covers
  // ---------------------------------------------------------------------------
  always @(posedge clk) begin
    if (rst_n) begin
      cov_core_req:     cover (core_req_valid[0]);
      cov_l1_is_d:      cover (l1_state[0] == L1_IS_D);
      cov_l1_im_d:      cover (l1_state[0] == L1_IM_D);
      cov_l1_s:         cover (l1_state[0] == L1_S);
      cov_l1_e:         cover (l1_state[0] == L1_E);
      cov_l1_m:         cover (l1_state[0] == L1_M);
      cov_dir_mem_wait: cover (dir_state_o == DIR_MEM_WAIT);
      cov_dir_s:        cover (dir_state_o == DIR_S);
      cov_dir_e:        cover (dir_state_o == DIR_E);
      cov_dir_m:        cover (dir_state_o == DIR_M);
      cov_dir_fwd_wait: cover (dir_state_o == DIR_FWD_WAIT);
    end
  end
```

### Action Item 5: Provide SBY Targets for BMC and Cover
In `cache_sva.sby`, define tasks or a companion `cache_cover.sby` file:
```ini
# cache_sva.sby
[tasks]
bmc
cover

[options]
bmc: mode bmc
bmc: depth 64
cover: mode cover
cover: depth 20

[engines]
smtbmc boolector

[script]
read_slang tile_pkg.sv l1_mesi_ctrl.sv dir_ctrl.sv cache_coherence_sva.sv sva_formal_top.sv
prep -top sva_formal_top

[files]
/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv
/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/l1/l1_mesi_ctrl.sv
/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv
/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sva_formal_top.sv
```

---

## 5. Verification Method

To independently verify the proposed stimulus architecture and non-vacuity proofs:

```bash
# 1. Set PATH for toolchain
export PATH="/usr/bin:/home/durgesh/.local/oss-cad-suite/bin:$PATH"

# 2. Check RTLIL netlist to verify zero memory cells exist for stimulus:
cd /tmp/explorer_m3_sandbox
yosys -p 'read_slang /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv \
                     /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/l1/l1_mesi_ctrl.sv \
                     /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv \
                     cache_coherence_sva.sv sva_formal_top.sv; \
          prep -top sva_formal_top; \
          write_rtlil check.il'
grep -n "\$mem_v2.*core" check.il
# Expected: Exit code 1 (no lines returned, 0 mem cells)

# 3. Verify top-level stimulus ports in check.il:
grep -n "in_core_req" check.il
# Expected: wire width 4 input 2 \in_core_req_valid
#           wire width 4 input 3 \in_core_req_is_write

# 4. Verify formal non-vacuity via SBY cover mode:
sby -f test_cover.sby
# Expected: reached cov_req_0 (step 2), cov_l1_is_d (step 3), cov_l1_im_d (step 3), cov_dir_mem (step 8)
# Status: PASS (rc=0)
```

**Invalidation Conditions:**
- Any occurrence of `$mem_v2` for `core_req_valid`, `core_req_is_write`, `core_evict_valid`, `core_req_addr`, or `core_req_wdata`.
- Any BMC pass where `cov_req_0` or `cov_dir_mem` cannot be reached.
