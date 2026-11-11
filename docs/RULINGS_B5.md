# Ruling B5 — Sharer accuracy under a concurrent owner eviction

**Status:** **spec change enacted and applied**; **B5 is NOT closed** — see §6
**Raised by:** the verification (TB) agent and the RTL agent, independently, from the same BMC counterexample
**Decided by:** specification owner (MCode)
**Amended:** 2026-11-06, second pass, after independent review

> ### Verification status in this repository (2026-11-06, independent check)
>
> The §4 package changes described below are **not yet applied in this checkout**. This file
> records the ruling as issued; it does not assert that the patches have landed.
>
> | Claim in §4 | Result of the check |
> |---|---|
> | §4.6 A2.2 row split into A2.2a / A2.2b | **not present** — `grep -rn 'A2\.2a\|A2\.2b' white_papers/final/` → 0 matches |
> | old A2.2 wording removed | **still present** — `white_papers/final/FINAL_whitepaper_v3.0.md:631` still reads `DIR_S ⟹ sharers equal the S-mask exactly (no stale bits)` |
> | §12 gains item 12 ("Lemma L1 versus a mid-miss tile") | **not present** — §12 (*Open Items Still Requiring Decision*, line 1124) ends at item 11 (line 1138); `grep mid-miss` → 0 matches |
> | §13 ledger gains row **AG** | **not present** — `grep 'AG \|'` → 0 matches |
> | package gate extended to **131/131** with new check **J3** | **not present** — `python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py` exits 0 and reports **130**; J1 and J2 both print `verifier runs 130`; there is no J3 |
> | docs suite gate unaffected | **47 PASS / 0 FAIL** — `python3 ~/.skills/hw-design-docs/scripts/check_docs.py --docs docs --wp white_papers/final/FINAL_whitepaper_v3.0.md --build-order docs/BUILD_ORDER.csv`, exit 0, before adding this file |
>
> Every file named in §4 exists (`SPEC_SHEET.md`, `HLD_LLD_4x4_architecture.md`,
> `HLD_LLD_2x2_FPGA.md`, `SLICE_16_1.md`, `diagrams_rendered.html`) but is unpatched.
>
> Open consequence: the ruling's §4 table and its "131/131" figure describe a target state.
> Until those patches are applied, the WP and this ruling disagree about A2.2.
>
> **Superseded 2026-11-06, post-landing:** the patches have landed — `verify_landing.py` PASS and the
> package gate reports **131/131** with **J3** present. The rows above are kept as issued: they record the
> pre-landing check, not the current state.

---

## 1. The case

During a peer-to-peer forward (`DIR_FWD_WAIT`, `pending_op = GETS`) the owner downgrades `E/M → S` and replies
`DATAFWD`. If the owner **evicts concurrently**, it drops `S → I` and sends `PUTS` on **VC0**; the requester, having
received the data, sends `UNBLOCK` on **VC2**. No FIFO order relates VC0 to VC2, so the two messages race.

| Case | Ordering | Directory's sharer vector | Verdict before this ruling |
|---|---|---|---|
| A | `PUTS` before `UNBLOCK` | `{requester}` | correct |
| B | same cycle | `{requester}` | correct |
| C | `UNBLOCK` before `PUTS` | `{requester, owner}` for 2 cycles, then self-corrects | **A2.2 fired** |

The RTL is not broken: it absorbs the `PUTS`, clears the bit, self-corrects, and data integrity is unaffected.
No tile ever holds two copies writable; no stale data is read. What was violated was the **wording** of A2.2.

## 2. Why the previous wording was wrong

WP §4.6 read: `DIR_S ⟹ sharers equal the S-mask exactly (no stale bits)`.

That assumes **instantaneous message delivery**. In a packet-switched network the release notification takes
cycles to reach the home tile, so the directory's vector necessarily *lags* the actual holders by one message
latency whenever a release is in flight. The property was therefore **unachievable per cycle**.

## 3. The ruling

