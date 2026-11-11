# §16 Implementation Work Breakdown — Cache-Coherent Tiled Multicore

**Source of truth:** `FINAL_whitepaper_v3.0.md` (v3.0) + `SPEC_SHEET.md` + the approved LLD PDF.
**Status of every item below:** specified in the WP; **not yet implemented** in RTL, reference model or testbench.
**Verifier:** run `python3 verify_patch_set.py --dir . --build-script build_diagrams_html.py` after any edit to the WP or the LLD `.md` sources (121 checks).

This document maps each of the 14 §16 items to (a) the normative rule(s) it realises, (b) the RTL module that owns it, (c) the SVA/formal assertion category that guards it, (d) the reference-model shadow that must agree with it, and (e) its dependency order. It is the entry point for the RTL phase; every §8 claim in the WP is still "Planned — milestone N" until the corresponding row below is green.

---

## 1. Dependency order (start here)

The assertions that bite hardest live in the **L1 FSM** and the **directory controller**; everything else consumes their outputs. Implement in this order:

1. **L1 MESI controller** — rules 2, 5, 8, 9, 10 (E/M install, forward release, exclusive bit, deferred eviction).
2. **Directory controller** — rules 3, 4, 8, 9, 10 + N4 (forward release, exclusive bit, DIR_I write-back, deferred eviction).
3. **L2 bank** — N3a/N13 (per-line word) + N15 (dirty set/clear).
4. **NIC** — N3b (DATAFWD dirty bit), B11 (FIFO depth), VC preservation.
5. **Router** — B1 (13-round fairness bound), credit management.
6. **Memory tap** — A6 (bank/tap currency), write-back commit.
7. **DMA tile** (gated, Week 8) — B4, §12 item 10/11.

No §16 item may be marked green until its SVA category and its reference-model shadow are both green.

---

## 2. Item-by-item mapping

### §16.1 — Forward release (rule 8)

| | |
|---|---|
| **Normative rule** | Rule 8 (forward-initiated release is not a replacement eviction); A1.1, A1.3, A2.2, A2.6 |
| **RTL module** | `l1_mesi_ctrl` (owner side), `dir_ctrl` (directory side) |
| **Behaviour** | On FWD_GETS: E/M → S, send DATAFWD (clean/dirty), no PUTS/PUTM. On FWD_GETM: E/M → I, send DATAFWD. Directory records owner+requester as sharers (GETS) or clears old owner's bit and sets Owner = requester (GETM). |
| **SVA / formal** | A1.1, A1.3, A2.2, A2.6 (BMC, K = 64); A3.1–A3.6 (forward legality) |
| **Reference-model shadow** | Per-tile L1 state/tag/data; per-bank directory entry (state, owner, sharers); outstanding-transaction set |
| **Depends on** | — (first item). The L1 side needs no prior item; the **directory** side writes the bank and so needs §16.3 + §16.4. |
| **Effort** | 3–4 days |

### §16.2 — DATA exclusive bit (rule 9)

| | |
|---|---|
| **Normative rule** | Rule 9; A1.3, A2.6 |
| **RTL module** | `dir_ctrl` (sets the bit on DATA), `l1_mesi_ctrl` (installs E on excl=1, S on excl=0) |
| **Behaviour** | excl = 1 on a DIR_I grant and on every GETM grant (including a forward); excl = 0 on every GETS grant (including a forward, where the old owner downgraded to S). |
| **SVA / formal** | A1.3, A2.6; L1 install path in Appendix A |
| **Reference-model shadow** | L1 MESI state after install; DATA exclusive bit in the packet |
| **Depends on** | §16.1 |
| **Effort** | 1 day |

### §16.3 — L2 per-line word (N3a, N13)

| | |
|---|---|
| **Normative rule** | §3.6 (per-line word `{valid, tag, dirty}`); A6 (bank/tap currency) |
| **RTL module** | `l2_bank` (tag array + dirty/valid bits), `l2_ctrl` |
| **Behaviour** | 23 b at 2×2 / 21 b at 4×4 = valid + address tag + dirty. `valid` distinguishes an empty way from a resident line (an all-zero empty tag would otherwise alias the line at address 0x0000_0000). `dirty` = bank copy newer than the tap. |
| **SVA / formal** | A6.1–A6.4 (data integrity); bank-hit path |
| **Reference-model shadow** | Per-bank/set/way L2 state, tag, dirty bit, data |
| **Depends on** | none (foundational) |
| **Effort** | 2 days |

