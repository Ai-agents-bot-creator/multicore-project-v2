# Implementation Build Order — Cache-Coherent Tiled Multicore

Source of truth: `FINAL_whitepaper_v3.0.md` (v3.0) + `SPEC_SHEET.md` + approved LLD.
Derived from: `WORK_BREAKDOWN_16.md` (§1 dependency order, §2–§4 item mapping).

This is the order the RTL/TB phase builds in. It is a projection of the verified spec — not a new design.

## Pre-flight (before any RTL line)

1. `python3 verify_patch_set.py --dir . --build-script build_diagrams_html.py` → **PASS - 130/130**, exit 0.

## Sequence

1. **L1 MESI controller** (`l1_mesi_ctrl`) — §16.1 (forward release incl. victim release, 4–5 d), §16.2 (exclusive bit, 1 d), §16.12 (deferred eviction, 0.5 d).
2. **Directory controller** (`dir_ctrl`) — §16.1 (dir side), §16.4 (DATAFWD dirty, 1 d), §16.5 (DIR_I write-back, 1 d), §16.6 (evict-during-forward, 2–3 d), §16.11 (DMA write-back).
3. **L2 bank** (`l2_bank` / `l2_ctrl`) — §16.3 (per-line word, 2 d), §16.8 (PLRU, 1 d), §16.10 (512-bit path, 1 d).
4. **NIC** (`nic`) — §16.9 (FIFO depth, 0.5 d), §16.4 (dirty-bit consumption), credit invariant (I3).
5. **Router** (`router`) — §16.7 (13-round fairness, B1, 2 d), credits, XY deterministic routing.
6. **Memory tap** — write-back commit, bank/tap currency (A6).
7. **DMA tile** (`dma_tile`) — §16.11, **gated on Week-8 gate exit**; blocked meanwhile by §12 item 10 (L1-lite FSM) until that open item is specified.

## Green criterion per item

All three (per `WORK_BREAKDOWN_16.md` §4) before any §8 claim is marked *Implemented*: RTL unit green → SVA category clean (BMC K = 64) → reference-model shadow agrees (scoreboard, directed tests 1–22).

## Effort totals

Baseline (no DMA): **~15–18 days**. With DMA (§16.11): **~19–23 days**.

## Future scope (no build work scheduled)

MSHRs (§3.3 residual), adaptive routing, snooping, >16-tile scale.
