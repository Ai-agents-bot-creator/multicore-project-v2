# Specification Sheet — Cache-Coherent Tiled Multicore on a 2D Mesh NoC

**Sources:** `FINAL_whitepaper_v3.0.md` (WP, source of truth) and the approved `LLD_2x2_mesh.pdf`.
**Diagrams:** `diagrams/HLD_LLD_2x2_FPGA.md`, `diagrams/HLD_LLD_4x4_architecture.md` (Mermaid), rendered as `diagrams/diagrams_rendered.html` (19 diagrams). HLD/LLD only — no sequence charts/MSCs.
**Convention:** anything a spec would normally carry that the WP does not enumerate is marked **⚠ not specified in WP** and is *not* invented here. Ledger letters refer to the WP §13 cross-model adjudication ledger.

---

## 1. Configurations and derived parameters

| Quantity | Formula | N=2 (2×2) | N=4 (4×4) |
|---|---|---|---|
| TILE_COUNT | N² | 4 | 16 |
| TILE_ID_W (logical) | ⌈log₂TILE_COUNT⌉ | 2 | 4 |
| SHARER_W | TILE_COUNT | 4 | 16 |
| Directory entry used bits | `3 + TILE_ID_W + N² + 1` | 10 | 24 |
| Directory entries per bank | L2 lines = 32 | 32 | 32 |
| L1 (per tile) | 4 sets × 4 ways × 64 B | 1 KB | 1 KB |
| L2 bank (per CPU tile) | 8 sets × 4 ways × 64 B | 2 KB | 2 KB |
| L2 total | banks × 2 KB | 8 KB (4 banks) | 32 KB = 16 banks; with the DMA tile: 30 KB = 15 banks (15 CPU + 1 DMA slot — the DMA tile has no L2 bank) |

A flat full-map single-level directory is bounded at N ≤ 16: at 64 tiles the entry is 74 bits and the sharer vector binds before any other resource (WP §3.2).

## 2. Tile organisation (HLD)

CPU tile, structurally identical at every position (WP §3.1):

| # | Block | Function |
|---|---|---|
| 1 | Core / stimulus interface | load/store/flush master; **no fence or atomic opcode**; 1 outstanding miss (WP §4.6 Premise R) |
| 2 | L1 cache | private; 4×4×64 B = 1 KB; write-back write-allocate; tree-PLRU 3 b/set; MESI per line |
| 3 | L2 bank | shared, distributed; 8×4×64 B = 2 KB; one per CPU tile; write-back write-allocate |
| 4 | Directory array | separate from L2 data/tag arrays; 32 entries, one entry per L2 line |
| 5 | NIC | packetisation, class→VC assignment, credit management, TX/RX FIFOs |
| 6 | Router | single 5-port module (LOCAL, N, S, E, W); 4 stages (RC/VA/SA/ST); 4 VCs per port; unused ports tied off |
| 7 | Memory tap | behavioural backing store for this tile's home slice; connects **only** to the L2/directory controller (fills/write-backs); **not** on the NoC datapath (R4) |
| 8 | Intra-tile mux | local-vs-remote routing; an L1 miss homed locally goes **directly to the local L2/directory controller — no NIC or NoC traversal** (R1) |

DMA device tile (gated, §12): core-less two-channel DMA engine + register file + L1-lite (2×2×64 B) + NIC + router; **no L2 bank, no directory, no memory tap**.

## 3. LLD datapath (approved `LLD_2x2_mesh.pdf`)

One tile module shown (Tile 0 port usage); all tiles instantiate the identical module. 64-bit flits.

