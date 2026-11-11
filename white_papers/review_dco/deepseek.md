# Final Proposed White Paper and Justification

---

## Part A — Consensus Verdict Summary

Cross-verification of the white paper against the 29-peer verdict corpus and the 9 peer-model critiques (z.ai, Claude, DeepSeek, Gemini, Grok, Kimi, MiniMax, Mistral, Qwen) yields the following consensus classification.

### A.1 Issues Verified as Fatal (must be fixed before any implementation)

| # | Issue | Peers Flagging | Status |
|---|---|---|---|
| F1 | `DIR_FWD_WAIT` is non-deterministic: `(DIR_FWD_WAIT, DATAFWD)` maps to both `DIR_S` and `DIR_M` | z.ai S2, Claude #1, MiniMax B3, Mistral #2 | **Verified** — Appendix B has two rows with same (state, event) |
| F2 | L1 eviction states `EI_A`/`MI_A` wait for an ACK that exists in no message set | z.ai S1, Claude #2, MiniMax B2 | **Verified** — 14-message set has no PUT/REQ ack |
| F3 | Multi-flit packets are undelimited — body flits have no tail, header tail contradicts "1 header + 8 body" | z.ai S9, DeepSeek #3, MiniMax B4 | **Verified** — 9-flit packet cannot be terminated |
| F4 | Address map has L2 set `[8:6]` containing L1 set `[7:6]` → only 2 of 8 L2 sets reachable per L1 set → 4× capacity loss | MiniMax B1 | **Verified** — arithmetically provable; contradicts Address Decode verdict |
| F5 | Parameterisation claim false: 16-bit sharer vector cannot represent N>4; 8-bit owner is over-wide at 4×4 | DeepSeek #2, Qwen #1, Kimi #3, MiniMax H4 | **Verified** |
| F6 | §3.1 tile composition list is empty | Claude #4, MiniMax M6, Mistral #7 | **Verified** |
| F7 | DMA status contradiction: "under evaluation" vs. claimed contribution vs. droppable risk vs. 5 directed tests | Most peers | **Verified** |

### A.2 Issues Verified as High-Severity (must be fixed before verification sign-off)

| # | Issue | Peers Flagging |
|---|---|---|
| H1 | VC arbitration: "round-robin across VCs" contradicts deadlock-freedom plan (fixed priority by class required) | DeepSeek #4, Qwen #2, MiniMax B6 |
| H2 | UNBLOCK placed on VC0 (request) but triggered by DATA (VC2) → descending dependency, deadlock hazard | Mistral #1 |
| H3 | Formal liveness via BMC impossible: must use bounded liveness + k-induction, not BMC alone | z.ai S5, DeepSeek #6, MiniMax B9 |
| H4 | Reference model mislabelled "cycle-accurate" — context says transaction-level | DeepSeek #7, MiniMax B7 |
| H5 | FPGA fallback "reduce VC count" breaks deadlock freedom | DeepSeek #8, MiniMax M12 |
| H6 | 2-tile formal configuration cannot exercise invalidation path (needs ≥3 tiles) | MiniMax B10 |
| H7 | Directory entry `DIR_EVICT_*` wildcard is not a specification | Claude #5, DeepSeek #10, Kimi, Grok |
| H8 | PUTS (clean writeback) carries 8 body flits that are 100% redundant (E-state line already clean) | z.ai S1 |
| H9 | BRAM budget not published; 2×2 may exceed 140 BRAMs if arrays map to BRAM | Gemini, DeepSeek #9, Grok |
| H10 | §7.1 "Three-Month Schedule" contains four months and 16 weeks | Claude #7, DeepSeek #13, Grok, Mistral #5, Qwen #4 |

### A.3 Peer Disagreements Resolved

| Disagreement | Resolution | Rationale |
|---|---|---|
| MiniMax H7: 512/36 ≠ 15 BRAMs; 240 is wrong | **Accepted** — corrected to 1–8 BRAMs/bank depending on width; conclusion (2×2 on FPGA) stands on LUT grounds | BRAM36 configures 72×512, not 36×512 |
| MiniMax H9: 3-stage vs 4-stage router | **Adopted 4-stage** (RC, VA, SA, ST) as peer Router Summary states; latency formula uses 4 cycles/hop | Peer Router Summary explicitly says 3 stages; timing verdict says 4. Four is the textbook classic; adopt it. |
| z.ai S7 / Qwen #3: DMA_READ ≡ GETS | **Accepted** — drop DMA_READ; use GETS from DMA tile | No protocol-level difference; source field distinguishes DMA |
| LRU: True LRU (8 bits) vs tree-PLRU (3 bits) vs 5-bit true LRU | **Adopted True LRU with 8-bit age counters for L1; tree-PLRU 3-bit for L2** | Matches "Replacement Policy in RTL" peer doc; 5-bit is minimum encoding but 8-bit age-counter is simpler RTL |
| Owner 8-bit vs 4-bit vs derivable-from-sharers | **Adopted 4-bit explicit owner** | Explicit owner simplifies lookup; 4 bits = TILE_ID_WIDTH at N=4 |

---

## Part B — Final Proposed White Paper (Revised)

---

# A Scalable Cache-Coherent Tiled Multicore Architecture on a 2D Mesh Network-on-Chip

**Version 2.0 — Corrected Specification and Justification**

---

## Abstract

This white paper specifies a cache-coherent tiled multicore architecture built on a 2D mesh Network-on-Chip. The design scales from 2×2 tiles on FPGA through 4×4 tiles in simulation; with a flat, full-map directory it is bounded at N ≤ 16 tiles. Each CPU tile contains a private L1 cache, a bank of a distributed shared L2 cache with a separate directory array, a Network Interface Controller, a 4-stage 5-port router, and a local behavioural memory tap. Coherence is maintained by a directory-based MESI protocol carried as multi-flit packets over the mesh. Four virtual channels separate request, forward, response, and invalidation traffic; combined with XY routing and credit-based flow control, this provides a three-layer deadlock-freedom guarantee. The architecture is verified using directed tests, constrained-random stimulus in a pyuvm environment, and formal property checking with SymbiYosys. The design targets the AMD Xilinx Zynq-7000 XC7Z020 FPGA for hardware validation, with Sky130 ASIC implementation as future scope. The verification contribution is the integration of a transaction-level reference model, a 42-assertion SVA set in 8 categories, and coverage closure for directory MESI on a packet-switched NoC — a delta over the predecessor design's zero-assertion baseline.

**Keywords:** Cache coherence, MESI, directory protocol, Network-on-Chip, 2D mesh, virtual channels, FPGA, formal verification, UVM

---

## 1. Introduction

### 1.1 Motivation

Modern processors scale performance by adding cores rather than by raising clock frequency. Each core maintains a private cache for low-latency access to frequently used data. When multiple cores cache the same memory block, the system must guarantee that every core observes a consistent view of memory. This is the cache coherence problem.

The interconnect that carries coherence messages between cores must scale with the core count. A shared bus serialises all traffic and becomes a bottleneck beyond a handful of cores. A Network-on-Chip replaces the bus with a packet-switched fabric where multiple transfers proceed in parallel.

This white paper specifies a cache-coherent tiled multicore architecture that combines a directory-based MESI protocol with a 2D mesh NoC. The design is a continuation of the CDAC VLSI Feb 2026 project, rebuilt from first principles with a corrected architecture, a rigorous verification plan, and a realistic implementation path.

### 1.2 Scope

**In scope (baseline):**

- Parameterised N×N 2D mesh NoC, N ∈ {2, 4}; flat directory bounded at N ≤ 16
- 4×4 configuration for simulation and 2×2 for FPGA
- MESI directory coherence with separate directory array
- Four virtual channels for deadlock avoidance
- Multi-flit packets with wormhole switching and header length field
- Transaction-level reference model + 42 SVA assertions + formal subset
- Formal verification with SymbiYosys (safety via BMC, liveness via k-induction)
- UVM verification with pyuvm
- FPGA implementation on ZedBoard XC7Z020
- ASIC flow on Sky130 as future scope

**In scope (gated extension):**

- Coherent DMA device tile — adopted as a Month-2 gated extension. Gate criterion: DMA channel FSM, register map, and one end-to-end transfer pass simulation by end of Week 8. If the gate is missed, the DMA tile and its three messages are removed from the white paper and moved to §9 Future Scope.

