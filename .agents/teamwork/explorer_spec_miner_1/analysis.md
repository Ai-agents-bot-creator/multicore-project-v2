# Comprehensive Specification Mining & Ground-Truth Verification Report

**Document:** `analysis.md`  
**Agent:** `explorer_spec_miner_1` (Specification Miner)  
**Date:** 2026-11-09  
**Target Under Audit:** `SRS_final.docx` (v0.2, 04-11-2026)  
**Authoritative Ground Truth:**  
- `FINAL_whitepaper_v3.0.md` (Gate 130/130, v3.0 Unified Final)
- `SPEC_SHEET.md` (Formal Specification Sheet)
- `HLD_LLD_4x4_architecture.md` & `HLD_LLD_2x2_FPGA.md`
- `WORK_BREAKDOWN_16.md` & `SLICE_16_1.md`
- `RULINGS_B1_B2_B4.md`, `RULINGS_B7.md`, `RULINGS_B8.md`
- `SRS_REVIEW.md` & `verify_srs.py`

---

## Executive Summary

A deep architectural audit and ground-truth feature mining was performed on `SRS_final.docx` (v0.2) against the complete project specification suite. While `SRS_final.docx` successfully resolves the 18 defects flagged in `SRS_REVIEW.md` and passes all 41 automated checks in `verify_srs.py`, this investigation uncovered critical specification drift, normative gaps, and compliance defects resulting from subsequent rulings and architectural freezes enacted after v0.2 was created on 2026-11-04.

Most notably, **Rulings B6, B7, and B8** (enacted 2026-11-07) introduced fundamental protocol mechanics:
1. **Ruling B6 / Whitepaper Rule 6 (Row AH):** Same-line `INV` during an outstanding L1 miss (`IS_D`, `IM_D`, `SM_D`) must abort the miss, send `INVACK` immediately, and re-issue the access to resolve concurrent upgrade races without deadlocking against the directory.
2. **Ruling B7 / Whitepaper §3.5 (Row AI):** The directory controller's receive path must be per-VC (4 independent queues) and popped with fabric class priority `RESP > INV > FWD > REQ`, preventing response head-of-line blocking behind requests. Aborted accesses must be completed or declined with `UNBLOCK`.
3. **Ruling B8 / Whitepaper §3.3 Rule 6 & §4.6 Lemma L2 (Row AJ):** Re-issued requests must enter the directory request queue at the back (FIFO within VC0, Invariant I4) as a new request, guaranteeing bounded progress and preventing upgrade livelocks.

