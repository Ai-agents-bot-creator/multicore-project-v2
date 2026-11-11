# Specification Survey & Verification Requirements Report: Slice 16.1

**Agent:** `spec_miner_survey_1`  
**Working Directory:** `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1`  
**Date:** 2026-11-05  
**Clean-Room Status:** STRICTLY VERIFIED. Zero inspection of `tb/self_test/`, `tb/l1_dir/`, or scratch test suites. All findings extracted exclusively from authorized whitepapers, specifications, decision logs, and package definitions.

---

## Executive Summary

This report establishes the complete, authoritative specification baseline for **Implementation Slice 16.1 (Forward Release - L1 FSM + Directory Controller)** of the cache-coherent tiled multicore architecture on a 2D mesh Network-on-Chip.

The authoritative specification sources examined comprise:
1. `FINAL_whitepaper_v3.0.md` — Unified Final Specification v3.0 (normative source of truth).
2. `SLICE_16_1.md` — §16.1 Implementation Slice — Forward Release (L1 FSM + Directory Controller).
3. `WORK_BREAKDOWN_16.md` — §16 Implementation Work Breakdown & Verification Mapping.
4. `RULINGS_B1_B2_B4.md` — Protocol Adjudication Rulings B1 (fairness bound), B2 (conflict eviction), and B4 (DMA 4×4 scope).
5. `SPEC_SHEET.md` — Architectural Specification Sheet & Parameter Derivations.
6. `docs/01_DECISION_LOG.md` — Architectural Decision Records ADR-001 & Rulings.
7. `docs/04_TECH_STACK.md` — Pinned Toolchain & Environment Specifications (cocotb 2.1.0, iverilog 13.0, SymbiYosys).
8. `rtl/pkg/tile_pkg.sv` — SystemVerilog Package Definitions (widths, enums, message types, VCs, DTR encodings).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | L1 FSM | E-state Forward Release (`FWD_GETS`) | Downgrades clean owner E→S, returns clean data via `DATAFWD` to home directory. No replacement eviction triggered. | `FWD_GETS` on VC1 | `DATAFWD` (bit [39]=0) on VC2; L1 state S | Unmatched message drops or raises A7.x; timeout > T raises A5.x | `SLICE_16_1.md` §1.1, `FINAL_whitepaper_v3.0.md` §3.3 rule 8, App A |
| 2 | L1 FSM | M-state Forward Release (`FWD_GETS`) | Downgrades dirty owner M→S, returns dirty data via `DATAFWD` (bit [39]=1) to home directory. | `FWD_GETS` on VC1 | `DATAFWD` (bit [39]=1) on VC2; L1 state S | Omission leaves stale bank, caught by A6.x | `SLICE_16_1.md` §1.1, `FINAL_whitepaper_v3.0.md` §3.3 rule 8, App A |
| 3 | L1 FSM | E-state Forward Ownership Transfer (`FWD_GETM`) | Downgrades clean owner E→I, returns clean data via `DATAFWD` to home directory. | `FWD_GETM` on VC1 | `DATAFWD` (bit [39]=0) on VC2; L1 state I | Surviving E alongside M violates A1.3/A2.6 | `SLICE_16_1.md` §1.1, `FINAL_whitepaper_v3.0.md` App A |
| 4 | L1 FSM | M-state Forward Ownership Transfer (`FWD_GETM`) | Downgrades dirty owner M→I, returns dirty data via `DATAFWD` to home directory. | `FWD_GETM` on VC1 | `DATAFWD` (bit [39]=1) on VC2; L1 state I | Two M states violates A1.1/A1.4 | `SLICE_16_1.md` §1.1, `FINAL_whitepaper_v3.0.md` App A |
| 5 | L1 FSM | Defensive `INVACK` on Forward in Transient (`EI_A`, `MI_A`, `I`) | Covers evict-during-forward race. If owner initiated eviction, answers `FWD` with `INVACK` on VC2. | `FWD_GETS`/`FWD_GETM` on VC1 while in `I`, `EI_A`, `MI_A`, `IS_D`, `IM_D` | `INVACK` on VC2; L1 state unchanged | Hanging forward wedges DIR_FWD_WAIT, violates A5.x | `SLICE_16_1.md` §1.1, `FINAL_whitepaper_v3.0.md` App A, Rulings B2 |
| 6 | L1 FSM | Silent Upgrade (E → M) | Store hit in E upgrades silently to M without sending coherence messages; L1 is authoritative. | CPU Store hit | L1 state M; no message sent | Directory traffic violates zero-message rule; failure violates A1.1/A6.x | `FINAL_whitepaper_v3.0.md` §3.3, §3.4, App A, Note 1 |
| 7 | L1 FSM | Conflict Eviction Sub-step (Ruling B2) | Eviction required by pending miss releases victim before issuing miss request on VC0 (dirty→PUTM, clean→PUTS). | Miss needing way allocation | `PUTM` (9 flits) or `PUTS` (1 flit) on VC0; wait PUTACK (M/E); then issue `GETS`/`GETM` | Proactive eviction during miss deadlocks; circular wait violates A5.x | `RULINGS_B1_B2_B4.md` B2, `FINAL_whitepaper_v3.0.md` §3.3 rule 10 |
| 8 | L1 FSM | DATA Exclusive Bit Consumption | L1 installs E on `DATA(excl=1)` and S on `DATA(excl=0)`. | `DATA` packet on VC2 with bit [38] | L1 state E or S; sends `UNBLOCK` on VC2 | Wrong bit installs E alongside S, violating A1.3/A2.6 | `SLICE_16_1.md` §1.4, `FINAL_whitepaper_v3.0.md` §3.3 rule 9 |
| 9 | Directory FSM | Forward Dispatch on `GETS` (`DIR_E`, `DIR_M`) | Directory receives `GETS` from non-owner; enters `DIR_FWD_WAIT`, sets `pending_op = GETS`, sends `FWD_GETS` to owner. | `GETS` from other tile | `DIR_FWD_WAIT`, `pending_op=GETS`, `FWD_GETS` on VC1 to owner | Missing forward deadlocks requester; violates A5.x | `SLICE_16_1.md` §2.1, `FINAL_whitepaper_v3.0.md` App B |
| 10 | Directory FSM | Forward Dispatch on `GETM` (`DIR_E`, `DIR_M`) | Directory receives `GETM` from non-owner; enters `DIR_FWD_WAIT`, sets `pending_op = GETM`, sends `FWD_GETM` to owner. | `GETM` from other tile | `DIR_FWD_WAIT`, `pending_op=GETM`, `FWD_GETM` on VC1 to owner | Missing forward deadlocks requester; violates A5.x | `SLICE_16_1.md` §2.1, `FINAL_whitepaper_v3.0.md` App B |
| 11 | Directory FSM | `DATAFWD` Absorption in `DIR_FWD_WAIT` | Writes data into home bank; sets bank dirty bit from header bit [39]; sends `DATA` to requester. | `DATAFWD` (9 flits) on VC2 | Bank write; bank dirty bit updated; `DATA` on VC2 to requester; remains in `DIR_FWD_WAIT` | Changing SRAM state violates Single-Exit Rule | `SLICE_16_1.md` §2.1, `FINAL_whitepaper_v3.0.md` §3.3, App B |
| 12 | Directory FSM | Single-Exit Rule Execution | Transients (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`) exit only on `UNBLOCK`. `pending_op` selects successor. | `UNBLOCK` on VC2 | `DIR_FWD_WAIT` transitions to `DIR_S` (if `pending_op==GETS`) or `DIR_M` (if `pending_op==GETM`) | Premature transition creates race; violates A7.x | `FINAL_whitepaper_v3.0.md` §3.3, §3.7, `SLICE_16_1.md` §2.1 |
| 13 | Directory FSM | Concurrent `PUTM` Absorption in `DIR_FWD_WAIT` | Owner evicted concurrently. `PUTM` satisfies forward data obligation. Writes bank, sets dirty, sends `PUTACK`, sends `DATA`. | `PUTM` (9 flits) from owner on VC0 | Bank updated; bank dirty=1; old owner cleared; `PUTACK` to owner; `DATA` to requester; awaits `UNBLOCK` | Rejecting `PUTM` wedges owner in `MI_A`, violates A5.x | `SLICE_16_1.md` §2.1, `FINAL_whitepaper_v3.0.md` App B (N12) |
| 14 | Directory FSM | Concurrent `PUTS` Absorption in `DIR_FWD_WAIT` | Clean owner evicted concurrently. Cancels forward; bank holds current clean data; serves requester from bank; sends `PUTACK`. | `PUTS` (1 flit) from owner on VC0 | Old owner cleared; `PUTACK` to owner; `DATA(excl=0)` to requester; awaits `UNBLOCK` | Wedges owner in `EI_A`, violates A5.x | `SLICE_16_1.md` §2.1, `FINAL_whitepaper_v3.0.md` App B (N12) |
| 15 | Directory FSM | Defensive `INVACK` Absorption in `DIR_FWD_WAIT` | Duplicate release notification from owner already evicting. Ignored without state change. | `INVACK` on VC2 from owner | No state change; continues waiting for `PUTS`/`PUTM` or `UNBLOCK` | Treating as error or state exit violates A7.x/A2.7 | `SLICE_16_1.md` §2.1, `FINAL_whitepaper_v3.0.md` App B (N12) |
| 16 | Directory FSM | Silent Upgrade Eviction (`DIR_E + PUTM`) | Owner in E silently upgraded to M and evicts: writes dirty data to bank, clears owner, sends `PUTACK`, transitions to `DIR_I`. | `PUTM` on VC0 while in `DIR_E` | Bank updated; bank dirty=1; owner cleared; `PUTACK` on VC2; next state `DIR_I` | Rejecting `PUTM` drops dirty line or wedges L1 | `SLICE_16_1.md` §2.1, `FINAL_whitepaper_v3.0.md` App B, §3.4 |
| 17 | Directory FSM | DATA Exclusive Bit Generation | Sets bit [38] on `DATA`: excl=1 for `DIR_I` grant and all `GETM` grants; excl=0 for all `GETS` grants. | Directory granting `DATA` | `DATA` header bit [38] = 0 or 1 | Wrong excl bit violates A1.3 or stalls upgrade | `SLICE_16_1.md` §2.2, `FINAL_whitepaper_v3.0.md` §3.3 rule 9 |
| 18 | Directory FSM | Deferred Sharer & Owner Commit | Sharer bits and Owner updates do NOT commit on forward dispatch; they commit strictly on exit transition via `UNBLOCK`. | `UNBLOCK` on VC2 | Commits sharers = old owner + requester (`DIR_S`) or Owner = requester (`DIR_M`) | Early commit creates transient invalid sharer state; violates A2.2 | `SLICE_16_1.md` §4 rules 1, 2, 9, 10 |
| 19 | L2 Cache / Bank | L2 Bank Per-Line Word Format | 23-bit word at 2×2 / 21-bit word at 4×4: `{valid, tag, dirty}`. `valid` separates empty way from address 0x0; `dirty` tracks memory currency. | Bank write operations | Updated `{valid, tag, dirty}` | Missing valid creates false hit at 0x0; missing dirty drops data | `FINAL_whitepaper_v3.0.md` §3.6, `WORK_BREAKDOWN_16.md` §16.3 |
| 20 | L2 Cache / Bank | `DIR_I` Dirty Victim Write-back | On L2 eviction in `DIR_EVICT`, if victim entry is `DIR_I` AND bank dirty bit is 1, take `WRITE_BACK` sub-state to tap. | Eviction selecting dirty `DIR_I` victim | Sub-state `EVICT_WRITE_BACK`; memory tap write | Omitting write-back silently corrupts memory; violates A6.x | `SLICE_16_1.md` §2.3, `WORK_BREAKDOWN_16.md` §16.5 (N4) |
| 21 | NIC & NoC | Flit Header Bit [39] Dirty Encoding | On `DATAFWD`, NIC sets bit [39]=1 iff owner was M, 0 iff owner was E. Directory consumes bit [39] to set bank dirty bit. | Owner L1 state (E vs M) | `DATAFWD` header bit [39] | Corrupted dirty bit corrupts bank dirty state | `SLICE_16_1.md` §1.5, `FINAL_whitepaper_v3.0.md` §3.8, N3b |
| 22 | Router & NoC | 13-Round Fairness Bound (Ruling B1) | Two-layer arbitration: class priority (RESP>INV>FWD>REQ) overridden by age counter ≥ 5 rounds. Bound = 5 + 3 + 5 = 13 cycles. | In-flight flits across 4 VCs | Granted flit to switch crossbar | Starvation violates Premise F and bounded liveness A5.x | `RULINGS_B1_B2_B4.md` B1, `FINAL_whitepaper_v3.0.md` §3.5 |

---

## Edge Cases

| # | Feature | Input / Condition | Observed Behavior |
|---|---------|-------------------|-------------------|
| 1 | Evict-during-forward (clean) | Tile A in `EI_A` (PUTS in flight on VC0), receives `FWD_GETS` on VC1 | Tile A sends defensive `INVACK` on VC2. Directory receives `PUTS`, cancels forward, sends `PUTACK` to Tile A, serves Tile B from bank with `DATA(excl=0)`. Directory receives `INVACK`, ignores as duplicate release. |
| 2 | Evict-during-forward (dirty) | Tile A in `MI_A` (PUTM in flight on VC0), receives `FWD_GETM` on VC1 | Tile A sends defensive `INVACK` on VC2. Directory in `DIR_FWD_WAIT` receives `PUTM` on VC0, absorbs it to satisfy forward data obligation, writes dirty data to bank, sets bank dirty=1, sends `PUTACK` to Tile A, sends `DATA(excl=1)` to Tile B. Directory receives `INVACK`, ignores. |
| 3 | Evict-during-forward message reordering | `PUTS`/`PUTM` on VC0 arrives AFTER defensive `INVACK` on VC2 | Directory in `DIR_FWD_WAIT` receives `INVACK` first: treats as duplicate release, remains in `DIR_FWD_WAIT`. Later receives `PUTS`/`PUTM`: resolves data obligation, sends `PUTACK`, sends `DATA` to requester. Safe against VC interleaving. |
| 4 | Receptivity under outstanding miss (Premise R) | Tile A has miss on Line X (`IS_D`/`IM_D`), receives `FWD_GETS` on Line Y | Tile A services `FWD_GETS` on Line Y immediately on independent snoop datapath; sends `DATAFWD` on Line Y without disturbing miss on Line X. Never stalls NoC. |
| 5 | Same-line forward during miss impossibility (Lemma L1) | Any attempt to forward Line X to Tile A while Tile A is in `IS_D`/`IM_D` for Line X | Lemma L1 proves this cannot occur: Directory blocks bank until `UNBLOCK`; INV excludes requester; forward only targets current recorded owner. |
| 6 | Silent upgrade followed by eviction | Tile A in E stores hit (E→M), then evicts before directory is notified | Sends `PUTM` (VC0, 9 flits). Directory is in `DIR_E` (believed owner was clean). Directory accepts `PUTM`, writes bank, sets dirty bit, clears owner, sends `PUTACK`, transitions to `DIR_I`. |
| 7 | Consecutive readers on shared line | Line in `DIR_E`; Tile B issues `GETS`; during resolution Tile C issues `GETS` | Directory blocks behind serialized L2 port/DTR until first forward completes and exits on `UNBLOCK` to `DIR_S`. Tile C's request is then serviced directly from bank in `DIR_S` (no forward). |
| 8 | Conflict eviction with dirty victim in set | L1 miss on Line X requires set whose 4 ways are full; PLRU victim is dirty (M) | L1 stays in `IS_D`/`IM_D`, sends `PUTM` for victim on VC0, waits for `PUTACK` on VC2. After `PUTACK`, issues `GETS`/`GETM` on VC0. Prevents circular wait deadlock on home bank. |
| 9 | Conflict eviction with clean victim in set | L1 miss on Line X requires set whose PLRU victim is clean (S or E) | Clean victim in E: sends `PUTS` on VC0, waits `PUTACK`, then issues `GETS`/`GETM`. Clean victim in S: sends `PUTS` on VC0, immediately issues `GETS`/`GETM` (S victim does not wait for PUTACK). |
| 10 | Eviction of dirty line whose directory entry is `DIR_I` | L2 bank replacement selects victim line whose directory entry is `DIR_I` and dirty bit is 1 | Directory enters `DIR_EVICT`, sub-state `EVICT_WRITE_BACK`; writes 64 B line to memory tap in 1 cycle, clears dirty bit, returns to `DIR_MEM_WAIT` to finish fill. |
| 11 | Duplicate / Spurious `UNBLOCK` in stable state | `UNBLOCK` arrives at Directory while in stable state (`DIR_S`, `DIR_M`, `DIR_E`, `DIR_I`) | Ignored as no-op; directory asserts no unmatched transaction. Does not alter state. |

---

## 1. Slice Architecture and Rules 1 Through 11

### 1.1 Scope & Microarchitectural Boundaries
Slice 16.1 unifies the **L1 MESI Controller (`l1_mesi_ctrl`)** and the **Directory Controller (`dir_ctrl`)** to implement forward release. It exercises interactions across:
- **L1 Cache:** 4 sets × 4 ways × 64 B (1 KB), tree-PLRU (3 bits/set), write-back, write-allocate.
- **L2 Bank:** 8 sets × 4 ways × 64 B (2 KB), tree-PLRU (3 bits/set), write-back, write-allocate, `{valid, tag, dirty}` per-line word (23 bits at 2×2).
- **Directory Array:** 32 entries × 32 bits (10 bits used at 2×2: `[9] Valid, [8:5] Sharers, [4:3] Owner, [2:0] State`).
- **DTR (Directory Transaction Record):** per-bank register holding `pending_op` (3 b), `pending_requester` (2 b), `evict_sub_state` (2 b), `evict_victim`, and `victim_dirty`.
- **NIC:** packetisation, 4 flits/VC TX/RX FIFOs, credit-based flow control (4-bit counter), message-to-VC mapping, DATAFWD dirty-bit injection on bit [39].
- **Router:** 5-port 2D mesh router (LOCAL, N, S, E, W), 4 stages (RC/VA/SA/ST), deterministic XY routing, VC preservation, 13-round derived fairness bound (ruling B1).

### 1.2 State Space Definition (`tile_pkg.sv` normative encodings)

#### Directory States (3-bit saturated SRAM field):
```systemverilog
typedef enum logic [2:0] {
  DIR_I         = 3'b000, // Invalid / unheld
  DIR_S         = 3'b001, // Shared by one or more tiles
  DIR_E         = 3'b010, // Exclusive clean owner
  DIR_M         = 3'b011, // Modified dirty owner
  DIR_MEM_WAIT  = 3'b100, // Awaiting bank / memory tap fill
  DIR_FWD_WAIT  = 3'b101, // Awaiting forwarded data / UNBLOCK
  DIR_INV_WAIT  = 3'b110, // Awaiting invalidation acknowledgements
  DIR_EVICT     = 3'b111  // Resolving L2 victim way
} dir_state_t;
```

#### L1 MESI States (4 stable + 5 transient):
```systemverilog
typedef enum logic [3:0] {
  L1_I    = 4'd0, // Invalid
  L1_S    = 4'd1, // Shared (clean, read-only)
  L1_E    = 4'd2, // Exclusive (clean, sole copy)
  L1_M    = 4'd3, // Modified (dirty, sole copy)
  L1_IS_D = 4'd4, // Waiting for DATA (load miss)
  L1_IM_D = 4'd5, // Waiting for DATA (store miss)
  L1_SM_D = 4'd6, // Waiting for DATA (upgrade from S)
  L1_EI_A = 4'd7, // Waiting for PUTACK (clean eviction)
  L1_MI_A = 4'd8  // Waiting for PUTACK (dirty eviction)
} l1_state_t;
```

#### Message Types and Virtual Channels:
- **VC0 (REQ, Depth 4):**
  - `MSG_GETS` (`4'b0000`, 1 flit): Request shared copy.
  - `MSG_GETM` (`4'b0001`, 1 flit): Request exclusive copy.
  - `MSG_PUTS` (`4'b0010`, 1 flit): Release clean copy (no data).
  - `MSG_PUTM` (`4'b0011`, 9 flits): Write back dirty copy (1 header + 8 body).
  - `MSG_DMA_WRITE` (`4'b1100`, 9 flits): Gated optional extension.
- **VC1 (FWD, Depth 4):**
  - `MSG_FWD_GETS` (`4'b1000`, 1 flit): Forward shared request to owner.
  - `MSG_FWD_GETM` (`4'b1001`, 1 flit): Forward exclusive request to owner.
- **VC2 (RESP, Depth 4):**
  - `MSG_UNBLOCK` (`4'b0100`, 1 flit): Line installed, release directory transient.
  - `MSG_INVACK` (`4'b0110`, 1 flit): Invalidation acknowledged.
  - `MSG_DATA` (`4'b0111`, 9 flits): Data delivery (bit [38] indicates exclusive).
  - `MSG_DATAFWD` (`4'b1010`, 9 flits): Forwarded data from owner to home directory (bit [39] indicates dirty).
  - `MSG_PUTACK` (`4'b1011`, 1 flit): Release acknowledged (exits `EI_A`/`MI_A`).
  - `MSG_DMA_ACK` (`4'b1101`, 1 flit): Gated optional extension.
- **VC3 (INV, Depth 4):**
  - `MSG_INV` (`4'b0101`, 1 flit): Invalidate / recall line.

#### Flit Header Format (64 bits):
- `[63:56]`: `dest_tile` (8 bits physical; logical width `TILE_ID_W`).
- `[55:48]`: `src_tile` (8 bits physical; logical width `TILE_ID_W`).
- `[47:44]`: `msg_type` (4 bits).
- `[43:42]`: `vc_id` (2 bits; checked field, must equal `class(msg)`).
- `[41]`: `head` (1 bit; set on first flit).
- `[40]`: `tail` (1 bit; set ONLY on single-flit packets).
- `[39]`: `write_enable` / `dirty` (on `DATAFWD`, 1 = dirty, 0 = clean).
- `[38]`: `exclusive` (on `DATA`, 1 = exclusive/M, 0 = shared/S).
- `[37:32]`: `length` (6 bits; total flits in packet: `6'd1` or `6'd9`).
- `[31:0]`: `address` (32 bits physical address).

---

### 1.3 Protocol Rules 1 Through 10 / B2 (Normative Protocol Specification)

1. **Rule 1 — PUTS carries no data:** A copy in S or E is clean by definition; home bank and memory already hold current data. `PUTS` is strictly a 1-flit control packet.
2. **Rule 2 — No eviction is silent:** An L1 evicting S or E must send `PUTS`; an L1 evicting M must send `PUTM`. Silent drops leave stale sharer bits, falsifying A2.2 and wedging `DIR_INV_WAIT`.
3. **Rule 3 — INV excludes requester:** When directory services `GETM` from tile *T* in `DIR_S`, `INV` is sent to all sharers except *T*. *T*'s sharer bit is cleared upon entering `DIR_INV_WAIT`; exit condition is `Sharers == 0`.
4. **Rule 4 — INVACK counting is bit-clearing:** Idempotent bit-clearing replaces counter logic. Prevents double-decrement from race between late `PUTS` and in-flight `INVACK`.
5. **Rule 5 — Response to INV:** S/E holder replies `INVACK`. M holder sends `PUTM` (dirty data) then `INVACK`. Invalid (I) state holder replies `INVACK` unconditionally (defensive rule covering evict-during-invalidate).
6. **Rule 6 — Receptivity (Premise R):** An L1 with an outstanding miss on line *A* must immediately accept and service `INV`/`DATA`/`INVACK`/`FWD` for other lines (*B ≠ A*) on an independent path.
7. **Rule 7 — UNBLOCK in stable state is a no-op:** Directory ignores `UNBLOCK` arriving in stable states and asserts no unmatched transaction.
8. **Rule 8 — Forward release is not replacement eviction:** When an owner downgrades on forward (`E/M→S` on `FWD_GETS`, `E/M→I` on `FWD_GETM`), it sends `DATAFWD` to the home directory and changes state without sending `PUTS`/`PUTM`.
9. **Rule 9 — DATA exclusive bit derivation:** Bit [38] is 1 only when requester becomes sole holder: set on `DIR_I` grants (GETS/GETM) and all `GETM` grants; clear (0) on all `GETS` grants including forwards.
10. **Rule 10 / Ruling B2 — Conflict vs Proactive Eviction:** Proactive evictions are deferred while a miss is outstanding. Conflict evictions (victim required by miss) are **not** deferred: L1 releases victim on VC0 before sending miss request on VC0; L1 stays in `IS_D`/`IM_D` (sub-step of miss transient, no MSHRs required).

---

### 1.4 Slice 16.1 Shadow Rules 1 Through 11 (Reference Model Specification)

These 11 rules govern cycle-by-cycle / transaction shadow updates in Slice 16.1 (`SLICE_16_1.md` §4 and `RULINGS_B1_B2_B4.md` B2):

1. **Shadow Rule 1 (FWD_GETS dispatch):** On `FWD_GETS` from `DIR_E` or `DIR_M`, old owner L1 state → S; directory state → `DIR_FWD_WAIT`; `pending_op = GETS`. Sharer bits are **deferred** until exit transition.
2. **Shadow Rule 2 (FWD_GETM dispatch):** On `FWD_GETM` from `DIR_E` or `DIR_M`, old owner L1 state → I; directory state → `DIR_FWD_WAIT`; `pending_op = GETM`. Clearing old owner and setting `Owner = requester` are **deferred** until exit transition.
3. **Shadow Rule 3 (Clean DATAFWD arrival):** On `DATAFWD` with bit [39]=0: home bank data written; bank dirty bit = 0; no L1 state change on requester yet (requester waits for `DATA`).
4. **Shadow Rule 4 (Dirty DATAFWD arrival):** On `DATAFWD` with bit [39]=1: home bank data written; bank dirty bit = 1; no L1 state change on requester yet (requester waits for `DATA`).
5. **Shadow Rule 5 (Shared DATA installation):** On `DATA` to requester with `excl = 0`: requester installs line in S and issues `UNBLOCK` (VC2).
6. **Shadow Rule 6 (Exclusive DATA installation):** On `DATA` to requester with `excl = 1`: requester installs line in M and issues `UNBLOCK` (VC2).
7. **Shadow Rule 7 (Concurrent PUTM absorption):** On `PUTM` arriving in `DIR_FWD_WAIT`: bank data written; bank dirty bit = 1; old owner's sharer bit cleared; `PUTACK` sent; for `pending_op = GETM`, `Owner = requester` committed here.
8. **Shadow Rule 8 (Concurrent PUTS absorption):** On `PUTS` arriving in `DIR_FWD_WAIT`: bank untouched (already holds clean data); old owner's sharer bit cleared; `PUTACK` sent; requester served from bank.
9. **Shadow Rule 9 (UNBLOCK resolution for GETS):** On `UNBLOCK` with `pending_op = GETS`: directory state → `DIR_S`; **sharer bits for old owner + requester committed** (Shadow Rule 1 deferral resolves).
10. **Shadow Rule 10 (UNBLOCK resolution for GETM):** On `UNBLOCK` with `pending_op = GETM`: directory state → `DIR_M`; **`Owner = requester` committed** (Shadow Rule 2 deferral resolves).
11. **Shadow Rule 11 (L1 conflict victim release):** On victim release (`PUTM` for M, `PUTS` for S/E): victim L1 state → I (after `PUTACK` for M); home bank dirty bit set on `PUTM`; victim sharer bit cleared by directory (`DIR_E + PUTM` row); requester miss issued only afterwards on VC0.

---

## 2. Directed Test Suite Specifications (F1 Through F9)

| Test ID | Test Name | Initial State (L1 / Dir) | Stimulus / Sequence of Transactions | Expected DUT Responses & Message Flow | Final State (L1 / Dir / Bank) | Test Intent & Spec Clause |
|---|---|---|---|---|---|---|
| **F1** | Forward, Clean Owner | Tile A: `E`<br>Tile B: `I`<br>Dir: `DIR_E` (Owner: A) | 1. Tile B issues `GETS` on VC0.<br>2. Dir dispatches `FWD_GETS` on VC1 to Tile A.<br>3. Tile A downgrades E→S, replies `DATAFWD` (clean, bit [39]=0) on VC2 to Dir.<br>4. Dir writes bank (dirty=0), sends `DATA(excl=0)` on VC2 to Tile B.<br>5. Tile B installs S, replies `UNBLOCK` on VC2 to Dir. | - `FWD_GETS` (VC1, 1 flit) to Tile A.<br>- `DATAFWD` (VC2, 9 flits, bit [39]=0) to Dir.<br>- `DATA` (VC2, 9 flits, bit [38]=0) to Tile B.<br>- `UNBLOCK` (VC2, 1 flit) to Dir. | Tile A: `S`<br>Tile B: `S`<br>Dir: `DIR_S`<br>Sharers: `{A, B}`<br>Bank dirty: 0 | Verify clean owner forward release, E→S downgrade, bank write, non-exclusive grant, sharer accumulation. (§16.1, Rule 8, Rule 9) |
| **F2** | Forward, Dirty Owner | Tile A: `M`<br>Tile B: `I`<br>Dir: `DIR_M` (Owner: A) | 1. Tile B issues `GETM` on VC0.<br>2. Dir dispatches `FWD_GETM` on VC1 to Tile A.<br>3. Tile A downgrades M→I, replies `DATAFWD` (dirty, bit [39]=1) on VC2 to Dir.<br>4. Dir writes bank (dirty=1), sends `DATA(excl=1)` on VC2 to Tile B.<br>5. Tile B installs M, replies `UNBLOCK` on VC2 to Dir. | - `FWD_GETM` (VC1, 1 flit) to Tile A.<br>- `DATAFWD` (VC2, 9 flits, bit [39]=1) to Dir.<br>- `DATA` (VC2, 9 flits, bit [38]=1) to Tile B.<br>- `UNBLOCK` (VC2, 1 flit) to Dir. | Tile A: `I`<br>Tile B: `M`<br>Dir: `DIR_M`<br>Owner: B<br>Sharers: `{B}`<br>Bank dirty: 1 | Verify dirty owner forward release, M→I downgrade, bank dirty bit set from header bit [39], ownership transfer to Tile B. (§16.1, §16.4, N3b) |
| **F3** | Forward, GETS from DIR_M | Tile A: `M`<br>Tile B: `I`<br>Dir: `DIR_M` (Owner: A) | 1. Tile B issues `GETS` on VC0.<br>2. Dir dispatches `FWD_GETS` on VC1 to Tile A.<br>3. Tile A downgrades M→S, replies `DATAFWD` (dirty, bit [39]=1) on VC2 to Dir.<br>4. Dir writes dirty data to bank (dirty=1), sends `DATA(excl=0)` on VC2 to Tile B.<br>5. Tile B installs S, replies `UNBLOCK` on VC2 to Dir. | - `FWD_GETS` (VC1, 1 flit) to Tile A.<br>- `DATAFWD` (VC2, 9 flits, bit [39]=1) to Dir.<br>- `DATA` (VC2, 9 flits, bit [38]=0) to Tile B.<br>- `UNBLOCK` (VC2, 1 flit) to Dir. | Tile A: `S`<br>Tile B: `S`<br>Dir: `DIR_S`<br>Sharers: `{A, B}`<br>Bank dirty: 1 | Verify dirty owner downgraded to shared S copy, bank refreshed with dirty line before transition to `DIR_S`. (§16.1, §3.4) |
| **F4** | Forward, GETM from DIR_E | Tile A: `E`<br>Tile B: `I`<br>Dir: `DIR_E` (Owner: A) | 1. Tile B issues `GETM` on VC0.<br>2. Dir dispatches `FWD_GETM` on VC1 to Tile A.<br>3. Tile A downgrades E→I, replies `DATAFWD` (clean, bit [39]=0) on VC2 to Dir.<br>4. Dir writes bank (dirty=0), sends `DATA(excl=1)` on VC2 to Tile B.<br>5. Tile B installs M, replies `UNBLOCK` on VC2 to Dir. | - `FWD_GETM` (VC1, 1 flit) to Tile A.<br>- `DATAFWD` (VC2, 9 flits, bit [39]=0) to Dir.<br>- `DATA` (VC2, 9 flits, bit [38]=1) to Tile B.<br>- `UNBLOCK` (VC2, 1 flit) to Dir. | Tile A: `I`<br>Tile B: `M`<br>Dir: `DIR_M`<br>Owner: B<br>Sharers: `{B}`<br>Bank dirty: 0 | Verify clean owner invalidation upon `GETM`, ownership transfer with clean bank data, exclusive grant to requester. (§16.1, App B) |
| **F5** | Silent Upgrade then Eviction | Tile A: `E`<br>Dir: `DIR_E` (Owner: A) | 1. Tile A executes store hit: transitions E→M silently locally (no message).<br>2. Tile A evicts: enters `MI_A`, sends `PUTM` (VC0, 9 flits) to Dir.<br>3. Dir in `DIR_E` receives `PUTM`: writes dirty data to bank (dirty=1), clears Owner/Sharers, sends `PUTACK` (VC2, 1 flit) to Tile A.<br>4. Tile A receives `PUTACK`: transitions `MI_A`→`I`. | - `PUTM` (VC0, 9 flits) from Tile A.<br>- Home bank write, dirty bit set.<br>- `PUTACK` (VC2, 1 flit) from Dir to Tile A.<br>- Dir transitions to `DIR_I`. | Tile A: `I`<br>Dir: `DIR_I`<br>Sharers: 0<br>Valid: 0<br>Bank dirty: 1 | Verify silent E→M upgrade followed by dirty eviction handling in directory (`DIR_E \| PUTM` row). Prevents orphan transients. (App B note 1, §16.1) |
| **F6** | Evict-During-Forward (Clean Owner) | Tile A: `E`<br>Tile B: `I`<br>Dir: `DIR_E` (Owner: A) | 1. Tile B issues `GETS` on VC0; Dir enters `DIR_FWD_WAIT`, sends `FWD_GETS` (VC1).<br>2. Concurrently, Tile A evicts: sends `PUTS` (VC0, 1 flit), enters `EI_A`.<br>3. Tile A receives `FWD_GETS` in `EI_A`: sends defensive `INVACK` (VC2).<br>4. Dir receives `PUTS`: cancels forward, sends `PUTACK` (VC2) to Tile A, serves Tile B from bank with `DATA(excl=0)`.<br>5. Dir receives `INVACK`: ignores as duplicate release.<br>6. Tile A receives `PUTACK` → `I`. Tile B receives `DATA` → installs S, sends `UNBLOCK` → Dir enters `DIR_S`. | - `PUTS` on VC0 absorbed in `DIR_FWD_WAIT`.<br>- `PUTACK` (VC2) to Tile A.<br>- `DATA(excl=0)` (VC2) to Tile B from bank.<br>- Defensive `INVACK` on VC2 ignored.<br>- `UNBLOCK` (VC2) from Tile B. | Tile A: `I`<br>Tile B: `S`<br>Dir: `DIR_S`<br>Sharers: `{B}`<br>Bank dirty: 0 | Verify race resolution when clean owner concurrently evicts: defensive `INVACK` handling, forward cancellation, bank serving, and `PUTACK` handshake. (§16.6, N5, N12) |
| **F7** | Evict-During-Forward (Dirty Owner) | Tile A: `M`<br>Tile B: `I`<br>Dir: `DIR_M` (Owner: A) | 1. Tile B issues `GETM` on VC0; Dir enters `DIR_FWD_WAIT`, sends `FWD_GETM` (VC1).<br>2. Concurrently, Tile A evicts: sends `PUTM` (VC0, 9 flits), enters `MI_A`.<br>3. Tile A receives `FWD_GETM` in `MI_A`: sends defensive `INVACK` (VC2).<br>4. Dir receives `PUTM`: satisfies forward data obligation! Writes bank (dirty=1), clears Tile A, sets Owner=Tile B, sends `PUTACK` (VC2) to Tile A, sends `DATA(excl=1)` (VC2) to Tile B.<br>5. Dir receives `INVACK`: ignores.<br>6. Tile A receives `PUTACK` → `I`. Tile B receives `DATA` → installs M, sends `UNBLOCK` → Dir enters `DIR_M`. | - `PUTM` on VC0 absorbed in `DIR_FWD_WAIT`.<br>- `PUTACK` (VC2) to Tile A.<br>- `DATA(excl=1)` (VC2) to Tile B with `PUTM` data.<br>- Defensive `INVACK` ignored.<br>- `UNBLOCK` (VC2) from Tile B. | Tile A: `I`<br>Tile B: `M`<br>Dir: `DIR_M`<br>Owner: B<br>Sharers: `{B}`<br>Bank dirty: 1 | Verify race resolution when dirty owner concurrently evicts: `PUTM` absorption satisfying forward data obligation, clean release of owner, exclusive grant to requester. (§16.6, N5, N12) |
| **F8** | Exclusive-Bit Correctness | Variable across sub-cases | Sub-case A: Forward of `GETS` grants `excl = 0` (requester installs S).<br>Sub-case B: Forward of `GETM` grants `excl = 1` (requester installs M).<br>Sub-case C: Clean grant from `DIR_I` on `GETS` grants `excl = 1` (requester installs E).<br>Sub-case D: Subsequent `GETS` to `DIR_S` grants `excl = 0` (requester installs S). | Header bit [38] on `DATA` matches exact sole-holder rule: 1 iff requester becomes sole holder, 0 otherwise. | Requester MESI state matches: E for excl=1 on GETS, M for excl=1 on GETM, S for excl=0. | Verify bit [38] generation logic in `dir_ctrl` and consumption in `l1_mesi_ctrl`. Guard against placing E copy alongside S copy. (§16.2, Rule 9, A1.3, A2.6) |
| **F9** | Formal Safety & Bounded Liveness on Forward Path | 2×2 configuration, unconstrained legal stimulus | Formal model checking (SymbiYosys `sby`, BMC K=64) verifying properties A1.1, A1.3, A2.2, A2.6, A7.x, A5.x across all forward interleavings and evictions. | Solver proves zero counterexamples to safety invariants and bounded liveness (T=64 cycles) under Premise F. | Proved PASS at K=64 depth. | Prove absence of protocol deadlocks, orphan transients, or MESI invariant violations on forward paths. (§5.2, §5.3, §16.1) |

---

## 3. Shadow Reference Model Specifications

### 3.1 Model Architecture & State Representation
The Python shadow reference model must maintain an independent, transaction-level representation of the multicore cache hierarchy:

1. **Per-Tile L1 Cache State:**
   - `l1_state[tile][set][way]` $\in \{I, S, E, M\}$
   - `l1_transient[tile]` $\in \{NONE, IS\_D, IM\_D, SM\_D, EI\_A, MI\_A\}$
   - `l1_tag[tile][set][way]` (24-bit line tag)
   - `l1_data[tile][set][way]` (512-bit cache line)
   - `l1_plru[tile][set]` (3-bit tree-PLRU)

2. **Per-Bank L2 Cache State:**
   - `l2_valid[bank][set][way]` (1-bit valid flag)
   - `l2_dirty[bank][set][way]` (1-bit dirty flag)
   - `l2_tag[bank][set][way]` (21-bit address tag `{addr[31:13], addr[7:6]}` at 2×2)
   - `l2_data[bank][set][way]` (512-bit cache line)
   - `l2_plru[bank][set]` (3-bit tree-PLRU)

3. **Per-Bank Directory State:**
   - `dir_state[bank][entry]` $\in \{DIR\_I, DIR\_S, DIR\_E, DIR\_M, DIR\_MEM\_WAIT, DIR\_FWD\_WAIT, DIR\_INV\_WAIT, DIR\_EVICT\}$
   - `dir_owner[bank][entry]` (tile ID, 2 bits at 2×2)
   - `dir_sharers[bank][entry]` (full-map bitmask, 4 bits at 2×2)
   - `dir_valid[bank][entry]` (1-bit valid flag)

4. **Per-Bank DTR State:**
   - `dtr_pending_op[bank]` $\in \{NONE, GETS, GETM, PUT, DMA\}$
   - `dtr_pending_requester[bank]` (tile ID)
   - `dtr_evict_sub_state[bank]` $\in \{NONE, INV\_SHARERS, RECALL\_OWNER, WRITE\_BACK\}$
   - `dtr_evict_victim[bank]` (tag + set + way)
   - `dtr_victim_dirty[bank]` (1 bit)

5. **Memory Tap & Transaction Tracking:**
   - `mem_tap[address]` (backing store 512-bit line map, authoritative only when line is not bank-resident)
   - `in_flight_transactions`: map of active transactions to verify bounded round-trip latency $T \le 64$ cycles.

### 3.2 Cycle-by-Cycle / Step Comparison Protocol
At every step where the DUT completes a phase or receives/transmits a coherence packet:
- **L1 Inspection:** Compare `dut.l1_state`, `dut.l1_tag`, and `dut.l1_data` against reference model.
- **Directory Inspection:** Compare `dut.dir_state`, `dut.dir_owner`, and `dut.dir_sharers` against reference model.
- **L2 Bank Inspection:** Compare `dut.l2_valid`, `dut.l2_dirty`, and `dut.l2_data` against reference model.
- **Scoreboard Reporting:** Output structured failure if any field mismatches:
  `[SCOREBOARD MISMATCH] Cycle: <C> | Entity: Tile <T> / Bank <B> | Field: <Field> | Expected: <Ref> | Actual: <DUT>`

---

## 4. Mutation Testing Matrix & Verification Expectations

To guarantee that the clean-room acceptance suite (`tb_acceptance/`) is sensitive to specification violations, the following ten mutation classes are derived directly from the normative clauses:

| Mutation ID | Target Module / Clause | Fault Injected (Mutation Description) | Expected Positive (Baseline) | Expected Neg 1 (Directed F-Test) | Expected Neg 2 (Formal BMC / SVA) | Spec Clause Cited |
|---|---|---|---|---|---|---|
| **MUT-01** | `l1_mesi_ctrl`<br>§1.1, Rule 8 | **Downgrade Omission on FWD_GETS:** Owner in E or M receiving `FWD_GETS` sends data but remains in E or M (fails to downgrade to S). | PASS (clean downgrade to S) | **FAIL** in F1 / F3 (Scoreboard flags Tile A state mismatch: expected S, actual E/M) | **FAIL** (SVA A1.3 violated: S copy alongside E/M copy; A1.1 if two M) | `FINAL_whitepaper_v3.0.md` §3.3 rule 8; `SLICE_16_1.md` §1.1 |
| **MUT-02** | `dir_ctrl`<br>§2.2, Rule 9 | **Exclusive Bit Inversion on Forward:** Directory sets header bit [38]=1 (`excl=1`) on `DATA` packet following `FWD_GETS`. | PASS (requester installs S on excl=0) | **FAIL** in F1 / F3 / F8 (Scoreboard flags requester state mismatch: expected S, actual E/M) | **FAIL** (SVA A1.3 / A2.6 violated: requester in E while old owner in S) | `FINAL_whitepaper_v3.0.md` §3.3 rule 9; `SLICE_16_1.md` §2.2 |
| **MUT-03** | `nic` / `dir_ctrl`<br>§1.5, N3b | **DATAFWD Dirty Bit Dropped:** Owner in M sends `DATAFWD` with header bit [39]=0 instead of 1; directory clears bank dirty bit. | PASS (bank marked dirty, tap updated on dirty eviction) | **FAIL** in F2 / F3 (Scoreboard flags bank dirty bit mismatch; subsequent tap read stale) | **FAIL** (SVA A6.x data currency violation upon eviction without write-back) | `FINAL_whitepaper_v3.0.md` §3.8; `SLICE_16_1.md` §1.5 |
| **MUT-04** | `dir_ctrl`<br>§2.1, App B | **Silent Upgrade PUTM Rejected:** Directory in `DIR_E` drops or asserts on incoming `PUTM` from owner instead of transitioning to `DIR_I`. | PASS (`PUTM` absorbed, `PUTACK` sent, transitions to `DIR_I`) | **FAIL** in F5 (Tile A hangs in `MI_A` waiting for `PUTACK`; test times out) | **FAIL** (SVA A7.x undefined transition; SVA A5.x orphan transient timeout) | `FINAL_whitepaper_v3.0.md` App B note 1; `SLICE_16_1.md` §2.1 |
| **MUT-05** | `dir_ctrl`<br>§4, App B | **Premature Sharer Commit:** Directory in `DIR_E`/`DIR_M` commits requester into sharers vector upon issuing `FWD_GETS` instead of awaiting `UNBLOCK`. | PASS (sharers vector updated strictly on `UNBLOCK`) | **FAIL** in F1 / F6 (Scoreboard flags sharers vector mismatch during `DIR_FWD_WAIT`) | **FAIL** (SVA A2.2 sharer vector inaccuracy during transient window) | `SLICE_16_1.md` §4 rule 1, 9; `FINAL_whitepaper_v3.0.md` App B |
| **MUT-06** | `l1_mesi_ctrl`<br>§1.1, N12 | **Defensive INVACK Omitted:** L1 in `EI_A` or `MI_A` drops incoming `FWD_GETS`/`FWD_GETM` without returning defensive `INVACK`. | PASS (defensive `INVACK` on VC2 returned immediately) | **FAIL** in F6 / F7 (Testbench protocol monitor flags unacknowledged forward) | **FAIL** (SVA A3.1 unserviced request; SVA A5.x bounded liveness) | `FINAL_whitepaper_v3.0.md` App A, §3.3 rule 5; `SLICE_16_1.md` §1.1 |
| **MUT-07** | `dir_ctrl`<br>§2.1, N12 | **Evict-During-Forward Absorption Missing:** Directory in `DIR_FWD_WAIT` rejects incoming `PUTS` or `PUTM` on VC0 from owner. | PASS (directory absorbs `PUTS`/`PUTM`, releases owner with `PUTACK`) | **FAIL** in F6 / F7 (Owner hangs in `EI_A`/`MI_A`; timeout) | **FAIL** (SVA A5.x orphan transient; SVA A7.x undefined transition) | `SLICE_16_1.md` §2.1; `FINAL_whitepaper_v3.0.md` App B |
| **MUT-08** | `dir_ctrl`<br>§2.1, §3.3 | **Single-Exit Rule Violation:** Directory transitions SRAM state field from `DIR_FWD_WAIT` to `DIR_S`/`DIR_M` immediately upon receiving `DATAFWD`. | PASS (SRAM state exits ONLY on `UNBLOCK`) | **FAIL** in F1 / F2 (Scoreboard detects premature state exit before requester receives DATA) | **FAIL** (SVA A7.x single-exit rule; A2.7 transient well-formedness) | `FINAL_whitepaper_v3.0.md` §3.3; `SLICE_16_1.md` §2.1 |
| **MUT-09** | `l1_mesi_ctrl`<br>Ruling B2 | **Conflict Eviction Ordering Inversion:** L1 issues `GETS`/`GETM` before dirty PLRU victim is released via `PUTM` and acknowledged by `PUTACK`. | PASS (PLRU victim released and acked before miss request issued on VC0) | **FAIL** in conflict eviction directed test (Scoreboard flags packet order violation on VC0) | **FAIL** (Deadlock on home bank; SVA A5.x bounded liveness timeout) | `RULINGS_B1_B2_B4.md` B2; `FINAL_whitepaper_v3.0.md` §3.3 rule 10 |
| **MUT-10** | `dir_ctrl`<br>§2.3, N4 | **DIR_I Dirty Victim Write-Back Omitted:** When an L2 eviction selects a `DIR_I` victim with `dirty == 1`, directory skips `WRITE_BACK` sub-state. | PASS (directory transitions to `WRITE_BACK`, writing line to memory tap) | **FAIL** in L2 eviction test (Subsequent memory tap read returns stale data; scoreboard mismatch) | **FAIL** (SVA A6.x data integrity violation: bank dirty line dropped silently) | `SLICE_16_1.md` §2.3; `WORK_BREAKDOWN_16.md` §16.5 |

---

## Conclusion & Handover

All requirements for Slice 16.1 specification mining have been fulfilled:
1. Every state transition, directory rule, and package parameter has been extracted directly from authoritative white papers and rulings without any reliance on restricted test files.
2. Directed tests F1 through F9 are fully specified with initial states, multi-step transaction traces, expected message packets, and final assertions.
3. Reference model shadow rules 1 through 11 and cycle-by-cycle comparison obligations are established.
4. Ten targeted mutations with positive and negative testing criteria are defined to drive verification suite qualification.
