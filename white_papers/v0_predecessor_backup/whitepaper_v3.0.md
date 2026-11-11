# A Scalable Cache-Coherent Tiled Multicore Architecture on a 2D Mesh Network-on-Chip

**Version 3.0 — Unified Final Specification**

*Single consolidated white paper reconciling all six model drafts (Qwen, Mistral/GLM-5.3, MiniMax, Grok, Gemini, DeepSeek). Every contested point is adjudicated in §13 (Cross-Model Adjudication Ledger), where each model's position, the ruling, and the proof basis are recorded.*

---

## Abstract

This white paper specifies a cache-coherent tiled multicore architecture built on a 2D mesh Network-on-Chip. The design is parameterised on the mesh dimension *N* and is evaluated at two configurations: 4×4 (16 tiles) in simulation and 2×2 (4 tiles) on the AMD Xilinx Zynq-7000 XC7Z020 FPGA. Each CPU tile contains a private L1 cache, a bank of a distributed shared L2 cache with a separate directory array, a Network Interface Controller (NIC), a four-stage 5-port router, and a local behavioural memory tap. Coherence is maintained by a directory-based MESI protocol carried as multi-flit packets over the mesh. Four virtual channels separate request, forward, response, and invalidation traffic; together with deterministic XY routing and credit-based flow control this yields a three-layer deadlock-freedom guarantee, stated in §4.6 with its two explicit premises (receptivity *R* and fairness *F*). A flat full-map directory bounds the architecture at *N* ≤ 16 tiles. Verification combines directed tests, a transaction-level reference model in a pyuvm/cocotb environment, a 42-assertion SystemVerilog Assertion (SVA) set bound non-invasively via `bind`, and formal checking with SymbiYosys — safety by bounded model checking (BMC), bounded liveness with a derived bound *T*, and deadlock freedom by k-induction on top of the structural proof. FPGA implementation targets the ZedBoard XC7Z020 at 100 MHz; Sky130 ASIC implementation is future scope. A coherent DMA device tile is defined as a **Month-2 gated optional extension** and is not claimed as a contribution of this version. The contribution is a complete, open, reproducible verification flow for directory MESI on a packet-switched NoC, with every protocol state, message, encoding, and proof obligation enumerated to formal-verification grade — a stated delta over the predecessor design's zero-assertion, state-only-checking baseline.

**Keywords:** Cache coherence, MESI, directory protocol, Network-on-Chip, 2D mesh, virtual channels, deadlock freedom, FPGA, formal verification, UVM, pyuvm, SymbiYosys

---

## 1. Introduction

### 1.1 Motivation

Modern processors scale performance by adding cores rather than by raising clock frequency. Each core maintains a private cache for low-latency access to frequently used data. When multiple cores cache the same memory block, the system must guarantee that every core observes a consistent view of memory. This is the cache coherence problem.

The interconnect that carries coherence messages between cores must scale with the core count. A shared bus serialises all traffic and becomes a bottleneck beyond a handful of cores. A Network-on-Chip replaces the bus with a packet-switched fabric in which multiple transfers proceed in parallel.

This white paper specifies a cache-coherent tiled multicore architecture combining a directory-based MESI protocol with a 2D mesh NoC. The design is a continuation of the CDAC VLSI project, rebuilt from first principles with a corrected architecture, a rigorous verification plan, and a realistic implementation path.

### 1.2 Scope

**In scope (baseline):**

- Parameterised *N*×*N* 2D mesh NoC; flat full-map directory bounded at *N* ≤ 16 (§3.7)
- 4×4 configuration for simulation; 2×2 for FPGA
- MESI directory coherence with a separate, non-inclusive directory array and an explicit Directory Transaction Record (§3.3, §3.7)
- Four virtual channels with a stated class-dependency rule (§3.5, §4.6)
- Multi-flit packets with wormhole switching and a header-resident length field (§3.8)
- Behavioural per-tile memory tap (§3.9)
- Ordering contract: per-address ordering only (§3.10)
- Formal verification with SymbiYosys (BMC safety, derived-bound liveness, k-induction deadlock freedom)
- Directed and constrained-random verification with pyuvm; 42 bound SVA assertions (§5)
- FPGA implementation on ZedBoard XC7Z020
- ASIC flow on Sky130 as future scope

**In scope (gated extension):**

- Coherent DMA device tile — adopted only if the Month-2 gate (§3.11, §7.1) is passed. Gate criterion: DMA channel FSM, register map, and one end-to-end transfer pass simulation by end of Week 8. If the gate is missed, the DMA tile and its two messages are removed from the baseline and moved to §9; message codes 1100–1101 revert to *Reserved* and are not reassigned.

**Out of scope:**

- Processor core RTL (stimulus via testbench)
- Pipeline hazard handling
- Memory consistency beyond per-address coherence — no fences, no atomics, no cross-address ordering (§3.10)
- Dynamic voltage and frequency scaling, cache compression, non-volatile memory
- Adaptive routing, multi-level directories, and any *N* > 16 configuration (§3.7)
- DRAM timing, ECC, refresh, bank interleaving, prefetching (behavioural tap only)

### 1.3 Primary Contributions

1. **Scalable tiled architecture** with a parameterised mesh topology and a distributed full-map directory whose every field width is derived from a single tile-count parameter, with the *N* ≤ 16 bound stated rather than implied.
2. **Integrated verification methodology** combining directed tests, a pyuvm constrained-random environment with a transaction-level reference model that checks **data values** and not only state, a 42-assertion SVA set bound via `bind`, and a SymbiYosys formal campaign with separately stated safety, bounded-liveness, and deadlock obligations. The delta over the predecessor is the reference model (absent) and the assertion set (zero → 42).
3. **Explicit three-layer deadlock-freedom argument** (§4.6) with two named premises — receptivity *R* and fairness *F* — rather than an assertion that virtual channels alone suffice.
4. **Engineering baseline** demonstrating measurable scaling from 2×2 (FPGA) to 4×4 (simulation), with a published per-module resource budget.

*The DMA device tile is deliberately **not** claimed as a contribution: it is a Month-2-gated extension (§3.11). A primary contribution cannot simultaneously be "under evaluation" and "droppable".*

### 1.4 Document Structure

§2 reviews related work. §3 specifies the architecture (3.1 tiles, 3.2 cache hierarchy, 3.3 protocol, 3.4 message set, 3.5 NoC and virtual channels, 3.6 address map and tags, 3.7 directory transaction record, 3.8 packet format, 3.9 memory model, 3.10 ordering contract, 3.11 DMA). §4 justifies design decisions, including the deadlock proof. §5 presents the verification plan. §6 covers implementation. §7 gives the project plan. §8 reconciles claims against artifacts. §9 states future scope. §10 gives references. §11 gives appendices (FSM tables, encodings, message×VC cross, formal property list). §12 lists open items. §13 records the cross-model adjudication ledger.

---

## 2. Related Work

### 2.1 Cache Coherence

Snooping protocols broadcast every miss to all caches. The Illinois protocol [1] is an early example and an ancestor of MESI. Snooping does not scale, because broadcast traffic grows with the core count.

Directory protocols record which caches hold each block. Censier and Feautrier [2] introduced the concept. The Stanford DASH multiprocessor [3] made it practical for scalable machines. The Primer on Memory Consistency and Cache Coherence [4] provides the standard taxonomy of stable and transient states and the message vocabulary (GetS, GetM, Fwd\_\*, Inv, Put\*, Unblock) reused in this design. Sorin, Hill, and Wood [5] give the companion treatment of memory ordering.

Martin, Hill, and Sorin [6] argue that on-chip coherence remains necessary and that its cost is manageable when the tracking structures are modest. This design follows that position: a full-map sharer vector is the only per-line tracking structure, and it is bounded at 16 bits (§3.2, §3.7).

### 2.2 Distributed Shared Caches

Kim, Burger, and Keckler introduced Non-Uniform Cache Architectures [7], contrasting static NUCA (address-interleaved bank mapping) with dynamic NUCA (data migrates toward the requester). Zhang and Asanović [8] proposed victim replication and reported meaningful average-memory-access-latency reductions on their simulated tiled CMP; the reported figures are configuration-specific and are not generalised here. This design uses static NUCA with address-interleaved banks.

### 2.3 On-Chip Networks

Dally and Towles argued that chips should route packets, not wires [9], and established the mesh as the standard manycore topology in the 3D mesh study [10]. Benini and De Micheli framed the NoC as a new SoC paradigm [11]. The textbook by Dally and Towles [12] covers topology, routing, flow control, and deadlock, including the channel-dependency formulation used in §4.6. Duato's theory [13] and Dally and Seitz [14] provide the general conditions for deadlock freedom in wormhole networks, including the message-dependency formulation.

Ring topologies have the lowest router complexity but linear average distance and constant bisection bandwidth. Meshes scale better. Torus topologies reduce hop count further but require virtual channels or separate physical networks to avoid deadlock. Production manycore designs (Intel mesh, AMD Infinity Fabric) and the OpenPiton framework [15] use meshes for these reasons.

### 2.4 Verification of Coherence Protocols

Directed testing covers expected cases. Constrained-random stimulus finds corner cases. Formal verification proves invariants. The three are complementary.

UVM [16] is the industry standard for constrained-random verification. pyuvm [17] brings UVM structure to Python and integrates with cocotb. SymbiYosys [18] provides open-source formal verification with SystemVerilog Assertions, bounded model checking, and k-induction. Bounded model checking is a bounded refutation technique and cannot by itself discharge unbounded liveness claims [19]; induction-based methods [20] are required. This distinction governs §5.3.

### 2.5 Positioning of This Work

Each verification technique above is established prior art individually, and combinations are also known. The contribution claimed is therefore **not novelty of the ingredients** but a specific, falsifiable integration: a 42-assertion SVA set bound to a directory-MESI implementation over a packet-switched 2D mesh, checked against a transaction-level reference model that validates data values, with numeric coverage-closure criteria (§5.4) and a published artifact list (§8, §12). §8 records the predecessor state (zero assertions, state-only checks) as the baseline this improves upon. A related-work delta table against [15]–[18] is a required deliverable of the submission package (§12).

---

## 3. Architecture Specification

### 3.1 Tile Organisation

A **CPU tile** is structurally identical across the mesh:

| # | Block | Function |
|---|---|---|
| 1 | Core / stimulus interface | Master port for load/store/flush requests; no fence or atomic opcode is supported |
| 2 | L1 cache | Private; 4 sets × 4 ways × 64 B = 1 KB; write-back, write-allocate; tree-PLRU; MESI per line |
| 3 | L2 bank | Shared, distributed; 8 sets × 4 ways × 64 B = 2 KB; one bank per CPU tile; tree-PLRU |
| 4 | Directory array | Separate from the L2 data and tag arrays; one 24-bit entry per L2 line (32 entries), padded to 32 bits |
| 5 | NIC | Packetisation, message-class → VC assignment, credit management, TX/RX FIFOs |
| 6 | Router | Single 5-port mesh router module (LOCAL, N, S, E, W); 4 stages; 4 VCs per port; unused ports tied off |
| 7 | Memory tap | Behavioural backing store for this tile's home address slice; connects **only** to the L2/directory controller (fills and write-backs). It is **not** on the network datapath — the NIC connects directly to the router LOCAL port (supersedes earlier pass-through wording) |
| 8 | Intra-tile mux | Routes local vs. remote requests; routes incoming packets by message type. **An L1 miss on a line homed at this tile is routed directly to the local L2/directory controller — no NIC or NoC traversal** |

A **DMA device tile** (gated, §3.11) is a structural *variant*, not an identical tile: a core-less DMA engine with two channels and a memory-mapped register file, an L1-lite cache (2 sets × 2 ways × 64 B), a NIC, and a router. It has **no L2 bank, no directory, and no memory tap**. It is a consumer of coherence, not a provider: the directories of the other tiles track its copies exactly as they track an ordinary cache.

### 3.2 Cache Hierarchy

**L1 cache (private, per CPU tile):**

- 4 sets × 4 ways × 64 B = 1 KB (16 lines)
- Write-back, write-allocate
- **Tree-PLRU, 3 bits per set** (12 bits per tile) — adjudicated policy, see §13 item J
- MESI state per line: 4 stable encodings (2 bits) in the tag word + 5 transient states in the controller FSM (§3.3)

**L2 bank (shared, distributed):**

- 8 sets × 4 ways × 64 B = 2 KB (32 lines per bank)
- Tree-PLRU, 3 bits per set (24 bits per bank)
- Separate directory array: 32 entries × 24 bits used, padded to 32 bits for BRAM alignment
- 4×4 baseline: 16 banks = **32 KB**; with the DMA tile enabled: 15 banks = **30 KB**