- **Datapath:** CORE → L1 → INTRA-TILE MUX → (ADDRESS DECODER: `home = addr[12:11]`, `home == TILE_ID?`) → local: DIRECTORY CONTROLLER + DTR / remote: NIC → 5-PORT XY ROUTER → mesh.
- **Directory path:** CONTROLLER + DTR (8-state FSM over the 8 state codes of §3.3; DTR sub-state held separately, §4) → BANK ARBITER (queues: local req, remote req, mem fill/WB → one serialized L2 port) → DIRECTORY ARRAY + L2 BANK → MEMORY PORT (off the NoC path).
- **Router:** RC → VA → SA → ST; 4 VCs × 4 flits/port; **credit 4 b**, wormhole; arbitration RESP > INV > FWD > REQ, age escape at 8 rounds (status: *proposed*, §9.3), round-robin per output; Local port = NIC.
- **Per-port interface (widths and fields normative; signal names illustrative):** `flit_out/in[63:0]`, `flit_out/in_vc[1:0]`, `flit_out/in_valid`, **`credit_in/out[3:0]`**.
- **Directory array block:** 32 entries × 32 b (10 b used, 22 b pad at 2×2): `V | sharers[4] | owner[2] | state[3]`.
- **L2 bank block:** TAG 32 × 23 b = `{valid, addr[31:13], addr[7:6], dirty}`; DATA 2 KB = 32 × 64 B; tree-PLRU 3 b/set. (dirty = bank copy newer than the tap, N3a; valid distinguishes an empty way from a resident line, N13 — neither participates in the tag comparison)
- **Signal names in the LLD are illustrative** — "replace with RTL names" (LLD note). RTL names: **⚠ not specified in WP**.
- The LLD footnote "Numbering is proposed; match your RTL" is **superseded** by the WP §13 item Y ruling (§5 below), which is normative.

## 4. Directory entry

**Conceptual fields (WP §3.2 parameter table):**

| Field | Width (general) | Width (4×4) | Meaning |
|---|---|---|---|
| State | 3 | 3 | 4 stable + 4 transient codes, exactly saturated |
| Owner | TILE_ID_W | 4 | tile ID of exclusive owner (valid in DIR_E, DIR_M) |
| Sharers | N² | 16 | full-map vector; bit *t* = 1 iff tile *t* holds a copy |
| Valid | 1 | 1 | entry in use |

**Physical bit layout in the 32-bit word (decision Z, adopted from the approved LLD, WP §3.2):** fields packed into the low-order used bits, high-order bits zero-padded for BRAM alignment. Field order MSB→LSB of the *used* bits: **Valid, Sharers, Owner, State** — the reverse of the parameter table (that table order is conceptual, not physical). Field bit order is LSB-first.

- **2×2 (10 used):** `[31:10]` pad, `[9]` V, `[8:5]` Sharers, `[4:3]` Owner, `[2:0]` State.
  State[0] = bit 0; Owner[0]=Y = bit 3, Owner[1]=X = bit 4; Sharers bit *t* = tile *t* (§5 numbering).
- **4×4 (24 used):** `[31:24]` pad, `[23]` V, `[22:7]` Sharers, `[6:3]` Owner, `[2:0]` State.

State codes: 000 DIR_I, 001 DIR_S, 010 DIR_E, 011 DIR_M, 100 DIR_MEM_WAIT, 101 DIR_FWD_WAIT, 110 DIR_INV_WAIT, 111 DIR_EVICT — zero encoding headroom; a future state requires entry re-layout (stated as cost, WP §3.3).

**DTR (per bank, in the L2 controller — WP §3.7):** Pending op 3 b (000 NONE, 001 GETS, 010 GETM, 011 PUT, 100 DMA; 5 used, 101–111 unused). The eviction is held in the 2-bit evict sub-state, not in pending_op — the pending fill's GETS/GETM survives the DIR_EVICT excursion (§3.3 single-exit rule). Pending requester TILE_ID_W, Evict sub-state 2 b (NONE/INV_SHARERS/RECALL_OWNER/WRITE_BACK), Evict victim (tag+set+way), Victim dirty 1 b. One outstanding transaction per bank (premise, §13 item X). If the Month-2 DMA gate fails, §3.11's "no RTL change required" implies the DMA pending-op code stays in the encoding but is never asserted — ⚠ this consequence is not stated explicitly in the WP.

## 5. Tile-ID encoding, numbering, corner ports (decisions Y + AA)

