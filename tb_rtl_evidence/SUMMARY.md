# RTL Evidence Sweep Summary — 2026-11-06

> **Document Purpose**: Consolidated summary of overnight evidence tasks against frozen RTL (Slice 16.1).  
> **Writing Standard**: ~80% ASD-STE100 — direct active verbs, exact file references.

## Tasks Completed

| Task | Description | Status | Output |
|---|---|---|---|
| **1** | BMC K=64 on `rtl_frozen/` | **FAIL** | `tb_rtl_evidence/FORMAL_K64.md`, `FORMAL_FAILURES.md` |
| **2** | BMC K=128 on `rtl_frozen/` | **FAIL** | `tb_rtl_evidence/FORMAL_K128.md` |
| **3** | Static RTL-vs-spec audit | **COMPLETE** | `tb_rtl_evidence/AUDIT.md` |
| **4** | Lint sweep (iverilog + verilator) | **COMPLETE** | `tb_rtl_evidence/LINT.md` |
| **5** | Open items (R5, OI-8, OI-9) | **COMPLETE** | `docs/01_DECISION_LOG.md`, `docs/AI_SCRATCHPAD.md` |

## Tasks Failed / Blocked

| Task | Issue |
|---|---|
| **1, 2** | Both BMC runs failed on `a2_2` (Sharer accuracy) at step 48. Root cause: formal harness allows requester to send `UNBLOCK` while in `SM_D` (transient). RTL fix cannot resolve harness assumption gap. |

## Key Finding — Must Read First

**BMC FAILURE on `a2_2` (Sharer accuracy)**:
- **Location**: `rtl_frozen/directory/dir_ctrl.sv` lines 304–317 (DIR_FWD_WAIT → DIR_S transition)
- **Root cause**: Directory enters `DIR_S` on `UNBLOCK` from owner while requester is still in `SM_D` (transient, awaiting DATA). Sharers mask claims requester is in stable `S`, but it isn't yet.
- **Why RTL fix didn't help**: The counterexample shows the requester L1 sending `UNBLOCK` while still in `SM_D` — a protocol violation the real L1 RTL never does (it sends `UNBLOCK` only after receiving `DATA` and reaching `S`). The formal harness lacks the assumption that `UNBLOCK` implies prior `DATA` receipt.
- **Fix required**: Add formal harness assumption: `assume(UNBLOCK from req_tile → L1 state ∈ {S,E,M})`. This is a harness fix, not an RTL fix.

> **Top 3 items for RTL author tomorrow**:
> 1. **Harness fix**: Add `assume(UNBLOCK → prior DATA)` to `tb_rtl_evidence/sby_k64/fml_l1_dir.sv`
> 2. Re-run BMC K=64 after harness fix
> 3. Clean up 4 unused signals (`rx_data[511:448]`, `rx_we`, `conflict` in L1; `rx_data[511:448]` in Dir) per `LINT.md`

## Evidence Inventory

All artifacts under `tb_rtl_evidence/`:
```
tb_rtl_evidence/
├── sby_k64/
│   ├── run_final.log          # Full sby output (4h 28m)
│   └── l1_dir/engine_0/
│       ├── trace.vcd          # Counterexample waveform
│       ├── trace_tb.v         # Verilog testbench
│       ├── trace.smtc         # Constraints
│       └── trace.yw           # Yosys witness
├── sby_k128/
│   ├── run_final.log          # Full sby output (4h 31m)
│   └── l1_dir/engine_0/
│       └── trace.vcd          # Counterexample waveform
├── lint/
│   ├── iverilog_l1.log
│   ├── iverilog_dir.log
│   ├── verilator_l1.log
│   └── verilator_dir.log
├── FORMAL_K64.md
├── FORMAL_K128.md
├── FORMAL_FAILURES.md
├── AUDIT.md
├── LINT.md
└── SUMMARY.md                 # (this file)
```

## Gate Status (on frozen RTL)

| Gate | Command | Result |
|---|---|---|
| Spec | `python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py` | **131/131 PASS** (exit 0) |
| Docs | `python3 ~/.skills/hw-design-docs/scripts/check_docs.py --docs docs --wp white_papers/final/FINAL_whitepaper_v3.0.md --build-order docs/BUILD_ORDER.csv` | **47/47 PASS** (exit 0) |
| Icarus 13 | `iverilog -g2012 -Wall` | exit 0 (21 "sorry" = Icarus limitation) |
| Verilator 5.054 | `verilator --lint-only -Wall -Wno-fatal` | exit 0 (4 real UNUSEDSIGNAL, 42 UNUSEDPARAM style) |
| Coding rules | `python3 lint/check_rules.py --verilator` | **PASS** (exit 0) — historical row, pre-canonical |
| BMC K=64 | `sby -f l1_dir.sby` | **FAIL** (a2_2 step 48) |
| BMC K=128 | `sby -f l1_dir.sby` | **FAIL** (a2_2 step 48) |

## Formal Scope Limitation (R5 / OI-8)

Both BMC results are **conditional on `assume(!dir_oflow)`** — an environment assumption modeling missing NIC credit management (§16.9 not implemented). Per R5: "F1 formal results valid ONLY under this assumption. Re-run without assumption when §16.9 lands."

## New Open Item (OI-9)

**Sharer accuracy failure on FWD_WAIT→DIR_S transition** — directory enters `DIR_S` with stale sharers while requester is `SM_D`. Requires RTL fix in `dir_ctrl.sv` lines 304–310.

## v5 Gate Status (2026-11-07, post-B7 landed RTL: B6 abort + B7.1 per-VC receive path)