None of these four major rulings are reflected in `SRS_final.docx` (which only references Rulings B1, B2, and B4 up to row AF). In addition, this audit identified:
- Technical errors in Section 7.2 (erroneous `ready` signals in credit-based flow control; missing `TILE_ID` and flit VC sideband; conflation of chip top-level I/O with internal tile router ports).
- Incomplete Traceability Matrix (Section 10), which traces only `FR-01` through `FR-14`, completely omitting all Performance (`PERF-*`), Power (`PWR-*`), Area (`AREA-*`), FPGA (`FPGA-*`), and Assumption (`AC-*`) requirements.
- Unnecessary "TBD" placeholders for the FPGA target frequency (established as 100 MHz / 10 ns by WP §6.1/§6.4 and HLD-F3).
- Missing STA closure metrics (`WHS >= 0`, `WPWS >= 3.750 ns`, `TNS = 0`).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Coherence | Directory-based MESI | Distributed shared cache coherence across 2D tiled mesh using 4 stable states (M, E, S, I) and inclusive directory | CPU core load/store/flush, NoC packets | Cache line data, coherence control flits | Transaction timeout after bound $T$; caught by A1.x, A2.x, A5.x | WP §3.3, SPEC_SHEET §7 |
| 2 | Routing | Deterministic XY Routing | Flits route along X dimension to target column, then along Y dimension to target row. Turns from Y to X are strictly prohibited | 64-bit flit header with Dest Tile `[63:56]` | Router output port select (LOCAL, N, S, E, W) | Routing out of bounds or illegal turn caught by SVA A8.x and Invariant I1 | WP §3.5, HLD_LLD_4x4 LLD-1 |
| 3 | Flow Control | Credit-Based Flow Control | Flow control on each inter-router link using per-VC credit tracking; buffer occupancy never exceeds FIFO depth 4 | Credit return pulses (`credit_in[3:0]`) from downstream router | Flit transmission valid only when credit > 0; pulses `credit_out[3:0]` on dequeue | Credit underflow/overflow or send at credit 0 caught by SVA A4.x and Invariant I3 | WP §3.5, SPEC_SHEET §9.2 |
| 4 | Arbitration | Two-Level Class Priority with Age Escape | Input arbiter enforces fixed class priority `RESP > INV > FWD > REQ`. Age counter (threshold 5 rounds) grants oldest starving VC. Output arbiter is port-granular round-robin across input ports | Inbound flits on 4 VCs across active ports | Selected VC flit forwarded to switch crossbar | Starvation beyond derived bound (13 rounds interior, 11 corner) caught by A5.x and Premise F | Ruling B1, WP §3.5, SPEC_SHEET §9.3 |
| 5 | Eviction | Non-Silent Eviction with PUTACK | Clean lines (S/E) send PUTS; dirty lines (M) send PUTM (9 flits). Directory returns PUTACK to exit `EI_A`/`MI_A`. Silent drops prohibited | L1 cache replacement or eviction trigger | `PUTS` / `PUTM` packet to directory on VC0 | Silent drop violates A2.2 and wedges DIR_INV_WAIT; caught by SVA A1.1, A1.2, A3.x | WP §3.3 Rule 2, Ruling B2 |
| 6 | Eviction | Conflict Eviction Before Miss (Rule 10) | If a miss encounters a full cache set, the PLRU victim is evicted *before* the miss request is issued. Both travel on VC0; L1 remains in `IS_D`/`IM_D` | Load/store miss on set with no invalid way | Victim `PUTM`/`PUTS` on VC0, followed by `GETS`/`GETM` on VC0 after PUTACK | Reversing event order deadlocks against directory; caught by SVA A7.x | Ruling B2, WP §3.3 Rule 10 |
| 7 | Directory FSM | Single-Exit Transient Directory FSMs | Transient directory states (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`) have exactly one exit event: `UNBLOCK`. Intermediate messages only advance DTR | `UNBLOCK` response flit on VC2 from requester | Successor stable state (`DIR_S`, `DIR_M`, `DIR_E`) committed | Orphan transient or premature exit caught by SVA A2.7, A7.x | Ruling B, WP §3.3, §3.7 |
| 8 | DMA | Gated 4x4 Simulation-Only DMA | DMA write path (GETM-mapped) evaluated at Week-8 gate in 4x4 simulation only. 2x2 FPGA build has zero DMA tile; `pending_op = DMA` unreachable | DMA channel commands via register map | DMA read/write transactions on mesh | Enabling DMA in 2x2 build raises configuration assertion; A8.4 catches reserved DMA home code | Ruling B4, WP §3.11, §13 row AD |
| 9 | Datapath | 512-bit Intra-Tile Transfer | Single-cycle transfer of whole 64-byte line between L1, L2 bank, directory, and NIC within a tile | 512-bit cache line bus | 512-bit data delivered in 1 clock cycle | Mismatched data caught by SVA A6.x | WP §3.1, SPEC_SHEET §2 |
| 10 | Forwarding | Forward Release Without Replacement Eviction | Owner servicing `FWD_GETS` downgrades E/M→S; servicing `FWD_GETM` downgrades E/M→I. Data returned via `DATAFWD` on VC2; owner does not send PUTS/PUTM | Inbound `FWD_GETS` / `FWD_GETM` on VC1 | `DATAFWD` on VC2; owner state downgraded | Spurious PUTS/PUTM corrupts directory tracking; caught by A1.3, A2.2, A2.6 | WP §3.3 Rule 8, SLICE_16_1 |
| 11 | Protocol | DATA Exclusive Ownership Grant | Directory sets exclusive bit in DATA header (`[38] = 1`) only when requester becomes sole holder (DIR_I grant or any GETM grant). Set to 0 on shared GETS grants | Directory issuing DATA flit | Header bit `[38]` set to 1 or 0 | Granting exclusive on shared copy violates A1.3 (no E/M alongside S) | WP §3.3 Rule 9, SLICE_16_1 |
| 12 | Memory Hierarchy | L2 Per-Line Word Formatting | Tag array stores `{valid, address tag, dirty}` (23 bits at 2x2, 21 bits at 4x4). `valid` and `dirty` are excluded from tag compare | Address tag bits and dirty/valid flags | Stored 23b/21b tag word; hit/miss signal | Aliasing address 0x0 caught by A6.x if valid missing; stale data if dirty dropped | WP §3.6, SPEC_SHEET §6 |
| 13 | Packet Format | DATAFWD Dirty Indication | Inbound `DATAFWD` header bit `[39]` carries dirty status, set iff owner held line in M. Directory writes data to bank and sets bank dirty bit | Owner MESI state | Header bit `[39]` asserted on DATAFWD | Silently dropping dirty status causes tap incoherence; caught by A6.x | WP §3.8, SLICE_16_1 §1.5 |
| 14 | L2 Eviction | DIR_I Victim Write-Back to Tap | When L2 line in DIR_I with dirty bank bit is replaced during `DIR_EVICT`, it enters `WRITE_BACK` sub-state to flush data to memory tap | L2 victim selection during pending fill | 512-bit write-back to memory tap | Dropping dirty line without write-back caught by SVA A6.x (data integrity) | WP §3.3, Appendix B (N4) |
| 15 | Protocol | Receptivity for Other Lines (Premise R) | L1 with an outstanding miss continues to accept and service `INV`, `DATA`, `INVACK`, and `FWD` traffic for other lines immediately | Network packets arriving on NIC RX | Responses/acknowledgements dispatched | Blocking other-line traffic causes protocol deadlock; caught by A3.x, A7.x | WP §3.3 Rule 6, WP §4.6 |
| 16 | Race Resolution | Same-Line Invalidation Abort | When L1 in `IS_D`, `IM_D`, or `SM_D` receives `INV` for the same line as its pending miss, it aborts the miss, invalidates copy, sends `INVACK`, and re-issues | Inbound `INV` for line matching pending miss | Immediate `INVACK` on VC2; local miss aborted | Deferring INV causes fatal deadlock in `DIR_INV_WAIT`; caught by A3.x, A7.x | Ruling B6, WP §3.3 Rule 6 |
| 17 | Protocol | Directory Receive Path Per-VC FIFO Ordering | Directory controller maintains 4 independent RX queues (one per VC) popped with priority `RESP > INV > FWD > REQ`. Responses never blocked behind requests | Inbound flits from NIC RX path | Flits popped into directory controller | Single arrival queue deadlocks on concurrent upgrade; caught by SVA A4.x, Invariant I4 | Ruling B7, WP §3.5, §13 row AI |
| 18 | Livelock Prevention | FIFO Request Re-issue Ordering (Lemma L2) | An aborted or declined request re-issues as a new request enqueued at the back of the directory request queue (FIFO within VC0, I4), never overtaking older requests | Aborted access re-issue | `GETM`/`GETS` injected at back of VC0 queue | Livelock / repeated ping-pong aborts prevented by Lemma L2; verified by A5.x | Ruling B8, WP §3.3 Rule 6, §4.6 |
| 19 | Coherence | Aborted Access Completion / Decline Rule | When directory delivers a grant for an aborted request, tile may accept (installing and sending UNBLOCK) or decline and re-issue; directory transient must always exit | Stale `DATA` grant arriving at aborted L1 | `UNBLOCK` returned on VC2 to directory | Orphan transient in directory if UNBLOCK not returned; caught by A2.7 | Ruling B7, WP §3.3 Rule 6 |
| 20 | Defensive Protocol | Defensive Invalidation & Forward Handling | L1 in state I, `EI_A`, or `MI_A` receiving `INV` or `FWD` responds with `INVACK` unconditionally. Directory absorbs late `PUTS`/`PUTM` in `DIR_FWD_WAIT` | Inbound `INV` or `FWD` in transient/invalid state | Defensive `INVACK` on VC2; directory absorbs release | Race between forward and eviction resolved without orphan transient; caught by A7.x | WP §3.3 Rule 5, Appendix A |
| 21 | Microarchitecture | Local Home Request Shortcut (Rule R1) | L1 miss on a line homed at the local tile bypasses NIC and NoC, routing directly to the local L2 bank / directory controller via intra-tile mux | Address decoded with `home == TILE_ID` | Direct transfer to local directory request queue | Routing local miss through NoC wastes credits and latency; caught by SVA A8.x | WP §3.1, §3.12 (Rule R1) |
| 22 | Replacement | Tree-PLRU Cache Replacement | 4-way L1 and 4-way L2 implement 3-bit tree-PLRU per set. On hit, way subtree becomes MRU; on miss, LRU subtree way is victim (lower-numbered on tie) | Cache access (hit or eviction) | 3-bit PLRU state updated; victim way index output | Suboptimal replacement or tie-break ambiguity; verified by functional coverage | WP §4.4, SPEC_SHEET §2 |
| 23 | Addressing | Static-NUCA Address Decomposition | Physical address partitioned into L2 tag, home tile, L2 set, L1 set, and byte offset. L1 set (`[7:6]`) and L2 set (`[10:8]`) strictly disjoint | 32-bit physical address | Tag compare fields, home tile ID, set indexes | Overlapping set bits restricts L2 reachability; caught by SVA A8.x | WP §3.6, SPEC_SHEET §6 |
| 24 | Hardware Target | 2x2 FPGA Implementation (ZedBoard) | 4 CPU corner tiles mapped to XC7Z020 FPGA. Target clock 100 MHz, LUTs <= 20,000, FFs <= 25,000, BRAM36 <= 48, DSP = 0 | 100 MHz oscillator, reset, JTAG stimulus | Operational multicore on silicon; status LEDs | Timing failure (WNS<0, WHS<0) or resource overutilization caught by Vivado STA | WP §6.1, §6.4, HLD_LLD_2x2 |

---

## Edge Cases

| # | Feature | Input / Scenario | Observed Behavior |
|---|---|---|---|
| E01 | MESI Upgrade Race | Two tiles in S concurrently issue `GETM` for the same line | Directory services the first `GETM`, enters `DIR_INV_WAIT`, and sends `INV` to all other sharers. When the second tile (in `SM_D`) receives the same-line `INV`, it **aborts** its miss, transitions to I, sends `INVACK`, and re-issues (Ruling B6). Directory receives all `INVACK`s, delivers `DATA(excl=1)`, receives `UNBLOCK`, and transitions to `DIR_M`. |
| E02 | Directory Receive Contention | `INVACK` arrives at directory behind an earlier `GETM` from another tile | Directory controller has separate per-VC receive queues and pops with priority `RESP > INV > FWD > REQ` (Ruling B7). The `INVACK` (on VC2) is popped and processed immediately, allowing `DIR_INV_WAIT` to complete without deadlocking behind the unserviced `GETM` (on VC0). |
| E03 | Repeated Upgrade Contention | Two tiles repeatedly abort each other's upgrade requests | Each re-issued request is treated as a brand-new request and enqueued at the **back** of the directory's VC0 request queue (Ruling B8, Invariant I4). The oldest pending request is never invalidated by a younger request and completes. Livelock is mathematically impossible under Lemma L2. |
| E04 | Evict-During-Forward (Clean Owner) | Owner in E receives `FWD_GETS` while concurrently evicting the line (`EI_A`) | Owner in `EI_A` sends defensive `INVACK` on VC2 (N12). The directory in `DIR_FWD_WAIT` absorbs the owner's `PUTS` from VC0, cancels the forward, serves the requester from the home bank, and sends `PUTACK` to the owner. Directory commits `DIR_S` upon receiving `UNBLOCK`. |
| E05 | Evict-During-Forward (Dirty Owner) | Owner in M receives `FWD_GETM` while concurrently evicting the line (`MI_A`) | Owner in `MI_A` sends defensive `INVACK` on VC2 (N12). The directory in `DIR_FWD_WAIT` absorbs the owner's `PUTM` (9 flits) from VC0, writes dirty data to the bank, sets the bank dirty bit, clears the old owner, sends `PUTACK`, and completes the transfer to the requester without orphan transients. |
| E06 | Conflict Eviction Under Full Set | Load miss occurs on set with all 4 ways valid and dirty (in M) | L1 releases the PLRU victim first by sending `PUTM` (9 flits) on VC0 and remains in `IS_D` (Ruling B2). It waits for `PUTACK` on VC2 before issuing `GETS` on VC0. Invariant I4 preserves source ordering at the home bank, preventing directory deadlock without requiring MSHRs. |
| E07 | Stale Grant at Aborted Requester | Directory delivers `DATA` grant for an access the requester already aborted | Aborted tile may decline the grant or accept it (Ruling B7). In either case, the tile **must return `UNBLOCK`** on VC2 so the directory transient exits. If declined, directory does not record the tile as owner. |
| E08 | Unmapped / Out-of-Bounds Address | Core or DMA attempts access to address in unmapped ranges (e.g. `0x1000_0000..0xEFFF_FFFF`) | Transaction is trapped by SVA assertion A8.1 / A8.4, which halts simulation and flags an illegal access. |
| E09 | Mesh Buffer Saturation | High injection rate across all tiles drives credit counters to zero | Downstream credit counter reaches 0. Routers refuse to transmit flits on exhausted VCs while continuing to arbitrate and advance unblocked VCs. When downstream FIFO flits are consumed, credit pulses return and traffic resumes with zero flit loss (checked by SVA A4.x and Invariant I3). |
| E10 | Starvation Under Heavy REQ Load | Continuous stream of `GETS`/`GETM` misses on VC0 threatens to starve lower-priority traffic | Fixed class priority `RESP > INV > FWD > REQ` normally prioritizes responses. If a REQ VC waits $\ge 5$ router cycles, its age counter triggers the age escape. Oldest waiting VC is granted switch access within 13 rounds (interior) or 11 rounds (corner), satisfying Premise F. |
| E11 | Address 0x0000_0000 Resident Tag Aliasing | Cache set contains an empty way alongside line at address `0x0000_0000` | Stored L2 tag word includes a dedicated `valid` bit `{valid, tag, dirty}`. Even though address 0 has all tag bits zero, an empty way has `valid = 0` and does not match the tag comparison, preventing false hits on address 0. |
| E12 | Silent Upgrade Then Eviction | Tile in E silently upgrades to M on store hit, then later evicts line | Tile is in M locally, so eviction generates `PUTM` (9 flits, carrying dirty line) to directory. Directory, which had recorded the tile in `DIR_E`, absorbs `PUTM`, writes data to bank, sets bank dirty bit, clears owner, and returns `PUTACK`, transitioning to `DIR_I` (Rule 8). |

---

## Detailed Task Verification Findings

### Task 1: Verification of Functional Requirements (FR-01 through FR-14)

Every functional requirement currently in `SRS_final.docx` was audited against normative text in `FINAL_whitepaper_v3.0.md`, `SPEC_SHEET.md`, and the Rulings:

1. **FR-01 (MESI Coherence):** PASS. Correctly mandates 4-state MESI coherence. Verified by A1.1–A1.5, A2.1–A2.7, and TC-01. However, TC-01 only references a subset of tests (#1, #3, #5, #7, #14).
2. **FR-02 (XY Routing):** PASS. Verified by SVA A8.x, Invariant I1, and TC-02. Phantom reference A13 has been fully expunged.
3. **FR-03 (Flow Control):** PASS. Depth-4 per-VC FIFOs, credit-based flow control, verified by Invariant I3, A4.x, and TC-03.
4. **FR-04 (Arbitration & Fairness):** PASS with minor caveat. Correctly derives 13 rounds ($5+3+5$) and 11 rounds ($5+3+3$). Citations list `A5.x, I2 / TC-04`. Note that Invariant `I2` is `flit.VC == class(flit.msg)` (VC allocation invariant); the fairness bound is actually SVA `A5.x` and Premise F.
5. **FR-05 (Eviction & Conflict Ordering):** PASS with minor caveat. Correctly specifies non-silent eviction (`PUTS`/`PUTM` + `PUTACK`) and Ruling B2's conflict eviction sub-step on VC0. Cites `A1.1, A1.2, A3.x / TC-05`. Ruling B2 explicitly notes that event ordering within the transient is governed by `A7.x` (FSM legality), which should be cited.
6. **FR-06 (Single-Exit Directory FSM):** PASS. Only exit event is `UNBLOCK`. Verified by A7.x, A2.7, and TC-06.
7. **FR-07 (DMA Scope):** PASS. Correctly restricted to 4x4 simulation scope; unreachable in 2x2 build. Verified by A8.4 and TC-07.
8. **FR-08 (Intra-Tile Datapath):** PASS. 512-bit intra-tile transfer for 64 B line. Verified by A6.x and TC-08.
9. **FR-09 (Forward Release):** PASS. On `FWD_GETS`, E/M→S and `DATAFWD`; on `FWD_GETM`, E/M→I and `DATAFWD`. No `PUTS`/`PUTM`. Verified by A1.3, A2.2, A2.6, and TC-09.
10. **FR-10 (DATA Exclusive Bit):** PASS. Exclusive bit set to 1 only when requester becomes sole holder (`DIR_I` grant or any `GETM` grant); 0 on shared grants. Verified by A1.2, A1.3, and TC-10.
11. **FR-11 (L2 Stored Word):** PASS. Correctly specifies `{valid, tag, dirty}` (23b at 2x2, 21b at 4x4); dirty excluded from tag comparison. Verified by A6.x and TC-11.
12. **FR-12 (DATAFWD Dirty Bit):** PASS. Header bit `[39]` carries dirty status iff owner held line in M. Verified by A6.x and TC-12.
13. **FR-13 (DIR_I Victim Write-Back):** PASS. Dirty victim in DIR_I takes `WRITE_BACK` sub-state to tap. Verified by A6.x and TC-13.
14. **FR-14 (Premise R Receptivity):** **PARTIAL / CRITICAL GAP.** Covers receptivity for *other* lines, but completely omits the normative requirements established by Rulings B6, B7, and B8 for the *same* line during concurrent upgrade races!

#### Missing Requirements to be Added:
- **FR-15 (Same-Line Invalidation Abort):** L1 in `IS_D`, `IM_D`, or `SM_D` receiving `INV` for the same line aborts the miss, sends `INVACK`, and re-issues (Ruling B6).
- **FR-16 (FIFO Re-issue & Bounded Progress):** Re-issued requests enter the back of the VC0 queue as new requests, guaranteeing progress under Lemma L2 (Ruling B8).
- **FR-17 (Directory Receive Path Per-VC Ordering):** Directory receive path holds 4 separate VC queues popped by `RESP > INV > FWD > REQ` (Ruling B7).
- **FR-18 (Defensive Protocol Rules):** Unconditional `INVACK` sent on `INV` or `FWD` arriving in state I, `EI_A`, or `MI_A`; directory absorbs `PUTS`/`PUTM` in `DIR_FWD_WAIT` (Rules 5, 8, N5, N12).
- **FR-19 (Inclusive Distributed L2 & Local Shortcut):** Inclusive cache hierarchy, disjoint set indexes, and Rule R1 local-miss direct path bypassing NoC.
- **FR-20 (Tree-PLRU Replacement):** 3-bit tree-PLRU policy for 4-way L1 and L2 sets.

---

### Task 2: Verification of Performance, Area, Frequency, and Interface Metrics

Cross-check between `SRS_final.docx`, `SPEC_SHEET.md`, `FINAL_whitepaper_v3.0.md`, and `HLD_LLD_2x2_FPGA.md`:

| Parameter | SRS v0.2 Value | Ground Truth Spec Value | Compliance Status | Analysis & Remediation |
|---|---|---|---|---|
| **FPGA Part Number** | ZedBoard, XC7Z020-CLG484-1 | XC7Z020-CLG484-1 | **COMPLIANT** | Matches WP §6.1. |
| **LUT Target (2x2)** | <= 20,000 (38 % of 53,200) | <= 20,000 (estimate 13,000–19,000) | **COMPLIANT** | Matches WP §6.1, LLD-F2. |
| **LUT Ceiling (2x2)** | <= 40,000 (75 %) | <= 40,000 (75 %) | **COMPLIANT** | Matches WP §6.1. |
| **FF Target / Limit** | <= 25,000 / <= 50,000 | <= 25,000 / <= 50,000 (of 106,400) | **COMPLIANT** | Matches LLD-F2. |
| **BRAM36 Target (2x2)** | <= 48 (estimate 28) | <= 48 (estimate 28) | **COMPLIANT** | Matches WP §6.1. |
| **BRAM36 Ceiling (2x2)**| <= 80 | <= 80 (of 140 available) | **COMPLIANT** | Matches WP §6.1, LLD-F2. |
| **DSP Utilization** | 0 Target / 0 Maximum | 0 Target / 0 Maximum (220 avail) | **COMPLIANT** | No multipliers inferred. |
| **Clock Frequency** | TBD (PERF-01, FPGA-01) | **100 MHz (10 ns period)** | **DEFECT / TBD GAP** | WP §6.1, §6.4 and HLD-F3 fix 100 MHz oscillator. Target must be 100 MHz, Minimum 50 MHz. |
| **Timing Closure** | WNS >= 0 (FPGA-02) | **WNS >= 0, WHS >= 0, WPWS >= 3.750 ns, TNS = 0** | **INCOMPLETE** | LLD-F3 requires full constraint set; SRS omits WHS, WPWS, and TNS. |
| **Hop Latency** | 4 cycles (PERF-03) | 4 cycles (RC, VA, SA, ST) | **COMPLIANT** | Matches WP §3.5. |
| **Line Transfer** | 9 flits (PERF-04) | 9 flits (1 header + 8 data) | **COMPLIANT** | Matches WP §3.8. |
| **Liveness Bound $T$** | 64 cyc (2x2) / 150 cyc (4x4) | 64 cycles (2x2 formal) / 150 cycles (4x4 sim) | **COMPLIANT** | Matches WP §5.3. |
| **Fairness Bound** | 13 rounds ($5+3+5$) | 13 rounds interior, 11 corner ($5+3+3$) | **COMPLIANT** | Matches Ruling B1. |
| **Flit Width** | "flit (header+body)" | **64 bits** | **VAGUE** | Specify explicit 64-bit width. |
| **FIFO Buffer Depth**| 4 flits per VC | 4 flits per VC | **COMPLIANT** | Matches WP §3.5. |
| **Credit Bus Width** | 4 bits (`credit_in/out[3:0]`)| 4 bits (initialized to 4) | **COMPLIANT** | Decision AC / WP §3.5. |

---

### Task 3: Verification of VC Mapping, Message Set, Priority Rules, and FSM States

1. **Virtual Channel Mapping:**
   - `VC0 = REQ`: GETS, GETM, PUTS, PUTM, *DMA_WRITE*
   - `VC1 = FWD`: FWD_GETS, FWD_GETM
   - `VC2 = RESP`: DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, *DMA_ACK*
   - `VC3 = INV`: INV
   - **Status:** PASS. AC-03 and Table 7.1 accurately reflect source-indexed, invariant channel assignment.
2. **Message Encodings (Appendix C):**
   - Table 7.1 in SRS lists all 14 messages (12 core + 2 gated), but omits the normative 4-bit opcodes:
     - `0000`: GETS, `0001`: GETM, `0010`: PUTS, `0011`: PUTM
     - `0100`: UNBLOCK, `0101`: INV, `0110`: INVACK, `0111`: DATA
     - `1000`: FWD_GETS, `1001`: FWD_GETM, `1010`: DATAFWD, `1011`: PUTACK
     - `1100`: DMA_WRITE, `1101`: DMA_ACK, `1110`/`1111`: Reserved
   - **Remediation:** Add 4-bit opcode column to Table 7.1.
3. **Priority Hierarchy:**
   - Fabric VC priority: Fixed class priority `RESP > INV > FWD > REQ` (`VC2 > VC3 > VC1 > VC0`).
   - Router switch arbitration: Port-granular round-robin across input ports with 5-round age escape.
   - Directory receive path: Fixed class priority `RESP > INV > FWD > REQ` across 4 per-VC queues (Ruling B7). **Currently omitted from SRS!**
4. **Deadlock Prevention Architecture:**
   - Three layers:
     1. Layer 1: Routing fabric acyclic per VC (XY dimension-order routing, turns from Y to X prohibited; VC index preserved across hops).
     2. Layer 2: Message dependency graph acyclic across VCs (feed-forward order: `VC0 (REQ) -> {VC1 (FWD), VC3 (INV)} -> VC2 (RESP)`).
     3. Layer 3: Flow control buffer management (credit flow control depth 4, Premise R receptivity, Ruling B6 same-line INV abort, Lemma L2 FIFO re-issue).
   - **Status:** Needs explicit consolidation in Section 2.3 or Section 3.
5. **FSM State Space:**
   - L1: 4 stable states (M, E, S, I) + 5 transient states (`IS_D`, `IM_D`, `SM_D`, `EI_A`, `MI_A`).
   - Directory: 4 stable states (`DIR_I`, `DIR_S`, `DIR_E`, `DIR_M`) + 4 transient states (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`, `DIR_EVICT`). Exactly saturates 3-bit field (codes `000` to `111`).
   - Single-exit rule strictly enforced (exit on `UNBLOCK`).