- **Encoding:** home-tile field = {X, Y} with X in the higher-order bits. 2×2: X = addr[12], Y = addr[11] → `TILE_ID[1]=X, TILE_ID[0]=Y`, TILE_ID = 2·X + Y = **addr[12:11] directly**. 4×4: X = addr[14:13], Y = addr[12:11] → TILE_ID = 4·X + Y = **addr[14:11] directly**.
- **Numbering:** T0=(0,0), T1=(0,1), T2=(1,0), T3=(1,1); T0–T15 at 4×4 in the same order. X runs west→east (X=0 = west edge); Y runs south→north (Y=0 = south edge).
- **Corner ports:** T0: N,E · T1: S,E · T2: N,W · T3: S,W (LOCAL on every tile).
- **Width:** TILE_ID_W is logical (2 at 2×2, 4 at 4×4); **8 bits physical** in the packet header at `[63:56]`/`[55:48]`, high bits reserved zero. The LLD's 2-bit `TILE_ID[1:0]` ports are correct; the WP §3.6 "(256 tiles)" claim is withdrawn — an 8-bit header allocation is a layout choice, not a scalability claim.
- **Delivery:** TILE_ID is a **static, hardwired module input**, not a register (LLD: `Global: clk, rst_n, TILE_ID[1:0] (static)`). How it is tied off at the mesh top level is ⚠ not specified in WP.

## 6. Address map (WP §3.6)

**4×4:** `[31:15]` L2 tag (17) · `[14:11]` Home (X,Y) (4) · `[10:8]` L2 set (3) · `[7:6]` L1 set (2) · `[5:0]` offset (6).
**2×2:** `[31:13]` L2 tag (19) · `[12:11]` Home (X,Y) (2) · `[10:8]` L2 set (3) · `[7:6]` L1 set (2) · `[5:0]` offset (6).

Stored tags (every line-address bit except index and constant-per-bank bits): L1 = addr[31:8] = 24 b (both configs); the L2 address tag = {addr[31:13], addr[7:6]} = 21 b at 2×2 and {addr[31:15], addr[7:6]} = 19 b at 4×4; the L2 per-line word = valid + address tag + dirty = **23 b at 2×2 and 21 b at 4×4**, where `dirty` = the bank copy is newer than the tap (N3a) and `valid` distinguishes an empty way from a resident line (N13). L1 set [7:6] and L2 set [10:8] are **disjoint** — a hard requirement: the predecessor layout (L2 at [8:6]) made 6 of 8 L2 sets unreachable per L1 set.

## 7. Coherence (MESI, WP §3.3)

**L1 stable (4):** M (only copy, dirty), E (only copy, clean), S (read-only), I.
**L1 transient (5):** IS_D, IM_D, SM_D, EI_A, MI_A (entry/exit per WP §3.3 table; SM_D exits on DATA alone — INVACKs go to the directory, never the requester).
**Directory stable:** DIR_I/S/E/M; **transient:** DIR_MEM_WAIT, DIR_FWD_WAIT, DIR_INV_WAIT, DIR_EVICT. **Single-exit rule:** all transients exit on UNBLOCK (DIR_EVICT → DIR_MEM_WAIT when the victim is fully resolved); intermediate events advance DTR sub-state only.

**Normative rules (10):** (1) PUTS carries no data; (2) no eviction is silent — S/E ⇒ PUTS, M ⇒ PUTM; (3) INV excludes the requester, exit condition `Sharers == 0`; (4) INVACK counting = idempotent bit-clearing, no counter; (5) response to INV: S/E ⇒ INVACK, M ⇒ PUTM then INVACK, I ⇒ INVACK (defensive); (6) receptivity — an L1 with an outstanding miss must service INV/DATA/INVACK/FWD for other lines immediately; (7) UNBLOCK in a stable state is a no-op; (8) a forward-initiated release is not a replacement eviction — on FWD_GETS the owner downgrades E/M→S (sends DATAFWD), on FWD_GETM E/M→I; rule 2 applies only to replacement evictions. Forward release also drives `DIR_E + PUTM → DIR_I` (owner silently upgraded to M then evicted); (9) the DATA exclusive bit is 1 only when the requester becomes the sole holder — 1 on a DIR_I grant and on every GETM grant including a forward, 0 on every GETS grant including a forward (the old owner has downgraded to S); (10) no eviction is started while a miss is outstanding — a needed eviction is deferred until the miss completes.

