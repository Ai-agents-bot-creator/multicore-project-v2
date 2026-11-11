# Rulings B1, B2, B4 — protocol decisions for the RTL phase

**Status:** decided. These close the last three protocol gaps that block RTL/TB work.
**Authority:** supervisor ruling, to be recorded in the WP §13 adjudication ledger.
**Scope:** normative text only. Every patch below is verbatim; apply as-is.

The 42-assertion set is **unchanged** by all three rulings. No new numbered assertion is
required — the new obligations are covered by A7.x (FSM legality), A2.7 (transient
well-formedness) and the existing §3.5 / §3.3 normative text.

---

## B1 — Fairness bound composition → **13 = 5 + 3 + 5 (derived, not asserted)**

### Decision

1. **A round is one router clock cycle.** Every input port's VC arbiter and every output
   port's switch arbiter arbitrate once per cycle; all counters and pointers advance once
   per round.
2. **The age-escape threshold is 5 rounds** (was: a "working value" of 8, proposed and
   explicitly not confirmed by §12 item 8).
3. **The bound is derived:** 5 (age escape) + 3 (the other VCs at the same input port —
   4 VCs per port) + 5 (input ports at the output switch — the router's LOCAL, N, S, E, W).
4. **The output switch arbiter is port-granular.** Round-robin across *input ports*, never
   across input-port × VC pairs. This is a normative obligation on the RTL, because the
   wormhole model reserves *the* output path (one header flit holds it), and because a
   VC-aware output arbiter (20 candidates) would make the second term 20 and void the bound.
5. **The oldest counter wins the escape**, ties broken by the fixed class priority. Without
   this tie-break the "+3" term is lost and the bound is wrong.

### Why 5, and why this is not a preference

The WP already contains the answer in its own numbers, and they are currently inconsistent:

- §3.5 states the corner-tile bound as **11**.
- With a threshold of 8: 8 + 3 (sibling VCs) + 3 (active ports at a corner) = **14** ≠ 11.
- With a threshold of 5: 5 + 3 + 3 = **11** ✓ — exactly the figure the WP already prints.

The spec's stated corner bound of 11 is only derivable with a 5-round threshold. The WP's
"8 + 5 = 13" decomposition was missing the sibling-VC term, and its two published figures
(13 at an interior tile, 11 at a corner) could not both be true. **5 is the value that
reconciles them**, which also closes §12 item 8 (explicitly reserved for this decision).

Note the liveness argument is unaffected: Premise F only requires *some* finite bound, and
13 < T = 64 either way. What changes is that the bound is now derivable from the structure
instead of asserted, so the k-induction premises in §5.3 have something to stand on.

### Patches

**P-B1.1** — §3.5, arbitration item 2 (replace the whole paragraph):

> 2. **Starvation escape (Premise F):** fixed priority alone is not fair to the most heavily loaded class (every L1 miss injects REQ). Therefore an arbiter **age counter** overrides the fixed order: a VC that has waited ≥ **5** arbitration rounds is granted next. The age counter is per (input port, VC) and increments once per round while that VC has a flit at the head of its VC FIFO and is not granted; when several VCs qualify, the **oldest counter is granted first**, ties broken by the fixed class priority. **One round is one clock cycle of the router** — every input port's VC arbiter and every output port's switch arbiter arbitrate once per cycle, and all counters and pointers advance once per round. The end-to-end bound is therefore **derived, not asserted**: 5 rounds for the age escape, plus at most 3 further rounds for the other VCs at the same input port (4 VCs per port, §3.5), plus at most 5 further rounds for the output switch arbiter, which is **round-robin across input ports** — the router's ports are LOCAL, N, S, E, W, so at most 5 contenders — giving **5 + 3 + 5 = 13 switch-arbitration rounds**. At a corner tile only 3 ports are active, so the bound there is **5 + 3 + 3 = 11**. Two obligations follow and are normative: **(a)** the output switch arbiter must be *port-granular*; a VC-aware output arbiter (round-robin over input-port × VC pairs, 20 candidates) would make the second term 20 and void the bound — and would contradict the wormhole model, in which the header flit reserves *the* output path; **(b)** the age counter must be per (input port, VC) and the oldest-first tie-break must be implemented, or the "+3" term is lost. 13 rounds ≈ 13 cycles < T = 64 ✓. The value 5 is confirmed by this ruling (§12 item 8); it is to be retuned against measured VC load at Week 10 — a retuned threshold requires re-deriving the bound (T + 3 + 5), and does not affect the deadlock proof, which is parametric in the bound.

**P-B1.2** — §5.3, Premise F (replace):

> **Premise F (fairness).** Every VC with pending traffic is served within at most **13** arbitration rounds (§3.5: a round is one router clock cycle; the bound is derived as 5 rounds of age escape at the input port, plus at most 3 further rounds for the other VCs at the same input port, plus at most 5 further rounds of output-port round-robin across the router's ≤5 input ports; the output switch arbiter is port-granular, not VC-aware), and the fabric delivers transmitted flits. Liveness is claimed *under* this premise; without it, strict priority would permit REQ starvation and the liveness properties of §5.3 would be false.

**P-B1.3** — §12 item 8 (replace the row):

> | 8 | Age-counter threshold for the fairness escape | **Confirmed: 5 rounds** (ruling B1) — the only value consistent with the WP's own corner-tile bound of 11 (5 + 3 + 3); retune against measured VC load at Week 10, and re-derive the bound if it changes | Week 10 (retune only) |

**P-B1.4** — no change is needed to the "Bounded service" row (still 13 arbitration rounds,
Premise F) or to §5.1's directed tests.

### RTL consequences

- Age counter: 3 bits per (input port, VC), terminal value 5. Terminal count 4 is enough
  (0–5); 3 bits is comfortable.
- The input-port VC arbiter must compare counters and pick the maximum (oldest), not just
  test "counter ≥ threshold" and apply the fixed class priority. That comparison is a
  4-input priority network over 3-bit values — small, and it is what buys the "+3" term.
- The output switch arbiter must be port-granular. **This is the single most likely
  accidental violation**, because VC-aware output scheduling is a common design choice.

---

## B2 — Dirty eviction concurrent with an outstanding miss → **conflict eviction is not deferred**

### Decision

Rule 10 is split into two cases:

1. **Proactive eviction** — a release the tile initiates on its own initiative (a directory
   recall; giving up a line it no longer needs). **Deferred** until the miss completes.
   Rule 10 as written stands.
2. **Conflict eviction** — the victim the pending miss itself requires, because the
   incoming line's set is full. **Not deferred.** The L1 releases the PLRU victim
   **before** it issues the miss request:
   - dirty victim (M) → `PUTM` (VC0, 9 flits), wait for `PUTACK`;
   - clean victim (S or E) → `PUTS` (VC0, 1 flit, no data); the E case waits for `PUTACK`,
     the S case does not (rule 9).
3. The victim's release is a **sub-step of the miss transient**: the L1 stays in
   `IS_D`/`IM_D`, no second transient is opened, and `MI_A`/`EI_A` are entered only for
   proactive evictions. **One transient per tile holds; no MSHRs.**
4. The release and the subsequent `GETS`/`GETM` both ride **VC0 (REQ)**, so the per-VC FIFO
   ordering of I4 preserves their order **at the source**. The home bank therefore processes
   the release first, and the L1 never waits on a directory transaction that is blocked
   behind its own miss.

### Why

Under a literal "defer every eviction while a miss is outstanding", a set-full conflict
miss deadlocks: the miss needs a way, the way needs a PUTACK, the PUTACK needs the home
bank, and the home bank is busy with the miss the L1 is waiting to complete. The
evict-then-fetch order removes the cycle without a second transient, because the miss
request is not in flight while the release is outstanding.

Ordering by VC0 is what makes this safe without a directory-side concurrency mechanism:
the NIC's per-VC FIFO delivers the `PUTM` before the `GETS` to the same home bank, so the
directory never sees the two transactions out of order, and the one-transaction-per-bank
DTR is sufficient.

The N12 machinery already covers the overlap: if a `FWD` for the victim is in flight while
the L1 is releasing it, the L1 answers `INVACK` (its release already carries the data
obligation, exactly as in `MI_A`/`EI_A`) and the directory's `DIR_FWD_WAIT` absorbs both the
`INVACK` and the `PUTM`.

### Patches

**P-B2.1** — §3.3, behavioural rule 10 (replace):

> 10. **No eviction is started while a miss is outstanding — except the eviction the miss itself requires.** An L1 with an outstanding miss does not begin a **proactive** eviction (a release the tile initiates on its own initiative: a directory recall, or giving up a line it no longer needs); such an eviction is deferred until the miss completes. The **conflict eviction** intrinsic to the pending miss is **not** deferred: if the incoming line's set is full, the L1 releases the PLRU victim **before** it issues the miss request — dirty victim (M) → `PUTM` (VC0, 9 flits) and wait for `PUTACK`; clean victim (S or E) → `PUTS` (VC0, 1 flit, no data); the E case waits for `PUTACK`, the S case does not (rule 9). The victim's release is a **sub-step of the miss transient** — the L1 remains in `IS_D`/`IM_D` and no second transient is opened, so `MI_A`/`EI_A` are entered only for proactive evictions and the one-transient-per-tile model holds without MSHRs. The release and the subsequent `GETS`/`GETM` both travel on **VC0 (REQ)**, so the per-VC FIFO ordering of I4 preserves their order at the source and the home bank processes the release first — the L1 therefore never waits on a directory transaction that is blocked behind its own miss, and the sequence is deadlock-free. MSHRs are future scope (§9).

**P-B2.2** — Appendix A, insert after the row `| I | Store miss | IM_D | Send GETM (VC0) |`:

> | I | Load miss, victim in M (conflict) | IS_D | Release the victim first: send `PUTM` (VC0, 9 flits) with the dirty line; the `GETS` is **not** sent until `PUTACK` (rule 10) |
> | I | Store miss, victim in M (conflict) | IM_D | Release the victim first: send `PUTM` (VC0, 9 flits) with the dirty line; the `GETM` is **not** sent until `PUTACK` (rule 10) |
> | I | Load or store miss, victim in S or E (conflict) | IS_D / IM_D | Release the victim first: send `PUTS` (VC0, 1 flit, no data); the E case waits for `PUTACK`, the S case does not (rules 9, 10) |
> | IS_D | Victim released (`PUTACK`, or immediately for an S victim) | IS_D | Issue the `GETS` (VC0) — the miss request follows the release on VC0 |
> | IM_D | Victim released (`PUTACK`, or immediately for an S victim) | IM_D | Issue the `GETM` (VC0) |
> | IS_D / IM_D | FWD_GETS/FWD_GETM received (VC1) | unchanged | Send `INVACK` (VC2) — the victim's release has already been sent and carries the data obligation, exactly as in `MI_A`/`EI_A` (N12) |

The two rows written `IS_D / IM_D` are shorthand for one row per state (A7 checks each
(state, event) pair), and the `I`-state rows are likewise one row each for the load and
store variants.

**P-B2.3** — `SLICE_16_1.md` §4 (reference-model shadow), add after rule 10:

> 11. On the L1's victim release (`PUTM` for an M victim, `PUTS` for an S/E victim): the victim's L1 state → I (for an M victim, after `PUTACK`); the home bank's dirty bit is set on `PUTM`; the victim's sharer bit is cleared by the directory when the release is processed (the `DIR_E + PUTM` row); the requester's miss request is issued only afterwards.

**P-B2.4** — `WORK_BREAKDOWN_16.md` §16.1 row: the L1-side scope grows by the
victim-release path; effort 3–4 days → **4–5 days**; and the assertion-coverage table gains
one line: the conflict-eviction ordering (the release is enqueued on VC0 before the miss
request) is covered by **A7.x** (FSM legality — the event order within the transient is
defined), not by a new numbered assertion.

---

## B4 — DMA directory path → **the 2×2 build has no DMA tile**

### Decision

**The committed 2×2 FPGA build contains no DMA tile, no DMA home code and no DMA sharer
arithmetic.** The DMA track is a **4×4 simulation-only** study, evaluated against the
Week-8 gate; it never enters the 2×2 build.

### Why

- The committed 2×2 mesh has exactly **4 tile positions**, and §6.1 already budgets all
  four as CPU tiles ("2×2, 4 CPU tiles | 28 | 80" BRAM36). Adding a DMA tile to a 2×2
  mesh would make it a 5-tile irregular mesh — a change to the committed topology, the
  address map and the BRAM/LUT budget, for a device the baseline does not need.
- §3.11 defines the DMA tile as **the 16th tile of a 4×4 mesh** (15 CPU tiles + 1 DMA
  tile; the 16-bit sharer vector is exactly saturated at 15 CPU L1s + 1 DMA L1-lite; one
  home code is reserved). There is no 2×2 construction to reuse.
- The gate itself cannot have passed: its criterion (§1 and §7.1) is *"DMA channel FSM,
  register map, and one end-to-end transfer pass simulation by end of Week 8"* — the DMA
  path is a **deliverable** of the gate, not a precondition of it.
- The fallback already exists and needs no change: if the gate fails, DMA moves to §9,
  codes 1100–1101 revert to Reserved and are not reassigned, and there is **no RTL change**
  to the baseline.

### RTL consequences

- The DTR's `pending_op` encoding keeps code `100` (DMA) reserved but **unreachable** in
  the 2×2 build. The DMA_WRITE handler is a gated stub; enabling the DMA gate in a 2×2
  build must raise a **configuration error** (an assertion), not misbehave silently.
- The 2×2 build treats message codes 1100–1101 as Reserved ✓ (consistent with A8.4, which
  rejects the reserved DMA home code).
- §16's DMA rows (the DMA L1-lite FSM, §12 item 10) remain **conditional on the gate** and
  run in the 4×4 track only.

### Patches

**P-B4.1** — §3.11, append to the "Status" paragraph:

> **Scope: 4×4 only (ruling B4).** The DMA tile is the 16th tile of a 4×4 mesh; the committed 2×2 FPGA build has no DMA tile, no DMA home code and no DMA sharer arithmetic, and the DTR's `pending_op = DMA` code (100) is unreachable in the 2×2 build. The DMA track is evaluated against the Week-8 gate on the 4×4 configuration only.

**P-B4.2** — §12 item 11 (replace the row):

> | 11 | DMA configuration — **4×4 only; withdrawn from the 2×2 build** (ruling B4) | The committed 2×2 mesh has exactly 4 tile positions and all 4 are CPU tiles (§6.1: "2×2, 4 CPU tiles"); §3.11's DMA tile is the 16th tile of a 4×4 mesh, so a DMA tile cannot join the 2×2 build without changing the committed topology and the BRAM/LUT budget. The DMA track is therefore **simulation-only on the 4×4 configuration**, evaluated against the Week-8 gate; if the gate passes, the work proceeds in the 4×4 track (home code, tile slot, sharer arithmetic); if it fails, §3.11's fallback applies (codes 1100–1101 revert to Reserved, DMA moves to §9, no RTL change). **No 2×2 DMA deliverable exists.** | 4×4 track, Week-8 gate exit |

**P-B4.3** — §13 adjudication ledger: record B4 as a ruling (one line, in the existing
ledger format).

---

## Verifier changes required by these rulings (group K)

Add after the WP is patched; each check is anchored to the text above.

| ID | Check |
|---|---|
| K1 | §3.5 states the age-escape threshold **5** and the decomposition **5 + 3 + 5 = 13** |
| K2 | §3.5 states that the output switch arbiter is **port-granular, not VC-aware** |
| K3 | Premise F (§5.3) states the **derived** decomposition, not "8 + 5" |
| K4 | §12 item 8 records the threshold as **confirmed: 5 rounds** |
| K5 | no stale "**8 + 5 = 13**" / "**≥ 8 arbitration rounds**" / "working value: 8" remains |
| K6 | rule 10 contains the **conflict-eviction carve-out** and the **VC0 ordering** clause |
| K7 | Appendix A contains the victim-release rows (`PUTM` before `GETS`/`GETM`) |
| K8 | §12 item 11 records the **4×4-only** DMA scope and that no 2×2 DMA deliverable exists |
| K9 | the assertion count is still **42** (no new A-row was added by these rulings) |
| K10 | §16.1's effort in the breakdown reads **4–5 days** |

K9 is the guard that keeps these rulings from silently inflating the assertion set: if a
future patch adds an A-row, the count bookkeeping in §4.6, Appendix E and the diagrams all
have to move with it.
