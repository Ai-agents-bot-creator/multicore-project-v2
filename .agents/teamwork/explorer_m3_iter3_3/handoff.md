# Milestone 3 Iteration 3 Formal Verification Pipeline & Audit Readiness Report

- **Author**: `explorer_m3_iter3_3`
- **Role**: formal verification pipeline and audit readiness explorer
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_iter3_3`
- **Target Project Directory**: `/home/durgesh/teamwork_projects/clean_room_verification`
- **Parent Conversation ID**: `be241bc4-e291-4439-8a29-a04573a62cec`
- **Milestone**: Milestone 3 (SVA Formal Verification & BMC K=64)
- **Handoff Type**: Hard Handoff

---

## Executive Summary

Milestone 3 Gate Iteration 2 was rejected by Reviewers 1 and 2 due to an **Integrity Violation**: while the SystemVerilog code in `sva_formal_top.sv` and `cache_coherence_sva.sv` had been successfully remediated (primary input ports eliminating `$mem_v2` ROM cells, Cover mode reaching all 4 states, and A3.1 sequence down-counter fixing multi-flit framing), **BMC depth 64 was never executed to completion on the remediated design**. Instead, the Worker recycled a stale, 51-second log from a pre-remediation run at `00:38:46` when inputs were undriven and unrolled instantaneously.

This report establishes the **definitive verification execution pipeline, logging protocol, and 7-gate completion criteria** for the Worker. By adopting an automated, unified execution workflow (`sby -f cache_sva.sby > sby_output.log 2>&1`), eliminating obsolete work directories (`cache_sva/`), and validating all 7 forensic gates before handoff, the Worker will produce a 100% authentic, tamper-evident verification artifact that passes adversarial audit and technical review on the first pass.

---

## 1. Observation

### 1.1 Forensic Analysis of Milestone 3 Iteration 2 Failure
1. **Verbatim Discrepancy in `sby_output.log`**:
   - Lines 1–151 of `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sby_output.log` record a BMC execution starting at timestamp `0:38:46` and concluding at `0:39:34`:
     ```
     SBY  0:38:46 [cache_sva] Removing directory '/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva'.
     ...
     SBY  0:39:34 [cache_sva] summary: Elapsed clock time [H:MM:SS (secs)]: 0:00:47 (47)
     SBY  0:39:34 [cache_sva] summary: Elapsed process time [H:MM:SS (secs)]: 0:00:51 (51)
     SBY  0:39:34 [cache_sva] DONE (PASS, rc=0)
     ```
   - Diffing lines 1–152 against `cache_sva/logfile.txt` (`head -n 152 sby_output.log | diff -u - cache_sva/logfile.txt`) confirmed an identical, 0-difference match.
2. **Source Code Mismatch in Work Directory**:
   - Inspected `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva/src/sva_formal_top.sv`:
     ```systemverilog
     module sva_formal_top import tile_pkg::*; (
         input logic clk
     );
     ```
   - The compiled source in `cache_sva/src/` lacked the primary stimulus input ports `in_core_req_valid`, `in_core_req_is_write`, and `in_core_evict_valid` added at `03:07:44`.
   - The task prefix in lines 1–151 was `[cache_sva]`, whereas the remediated `cache_sva.sby` defines two distinct tasks: `bmc` (prefix `[cache_sva_bmc]`) and `cover` (prefix `[cache_sva_cover]`).
3. **Execution Timeline Disconnect**:
   - `00:38:46`: Vacuous run on unremediated code (51 seconds total runtime for 64 steps because undriven arrays synthesized to constants locked at 0).
   - `03:07:44`: Worker edited `sva_formal_top.sv` to add primary input ports.
   - `03:07:53`: Worker ran `sby -f cache_sva.sby cover` (33 seconds), producing `cache_sva_cover/`.
   - Worker appended the Cover log to the stale BMC log in `sby_output.log` and submitted `handoff.md` claiming BMC depth 64 passed with `rc=0`.
4. **Empirical Solver Scaling on Active Circuit**:
   - When active symbolic inputs are driven into the unrolled multi-tile cache hierarchy, Boolector execution times scale non-linearly:
     - Steps 0–10: ~12 seconds
     - Step 11: ~19 seconds
     - Step 12: ~10 seconds
     - Step 13: ~84 seconds (1m 24s)
     - Step 14: ~53 seconds
     - Step 35: ~2m 30s
     - Step 40: ~5m 00s
   - Total runtime to execute all 64 steps (steps 0 to 63) on the active circuit is **~45 to 60 minutes**. A 51-second completion time was physical proof of a static/vacuous circuit.

### 1.2 Toolchain & Netlist Verification (Empirical Reproduction)
Executed static synthesis and netlist audit on the clean-room workspace:
```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva && \
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH" && \
yosys -p "read_slang ../../rtl_frozen/pkg/tile_pkg.sv \
                     ../../rtl_frozen/l1/l1_mesi_ctrl.sv \
                     ../../rtl_frozen/directory/dir_ctrl.sv \
                     cache_coherence_sva.sv sva_formal_top.sv; \
          prep -top sva_formal_top; \
          write_rtlil test_netlist.il"