**Forward path (new):** DIR_E/DIR_M + GETS(other) → DIR_FWD_WAIT, FWD_GETS → owner downgrades E/M→S, directory records owner+requester as sharers (a tile that has already released the line is not recorded as a sharer — ruling B5; the sharer vector is a conservative superset of the actual holders, never a subset) → DIR_S on UNBLOCK. DIR_E/DIR_M + GETM(other) → DIR_FWD_WAIT, FWD_GETM → owner downgrades to I, directory clears old owner's sharer bit and sets Owner = requester → DIR_M on UNBLOCK. Owner-side FWD handling: E/M on FWD_GETS → S (DATAFWD clean/dirty); E/M on FWD_GETM → I (DATAFWD clean/dirty); I/EI_A/MI_A on FWD → INVACK (defensive, N5/N12). Evict-during-forward: the directory absorbs a PUTM in DIR_FWD_WAIT (it satisfies the forward — write the bank, set dirty, clear the old owner's bit, send PUTACK) and a PUTS in DIR_FWD_WAIT (it cancels the forward — the bank holds the current value, so the requester is served from the bank; send PUTACK); a defensive INVACK arriving in DIR_FWD_WAIT is a duplicate release and is ignored. The PUTS and the INVACK travel on different VCs and may arrive in either order.

**L2 bank per-line word (N3a, N13):** `{valid, tag, dirty}` — 23 b at 2×2, 21 b at 4×4 (21 b / 19 b address tag + one bit each). `dirty` = the bank copy is newer than the tap; on every bank write it is set to the dirtiness of the data written, and it is cleared on a write-back to the tap. `valid` distinguishes an empty way from a resident line, because an empty all-zero tag would otherwise alias the line at address 0x0000_0000. Neither bit participates in the tag comparison. Header bit [39] on a DATAFWD packet is the dirty indication (set iff the owner held the line in M) (N3b). `DIR_EVICT` sub-state = WRITE_BACK when the victim is DIR_I with a dirty bank line (N4).

**Load-bearing message fixes:** PUTACK (1011) exists (no orphan transients — predecessor defect F2); UNBLOCK is on VC2 (causally downstream of DATA); DATAFWD goes owner → home directory → requester (dirty lands in the bank before the DIR_M/DIR_S transition).

## 8. Message set (WP §3.3 / Appendix C)

Baseline = **12 core messages** (0000–1011); **+2 gated DMA** (1100–1101); 1110/1111 Reserved unconditionally.

| Code | Message | Direction | Class | VC | Flits | Status |
|---|---|---|---|---|---|---|
| 0000 | GETS | L1 → dir | REQ | VC0 | 1 | Baseline |
| 0001 | GETM | L1 → dir | REQ | VC0 | 1 | Baseline |
| 0010 | PUTS | L1 → dir | REQ | VC0 | 1 | Baseline |
| 0011 | PUTM | L1 → dir | REQ | VC0 | 9 | Baseline |
| 0100 | UNBLOCK | L1 → dir | RESP | VC2 | 1 | Baseline |
| 0101 | INV | dir → L1 | INV | VC3 | 1 | Baseline |
| 0110 | INVACK | L1 → dir | RESP | VC2 | 1 | Baseline |
| 0111 | DATA | dir → L1 | RESP | VC2 | 9 | Baseline |
| 1000 | FWD_GETS | dir → owner | FWD | VC1 | 1 | Baseline |
| 1001 | FWD_GETM | dir → owner | FWD | VC1 | 1 | Baseline |
| 1010 | DATAFWD | owner → dir | RESP | VC2 | 9 | Baseline |
| 1011 | PUTACK | dir → L1 | RESP | VC2 | 1 | Baseline |
| 1100 | DMA_WRITE | DMA → dir | REQ | VC0 | 9 | **Gated — not baseline (§3.11)** |
| 1101 | DMA_ACK | dir → DMA | RESP | VC2 | 1 | **Gated — not baseline (§3.11)** |
| 1110 | Reserved | — | — | — | — | Not decoded |
| 1111 | Reserved | — | — | — | — | Not decoded |

**Footnote 1 — Gated extension.** DMA_WRITE (write-with-inline-data, no fetch-before-write) and DMA_ACK (completion to the DMA register file) are defined only if the Month-2 gate is passed (Week 8: DMA channel FSM, register map, and one end-to-end transfer passing simulation). **No DMA_READ message exists** — a DMA read is a GETS issued by the DMA tile's L1-lite; the source tile ID distinguishes it (§3.3). If the gate is missed: both rows become Reserved, they are not reassigned, and no RTL change is required. The baseline LLD correctly omits the DMA tile and these two messages; if the gate passes, the LLD must be extended and re-reviewed.