**Directory entry (parameterised):**

| Field | Width (general) | Width (4×4) | Meaning |
|---|---|---|---|
| State | 3 | 3 | 4 stable + 4 transient codes, exactly saturated (§3.3) |
| Owner | `TILE_ID_W = ⌈log₂(TILE_COUNT)⌉` | 4 | Tile ID of the exclusive owner (valid in DIR_E, DIR_M) |
| Sharers | `TILE_COUNT = N²` | 16 | Full-map vector; bit *t* = 1 iff tile *t* holds a shared copy |
| Valid | 1 | 1 | Entry in use |
| **Used** | `3 + TILE_ID_W + N² + 1` | **24** | Padded to 32 bits |

**Parameter derivation (single source of truth):**

| Quantity | Formula | N=2 | N=4 | N=8 |
|---|---|---|---|---|
| TILE_COUNT | N² | 4 | 16 | 64 |
| TILE_ID_W | ⌈log₂TILE_COUNT⌉ | 2 | 4 | 6 |
| SHARER_W | TILE_COUNT | 4 | 16 | 64 |
| DIR entry used bits | 3 + TILE_ID_W + N² + 1 | 10 | 24 | 74 |

**Inclusion policy.** The L2 bank is a write-back cache of its home slice. It holds the current value of every home block **except** while the directory is in DIR_M or DIR_FWD_WAIT with a dirty owner, during which the only current copy resides in the owner's L1 and the bank's copy is stale. The L1 is private and is *not* inclusive of the L2; the directory is **non-inclusive bookkeeping only** — it stores state, owner, and sharers, never data. This policy is stated explicitly because "inclusive caches" wording in [6] does not describe this design.

**Bank access and fill path (resolved ambiguity).** The L2 bank presents a **single serialized access port** to the directory controller: local L1 fills, remote NoC requests and memory-tap fills/write-backs all queue behind it (the service order is not fixed by this specification). On a DIR_MEM_WAIT fill the directory reads the **L2 data array first** and consults the memory tap **only on a bank (tag) miss**, installing the fetched line into the victim way (DIR_EVICT first if a victim is required); PUTM and DATAFWD write dirty data into the bank; DIR_EVICT/WRITE_BACK writes bank to tap. While DIR_M with a dirty owner the bank copy is stale and the owner's L1 is authoritative.

**Owner-field redundancy.** The Owner field is redundant with the Sharers vector (the owner is by construction the unique tile whose sharer bit is set in DIR_E/DIR_M). It is retained because formal property A2.3 requires the directory to name the owner explicitly, which removes a bit-scan from the RTL critical path.

### 3.3 MESI Coherence Protocol

**Four stable L1 states:**

| State | Meaning |
|---|---|
| Modified (M) | Only copy, dirty; home bank and memory stale |
| Exclusive (E) | Only copy, clean; home bank and memory current |
| Shared (S) | Read-only copy; other copies may exist; home bank current |
| Invalid (I) | No valid copy |

**L1 transient states (5):**

| State | Meaning | Entry | Exit event |
|---|---|---|---|
| IS_D | I → S/E, waiting for data | Load miss (I) | DATA (shared → S; exclusive → E) |
| IM_D | I → M, waiting for data | Store miss (I) | DATA (exclusive → M) |
| SM_D | S → M, upgrade in flight | Store hit (S) | DATA (exclusive → M) |
| EI_A | E → I, awaiting release ack | Eviction (E) | PUTACK → I |
| MI_A | M → I, awaiting release ack | Eviction (M) | PUTACK → I |

*SM_D exits on DATA alone.* INVACKs are delivered to the **directory**, never to the requester; the requester cannot observe them, so they cannot be an exit condition of the requester's FSM (§13 item M).

**Directory states — 4 stable + 4 transient = 8 codes, exactly saturating the 3-bit SRAM field:**

| Code | State |
|---|---|
| 000 | DIR_I |
| 001 | DIR_S |
| 010 | DIR_E |
| 011 | DIR_M |
| 100 | DIR_MEM_WAIT |
| 101 | DIR_FWD_WAIT |
| 110 | DIR_INV_WAIT |
| 111 | DIR_EVICT |

The eviction sub-states and the GETS/GETM discriminator required to resolve DIR_FWD_WAIT are held in the **Directory Transaction Record (DTR)** in the L2 controller, not in the SRAM entry (§3.7). **The 3-bit field has zero encoding headroom; any future directory state requires re-layout of the entry.** This is stated as a cost, not hidden.

**Single-exit rule.** Each transient state field has exactly one exit event: DIR_MEM_WAIT, DIR_FWD_WAIT, and DIR_INV_WAIT exit on **UNBLOCK**; DIR_EVICT exits when the victim is fully resolved (final INVACK/PUTM received and any dirty write-back committed) into DIR_MEM_WAIT. Intermediate events (MEM_DATA, DATAFWD, INVACK, PUTM) advance DTR progress counters and sub-state only; they never change the SRAM state field on their own. This makes every directory transient a single-exit state — the property that makes the bounded-liveness proof in §5.3 meaningful, and the property the predecessor's dead `PROXY_WAIT` state violated.

**Normative protocol rules:**

1. **PUTS carries no data.** A copy in S or E is clean by definition; the home bank and memory already hold the current value. PUTS is a 1-flit release notification. Sending body flits on a clean eviction would be pure bandwidth waste.
2. **No eviction is silent.** An L1 that evicts a line in S or E **must** send PUTS; an L1 that evicts a line in M must send PUTM. A silent drop leaves a stale sharer bit, which falsifies the directory-consistency property A2.2 (sharers must equal the S-mask) and can wedge DIR_INV_WAIT.
3. **INV excludes the requester.** When the directory services a GETM from tile *T* while in DIR_S, INV is sent to every sharer **except *T***. *T*'s sharer bit is cleared on entering DIR_INV_WAIT; the exit condition is `Sharers == 0`. This closes the (SM_D, INV) self-invalidation race at its source.
4. **INVACK counting is bit-clearing, not a counter.** Each sharer receives exactly one INV, so bit-clearing is bijective with counting; it is also **idempotent**, so a late PUTS and an in-flight INVACK from the same tile cannot double-count. No separate counter field exists in the DTR.
5. **Response to INV.** An L1 holding the line in S or E sends INVACK. An L1 holding the line in M first sends PUTM (dirty data) and then INVACK, so the count remains one-INV-to-one-INVACK. An L1 in state I receiving an INV responds INVACK unconditionally (defensive rule, formally checked — it covers the evict-during-invalidate race).
6. **Receptivity (Premise R).** An L1 with an outstanding miss on line *A* must continue to accept and service incoming INV/DATA/INVACK traffic for *other* lines immediately, on a path independent of its miss path. Incoming messages for line *A* itself cannot occur, by Lemma L1 (§4.6).
7. **UNBLOCK in a stable state is a no-op.** UNBLOCK is required only to release a transient; the directory ignores it in stable states and asserts it is not carrying an unmatched transaction.

**Message set — 12 core messages (complete and minimal) + 2 gated DMA messages:**

| Code | Message | Direction | Class | VC | Flits | Purpose |
|---|---|---|---|---|---|---|
| 0000 | GETS | L1 → dir | REQ | VC0 | 1 | Request shared copy |
| 0001 | GETM | L1 → dir | REQ | VC0 | 1 | Request exclusive copy |
| 0010 | PUTS | L1 → dir | REQ | VC0 | 1 | Release clean copy (S or E) |
| 0011 | PUTM | L1 → dir | REQ | VC0 | 9 | Write back dirty copy (M) |
| 0100 | UNBLOCK | L1 → dir | RESP | VC2 | 1 | Data installed; release directory transient |
| 0101 | INV | dir → L1 | INV | VC3 | 1 | Invalidate / recall |
| 0110 | INVACK | L1 → dir | RESP | VC2 | 1 | Invalidation acknowledged |
| 0111 | DATA | dir → L1 | RESP | VC2 | 9 | Data delivery (exclusive bit in control) |
| 1000 | FWD_GETS | dir → owner | FWD | VC1 | 1 | Forward shared request |
| 1001 | FWD_GETM | dir → owner | FWD | VC1 | 1 | Forward exclusive request |
| 1010 | DATAFWD | owner → dir | RESP | VC2 | 9 | Owner returns data to the home directory |
| 1011 | PUTACK | dir → L1 | RESP | VC2 | 1 | Release acknowledged; exits EI_A / MI_A |
| 1100 | *DMA_WRITE* | DMA → dir | REQ | VC0 | 9 | *(Gated)* write with inline data |
| 1101 | *DMA_ACK* | dir → DMA | RESP | VC2 | 1 | *(Gated)* DMA completion |
| 1110 | Reserved | — | — | — | — | Not decoded by any RTL |
| 1111 | Reserved | — | — | — | — | Not decoded by any RTL |

**Why these three messages are the load-bearing fixes.** (a) **PUTACK** (code 1011): without it EI_A and MI_A have no consuming event — an orphan transient, which the design's own "no orphan transient" invariant forbids; its absence was fatal defect F2 in the predecessor. (b) **UNBLOCK on VC2, not VC0**: it is causally downstream of DATA(VC2); placing it on VC0 creates a descending DATA(VC2)→UNBLOCK(VC0) dependency. (c) **DATAFWD to the directory, not to the requester**: the forward data path is owner → home directory → requester, so the dirty write-back lands in the L2 bank *before* the DIR_M/DIR_S transition (required by the inclusion policy of §3.2), and the directory directly observes forward completion while still holding the requester in its UNBLOCK-wait state (needed by Lemma L1, §4.6).

**DMA message minimality.** *DMA_READ is not defined*: from the coherence protocol's perspective a DMA read is a GETS issued by the DMA tile's L1-lite — same class, same VC, same directory path, same DATA response; the source tile ID in the header distinguishes it. *DMA_WRITE* is retained because write-with-inline-data performs no fetch-before-write and is genuinely distinct from GETM. *DMA_ACK* signals completion to the DMA register file. This resolves the six-way disagreement in §13 item G.

### 3.4 Protocol Sequences (normative walkthroughs)

| Sequence | Path |
|---|---|
| Load miss, line in DIR_I | L1: IS_D, GETS → dir: DIR_MEM_WAIT, mem_tap read → dir: DATA(excl=0/1) → L1: S or E, UNBLOCK → dir: DIR_S / DIR_E |
| Store miss, line in DIR_I | L1: IM_D, GETM → dir: DIR_MEM_WAIT → DATA(excl=1) → L1: M, UNBLOCK → dir: DIR_M |
| Silent upgrade | L1 in E stores: E → M locally, **no message**; the owner's L1 is authoritative for E-versus-M (Appendix B, note 1) |
| Two readers | dir DIR_S: GETS → reply DATA, add sharer, no transient |
| Upgrade with invalidation | L1 in S stores: SM_D, GETM → dir DIR_S → clear requester bit, INV to sharers \ {T} → INVACK ×n until Sharers == 0 → DATA(excl=1) → requester M, UNBLOCK → dir DIR_M |
| Forward, clean owner | dir DIR_E + GETS(other): DIR_FWD_WAIT, FWD_GETS → owner replies DATAFWD to dir → dir writes bank, sends DATA → requester UNBLOCK → dir DIR_S (pending_op = GETS) |
| Forward, dirty owner | dir DIR_M + GETM(other): DIR_FWD_WAIT, FWD_GETM → owner sends DATAFWD(dirty) to dir → dir updates bank, sends DATA(excl=1) → requester UNBLOCK → dir DIR_M (pending_op = GETM) |
| L1 clean eviction | L1: EI_A (or S direct), PUTS → dir DIR_E/DIR_S → clear owner/sharer, PUTACK → L1: I |
| L1 dirty eviction | L1: MI_A, PUTM(9) → dir: write bank, clear owner, PUTACK → L1: I |
| L2 victim, shared | dir DIR_EVICT (sub-state INV_SHARERS): INV to sharers → INVACK ×n → (dirty? WRITE_BACK) → DIR_MEM_WAIT, proceed with fill |
| L2 victim, owned | dir DIR_EVICT (sub-state RECALL_OWNER): INV to owner → owner sends PUTM (if M) then INVACK → WRITE_BACK → DIR_MEM_WAIT |

### 3.5 Network-on-Chip and Virtual Channels

**Topology.** 2D mesh. One 5-port router module is instantiated at every tile position; unused edge/corner ports are tied off and synthesis prunes the tied-off logic (a corner tile has 3 active ports but uses the same module).

