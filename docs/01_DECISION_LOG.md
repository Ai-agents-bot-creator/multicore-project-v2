# Architectural Decision Log (ADR)

> **Document Purpose**: Authoritative Architectural Decision Record (ADR) capturing formal protocol rulings, microarchitectural adjudications, and implementation contracts.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — direct active verbs, restricted synonym usage, unambiguous criteria, and strict clause brevity.

## Rulings

| ID | Topic | Ruling | Contested | Resolved by |
|---|---|---|---|---|
| B1 | Age-escape threshold | 5 rounds; bound 5+3+5=13; port-granular arbiter | No | Supervisor 2026-11-04 |
| B2 | Conflict eviction | Victim released before miss on VC0; sub-step of miss transient | No | Supervisor 2026-11-04 |
| B4 | DMA scope | 2×2 has 4 CPU tiles, 0 DMA; DMA is 4×4 sim-only Week-8 gated | No | Supervisor 2026-11-04 |
| B5 | Sharer accuracy (A2.2) | A2.2 becomes two clauses under one ID: **a** — no missing bits (strict, never relaxed); **b** — extra bits allowed only while `PUTS`/`PUTM` is in flight, cleared within T = 64. Sharer vector is a conservative **superset**, never a subset. On `DIR_FWD_WAIT → DIR_S` the committed set excludes an already-released tile. **No RTL change** for the Case-C bookkeeping lag. **B5 is NOT closed** (§12 item 12 open; needs live K=64 BMC + mid-miss directed test) | No | Specification owner (MCode) 2026-11-06 — full text in `docs/RULINGS_B5.md` |
| B6 | Same-line INV during an outstanding miss | A same-line INV in `IS_D`/`IM_D`/`SM_D` **aborts the outstanding miss**: the L1 invalidates its copy, answers INVACK immediately, and re-issues the access. Deferral is forbidden (it deadlocks the one-outstanding-transaction-per-bank directory). Lemma L1 restated; the formal harness may not drive UNBLOCK before the requester installed the data. §12 item 12 closed | No | Specification owner (MCode) 2026-11-07 — row AH in WP §13 |
| B7 | Directory receive-path ordering (per-VC) | The home tile's receive path holds **one queue per VC** and pops them by the fabric's class priority **RESP > INV > FWD > REQ**, so a response is never head-of-line blocked behind a request that arrived earlier. An aborted access is **completed or re-issued**: the tile may accept the stale grant (install + UNBLOCK) or decline it, but the directory's transient must always exit and a declining tile is never recorded as owner. §12 item 13 (bounded progress under repeated aborts) recorded **open** by B7 — **closed by ruling B8** (see below) | **Yes — `dir_ctrl.sv` per-VC RX mailbox** | Specification owner (MCode) 2026-11-07 — row AI in WP §13 |
| B8 | FIFO re-issue ordering (bounded progress) | A re-issued access is a **new request**: it is transmitted like any other request and enqueued at the **back** of the directory's request queue for that line (FIFO within VC0, invariant I4) — it never re-enters at the head. Lemma L2 (§4.6): the directory serves a line's requests in FIFO order, so the request it services is the oldest pending one; the invalidation sweep targets the other, younger sharers — therefore the oldest pending request is never invalidated by a concurrent upgrade and always completes, and each round retires at least one pending request. No backoff, ticket or ageing mechanism is required. §12 item 13 **closed** | No — spec clarification of the ordering the spec already implied | Specification owner (MCode) 2026-11-07 — row AJ in WP §13 |
| R2 | Bank arbiter order | **Provisional**: tap > remote > L1 (see `BANK_ARB_TAP_FIRST` in `tile_pkg.sv`); spec §12 item 9 leaves order unspecified | **Yes — provisional** | Open (OI-4) |
| R3 | L2 bank port shape | Frozen per `tile_pkg.sv`: req {valid, is_write, addr, wdata, wstrb, source_sel}, rsp {valid, rdata, rstrb, rlast}, status {dtr_busy}. source_sel enum {TAP, REMOTE, L1} is the R2 input. | Provisional pending PLRU/write-logic impl | Open (R2/OI-4 arbiter) |
| R4 | cocotb major version | Pinned to 2.1.0 (installed via pipx; iverilog 13.0). Consequence: `dut.<sig>.value` returns LogicArray (not int); Timer signature; no `cocotb.binary`. Future tests must match 2.x. Revisit only if cocotb upgrade re-runs tb/smoke green. | No | 2026-11-04 |
| R5 | Formal scope: NIC backpressure | **Provisional:** `assume(!dir_oflow)` is a formal environment assumption standing in for NIC credit management (WP §16.9 not implemented). F1 formal results valid ONLY under this assumption. Re-run without the assumption when §16.9 lands. | Yes — provisional | Open until §16.9 implemented |