**Footnote 2 — Baseline set.** Baseline message set = **12** (codes 0000–1011). Codes 1100–1101 are defined-but-gated, not baseline; 1110–1111 are Reserved unconditionally.

**Footnote 3 — Coverage cross (see §13).** The 238-term cross uses 14 active messages **only when the gate passes**; on the baseline it is (9 L1 + 8 dir states) × 12 messages = **204 terms**. Both numbers are stated so neither configuration is silently wrong.

## 9. Network-on-Chip (WP §3.5)

### 9.1 Topology and routing
2D mesh; one 5-port router module per tile; unused edge/corner ports tied off and pruned by synthesis. XY deterministic routing (X first, then Y). VC index assigned at the source NIC from message class and **never changed by any router** (VC preservation — load-bearing premise for the §4.6 deadlock argument).

### 9.2 Flow control (decision AC)
Credit-based per VC: **4-bit credit counter** initialised to the downstream FIFO depth of 4. (3 bits is the minimal sufficient encoding for depth 4; 4 bits is used for interface regularity and headroom if depth increases; the approved LLD fixes the bus at `credit_in/out[3:0]`.) A flit is transmitted only when a credit is available; a credit returns when the downstream FIFO advances. Buffer occupancy is always ≤ depth.

### 9.3 Virtual channels and arbitration

| VC | Class | Messages | FIFO depth |
|---|---|---|---|
| VC0 | REQ | GETS, GETM, PUTS, PUTM, *DMA_WRITE (gated)* | 4 flits |
| VC1 | FWD | FWD_GETS, FWD_GETM | 4 flits |
| VC2 | RESP | DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, *DMA_ACK (gated)* | 4 flits |
| VC3 | INV | INV | 4 flits |

Arbitration (WP §3.5, two layers): **per input port** — fixed class priority **RESP > INV > FWD > REQ** plus an **age-counter escape**; **per output port** — round-robin across input ports. Age threshold: value **8 rounds is a working value, status "proposed" — not confirmed** (decision AB); to be confirmed against measured VC load at Week 10 (§12 item 8), with the chosen value and measurement recorded in §3.5. The liveness proof is parametric in the bound — a retuned value does not affect the deadlock proof. The LLD's "age escape at 8 rounds" is this same working value, not an empirical confirmation.

## 10. Packet and flit format (WP §3.8 / Appendix C)

64-bit flit; packet = one header flit + zero or more body flits.

| Bits | Field | Width | Meaning |
|---|---|---|---|
| [63:56] | Dest tile | 8 physical / TILE_ID_W logical | low TILE_ID_W bits meaningful, high bits reserved zero |
| [55:48] | Src tile | 8 physical / TILE_ID_W logical | low TILE_ID_W bits meaningful, high bits reserved zero |
| [47:44] | Msg type | 4 | §8 table |
| [43:42] | VC ID | 2 | **checked field**: must equal class(msg); asserted by NIC and formal invariant I3; never a routing input |
| [41] | Head | 1 | first flit |
| [40] | Tail | 1 | set only on single-flit packets |
| [39] | Write enable | 1 | memory/bank write indication |
| [38] | Exclusive | 1 | DATA grants exclusive ownership |
| [37:32] | Length (LEN) | 6 | total flits in packet, 1–63 |
| [31:0] | Address | 32 | line address of the transaction |

Body flit: 64 bits pure payload, no control bits; packet delimited by LEN. Control packet (GETS, GETM, PUTS, UNBLOCK, INV, INVACK, FWD_GETS, FWD_GETM, PUTACK, *DMA_ACK*) = 1 flit; cache-line packet (PUTM, DATA, DATAFWD, *DMA_WRITE*) = 9 flits (1 header + 8 × 64 B). All coherence transfers are single-cache-line granularity; multi-block DMA is future scope.

## 11. Memory model and ordering (WP §3.9, §3.10)

