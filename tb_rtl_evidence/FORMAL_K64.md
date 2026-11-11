# BMC K=64 Formal Evidence — F1 Slice (Frozen RTL)

> **Document Purpose**: Formal BMC K=64 result for F1 forward-release slice on frozen RTL.  
> **Writing Standard**: ~80% ASD-STE100 — direct active verbs, exact tool output.

## Command

```
cd /mnt/Code/visualstudio/Design-arch_multi-core/tb_rtl_evidence/sby_k64 && export PATH="$HOME/.local/oss-cad-suite/bin:$PATH" && sby -f l1_dir.sby
```

## Exit Code

`SBY_EXIT=2` — **FAIL**

## Elapsed Time

- Clock: 4h 28m 13s (16093s)
- Process: 4h 26m 58s (16018s)

## SBY Summary (full tail)

```
SBY  5:40:40 [l1_dir] engine_0: ##   4:27:52  BMC failed!
SBY  5:40:40 [l1_dir] engine_0: ##   4:27:52  Assert failed in fml_l1_dir: u_sva.a2_2
SBY  5:40:40 [l1_dir] engine_0: ##   4:27:52  Writing trace to VCD file: engine_0/trace.vcd
SBY  5:40:43 [l1_dir] engine_0: ##   4:27:55  Writing trace to Verilog testbench: engine_0/trace_tb.v
SBY  5:40:44 [l1_dir] engine_0: ##   4:27:55  Writing trace to constraints file: engine_0/trace.smtc
SBY  5:40:44 [l1_dir] engine_0: ##   4:27:55  Writing trace to Yosys witness file: engine_0/trace.yw
SBY  5:40:49 [l1_dir] engine_0: ##   4:28:00  Status: failed
SBY  5:40:49 [l1_dir] engine_0: finished (returncode=1)
SBY  5:40:49 [l1_dir] engine_0: Status returned by engine: FAIL
SBY  5:40:49 [l1_dir] summary: Elapsed clock time [H:MM:SS (secs)]: 4:28:13 (16093)
SBY  5:40:49 [l1_dir] summary: Elapsed process time [H:MM:SS (secs)]: 4:26:58 (16018)
SBY  5:40:49 [l1_dir] summary: engine_0 (smtbmc boolector) returned FAIL
SBY  5:40:49 [l1_dir] summary: counterexample trace: l1_dir/engine_0/trace.vcd
SBY  5:40:49 [l1_dir] summary:   failed assertion fml_l1_dir.\u_sva.a2_2 at sva_l1_dir.sv:74.5-75.65 step 48
SBY  5:40:49 [l1_dir] DONE (FAIL, rc=2)
```

## Assertions Proven (up to step 47)

The following assertions held for all steps 0–47 (64-cycle bound not reached due to failure at step 48):

| Category | Assertions | Status |
|---|---|---|
| **A1.1** | At most one L1 in M | **PASS** (steps 0–47) |
| **A1.2** | At most one L1 in E | **PASS** (steps 0–47) |
| **A1.3** | No E/M alongside S | **PASS** (steps 0–47) |
| **A1.4** | M excludes all others | **PASS** (steps 0–47) |
| **A1.5** | Shared data equality | **PARTIAL** (slice lacks per-set compare) |
| **A2.1** | DIR_I ⟺ unheld | **PASS** (steps 0–47) |
| **A2.2** | Sharer accuracy (DIR_S = S-mask) | **FAIL** at step 48 |
| **A2.3** | Owner validity (DIR_E/M) | **PASS** (steps 0–47) |
| **A2.4** | DIR_I → sharers=0 | **PASS** (steps 0–47) |
| **A2.5** | Owner qualification | **PASS** (steps 0–47) |
| **A2.6** | Owner ∈ sharers | **PASS** (steps 0–47) |
| **A2.7** | Transient well-formedness | **PASS** (steps 0–47) |
| **A3.1** | Message protocol (DATA/FWD) | **PASS** (steps 0–47) |
| **A7.x** | FSM legality (L1 & Dir) | **PASS** (steps 0–47) |

> **Note**: A4.x, A5.x, A6.x, A8.x, I1–I7 require router/NIC/tap not in this slice.

## Formal Scope Assumption (R5 / OI-8)

**`assume(!dir_oflow)`** — models NIC credit management (§16.9 not implemented). F1 formal results valid ONLY under this assumption. Re-run without assumption when §16.9 lands.

## Counterexample Artifacts

- **Trace VCD**: `tb_rtl_evidence/sby_k64/l1_dir/engine_0/trace.vcd`
- **Verilog testbench**: `tb_rtl_evidence/sby_k64/l1_dir/engine_0/trace_tb.v`
- **Constraints**: `tb_rtl_evidence/sby_k64/l1_dir/engine_0/trace.smtc`
- **Yosys witness**: `tb_rtl_evidence/sby_k64/l1_dir/engine_0/trace.yw`

## Verdict

**BMC K=64: FAIL** on assertion `a2_2` (Sharer accuracy) at step 48.

**Why the RTL fix didn't resolve it**: The counterexample shows the requester L1 sending `UNBLOCK` while still in `SM_D` (transient, awaiting DATA). The real L1 RTL (lines 203–206 in `l1_mesi_ctrl.sv`) only sends `UNBLOCK` after receiving `DATA` and transitioning to `S`. The formal harness has no assumption preventing this protocol violation. The conservative RTL fix (only adding old owner to sharers) cannot fix a harness environment issue.

**Formal scope assumption (R5 / OI-8)**: `assume(!dir_oflow)` — models NIC credit management (§16.9 not implemented). F1 formal results valid ONLY under this assumption. Re-run without assumption when §16.9 lands.

**New harness assumption needed**: `assume` that `UNBLOCK` from `req_tile` only arrives after that L1 received `DATA` (i.e., L1 state ≠ SM_D/IM_D/IS_D). This is a harness fix, not an RTL fix.

See `tb_rtl_evidence/FORMAL_FAILURES.md` for root cause analysis.