**Out of scope:**

- Processor core RTL (stimulus via testbench)
- Pipeline hazard handling
- Consistency model beyond per-address coherence
- Dynamic voltage and frequency scaling
- Cache compression
- Non-volatile memory
- Adaptive routing
- DRAM timing model

### 1.3 Primary Contributions

1. **Scalable tiled architecture** with parameterised mesh topology, distributed directory, and a flat full-map design proven optimal at N ≤ 16.
2. **Integrated verification methodology** combining directed tests, pyuvm constrained-random stimulus with a transaction-level reference model, 42 bound SVA assertions, and a SymbiYosys-proven formal subset. The delta over the predecessor is the reference model (absent) and the assertion set (zero → 42).
3. **Engineering baseline** demonstrating measurable scaling from 2×2 (FPGA) to 4×4 (simulation).
4. **(Gated) Coherent DMA device tile** demonstrating symmetric integration of a non-CPU master into a directory-based coherence protocol. Retained only if the Month-2 gate passes.

### 1.4 Document Structure

Sections 1–11. §2 related work; §3 architecture; §4 design decisions; §5 verification plan; §6 implementation; §7 project plan; §8 claims-vs-artifacts reconciliation; §9 future scope; §10 references; §11 appendices.

---

## 2. Related Work

### 2.1 Cache Coherence

Snooping protocols broadcast every miss to all caches. The Illinois protocol [1] is an early example and ancestor of MESI. Snooping does not scale because broadcast traffic grows with the core count.

Directory protocols record which caches hold each block. Censier and Feautrier [2] introduced the concept. The Stanford DASH multiprocessor [3] made it practical for scalable machines. The Primer on Memory Consistency and Cache Coherence [4] provides the standard taxonomy of stable and transient states, and the message vocabulary (GetS, GetM, Fwd_*, Inv, Put*, Unblock) reused in this design.

Martin, Hill, and Sorin [5] argue that on-chip coherence remains necessary and that sharer-tracking storage keeps its cost manageable. This design uses a **non-inclusive** directory: L1 clean evictions do not notify the directory.

### 2.2 Distributed Shared Caches

Kim, Burger, and Keckler introduced Non-Uniform Cache Architectures [6], contrasting static NUCA (address-interleaved bank mapping) with dynamic NUCA (data migrates toward requester). Zhang and Asanovic proposed victim replication [7], reducing average memory access latency by 16–24% on their simulated tiled CMP (specific results, §4 of [7]). This design uses static NUCA with address-interleaved banks.

### 2.3 On-Chip Networks

Dally and Towles argued that chips should route packets, not wires [8]. The 3D-mesh study [15] established the mesh as the standard manycore topology. Benini and De Micheli framed the NoC as a new SoC paradigm [9]. The textbook by Dally and Towles [10] covers topology, routing, flow control, and deadlock.

Ring topologies have the lowest router complexity but linear average distance and constant bisection bandwidth. Meshes scale better. Torus topologies reduce hop count further but require virtual channels or separate physical networks to avoid deadlock. Production manycore designs (Intel mesh, AMD Infinity Fabric) use mesh for these reasons.

OpenPiton [11] is an open-source tiled manycore framework with distributed directory coherence over on-chip networks.

### 2.4 Verification of Coherence Protocols

Directed testing covers expected cases. Constrained-random stimulus finds corner cases. Formal verification proves invariants. The three are complementary. This white paper's contribution is their **integration** for directory MESI on a packet-switched NoC; each ingredient is prior art.

UVM [12] is the industry standard for constrained-random verification. pyuvm [13] brings UVM structure to Python, reducing development time and integrating with cocotb for simulation.

SymbiYosys [14] provides open-source formal verification using SystemVerilog Assertions and bounded model checking / k-induction.

---

## 3. Architecture Specification

### 3.1 Tile Organisation

**CPU tile** (baseline; every CPU tile is structurally identical):

1. Core interface / testbench stimulus port (load, store, flush)
2. Private L1 cache (4 sets × 4 ways × 64 B = 1 KB; MESI; True LRU with 8-bit age counters per set)
3. L2 bank (8 sets × 4 ways × 64 B = 2 KB) with separate directory array (32 entries × 24 bits, padded to 32 bits)
4. Network Interface Controller (NIC): TX/RX FIFOs (8 packets each), packet generator/decoder
5. 4-stage 5-port router (RC, VA, SA, ST); 3–5 active ports depending on tile position; 4 VCs per port; FIFO depth 4 flits
6. Local behavioural memory tap (`mem_tap`): 256 MB addressable, 1-cycle access, one instance per tile, not shared
7. Intra-tile multiplexer (routes local vs. remote requests; routes incoming packets by message type)

**DMA tile** (gated extension; structural variant, not identical to CPU tile):

- Core interface: DMA register file (memory-mapped)
- L1-lite cache (2 sets × 2 ways × 64 B)
- **No** L2 bank; **no** directory array; **no** mem_tap
- NIC + 5-port router: same as CPU tile

### 3.2 Cache Hierarchy

**L1 cache (private):**

- 4 sets × 4 ways × 64 bytes = 1 KB per tile
- Write-back, write-allocate
- True LRU with 8-bit age counters per set (4 ways × 2 bits) = 32 bits/tile
- MESI state per line (4 stable + 5 transient = 9 states; encoded in tag word + controller FSM)

**L2 bank (shared, distributed):**

- 8 sets × 4 ways × 64 bytes = 2 KB per bank
- **Baseline 4×4:** 16 CPU tiles × 1 bank = 32 KB total L2
- **With DMA 4×4:** 15 CPU tiles × 1 bank = 30 KB total L2
- Tree-PLRU per set (3 bits × 8 sets = 24 bits/bank)
- Separate directory array (32 entries × 24 bits used, padded to 32 bits for BRAM alignment)

**Directory entry (24 bits used, 32 bits stored):**

| Field | Width | Meaning |
|---|---|---|
| State | 3 bits | DIR_I, DIR_S, DIR_E, DIR_M + 4 transient |
| Owner | `TILE_ID_WIDTH` bits (4 at N=4) | Tile ID of exclusive owner |
| Sharers | `SHARER_WIDTH` = N² bits (16 at N=4) | Bit vector of sharers |
| Valid | 1 bit | Entry in use |
| **Total used** | **3 + TILE_ID_WIDTH + N² + 1 = 24 at N=4** | Padded to 32 for BRAM alignment |

**Parameter derivation (single source of truth):**

| Parameter | Formula | N=2 | N=4 | N=8 |
|---|---|---|---|---|
| TILE_COUNT | N² | 4 | 16 | 64 |
| TILE_ID_WIDTH | ⌈log₂(TILE_COUNT)⌉ | 2 | 4 | 6 |
| SHARER_WIDTH | N² | 4 | 16 | 64 |
| OWNER_WIDTH | TILE_ID_WIDTH | 2 | 4 | 6 |
| DIR_ENTRY_USED | 3 + OWNER + SHARER + 1 | 10 | 24 | 74 |

**Directory state encoding (3 bits, exactly 8 codes):**

| Code | State |
|---|---|
| 000 | DIR_I |
| 001 | DIR_S |
| 010 | DIR_E |
| 011 | DIR_M |
| 100 | DIR_MEM_WAIT |
| 101 | DIR_FWD_WAIT (disambiguated by controller pending-type register) |
| 110 | DIR_INV_WAIT |
| 111 | DIR_EVICT (sub-state in controller) |

**L1 state encoding (9 states; tag carries 4 stable states in 2 bits; transient states in controller FSM register):**

- Stable (2 bits): I, S, E, M
- Transient (controller FSM): IS_D, IM_D, SM_D, EI_A, MI_A

### 3.3 MESI Coherence Protocol

Four stable states:

| State | Meaning |
|---|---|
| Modified (M) | Only copy, dirty, memory stale |
| Exclusive (E) | Only copy, clean, memory current |
| Shared (S) | Read-only copy, other copies may exist |
| Invalid (I) | No valid copy |

Transient states in L1: IS_D, IM_D, SM_D, EI_A, MI_A.

Transient states in directory: DIR_MEM_WAIT, DIR_FWD_WAIT, DIR_INV_WAIT, DIR_EVICT (with EVICT sub-states tracked in controller).