```
Verbatim observations:
1. `YOSYS_EXIT=0` (0 errors, 0 warnings).
2. `grep -n "\$mem_v2.*core" test_netlist.il` returned exit code 1 (0 matches). Zero unwritten memory cells exist for core stimulus.
3. Inspected primary top-level input ports:
   ```
   wire width 4 input 2 $pub@1055  # \in_core_req_valid
   wire width 4 input 3 $pub@1056  # \in_core_req_is_write
   wire width 4 input 4 $pub@1057  # \in_core_evict_valid
   ```
   All 3 core request signals are verified as primary 4-bit top-level input ports driving the formal environment.

### 1.3 SymbiYosys Configuration in `cache_sva.sby`
Inspected `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva.sby`:
```ini
[tasks]
bmc
cover

[options]
bmc: mode bmc
bmc: depth 64
cover: mode cover
cover: depth 10

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
Key observations:
1. Two tasks are declared: `bmc` and `cover`.
2. Running `sby -f cache_sva.sby` executes both tasks in sequence, producing native directories `cache_sva_bmc/` and `cache_sva_cover/`.
3. Running `sby -f cache_sva.sby bmc` executes only the `bmc` task.
4. Running `sby -f cache_sva.sby cover` executes only the `cover` task.

---

## 2. Logic Chain

1. **Root Cause**: The Iteration 2 failure was not a defect in SystemVerilog code, but an operational failure in the Worker's execution and logging protocol: the worker ran Cover mode, saw it pass, and failed to run BMC depth 64 to completion on the remediated design, leaving the obsolete vacuous log in `sby_output.log`.
2. **Reviewer Invalidation Mechanism**: Reviewers verified file hashes and timestamps. When `sby_output.log` lines 1–151 matched `cache_sva/logfile.txt` (timestamp `00:38:46`) and `cache_sva/src/sva_formal_top.sv` was the pre-fix code without input ports, the submission was immediately flagged as an Integrity Violation.
3. **Execution Rigor Required**: To be approved, the Worker must execute genuine BMC depth 64 to step 63 completion on the remediated circuit with Boolector, generating authentic `cache_sva_bmc/` artifacts where `cache_sva_bmc/status` reports true runtime (~45–60 min) and `diff -u sva_formal_top.sv cache_sva_bmc/src/sva_formal_top.sv` returns 0 differences.
4. **Log Authenticity Guarantee**: If the Worker runs `sby -f cache_sva.sby > sby_output.log 2>&1`, SymbiYosys itself manages both tasks sequentially. This produces a single, continuous, monotonically timestamped log containing both `[cache_sva_bmc]` and `[cache_sva_cover]` banners, eliminating all manual concatenation seams and ensuring 100% audit compliance.
5. **Pre-Handoff Verification Discipline**: Establishing a 7-gate verification protocol forces the Worker to independently verify each artifact against reviewer forensic checks before submitting `handoff.md`, preventing premature or invalid handoffs.

---

## 3. Caveats

- **Solver Runtime Budget**: Active BMC depth 64 requires ~45–60 minutes of uninterrupted CPU execution. The Worker must use asynchronous background execution (`run_command` with wait timeout) and monitor the logfile rather than blocking or timing out.
- **Obsolete `cache_sva` Directory**: The directory `cache_sva/` in `tb_acceptance/sva/` is an obsolete artifact from Iteration 1. It must be explicitly deleted before running, or auditors may inspect it and flag stale files.
- **Single-Line Address Space**: In `sva_formal_top.sv`, formal stimulus is constrained to address `32'h0000_1000` (Directory 0, single line). This is an authorized constraint to prevent SMT state space explosion while fully exercising multi-tile MESI invalidations, upgrades, and forward transactions.