---

### Task 4: Verification of Assertion IDs and Test Plans

1. **Assertion Inventory:**
   - **42 Bound SVA:**
     - A1: MESI invariants (5): A1.1–A1.5
     - A2: Directory invariants (7): A2.1–A2.7 (with A2.2 split into A2.2a strict and A2.2b bounded lag)
     - A3: Message protocol (6): A3.1–A3.6
     - A4: Flow control (8): A4.1–A4.8
     - A5: Bounded liveness (4): A5.1–A5.4
     - A6: Data integrity (4): A6.1–A6.4
     - A7: State machine legality (4): A7.1–A7.4
     - A8: Address and routing (4): A8.1–A8.4
   - **7 Formal-Only Network Invariants:** I1 (XY path), I2 (VC=class), I3 (credit invariant), I4 (per-VC FIFO order), I5 (delivery/termination), I6 (VC preservation), I7 (inter-class edge ascent).
   - Total Property Count: **49 properties** (42 simulation-bound SVA + 7 formal-only invariants).
   - **Status:** Perfectly aligned with WP §5.2 and Appendix E.
2. **Directed Test Plan (Table 8.4):**
   - 14 rows (`TC-01` through `TC-14`) mapped to WP directed tests 1–17 and conditional tests 18–22.
   - **Gap:** Missing explicit directed test cases for Ruling B6 (same-line INV abort race), Ruling B7 (directory receive per-VC queueing without stall), and Ruling B8 (repeated upgrade contention with FIFO re-issue).
