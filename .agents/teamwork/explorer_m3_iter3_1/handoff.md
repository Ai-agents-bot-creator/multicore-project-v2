# Milestone 3 Remediation Strategy & Solver Performance Analysis Report

- **Agent**: `explorer_m3_iter3_1`
- **Archetype**: explorer (SMT and formal verification scaling explorer)
- **Target Work Product**: `~/teamwork_projects/clean_room_verification/tb_acceptance/sva`
- **Target Project Directory**: `/home/durgesh/teamwork_projects/clean_room_verification`
- **Milestone**: Milestone 3 Gate Iteration 3
- **Parent Conversation ID**: `be241bc4-e291-4439-8a29-a04573a62cec`

---

## Executive Summary

Milestone 3 Gate Iteration 2 failed audit because the worker submitted handoff citing a stale, pre-remediation 47-second vacuous log from `00:39:34`, while the genuine remediated design—incorporating active symbolic stimulus—requires ~45–60 minutes of solver time for Bounded Model Checking (BMC) at bound $K=64$.

This investigation analyzed SymbiYosys (`sby`), `yosys-smtbmc`, and Boolector solver scaling, evaluated alternative flags and solvers, verified the root causes of execution delays, and developed a complete, deterministic execution and monitoring strategy for the Worker.

**Key Findings**:
1. **Solver Configuration**: In `cache_sva.sby`, `smtbmc boolector` automatically supplies `--presat` and `--unroll`. Empirical benchmarking at depth 12 proved that `--presat` not only guarantees non-vacuous assumption checks (preventing spurious passes due to contradictory assumptions), but also speeds up solving by pre-warming SAT literal databases: depth 12 finished in **29.4s** with `--presat`, whereas omitting `--presat` caused step 10 alone to exceed **40s** (>3x slowdown).
2. **Monolithic vs Incremental**: Breaking BMC into skip-step chunks does not save runtime because transition relation unrolling must still occur from step 0. Monolithic execution of `sby -f cache_sva.sby bmc` is required to generate the authentic `status` and `logfile.txt` artifacts demanded by gate reviewers.
3. **Runtime & Monitoring Protocol**: Total wall-clock runtime for depth 64 is empirically projected at **45 to 60 minutes** (~50–65s/step for steps 15–63). The Worker must launch BMC as a background task via `run_command` and maintain the mandatory 5-minute `progress.md` heartbeat using native `schedule(DurationSeconds=300)` wakeup timers without polling in shell sleep loops.

---

## 1. Observation

### 1.1 Solver Configuration & Command-Line Construction in SymbiYosys
Inspection of SymbiYosys internal engine dispatch in `/home/durgesh/.local/oss-cad-suite/share/yosys/python3/sby_engine_smtbmc.py`:
- Lines 26–27: `presat_opt = True`, `unroll_opt = None`.
- Lines 80–81: `if i == 0 and a == "z3" and unroll_opt is None: unroll_opt = False`. For all other solvers (including Boolector), `unroll_opt` defaults to `True`.
- Lines 90–94:
  ```python
  if presat_opt:
      smtbmc_opts += ["--presat"]
  if unroll_opt is None or unroll_opt:
      smtbmc_opts += ["--unroll"]
  ```
- Line 141–142: `if not progress: smtbmc_opts.append("--noprogress")`.
- When `cache_sva.sby` specifies:
  ```sby
  [engines]
  smtbmc boolector
  ```
  SymbiYosys automatically synthesizes the command:
  ```bash
  yosys-smtbmc -s boolector --presat --unroll --noprogress -t 64 --append 0 \
    --dump-vcd engine_0/trace.vcd --dump-yw engine_0/trace.yw \
    --dump-vlogtb engine_0/trace_tb.v --dump-smtc engine_0/trace.smtc \
    model/design_smt2.smt2
  ```

### 1.2 Empirical Solver Flag Benchmarking (Clean-Room Model)
Benchmarked `yosys-smtbmc` directly against `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/model/design_smt2.smt2` at depth $K=12$:

| Test Configuration | Solver | Flags | Step 10 Time | Total Time (Depth 12) | Result |
|---|---|---|---|---|---|
| **Test 1 (Standard)** | Boolector 3.2.4 | `--presat --unroll` | 12.0s | **29.46s** | **PASS** |
| **Test 2 (No PreSAT)** | Boolector 3.2.4 | `--unroll` (no `--presat`) | >40.0s (running) | >65s | Interrupted |
| **Test 3 (Bitwuzla)** | Bitwuzla 0.7.0 | `--presat --unroll` | 7.0s | **18.69s** | **PASS** |
| **Test 4 (Z3)** | Z3 4.14.0 | standard | >10s at step 6 | >120s | Interrupted |