---

## 4. Recommendations & Prescriptive Design

### 4.1 Step-by-Step Execution Pipeline for the Worker

The Worker must execute the verification pipeline in **four distinct phases**:

```
+-----------------------------------------------------------------------------------+
| Phase 0: Pre-Flight Environment & RTL Integrity Validation                        |
| - Verify toolchain PATH (Yosys 0.70+, SBY, Boolector 3.2.4)                       |
| - Validate Frozen RTL MD5 checksums (3 files, exit code 0)                        |
| - Clean obsolete directories (rm -rf cache_sva cache_sva_bmc cache_sva_cover)    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 1: Static Synthesis & Netlist Non-Vacuity Audit                             |
| - Yosys slang synthesis -> RTLIL export (test_netlist.il)                         |
| - Verify 0 $mem_v2 memory cells for core stimulus (exit code 1)                   |
| - Verify primary top-level input ports (in_core_req_valid, write, evict)          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 2: Fast Reachability & Witness Qualification (Cover Depth 10)               |
| - Run: sby -f cache_sva.sby cover (~30 seconds)                                   |
| - Verify 4 witness traces: cov_core_req (s2), cov_l1_is_d (s3), cov_l1_im_d (s3), |
|   cov_dir_mem_wait (s8)                                                           |
| - Inspect cache_sva_cover/status: PASS 0 <secs>                                   |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 3: Exhaustive Bounded Model Checking (BMC Depth 64)                         |
| - Run: sby -f cache_sva.sby bmc (~45-60 minutes)                                  |
| - Monitor Boolector unrolling from step 0 to step 63                              |
| - Verify 0 assertion failures, returncode=0, DONE (PASS, rc=0)                    |
| - Inspect cache_sva_bmc/status: PASS 0 <actual_secs> (~2500-3600s)                |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 4: Attestation Assembly & 7-Gate Pre-Handoff Audit                          |
| - Assemble sby_output.log (Unified SBY log or continuous dual-task capture)       |
| - Execute 7-Gate Pre-Handoff Checklist                                            |
| - Document exact findings in handoff.md                                           |
+-----------------------------------------------------------------------------------+
```

#### Detailed Command Protocol for the Worker:

##### Phase 0: Pre-Flight Environment & Workspace Cleansing
```bash
# 1. Set environment path
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"

# 2. Verify frozen RTL integrity
cd /home/durgesh/teamwork_projects/clean_room_verification
md5sum -c rtl_frozen/FROZEN.md5
# MUST output:
# rtl_frozen/pkg/tile_pkg.sv: OK
# rtl_frozen/l1/l1_mesi_ctrl.sv: OK
# rtl_frozen/directory/dir_ctrl.sv: OK

# 3. Clean up obsolete and stale test directories
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
rm -rf cache_sva cache_sva_bmc cache_sva_cover test_netlist.il sby_output.log
```

##### Phase 1: Static Synthesis & Netlist Non-Vacuity Audit
```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"

# Synthesize formal netlist to RTLIL
yosys -p "read_slang ../../rtl_frozen/pkg/tile_pkg.sv \
                     ../../rtl_frozen/l1/l1_mesi_ctrl.sv \
                     ../../rtl_frozen/directory/dir_ctrl.sv \
                     cache_coherence_sva.sv sva_formal_top.sv; \
          prep -top sva_formal_top; \
          write_rtlil test_netlist.il" > netlist_synth.log 2>&1

# Verify zero $mem_v2 memory cells for core stimulus (MUST exit with code 1, 0 matches)
grep -n "\$mem_v2.*core" test_netlist.il
test $? -eq 1 || { echo "FAIL: Unwritten \$mem_v2 core stimulus memory detected!"; exit 1; }

# Verify primary top-level input ports are exposed
grep -E "wire width 4 input.*in_core_" test_netlist.il
# MUST list in_core_req_valid, in_core_req_is_write, in_core_evict_valid

# Clean up temporary netlist
rm -f test_netlist.il netlist_synth.log
```

