# BMC K=128 Formal Evidence — F1 Slice (Frozen RTL)

> **Document Purpose**: Formal BMC K=128 result for F1 forward-release slice on frozen RTL.  
> **Writing Standard**: ~80% ASD-STE100 — direct active verbs, exact tool output.

## Command

```
cd /mnt/Code/visualstudio/Design-arch_multi-core/tb_rtl_evidence/sby_k128 && export PATH="$HOME/.local/oss-cad-suite/bin:$PATH" && sby -f l1_dir.sby
```

## Exit Code

`SBY_EXIT=2` — **FAIL**

## Elapsed Time

- Clock: 4h 30m 44s (16244s)
- Process: 4h 29m 28s (16168s)

## SBY Summary (full tail)

```
SBY  5:43:15 [l1_dir] engine_0: ##   4:30:22  BMC failed!
SBY  5:43:15 [l1_dir] engine_0: ##   4:30:22  Assert failed in fml_l1_dir: u_sva.a2_2
SBY  5:43:15 [l1_dir] engine_0: ##   4:30:22  Writing trace to VCD file: engine_0/trace.vcd
SBY  5:43:18 [l1_dir] engine_0: ##   4:30:25  Writing trace to Verilog testbench: engine_0/trace_tb.v
SBY  5:43:18 [l1_dir] engine_0: ##   4:30:25  Writing trace to constraints file: engine_0/trace.smtc
SBY  5:43:18 [l1_dir] engine_0: ##   4:30:25  Writing trace to Yosys witness file: engine_0/trace.yw
SBY  5:43:23 [l1_dir] engine_0: ##   4:30:30  Status: failed
SBY  5:43:23 [l1_dir] engine_0: finished (returncode=1)
SBY  5:43:23 [l1_dir] engine_0: Status returned by engine: FAIL
SBY  5:43:23 [l1_dir] summary: Elapsed clock time [H:MM:SS (secs)]: 4:30:44 (16244)
SBY  5:43:23 [l1_dir] summary: Elapsed process time [H:MM:SS (secs)]: 4:29:28 (16168)
SBY  5:43:23 [l1_dir] summary: engine_0 (smtbmc boolector) returned FAIL
SBY  5:43:23 [l1_dir] summary: counterexample trace: l1_dir/engine_0/trace.vcd
SBY  5:43:23 [l1_dir] summary:   failed assertion fml_l1_dir.\u_sva.a2_2 at sva_l1_dir.sv:74.5-75.65 step 48
SBY  5:43:23 [l1_dir] DONE (FAIL, rc=2)
```

## Comparison with K=64

| Metric | K=64 | K=128 |
|---|---|---|
| Exit | FAIL (rc=2) | FAIL (rc=2) |
| Failing assertion | `a2_2` | `a2_2` |
| Step | 48 | 48 |
| Clock time | 4h 28m | 4h 31m |
| Process time | 4h 27m | 4h 29m |

**Conclusion**: Failure is **identical** at both bounds — not a bound artifact. The counterexample manifests at step 48 in both runs; the deeper bound only increases solver time.

## Assertions Proven (up to step 47)

Same as K=64 — all assertions except `a2_2` hold through step 47.

## Formal Scope Assumption (R5 / OI-8)

**`assume(!dir_oflow)`** — same as K=64. Results conditional on NIC credit management (§16.9 not implemented).

## Verdict

**BMC K=128: FAIL** — same root cause as K=64. Increasing bound to 128 does not change the outcome.

See `tb_rtl_evidence/FORMAL_FAILURES.md` for root cause analysis.