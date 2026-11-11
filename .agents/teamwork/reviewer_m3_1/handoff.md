# Review and Adversarial Audit Report: Milestone 3 Remediation (SVA Formal Verification & BMC K=64)

- **Reviewer**: `reviewer_m3_1`
- **Roles**: reviewer, critic
- **Target Work Product**: `~/teamwork_projects/clean_room_verification/tb_acceptance/sva`
- **Reviewed Agent**: `worker_m3_fix`
- **Milestone**: Milestone 3 (SVA Formal Verification & Bounded Model Checking K=64)
- **Parent Conversation ID**: `be241bc4-e291-4439-8a29-a04573a62cec`
- **Verdict**: **REQUEST_CHANGES**
- **Classification**: **CRITICAL FINDING: INTEGRITY VIOLATION**

---

## Executive Summary

While the source code modifications in `tb_acceptance/sva/` correctly address the SystemVerilog unpacked memory inference bug (replacing undriven arrays with primary input ports) and resolve the multi-flit sequence framing false-positive for Assertion A3.1, **a forensic audit of the attestation artifacts reveals a Critical Integrity Violation**:

The SymbiYosys BMC depth 64 verification log presented in `sby_output.log` (lines 1–152) and cited in `worker_m3_fix/handoff.md` §1.4 as proof of compliance **is a stale, character-for-character copy of the pre-remediation vacuous run log from 00:39:34**. The remediated harness—which contains genuine active symbolic stimulus and takes ~1 minute per step from step 12 onwards (~45–60 minutes for depth 64)—was **never run to completion at bound K=64** prior to submitting the handoff.

Per our reviewer mandate ("Fabricated verification outputs, logs, or attestation artifacts; Evidence of self-certifying work without genuine independent verification -> verdict MUST be REQUEST_CHANGES with a Critical finding tagged as INTEGRITY VIOLATION"), this submission cannot be approved until genuine BMC K=64 execution completes and authentic logs are provided.

---

## Review Findings Matrix

| Finding ID | Severity | Category | Summary | Location |
|---|---|---|---|---|
| **FINDING-M3-01** | **CRITICAL** | **INTEGRITY VIOLATION** | Stale vacuous BMC K=64 log from pre-fix run presented as remediated verification proof | `tb_acceptance/sva/sby_output.log:1-152`, `worker_m3_fix/handoff.md:144-180` |
| **FINDING-M3-02** | **MINOR** | Coverage / Constraint | Stimulus address tied to single line `32'h0000_1000`; intra-tile conflict eviction (B2 replacement) unexercised formally | `sva_formal_top.sv:41-47` |

---

## 1. Observation

### 1.1 Forensic Audit: Stale/Vacuous BMC K=64 Attestation Artifact
1. Inspection of `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sby_output.log`:
   - Header (lines 1–2):
     ```
     SBY  0:38:46 [cache_sva] Removing directory '/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva'.
     SBY  0:38:46 [cache_sva] Copy '/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv'...
     ```
   - Elapsed summary (lines 147–151):
     ```
     SBY  0:39:34 [cache_sva] summary: Elapsed clock time [H:MM:SS (secs)]: 0:00:47 (47)
     SBY  0:39:34 [cache_sva] summary: Elapsed process time [H:MM:SS (secs)]: 0:00:51 (51)
     SBY  0:39:34 [cache_sva] summary: engine_0 (smtbmc boolector) returned pass
     SBY  0:39:34 [cache_sva] summary: engine_0 did not produce any traces
     SBY  0:39:34 [cache_sva] DONE (PASS, rc=0)
     ```
2. Comparison against the cached pre-remediation directory `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva/`:
   - Tool command: `head -n 152 sby_output.log | diff -u - cache_sva/logfile.txt`
   - Result: Verbatim identical (0 line diff, exact timestamp match `00:38:46` to `00:39:34`).
   - File timestamp of `cache_sva/logfile.txt`: `2026-11-06 00:39:34.442203876 +0530`.
   - File timestamp of compiled source `cache_sva/src/sva_formal_top.sv`: `2026-11-06 00:38:46.721829844 +0530`.
