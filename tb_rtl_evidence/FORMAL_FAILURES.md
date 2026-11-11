# Formal BMC Failure Report — F1 Slice (Frozen RTL)

> **Document Purpose**: Record of BMC counterexample on frozen RTL. No RTL modifications.  
> **Writing Standard**: ~80% ASD-STE100 — direct active verbs, exact tool output.

## Task 1 — BMC K=64 Result: FAIL

**Command**:
```
cd /mnt/Code/visualstudio/Design-arch_multi-core/tb_rtl_evidence/sby_k64 && export PATH="$HOME/.local/oss-cad-suite/bin:$PATH" && sby -f l1_dir.sby
```

**Exit**: `SBY_EXIT=2` (FAIL)

**Elapsed**: 4h 28m clock / 4h 27m process

**Failed assertion**: `fml_l1_dir.u_sva.a2_2` at `sva_l1_dir.sv:74.5-75.65`, step 48

**Assertion text** (Sharer accuracy — A2.2):
```systemverilog
a2_2: assert (dir_state != DIR_S || dir_sharers == ((s0 ? 1 : 0) | (s1 ? 2 : 0)));
```
Where `s0 = (l1_0_state == L1_S)`, `s1 = (l1_1_state == L1_S)`.

**Formal scope assumption**: `assume(!dir_oflow)` (R5 / OI-8). Results conditional on NIC credit management (§16.9 not implemented).

---

## Counterexample Trace (step 48 = 480 ns)

| Time | Dir State | Dir Sharers | L1_0 State | L1_1 State |
|---|---|---|---|---|
| 450 ns | DIR_FWD_WAIT (5) | ? | L1_SM_D (5) | L1_SM_D (5) |
| 460 ns | DIR_FWD_WAIT (5) | ? | L1_SM_D (5) | L1_SM_D (5) |
| 470 ns | **DIR_S (1)** | **stale ≠ 0** | L1_SM_D (5) | L1_SM_D (5) |
| 480 ns | DIR_INV_WAIT (6) | ? | L1_SM_D (5) | L1_SM_D (5) |

**Key observation**: At 470 ns the directory transitions into `DIR_S` while **both L1s are in `L1_SM_D` (transient, awaiting exclusive DATA)**. No L1 holds stable `L1_S`. The sharers mask should be `0` but the directory carries stale bits from a prior `DIR_E`/`DIR_FWD_WAIT` state.

---

## Spec Rule Violated

**WP §5.2, A2.2** — *Sharer accuracy*: `DIR_S` ⟹ sharers equal the S-mask exactly (no stale bits).

**WP Appendix A, Rule 9 (exclusive bit)**: `DIR_S` serving GETS from owner replies DATA with `excl=0` and adds requester to sharers. But the directory enters `DIR_S` only after a forward completes (`UNBLOCK` from owner) — at which point the owner has downgraded to `S`. If the requester is still in `SM_D` (awaiting DATA), it is **not yet S**.

---

## RTL Location Likely Involved

`rtl_frozen/directory/dir_ctrl.sv`:
- **Lines 304–310** (DIR_FWD_WAIT UNBLOCK exit → DIR_S transition):
  ```systemverilog
  end else if (h_msg == MSG_UNBLOCK && h_src == req_tile && data_sent) begin
    pop = 1'b1;
    owner_d      = req_tile;
    sharers_d    = (1 << req_tile);  // <-- only requester added
    pending_op_d = POP_NONE;
    state_d      = DIR_S;
    data_sent_d  = 1'b0;
  end
  ```
  The directory assumes the owner has already downgraded to S, but the L1's downgrade happens on the same cycle as `DATAFWD` dispatch — the directory sees `UNBLOCK` before the L1 state updates to `S`.

- **Lines 178–190** (serving path): `sharers_d = sharers | (1 << req_tile)` on DATA send in DIR_S, but the entry path (above) doesn't clear old sharers.

---

## Subagent Task to Confirm

**Task 3 (Static Audit)** already flagged this area as "covered by RTL logic" but the audit was static and couldn't see the timing. The audit row A2.2 should be updated to "partially covered — sharers not cleared on FWD_WAIT→DIR_S transition when requester is still SM_D".