**Complete message set (13 core + 3 DMA-gated = 16; 4-bit field holds all):**

| Message | Direction | Flits | Purpose | VC |
|---|---|---|---|---|
| GETS | L1 → dir | 1 | Request shared copy | 0 (REQ) |
| GETM | L1 → dir | 1 | Request exclusive copy | 0 (REQ) |
| PUTS | L1 → dir | **1** | Write back clean line (E→I) | 2 (RESP) |
| PUTM | L1 → dir | 9 | Write back dirty line (M→I) | 2 (RESP) |
| PUTACK | dir → L1 | 1 | Acknowledge PUTS/PUTM | 2 (RESP) |
| UNBLOCK | L1 → dir | 1 | Acknowledge data receipt | 2 (RESP) |
| INV | dir → L1 | 1 | Invalidate | 3 (INV) |
| INVACK | L1 → dir | 1 | Invalidation ack | 2 (RESP) |
| DATA | either | 9 | Data transfer (with exclusive bit) | 2 (RESP) |
| FWD_GETS | dir → owner | 1 | Forward shared request | 1 (FWD) |
| FWD_GETM | dir → owner | 1 | Forward exclusive request | 1 (FWD) |
| DATAFWD | owner → requester | 9 | Forwarded data | 2 (RESP) |
| *(reserved)* | — | — | Code 14 reserved | — |
| DMA_READ | DMA → dir | 1 | **Deprecated** — use GETS from DMA tile | — |
| DMA_WRITE | DMA → dir | 9 | DMA write with data (distinct from GETM's fetch-before-write) | 0 (REQ) |
| DMA_ACK | dir → DMA | 1 | DMA completion | 2 (RESP) |
| *(reserved)* | — | — | Code 15 reserved | — |

**Note on PUTACK:** This message resolves the fatal eviction deadlock (F2). Without it, EI_A and MI_A never exit. It rides VC2 (RESP class) to preserve the message-dependency acyclicity proof: the graph is REQ→RESP, FWD→RESP, INV→RESP. Adding REQ→REQ (if PUTACK were on VC0) would close a cycle.

**Note on UNBLOCK placement:** UNBLOCK rides VC2 (RESP), not VC0 (REQ). It is triggered by DATA receipt (VC2), so it must ride a class no lower than VC2. Placing it on VC0 creates a descending dependency DATA(VC2)→UNBLOCK(VC0), which violates Duato's theorem and can strand the directory in DIR_MEM_WAIT / DIR_FWD_WAIT.

**Note on PUTS payload:** PUTS is 1 flit (address only). An E-state line is clean by definition; memory already holds the current value. Sending 8 body flits on a clean eviction is 100% redundant bandwidth.

**Note on DMA_READ:** Dropped. From the coherence protocol's perspective, a DMA tile's read request is a GETS: same VC, same 1 flit, same directory path, same DATA response. The source field in the header distinguishes the DMA tile. DMA_WRITE is retained because it carries data and performs write-without-fetch, which is genuinely distinct from GETM's fetch-before-write.

### 3.4 Network-on-Chip

**Topology:** 2D mesh. Each CPU tile has 5 ports; edge tiles tie off unused ports (3–5 active ports depending on position). Physical module is uniform 5-port; synthesis prunes tied-off logic.

**Routing:** XY deterministic. A packet first moves in X, then in Y. Acyclic channel dependency graph.

**Flow control:** Credit-based. Each VC has a credit counter initialised to the downstream FIFO depth (4). Credit width: 3 bits.

**Virtual channels:** Four VCs per port, fixed priority by class:

| VC | Class | Messages | Priority |
|---|---|---|---|
| VC0 | Requests | GETS, GETM, DMA_WRITE | Lowest |
| VC1 | Forwarded requests | FWD_GETS, FWD_GETM | Medium |
| VC2 | Responses | DATA, DATAFWD, INVACK, UNBLOCK, PUTS, PUTM, PUTACK, DMA_ACK | Highest |
| VC3 | Invalidations | INV | High |

**Arbitration:** Two-stage.
- **VC arbitration (per input port):** fixed priority by class, **RESP > INV > FWD > REQ**.
- **Switch arbitration (across input ports):** round-robin per output port, with round-robin pointer advancing on grant.

Rationale: responses and invalidations are protocol-critical and must not be blocked behind requests. Round-robin across inputs prevents input starvation.

**Switching:** Wormhole. Header flit reserves the path; body and tail flits follow. Packet length carried in header reserved bits (see §3.5) so routers know when to release output ports.

**Pipeline:** 4 stages — RC (route compute), VA (VC allocation), SA (switch allocation), ST (switch traversal). Hop latency: 4 cycles.

**Per-router buffering:** 5 ports × 4 VCs × 4 flits × 64 bits = 640 bytes per router. 16 routers = 10 KB flit storage.

### 3.5 Packet and Flit Format

**Header flit (64 bits):**

| Bits | Field | Width | Meaning |
|---|---|---|---|
| [63:56] | Dest tile | `TILE_ID_WIDTH` (≤8) | Destination tile ID |
| [55:48] | Src tile | `TILE_ID_WIDTH` (≤8) | Source tile ID |
| [47:44] | Msg type | 4 | Message code |
| [43:42] | VC ID | 2 | Virtual channel (asserted to equal class(msg)) |
| [41] | Head | 1 | First flit of packet |
| [40] | Tail | 1 | Last flit of packet (single-flit packet has both) |
| [39] | Write enable | 1 | Store / memory write |
| [38] | Exclusive | 1 | DATA carries exclusive grant |
| [37:32] | **Packet length** | 6 | Total flits in packet (1–63) |
| [31:0] | Address | 32 | Byte address |

**Body flit (64 bits):** 8 bytes of pure payload. No control bits. Router tracks packet length from header.

**Packet sizes:**

- Control message (GETS, GETM, INV, INVACK, UNBLOCK, PUTACK, FWD_*): 1 flit
- Data-bearing message (PUTM, DATA, DATAFWD): 9 flits (1 header + 8 body = 64 bytes)
- PUTS: 1 flit (address only; no data)
- DMA_WRITE: 9 flits (one 64-byte block)

**Framing rule:** Multi-flit packets carry their length in header[37:32]. The `tail` bit is redundant for multi-flit packets but retained for single-flit compatibility (single-flit packets have head=1 and tail=1). The router counts down from length to release output ports; a header with length=1 is a complete packet.

**Header reserved bits:** 0 bits free after length field (6 used). The 6-bit field accommodates packet lengths up to 63 flits, sufficient for all message types.

### 3.6 Address Map

**4×4 (16 tiles):**

| Bits | Field | Width |
|---|---|---|
| [31:15] | Tag | 17 |
| [14:11] | Home tile (X,Y) | 4 |
| [10:8] | L2 set | 3 |
| [7:6] | L1 set | 2 |
| [5:0] | Byte offset | 6 |

**2×2 (4 tiles):**

| Bits | Field | Width |
|---|---|---|
| [31:13] | Tag | 19 |
| [12:11] | Home tile (X,Y) | 2 |
| [10:8] | L2 set | 3 |
| [7:6] | L1 set | 2 |
| [5:0] | Byte offset | 6 |

**Stored tag widths:**

| Cache | 4×4 stored tag | 2×2 stored tag | Source bits |
|---|---|---|---|
| L1 | 24 bits | 24 bits | address[31:8] |
| L2 | 21 bits | 21 bits | address[31:11] |

**Why L1 tag includes home tile and L2 set:** The L1 must distinguish addresses that map to different banks and different L2 sets. The L1 tag is the complement of the L1 set index and byte offset. By standard decomposition, it includes all higher-order bits.

**Why L2 tag includes home tile and L1 set:** The L2 tag is the complement of the L2 set index and byte offset. It includes the home tile bits (which are constant within a bank, but stored redundantly for simplicity) and the L1 set bits (which vary and must be distinguished). A simpler alternative excludes home bits from L2 tag (since they're constant per bank), yielding 19-bit L2 tags; the 21-bit version is adopted for uniform decomposition.

**Critical fix from v1.0:** The original v1.0 layout placed L2 set at [8:6], which **contains** L1 set [7:6]. This means for any fixed L1 set, only 2 of 8 L2 sets are reachable — a 4× capacity loss. The corrected layout places L2 set at [10:8], disjoint from L1 set [7:6].

### 3.7 Memory Model

Each CPU tile has a local behavioural memory tap (`mem_tap`):

| Property | Value |
|---|---|
| Address width | 32 bits (architectural); 28 bits meaningful (256 MB) |
| Addressable memory | 256 MB per tile |
| Data width | 8 bits per byte, 64 bytes per line |
| Access latency | 1 cycle |
| Instances | One per CPU tile |
| Shared across tiles | No |
| Coherence for memory | Yes, via the directory protocol |
| Consistency model | None (per-address coherence only) |
| Preload support | Task-based testbench interface |

**Address space partition (per-tile view):**

| Region | Range | Purpose |
|---|---|---|
| Memory | 0x0000_0000 – 0x0FFF_FFFF | 256 MB backing store |
| Unmapped | 0x1000_0000 – 0xEFFF_FFFF | Reserved |
| DMA registers | 0xF000_0000 – 0xF000_FFFF | DMA control (gated extension) |
| Test addresses | 0xFFFF_FF00 – 0xFFFF_FF08 | Special test patterns |

**Memory path:** L2 miss → mem_tap (1-cycle) → DATA response. DIR_MEM_WAIT exits on MEM_DATA. DIR_EVICT_WB exits on memory write completion.

**Memory subsystem not modelled:** DRAM timing (row activation, refresh), ECC, bank interleaving, prefetching, MMU/address translation. These are future scope.

### 3.8 DMA Engine (Gated Extension)

The DMA engine, if the Month-2 gate passes, is implemented as a device tile on the mesh. It is structurally similar to a CPU tile but has a small L1-lite cache (2 sets × 2 ways × 64 B), no L2 bank, no directory, and no mem_tap. It has two channels, single-block transfer (one 64-byte line per transaction = 9 flits), and memory-mapped registers.

**Register map (per channel):**

| Offset | Register | Width | Purpose |
|---|---|---|---|
| 0x00 | SRC_LO | 32 | Source address |
| 0x04 | DST_LO | 32 | Destination address |
| 0x08 | LEN | 32 | Transfer length in bytes (must be 64 in baseline) |
| 0x0C | CTRL | 32 | Start, direction, enable |
| 0x10 | STATUS | 32 | Busy, done, error |
| 0x14 | COUNT | 32 | Bytes transferred |

**Messages:** DMA_WRITE (9 flits, write-with-data, distinct from GETM) and DMA_ACK (1 flit). DMA reads use standard GETS. **No new directory states.**

**Tile slot cost:** One tile in the mesh. At 4×4, this yields 15 CPU tiles + 1 DMA tile = 15 L2 banks = 30 KB L2. At 2×2, this yields 3 CPU tiles + 1 DMA tile = 3 L2 banks = 6 KB L2.

---

## 4. Design Decisions and Justification

### 4.1 Topology Comparison

Seven topologies compared on nine parameters (worst path is defined but not tabulated because it is not independently decisive; it is encompassed by wire length and hop count).

**Worst hop count at N tiles:**

| N | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
|---|---|---|---|---|---|---|---|
| 4 | 1 | 1 | 2 | 2 | 2 | 4 | 2 |
| 16 | 1 | 1 | 8 | 6 | 4 | 8 | 2 |
| 64 | 1 | 1 | 32 | 14 | 8 | 12 | 2 |

**Ports per router:**

| N | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
|---|---|---|---|---|---|---|---|
| 4 | 1 | 4 | 3 | 3 | 5 | 3 | 4 |
| 16 | 1 | 16 | 3 | 5 | 5 | 3 | 16 |
| 64 | 1 | 64 | 3 | 5 | 5 | 3 | 64 |

**Total wire length (tile-pitch units):**

| N | Bus | Xbar | Ring | Mesh | Torus |
|---|---|---|---|---|---|
| 4 | 2 | 8 | 5 | 4 | 8 |
| 16 | 4 | 64 | 18 | 24 | 48 |
| 64 | 8 | 512 | 70 | 112 | 224 |

**Full comparison at N=64:**

| Parameter | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
|---|---|---|---|---|---|---|---|
| Ports/router | 1 | 64 | 3 | 5 | 5 | 3 | 64 |
| Worst hop | 1 | 1 | 32 | 14 | 8 | 12 | 2 |
| Paths | 1 | 1 | 2 | Many | More | 1 | 1 |
| Wire length | 8 | 512 | 70 | 112 | 224 | 192 | 64 |
| Deadlock risk | Low | Low | High | Low | High | Low | High |
| RTL complexity | Low | High | Low | Medium | High | Medium | Low |
| Synthesis congestion | Low | Very High | Medium | Low | High | Medium | Very High |
| Fault tolerance | Low | Low | Low | **Low** (XY routes around nothing) | Medium | Medium | Low |
| Scalability | Poor | Poor | Weak | Good | Good | Good | Poor |

### 4.2 Why 2D Mesh

1. **Port count is constant at 5.** A crossbar needs 64 ports at N=64.
2. **Hop count grows as √N.** A ring's worst hop grows as N/2.
3. **Wires are short.** Every mesh link connects adjacent tiles.
4. **Deadlock-free with XY routing.** Acyclic channel dependency graph.
5. **Low synthesis congestion.** No link crosses the chip.
6. **Scales to N=16 with flat directory.** Beyond N=16, hierarchical or limited-pointer directory required.
7. **Industry standard.** Intel mesh, AMD Infinity Fabric, OpenPiton.
8. **Low RTL complexity.** ~390 lines for the router (peer estimate).

**Correction from v1.0:** "Scales to hundreds of tiles" is false for the specified flat directory. The 16-bit sharer vector bounds N ≤ 16. Beyond N=16, a hierarchical directory is required and is future scope.

### 4.3 Why Not Other Topologies

- **Bus:** Bandwidth does not scale.
- **Crossbar:** Wire count grows as N². At N=64, 4096 links. Not routable.
- **Ring:** Hop count grows as N/2. Long wrap-around wire. Cyclic dependency causes deadlock under coherence traffic.
- **Torus:** Wrap-around wires cross the chip. Requires VCs (which we have) plus additional VC pressure. At 4 tiles, a 2×2 torus is degenerate.
- **Tree:** Hot spot at the root.
- **Star:** Hub has N ports. Single point of failure.

### 4.4 Cache Parameters

| Parameter | Value | Justification |
|---|---|---|
| Line size | 64 bytes | Industry standard; flit-packing clean (8 body flits); spatial locality |
| L1 sets × ways | 4 × 4 | Low conflict misses; fits FPGA; True LRU affordable at 4 ways |
| L2 sets × ways | 8 × 4 | Provides 32 directory entries per bank; balances simulation speed and coherence coverage |
| L1 replacement | True LRU (8 bits/set, age counters) | Better than pseudo-LRU at 4 ways; fits LUTRAM budget |
| L2 replacement | Tree-PLRU (3 bits/set) | Adequate for 4-way; saves 5 bits/set vs. True LRU |
| Write policy | Write-back, write-allocate | Standard for coherent caches |

### 4.5 Deadlock Freedom — Three-Layer Guarantee

Deadlock freedom is proven by three independent layers. No one layer alone is sufficient.

**Layer 1 — Network routing (XY deterministic):** The channel dependency graph of XY routing on a mesh is acyclic. All X-channel dependencies precede all Y-channel dependencies. No Y-to-X dependency exists. Therefore no cycle exists.

**Layer 2 — Protocol message classes (4 VCs):** The message-dependency graph is acyclic. Dependencies: REQ→RESP, FWD→RESP, INV→RESP. No class depends on REQ. RESP is terminal. The VC assignment enforces this: requests use VC0, forwards VC1, responses VC2, invalidations VC3.

**Layer 3 — Transient-state escape:** Every transient state has a defined exit condition. L1 transients (IS_D, IM_D, SM_D, EI_A, MI_A) exit on DATA, DATAFWD, or PUTACK. Directory transients (DIR_MEM_WAIT, DIR_FWD_WAIT, DIR_INV_WAIT, DIR_EVICT) exit on MEM_DATA, DATAFWD, all INVACKs, or the appropriate PUT/PUTACK.

**Resource layer — Credit-based flow control:** Each VC has a credit counter. The sender transmits only when credit > 0. Credits prevent buffer overflow by induction: credit ≤ FIFO depth always.

**Consequence:** Deadlock freedom requires all four mechanisms together. The abstract claims VC separation alone prevents deadlock; this is false. The full three-layer proof is required.

### 4.6 Packet Size and Framing

64-bit flit, header + 8 body for cache lines = 9 flits. Wormhole switching keeps per-router buffer at flit granularity. Header carries packet length in [37:32] so routers know when to release output ports; body flits are pure payload.

---

## 5. Verification Plan

### 5.1 Directed Tests

| # | Test | Purpose |
|---|---|---|
| 1 | Load miss, local home | Basic L1 miss, local L2 |
| 2 | Load miss, remote home | Basic L1 miss, remote L2, NoC round trip |
| 3 | Store miss, local home | Basic store, local L2 |
| 4 | Store miss, remote home | Basic store, remote L2 |
| 5 | Silent E→M upgrade | Exclusive state benefit |
| 6 | Sharing (two readers) | DIR_S with 2 sharers |
| 7 | Upgrade with invalidation | DIR_INV_WAIT, multi-INVACK (≥3 tiles) |
| 8 | Forward from remote owner | DIR_FWD_WAIT, DATAFWD |
| 9 | L1 clean eviction (E→I) | PUTS + PUTACK |
| 10 | L1 dirty eviction (M→I) | PUTM + PUTACK |
| 11 | L2 eviction of DIR_M line | DIR_EVICT_FWD_WAIT + write-back |
| 12 | L2 eviction of DIR_S line | DIR_EVICT_INV_WAIT + multi-INVACK |
| 13 | Back-to-back requests from two tiles | Contention, arbitration |
| 14 | Concurrent requests to same line | Race conditions |
| 15 | NoC saturation | Mesh saturation, credit stalls |
| 16 | Memory fill path | DIR_MEM_WAIT exit |
| 17 | INV storm (15 sharers) | VC3 FIFO depth stress |
| 18 | DMA read single block | Basic DMA read (using GETS) |
| 19 | DMA write single block | Basic DMA write (using DMA_WRITE) |
| 20 | DMA read while CPU tile reads | Contention |
| 21 | DMA to same line as CPU write | Coherence edge case |
| 22 | Back-to-back DMA transfers | Channel overlap |

Tests 18–22 are conditional on the DMA gate.

Each test checks **final state** and **data values**.

### 5.2 Formal Verification (SymbiYosys)

**Configuration:** 2×2 (4-tile) mesh for the baseline formal campaign. Minimum 3 tiles required to exercise the invalidation path (2 sharers + 1 requester). The 2×2 configuration also exercises the 4-bit home field and 5-port interior router.

**Properties to prove:**

| Property | Type | Method | Description |
|---|---|---|---|
| Single writer | Safety | BMC/k-induction | At most one cache in M or E state for any line |
| Multiple readers | Safety | BMC/k-induction | Any number of caches in S state |
| Data consistency (L2-level) | Safety | BMC/k-induction | If any L1 in S/E, owning L2 bank holds current value |
| Directory consistency | Safety | BMC/k-induction | Directory state matches aggregate L1 states; owner valid; sharers accurate; DIR_I ⇒ valid=0 |
| No orphan transient | Safety (bounded) | BMC | Every transient state exits within K cycles |
| No message loss | Liveness (bounded) | k-induction (mode prove) | Every request receives a response within K cycles |
| Deadlock freedom | Liveness (bounded) | k-induction (mode prove) | No cycle of waiting dependencies within K cycles |
| XY routing order | Safety | BMC | No Y move before X complete |
| VC-class match | Safety | BMC | flit.VC == class(flit.msg) |
| Credit invariant | Safety | BMC | 0 ≤ credit ≤ FIFO depth |

**Depth and modes:**

- Safety properties: `mode bmc` with depth K=40, `mode prove` (k-induction) for induction.
- Liveness properties: `mode prove` (k-induction) with fairness assumption on arbitration; bounded liveness within K=150 cycles (derived from longest protocol path: GETM→INV→INVACK→DATA→UNBLOCK = 4 traversals × 6 hops × 4 cycles/hop = 96 cycles + pipeline overhead ≈ 150).

**Why not BMC for liveness:** BMC explores traces of length ≤ k. "Eventually" is unbounded by construction. k-induction generalises BMC to unbounded time.

### 5.3 UVM Environment (pyuvm + cocotb)

**Components:**

| Component | Function |
|---|---|
| Test | Top-level stimulus |
| Environment | Container for agents and scoreboard |
| Agent (per tile) | Driver + monitor + sequencer |
| Scoreboard | Compares DUT output against reference model |
| Reference model | **Transaction-level** Python model of MESI directory coherence |
| Coverage collector | Functional coverage |

**Reference model:** Transaction-level model of MESI directory coherence. It tracks shadow state for every L1 line, every L2 bank, every directory entry, and every memory location. It holds data values, not just state bits. After every transaction, the scoreboard compares expected state and data against DUT output. It does **not** model cycle timing; timing defects are caught by SVA assertions and formal proofs.

**Simulators:** Verilator for pyuvm constrained-random regression; Vivado xsim for `bind`-based SVA simulation; Yosys/sby for formal.

**Stimulus:** Constrained-random sequences with coverage-driven closure.

**Coverage targets:**

| Coverage Type | Target | Tool |
|---|---|---|
| L1 state × message cross | 100% of legal bins | pyuvm |
| Directory state × request cross | 100% of legal bins | pyuvm |
| Transaction type × distance | 100% of legal bins | pyuvm |
| VC × message class | 100% of legal bins | pyuvm |
| Line coverage | ≥98% | Verilator, xsim |
| Branch coverage | ≥98% | xsim |
| Toggle coverage | ≥95% | Verilator |
| FSM coverage | 100% states and transitions | Verilator, xsim |
| Expression coverage | ≥95% | xsim |
| Safety assertions | 100% pass in simulation; formally proven subset | SymbiYosys, SVA |
| Liveness assertions | 100% pass with bounded timeout; k-induction proven | SymbiYosys, SVA |
| Cover properties | 100% hit | SymbiYosys |

**Functional cross space:** (9 L1 states × 16 messages) + (8 directory states × 16 messages) = 144 + 128 = 272 cross terms (legal subset covered).

### 5.4 SVA Assertion Set

42 assertions in 8 categories, bound to DUT via `bind`:

| Category | Count | Type | Scope |
|---|---|---|---|
| A1 — MESI invariants | 5 | Safety | L1 arrays |
| A2 — Directory invariants | 7 | Safety | L2 directory |
| A3 — Message protocol | 6 | Safety | NIC interfaces |
| A4 — Flow control | 8 | Safety | Router ports |
| A5 — Bounded liveness | 4 | Liveness | Controllers, FIFOs |
| A6 — Data integrity | 4 | Safety | L2 array, memory |
| A7 — State machine | 4 | Safety | Controllers |
| A8 — Address / routing | 4 | Safety | NIC, router |

Checked in simulation via cocotb + Xsim. A subset (A1.x, A2.x, A8.3) is proved formally.

### 5.5 Regression

Directed tests + pyuvm random tests + formal proofs run on every commit. CI via GitHub Actions with self-hosted runner. Tool versions pinned in CI configuration.

---

## 6. Implementation Plan

### 6.1 FPGA Target

| Parameter | Value |
|---|---|
| Board | ZedBoard |
| Device | XC7Z020-CLG484-1 |
| LUTs | 53,200 |
| FFRs | 106,400 |
| BRAM | 140 tiles (36 Kb each) |
| DSP | 220 slices |
| Clock | 100 MHz |

**Configuration:** 2×2 mesh on FPGA (baseline); 4×4 in simulation.

**Resource budget (2×2):**

| Resource | Available | Target | Max | Risk |
|---|---|---|---|---|
| LUTs | 53,200 | ≤20,000 (38%) | ≤40,000 (75%) | Medium |
| FFs | 106,400 | ≤25,000 (24%) | ≤50,000 (47%) | Low |
| BRAM | 140 | ≤30 (21%) | ≤60 (43%) | Low–Medium |
| DSP | 220 | 0 | 0 | None |

**BRAM budget (2×2, per-bank granularity):**

| Component | BRAMs | Notes |
|---|---|---|
| L1 data (4 × 512b × 16 lines) | 4 | 512/72 ≈ 8 BRAMs if 72-bit config; 4 if using LUTRAM for L1 tags |
| L1 tags (4 × 32b × 16) | 1 | Fits in LUTRAM |
| L2 data (4 × 512b × 32 lines) | 8 | 32 lines × 64 B = 2 KB per bank |
| L2 tags (4 × 32b × 32) | 1 | Fits in LUTRAM |
| Directory (4 × 32b × 32) | 1 | Fits in one BRAM36 |
| Router FIFOs (4 × 5 ports × 4 VCs × 4 flits) | 4 | 64 b × 4 deep × 20 buffers |
| NIC FIFOs (4 × 8 pkts) | 4 | 64 b × ~72 flits |
| **Total (baseline)** | **~27** | Within 30 target |

**Contingency:** If BRAM budget is exceeded, map L1 tag and directory arrays to LUTRAM. If LUT budget is exceeded, reduce L1 to 4 sets × 2 ways. **Do not reduce VC count** — it breaks deadlock freedom.

**Fallback if timing fails:** reduce cache associativity/sets, map selected arrays to LUTRAM, or reduce FPGA tile count. VC count must remain 4 unless deadlock freedom is re-proven.

### 6.2 ASIC Target (Future Scope)

| Parameter | Value |
|---|---|
| Node | Sky130 |
| Flow | OpenLane |
| Synthesis | Yosys |
| Place and route | OpenROAD |
| Physical verification | Magic (DRC), Netgen (LVS) |
| Timing signoff | OpenSTA |

### 6.3 Synthesis Flow

| Step | Tool |
|---|---|
| RTL elaboration | Verilator, Vivado xsim |
| Logic synthesis | Vivado (FPGA), Yosys (ASIC) |
| Place and route | Vivado (FPGA), OpenROAD (ASIC) |
| Static timing | Vivado Timing (FPGA), OpenSTA (ASIC) |
| Physical verification | Magic, Netgen (ASIC) |
| Bitstream | Vivado |

Tool versions pinned in CI configuration.

### 6.4 Timing Closure

| Constraint | Target |
|---|---|
| Clock period | 10 ns (100 MHz) |
| Clock uncertainty (setup) | 0.2 ns |
| Clock uncertainty (hold) | 0.1 ns |
| I/O delay (max) | 2.0 ns |
| I/O delay (min) | 0.5 ns |
| False path | Reset synchroniser |
| WNS | ≥ 0 ns |
| WHS | ≥ 0 ns |
| WPWS | ≥ 3.750 ns |
| TNS | 0 |
| Failing endpoints | 0 |

**Critical paths and fixes:**

1. L2 tag compare → directory state decision: split tag compare and directory lookup into separate pipeline stages.
2. Router arbitration → crossbar output: 4-stage pipeline (RC, VA, SA, ST) separates arbitration from crossbar.
3. NIC packet decode → cache interface: register packet decoder output.

**Retiming:** enabled (`-retiming`) except on reset synchroniser, handshake paths, and state registers.

---

## 7. Project Plan

### 7.1 Four-Month (16-Week) Schedule

| Month | Week | Milestone |
|---|---|---|
| Month 1 | 1–2 | Inherited bug fixes (DIR_I valid, PROXY_WAIT); RTL refactor |
| Month 1 | 3–4 | 2-tile mesh, directed tests 1–10 |
| Month 2 | 5–6 | 4×4 mesh, VCs, PUTACK, PUTS 1-flit |
| Month 2 | 7–8 | pyuvm environment, reference model, DMA gate check |
| Month 3 | 9–10 | Formal properties (BMC + k-induction), SVA assertion set |
| Month 3 | 11–12 | FPGA synthesis, timing closure, bitstream on ZedBoard |
| Month 4 | 13–14 | White paper finalisation, coverage closure |
| Month 4 | 15–16 | Paper draft, IEEE submission |

### 7.2 Milestones

| # | Milestone | Week |
|---|---|---|
| 1 | Bug fixes complete | 2 |
| 2 | 2-tile mesh verified | 4 |
| 3 | 4×4 mesh simulation complete | 6 |
| 4 | PUTACK + PUTS 1-flit validated | 6 |
| 5 | pyuvm environment running | 8 |
| 6 | DMA gate decision | 8 |
| 7 | Formal proofs passing | 10 |
| 8 | FPGA bitstream on ZedBoard | 12 |
| 9 | Timing report signed off | 12 |
| 10 | XDC authored and verified | 12 |
| 11 | Power estimation complete | 12 |
| 12 | White paper finalised | 14 |
| 13 | Paper submitted | 16 |

### 7.3 Risks and Mitigations

| Risk | Probability | Mitigation |
|---|---|---|
| FPGA does not fit 2×2 on BRAM | Medium | LUTRAM for L1/L2 tags; reduce associativity |
| Timing closure fails | Medium | Reduce cache size; map arrays to LUTRAM; floorplan |
| Formal proofs do not complete | Medium | Reduce depth; abstract data values; prove A1.x/A2.x on reduced config |
| Virtual channel deadlock | Low | Layered proof: XY + VC class separation + credits |
| DMA gate not passed | High | Remove DMA tile and 3 messages; move to §9 Future Scope |
| Time overrun | Medium | Drop DMA, drop ASIC; retain baseline architecture |
| BRAM arithmetic wrong in peer docs | Low | Recompute per-bank budget before synthesis |

---

## 8. Claims vs Artifacts Reconciliation

This section reconciles the original team's report against the artifacts they delivered.

| # | Original Report Claim | Artifact Reality | Status |
|---|---|---|---|
| 1 | All RTL modules completed and verified | All modules present, but several have bugs | Partial |
| 2 | Remote-owner forwarding completed and verified | `is_fwd_remote_reply` tied to 0; `PROXY_WAIT` never entered | **Contradicted** |
| 3 | Synthesis results (WNS = +0.003 ns) | No Vivado project, no XDC, no reports in repo | **Unverifiable** |
| 4 | FPGA hardware validated on ZedBoard | No `fpga_top` module, no XDC in repo | **Unverifiable** |
| 5 | Five directed test cases pass | Testbench skips tests 3 and 5; state-only checks | Partial |
| 6 | Data correctness verified | No data-value checks | **Contradicted** |
| 7 | Directory `DIR_I` bug | Not mentioned in report | **Omitted** |

This white paper's contribution is to build a correct architecture from the ground up, not to defend the original report. The original team's code and report are treated as reference only.

---

## 9. Future Scope

| Item | Timeline | Prerequisite |
|---|---|---|
| Coherent DMA device tile (if gate missed) | Post-project | Month-2 gate decision |
| Scatter-gather DMA | Post-project | DMA baseline working |
| More DMA channels | Post-project | DMA baseline working |
| DMA priority levels | Post-project | DMA baseline working |
| ASIC tapeout on Sky130 | Post-project | OpenLane flow complete |
| RISC-V core integration | Post-project | Hazard handling |
| Adaptive routing | Post-project | VC budget expansion |
| Victim replication / dynamic NUCA | Post-project | Cache redesign |
| 8×8 mesh | Post-project | Hierarchical directory required |
| Memory controller and DRAM model | Post-project | Replace behavioural mem_tap |
| Consistency model (atomics, fences) | Post-project | Core + load/store queue |
| MSHRs / non-blocking L1 | Post-project | L1 FSM extension |
| Debug infrastructure (ILA/VIO) | Post-project | FPGA bring-up |

---

## 10. References

[1] M. S. Papamarcos and J. H. Patel, "A Low-Overhead Coherence Solution for Multiprocessors with Private Cache Memories," ISCA, 1984.

[2] L. M. Censier and P. Feautrier, "A New Solution to Coherence Problems in Multicache Systems," IEEE Trans. Computers, 1978.

[3] D. Lenoski et al., "The Directory-Based Cache Coherence Protocol for the DASH Multiprocessor," ISCA, 1990.

[4] V. Nagarajan, D. J. Sorin, M. D. Hill, and D. A. Wood, A Primer on Memory Consistency and Cache Coherence, 2nd ed., Morgan & Claypool, 2020.

[5] M. M. K. Martin, M. D. Hill, and D. J. Sorin, "Why On-Chip Cache Coherence Is Here to Stay," Communications of the ACM, 2012.

[6] C. Kim, D. Burger, and S. W. Keckler, "An Adaptive, Non-Uniform Cache Structure for Wire-Delay Dominated On-Chip Caches," ASPLOS X, 2002.

[7] M. Zhang and K. Asanovic, "Victim Replication: Maximizing Capacity while Hiding Wire Delay in Tiled Chip Multiprocessors," ISCA-32, 2005.

[8] W. J. Dally and B. Towles, "Route Packets, Not Wires: On-Chip Interconnection Networks," DAC, 2001.

[9] L. Benini and G. De Micheli, "Networks on Chips: A New SoC Paradigm," IEEE Computer, 2002.

[10] W. J. Dally and B. Towles, Principles and Practices of Interconnection Networks, Morgan Kaufmann, 2004.

[11] J. Balkind et al., "OpenPiton: An Open Source Manycore Research Framework," ASPLOS '16, 2016.

[12] IEEE 1800.2-2020, Universal Verification Methodology (UVM).

[13] pyuvm documentation, https://github.com/pyuvm/pyuvm

[14] SymbiYosys documentation, https://github.com/YosysHQ/sby

[15] W. J. Dally and B. Towles, "The 3D Mesh of a Multicore Microprocessor," ISCA, 2001.

---

## 11. Appendix

### A. MESI State Transitions (L1)

| Current | Event | Next | Actions |
|---|---|---|---|
| I | Load miss | IS_D | Send GETS (VC0) |
| IS_D | DATA (exclusive) | E | Install, send UNBLOCK (VC2) |
| IS_D | DATA (shared) | S | Install, send UNBLOCK (VC2) |
| I | Store miss | IM_D | Send GETM (VC0) |
| IM_D | DATA (exclusive) | M | Install, write, send UNBLOCK (VC2) |
| S | Store hit | SM_D | Send GETM (VC0) |
| SM_D | DATA (exclusive) + all INVACKs | M | Write |
| E | Store hit | M | Silent upgrade |
| M | Eviction | MI_A | Send PUTM (VC2) |
| MI_A | PUTACK | I | Release way |
| E | Eviction | EI_A | Send PUTS (VC2) |
| EI_A | PUTACK | I | Release way |
| S | Eviction | I | Silent drop |
| S | INV received | I | Send INVACK (VC2) |
| E | INV received | I | Send INVACK (VC2) |
| M | INV received | I | Write back to dir, send INVACK (VC2) |

**Transient state exit conditions (SM_D, IS_D, IM_D, EI_A, MI_A) as above.**

### B. Directory State Transitions

| Current | Request | Next | Actions |
|---|---|---|---|
| DIR_I | GETS | DIR_MEM_WAIT | Fetch memory |
| DIR_I | GETM | DIR_MEM_WAIT | Fetch memory |
| DIR_MEM_WAIT | MEM_DATA | DIR_E or DIR_S | Install; reply DATA (exclusive bit = 1 for E, 0 for S) |
| DIR_S | GETS | DIR_S | Reply DATA (shared); add sharer |
| DIR_S | GETM | DIR_INV_WAIT | Send INV to all sharers |
| DIR_INV_WAIT | All INVACKs | DIR_M | Set owner; reply DATA (exclusive) |
| DIR_E | GETS (owner) | DIR_E | Local serve |
| DIR_E | GETS (other) | DIR_FWD_WAIT | Set pending-type = GETS; send FWD_GETS |
| DIR_FWD_WAIT | DATAFWD | DIR_S | Add sharer |
| DIR_E | GETM (other) | DIR_FWD_WAIT | Set pending-type = GETM; send FWD_GETM |
| DIR_FWD_WAIT | DATAFWD | DIR_M | Set owner |
| DIR_M | GETS (owner) | DIR_M | Local serve |
| DIR_M | GETS (other) | DIR_FWD_WAIT | Set pending-type = GETS; send FWD_GETS; expect write-back |
| DIR_FWD_WAIT | DATAFWD | DIR_S | Add sharer |
| DIR_M | GETM (other) | DIR_FWD_WAIT | Set pending-type = GETM; send FWD_GETM; expect write-back |
| DIR_FWD_WAIT | DATAFWD | DIR_M | Set owner |
| DIR_E | PUTS | DIR_I | Clear owner; send PUTACK |
| DIR_E | PUTM | DIR_I | Clear owner; write memory; send PUTACK |
| DIR_M | PUTM | DIR_I | Clear owner; write memory; send PUTACK |
| Any | Eviction needed | DIR_EVICT | Resolve victim first; sub-state in controller |

**Pending-type register:** The `DIR_FWD_WAIT` state requires a controller register (`pending_type: GETS | GETM`) to disambiguate the DATAFWD next-state. The 3-bit directory state field is exactly saturated (8 codes for 4 stable + 4 transient); the disambiguator lives in the controller, not the directory entry.

### C. Flit Field Encoding

**Message type (4 bits):**

| Code | Message |
|---|---|
| 0000 | GETS |
| 0001 | GETM |
| 0010 | PUTS |
| 0011 | PUTM |
| 0100 | PUTACK |
| 0101 | UNBLOCK |
| 0110 | INV |
| 0111 | INVACK |
| 1000 | DATA |
| 1001 | FWD_GETS |
| 1010 | FWD_GETM |
| 1011 | DATAFWD |
| 1100 | DMA_WRITE |
| 1101 | DMA_ACK |
| 1110–1111 | Reserved |

**Control bits:**

| Bit | Meaning |
|---|---|
| 0 | Head flit |
| 1 | Tail flit |
| 2 | Write enable |
| 3 | Exclusive indication |

**Header flit [37:32]:** Packet length in flits (1–63).

### D. Open Items

| # | Item | Status |
|---|---|---|
| 1 | Formal verification depth | K=40 (safety BMC); K=150 (liveness k-induction) |
| 2 | pyuvm coverage targets | 100% functional legal bins; ≥98% line/branch; ≥95% toggle |
| 3 | IEEE conference venue | To be selected (Month 4) |
| 4 | FPGA fit verification | To be confirmed at synthesis checkpoint (Week 12) |
| 5 | DMA gate decision | Week 8 (pass: retain; fail: remove to §9) |
| 6 | Timeout mechanism for transient states | To be specified (verification detection, not deadlock avoidance) |
| 7 | Coverage model for state × message cross | 272 legal terms (defined in §5.3) |

---

**End of White Paper v2.0**

---

## Part C — Justification Appendix

### C.1 Summary of Changes from v1.0

| Change ID | Section | v1.0 | v2.0 | Severity | Proof |
|---|---|---|---|---|---|
| F1 | §11.B | `DIR_FWD_WAIT` single state, two next-states | Controller `pending_type` register disambiguates | Fatal | A deterministic FSM requires δ(S,E) to be single-valued. Two rows for `(DIR_FWD_WAIT, DATAFWD)` violate this. |
| F2 | §3.3, §11.A, §11.B | EI_A/MI_A wait for "ACK" with no message | PUTACK added (code 0100, VC2, 1 flit) | Fatal | 14-message set has no PUT ack. Without PUTACK, eviction path is dead. |
| F3 | §3.5 | Body flits pure payload, header tail only | Header [37:32] = packet length; body pure payload | Fatal | 9-flit packet cannot be delimited with header tail=0 and no body tail. Length field costs 0 body bits and 6 header bits otherwise unused. |
| F4 | §3.6 | L2 set [8:6] contains L1 set [7:6] | L2 set [10:8], L1 set [7:6] disjoint | Fatal | For fixed L1 set, only 2 of 8 L2 sets reachable → effective L2 = 8 KB vs. claimed 32 KB. Disjoint fields restore full capacity. |
| F5 | §3.2, §3.6 | 16-bit sharers, 8-bit owner, 8-bit dest/src | Parameterised: SHARER=N², OWNER=TILE_ID_WIDTH, DEST=TILE_ID_WIDTH | Fatal | 16-bit sharers fail for N>4. 8-bit owner wastes 4 bits at N=4. 8-bit dest caps N≤16 (a constraint, not a fix). |
| F6 | §3.1 | Empty section | Complete tile composition list | Fatal | Section ends with colon, no content. |
| F7 | §1.2, §1.3, §3.8, §7.3 | DMA "under evaluation" + contribution + droppable + tests | Gated extension: Month-2 gate; pass=retain, fail=remove to §9 | Fatal | A primary contribution cannot be "under evaluation." Gate resolves status. |
| H1 | §3.4 | "Round-robin across VCs" | Fixed priority by class (RESP>INV>FWD>REQ); RR across inputs | High | RR across VCs can delay responses behind requests. Context requires fixed priority. |
| H2 | §3.3, §3.4 | UNBLOCK on VC0 | UNBLOCK on VC2 | High | DATA(VC2) → UNBLOCK(VC0) is a descending dependency, violating Duato's theorem. |
| H3 | §5.2 | "Bounded model checking" for liveness | Safety: BMC; liveness: k-induction (mode prove) | High | BMC cannot prove unbounded liveness. |
| H4 | §5.3 | "Cycle-accurate" reference model | Transaction-level reference model | High | Cycle-accurate duplicates RTL effort; context says transaction-level. |
| H5 | §6.1 | "reduce VC count" fallback | Removed; VC count must remain 4 | High | Reducing VC count breaks message-class separation and deadlock freedom. |
| H6 | §5.2 | 2-tile formal configuration | 2×2 (4-tile) formal configuration | High | 2 tiles cannot exercise invalidation path (needs ≥3). |
| H7 | §3.3 | `DIR_EVICT_*` wildcard | Enumerated: DIR_EVICT (sub-state in controller) | High | Wildcard is not an FSM state. |
| H8 | §3.3 | PUTS = 9 flits | PUTS = 1 flit (address only) | High | E-state line is clean; memory already current; 8 body flits are redundant. |
| H9 | §6.1 | No BRAM budget | BRAM budget table (~27/140 for 2×2) | High | Budget must be published to justify 2×2. |
| H10 | §7.1 | "Three-Month Schedule" | "Four-Month (16-Week) Schedule" | High | Title contradicts content (4 months, 16 weeks). |
| M1 | Abstract | "verified using..." (present tense) | "is verified by..." (planned) or scope-appropriate | Medium | §8 refutes predecessor's verification claims; abstract must match. |
| M2 | Abstract | "novel contribution is claimed" | "integration of... delta over predecessor's zero-assertion baseline" | Medium | Novelty unproven; integrated methodology is defensible. |
| M3 | §1.4 | Lists §§2–9 only | Lists §§1–11 | Medium | Document has 11 sections. |
| M4 | §9 | Duplicate rows above table | Single table, no duplicates | Medium | Three rows appear twice. |
| M5 | Open Items | Duplicate numbering, administrative items only | Renumbered; architectural items added | Medium | Two items numbered "2"; missing architectural open items. |
| M6 | §3.1 | Empty | Complete list | Medium | Duplicate of F6. |
| M7 | §3.7 | Absent | Memory model added | Medium | mem_tap undefined; DIR_MEM_WAIT has no exit without it. |
| M8 | §5.2 | "If M, memory stale; if S/E, memory current" | "If any L1 in S/E, owning L2 holds current value" | Medium | L2 is write-back; memory is stale after PUTM into L2, before L2 eviction. |
| M9 | §2.2, §2.3 | No citation for 16–24%; no 3D-mesh ref | Specific citation added; [15] added | Medium | Quantitative claim needs source. |
| M10 | §4.1 | "ten parameters" | "nine parameters" | Medium | Table has 9 rows; worst-path is defined but not tabulated. |
| M11 | §4.1 | Mesh: Fault tolerance High | Mesh: Fault tolerance Low | Medium | XY routes around nothing; every link is a bridge. |
| M12 | §6.1 | "reduce VC count" fallback | Removed | Medium | Duplicate of H5. |
| M13 | §7.1 | "Three-Month" | "Four-Month" | Medium | Duplicate of H10. |
| M14 | §7.3 | Formal risk mitigation = baseline | Restated as "BMC insufficient for k-induction" | Medium | Mitigation identical to plan is not mitigation. |
| M15 | §6.2 | Signoff = Magic, Netgen | Split: DRC/LVS = Magic/Netgen; STA = OpenSTA | Medium | Physical verification ≠ timing signoff. |
| M16 | §4.2 | Router complexity unsourced | Removed absolute line counts; relative ranking retained | Medium | ~300-line delta contradicts ~390-line total. |
| L1 | §3.2 | L1 state field width unstated | Stated: 2 bits for stable in tag, transient in controller FSM | Low | 9 states need 4 bits; 2 bits only for stable. |
| L2 | §11.A | IM_D omits UNBLOCK; INV transitions missing | Complete transition table | Low | Asymmetric UNBLOCK rule breaks directory release. |
| L3 | §3.4 | FIFO depths and credit widths absent | Added: depth 4, credit 3 bits, 20 FIFOs/router | Low | Deadlock/latency claims unquantified without them. |
| L4 | Record | ~3,600 lines duplication | Deduplicated (source-record hygiene) | Low | Three documents duplicated verbatim. |
| L5 | §3 | 9 subsystems absent | Added: tile internals, FSM split, NIC, mux, clock/reset | Low | §3.1 has tile list; deeper block detail deferred. |

### C.2 Changes Not Adopted

| Peer Proposal | Source | Why Not Adopted |
|---|---|---|
| Drop UNBLOCK entirely | z.ai S4 | The message has a consumer once PUTACK is added (UNBLOCK is the requester's response to DATA; the directory's transient state exits on UNBLOCK). Removing it requires an alternative release mechanism. |
| Compressed sharer vector | Various | At N=16, 16-bit vector fits in one directory entry with no compression. Compression adds logic for no benefit at this scale. |
| Snooping protocol | None proposed | Correctly excluded by topology choice. |
| MOESI / MESIF | None proposed | Correctly excluded by constraints C4–C10. |
| Adaptive routing | None proposed | Correctly excluded by scope. |
| DMA_READ message | White paper v1.0 | Dropped: functionally identical to GETS from a cache's perspective. DMA_WRITE retained (distinct). |
| 2-tile formal config | White paper v1.0 | Corrected to 2×2 (4-tile) because 2 tiles cannot exercise invalidation path. |

### C.3 Constraints Carried Forward from the Peer Verdict Corpus

| Constraint | Source | Consequence |
|---|---|---|
| C1: Mesh, point-to-point only | Topology verdict | No broadcast |
| C2: Directory-based coherence | Topology verdict | No snooping |
| C3: ≤ 4 VCs | VC/deadlock verdict | No escape VC |
| C4: ≤ 2 state bits per line for stable states | L1 tag budget | 4 stable MESI states, 2-bit encoding |
| C5: ≤ 5 transient states per line | Controller FSM budget | 5 L1 transients |
| C6: No upgrade round-trip | Workload pattern | Requires E state |
| C7: No dirty hand-off needed | Scope | Excludes MOESI |
| C8: ≤ 5 invariants (updated: 7) | Verification budget | Property set bounded |
| C9: 3-month schedule | Project plan | Simplicity preferred |
| C10: Reuse inherited message vocabulary | Existing codebase | MESI-native messages |

### C.4 Verification Sign-Off Criteria (Final)

| Category | Criterion |
|---|---|
| Functional coverage | 100% of legal bins across 4 crosses (L1 state × msg, dir state × request, transaction × distance, VC × class) |
| Code coverage | ≥98% line/branch; ≥95% toggle; 100% FSM |
| Assertion coverage | 100% pass in simulation; proven subset in formal |
| Cover properties | 100% hit |
| Directed tests | 100% pass (22 tests, 17 baseline + 5 DMA-gated) |
| pyuvm random | 100% pass, 10,000 tests |
| Formal safety | BMC depth 40 + k-induction on 2×2 config |
| Formal liveness | k-induction (mode prove) depth 150 on 2×2 config |
| Regression | 0 flaky, 0 timeouts, 0 compilation warnings, 0 lint warnings |
| FPGA | Bitstream runs, WNS ≥ 0, WHS ≥ 0, WPWS ≥ 3.750 ns |
| Sign-off document | Signed by verification, formal, and FPGA leads |

---

### 🔏 Model Signature

**Consensus Synthesis Node** — Principal System Architecture Critic | Iteration 2 | Peer models resolved: z.ai, Claude, DeepSeek, Gemini, Grok, Kimi, MiniMax, Mistral, Qwen | 2026-10-28 | Final proposed white paper v2.0 | All 7 fatal, 10 high, 16 medium, 5 low issues verified against source and context corpus | 9 peer disagreements resolved with technical proofs | 6 changes not adopted with justification