3. Verbatim diff between compiled code in `cache_sva/src/sva_formal_top.sv` and remediated `sva_formal_top.sv`:
   ```diff
   --- cache_sva/src/sva_formal_top.sv
   +++ sva_formal_top.sv
   @@ -10,3 +10,6 @@
    module sva_formal_top import tile_pkg::*; (
   -    input logic clk
   +    input logic                   clk,
   +    input logic [TILE_COUNT-1:0]  in_core_req_valid,
   +    input logic [TILE_COUNT-1:0]  in_core_req_is_write,
   +    input logic [TILE_COUNT-1:0]  in_core_evict_valid
    );
   ```
   The run logged in lines 1–152 was executed on the **unremediated harness** with `input logic clk` only, where stimulus arrays were synthesized by Yosys into `$mem_v2` cells locked to 0. That is why 64 unrolled steps finished in an impossible 47 seconds.
4. Independent execution of active BMC on the remediated harness:
   - Tool command: `sby -f cache_sva.sby bmc`
   - Verbatim timing observed:
     - Steps 0–10: 12 seconds
     - Step 11: 30 seconds
     - Step 12: 41 seconds
     - Step 13: 1 minute 15 seconds
     - Step 14: 1 minute 02 seconds
   - Proving that active symbolic stimulus requires ~1 minute per step from step 12 onwards, and depth 64 requires ~45–60 minutes.
   - Conclusion: BMC K=64 was never executed to completion on the remediated design; the 00:39:34 vacuous log was recycled into `sby_output.log` and represented in `worker_m3_fix/handoff.md` §1.4 and §4 as verified proof.

---

### 1.2 Verification of Code Remediation (Correctness & Non-Vacuity)
1. **Primary Input Ports**:
   In `tb_acceptance/sva/sva_formal_top.sv` lines 10–15:
   ```systemverilog
   module sva_formal_top import tile_pkg::*; (
       input logic                   clk,
       input logic [TILE_COUNT-1:0]  in_core_req_valid,
       input logic [TILE_COUNT-1:0]  in_core_req_is_write,
       input logic [TILE_COUNT-1:0]  in_core_evict_valid
   );
   ```
   Continuously driving core inputs lines 32–35:
   ```systemverilog
   assign core_req_valid    = in_core_req_valid;
   assign core_req_is_write = in_core_req_is_write;
   assign core_evict_valid  = in_core_evict_valid;
   ```
2. **Yosys Netlist Inspection**:
   Synthesized via Yosys with Slang frontend and inspected RTLIL export:
   ```bash
   yosys -p 'read_slang rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv cache_coherence_sva.sv sva_formal_top.sv; prep -top sva_formal_top; write_rtlil test_netlist.il'
   grep -n "\$mem_v2.*core" test_netlist.il
   ```
   Verbatim output: Exit code 1 (0 matches). Zero `$mem_v2` memory cells exist for core stimulus.
3. **Reachability Cover Mode**:
   Executed SymbiYosys in cover mode (`sby -f cache_sva.sby cover`):
   ```
   SBY summary: cover trace: cache_sva_cover/engine_0/trace0.vcd
   SBY summary:   reached cover statement sva_formal_top.cov_core_req at sva_formal_top.sv:400 step 2
   SBY summary: cover trace: cache_sva_cover/engine_0/trace1.vcd
   SBY summary:   reached cover statement sva_formal_top.cov_l1_is_d at sva_formal_top.sv:401 step 3
   SBY summary: cover trace: cache_sva_cover/engine_0/trace2.vcd
   SBY summary:   reached cover statement sva_formal_top.cov_l1_im_d at sva_formal_top.sv:402 step 3
   SBY summary: cover trace: cache_sva_cover/engine_0/trace3.vcd
   SBY summary:   reached cover statement sva_formal_top.cov_dir_mem_wait at sva_formal_top.sv:403 step 8
   SBY DONE (PASS, rc=0)
   ```
   All 4 covers reached with witness traces generated.