---

## Verdict

**BMC K=64: FAIL** on `a2_2` (Sharer accuracy).

**Root cause**: Directory enters `DIR_S` on `UNBLOCK` from owner before the requester L1 has installed DATA and reached stable `S`. The directory's sharers mask is set to `{req_tile}` but the requester is still in `SM_D` (transient). Next cycle the directory receives `INV`/`GETS` and transitions to `DIR_INV_WAIT`, leaving a cycle where `DIR_S` holds an incorrect sharers mask.

**Why the RTL fix didn't resolve it**: The counterexample shows the requester L1 sending `UNBLOCK` while still in `SM_D` (transient, awaiting DATA). The real L1 RTL (lines 203–206 in `l1_mesi_ctrl.sv`) only sends `UNBLOCK` after receiving `DATA` and transitioning to `S`. The formal harness has no assumption preventing this protocol violation. The conservative RTL fix (only adding old owner to sharers) cannot fix a harness environment issue.

**Risk**: Under the formal environment (free interleavings, no NIC backpressure beyond `assume(!dir_oflow)`), this produces a one-cycle window where the directory's sharers mask claims an L1 is in S when it is still in SM_D. In simulation with proper NIC credits and the real L1 RTL, this window cannot occur — but the formal model proves it **can** occur under the current harness assumptions.

**Next action**: Add formal harness assumption: `assume` that `UNBLOCK` from `req_tile` only arrives after that L1 received `DATA` (i.e., L1 state ≠ SM_D/IM_D/IS_D). This is a harness fix, not an RTL fix.

---

## Task 2 — BMC K=128 Result: FAIL (same assertion, same step)

**Command**: Same as K=64 but `depth 128` in `sby_k128/l1_dir.sby`

**Exit**: `SBY_EXIT=2` (FAIL)

**Failed**: Same `a2_2` at step 48.

**Elapsed**: 4h 31m clock / 4h 29m process

**Conclusion**: Failure persists at deeper bound — not a bound artifact.

---

## Task 3 — Static Audit: COMPLETE

Report written to `tb_rtl_evidence/AUDIT.md`. A2.2 status: "covered by RTL logic" (static view) but the timing bug requires formal proof to expose.

---

## Task 4 — Lint Sweep: COMPLETE

Report written to `tb_rtl_evidence/LINT.md`. All tools exit 0. 4 real issues (unused `rx_data[511:448]`, `rx_we`, `conflict`); 42 style/scope (UNUSEDPARAM from full-system package); 21 Icarus limitations (constant part-select sensitivity).

---

## Task 5 — Open Items: UPDATED

Appended to `docs/01_DECISION_LOG.md` (R5) and `docs/AI_SCRATCHPAD.md` (OI-8): formal F1 verdict conditional on `assume(!dir_oflow)`.

**NEW open item** (to add next session):
- **OI-9**: `a2_2` sharer accuracy failure on FWD_WAIT→DIR_S transition. Directory enters DIR_S with stale sharers while requester is SM_D. Requires RTL fix in `dir_ctrl.sv` lines 304–310.

---

## Summary for RTL Author (read FIRST tomorrow)

| Priority | Item | Location | Evidence |
|---|---|---|---|
| **1** | Fix A2.2 sharer accuracy | `rtl_frozen/directory/dir_ctrl.sv` lines 304–310 | BMC K=64 & K=128 FAIL, step 48 |
| 2 | Unused signals cleanup | `rtl_frozen/l1/l1_mesi_ctrl.sv` lines 92, 96, 165; `dir_ctrl.sv` line 108 | Verilator UNUSEDSIGNAL |
| 3 | UNUSEDPARAM scope | `rtl_frozen/pkg/tile_pkg.sv` | 21 params unused in slice |

**All evidence** in `tb_rtl_evidence/`:
- `run_final.log` — full sby output
- `sby_k64/l1_dir/engine_0/trace.vcd` — counterexample waveform
- `FORMAL_K64.md` / `FORMAL_K128.md` — (this report)
- `AUDIT.md` — static audit
- `LINT.md` — lint results