## Adjudication Ledger — Row AG (verbatim copy from WP §13)

*Quoted verbatim from `white_papers/final/FINAL_whitepaper_v3.0.md` §13 (row `| **AG** |`). Both copies are edited together or not at all, so they cannot drift.*

> | # | Contested point | Q | M | X | G | E | D | **Ruling (v3.0)** | Deciding basis |
> |---|---|---|---|---|---|---|---|---|---|
> | **AG** | Sharer accuracy under a concurrent owner eviction (ruling B5) | — | — | — | — | — | — | **A2.2 restated as two clauses under one assertion ID: A2.2a “no missing bits” (strict — every tile holding the line in S has its bit set) and A2.2b “bounded extra bits” (a stale bit is permitted only while that tile's release notification is in flight, and must clear within *T* = 64 cycles). The committed sharer set on the DIR_FWD_WAIT exit excludes a tile that has already released the line. The directory's sharer vector is a conservative superset of the actual holders, never a subset. **No RTL change is required for the Case-C bookkeeping lag**; the K = 64 BMC run with assertions live, and a directed test of the depth-128 trace scenario, must confirm that before B5 is closed (§12 item 12)** | Ruling B5: the verification team reproduced — by directed test and by a BMC counterexample — the case where the owner evicts while a forward is outstanding. The owner's PUTS travels on VC0 and the requester's UNBLOCK on VC2, and no FIFO order relates them, so the directory may exit DIR_FWD_WAIT while a sharer bit still names a tile that has already released. That transient is inherent to an asynchronous release notification, not an RTL defect: the directory absorbs the PUTS, clears the bit and self-corrects, and data integrity is unaffected. The previous wording (“sharers equal the S-mask exactly, no stale bits”) assumed instantaneous message delivery and is therefore unachievable per cycle. The correct restatement is one-sided: the missing-bit direction, which is what prevents two writers on one line, stays strict, and the extra-bit direction is bounded by the release flight time. Rejected: routing PUTS on VC1 (breaks invariant I2, VC = class) and adding PUTACK to S-state evictions (extra round trip, deadlock risk). |

## Adjudication Ledger — Row AH (verbatim copy from WP §13)

*Quoted verbatim from `white_papers/final/FINAL_whitepaper_v3.0.md` §13 (row `| **AH** |`). Both copies are edited together or not at all, so they cannot drift.*

> | # | Contested point | Q | M | X | G | E | D | **Ruling (v3.0)** | Deciding basis |
> |---|---|---|---|---|---|---|---|---|---|
> | **AH** | Same-line INV during an outstanding miss (ruling B6) | — | — | — | — | — | — | **A same-line INV aborts the L1's outstanding miss: the L1 invalidates its copy, answers INVACK immediately, and re-issues the access. Deferral is forbidden — it deadlocks against the one-outstanding-transaction-per-bank directory. Lemma L1 is restated from "no same-line message" to "no same-line message is serviced", with the abort as the single exception** | Ruling B6: the verification team's directed test of the concurrent-upgrade race found the directory issuing an INV to a tile in `L1_SM_D` on the same line — a case §3.3 rule 6 and Lemma L1 (§4.6) both declared impossible, so the §4.6 deadlock-freedom proof rested on a false premise. The fix is in the protocol, not in the assertion set: the abort path is the standard MESI resolution and costs no extra message. The formal harness must also be constrained: it may not drive an UNBLOCK from a requester that has not installed the data (the real L1 never does), which was the cause of the depth-128 counterexample. |

## Adjudication Ledger — Row AI (verbatim copy from WP §13)

*Quoted verbatim from `white_papers/final/FINAL_whitepaper_v3.0.md` §13 (row `| **AI** |`). Both copies are edited together or not at all, so they cannot drift.*

> | # | Contested point | Q | M | X | G | E | D | **Ruling (v3.0)** | Deciding basis |
> |---|---|---|---|---|---|---|---|---|---|
> | **AI** | Directory receive-path ordering and the completion of an aborted access (ruling B7) | — | — | — | — | — | — | **The home tile's receive path holds one queue per VC and pops them by the same class priority as the fabric (RESP > INV > FWD > REQ), so a response is never head-of-line blocked behind a request. An aborted access is completed or re-issued: the tile may accept the stale grant (installing the line and sending UNBLOCK) or decline it, but the directory's transient must always exit and the directory must never record a declining tile as the owner** | Ruling B7: with the B6 abort implemented, the directed upgrade-race test still stalled — the directory sat in `DIR_INV_WAIT` with `RXQ cnt=2 head_msg=GETM` and the `INVACK` behind it. The WP fixed VC priority only inside the router (§3.5 item 1), so a single arrival-ordered directory queue was specification-conformant and deadlocked: the directory pops only `INVACK`/`PUTS`/`PUTM`/`UNBLOCK` while a transient is open, so a queued `GETM` blocks the invalidation that must complete it. Two changes close it: the per-VC receive order (which makes the `INVACK` reachable) and the explicit completion/decline rule for the abandoned request (which keeps the directory's state consistent with what the tile actually holds). |

## Adjudication Ledger — Row AJ (verbatim copy from WP §13)

*Quoted verbatim from `white_papers/final/FINAL_whitepaper_v3.0.md` §13 (row `| **AJ** |`). Both copies are edited together or not at all, so they cannot drift.*

> | # | Contested point | Q | M | X | G | E | D | **Ruling (v3.0)** | Deciding basis |
> |---|---|---|---|---|---|---|---|---|---|
> | **AJ** | Bounded progress under repeated upgrade-race aborts (ruling B8) | — | — | — | — | — | — | **An aborted access re-issues as a new request and is enqueued at the BACK of the directory's request queue for that line (FIFO within VC0, invariant I4). The oldest pending request for a line is never invalidated by a concurrent upgrade, so it completes; each round retires at least one pending request. Lemma L2 states the bound. No backoff, ticket or ageing mechanism is required** | Ruling B8: the verification team re-raised the livelock challenge (two tiles aborting each other's upgrade in turn, unboundedly). The specification already implied the answer but never stated it — a re-issued access is a new request, so it enters the queue at the back rather than the head. Stating that makes the oldest pending request immune to concurrent invalidation, which bounds progress directly. The challenge is therefore **closed as a spec clarification**, not as a new protocol mechanism. |

### B8.1 (re-issue ordering) — RTL status: NOT RTL-VERIFIED

The current RTL implements the accept path only (B7.2 permits accept or decline), so the B6 abort does not re-transmit and no RTL behaviour depends on the re-issue ordering rule. The rule is verified in the transaction-level reference model (Mut-08, killed) and, after R3, by the three-tile directed case. Implement the decline path to close this at RTL level; tracked as an open item.

**Coverage note (v7 Task R3).** The three-tile directed case (`tb_rtl_evidence/directed_vc0_fifo/`) exercises the mechanism B8.1 depends on — the per-VC FIFO ordering (I4) of the directory's request queue — with the minimum setup that makes it observable: tile0 GETs the line, the directory is busy in `DIR_MEM_WAIT`, and tiles 1 and 2 GET the same line while it is busy, so **two pending REQs for the same line sit on VC0 at once** (proved from the queue pointers: `cnt=2 rd=1 wr=3`). The head-insertion mutant (MUT-D) is then killed by the **ordering detector** — arrival `[1,2]` but served `[2,1]` — while the line still completes (`sharers=0b111`, all three L1s in `L1_S`), so the kill is the ordering property itself and not a stall. The two-tile upgrade-race case could not show this: with one outstanding request per tile, VC0 never holds two same-line REQs at once. The mutation matrix is now 5 columns, **20/20 derived from the matrix**; the old two-tile case is kept as a regression.

This does **not** change B8's status as a *specification* ruling (it closes §12 item 13 on paper). It records that the property is **not yet verified at RTL level**, because the re-issue it constrains does not exist in the RTL. The decline path is the missing piece; tracked as an open item.

## Contested Decisions

*(None currently contested. Contested decisions are recorded here with open questions and resolution path.)*

## ADR-001: Baseline Unified Specification & Corrected 12-Module Build Order
- **Date:** 2026-11-04
- **Status:** Accepted
- **Context:** Correcting scope creep from old attached single-core SoC artifacts (`Build Order cf8a8428393d.md` / `Flat Table Database 2766ea9dcf5c.csv`). Establishing verified coherence-only fabric tree.
- **Decision:** 
  1. Processor core RTL is strictly **out of scope** (WP §1.2 line 49). Stimulus via testbench / on-board JTAG bridge.
  2. Implement in corrected dependency order: `tile_pkg` (Done) -> `l2_bank` (freeze bank/tag port) -> `l1_mesi_ctrl` + `dir_ctrl` (co-landed) -> `nic` -> `router` -> `mem_tap` -> `intra_tile_mux` -> `cpu_tile` -> `mesh_top` -> `fpga_top`.
  3. DMA Tile (`dma_tile.sv`) is strictly gated on Week 8 in 4×4 simulation only; 0 DMA tiles in 2×2 FPGA build (Ruling B4).
  4. Four-Item Green Criterion enforced per module: RTL clean lint/test + SVA BMC K=64 + TLM reference model zero mismatch + 134/134 `verify_patch_set.py` pass.