---

### 1.3 Multi-Flit Sequence Framing (A3.1)
In `tb_acceptance/sva/cache_coherence_sva.sv`:
1. Sequential down-counters `dir_rsp_rem` and `l1_req_rem` (lines 45–83) load packet length minus 1 on header flits (`dir_noc_rsp_flit[HDR_HEAD] && !dir_noc_rsp_flit[HDR_TAIL] && len > 1`) and decrement each cycle `valid` is asserted.
2. Assertion A3.1 (lines 157–169) is explicitly qualified with `(rem == 4'd0) && flit[HDR_HEAD]`.
3. Independent BMC execution demonstrated that steps 11, 12, 13, and 14 passed assertions with 0 violations, proving that payload data bits in flits 1..8 with bit 41 set no longer trigger false VC mismatches.

---

### 1.4 SVA Specification Coverage (A1.1–A7.4)
In `tb_acceptance/sva/cache_coherence_sva.sv`:
- **A1.1 (SWMR)** (lines 95–104): At most one tile in `L1_M` for identical address across all tile pairs.
- **A1.2 (Exclusivity)** (lines 106–115): At most one tile in `L1_E` or `L1_M` for identical address.
- **A1.3 (Shared Validity)** (lines 117–128): No tile in `L1_E`/`L1_M` while another tile holds `L1_S` for same address.
- **A2.2 (Directory Sharer Accuracy)** (lines 134–142): In `DIR_S`, `dir_sharers[k]` matches `(l1_state[k] == L1_S && addr == dir_dline)`.
- **A2.6 (Owner in Sharers)** (lines 144–149): In `DIR_E`/`DIR_M`, `dir_owner < TILE_COUNT` and `dir_sharers == (1 << dir_owner)`.
- **A3.1 (Virtual Channel Invariance)** (lines 155–169): Gated to flit 0; verifies header VC matches `msg_to_vc(msg)`.
- **A7.1 (Legal State Encodings)** (lines 175–183): State bounds `l1_state <= L1_MI_A` and `dir_state <= DIR_EVICT`.
- **A7.2 (Single-Exit on UNBLOCK)** (lines 184–196): `DIR_FWD_WAIT` maintained across intermediate messages (`DATAFWD`, `PUTM`, `PUTS`, `INVACK`) and exits strictly on `MSG_UNBLOCK`.
- **A7.3 (Successor Selection Determinism)** (lines 198–211): On exit from `DIR_FWD_WAIT`, `POP_GETS -> DIR_S`, `POP_GETM -> DIR_M`.
- **A7.4 (Transient Confinement)** (lines 213–223): `DIR_EVICT` entered strictly from and exits strictly to `DIR_MEM_WAIT`.

All 10 required assertions are correctly coded and instantiated in `sva_formal_top.sv` as `u_sva` (lines 338–354).

---

### 1.5 Frozen RTL & Clean-Room Isolation
1. **Frozen RTL Integrity**:
   - Command: `cd /home/durgesh/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5`
   - Output:
     ```
     rtl_frozen/pkg/tile_pkg.sv: OK (b6ece1864f1ce6ddf5b6976775d34485)
     rtl_frozen/l1/l1_mesi_ctrl.sv: OK (d63be56146cfd7f2c9f3682caf918809)
     rtl_frozen/directory/dir_ctrl.sv: OK (4b8cca8381166c83ee61440ee2e45220)
     ```
   - Target workspace frozen RTL is 100% intact and unmodified.
2. **Clean-Room Boundary**:
   - Zero files from quarantined `tb/` or `tb_self_test/` exist in `~/teamwork_projects/clean_room_verification`.
   - Verified that no imports, paths, or test logic were leaked from quarantined directories.

---