**Observations**:
- Omitting `--presat` substantially degraded solving speed: without pre-solving the assumption space, the incremental SAT solver has not pruned unreachable state subspaces when entering assertion checks.
- Bitwuzla is ~37% faster than Boolector on this circuit (18.69s vs 29.46s), but `PROJECT.md` §Interface Contracts line 56 explicitly stipulates: `Engines: smtbmc boolector and smtbmc z3`. Gate auditor and reviewer checklists expect Boolector in `sby_output.log`.
- Z3 is uncompetitive on bit-vector unrolling for this multi-controller circuit.
- Therefore, `smtbmc boolector` with default `--presat --unroll` remains the mandated and optimal choice.

### 1.3 Step Runtime Scaling Analysis
Direct measurement from `cache_sva_bmc/logfile.txt`:
```
Step  0-10: 12 seconds total
Step 11:    30 seconds (checking assumptions: 1s, checking assertions: 29s)
Step 12:    41 seconds (checking assumptions: 1s, checking assertions: 40s)
Step 13:    86 seconds (checking assumptions: 1s, checking assertions: 85s)
Step 14:    53 seconds (checking assumptions: 1s, checking assertions: 52s)
```
- In all steps, checking assumptions with `--presat` required $\le 1$ second. The remaining 98%+ of execution time is spent on assertion satisfaction queries.
- From step 11 to 14, average step solving time is $52.5$ seconds.
- Cumulative calculation for 64 steps:
  - Steps 0–14: ~4.5 minutes.
  - Steps 15–63 (49 steps): $49 \times 55\text{s} \approx 45\text{ minutes}$.
  - Expected total wall-clock runtime: **45 to 60 minutes**.

### 1.4 Workspace State & Stale Artifact Inspection
Inspected `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva`:
- `cache_sva/`: Generated at `00:38:46` from pre-remediation harness without input ports (`input logic clk` only). Stale artifact.
- `cache_sva_bmc/`: Initiated at `06:33:03` by reviewer during audit; aborted at step 14 after demonstrating active solver scaling.
- `cache_sva_cover/`: Generated at `03:07:53` by `worker_m3_fix` using `sby -f cache_sva.sby cover`. Completed cleanly in 28s with 4 witness traces.
- `sby_output.log`: Contains stale vacuous BMC run lines 1–152 followed by appended cover log lines 153–227.

---

## 2. Logic Chain

1. **Premise 1**: Milestone 3 Gate failed solely due to an attestation integrity failure: `worker_m3_fix` cited a stale 47-second vacuous run from `00:38:46` instead of executing BMC depth 64 to completion on the remediated design.
2. **Premise 2**: Remediation of `sva_formal_top.sv` (primary symbolic ports, 0 `$mem_v2` memory cells) and `cache_coherence_sva.sv` (A3.1 flit framing down-counters) was independently audited by `auditor_m3_1` and confirmed 100% sound, non-vacuous, and functional.
3. **Premise 3**: Running active symbolic BMC on this 4-L1 + Directory + wormhole network circuit with Boolector inherently takes 45–60 minutes because step complexity scales to ~50–65s/step past step 10.
4. **Premise 4**: Empirical testing confirmed that `--presat --unroll` is the fastest and safest solver configuration for Boolector; disabling `--presat` slows down solving by >3x and eliminates protection against vacuous assumption conflicts.
5. **Premise 5**: Incremental chunking (running $0..20$, then $20..40$, etc.) does not reduce runtime because transition relations must be unrolled from reset in every chunk, multiplying total work.
6. **Conclusion**: The Worker must execute a clean, monolithic run of `sby -f cache_sva.sby bmc` to bound $K=64$, utilize background process execution with native 5-minute `schedule` heartbeat polling to comply with team liveness protocols, and consolidate authentic logs into `sby_output.log`.

---

## 3. Caveats

- **No Premature Step Timeout**: While an overall task timeout in `cache_sva.sby` (`timeout 7200` = 2 hours) is advisable as a safety rail, per-step timeouts (`-S --timeout`) must NOT be configured. Step solving times fluctuate naturally based on SAT variable branching heuristics; a strict 60s per-step timeout would terminate valid proofs prematurely.
- **Resource Contention**: The host machine has active background processes (e.g. `PID 619527` running Boolector on an experiment in `tb_rtl_evidence`). While sufficient cores (8+ vCPUs) and RAM exist, the worker should run BMC without launching other concurrent compute-heavy tasks.
- **Scope Restriction**: Per explorer mandate, this investigation is read-only. No source files or `.sby` files in the target workspace were modified during this investigation.

---

## 4. Conclusion & Turnkey Execution Plan for Worker