3. **FPGA Implementation Test Plan (Table 9.5):**
   - 14 rows (`FV-01` through `FV-14`) mapped to implementation slice items §16.1 through §16.14.
   - **Gap:** Implementation breakdown item §16.15 (Same-line INV abort, Ruling B6) has no corresponding validation test row in Table 9.5!
   - Rows FV-13 (TILE_ID tie-off) and FV-14 (stimulus path confirmation) lack Req IDs in the table because corresponding FRs were missing.

---

### Task 5: Verification of Signal Lists (2x2 FPGA vs 4x4 Simulation)

Audit of Section 7.2 identified major structural and technical issues:

1. **Bogus `ready` Signal:** Table 7.2 lists `port_in_ready` and `port_out_ready`. Credit-based flow control does not use `ready` handshakes; transmission is throttled solely by credit counters (`credit_in[3:0]`).
2. **Conflation of Chip Top-Level I/O vs Internal Mesh Links:**
   - In the committed 2x2 FPGA build, the 4 tiles and their inter-connecting router links are *internal* to the `fpga_top` module.
   - The actual top-level FPGA signals are:
     - `clk` (100 MHz oscillator input, 1 bit)
     - `rst_n` / `reset` (active-low push-button reset, 1 bit)
     - JTAG stimulus interface (`tck`, `tms`, `tdi`, `tdo`) or UART stimulus interface
     - Status output LEDs (`led[7:0]` for heartbeat, test pass/fail, error flags)