- Per-address ordering is guaranteed, serialised at the home directory; **cross-address ordering is not guaranteed**. No fences, atomics, or memory consistency model — coherence, not consistency.
- Backing store: per-tile behavioural memory tap — 32-bit physical address, 256 MB window at 0x0000_0000, 64 B lines, 1-cycle access, one per CPU tile serving only its home addresses, no coherence participation, not on the NoC datapath. DRAM timing/ECC/refresh/interleaving/prefetch not modelled.
- Regions: Memory 0x0000_0000–0x0FFF_FFFF · Unmapped 0x1000_0000–0xEFFF_FFFF and 0xF001_0000–0xFFFF_EEFF (A8 catches) · DMA registers 0xF000_0000–0xF000_FFFF (gated; unmapped if the DMA gate fails) · Test addresses 0xFFFF_FF00/FF04/FF08 → 0xDEADBEEF / the address / a counter.
- Bank access: single serialized port behind the bank arbiter (R2); bank first, tap on bank miss (R3); in DIR_M the owner's L1 is authoritative and the bank copy is stale.

## 12. DMA engine — gated optional extension (WP §3.11)

**Status: not part of the baseline.** Adopted only if the Month-2 gate passes (Week 8: 4×4 mesh simulated clean, pyuvm regression green, all formal safety properties discharged, one end-to-end DMA transfer passing simulation). On failure: DMA moves to §9 (future scope), codes 1100–1101 revert to Reserved and are **not reassigned**, no RTL change required.
When active: two-channel engine + register map (SRC_LO 0x00, DST_LO 0x04, LEN 0x08 — must be 64 in baseline, CTRL 0x0C, STATUS 0x10, COUNT 0x14); coherence via the existing 12 core messages + DMA_WRITE/DMA_ACK with **no new directory states**; 4×4 → 15 CPU + 1 DMA tile, 15 L2 banks = 30 KB, sharer vector exactly saturated; directed tests 18–22 conditional on the gate.

## 13. Verification coverage cross (WP Appendix D)

- **Gate passes (14 active messages):** (9 L1 states + 8 directory states) × 14 = (9+8)×14 = **238 terms**.
- **Baseline (12 messages):** (9+8)×12 = **204 terms**.

Both figures are stated because the spec carries the full code space while the baseline implementation carries only the 12-message subset. The pyuvm coverage bin list behind the numeric criteria is WP §12 item 2 (confirm after environment runs, Week 12).

## 14. Status of the six rulings (WP §13 ledger)

| Ruling | Decision | Ledger | Status |
|---|---|---|---|
| (a) Credit counter width | **4 bits** (`credit_in/out[3:0]`); WP §3.5 corrected from 3 | **AC** | Normative — in WP, LLD PDF, diagrams |
| (b) Tile-ID bit order / numbering | TILE_ID[1]=X, TILE_ID[0]=Y; T0=(0,0) T1=(0,1) T2=(1,0) T3=(1,1); corner ports T0:N,E / T1:S,E / T2:N,W / T3:S,W | **Y** | Normative — supersedes LLD's "proposed" hedge |
| (c) Directory entry physical layout | V \| Sharers \| Owner \| State packed into low-order used bits (§4) | **Z** | Normative — in WP §3.2, matches LLD |
| (d) Tile-ID field width | TILE_ID_W logical (2/4); 8 bits physical in header, high bits reserved; "(256 tiles)" withdrawn | **AA** | Normative — in WP §3.6/§3.8 |
| (e) Age-escape threshold | 8 rounds = **working value, proposed**, not confirmed (Week 10 vs measured VC load) | **AB** | Open item WP §12 #8 |
| (f) DMA messages | DMA_WRITE/DMA_ACK present but **gated**; baseline = 12; missed gate ⇒ Reserved, never reassigned | **G** | Gated (§3.11) |

## 15. ⚠ Not specified in WP (do not invent)