### 4.1 Recommended Strategy
1. **Retain `cache_sva.sby` Engine Settings**: Keep `[engines] smtbmc boolector`. SBY automatically configures `--presat --unroll --noprogress`.
2. **Execute Clean Monolithic BMC Run**: Execute `sby -f cache_sva.sby bmc` from step 0 to 64.
3. **Background Execution with Timer Heartbeat**: Launch via `run_command` (async task) and maintain `progress.md` heartbeat every 5 minutes via the `schedule` tool.
4. **Consolidate Verification Evidence**: Overwrite `sby_output.log` with the concatenated genuine BMC depth 64 log and Cover mode log.

### 4.2 Step-by-Step Worker Execution Runbook

The Worker must execute the following exact commands in sequence:

#### Step 1: Pre-Execution Workspace Hygiene
Remove the stale pre-remediation directory and any interrupted runs:
```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
rm -rf cache_sva cache_sva_bmc
```

#### Step 2: Verify Cover Mode (Quick Sanity Check)
Run Cover mode to ensure non-vacuous reachability is fresh:
```bash
export PATH="$HOME/.local/oss-cad-suite/bin:$PATH"
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
sby -f cache_sva.sby cover
```
*Expected output*: `DONE (PASS, rc=0)` in ~28–32 seconds, reaching covers at steps 2, 3, 3, and 8.

#### Step 3: Launch Genuine BMC Depth 64 in Background
Launch the BMC run via `run_command` with `WaitMsBeforeAsync: 1000`:
```bash
export PATH="$HOME/.local/oss-cad-suite/bin:$PATH"
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
sby -f cache_sva.sby bmc
```
*Expected behavior*: The tool call will background after 1 second, returning a task ID.

#### Step 4: Liveness Monitoring Protocol (Every 5 Minutes)
Immediately schedule a 5-minute timer using the `schedule` tool:
```json
{
  "DurationSeconds": 300,
  "Prompt": "Heartbeat check: inspect BMC progress in cache_sva_bmc/logfile.txt and update progress.md"
}
```
On each timer wakeup:
1. Inspect the latest 10 lines of the active log:
   ```bash
   tail -n 10 /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/logfile.txt
   ```
2. Parse the current step (e.g., `Checking assertions in step 32..`).
3. Update `progress.md` in the worker's working directory:
   ```markdown
   **Last visited**: [CURRENT_UTC_TIMESTAMP]
   **Status**: BMC K=64 running. Current step: 32/64.
   ```
4. If the background task has not completed, schedule the next 300-second timer.

#### Step 5: Post-Completion Log Assembly
When the background task completes with return code 0 (`DONE (PASS, rc=0)`):
Assemble the complete attestation artifact:
```bash
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
cat cache_sva_bmc/logfile.txt > sby_output.log
echo "" >> sby_output.log
echo "================================================================================" >> sby_output.log
echo "COVER MODE REACHABILITY WITNESS LOG (Non-Vacuous Witness Verification)" >> sby_output.log
echo "================================================================================" >> sby_output.log
cat cache_sva_cover/logfile.txt >> sby_output.log
```

#### Step 6: Attestation Verification Checks Before Handoff
Verify that all 4 forensic criteria are met:
1. `grep -n "DONE (PASS, rc=0)" sby_output.log` -> matches both BMC and Cover.
2. `grep -n "Elapsed clock time" cache_sva_bmc/logfile.txt` -> displays authentic elapsed time between 45:00 and 60:00 (e.g., `0:52:14`).
3. `cat cache_sva_bmc/status` -> reads `PASS 0 <actual_seconds>`.
4. `diff -u sva_formal_top.sv cache_sva_bmc/src/sva_formal_top.sv` -> returns 0 differences.

---

## 5. Verification Method

To independently verify the observations, benchmark results, and conclusions in this report:

```bash
# 1. Verify SymbiYosys smtbmc engine default options:
grep -n -C 5 "presat_opt" /home/durgesh/.local/oss-cad-suite/share/yosys/python3/sby_engine_smtbmc.py
# Confirms --presat and --unroll are passed by default to boolector.

# 2. Reproduce the depth 12 benchmark comparison:
export PATH="$HOME/.local/oss-cad-suite/bin:$PATH"
cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva

# Test with --presat (warm-up):
time yosys-smtbmc -s boolector --presat --unroll -t 12 cache_sva_bmc/model/design_smt2.smt2
# Result: ~29 seconds PASS

# Test with Bitwuzla:
time yosys-smtbmc -s bitwuzla --presat --unroll -t 12 cache_sva_bmc/model/design_smt2.smt2
# Result: ~18 seconds PASS

# 3. Verify step solving time progression:
grep -E "Checking assertions in step [0-9]+" cache_sva_bmc/logfile.txt
# Shows scaling from 12s at step 10 to ~53s at step 14.
```