3. **Missing Module Interface Signals:**
   - `tile_id[1:0]` (2 bits at 2x2, 4 bits at 4x4): static hardwired tile position input.
   - `flit_in_vc[1:0]` / `flit_out_vc[1:0]`: 2-bit sideband channel selector accompanying flit streams.
   - Flit bus width should be explicitly declared as 64 bits (`[63:0]`).
4. **Memory Tap Interface:**
   - Per-tile L2 bank connection to behavioural backing store:
     - `mem_req_valid`, `mem_req_addr[31:0]`, `mem_req_type`, `mem_req_wdata[511:0]`, `mem_rsp_valid`, `mem_rsp_rdata[511:0]`.

---

### Task 6: Traceability Matrix Completeness (Section 10)

Audit of Section 10 against the IEEE 830 / ISO 29148 standard and the Student Guide:
- **Current State:** Table 10 contains only 14 rows, tracing solely `FR-01` through `FR-14`.
- **Defect:** The Student Guide explicitly dictates:
  > "Section 10 must link every ID to how you will check it... one row per requirement ID from sections 3 to 9, showing the method, test/report, and status."
- **Missing Traces:**
  - `AC-01` through `AC-05` (5 assumptions/constraints)
  - `PERF-01` through `PERF-06` (6 performance requirements)
  - `PWR-01` through `PWR-03` (3 power requirements)
  - `AREA-01` through `AREA-03` (3 area requirements)
  - `FPGA-01` through `FPGA-05b` (6 FPGA validation requirements)
  - Proposed additions `FR-15` through `FR-20` (6 new functional requirements)
