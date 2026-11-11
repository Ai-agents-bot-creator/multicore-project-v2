# Ruling B8 — FIFO re-issue ordering, and Lemma L2 (bounded progress)

**Status:** enacted and applied to the spec package, 2026-11-07
**Raised by:** the verification team (repeated livelock challenge to ruling B6)
**Decided by:** specification owner (MCode)
**Closes:** WP §12 item 13

---

## 1. The challenge

Ruling B6's abort can, in principle, ping-pong: two tiles upgrading the same line repeatedly abort and
re-issue against each other, with no protocol-level bound on consecutive aborts. Premise F bounds *message
service*, not *request-level progress*. The verification team recommended ageing, a ticket, or backoff.

## 2. The answer is an ordering rule, not a new mechanism

The specification already implied the answer and never stated it: **a re-issued access is a new request.**
It is transmitted like any other request and therefore enters the directory's request queue at the **back**
(FIFO within VC0, invariant I4) — it never re-enters at the head.

Consequences:

- The directory serves a line's requests in FIFO order, so the request it services is the **oldest** pending
  one.
- The invalidation sweep that accompanies that service targets the **other** sharers — whose pending
  requests, if any, are younger. They are the ones aborted.
- The oldest pending request for a line is therefore **never invalidated by a concurrent upgrade**, and it
  completes.
- Each round retires at least one pending request, so the set drains.

**No livelock is possible, and no backoff, ticket or ageing mechanism is required.** The verification team's
recommended remedies are unnecessary: with FIFO ordering the disadvantaged tile is not starved — it is
*served first*.

## 3. The ruling

**B8.1 — the re-issue ordering rule** (WP §3.3 rule 6): an aborted access re-issues as a **new** request
and is enqueued at the **back** of the directory's request queue for that line (FIFO within VC0, invariant
I4); it never re-enters at the head.

**B8.2 — Lemma L2 (bounded progress)**, stated in WP §4.6 beside Lemma L1, with the proof sketch above.

**B8.3 — §12 item 13 is closed.** The challenge was correct as an *observation* and is closed as a **spec
clarification**, not as a new protocol mechanism.

**Also recorded (a model correction, not a spec change):** the receive path has **four** queues — the WP's
four VCs, with INV on **VC3** and FWD on VC1, and INV ranking above FWD as a separate class. A model that
merges INV into VC1 is measuring the model, not the design.

## 4. What changed in the package

| File | Change |
|---|---|
| `FINAL_whitepaper_v3.0.md` | §3.3 rule 6 — the re-issue ordering clause; §4.6 — **Lemma L2**; §12 item 13 **closed**; §13 ledger row **AJ** |
| `SPEC_SHEET.md` | the re-issue ordering and the four-VC clarification |
| `HLD_LLD_4x4_architecture.md` | the directory block's note carries the re-issue ordering |
| `WORK_BREAKDOWN_16.md`, `SLICE_16_1.md` | the quoted verifier count → 134 |
| `diagrams_rendered.html` | re-rendered |

**Package gate: 134/134 PASS** (new check **J6** asserts the re-issue rule, Lemma L2, the closure of
§12 item 13 and ledger row AJ are all present).

## 5. What is still open

- The **per-VC receive path is unimplemented in the RTL** — it is what unblocks the stalled B6.3 test.
- The **reference model** must mirror B7.1/B7.2 (the TB has done this: its model now dequeues the `INVACK`
  ahead of the `GETM`, and both the accept and decline paths terminate with a single writer).
- The **K=64 BMC** with assertions live is still running (45 `$assert` cells; steps 0–16 clean at last
  report).
- The **`rtl/` vs `rtl_frozen/` vs HEAD** divergence must be resolved to one normative copy.