The frozen-RTL table above is history. Current gates on the landed tree (ruling B6 commits `a14a1ad`/`455558a`/`77cff96` + v5 Task 3.5 per-VC `dir_ctrl.sv`; v6 Task 3.7 = **no RTL change**, B8.1 holds by construction):

| Gate | Command | Result |
|---|---|---|
| Spec package | `python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py` | **134/134 PASS** (exit 0, Step 0 `apply_b78_repo.py`: B7 steps "already", B8 steps applied, J6 added) |
| Docs | `python3 ~/.skills/hw-design-docs/scripts/check_docs.py --docs docs --wp white_papers/final/FINAL_whitepaper_v3.0.md --build-order docs/BUILD_ORDER.csv` | **47/47 PASS** (exit 0) |
| Coding rules (canonical 25-rule set) | `python3 lint/check_rules.py --verilator` | **48/48 PASS** (exit 0) — 25 rules x 2 modules |
| Smoke ALU | `cd tb/smoke && make MODULE=test_smoke TOPLEVEL=tb_smoke` | **PASS** (1/1) |
| Smoke DFF | `cd tb/smoke && make` (MODULE=test_clocked) | **PASS** (1/1) |
| F1 forward | `cd tb_self_test/l1_dir && MODULE=test_f1_forward make` | positive **PASS**; both negatives FAIL with "fault not present" = the baseline row of the mutation matrix |
| F2–F8 | `cd tb_self_test/l1_dir && PYTHONPATH=$PWD/../../tb/ref_model MODULE=test_f2_f8 make` | **8/8 PASS** |
| Mutation matrix | `cd tb_self_test/l1_dir && python3 run_mutations.py` | **20/20 expected** (4 variants × 5 tests, count derived from the matrix; MUT-D = B8.1 head-insertion, caught by the `race` column and by the new `vc0_fifo` column) |
| Directed owner-evict (B5) | `cd tb_rtl_evidence/directed_owner_evict && make` | **2/2 PASS** |
| Directed upgrade race (B6) golden | `cd tb_rtl_evidence/directed_upgrade_race && make` | **B6.1 ✓ (t=8), B6.2 ✓ (abort t=10, INVACK t=11), B6.3 ✓ (tile1 t=28, tile0 t=61), B6.4 ✓ one M** — v6 rerun after Task 3.7 (RTL unchanged, md5 `0bc0d48f…`/`8e44ed1d…` match `rtl/FROZEN.md5`) |
| Directed upgrade race (B6) negative control | `make L1_MESI=l1_mesi_ctrl_defer_inv.sv SIM_BUILD=sim_build_mut` | B6.1 ✓ (fault present), B6.2 **FAIL: DEFER-INV FAULT PRESENT** — control asserts the fault is present |
| Directed VC0 FIFO order (B8.1) | `cd tb_rtl_evidence/directed_vc0_fifo && make` | **B8.1.1 ✓ (t=5: VC0 holds 2 pending same-line REQs, cnt=2 rd=1 wr=3, read from the queue pointers), B8.1.2 ✓ FIFO order (arrival [1,2] = served [1,2]), B8.1.3 ✓ line completes (DIR_S, sharers=0b111, all three L1s in L1_S)** — three tiles, the minimum that puts two pending REQs for one line on VC0 at once |
| Directed VC0 FIFO order (B8.1) negative control | MUT-D applied to `rtl/directory/dir_ctrl.sv` by `run_mutations.py` | **B8.1.2 FAIL: FIFO-ORDER VIOLATION** — arrival [1,2] but served [2,1]; the line still completes (`sharers=0b111`, all three L1s in L1_S), so the mutant is killed by the ordering property itself, not by a stall |
| BMC K=64 (v7, landed RTL) | `sby -f l1_dir.sby` in `tb_rtl_evidence/sby_k64` | **RUNNING — item OPEN** (not green). Live cells from the elaborated design: **36 `$check` = 32 asserts + 4 assumes**; depth **30/64** reached, 0 violations so far, wall clock 0:28:46 at the last logged step, no `status` file yet. The snapshot is md5-identical to `rtl/`. Run as a systemd user unit so a restart cannot kill it. Scope published as an ID list in `tb_rtl_evidence/FORMAL_SCOPE.md`; state in `tb_rtl_evidence/FORMAL_K64_STATUS.md` |

### B8.1 (re-issue ordering) — RTL status: NOT RTL-VERIFIED

The current RTL implements the accept path only (B7.2 permits accept or decline), so the B6 abort does not re-transmit and no RTL behaviour depends on the re-issue ordering rule. The rule is verified in the transaction-level reference model (Mut-08, killed) and, after R3, by the three-tile directed case. Implement the decline path to close this at RTL level; tracked as an open item.

The three-tile directed case (`tb_rtl_evidence/directed_vc0_fifo/`) exercises the *mechanism* the rule depends on — the per-VC FIFO ordering (I4) of the directory's request queue — and kills the head-insertion mutant with the ordering detector. It does **not** turn B8.1 into an RTL-verified property: the re-issue that B8.1 constrains never occurs in the RTL, because the decline path does not exist.

---

*Generated 2026-11-06 05:45 UTC; v4 gate section added 2026-11-07; v5 gate section updated 2026-11-07 (B7.1 landed, package 133/133); v6 gate section updated 2026-11-08 (B8 landed via Step 0, package 134/134, mutation matrix 16/16 with the B8.1 head-insertion control); v7 gate section updated 2026-11-10 (three-tile VC0 FIFO-order case added, mutation matrix 20/20, canonical 25-rule lint installed, BMC K=64 re-run on the landed RTL and left OPEN at the depth actually reached).*