**Routing.** XY deterministic: X first, then Y. The VC index is assigned at the source NIC from the message class and is **never changed by any router** (VC preservation — this premise is load-bearing for §4.6 Layer 1).

**Flow control.** Credit-based per VC: 3-bit credit counter initialised to the downstream FIFO depth of 4. A flit is transmitted only when a credit is available; a credit returns when the downstream FIFO advances. Buffer occupancy is therefore always ≤ depth.

**Virtual channels (4 per port):**

| VC | Class | Messages | FIFO depth |
|---|---|---|---|
| VC0 | REQ | GETS, GETM, PUTS, PUTM, *DMA_WRITE* | 4 flits |
| VC1 | FWD | FWD_GETS, FWD_GETM | 4 flits |
| VC2 | RESP | DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, *DMA_ACK* | 4 flits |
| VC3 | INV | INV | 4 flits |

**Switching.** Wormhole: the header flit reserves the output path; body flits follow; the path is released when the packet's final flit is transmitted, determined by counting against the header's length field (§3.8).

**Pipeline.** Four stages — RC (route compute), VA (VC allocation), SA (switch arbitration), ST (switch traversal) — giving 4 cycles of hop latency. Per-router buffering: 5 ports × 4 VCs × 4 flits × 64 b = 5 120 b = 640 B (10 KB across 16 routers).

**Arbitration (two levels, with a bounded-wait escape).**

1. **VC arbitration per input port:** fixed priority by *class* — **RESP > INV > FWD > REQ** — so protocol-critical responses and invalidations are never queued behind request traffic.
2. **Starvation escape (Premise F):** fixed priority alone is not fair to the most heavily loaded class (every L1 miss injects REQ). Therefore an arbiter **age counter** overrides the fixed order: a VC that has waited ≥ 8 arbitration rounds is granted next. Every VC with pending traffic is thus served within a bound of at most 8 rounds, which is exactly the fairness premise the liveness proof of §5.3 requires.
3. **Switch arbitration per output port:** round-robin across input ports, preventing input starvation.

This synthesises the majority position (fixed class priority: Qwen, Mistral, Grok, Gemini, DeepSeek) with the minority objection (REQ starvation under pure fixed priority: MiniMax) — see §13 item H. Deadlock freedom does **not** depend on the arbiter (§4.6); the arbiter choice is a liveness and QoS question.

### 3.6 Address Map and Tag Decomposition

The home-tile mapping is **range-based and contiguous**: the tile index is taken from a contiguous group of high-order line-address bits, so a tile owns a contiguous address slice; decode is closed-form and requires zero logic.

**4×4 configuration (16 tile slots):**

| Bits | Field | Width |
|---|---|---|
| [31:15] | L2 tag field | 17 |
| [14:11] | Home tile (X, Y) | 4 |
| [10:8] | L2 set index | 3 |
| [7:6] | L1 set index | 2 |
| [5:0] | Byte offset | 6 |

**2×2 configuration (4 tile slots):**

| Bits | Field | Width |
|---|---|---|
| [31:13] | L2 tag field | 19 |
| [12:11] | Home tile (X, Y) | 2 |
| [10:8] | L2 set index | 3 |
| [7:6] | L1 set index | 2 |
| [5:0] | Byte offset | 6 |

**The L1 set index and the L2 set index are disjoint.** This is a hard requirement, not a preference. The predecessor layout placed the L2 set at [8:6], which *contains* the L1 set [7:6]; for a fixed L1 set only 2 of the 8 L2 sets are then reachable, so one L1 set is backed by 2 × 4 × 64 B = 512 B — less than the 1 KB L1 itself — and conflict behaviour becomes correlated between the two levels. The layout above gives every L1 set access to all 8 L2 sets.

**Stored tag widths (corrected decomposition):** the stored tag is *every line-address bit except the index bits and the bits constant per bank*. Line address = addr[31:6].

| Cache | Index | Constant-per-bank | Stored tag | Value (4×4) | Value (2×2) |
|---|---|---|---|---|---|
| L1 (every tile) | [7:6] | — | addr[31:8] | 24 b | 24 b |
| L2 (per bank) | [10:8] | home [14:11] / [12:11] | {addr[31:15], addr[7:6]} / {addr[31:13], addr[7:6]} | **19 b** | **21 b** |

Note that the L2 tag is **non-contiguous**: the L1 set bits [7:6] lie *below* the L2 index [10:8] but above the offset, so they are line-identity bits that must be compared. Storing addr[31:15] alone (17 bits) would alias lines differing only in [7:6] into the same L2 way — a correctness bug present in several draft versions (§13 item E). The home bits are excluded because they are constant within a bank; comparing them would be redundant.

**Parameterisation and the scaling bound.** Every coherence width derives from `TILE_COUNT`. A full-map sharer vector is 1 bit per tile, so the entry grows linearly: 24 bits at 16 tiles, 74 bits at 64 tiles. **A flat full-map single-level directory is optimal only up to 16 tiles; the design is therefore bounded at N ≤ 16.** The 8-bit tile-ID fields in the RTL (256 tiles) do not extend that bound — the sharer vector binds first. The claim "scales to hundreds of tiles" is removed. The 32-bit address map with the [14:11] home field accommodates N ≤ 16 without change; N > 16 requires a wider address map *and* a hierarchical or limited-pointer directory (§9).

**Reserved home range under DMA.** When the DMA tile is enabled it occupies one mesh slot and has no L2 bank, so the home-tile code of that slot has no directory. That code is declared **reserved/unmapped**: requests decoding to it are a protocol error and are caught by assertion A8.4. This costs 1/16 of the decode space, which is immaterial for a behavioural 256 MB model.

### 3.7 Directory Transaction Record (DTR)

Because the 3-bit state field is exactly saturated, the following information is held in a **per-bank** DTR in the L2 controller:

| Field | Width | Meaning |
|---|---|---|
| Pending op | 3 b | GETS, GETM, PUT, EVICT, DMA (5 used codes) |
| Pending requester | `TILE_ID_W` | Tile that will receive the grant / release |
| Evict sub-state | 2 b | NONE, INV_SHARERS, RECALL_OWNER, WRITE_BACK |
| Evict victim | tag + set + way | Line being resolved when a fill needs a victim way |
| Victim dirty | 1 b | Whether WRITE_BACK is required |

