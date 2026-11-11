# Ruling B7 — The directory's receive path is per-VC, and an aborted access has a completion rule

**Status:** enacted and applied to the spec package, 2026-11-07
**Raised by:** the RTL agent's escalation of the B6.3 stall (and confirmed independently by the verification team)
**Decided by:** specification owner (MCode)
**Relates to:** ruling B6 (the same-line INV abort); extends §12 item 12

---

## 1. What was found

With ruling B6's abort implemented (`abort_o` at t=10, INVACK at t=11), the directed upgrade-race test still
failed:

```
B6.1 ✓   the race is exercised — INV delivered to the mid-miss tile (t=8)
B6.2 ✓   the tile aborts and answers INVACK immediately (t=10, t=11)
B6.3 ✗   the system does not complete — the directory stalls in DIR_INV_WAIT
         RXQ cnt=2  head_msg=GETM        (the INVACK sits behind the GETM)
B6.4 ✗   zero tiles in M (both stalled in L1_SM_D)
```

The verification team reproduced the same deadlock in their reference model and confirmed it is a
**deadlock witness**, not a stall.

## 2. Root cause — a genuine specification gap

WP §3.5 fixes VC arbitration **inside the router** ("VC arbitration per input port: fixed priority by class —
RESP > INV > FWD > REQ"). It says **nothing about the directory controller's receive path**.

So a **single arrival-ordered directory queue is specification-conformant** — and it deadlocks:

1. The directory is in `DIR_INV_WAIT` and pops only `INVACK`/`PUTS`/`PUTM`/`UNBLOCK` (by design — one
   outstanding transaction per bank, §3.7).
2. The second tile's `GETM` is already in the directory's receive queue.
3. The `INVACK` that must complete the invalidation sits **behind** that `GETM`.
4. The `GETM` is never popped (the transient is open) → the `INVACK` is never popped → deadlock.

This is not an RTL defect in the abort logic; it is a hole in the spec that let a deadlock through.

## 3. The ruling

**B7.1 — the home tile's receive path is per-VC.** It holds **one queue per VC** and pops them by the
**same class priority as the fabric** (**RESP > INV > FWD > REQ**), so a response can never be head-of-line
blocked behind a request that arrived earlier. Per-VC ordering is what makes the `INVACK` reachable.
(Invariant I4 — per-VC FIFO ordering — now applies to the directory's receive path too.)

**B7.2 — an aborted access is completed or re-issued.** The directory may still grant the abandoned request;
the tile may either **accept that grant** as the completion of its access (installing the line and sending
UNBLOCK) or **decline it** and re-issue. Forbidden: leaving the directory's transient unexited, and the
directory recording a tile as the owner of a line that tile has declined.

The RTL's existing implementation (same-state self-edge, `abort_o`, the parked access re-driven by the
DATA-install path) is **conformant with B7.2** — the tile accepts the stale grant. The missing piece is
B7.1.

## 4. Also opened: §12 item 13

The verification team's challenge is accepted and recorded: repeated upgrade-race aborts could in principle
ping-pong (abort → re-issue → abort), and Premise F bounds *message service*, not *request-level progress*.
It is an **open item**, not a ruling — no implementation change is required now. Candidate resolutions:
a bound on consecutive aborts with an ageing rule, a queued ticket, or exponential backoff.

## 5. What changed in the package

| File | Change |
|---|---|
| `FINAL_whitepaper_v3.0.md` | §3.5 — the directory controller's receive path is per-VC; §3.3 rule 6 — the completion/decline clause; §4.6 Lemma L1 — the abort completes through the normal grant path; §12 **item 13** opened; §13 ledger row **AI** |
| `SPEC_SHEET.md` | the directory receive path is per-VC |
| `HLD_LLD_4x4_architecture.md` | the directory block's pending-request note carries the per-VC receive path |
| `WORK_BREAKDOWN_16.md` | the quoted verifier count → 133 |
| `SLICE_16_1.md` | the quoted verifier count → 133 |
| `diagrams_rendered.html` | re-rendered |

**Package gate: 133/133 PASS** (new check **J5** asserts the per-VC receive path, the completion rule,
§12 item 13 and ledger row AI are all present).

## 6. What is still open

- **The per-VC receive path is unimplemented in the RTL** (§16.16 to be added by the implementer) — it is
  what unblocks the stalled B6.3 test.
- The **reference model** must mirror B7.1 and B7.2, or it keeps reporting a deadlock the hardware no longer
  has.
- The **BMC K=64 run with assertions live** is still in progress (36 `$check` cells = 32 asserts + 4 assumes
  after the `env_unblk_installed` assumption).
- **§12 item 13** — bounded progress under repeated aborts.
- The **`rtl/` vs `rtl_frozen/` vs HEAD** divergence must still be resolved to one normative copy.