- **RTL signal names** — the LLD states its names are illustrative ("replace with RTL names"); the actual names are ⚠ not specified in WP.
- **Reset scheme** (assertion/deassertion discipline, synchronisation) — ⚠ not specified in WP; §6.4 declares only that the reset synchroniser is a false path. (Clock *is* specified: 100 MHz / 10 ns, §6.1 and §6.4.)
- **Credit-return latency in cycles** (WP specifies *event*: "when the downstream FIFO advances", not a cycle count) — ⚠ not specified in WP.
- **Core interface handshake** — the LLD's `req_valid/req_ready`, `req_type[1:0]` (load/store/flush) encoding and `rsp_*` handshake are LLD-defined; WP §3.1 states only "master port for load/store/flush requests". ⚠ not specified in WP.
- **Memory port structure** — the LLD's separate RD/WR channels are a micro-architectural choice; WP §3.9 specifies only the behavioural 1-cycle latency and 64 B line width. ⚠ not specified in WP.
- **Link / mesh wiring timing, PHY details** — ⚠ not specified in WP.
- **Bank arbiter service order** among local fills, remote requests and memory-tap fills — explicitly *declared* unspecified (R2; WP §12 #9).
- **Transient timeout detection mechanism** (how *T* is counted in RTL) — WP §12 #7, to be specified by Week 10.
- **Age-escape threshold empirical value** — working value 8, proposed; confirmed only by Week-10 measurement (§9.3).
- **Post-synthesis resources (LUT/FF/BRAM)** — WP §12 #5, Week 14; fit claim stays open until then.
- **pyuvm coverage bin list** — WP §12 #2, Week 12.
- **TILE_ID tie-off at the mesh top level** — the static input (§5) needs a top-level tie-off; the scheme is ⚠ not specified in WP.
- **Bank arbiter queue depth** — R2/§12 #9 leave service *order* open; queue *depth* is ⚠ not specified in WP.
- **Intra-tile mux RX routing table** — §3.1 block 8 says only "routes incoming packets by message type"; the explicit message-by-message mapping appears only in the LLD (outline derivable from §3.3 directions) — ⚠ not enumerated in WP.
- **DTR pending-op DMA code under a failed DMA gate** — §3.7 defines 5 codes including DMA; behaviour on gate failure is ⚠ not specified in WP (only implied by §3.11's no-RTL-change clause; see §4).
## 16. ⚠ Normative in the WP, pending RTL / testbench implementation

Specified in the white paper; not yet implemented in the RTL, the reference model or the testbench.

- **Forward release** (rule 8) — the owner downgrades E/M→S on FWD_GETS and E/M→I on FWD_GETM, sends DATAFWD and no PUTS/PUTM; the directory updates the sharer vector and the Owner field on the forward exit.
- **DATA exclusive bit** (rule 9) — 1 only when the requester becomes the sole holder; 0 on every GETS grant including a forward.
- **L2 per-line word** (N3a, N13) — `{valid, tag, dirty}`; valid separates an empty way from a resident line (an all-zero empty tag would otherwise alias the line at address 0x0000_0000); dirty = the bank copy is newer than the tap, set to the dirtiness of the data written on every bank write.
- **Dirty indication on DATAFWD** (N3b) — header bit [39] on a DATAFWD packet is dirty (set iff the owner held the line in M); the NIC sets it from the owner's L1 state and the directory consumes it.
- **DIR_I victim write-back** (N4) — a DIR_EVICT whose victim is DIR_I with a dirty bank line takes the WRITE_BACK sub-state; otherwise the dirty line is silently dropped.
- **Evict-during-forward** (N5, N12) — the L1 answers a FWD arriving in I, EI_A or MI_A with the defensive INVACK; the directory absorbs a PUTM in DIR_FWD_WAIT (satisfying the forward, sending PUTACK) and a PUTS in DIR_FWD_WAIT (cancelling the forward and serving the requester from the bank).
- **FPGA stimulus source** — the on-board JTAG bridge (WP §6.1); ILA/VIO debug is future scope (§9).
- **Rule 10 (deferred eviction)** — an L1 with an outstanding miss does not begin a replacement eviction; a needed eviction is deferred until the miss completes.
- **Fairness bound** — a VC is served within 13 arbitration rounds (8-round age escape + ≤5 rounds of output-port round-robin).
- **Tree-PLRU update rule** — on a hit in way w, the 3-bit tree is updated so w's subtree becomes MRU; the victim is the way in the LRU subtree, lower-numbered way on a tie.
- **NIC FIFO depth** — TX and RX FIFOs are 4 flits per VC.
- **Intra-tile datapath width** — a whole cache line moves in one 512-bit transfer; the NoC moves the same line as 9 flits.
- **Tile-ID → mesh position** — tile T at (X,Y) sits at mesh row Y, column X; TILE_ID = N·X + Y.
- **DMA path mapping** — DMA_WRITE is serviced by the directory exactly as a GETM (DIR_FWD_WAIT if owned, DIR_INV_WAIT if shared).