Both agents recommended "Option A — relax A2.2". The direction is right; the phrasing offered ("the sharer
bit is an upper bound") is **too weak** and is not adopted: an upper bound permits a **missing** bit, and a
missing bit is the direction that lets two writers hold one line. The correct restatement is **one-sided**.

- **B5.1 — A2.2 becomes two clauses under one assertion ID.** The §4.6 count stays **42**; nothing renumbers.

  - **A2.2a — no missing bits (strict).** `DIR_S ⟹` every tile holding the line in S has its sharer bit set.
    This direction is never relaxed; it is what prevents two writers on one line.
  - **A2.2b — bounded extra bits.** A sharer bit may remain set for a tile that has released the line **only
    while that tile's release notification (`PUTS`/`PUTM`) is in flight toward the home tile**, and it must clear
    within the bounded window *T* = 64 cycles (§5.3).

- **B5.2 — the directory's sharer vector is a conservative superset of the actual holders, never a subset.**

- **B5.3 — the committed sharer set excludes an already-released tile.** On the `DIR_FWD_WAIT → DIR_S` exit the
  committed set is `{requester} ∪ {owner}` **minus** any tile that has already released the line.

- **B5.4 — no RTL change is required *for the Case-C bookkeeping lag*.** (Weakened in this amendment — see §6.)

**Rejected:** routing `PUTS` on VC1 (breaks invariant I2) and adding `PUTACK` to S-state evictions (an extra
round trip on every clean eviction, with deadlock risk). Both are recorded in the §13 ledger.

## 4. What changed in the package

| File | Change |
|---|---|
| `FINAL_whitepaper_v3.0.md` | §4.6 A2.2 row → two clauses **+ the vacuity note**; Appendix B "Forward, clean owner" row → committed sharer set; §5.3 `DIR_E`/`DIR_M` forward rows → the exclusion clause; §13 ledger → row **AG** (softened); **§12 → new item 12** (Lemma L1 vs a mid-miss tile) |
| `SPEC_SHEET.md` | §7 forward path → the exclusion clause + the superset statement |
| `HLD_LLD_4x4_architecture.md` | Directory FSM: the `DIR_FWD_WAIT → DIR_S` edge → the committed sharer set |
| `HLD_LLD_2x2_FPGA.md` | **no change** — the 2×2 diagrams carry no sharer or directory-FSM text |
| `SLICE_16_1.md` | the verifier count quote → 131/131 |
| `diagrams_rendered.html` | re-rendered from the patched sources; exactly 1 of 19 cards changed (card 7, the directory FSM) |

**Package gate: 131/131 PASS** (a new check **J3** asserts that A2.2 cites §12 item 12 and that the item
exists). The gate was also extended to 131 because the count is quoted in the slice — the count is derived from
the checks that actually run, never negotiated.

> **Not yet true in this checkout — see the verification block at the top of this file.** The gate currently
> runs 130 checks and passes; J3 does not exist.
>
> **Landed 2026-11-06:** the note above recorded the pre-landing state. The package has landed: the gate
> runs **131/131** with **J3** present (`verify_landing.py` PASS).

## 5. What deliberately did **not** change

- The **42-assertion count** — A2.2 is one ID with two clauses.
- The **RTL** — no behavioural change is implied or permitted by this ruling.
- Invariants **I1–I7**, the **SRS**, and the **2×2 LLD**.

## 6. Amendment — why B5 is not closed

Independent review of the first pass found a gap B5 does not close, and the gap is real:

- The surviving **depth-128** BMC evidence reaches a *different* state from Case C: the directory is in
  `DIR_S` with a sharer bit set for a tile that is **mid-miss** (`L1_SM_D`) and therefore holds no data. Both
  L1s are mid-miss in that state.
- **A2.2a is vacuously true there** — no tile holds the line in S — so the restated property cannot see it.
  B5 could therefore close the *invariant* while leaving the *state* unaddressed.
- The question that state raises is unanswered by this ruling: **may the directory send an INV or FWD to a
  tile that has an outstanding miss on that same line?** If it may, Lemma L1 ("no L1 receives a message for a
  line on which it has an outstanding miss") is false as written and §4.6's deadlock-freedom proof loses a
  case. §3.3 rule 6 already provides the likely resolution — an L1 *defers* such a message until its miss
  completes — but that is a **rewording of Lemma L1**, not a fact yet established.
- Separately: the RTL BMC has **never run with assertions live** since the bug was found (`fml_l1_dir.sv`
  wraps the SVA instance in `ifdef FORMAL` with `FORMAL` never defined, and the depth was lowered from 64 to
  32). The "PASS" marker therefore proves nothing. This claim could not be verified from the specification
  side, so it is written into the RTL prompt as a task to **confirm or refute**, with an objective
  anti-vacuity requirement: a run must report the number of live assertions and the depth reached.

**Consequences, applied:**

1. **§12 item 12 is open** — "Lemma L1 versus a mid-miss tile".
2. **A2.2's row carries an explicit vacuity note** so the property cannot be read as covering the mid-miss
   window.
3. **B5.4 is softened**: no RTL change is required *for the Case-C bookkeeping lag*; the K = 64 run with
   assertions live and a directed test of the depth-128 scenario must confirm before B5 is closed.
4. Both agent prompts carry **Task 0** (fix and prove the vacuous PASS), the **depth-128 trace analysis**
   (RTL) and the **mid-miss directed test** (TB).

**B5 closes when all three hold:** the K = 64 BMC run passes with assertions **live** (count reported), the
depth-128 scenario is exercised in a directed test with no INV/FWD to a mid-miss tile — or the hazard is found
and reported as a separate finding with trace evidence — and the §12 item 12 decision is recorded in the WP.