- **Status:** Complete revision required to achieve 100% requirements-to-verification traceability.

---

### Task 7: Comprehensive Discrepancy, Omission, and Ambiguity Register

| Defect ID | Severity | Category | Location in SRS | Description | Authoritative Spec Ground Truth | Required Correction |
|---|---|---|---|---|---|---|
| **D01** | **Blocker** | Protocol Spec | §3 (FR-14) | Omits same-line `INV` abort mechanism during concurrent upgrade race | Ruling B6, WP §3.3 Rule 6, Lemma L1 (§4.6), §13 row AH | Add FR-15: Same-line INV aborts L1 miss in `IS_D`/`IM_D`/`SM_D`, sends `INVACK`, and re-issues |
| **D02** | **Blocker** | Protocol Spec | §2.3 / §3 / §7 | Omits directory controller per-VC receive queueing and priority popping | Ruling B7, WP §3.5, §13 row AI | Add FR-17: Directory receive path has 4 per-VC queues popped by `RESP > INV > FWD > REQ` |
| **D03** | **Blocker** | Protocol Spec | §3 | Omits FIFO request re-issue ordering and Lemma L2 progress guarantee | Ruling B8, WP §3.3 Rule 6, §4.6 Lemma L2, §13 row AJ | Add FR-16: Re-issued requests enter back of VC0 queue as new requests, bounding progress |
| **D04** | **Major** | Interface Spec | §7.2 | Lists `port_in_ready` and `port_out_ready` on router link interfaces | WP §3.5, SPEC_SHEET §3 | Remove `ready` signals; flow control is governed exclusively by credit counters |
| **D05** | **Major** | Traceability | §10 | Traceability matrix omits Sections 4, 5, 6, and 9 requirements (PERF, PWR, AREA, FPGA) | SRS Student Guide, ISO/IEC/IEEE 29148 | Expand Table 10 to trace all requirement IDs from Sections 2 through 9 |
| **D06** | **Major** | Performance | §4, §9.3 | Clock frequency listed as "TBD" (PERF-01, FPGA-01) | WP §6.1, §6.4, HLD-F3 | Replace "TBD" with Target: 100 MHz (10 ns period), Minimum: 50 MHz (20 ns period) |
| **D07** | **Major** | Interface Spec | §7.2 | Conflates top-level FPGA board I/O with internal tile router links | HLD-F2, SPEC_SHEET §3 | Split §7.2 into Top-Level FPGA I/O (clk, rst, JTAG, LEDs) and Tile Router Ports |
| **D08** | **Major** | Architecture | §3 | Omits local-home miss direct routing shortcut (Rule R1) | WP §3.1, §3.12 (Rule R1), SPEC_SHEET §2 | Add FR-19 covering inclusive cache hierarchy and Rule R1 intra-tile bypass |
| **D09** | **Minor** | Verification | §9.5 | Implementation test plan omits §16.15 (Same-line INV abort) | WORK_BREAKDOWN_16 §16.15 | Add test row FV-15 checking same-line INV abort under concurrent upgrade |
| **D10** | **Minor** | Verification | §9.5 | Table 9.5 rows FV-13 and FV-14 have empty Req IDs ("-") | SRS Student Guide | Map FV-13 to new FR-19 (address mapping/tile ID) and FV-14 to top-level stimulus |
| **D11** | **Minor** | Protocol Spec | §7.1 | Table 7.1 omits 4-bit binary opcode column for messages | WP Appendix C | Add 4-bit opcode column (`0000` to `1111`) to Table 7.1 |
| **D12** | **Minor** | Interface Spec | §7.2 | Flit bus width listed as "flit" without explicit 64-bit width; missing `flit_vc[1:0]` | WP §3.8, SPEC_SHEET §3 | Explicitly define `flit_data[63:0]` and `flit_vc[1:0]` sideband |
| **D13** | **Minor** | FPGA Spec | §9.3 | FPGA implementation targets omit WHS, WPWS, and TNS | HLD-LLD-2x2 LLD-F3 | Add WHS >= 0 ns, WPWS >= 3.750 ns, TNS = 0 ns to FPGA-02 |
| **D14** | **Minor** | Protocol Spec | §1.4 | References omit Rulings B7 and B8, and WP ledger rows AG, AH, AI, AJ | RULINGS_B7.md, RULINGS_B8.md, WP §13 | Update Reference [4] to include RULINGS_B7, RULINGS_B8, and WP ledger rows AD–AJ |
| **D15** | **Minor** | Verification | §3 (FR-04/FR-05) | FR-04 cites Invariant I2 for fairness; FR-05 omits SVA A7.x | Ruling B1, Ruling B2 | Replace I2 with Premise F / A5.x in FR-04; add A7.x to FR-05 Verified-by cell |

---

## Conclusion & Recommendations

The SRS is structurally sound and satisfies all baseline checks in `verify_srs.py`, but it has fallen behind the normative specification updates of 2026-11-07. Incorporating Rulings B6, B7, and B8 into new functional requirements (FR-15 through FR-18), expanding the Traceability Matrix to 100% coverage across all sections, removing the non-existent `ready` signals from credit flow control, fixing the FPGA clock frequency at 100 MHz, and updating the signal list will elevate the document to institutional-grade, fully auditable SRS v2.0 status.