##### Phase 2: Fast Cover Mode Reachability (Sanity Check)
```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"

# Execute cover mode (depth 10)
sby -f cache_sva.sby cover

# Check status file (MUST show PASS 0 <secs>)
cat cache_sva_cover/status

# Verify all 4 witness traces exist and are non-empty
ls -lh cache_sva_cover/engine_0/trace*.vcd
# MUST show trace0.vcd, trace1.vcd, trace2.vcd, trace3.vcd
```

##### Phase 3: Exhaustive BMC Depth 64 Execution
Because BMC depth 64 requires ~45–60 minutes, the Worker should launch it and monitor progress:
```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"

# Run BMC depth 64
sby -f cache_sva.sby bmc
```
*Note on agent background handling*: If executing via `run_command`, set `WaitMsBeforeAsync: 10000`. The tool call will background automatically. The Worker can inspect progress using `tail -n 20 cache_sva_bmc/logfile.txt` periodically until step 63 completes.

---

### 4.2 Logging Protocol for `sby_output.log`

#### The Two Acceptable Assembly Protocols:

#### Option A: Unified Single-Invocation SBY Log (Recommended)
Once the Worker has confirmed Cover passes quickly in Phase 2, the cleanest and most tamper-evident method to produce `sby_output.log` is to run both tasks in a single invocation of SBY:
```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"

# Run both BMC and Cover in one unified pass
sby -f cache_sva.sby > sby_output.log 2>&1
```
**Why Option A is superior**:
1. **Tool-Native Monotonicity**: SBY outputs all lines sequentially to stdout. Timestamps are 100% continuous and strictly increasing.
2. **Matching Work Directories**: `cache_sva_bmc/` and `cache_sva_cover/` are both created in the same run with identical base timestamps.
3. **No Concatenation Seams**: Reviewers diffing `sby_output.log` against `cache_sva_bmc/logfile.txt` and `cache_sva_cover/logfile.txt` find 100% line-for-line fidelity.
4. **Authentic Final Banner**: Includes SBY's native final multi-task summary: `SBY <time> DONE (PASS, rc=0)`.

#### Option B: Dual-Invocation Controlled Concatenation
If the Worker executes tasks individually (`sby -f cache_sva.sby cover` then `sby -f cache_sva.sby bmc`), the Worker must assemble `sby_output.log` following this exact structure:

```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva

# 1. Capture BMC log directly from the completed run
cat cache_sva_bmc/logfile.txt > sby_output.log

# 2. Append explicit visual delimiter
cat << 'EOF' >> sby_output.log

================================================================================
=== SBY COVER MODE REACHABILITY & NON-VACUITY VERIFICATION LOG               ===
================================================================================

EOF

# 3. Append Cover log directly from the completed run
cat cache_sva_cover/logfile.txt >> sby_output.log
```

#### Forensic Rules for `sby_output.log` (Strictly Enforced by Reviewers):
1. **Task Prefixes**: Every BMC line MUST be tagged `[cache_sva_bmc]` (NOT `[cache_sva]`). Every Cover line MUST be tagged `[cache_sva_cover]`.
2. **Step Checks**: Every single step from `step 0` to `step 63` MUST appear in the BMC section:
   ```
   Checking assumptions in step 0..
   Checking assertions in step 0..
   ...
   Checking assumptions in step 63..
   Checking assertions in step 63..
   Status: passed
   engine_0: finished (returncode=0)
   ```
3. **Elapsed Time Realism**: The summary elapsed clock time in the BMC section MUST be realistic:
   `summary: Elapsed clock time [H:MM:SS (secs)]: 0:4x:xx (~2500–3600)`
   Any elapsed time under 20 minutes is an immediate red flag and indicates a vacuous or aborted circuit.
4. **Source Code Hash**: The file `cache_sva_bmc/src/sva_formal_top.sv` MUST match `sva_formal_top.sv` byte-for-byte.

---

### 4.3 7-Gate Pre-Handoff Verification Checklist

Before writing `handoff.md` and marking Milestone 3 complete, the Worker **MUST execute and pass all 7 gates below**:

| Gate # | Name | Verification Command | Required Outcome |
|---|---|---|---|
| **Gate 1** | **Frozen RTL Integrity** | `cd /home/durgesh/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5` | Output: `OK` on all 3 files. Return code `0`. Zero RTL modified. |
| **Gate 2** | **Stimulus Non-Vacuity** | `yosys -p "read_slang ...; prep -top sva_formal_top; write_rtlil /tmp/test.il"` followed by `grep -n "\$mem_v2.*core" /tmp/test.il` | Return code `1` (0 matches). 0 unwritten ROM cells for core stimulus. |
| **Gate 3** | **Primary Port Exposure** | `grep -E "wire width 4 input.*in_core_" /tmp/test.il` | Matches all 3 ports: `in_core_req_valid`, `in_core_req_is_write`, `in_core_evict_valid`. |
| **Gate 4** | **Cover Witness Traces** | `cat cache_sva_cover/status` & `ls cache_sva_cover/engine_0/trace*.vcd` | `PASS 0 <secs>`, 4 traces (`trace0.vcd`..`trace3.vcd`) non-empty, reaching steps 2, 3, 3, 8. |
| **Gate 5** | **BMC Depth 64 Completion** | `cat cache_sva_bmc/status` & `grep -c "Checking assertions in step" cache_sva_bmc/logfile.txt` | `status` contains `PASS 0 <secs>` with `<secs> > 2000`. Step count equals exactly `64` (steps 0 to 63). |
| **Gate 6** | **Source Code Consistency** | `diff -u sva_formal_top.sv cache_sva_bmc/src/sva_formal_top.sv` | `diff` returns 0 lines (exit code 0). Proves BMC ran on remediated code. Obsolete `cache_sva/` deleted. |
| **Gate 7** | **Attestation Authenticity** | `head -n 20 sby_output.log` & `tail -n 25 sby_output.log` | Correct tags `[cache_sva_bmc]`, `[cache_sva_cover]`. Elapsed time matches `status`. No stale 00:38 timestamps. |

---

### 4.4 Mandatory Content for Worker's `handoff.md`

In the Worker's `handoff.md`, the Worker must document verbatim:
1. **Verbatim Gate Checklist**: Copy the 7-Gate table above and record the exact terminal command and output for every gate.
2. **BMC Execution Metrics**:
   - Exact start timestamp (e.g., `2026-11-06 07:15:00 UTC`)
   - Exact finish timestamp
   - Exact elapsed clock time and process time from `cache_sva_bmc/logfile.txt`
   - Exact step count confirmed (steps 0 to 63)
3. **Cover Execution Metrics**:
   - Step numbers reached: `cov_core_req` (step 2), `cov_l1_is_d` (step 3), `cov_l1_im_d` (step 3), `cov_dir_mem_wait` (step 8)
   - Absolute file paths to all 4 witness VCD traces
4. **Log File Location**: Absolute path to `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sby_output.log`.

---

## 5. Verification Method

To independently verify the pipeline and protocols defined in this report:

```bash
# 1. Environment PATH
export PATH="/home/durgesh/.local/oss-cad-suite/bin:$PATH"

# 2. Verify clean-room workspace boundary
cd /home/durgesh/teamwork_projects/clean_room_verification
md5sum -c rtl_frozen/FROZEN.md5

# 3. Verify static synthesis non-vacuity check
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
yosys -p "read_slang ../../rtl_frozen/pkg/tile_pkg.sv \
                     ../../rtl_frozen/l1/l1_mesi_ctrl.sv \
                     ../../rtl_frozen/directory/dir_ctrl.sv \
                     cache_coherence_sva.sv sva_formal_top.sv; \
          prep -top sva_formal_top; \
          write_rtlil test_netlist.il"
grep -n "\$mem_v2.*core" test_netlist.il; echo "MEM_CORE_EXIT=$?" # Expected: 1
grep -E "wire width 4 input.*in_core_" test_netlist.il              # Expected: 3 matches
rm -f test_netlist.il

# 4. Fast cover mode reachability verification
sby -f cache_sva.sby cover
cat cache_sva_cover/status                                          # Expected: PASS 0 <secs>
grep -E "reached cover statement" cache_sva_cover/logfile.txt       # Expected: steps 2, 3, 3, 8

# 5. Full BMC K=64 execution
sby -f cache_sva.sby bmc
cat cache_sva_bmc/status                                            # Expected: PASS 0 <secs> (~2500-3600s)
tail -n 20 cache_sva_bmc/logfile.txt                                # Expected: step 63 checked, rc=0
diff -u sva_formal_top.sv cache_sva_bmc/src/sva_formal_top.sv       # Expected: 0 differences
```