*(The evict sub-states correspond to MiniMax's EVICT_NONE / EVICT_INV / EVICT_FWD / EVICT_WB, renamed for precision: RECALL_OWNER is the owned-victim path, which is driven by INV rather than by a forward.)*

The DTR is the single source of the discriminators the SRAM state field cannot hold:

- **DIR_FWD_WAIT is deterministic.** The pair `(DIR_FWD_WAIT, UNBLOCK)` has two legal successors; `pending_op` selects DIR_S (GETS) or DIR_M (GETM). The transition function is therefore a function, which is a precondition for any equivalence check against a reference model. *(The predecessor's two rows for `(DIR_FWD_WAIT, DATAFWD)` were fatal defect F1.)*
- **One outstanding transaction per bank.** The DTR implies the bank is blocked while a transient is open; concurrent requests to other lines in that bank queue in the NIC and are the source of the bounded-service requirement in §5.3. This premise is stated explicitly because both the single-exit rule and Lemma L1 depend on it.
- **No outstanding-ack counter.** Sharer-bit clearing (§3.3 rule 4) subsumes it and is idempotent; a counter would double-decrement on a late PUTS.

### 3.8 Packet and Flit Format

The flit is 64 bits. A packet is one header flit followed by zero or more body flits.

**Header flit:**

| Bits | Field | Width | Meaning |
|---|---|---|---|
| [63:56] | Dest tile | 8 (logical `TILE_ID_W`, 8 reserved) | Destination tile ID; 8-bit field supports N ≤ 16, unused high bits zero |
| [55:48] | Src tile | 8 (logical `TILE_ID_W`) | Source tile ID |
| [47:44] | Msg type | 4 | Appendix C |
| [43:42] | VC ID | 2 | **Checked field**: must equal class(msg); asserted by the NIC and by formal invariant I3, never used as a routing input |
| [41] | Head | 1 | First flit of a packet |
| [40] | Tail | 1 | Set only on single-flit packets (head = tail = 1) |
| [39] | Write enable | 1 | Memory/bank write indication |
| [38] | Exclusive | 1 | DATA grants exclusive ownership |
| [37:32] | **Length (LEN)** | **6** | **Total flits in the packet, 1–63** |
| [31:0] | Address | 32 | Line address of the transaction |

**Body flit:** 64 bits of pure payload; no control bits. **The packet is delimited by the header's LEN field** — the router counts flits as they pass and releases the output when the count completes. Body flits therefore keep 100 % payload bandwidth.

*Why not a tail bit in every body flit:* a 63-bit payload would require ⌈512/63⌉ = 9 body flits per 64 B line, raising every line transfer from 9 to 10 flits — an 11 % increase in NoC occupancy for no benefit. *Why not a 4-bit LEN:* it caps packets at 16 flits and leaves 2 reserved bits for no purpose; 6 bits uses the whole reserved field with headroom.

**Packet sizes:**

| Class | Messages | Header | Body | Total |
|---|---|---|---|---|
| Control | GETS, GETM, PUTS, UNBLOCK, INV, INVACK, FWD_GETS, FWD_GETM, PUTACK, *DMA_ACK* | 1 | 0 | 1 |
| Cache line | PUTM, DATA, DATAFWD, *DMA_WRITE* | 1 | 8 | 9 |

All coherence transfers are single-cache-line granularity. The predecessor's "DMA bulk up to 16 flits" is deleted: 15 body flits is 120 B, not a whole number of cache lines, and it had no defined address/length semantics. Multi-block DMA is future scope (§9).

### 3.9 Memory Model

The backing store is a per-tile behavioural **memory tap**. It is a simulation model, not a DRAM controller.

| Parameter | Value |
|---|---|
| Physical address width | 32 bits (full decode, §3.6) |
| Modelled window | 256 MB at 0x0000_0000 (sparse beyond) |
| Data width | 64 B per line |
| Access latency | 1 cycle |
| Instances | One per CPU tile; **not shared**; serves only addresses homed at that tile |
| Coherence participation | None — the backing store does not participate; the directory does |
| DRAM timing, ECC, refresh, bank interleaving, prefetch | Not modelled (future scope) |

**Address regions:**

| Region | Range | Purpose |
|---|---|---|
| Memory | 0x0000_0000 – 0x0FFF_FFFF | 256 MB backing store |
| Unmapped | 0x1000_0000 – 0xEFFF_FFFF | Reserved; A8 catches access |
| DMA registers | 0xF000_0000 – 0xF000_FFFF | DMA control window (gated) |
| Test addresses | 0xFFFF_FF00 / FF04 / FF08 | Return 0xDEADBEEF / the address / a counter |

The tap has two roles: it answers its L2 bank's **cold (bank tag) misses** and **write-backs** (DIR_MEM_WAIT fill on a bank miss, DIR_EVICT WRITE_BACK), and it is accessed **only by the L2/directory controller**. It is **not on the network datapath**: the NIC connects directly to the router LOCAL port; the earlier wording that the tap "also passes non-memory packets to and from the NIC" is superseded. Because coherence guarantees exactly one dirty copy per line, the home tap always holds the authoritative value for its home addresses once a line is not in DIR_M.

### 3.10 Ordering and Consistency Contract

**Per-address ordering is guaranteed and is serialised at the home directory. Cross-address ordering is not guaranteed.** Memory fences, atomic operations, and a memory consistency model are out of scope: the design contains no core, no load/store queue, and no mechanism to issue ordering instructions; adding them would require core integration and litmus-test verification.

The practical consequence: a multithreaded program must not assume that writes to *different* addresses are observed in program order. The design provides coherence, not consistency. *(A "sequential consistency" claim appearing in one draft is rejected as contradicting the design's own out-of-scope list — §13 item I.)*

### 3.11 DMA Engine (Gated Optional Extension)

**Status: not part of the baseline.** The DMA device tile is adopted only if the Month-2 gate is passed (§7.1, Week 8): 4×4 mesh simulated clean, pyuvm regression green, all formal safety properties discharged, and one end-to-end DMA transfer passing simulation. If the gate fails, DMA moves to §9, codes 1100–1101 revert to *Reserved* and are not reassigned, and no RTL change is required.

When active:

- **Structure:** device tile with a two-channel DMA engine, memory-mapped registers, L1-lite (2 × 2 × 64 B), NIC, router; **no L2 bank, no directory, no memory tap**.
- **Coherence:** standard MESI via the existing 12 core messages plus DMA_WRITE and DMA_ACK; **no new directory states**, because DMA requests map onto existing paths (a DMA read is a GETS; a DMA write maps onto the GETM path with inline data).
- **Tile slot cost:** 4×4 → 15 CPU tiles + 1 DMA tile = 15 L2 banks = 30 KB; the 16-bit sharer vector is exactly saturated (15 CPU L1s + 1 DMA L1-lite); one home code is reserved (§3.6).
- **Register map (per channel):** SRC_LO 0x00, DST_LO 0x04, LEN 0x08 (must be 64 in baseline), CTRL 0x0C, STATUS 0x10, COUNT 0x14.
- **Directed tests 18–22 are conditional on the gate.**

### 3.12 Resolved ambiguities (diagram generation, 2026-10-28)

Four points in §3 were not stated precisely enough to draw a unique datapath. They were adjudicated as follows; the resolution is now normative and the relevant sections above were amended.

| # | Ambiguity | Resolution | Where stated |
|---|---|---|---|
| R1 | Physical path of a same-tile L1 miss (a miss on a line homed at its own tile) | **Direct to the local L2/directory controller via the intra-tile mux — no NIC or NoC traversal.** | §3.1 block 8 |
| R2 | L2 bank access model among (a) local L1 fills, (b) remote NoC requests, (c) memory-tap fills/write-backs | **Single serialized bank port behind a bank arbiter; all three sources queue. Service/queue order is not fixed by this specification.** | §3.2, "Bank access and fill path" |
| R3 | Fill / dirty-data path (§3.9 and Appendix B "fill from the memory tap" vs. §3.2 "bank holds the current value") | **Bank first, tap on bank miss**: DIR_MEM_WAIT reads the L2 data array first and consults the tap only on a bank (tag) miss; PUTM/DATAFWD write the bank (dirty lives in the bank); DIR_EVICT/WRITE_BACK writes bank → tap; in DIR_M the owner's L1 is authoritative and the bank copy is stale. | §3.2, "Bank access and fill path"; §3.9 |
| R4 | Memory-tap datapath ("also passes non-memory packets to and from the NIC") | **NIC ↔ router directly; the tap connects only to the L2/directory controller (fills and write-backs). The pass-through sentence is superseded wording.** | §3.1 block 7; §3.9 |

---

## 4. Design Decisions and Justification

### 4.1 Topology Comparison

Seven topologies compared on nine parameters. *Worst path* is defined in the source metric list but is not tabulated, because it is a strict function of wire length and hop count already tabulated.

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

The "3" at N = 4 for the mesh is the count of *active* ports at corner tiles, not a different router: one 5-port module is instantiated everywhere and unused ports are tied off.

**Total wire length (tile-pitch units), including wrap-around link cost:**

| N | Bus | Xbar | Ring | Mesh | Torus |
|---|---|---|---|---|---|
| 4 | 2 | 8 | 5 | 4 | 8 |
| 16 | 4 | 64 | 18 | 24 | 48 |
| 64 | 8 | 512 | 70 | 112 | 224 |

These figures are derived, not estimated: an *n*×*n* mesh has 2*n*(*n*−1) internal links of one pitch, giving 2M(M−1) for M = √N; a torus adds 2M wrap-around links of (M−1) pitches, giving 4M(M−1); a bus spans the floorplan diagonal, ⌈√N⌉; a tree has depth 2log₂N.

**Full comparison at N = 64:**

| Parameter | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
|---|---|---|---|---|---|---|---|
| Ports/router | 1 | 64 | 3 | 5 | 5 | 3 | 64 |
| Worst hop | 1 | 1 | 32 | 14 | 8 | 12 | 2 |
| Paths | 1 | 1 | 2 | Very many | More | 1 | 1 |
| Wire length | 8 | 512 | 70 | 112 | 224 | 192 | 64 |
| Deadlock risk | Low | Low | High | Low | High | Low | High |
| RTL complexity | Low | High | Low | Medium | High | Medium | Low |
| Synthesis congestion | Low | Very High | Medium | Low | High | Medium | Very High |
| Fault tolerance | Low | Low | Low | **Low** | Medium | Medium | Low |
| Scalability | Poor | Poor | Weak | Good | Good | Good | Poor |

**Fault tolerance is rated Low for the mesh.** Under deterministic XY routing every link is a bridge: removing any single link partitions the graph and no alternative path exists. The metric is *route around a broken link*, which this design cannot do without adaptive routing (out of scope). A torus offers two disjoint routes per dimension (Medium); a single node failure still isolates it. Neither rating can be raised without adaptive routing or duplicated links.

### 4.2 Why 2D Mesh

1. **Port count is constant at 5.** A crossbar needs 64 ports at N = 64; a mesh needs 5.
2. **Hop count grows as √N.** A ring's worst hop grows as N/2: at 64 tiles, mesh = 14, ring = 32.
3. **Wires are short.** Every mesh link connects adjacent tiles; a ring needs one long wrap-around wire, a torus two.
4. **Deadlock-free with XY routing**, and VC preservation keeps the per-VC channel sets disjoint (§4.6 Layer 1).
5. **Low synthesis congestion** — no link crosses the chip, so place-and-route can meet timing.
6. **Scales to the 16-tile ceiling of this design** (§3.6); the RTL itself instantiates any *N*×*N*.
7. **Industry standard** — Intel mesh, AMD Infinity Fabric, OpenPiton [15].
8. **Low RTL complexity** — the router is one small module (routing, VC allocation, arbitration, crossbar, credits, header decode) reused at every position.

### 4.3 Why Not Other Topologies

- **Bus:** bandwidth does not scale; one transfer at a time; capacitive loading at high *N*.
- **Crossbar:** wire count grows as N²; at N = 64, 4096 links — not routable.
- **Ring:** hop count grows as N/2; long wrap-around wire; cyclic channel dependency under coherence traffic (the predecessor's documented deadlock risk).
- **Torus:** wrap-around wires cross the chip; wire length is twice the mesh's at every size; at 4 tiles a 2×2 torus is degenerate (the same pair joined twice).
- **Tree:** hot spot at the root; coherence traffic is not uniform, so the root bottlenecks.
- **Star:** hub has *N* ports; single point of failure; does not scale.

### 4.4 Cache Parameters

| Parameter | Value | Justification |
|---|---|---|
| Line size | 64 B | Industry standard; 8 body flits × 64 b fills a line exactly — zero padding |
| L1 sets × ways | 4 × 4 | 1 KB; low conflict misses; fits FPGA LUT/BRAM budget |
| L2 sets × ways | 8 × 4 | 2 KB/bank; 32 directory entries per bank; 8 sets match the 3-bit index |
| L1 replacement | Tree-PLRU, 3 b/set | 12 b/tile; at 4 ways the hit-rate delta vs. true LRU is ~1 %, immaterial at 1 KB; one policy for both levels keeps the reference model and assertions single-sourced (§13 item J) |
| L2 replacement | Tree-PLRU, 3 b/set | 24 b/bank; deterministic; exact policy stated (not generic "pseudo-LRU") to prevent implementer ambiguity |
| Write policy | Write-back, write-allocate | Standard for coherent caches; makes the silent E→M upgrade meaningful |
| Total LRU state | 15 × 12 b + 15 × 24 b = 540 b | Registers, not memory |

Tree-PLRU at 4 ways is a 3-node binary tree: 3 bits per set record which subtree was accessed least recently. The alternative — true LRU (minimum 5 bits/set by ⌈log₂4!⌉, 6 for a pairwise scheme, 8 with age counters) — was proposed by three drafts; it is rejected here on specification-uniformity grounds, not area grounds, and the counter-argument is recorded in §13 item J.

### 4.5 Virtual Channel Assignment

Four VCs separate the message classes so that a request never shares a buffer with a response and an invalidation never shares a buffer with data. The numeric VC index carries **no ordering meaning** for the deadlock proof (§4.6); it matters only for arbitration priority (§3.5). UNBLOCK and PUTACK ride VC2 because they are causally downstream of DATA/PUT; placing them on VC0 would reintroduce a descending dependency. INVACK rides VC2 (it is a response) even though it is caused by INV(VC3) — this is precisely the edge case that forces the corrected class-graph statement in §4.6 rather than the naïve "no message is ever sent on a lower-numbered VC than the message that caused it" rule, which is **false** for INV→INVACK.

### 4.6 Deadlock Freedom — Three-Layer Argument with Two Premises

No single layer is sufficient; the guarantee is their conjunction.

**Layer 1 — Network (acyclic channel dependency).**
Under XY routing on a mesh, the channel-dependency graph (CDG) of a single virtual channel is acyclic: every X-channel dependency precedes every Y-channel dependency and no Y→X turn exists. Because the VC index is assigned at the source NIC and never changed by a router, the physical channel sets of distinct VCs are **disjoint**, and the extended CDG is the disjoint union of acyclic graphs over disjoint vertex sets — hence acyclic. Network-level deadlock freedom therefore holds for any *N*, independent of the arbitration policy and of the protocol.

**Layer 2 — Protocol (inter-class dependency).**
Rank the classes REQ(0) < FWD(1) < INV(2) < RESP(3). Enumerating every causal message dependency of §3.3/§3.4:

| Cause | Effect | Edge |
|---|---|---|
| GETS / GETM (REQ) | DATA (RESP) | 0 → 3 |
| GETM (REQ) | INV (INV) | 0 → 2 |
| PUTS / PUTM (REQ) | PUTACK (RESP) | 0 → 3 |
| FWD_GETS / FWD_GETM (FWD) | DATAFWD (RESP) | 1 → 3 |
| INV (INV) | INVACK (RESP) | 2 → 3 |
| last INVACK (RESP) | DATA (RESP) | intra-class |
| DATA (RESP) | UNBLOCK (RESP) | intra-class |

Every **inter-class** edge ascends in rank, so the inter-class dependency graph is acyclic with topological order REQ → FWD → INV → RESP, and RESP is terminal (no outgoing inter-class edge). The only **intra-class** edges are within RESP; intra-class dependencies are discharged by Layer 1 (the per-VC CDG of VC2 is acyclic) plus Premise R below. *This is the correct statement: the common draft rule "no message is ever sent in a class lower than the class that caused it" fails on INV(VC3)→INVACK(VC2), and the equally common rule "the class graph is acyclic" is formally false while a RESP→RESP self-edge exists. Neither formulation is used here.*

**Layer 3 — Resource (bounded occupancy).**
Under credit-based flow control the receiver's buffer occupancy never exceeds its depth, by induction on the credit count: initialised to the depth, decremented on transmit, incremented on receipt. No agent holds a network buffer while in a protocol transient — transients are agent-local register states — so protocol waits cannot become channel dependencies.

**Premise R (receptivity).** An L1 with an outstanding miss on line *A* continues to accept and service INV, DATA, and INVACK traffic for other lines; its snoop-response path is independent of its miss path and consumes no miss-handling slot. The L1 supports at most one outstanding miss (MSHRs are future scope), which bounds the formal state space.

**Premise F (fairness).** Every VC with pending traffic is served within at most 8 arbitration rounds (§3.5 escape counter), and the fabric delivers transmitted flits. Liveness is claimed *under* this premise; without it, strict priority would permit REQ starvation and the liveness properties of §5.3 would be false.

**Lemma L1 (no same-line message during a transient).** No L1 receives a message for a line on which it has an outstanding miss, other than the DATA that completes it. Proof sketch: (i) the directory blocks its bank until UNBLOCK (single outstanding transaction per bank, §3.7), so no second transaction for that line can be launched; (ii) INV excludes the requester (§3.3 rule 3); (iii) a forward cannot be issued for a line whose directory transient is open. The defensive rules (I + INV → INVACK) cover the residual evict-during-invalidate race and are formally checked.

**Consequence.** Deadlock freedom is not a property of "four VCs" alone: it requires Layer 1 (XY + VC preservation), Layer 2 (ascends inter-class graph), Layer 3 (credits), Premise R, and Premise F together. Removing a VC does not merely reduce performance — it merges two classes, destroys Layer 2, and invalidates the proof; hence **the VC count is frozen at 4** in every fallback path (§6.1, §7.3).

---

## 5. Verification Plan

Three techniques are used and are not conflated: directed tests for expected cases, constrained-random stimulus for corner cases, formal checking for invariants. Each obligation below states its method, its bound, and its configuration.

### 5.1 Directed Tests

| # | Test | Purpose |
|---|---|---|
| 1 | Load miss, local home | DIR_I → DIR_MEM_WAIT → DIR_E; memory fill path |
| 2 | Load miss, remote home | Cross-tile GETS, NoC round trip |
| 3 | Store miss, local home | DIR_I → DIR_M |
| 4 | Store miss, remote home | Cross-tile exclusive grant |
| 5 | Silent E→M upgrade | Local transition, no directory traffic |
| 6 | Sharing (two readers) | DIR_E → DIR_FWD_WAIT → DIR_S, sharer tracking |
| 7 | Upgrade with invalidation | DIR_S → DIR_INV_WAIT → DIR_M; multi-INVACK completion (≥3 tiles) |
| 8 | Forward from remote owner | DIR_E and DIR_M paths; owner write-back before serving the forward |
| 9 | L1 clean eviction (S/E) | PUTS → PUTACK; sharer/owner bit cleared |
| 10 | L1 dirty eviction (M) | MI_A → PUTM → PUTACK → I |
| 11 | L2 eviction of a shared victim | DIR_EVICT/INV_SHARERS → multi-INVACK → resume fill |
| 12 | L2 eviction of an owned dirty victim | DIR_EVICT/RECALL_OWNER → PUTM + INVACK → WRITE_BACK → fill |
| 13 | Back-to-back requests from two tiles | Directory serialisation, arbitration |
| 14 | Concurrent requests to the same line | Per-address ordering, race resolution |
| 15 | Mesh saturation | Multi-hop injection, credit stalls |
| 16 | Invalidation storm | Many INVs to one tile; VC3 FIFO stress; Premise R |
| 17 | Timeout and recovery | Orphan-transient detection within bound *T* |

**DMA tests (conditional on the §3.11 gate):**

| # | Test | Purpose |
|---|---|---|
| 18 | DMA read single block (GETS path) | Basic DMA read |
| 19 | DMA write single block (DMA_WRITE) | Write with inline data |
| 20 | DMA read while a CPU tile reads | Contention on the same line |
| 21 | DMA write while a CPU tile holds the line in M | Hardest case: invalidation of a dirty CPU copy |
| 22 | Back-to-back DMA transfers | Channel overlap, timeout handling |

Every test checks **final state *and* data values** in every participating L1, every L2 bank, the directory, and the memory tap. State-only checking is the predecessor defect this rule exists to prevent.

### 5.2 SVA Assertion Set (42 assertions, 8 categories)

42 assertions bound to the DUT with `bind` (non-invasive: the design is not modified to accommodate them):

| Category | Count | Type | Scope |
|---|---|---|---|
| A1 — MESI invariants | 5 | Safety | L1 arrays |
| A2 — Directory invariants | 7 | Safety | Directory arrays |
| A3 — Message protocol | 6 | Safety | NIC interfaces |
| A4 — Flow control | 8 | Safety | Router ports |
| A5 — Bounded liveness | 4 | Liveness | Controllers, FIFOs |
| A6 — Data integrity | 4 | Safety | L2 array, memory |
| A7 — State machine legality | 4 | Safety | Controllers |
| A8 — Address and routing | 4 | Safety | NIC, router |
| **Total** | **42** | | |

Principal properties:

| ID | Property | Type | Description |
|---|---|---|---|
| A1.1–A1.2 | Single writer | Safety | At most one L1 in M; at most one L1 in E, for any line |
| A1.3 | No E/M alongside S | Safety | A line in S excludes any E or M copy |
| A1.4 | M excludes all others | Safety | If any L1 is in M, every other L1 is invalid for that line |
| A1.5 | Shared data equality | Safety | All S copies hold identical data |
| A2.1 | DIR_I ⟺ unheld | Safety | DIR_I iff no L1 holds the line |
| A2.2 | Sharer accuracy | Safety | DIR_S ⟹ sharers equal the S-mask exactly (no stale bits) |
| A2.3 | Owner validity | Safety | DIR_E/DIR_M ⟹ exactly one holder, equal to Owner, Owner < TILE_COUNT |
| A2.4 | DIR_I ⟹ empty | Safety | DIR_I ⟹ sharers = 0 and valid = 0 |
| A2.5 | Owner qualification | Safety | Owner is consulted only in DIR_E/DIR_M; in all other states Owner is ignored and must not be read by the RTL |
| A2.6 | Owner ∈ sharers | Safety | DIR_E/DIR_M ⟹ Owner < TILE_COUNT and sharers = {Owner} |
| A2.7 | Transient well-formedness | Safety | A DIR_*_WAIT entry ⟹ valid = 1 and DTR.pending_op ≠ NONE |
| A3.x | Message protocol | Safety | Every request is answered; no response without a request; correct destination |
| A4.x | Flow control | Safety | 0 ≤ credit ≤ FIFO depth; no transmission at credit 0; no flit loss or duplication |
| A6.x | Data integrity | Safety | Write-then-read returns the written value; home bank current whenever any L1 holds the line in S or E and no DIR_M is open |
| A7.x | FSM legality | Safety | No illegal transition; each transient exits only via its defined event |
| A8.x | Address/routing | Safety | Correct home tile; XY turn order; A8.4 rejects the reserved DMA home code |
| I1–I7 | Network invariants | Safety | XY path correctness; `flit.VC == class(flit.msg)`; credit invariant; per-VC FIFO ordering; delivery or protocol termination |

*The A1.x, A2.x, A4.x, A6.x, A8.x subsets are additionally **proved formally**; the remainder are checked in simulation. "Checked in simulation" and "proved formally" are kept distinct throughout — the predecessor had zero assertions.*

*Bookkeeping: the **42 bound SVA** are exactly the eight categories A1–A8 (5+7+6+8+4+4+4+4). The seven **network invariants I1–I7** (XY path correctness, `flit.VC == class(flit.msg)`, credit invariant, no transmission at zero credit, per-VC FIFO ordering, delivery-or-termination) are **formal-only properties proved in SymbiYosys** and are not part of the 42-item simulation-bound set — 42 + 7 = 49 properties in total. Any report that claims "42 assertions" must not silently include I1–I7, and any report that claims "49" must say so.*

### 5.3 Formal Verification (SymbiYosys)

**Two proof obligations are stated separately and never conflated.**

**Configuration: the 2×2 (4-tile) mesh.** Four tiles is the minimum that exercises a multi-sharer invalidation fan-out (2 sharers + 1 requester) and the 4-bit/2-bit home-tile decode; a 2-tile model cannot generate three-requester interleavings at all. The remaining coverage boundary is disclosed, not hidden:

| Scenario | Minimum tiles | Covered at 2×2 (4 tiles)? |
|---|---|---|
| Single-sharer invalidation | 2 | Yes |
| Single-owner forward (DIR_E / DIR_M) | 2 | Yes |
| Silent E→M upgrade | 2 | Yes |
| Multi-sharer invalidation fan-out | 3 | Yes |
| DIR_M with two concurrent GETS | 3 | Yes |
| Two distinct home tiles | 4 | Yes |
| **Interior 5-port router** (all 2×2 tiles are corners) | 9 | **No** |
| **≥3 sharers, distinct homes simultaneously** | 5+ | **No** |

The uncovered scenarios are covered by the directed and constrained-random campaigns on the 4×4 configuration. This substitution is stated as a known limitation of the formal scope, not presented as equivalent coverage.

**Safety — proved by BMC.** Method: `mode bmc`, depth **K = 64** (≥ 2× the worst-case coherence round trip on 2×2, see *T* below), plus `mode prove` (k-induction) as the primary engine where tractable. Properties: A1.1–A1.5, A2.1–A2.7, A3, A4, A6, A7, A8, and the formal-only invariants I1–I7.

**Bounded liveness — stated with an explicit bound and an explicit fairness premise.** BMC is a bounded refutation technique and cannot discharge an unbounded `eventually` claim [19]; therefore no unbounded liveness claim is made.

| Property | Form |
|---|---|
| No orphan transient | Every transient state field exits within **T** cycles |
| No message loss | Every request receives a response within **T** cycles |
| Bounded service | Every VC with pending traffic is served within 8 arbitration rounds (Premise F) |

**Derivation of *T*.** The longest coherence transaction is GETM → INV → INVACK → DATA → UNBLOCK: five fabric traversals. Worst-case Manhattan distance is 2 hops at 2×2 and 6 hops at 4×4; the router pipeline is 4 cycles/hop.

- **Formal (2×2):** 5 × 2 × 4 = 40 cycles of fabric + ≤ 24 cycles of NIC/controller/memory-tap overhead ⇒ **T = 64 cycles**. A BMC depth below *T* would be unsound: a full remote transaction could not complete and every liveness property would pass vacuously.
- **Simulation (4×4):** 5 × 6 × 4 = 120 + 30 overhead ⇒ **T = 150 cycles** for the bound used by the A5 assertions in regression.

**Deadlock freedom — structural proof discharged by k-induction.** The three-layer argument of §4.6 is stated as a documented lemma (it is *N*-independent and cannot be obtained from bounded checking); SymbiYosys `mode prove` with target **k = 16** confirms the lemma's premises on the modelled instance — that the VC index is preserved, that the inter-class edges ascend, and that the credit invariant holds.

### 5.4 UVM Environment (pyuvm + cocotb)

| Component | Function |
|---|---|
| Test | Top-level stimulus |
| Environment | Container for agents and scoreboard |
| Agent (per tile) | Driver + monitor + sequencer |
| Scoreboard | Compares DUT output against the reference model |
| Reference model | **Transaction-level** Python model of MESI directory coherence |
| Coverage collector | Functional coverage |

**Reference model: transaction-level, not cycle-accurate.** It processes transactions in order, computes the correct state *and data* after each, and hands the result to the scoreboard. Shadow structures: per tile/set/way L1 state, tag, MESI state, data; per bank/set/way L2 state, tag, data, directory entry; a global address→data memory map; a set of outstanding transactions used to detect lost messages. Timing and protocol-ordering defects are caught by the SVA set and the formal proofs, not by the model. A cycle-accurate model would duplicate the RTL effort and must be re-synchronised with every RTL change — the reason the "cycle-accurate" claim of the predecessor drafts is corrected (§13 item D).

**Scoreboard compares after every transaction:** L1 state, L1 data, L2 state, L2 data, directory state, directory owner, directory sharers, memory contents.

**Simulators (named explicitly — a build without a named simulator is not a plan):** **Verilator** for constrained-random regression, **Vivado xsim** for `bind`-based SVA simulation, **Yosys/SymbiYosys** for formal.

**Stimulus:** constrained-random sequences with coverage-driven closure.

**Coverage closure criteria (numeric, so closure can be signed off):**

| Metric | Target |
|---|---|
| Legal functional bins | 100 % |
| FSM states and transitions (L1 and directory) | 100 % |
| Assertions | 100 % pass, zero waivers |
| Cover properties | 100 % hit |
| Line / branch coverage | ≥ 98 % |
| Toggle coverage | ≥ 95 % |
| State × message cross (2×2 formal scope) | 100 % |
| State × message cross (4×4 simulation) | 100 % of the per-agent cross |
| Unreachable bins | Waived with written justification |

**Cross space is defined per agent, not per tile:** (9 L1 states × 14 messages) + (8 directory states × 14 messages) = 126 + 112 = **238 cross terms**, of which the legal subset is the closure target. Crossing the tile dimension (×16 → 3 808) is neither required by the stated properties nor tractable, and is therefore out of scope by construction rather than by accident.

### 5.5 Regression

Directed tests + pyuvm random tests + the bound SVA set + formal proofs run on every commit. CI via GitHub Actions installs and runs all three toolchains with **pinned versions** (Yosys, SymbiYosys, pyuvm, cocotb, Verilator, Vivado) so a regression failure is attributable.

---

## 6. Implementation Plan

### 6.1 FPGA Target (ZedBoard XC7Z020)

| Parameter | Value |
|---|---|
| Board | ZedBoard |
| Device | XC7Z020-CLG484-1 |
| LUTs | 53,200 |
| Flip-flops | 106,400 |
| BRAM (36 Kb tiles) | 140 (≈ 630 KB) |
| DSP slices | 220 |
| Clock | 100 MHz (10 ns) |
| Committed configuration | **2×2 mesh** |
| Simulation configuration | 4×4 mesh |

**Resource budget for 2×2 (first-order estimate; synthesis must confirm):**

| Resource | Available | Target | Ceiling | Risk |
|---|---|---|---|---|
| LUTs | 53,200 | ≤ 20,000 (38 %) | ≤ 40,000 (75 %) | Medium |
| FFs | 106,400 | ≤ 25,000 (24 %) | ≤ 50,000 (47 %) | Low |
| BRAM36 | 140 | ≤ 48 (34 %) | ≤ 70 (50 %) | Low–Medium |
| DSP | 220 | 0 | 0 | None (no multipliers inferred) |

**BRAM arithmetic (corrected).** A BRAM36 configures as 1024×36 or **512×72**, so a 2 KB bank (32 lines × 64 B) is **one** BRAM36 with a single 64-bit port, 4 with four parallel way ports, or 8 for a full 512-bit line read. The inherited figure of "15 BRAMs per bank", obtained by dividing 512 bits by the 36-bit width, ignores the 72-bit configuration *and* the array depth, and overstates the data array by 2–15×.

| Per CPU tile (2×2) | BRAM36 |
|---|---|
| L1 data (16 lines × 64 B) | 1 – 4 |
| L1 tag (16 × 24 b) | 0 – 1 (LUTRAM-capable) |
| L2 data (32 lines × 64 B) | 1 – 8 |
| L2 tag (32 × 19 b) | 0 – 1 (LUTRAM-capable) |
| Directory (32 × 32 b) | 1 |
| Router input FIFOs (5 ports × 4 VCs × 4 × 64 b) | 3 |
| NIC FIFOs | 1 – 2 |
| LRU state (registers) | 0 |
| **Total per CPU tile** | **7 – 20** |

| Configuration | BRAM36 (favourable array mapping) | BRAM36 (conservative array mapping) |
|---|---|---|
| 2×2, 4 CPU tiles | 28 | 80 |
| 4×4, 16 CPU tiles | 112 | 320 |

**LUT estimate.** Router ≈ 2 200–2 500 LUTs (5×5 crossbar ≈ 1 600, VC allocation/arbitration ≈ 400, control ≈ 200); L1/L2/directory controller ≈ 700 per tile; NIC ≈ 300 per tile.

- **2×2:** ≈ 13,000–19,000 LUTs (25–36 % of 53,200) — comfortably inside budget.
- **4×4:** ≈ 55,000 LUTs — **exceeds** 53,200.

**Conclusion.** The 2×2 configuration is the committed FPGA target; 4×4 is simulation-only. The binding constraints for 4×4 are **LUT capacity (≈55 k > 53.2 k)** and **BRAM margin (112–320 BRAM36 against 140 available — only the most favourable mapping even approaches the limit, and it leaves no margin)**. BRAM is *not* a constraint at 2×2 (28–80 of 140). This reverses the *reasoning* given in the predecessor draft (which rejected 4×4 on an arithmetic error) while keeping the *decision* unchanged; the decision now rests on sound arithmetic. A post-synthesis resource table (LUT/FF/BRAM at 2×2) must be appended to this section before the fit claim is closed (§12 item 5).

**Fallback if timing or fit fails** (in order): reduce cache associativity or set count; map tag/state arrays to LUTRAM; pipeline the router crossbar; reduce FPGA tile count. **The VC count must not be reduced** — merging the four classes destroys Layer 2 of §4.6 and invalidates the paper's own deadlock proof; if it is ever contemplated, the class-dependency graph must be re-derived and re-proven from scratch.

### 6.2 ASIC Target (Future Scope)

| Parameter | Value |
|---|---|
| Node | Sky130 |
| Flow | OpenLane |
| Synthesis | Yosys |
| Place and route | OpenROAD |
| DRC / LVS | Magic, Netgen |
| Timing signoff | OpenSTA (MCMM) |

Physical verification (Magic/Netgen) and timing signoff (OpenSTA) are separate steps and are listed separately.

### 6.3 Synthesis Flow

| Step | Tool |
|---|---|
| RTL elaboration | Verilator, Vivado xsim |
| Logic synthesis | Vivado (FPGA), Yosys (ASIC) |
| Place and route | Vivado (FPGA), OpenROAD (ASIC) |
| Static timing | Vivado Timing (FPGA), OpenSTA (ASIC) |
| Physical verification | Magic, Netgen (ASIC) |
| Bitstream | Vivado |

Tool versions are pinned for every entry; an unpinned flow is not evidence.

### 6.4 Timing Closure

| Constraint | Target |
|---|---|
| Clock period | 10 ns (100 MHz) |
| Setup uncertainty | 0.2 ns |
| Hold uncertainty | 0.1 ns |
| I/O delay | 2.0 ns max / 0.5 ns min |
| Reset synchroniser | False path declared |
| WNS | ≥ 0 ns |
| WHS | ≥ 0 ns |
| WPWS | ≥ 3.750 ns |
| TNS | 0 |
| Failing endpoints | 0 |
| Retiming | Enabled, except reset synchroniser, handshake paths, state registers |

**Critical paths and their mitigations (known in advance):**

1. L2 tag compare → directory state decision: split the tag compare and the directory lookup into separate pipeline stages.
2. Router arbitration → crossbar output: the 4-stage pipeline (RC/VA/SA/ST) separates arbitration from traversal.
3. NIC packet decode → cache interface: register the decoder output.

An XDC file is a named deliverable (§7.2 milestone 10). Its absence is one of the specific failures recorded against the predecessor in §8 and is not repeated here.

**Power:** total ≤ 50 mW, estimated pre-synthesis with the Xilinx Power Estimator and measured post-implementation with `report_power`.

---

## 7. Project Plan

### 7.1 Sixteen-Week (Four-Month) Schedule

*(Titled for what it contains: four months, sixteen weeks. The predecessor's "Three-Month Schedule" contradicted its own body.)*

| Month | Weeks | Milestone |
|---|---|---|
| 1 | 1–2 | Inherited bug fixes (DIR_I valid handling, `PROXY_WAIT` removal); RTL refactor |
| 1 | 3–4 | 2-tile mesh; directed tests 1–10 |
| 2 | 5–6 | 4×4 mesh, virtual channels, PUTACK path, PUTS 1-flit validation |
| 2 | 7–8 | pyuvm environment + transaction-level reference model; **DMA gate decision at Week 8 exit** |
| 3 | 9–10 | Formal properties (BMC + k-induction), 42-assertion SVA set bound and running |
| 3 | 11–12 | FPGA 2×2 synthesis, XDC, timing closure, bitstream on ZedBoard |
| 4 | 13–14 | Coverage closure, documentation, white paper finalisation |
| 4 | 15–16 | Paper draft, related-work delta table, IEEE submission |

### 7.2 Milestones

| # | Milestone | Week |
|---|---|---|
| 1 | Bug fixes complete | 2 |
| 2 | 2-tile mesh verified | 4 |
| 3 | 4×4 mesh simulation complete | 6 |
| 4 | PUTACK + 1-flit PUTS validated | 6 |
| 5 | pyuvm environment running | 8 |
| 6 | **DMA gate decision** | 8 |
| 7 | SVA set running in simulation | 10 |
| 8 | Formal proofs passing | 12 |
| 9 | FPGA bitstream on ZedBoard | 14 |
| 10 | XDC authored; timing closed (WNS/WHS ≥ 0) | 14 |
| 11 | Resource budget confirmed by synthesis | 14 |
| 12 | White paper finalised | 15 |
| 13 | Paper submitted | 16 |

### 7.3 Risks and Mitigations

| Risk | Probability | Mitigation |
|---|---|---|
| FPGA does not fit 2×2 | Low–Medium | LUT estimate has ≈ 3 × headroom; reduce associativity/sets, LUTRAM for tag arrays. **VC count is fixed at 4** and is not a fallback variable |
| Timing closure fails at 100 MHz | Medium | Reduce cache size, LUTRAM mapping, additional router pipeline stage, floorplanning |
| Formal proofs do not complete | Medium | Reduce BMC depth only down to *T* = 64; abstract data values to symbols; split properties by VC class. The 2×2 configuration is already the baseline, so it is not itself a fallback |
| Virtual channel deadlock | Low | Three-layer proof of §4.6 with premises R and F; discharged by k-induction |
| DMA gate not passed (Week 8) | High | DMA moves to §9; codes 1100–1101 revert to Reserved and are not reassigned; no RTL change |
| Coverage closure not reached | Medium | Numeric criteria of §5.4; unreachable bins waived with written justification |
| BRAM/LUT estimate wrong | Medium | Recompute per-bank budget before synthesis; resource table is a mandatory deliverable (§12 item 5) |
| Time overrun | Medium | Drop the ASIC flow from the submission package; DMA is already gated, so the baseline completes without it |

*A mitigation that restates the plan is not a mitigation; each row above names an action distinct from §7.1.*

---

## 8. Claims vs Artifacts Reconciliation

This section reconciles the original team's report against the artifacts they delivered.

| # | Original report claim | Artifact reality | Status |
|---|---|---|---|
| 1 | All RTL modules completed and verified | All modules present, but several have bugs | Partial |
| 2 | Remote-owner forwarding completed and verified | `is_fwd_remote_reply` tied to 0; `PROXY_WAIT` never entered | **Contradicted** |
| 3 | Synthesis results (WNS = +0.003 ns) | No Vivado project, no XDC, no reports in repo | **Unverifiable** |
| 4 | FPGA hardware validated on ZedBoard | No `fpga_top` module, no XDC in repo | **Unverifiable** |
| 5 | Five directed test cases pass | Testbench skips tests 3 and 5; state-only checks | Partial |
| 6 | Data correctness verified | No data-value checks | **Contradicted** |
| 7 | Directory `DIR_I` bug | Not mentioned in report | **Omitted** |

`PROXY_WAIT` names a state in the predecessor's implementation; it does not exist in this design and appears above only as a description of that defect.

**This paper's own claims and their status:**

| Claim | Status in this version |
|---|---|
| Architecture, protocol, address map, and verification plan are specified | **Complete — this document** |
| The 42-assertion SVA set exists and is bound to the design | Planned — milestone 7, Week 10 |
| Formal proofs pass | Planned — milestone 8, Week 12 |
| FPGA bitstream generated on ZedBoard | Planned — milestone 9, Week 14 |
| Post-synthesis resource table | Planned — milestone 11, Week 14 |
| A novelty claim for the verification methodology | **Withdrawn.** Contribution stated as a falsifiable integration (§2.5); delta table is §12 item 3 |
| Verification of the current design has been performed | **Withdrawn.** Present-tense verification claims are false against this document's own §7 schedule; the abstract states the plan |
| DMA as a contribution | **Withdrawn** — gated extension (§3.11), excluded from §1.3 |

The same standard this document applies to the predecessor is applied to itself: **no claim is stated without a defined artifact that will evidence it.**

---

## 9. Future Scope

| Item | Prerequisite |
|---|---|
| DMA device tile (if the Week-8 gate is missed) | Gate decision (§3.11) |
| Scatter-gather DMA (multi-block transfers) | Explicit length semantics; descriptor fetch path |
| Additional DMA channels / priority levels | Parameterised channel count; QoS at the NIC |
| ASIC tapeout on Sky130 | §6.2 flow executed |
| RISC-V core integration (hazard handling) | Core RTL; load/store queue |
| Adaptive routing (fault tolerance) | Turns model; new deadlock proof |
| Consistency model (atomics, fences) | Core + store buffer + litmus-test harness |
| MSHRs / non-blocking L1 | L1 FSM extension; relaxed receptivity rule |
| Hierarchical or limited-pointer directory | Required for any N > 16 (§3.6) |
| 8×8 mesh | Hierarchical directory **and** wider address map |
| Victim replication / dynamic NUCA | Data-migration engine |
| Real memory controller and DRAM model | AXI/TileLink interface replacing `mem_tap` |
| MOESI / MESIF exploration | Re-opens the minimality constraint C7 |
| Debug infrastructure (ILA/VIO) | FPGA bring-up |
| 4×4 on FPGA | LUT capacity (§6.1) |

---

## 10. References

[1] M. P. Papamarcos and J. H. Patel, "A Low-Overhead Coherence Solution for Multiprocessors with Private Cache Memories," *ISCA*, 1984.

[2] L. M. Censier and P. Feautrier, "A New Solution to Coherence Problems in Multicache Systems," *IEEE Trans. Computers*, vol. C-27, 1978.

[3] D. Lenoski et al., "The Directory-Based Cache Coherence Protocol for the DASH Multiprocessor," *ISCA*, 1990.

[4] V. Nagarajan, D. J. Sorin, M. D. Hill, and D. A. Wood, *A Primer on Memory Consistency and Cache Coherence*, 2nd ed., Morgan & Claypool, 2020.

[5] D. J. Sorin, M. D. Hill, and D. A. Wood, *Memory Ordering and Coherence*, Morgan & Claypool, 2011.

[6] M. M. K. Martin, M. D. Hill, and D. J. Sorin, "Why On-Chip Cache Coherence Is Here to Stay," *Communications of the ACM*, 2012.

[7] C. Kim, D. Burger, and S. W. Keckler, "An Adaptive, Non-Uniform Cache Structure for Wire-Delay Dominated On-Chip Caches," *ASPLOS X*, 2002.

[8] M. Zhang and K. Asanović, "Victim Replication: Maximizing Capacity while Hiding Wire Delay in Tiled Chip Multiprocessors," *ISCA-32*, 2005.

[9] W. J. Dally and B. Towles, "Route Packets, Not Wires: On-Chip Interconnection Networks," *DAC*, 2001.

[10] W. J. Dally and B. Towles, "The 3D Mesh of a Multicore Microprocessor," *ISCA*, 2001.

[11] L. Benini and G. De Micheli, "Networks on Chips: A New SoC Paradigm," *IEEE Computer*, 2002.

[12] W. J. Dally and B. Towles, *Principles and Practices of Interconnection Networks*, Morgan Kaufmann, 2004.

[13] J. Duato, "A New Theory of Deadlock-Free Adaptive Routing in Wormhole Networks," *IEEE Trans. Parallel and Distributed Systems*, 1993.

[14] W. J. Dally and C. L. Seitz, "Deadlock-Free Message Routing in Multicomputer Networks," *IEEE Trans. Computers*, 1987.

[15] J. Balkind et al., "OpenPiton: An Open Source Manycore Research Framework," *ASPLOS '16*, 2016.

[16] IEEE 1800.2-2020, *Universal Verification Methodology (UVM)*.

[17] pyuvm documentation, https://github.com/pyuvm/pyuvm

[18] SymbiYosys documentation, https://github.com/YosysHQ/sby

[19] A. Biere, A. Cimatti, E. M. Clarke, and Y. Zhu, "Symbolic Model Checking without BDDs," *TACAS*, 1999. *(BMC is a bounded technique; it does not establish unbounded liveness.)*

[20] M. Sheeran, K. Singh, and G. Stålmarck, "Checking Safety Properties Using Induction and a SAT Solver," *FMCAD*, 2000. *(Basis for the k-induction obligations in §5.3.)*

[21] Xilinx Inc., *Zynq-7000 SoC Data Sheet (DS190)* — device resources cited in §6.1.

---

## 11. Appendices

### A. L1 MESI State Transitions

| Current | Event | Next | Actions |
|---|---|---|---|
| I | Load miss | IS_D | Send GETS (VC0) |
| IS_D | DATA (shared) | S | Install, send UNBLOCK (VC2) |
| IS_D | DATA (exclusive) | E | Install, send UNBLOCK (VC2) |
| I | Store miss | IM_D | Send GETM (VC0) |
| IM_D | DATA (exclusive) | M | Install, write, send UNBLOCK (VC2) |
| S | Store hit | SM_D | Send GETM (VC0) |
| SM_D | DATA (exclusive) | M | Write the store data, send UNBLOCK (VC2). INVACKs go to the directory and are never an exit condition here |
| E | Store hit | M | Silent upgrade; no message; the L1 is authoritative for E-vs-M |
| M | Eviction | MI_A | Send PUTM (VC0, 9 flits) with the dirty line |
| MI_A | PUTACK | I | Release the way |
| E | Eviction | EI_A | Send PUTS (VC0, 1 flit, no data) |
| EI_A | PUTACK | I | Release the way |
| S | Eviction | — | Send PUTS (VC0, 1 flit); **not silent** — the directory must clear the sharer bit |
| S | INV received | I | Send INVACK (VC2) |
| E | INV received | I | Send INVACK (VC2) |
| M | INV received | I | Send PUTM (dirty data), then INVACK (VC2) |
| I | INV received | I | Send INVACK (VC2) — defensive; covers evict-during-invalidate |
| any | INV/DATA/INVACK for a **different** line | unchanged | Serviced immediately (Premise R); does not disturb the outstanding miss |
| any transient | timeout > *T* | error | A5 / test 17: orphan-transient detection |

### B. Directory State Transitions

Each transient **state field** has exactly one exit event (§3.3); intermediate events advance DTR progress only.

| Current | Event | Action | Next |
|---|---|---|---|
| DIR_I | GETS | Enter DIR_MEM_WAIT; `pending_op = GETS`; fetch from the memory tap | **DIR_E** on UNBLOCK (sole-copy clean grant enables silent upgrade) |
| DIR_I | GETM | Enter DIR_MEM_WAIT; `pending_op = GETM`; fetch | **DIR_M** on UNBLOCK |
| DIR_MEM_WAIT | MEM_DATA | Send DATA to the requester | — (awaiting UNBLOCK) |
| DIR_S | GETS | Reply DATA (no transient); add sharer | DIR_S |
| DIR_S | GETM from *T* | Enter DIR_INV_WAIT; clear *T*'s bit; send INV to sharers \ {*T*} | **DIR_M** on UNBLOCK (owner = *T*) |
| DIR_INV_WAIT | INVACK | Clear that sharer's bit (idempotent) | — |
| DIR_INV_WAIT | Sharers == 0 | Send DATA (exclusive) to the requester | — (awaiting UNBLOCK) |
| DIR_E | GETS, requester = owner | Reply DATA from the home bank | DIR_E |
| DIR_E | GETS, other | Enter DIR_FWD_WAIT; `pending_op = GETS`; send FWD_GETS | **DIR_S** on UNBLOCK |
| DIR_E | GETM, other | Enter DIR_FWD_WAIT; `pending_op = GETM`; send FWD_GETM | **DIR_M** on UNBLOCK |
| DIR_M | GETS, requester = owner | Reply DATA (owner is authoritative) | DIR_M |
| DIR_M | GETS, other | Enter DIR_FWD_WAIT; `pending_op = GETS`; send FWD_GETS | **DIR_S** on UNBLOCK (after DATAFWD update) |
| DIR_M | GETM, other | Enter DIR_FWD_WAIT; `pending_op = GETM`; send FWD_GETM | **DIR_M** on UNBLOCK (ownership transfer) |
| DIR_FWD_WAIT | DATAFWD | Write dirty data into the home bank; send DATA to the requester | — (awaiting UNBLOCK; `pending_op` selects the successor) |
| DIR_E | PUTS (owner) | Clear Owner; send PUTACK | DIR_I |
| DIR_S | PUTS (sharer) | Clear that sharer bit; send PUTACK | DIR_S (or DIR_I if no sharers remain) |
| DIR_M | PUTM (owner) | Write data into the home bank; clear Owner; send PUTACK | DIR_I |
| DIR_INV_WAIT / DIR_EVICT | PUTS from a tile already INV'd | Ignore the state change; the bit is already clear | unchanged (INVACK still arrives; idempotent) |
| any | Fill requires a victim | Enter DIR_EVICT; `evict_sub-state = INV_SHARERS` (victim shared) or `RECALL_OWNER` (victim owned) | — |
| DIR_EVICT / INV_SHARERS | Final INVACK | If dirty → WRITE_BACK, else → resolved | — |
| DIR_EVICT / RECALL_OWNER | PUTM + INVACK from owner | WRITE_BACK | — |
| DIR_EVICT / WRITE_BACK | Memory write committed (1 cycle) | Victim resolved; proceed with the pending fill | **DIR_MEM_WAIT** |
| any stable | UNBLOCK | No-op (assert no unmatched transaction) | unchanged |

**Notes.**

1. **DIR_E / DIR_M record the last known state of a sole owner.** Because the L1 performs a silent E→M upgrade without notifying the directory, the owner's L1 state is authoritative for E-versus-M; an owner that receives a forward while holding the line in M writes back (DATAFWD carries the dirty data to the bank) before the directory replies DATA. A PUTM arriving while DIR_FWD_WAIT is therefore legal and is absorbed by the DTR's WRITE_BACK sub-progress.
2. **The 3-bit state field has no spare code.** Any future directory state requires re-layout of the entry.
3. **Eviction is never silent and INVACK counting is bit-clearing** (§3.3 rules 2 and 4). The idempotence of bit-clearing is what makes the late-PUTS/in-flight-INVACK race harmless.
4. **The single-exit property is what makes the bounded-liveness claim of §5.3 meaningful**, and it is exactly what the predecessor's `PROXY_WAIT` dead state violated.

### C. Flit and Message Encodings

**Message type (4 bits):**

| Code | Message | Class | VC | Flits |
|---|---|---|---|---|
| 0000 | GETS | REQ | VC0 | 1 |
| 0001 | GETM | REQ | VC0 | 1 |
| 0010 | PUTS | REQ | VC0 | 1 |
| 0011 | PUTM | REQ | VC0 | 9 |
| 0100 | UNBLOCK | RESP | VC2 | 1 |
| 0101 | INV | INV | VC3 | 1 |
| 0110 | INVACK | RESP | VC2 | 1 |
| 0111 | DATA | RESP | VC2 | 9 |
| 1000 | FWD_GETS | FWD | VC1 | 1 |
| 1001 | FWD_GETM | FWD | VC1 | 1 |
| 1010 | DATAFWD | RESP | VC2 | 9 |
| 1011 | PUTACK | RESP | VC2 | 1 |
| 1100 | DMA_WRITE *(gated)* | REQ | VC0 | 9 |
| 1101 | DMA_ACK *(gated)* | RESP | VC2 | 1 |
| 1110 | Reserved | — | — | — |
| 1111 | Reserved | — | — | — |

**Control bits (header [41:38]):**

| Bit | Meaning |
|---|---|
| 0 ([41]) | Head flit |
| 1 ([40]) | Tail flit — set only for single-flit packets; multi-flit packets delimit via LEN |
| 2 ([39]) | Write enable |
| 3 ([38]) | Exclusive indication |

**Header length field [37:32]:** total flits in the packet, 1–63. Control packet ⇒ LEN = 1 (head = tail = 1); cache-line packet ⇒ LEN = 9.

### D. Message × Virtual Channel Cross

| Class | VC | Messages | Count |
|---|---|---|---|
| REQ | VC0 | GETS, GETM, PUTS, PUTM, *(DMA_WRITE)* | 4 + 1 gated |
| FWD | VC1 | FWD_GETS, FWD_GETM | 2 |
| RESP | VC2 | DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, *(DMA_ACK)* | 5 + 1 gated |
| INV | VC3 | INV | 1 |
| **Active total** | | | **12 core (+2 gated) = 14** |

**Coverage cross:** (9 L1 states × 14 messages) + (8 directory states × 14 messages) = 126 + 112 = **238 terms**.

### E. Formal Property List

**Safety (BMC-proved):** A1.1–A1.5 (5), A2.1–A2.7 (7), A3.1–A3.6 (6), A4.1–A4.8 (8), A6.1–A6.4 (4), A7.1–A7.4 (4), A8.1–A8.4 (4) = **38 bound safety assertions**, plus the four A5 bounded-liveness assertions = **42 bound SVA**. Separately, the seven **formal-only network invariants I1–I7** are proved in SymbiYosys and are not counted in the 42 (total property inventory: 49).

**Bounded liveness (proved under Premise F, bound *T*):** every transient state field exits within *T* = 64 cycles (2×2 formal) / 150 cycles (4×4 simulation); every request receives a response within *T*; every VC with pending traffic is served within 8 arbitration rounds.

**Structural lemma (documented, premises confirmed by k-induction at k = 16):** deadlock freedom per §4.6 — Layer 1 (XY + VC preservation), Layer 2 (ascends inter-class graph), Layer 3 (credits), Premises R and F.

---

## 12. Open Items Still Requiring Decision

| # | Item | Status | Closure |
|---|---|---|---|
| 1 | Formal depths after first proof run (proposed: BMC K = 64, liveness *T* = 64, k-induction k = 16) | Confirm empirically | Week 12 |
| 2 | pyuvm coverage bin list behind the §5.4 numeric criteria | Confirm after environment runs | Week 12 |
| 3 | Related-work delta table against [15]–[18] | To be written (required by §2.5) | Week 15 |
| 4 | Router pipeline depth (3-stage vs 4-stage) | This paper specifies 4; close at RTL freeze | Week 4 |
| 5 | Post-synthesis resource table (LUT/FF/BRAM at 2×2) | To be appended to §6.1; fit claim stays open until then | Week 14 |
| 6 | IEEE conference venue | To be selected | Week 15 |
| 7 | Transient timeout detection mechanism (how *T* is counted in RTL) | To be specified; bounded by *T* | Week 10 |
| 8 | Age-counter threshold for the fairness escape (proposed: 8 rounds) | To be confirmed against measured VC load | Week 10 |
| 9 | Bank arbiter service order among local fills, remote requests and tap traffic | Not fixed by this specification (R2); either specify or leave implementation-defined at RTL freeze | Week 4 |

---

## 13. Cross-Model Adjudication Ledger

All six draft white papers (Qwen, Mistral/GLM-5.3, MiniMax, Grok, Gemini, DeepSeek) agreed on the core architecture: **2D mesh + XY routing + directory MESI + 4 VCs + private L1 + static-NUCA distributed L2 + 64 B lines + 4×4 simulation / 2×2 FPGA + tree-PLRU/PLRU-class replacement + PUTACK existence + transaction-level reference model + 42 SVA + BMC-for-safety / k-induction-or-structural-for-liveness.** No model proposed dropping any of those. Every *contested* point is adjudicated below with the positions taken and the deciding argument. Positions are abbreviated: **Q** = qwen.md, **M** = mistral.md, **X** = minimax.md, **G** = grok.md, **E** = gemini.md, **D** = deepseek.md.

| # | Contested point | Q | M | X | G | E | D | **Ruling (v3.0)** | Deciding basis |
|---|---|---|---|---|---|---|---|---|---|
| **A** | Directory state field width | 3 b | **4 b** | 3 b | 3 b | 3 b | 3 b | **3 bits, exactly saturated (8 codes); discriminators in a per-bank DTR (§3.7)** | 5-vs-1; keeps the entry 24 bits and BRAM-aligned; zero headroom is declared as a cost rather than hidden |
| **B** | DIR_FWD_WAIT successor ambiguity (fatal F1) | 1-bit latch | split into _S/_M | DTR pending-op | latch or split | split (App. B) | pending_type register | **Single state + `pending_op` in the DTR; exit event is UNBLOCK, not DATAFWD (§3.7, App. B)** | Two rows for one (state,event) pair is a non-function and makes model equivalence unprovable; a controller register is the lightest fix that preserves the 3-bit field |
| **C** | Eviction acknowledgement (fatal F2) | add PUT_ACK | needed | add PUTACK | add PUTACK | add PUTACK | add PUTACK | **PUTACK, code 1011, VC2, 1 flit; PUTS/PUTM directory rows added (App. B)** | Unanimous; without it EI_A/MI_A are orphan transients, violating the design's own invariant |
| **D** | Reference model fidelity | transaction | transaction | transaction | — | transaction | transaction | **Transaction-level; timing checked by SVA/formal (§5.4)** | Unanimous once the predecessor's "cycle-accurate" wording is traced; a cycle model duplicates RTL |
| **E** | Address-map layout and stored tags | [14:11] home, [10:8] L2 set | **[12:9] home, [8:6] L2 set** | [14:11], disjoint | retained | [14:11], disjoint | [14:11], disjoint | **Disjoint map: offset[5:0], L1 set[7:6], L2 set[10:8], home[14:11], tag[31:15] (4×4) / home[12:11] (2×2). Stored L2 tag = {addr[31:15], addr[7:6]} = 19 b — corrected against *all six drafts*** | Overlapping L2/L1 sets correlate the two indices (one L1 set backed by only 512 B). Separately, every draft's stored-L2-tag width is wrong: L1-set bits [7:6] lie below the L2 index and must still be compared (§3.6) |
| **F** | Packet framing (fatal F3) | 6-bit LEN | **4-bit LEN + 2 reserved** | 6-bit LEN | reserved[5:0] = LEN | 6-bit LEN | 6-bit LEN | **6-bit LEN at header [37:32] = total flits (1–63); body flits pure payload; tail bit only on single-flit packets** | 5-vs-1; a tail bit in body flits costs 1 payload bit and 11 % NoC occupancy; 4 bits caps at 16 and leaves spare bits |
| **G** | DMA message vocabulary | drop DMA_READ | reserve 11–13 | keep all 3 | reserve 11–13 | keep 14 incl. DMA_READ | drop DMA_READ | **DMA_READ not defined (a DMA read *is* GETS from the L1-lite; the source tile ID distinguishes it); DMA_WRITE and DMA_ACK retained, codes 1100/1101, gated** | A message with no protocol delta is not a message; DMA_WRITE is genuinely distinct (write-with-inline-data, no fetch-before-write) |
| **H** | VC arbitration policy | fixed priority | fixed priority | **pure round-robin** | fixed priority | fixed priority | fixed priority | **Fixed class priority RESP > INV > FWD > REQ *plus* an age-counter escape (≥ 8 rounds ⇒ grant next) and round-robin across input ports (§3.5)** | Resolves the 5-vs-1 split: the majority is right that protocol-critical traffic must not queue behind requests; MiniMax is right that pure fixed priority starves REQ, which is a liveness failure under Premise F. The escape counter supplies the bound the liveness proof needs |
| **I** | Consistency claim | out of scope | out of scope | **per-address contract** | — | **"sequential consistency"** | out of scope | **Per-address ordering only; cross-address ordering explicitly not guaranteed (§3.10)** | Sequential consistency is impossible without a core, store buffer, or fences — all out of scope by every draft's own §1.2 |
| **J** | L1 replacement policy | **true LRU** | **true LRU** | **tree-PLRU** | **tree-PLRU** | **tree-PLRU** | **split: true LRU (L1) / tree-PLRU (L2)** | **Tree-PLRU (3 b/set) at both levels (§3.2, §4.4)** | Deadlock/protocol unaffected, so the tie-break is specification quality: one policy for both levels means one implementation, one reference-model routine, one assertion. At 4 ways the hit-rate delta (~1 %) is immaterial at 1–2 KB, and the inherited design note recommends PLRU. The true-LRU counter-argument (5 b/set minimum encoding, better hit rate) is recorded here as the losing position, not discarded |
| **K** | UNBLOCK placement | VC2 | VC2 | VC2 | VC2 | **absent from the message set** | VC2 | **UNBLOCK on VC2 (RESP)**; Gemini's 14-message set is rejected because it has no UNBLOCK at all | DATA(VC2)→UNBLOCK(VC0) is a descending dependency; and without UNBLOCK the directory has no release event at all (Gemini's gap) |
| **L** | Formal configuration | **4-tile** | **2-tile** | 2-tile | 2-tile | 2×2 | **2×2 (4-tile)** | **2×2 = 4 tiles** (§5.3), with the uncovered scenarios (interior router, ≥3 sharers with distinct homes) disclosed and deferred to 4×4 simulation | MiniMax's own coverage table shows 2 tiles cannot generate a multi-sharer invalidation; 4 is the minimum that exercises the fan-out while staying tractable |
| **M** | SM_D exit condition | DATA (dir gates on INVACKs) | **DATA *and* all INVACKs** | **DATA alone** | **DATA only** | DATA alone | DATA + INVACKs | **DATA alone (App. A)** | INVACKs are addressed to the directory and physically never reach the requester, so they cannot be a requester-side exit condition. The (SM_D, INV) race is closed at source by the INV-excludes-requester rule (§3.3 rule 3); the receptivity rule handles other-line traffic |
| **N** | S-state eviction | not tabulated | **silent drop** | **PUTS required** | PUTS | — | **silent drop** | **PUTS required — no silent eviction (§3.3 rule 2, App. A)** | A silent drop leaves a stale sharer bit, falsifying A2.2 (sharers must equal the S-mask) and wedging DIR_INV_WAIT. Defence in depth: I + INV → INVACK |
| **O** | Eviction sub-state ownership | controller note | split FWD states | **DTR** | controller record | — | controller register | **DTR `evict_sub-state` = NONE / INV_SHARERS / RECALL_OWNER / WRITE_BACK (2 b)** | Same as A/B: the SRAM field cannot hold it, so a named register must — and it must be *named*, because a wildcard is not an FSM |
| **P** | Formal method split | BMC + k-induction | BMC + k-induction | **k-induction primary** | BMC + structural | BMC | BMC + k-induction | **Safety: BMC K = 64. Liveness: bounded with derived *T* (64 formal / 150 simulation). Deadlock: structural lemma + k-induction k = 16 (§5.3)** | Unanimous that BMC alone cannot prove `eventually` [19]; the drafts disagreed only on numbers, which are now derived once, in one place |
| **Q** | Router pipeline depth | — | — | 4-stage | — | **3-stage** | 4-stage | **4 stages (RC/VA/SA/ST), 4 cycles/hop (§3.5)** | 4 is the textbook decomposition and is the value used by every latency derivation in every draft; a 3-stage claim would invalidate *T* |
| **R** | BRAM arithmetic (defect in predecessor) | "not the binding constraint" | **12–25 BRAM, not binding** | **1–8 per bank; LUT binds** | "4×4 exceeds 140" | **~52 BRAM for 2×2** | **~27 BRAM for 2×2** | **BRAM36 = 512×72, so a 2 KB bank is 1–8 BRAM36 by port organisation; 2×2 needs 28–80 of 140. 4×4 needs 112–320 of 140 *and* ≈55 k LUTs of 53.2 k, so it is excluded on both budgets (§6.1)** | The inherited "15 BRAM/bank" figure divides 512 bits by a 36-bit width and ignores both the 72-bit configuration and depth. The drafts' point estimates (≈27, ≈40, ≈52, 12–25) all fall inside or immediately adjacent to the corrected 2×2 range; a range is published instead of a false point value |
| **S** | "Reduce VC count" FPGA fallback | delete | delete | delete | delete | kept implicitly | delete | **Deleted everywhere; VC count frozen at 4 (§6.1, §7.3)** | Reducing VCs merges classes and destroys Layer 2 of §4.6 — the paper cannot cite a proof it has broken |
| **T** | Schedule title | "16-Week (4-Month)" | "Four-Month" | "Sixteen-Week" | "Four-Month" | "Sixteen-Week (Four-Month)" | "Four-Month (16-Week)" | **Sixteen-Week (Four-Month), 13 milestones (§7)** | Unanimous once the predecessor's "Three-Month" title was found to contain four months |
| **U** | Fault tolerance of the mesh | **Low** | High (table) | **Low** | — | — | **Low** | **Low under deterministic XY (§4.1)** | Every link is a bridge with XY routing; the metric is "route around a broken link", which requires adaptive routing (out of scope) |
| **V** | Novelty claim in the abstract | softened | falsifiable delta | withdrawn | softened | kept as "contribution" | delta vs. zero-assertion baseline | **Withdrawn; a falsifiable integration claim with an explicit delta over the zero-assertion baseline (§1.3, §2.5)** | Novelty requires a stated delta over [15]–[18]; the delta table is an open item (§12 #3), so no novelty claim can yet be sustained |
| **W** | Coverage cross definition | — | per-agent bins | **285 terms** | — | state×message | **272 terms** | **238 terms** = (9 L1 + 8 dir states) × 14 active messages, per agent (§5.4) | The count must follow *this* document's state and message counts; the drafts' 272/285 figures each assumed a different message total (16 and 15) |
| **X** | Concurrent-transaction model | — | — | **blocking bank + DTR** | — | — | DTR register | **One outstanding transaction per bank, declared as an explicit premise (§3.7)** | It is the fact that makes the single-exit rule, Lemma L1, and the DTR all sound; being implicit in the drafts, it is made normative here |

**Rejected with proof (recorded so they are not silently reintroduced):**

| Proposal | Origin | Why rejected |
|---|---|---|
| BRAM crisis — 192/240 BRAMs, shrink L2 to 1 KB | some draft nodes | Arithmetically false: a 2 KB bank is 1–8 BRAM36, and total 4×4 array storage (≈50–75 KB incl. L1s, directories and FIFOs) is far below the ≈630 KB device capacity (§6.1) |
| Replace L1 true LRU with tree-PLRU **as an area fix** | one draft | The 8-bit saving is negligible; tree-PLRU is adopted instead for specification uniformity (§13 J) — a different reason, a different cost/benefit |
| Drop UNBLOCK entirely | one peer node | It has a consumer: it is the requester's release signal for the directory transient; no alternative release mechanism was specified |
| 4-bit directory state field with all transients in SRAM | M | Not wrong in isolation, but it widens the entry, loses BRAM alignment, and duplicates state already carried by the DTR; rejected on parsimony (§13 A) |
| Sequential consistency | E | Impossible without a core, store buffer, or fences (§13 I) |
| Sequential "reduce-depth" as the *only* formal mitigation | predecessor plan | A mitigation identical to the plan is not a mitigation; §7.3 names distinct actions |
| Compressed / limited-pointer sharer vectors | various | At 16 tiles the full map fits in one 24-bit entry; compression adds logic for no benefit at this scale. Re-opened only for N > 16 (§9) |
| MOESI / MESIF, snooping, adaptive routing | none adopted | Excluded by the constraint set and by scope, as recorded in every draft |

**Net effect of the adjudication:** the MESI protocol, mesh topology, cache geometry, flit width, 4-VC structure, and 12-message core set are unchanged from the ratified drafts; every FSM is now deterministic and single-exit; the deadlock argument is a proof with named premises rather than an appeal to virtual channels; the stored-tag and arbitration questions are settled with arithmetic rather than by vote; and no claim in the document lacks an artifact that will evidence it.