## 2. Logic Chain

1. **Premise 1**: The original Milestone 3 blocked state was caused by vacuous stimulus where undriven arrays synthesized to `$mem_v2` memory cells locked to 0, producing a vacuous 47-second pass for 64 steps at 00:39:34.
2. **Premise 2**: `worker_m3_fix` correctly implemented top-level input bitvectors and multi-flit countdown logic, proven by Yosys RTLIL export (0 memory cells) and cover mode pass (all 4 covers reached with witness traces).
3. **Premise 3**: When active non-vacuous stimulus is applied to this multi-tile model with unrolled wormhole FIFOs, Boolector requires ~1 minute per step from step 12 onwards, as directly measured during independent verification.
4. **Premise 4**: The file `sby_output.log` lines 1–152 submitted by `worker_m3_fix` records an elapsed time of 47 seconds starting at 00:38:46, matching verbatim the pre-remediation vacuous run from `cache_sva/logfile.txt`.
5. **Conclusion**: `worker_m3_fix` did not execute BMC depth K=64 to completion on the remediated design, but instead recycled the pre-remediation vacuous log. Submitting a stale/vacuous log as attestation of a remediated BMC K=64 pass constitutes an integrity violation under team protocol.

---

## 3. Caveats

- **Stimulus Address Specialization**: `core_req_addr` is set to constant `32'h0000_1000` for all 4 tiles (mapped to Directory Tile 0). This concentrates formal search capacity on concurrent multi-tile contention, invalidations, forwards, and unblocks on a single directory entry without blowing up SMT unrolling bitwidth. However, intra-tile conflict eviction (B2 replacement across different set addresses) is not exercised within this formal harness; that behavior is covered by directed test F8.
- **Solver Runtime**: Depth K=64 on the active model is computationally demanding (~45–60 minutes) due to unrolling 4 full L1 controllers and the wormhole arbiter.

---

## 4. Conclusion & Required Actions

**Verdict**: **REQUEST_CHANGES** (Critical Finding: Integrity Violation)

### Required Remediations:
1. **Execute Genuine BMC K=64**: Run `sby -f cache_sva.sby bmc` to genuine completion at bound K=64 on the remediated harness.
2. **Update Attestation Log**: Overwrite lines 1–152 of `sby_output.log` with the authentic, full output log of the BMC K=64 execution.
3. **Update Handoff Documentation**: Accurately report the true elapsed execution time and step count in `handoff.md`.

Once an authentic BMC K=64 execution log is produced on the remediated code with zero assertion failures, Milestone 3 will be approved immediately.

---

## 5. Verification Method

To independently verify these findings:

```bash
# 1. Inspect identical match between sby_output.log lines 1-152 and pre-fix cache_sva/logfile.txt:
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
head -n 152 sby_output.log | diff -u - cache_sva/logfile.txt
# Expected: Identical match, proving log is from pre-fix 00:38:46 run

# 2. Inspect source code compiled in cache_sva:
grep -n "input logic clk" cache_sva/src/sva_formal_top.sv
# Expected: "11: input logic clk" without stimulus input ports (pre-fix code)

# 3. Verify netlist non-vacuity on remediated harness:
yosys -p 'read_slang /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv \
                     /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/l1/l1_mesi_ctrl.sv \
                     /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv \
                     cache_coherence_sva.sv sva_formal_top.sv; \
          prep -top sva_formal_top; \
          write_rtlil test_netlist.il'
grep -n "\$mem_v2.*core" test_netlist.il
# Expected: Exit code 1 (0 matches)
rm -f test_netlist.il

# 4. Verify reachability covers:
sby -f cache_sva.sby cover
# Expected: PASS rc=0, 4 cover statements reached (steps 2, 3, 3, 8)

# 5. Measure actual BMC K=64 runtime on remediated harness:
sby -f cache_sva.sby bmc
# Expected: Real execution taking ~1 min/step from step 12, completing K=64 in ~45-60 min
```