### §16.4 — Dirty indication on DATAFWD (N3b)

| | |
|---|---|
| **Normative rule** | N3b; §3.8 header bit [39] |
| **RTL module** | `nic` (sets bit 39 from the owner's L1 state), `dir_ctrl` (consumes it) |
| **Behaviour** | On a DATAFWD packet, header bit [39] = dirty iff the owner held the line in M. Directory sets the bank dirty bit from this bit. |
| **SVA / formal** | A6.x (dirty-data integrity) |
| **Reference-model shadow** | Packet header [39]; bank dirty bit |
| **Depends on** | §16.1, §16.3 |
| **Effort** | 1 day |

### §16.5 — DIR_I victim write-back (N4)

| | |
|---|---|
| **Normative rule** | N4; §3.3 single-exit rule |
| **RTL module** | `dir_ctrl` (victim classification in DIR_EVICT) |
| **Behaviour** | A DIR_EVICT whose victim is DIR_I with a dirty bank line takes the WRITE_BACK sub-state (bank → tap); otherwise the victim needs no write-back. |
| **SVA / formal** | A7.x (state-machine legality) + A5.x (no orphan transient) |
| **Reference-model shadow** | Directory evict sub-state; tap contents |
| **Depends on** | §16.3 (dirty bit) |
| **Effort** | 1 day |

### §16.6 — Evict-during-forward handling (N5, N12)

| | |
|---|---|
| **Normative rule** | N5, N12; rule 5 (INV response), defensive INVACK |
| **RTL module** | `l1_mesi_ctrl` (I/EI_A/MI_A on FWD → INVACK), `dir_ctrl` (DIR_FWD_WAIT absorbs PUTM/PUTS/INVACK) |
| **Behaviour** | L1 in I/EI_A/MI_A on a FWD answers with the defensive INVACK. Directory in DIR_FWD_WAIT absorbs a PUTM (satisfies the forward — write bank, set dirty, clear old owner's bit, send PUTACK), a PUTS (cancels the forward — bank holds current value, serve requester from bank, send PUTACK), or a defensive INVACK (duplicate release, ignored). |
| **SVA / formal** | A1.x, A2.x (no orphan transient); A7.x (FSM legality) |
| **Reference-model shadow** | L1 state, directory state, owner/sharer bits, bank dirty bit |
| **Depends on** | §16.1, §16.3, §16.4 |
| **Effort** | 2–3 days |

### §16.7 — 13-round fairness bound (B1)

| | |
|---|---|
| **Normative rule** | B1; Premise F |
| **RTL module** | `router` (age counter per (input port, VC); output-port round-robin) |
| **Behaviour** | A VC that has waited ≥ 8 arbitration rounds is granted next; the end-to-end bound is 8 + 5 = 13 switch-arbitration rounds (11 at a corner tile). |
| **SVA / formal** | A5.x (bounded liveness) + the §4.6 deadlock lemma confirmed by k-induction at k = 16 |
| **Reference-model shadow** | Not modelled at transaction level (timing) — checked by SVA/formal |
| **Depends on** | none (router-local) |
| **Effort** | 2 days |

### §16.8 — Tree-PLRU update rule (B10)

| | |
|---|---|
| **Normative rule** | B10; §4.4 |
| **RTL module** | `l1_cache` (PLRU logic), `l2_bank` (PLRU logic) |
| **Behaviour** | On a hit in way w, update the 3-bit tree so w's subtree becomes MRU; victim = way in the LRU subtree, lower-numbered way on a tie. |
| **SVA / formal** | No assertion covers replacement determinism. Guard is the reference model: the model's victim choice must match the RTL bit-for-bit. |
| **Reference-model shadow** | Per-set PLRU bits in both L1 and L2 |
| **Depends on** | §16.3 (L2 tag array layout) |
| **Effort** | 1 day |

### §16.9 — NIC FIFO depth (B11)

| | |
|---|---|
| **Normative rule** | B11; §3.5 |
| **RTL module** | `nic` (TX/RX FIFOs) |
| **Behaviour** | TX and RX FIFOs are 4 flits per VC, matching the router's per-port FIFO depth and the credit depth. |
| **SVA / formal** | Credit invariant (I3); buffer occupancy ≤ depth; in simulation A4.x |
| **Reference-model shadow** | Not modelled at transaction level |
| **Depends on** | none |
| **Effort** | 0.5 day |

### §16.10 — 512-bit intra-tile path (B5)

| | |
|---|---|
| **Normative rule** | B5; §3.1 |
| **RTL module** | `intra_tile_mux`, `l1_mesi_ctrl`, `l2_ctrl`, `dir_ctrl` (bus widths) |
| **Behaviour** | A whole cache line moves in one 512-bit transfer (`evict_data`, `fill_data`, `l2_wdata`, `mem_wdata`, `tx_data`); the NoC moves the same line as 9 flits. |
| **SVA / formal** | A6.x (the 512-bit transfer equals the 64 B line; write-then-read returns the written value) |
| **Reference-model shadow** | L1/L2 data arrays (64 B lines) |
| **Depends on** | §16.3 (line size) |
| **Effort** | 1 day (width plumbing) |

### §16.11 — DMA path mapping (B4)

| | |
|---|---|
| **Normative rule** | B4; §3.11 |
| **RTL module** | `dma_tile` (L1-lite + engine), `dir_ctrl` (DMA_WRITE handling) |
| **Behaviour** | DMA_WRITE is serviced as a GETM: DIR_FWD_WAIT if owned, DIR_INV_WAIT if shared; the DMA tile's copy is tracked by its sharer bit; the directory replies DMA_ACK on completion. The owner's write-back is committed to the bank before the DMA's inline data is written. |
| **SVA / formal** | A1.x–A4.x (directory legality); A8.x (DMA invariants) |
| **Reference-model shadow** | DMA tile's L1-lite state; directory state; bank data |
| **Depends on** | §16.1, §16.2, §16.6 (forward handling), §12 item 10 (L1-lite FSM) |
| **Effort** | 4–5 days (gated on Week-8 gate) |

---

### §16.12 — Rule 10 (deferred eviction)

| | |
|---|---|
| **Normative rule** | Rule 10; §3.3 |
| **RTL module** | `l1_mesi_ctrl` |
| **Behaviour** | An L1 with an outstanding miss does not begin a replacement eviction; a needed eviction is deferred until the miss completes. MSHRs are future scope. |
| **SVA / formal** | None in the 42 — guarded by the reference model + scoreboard (candidate if the assertion set ever grows). |
| **Reference-model shadow** | L1 outstanding-miss flag; eviction-deferral flag |
| **Depends on** | none |
| **Effort** | 0.5 day |

### §16.13 — Tile-ID tie-off (§5, §3.6)

| | |
|---|---|
| **Normative rule** | §5 (static TILE_ID input), §3.6 (mesh position) |
| **RTL module** | mesh top-level (tie-off), `tile` (TILE_ID port) |
| **Behaviour** | TILE_ID is a static, hardwired module input tied off to N·X + Y at the mesh top level. |
| **SVA / formal** | None in the 42 — guarded by the reference model. |
| **Reference-model shadow** | Tile numbering in the reference model |
| **Depends on** | none |
| **Effort** | 0.25 day |

### §16.14 — FPGA stimulus source (§6.1)

| | |
|---|---|
| **Normative rule** | §6.1 (stimulus source = on-board JTAG bridge); §9 (ILA/VIO future scope) |
| **RTL module** | board-level test harness (not in the tile RTL) |
| **Behaviour** | The FPGA build's stimulus source is the on-board JTAG bridge; ILA/VIO debug is future scope. |
| **SVA / formal** | None (board-level) |
| **Reference-model shadow** | not applicable |
| **Depends on** | none |
| **Effort** | 1–2 days |

## 3. Effort summary

| Item | Days | Gate |
|---|---|---|
| §16.1 Forward release | 3–4 | Week 10 |
| §16.2 Exclusive bit | 1 | Week 10 |
| §16.3 L2 per-line word | 2 | Week 4 |
| §16.4 DATAFWD dirty bit | 1 | Week 6 |
| §16.5 DIR_I write-back | 1 | Week 6 |
| §16.6 Evict-during-forward | 2–3 | Week 10 |
| §16.7 13-round fairness | 2 | Week 4 |
| §16.8 PLRU rule | 1 | Week 4 |
| §16.9 NIC FIFO depth | 0.5 | Week 4 |
| §16.10 512-bit path | 1 | Week 4 |
| §16.11 DMA path | 4–5 | Week 8 (gated) |
| §16.12 Rule 10 (deferred eviction) | 0.5 | Week 4 |
| §16.13 Tile-ID tie-off | 0.25 | Week 4 |
| §16.14 FPGA stimulus source | 1–2 | Week 12 |
| **Total (baseline, no DMA)** | **~15–18 days** | |
| **Total (with DMA)** | **~19–23 days** | |

---

## 3b. Assertion coverage (honest answer)

Which normative rule is checked by which assertion. Four of the fourteen items have **no direct assertion** in the 42 — they are guarded only by the reference model and the scoreboard, and are the candidates if the assertion set ever grows beyond the fixed 42.

| §16 item | Direct assertion? | Coverage |
|---|---|---|
| §16.1 Forward release | Yes | A1.1, A1.3, A2.2, A2.6 |
| §16.2 Exclusive bit (consequences) | Yes | A1.3, A2.6 |
| §16.3 L2 per-line word | Indirect | A6.x (data integrity) |
| §16.4 DATAFWD dirty bit | Indirect | A6.x |
| §16.5 DIR_I write-back | Indirect | A4.x, A7.x |
| §16.6 Evict-during-forward | Yes | A1.x, A2.x, A7.x, A5.x |
| §16.7 13-round fairness | Yes | A5.x (bounded liveness) + §4.6 deadlock lemma (k-induction, k = 16) |
| §16.8 PLRU rule | **No** | Reference model + scoreboard only |
| §16.9 NIC FIFO depth | Indirect | A4.x (credit invariant) |
| §16.10 512-bit path | Indirect | A6.x |
| §16.11 DMA path | Yes | A1.x–A4.x, A8.x |
| §16.12 Rule 10 (deferred eviction) | **No** | Reference model + scoreboard only |
| §16.13 Tile-ID tie-off | **No** | Reference model only |
| §16.14 FPGA stimulus source | **No** | Board-level; not in the 42 |

**No direct assertion:** replacement determinism (§16.8), the deferred-eviction rule (§16.12), the tile-ID tie-off (§16.13). These three plus the exclusive-bit rule's *text* are the candidates if the assertion set ever grows beyond the fixed 42.

## 4. Verification gate for each item

An item is green only when all three are green:

1. **RTL implemented** — the module compiles and passes its unit tests.
2. **SVA passing** — the assertion category listed above is clean in simulation (BMC K = 64 for safety).
3. **Reference model agrees** — the scoreboard's per-tile/per-bank/per-directory comparison shows zero mismatches on the dirty-line test suite (directed tests 1–22, §5.1).

Until all three are green, the corresponding §8 claim stays "Planned — milestone N".

---

## 5. Notes

- The 121-check verifier (`verify_patch_set.py`) guards the *specification*; it does not guard the RTL. Run it after any WP or LLD edit, including edits made during the RTL phase, because the reference model and the SVA set must move in lockstep with the WP.
- The DMA L1-lite FSM (§12 item 10) is the one gated open item that blocks §16.11; it must be specified before the DMA week.
- The age threshold's empirical value (§12 item 8) and the bank service order (§12 item 9) are deliberately left open; the RTL may choose either, but the choice must be recorded in §3.5 / §3.7 before sign-off.
- The coverage bin list (§12 item 2) and the *T*-counting mechanism (§12 item 7) are testbench-side and do not block any §16 item.
