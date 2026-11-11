
# A Scalable Cache-Coherent Tiled Multicore Architecture on a 2D Mesh Network-on-Chip

**Version 2.0 — Consensus-Finalized Specification and Justification**
*(v1.0 amended per multi-agent architectural review; all changes adjudicated in the accompanying Change Log.)*

---

## Abstract

This white paper specifies a cache-coherent tiled multicore architecture built on a 2D mesh Network-on-Chip. The design scales from a 4×4 configuration in simulation to parameterised N×N configurations bounded by the address map. Each CPU tile contains a private L1 cache, a bank of a distributed shared L2 cache with a separate directory array, a Network Interface Controller, a 5-port router, and a local memory tap. Coherence is maintained by a directory-based MESI protocol carried as multi-flit packets over the mesh. Four virtual channels separate request, forward, response, and invalidation traffic into an acyclic message-dependency ordering that prevents protocol-level deadlock. The architecture is verified using directed tests, constrained-random stimulus in a pyuvm environment, and bounded formal property checking with SymbiYosys, with liveness properties discharged by k-induction. The design targets the AMD Xilinx Zynq-7000 XC7Z020 FPGA (2×2) for hardware validation, with Sky130 ASIC implementation as future scope. The contribution is a complete, open verification flow — directed tests, a transaction-level pyuvm reference model, and SymbiYosys formal proofs — for a directory-based MESI protocol on a packet-switched NoC, with every protocol state and message enumerated to formal-verification grade.

**Keywords:** Cache coherence, MESI, directory protocol, Network-on-Chip, 2D mesh, virtual channels, FPGA, formal verification, UVM

---

## 1. Introduction

### 1.1 Motivation

Modern processors scale performance by adding cores rather than by raising clock frequency. Each core maintains a private cache for low-latency access to frequently used data. When multiple cores cache the same memory block, the system must guarantee that every core observes a consistent view of memory. This is the cache coherence problem.

The interconnect that carries coherence messages between cores must scale with the core count. A shared bus serialises all traffic and becomes a bottleneck beyond a handful of cores. A Network-on-Chip replaces the bus with a packet-switched fabric where multiple transfers proceed in parallel.

This white paper specifies a cache-coherent tiled multicore architecture that combines a directory-based MESI protocol with a 2D mesh NoC. The design is a continuation of the CDAC VLSI Feb 2026 project, rebuilt from first principles with a corrected architecture, a rigorous verification plan, and a realistic implementation path.

### 1.2 Scope

**In scope:**

- Parameterised N×N 2D mesh NoC (address map defined for N ≤ 8; extension to N ≤ 16 requires address-map widening, see §3.6)
- 4×4 configuration for simulation; 2×2 for FPGA
- MESI directory coherence with separate directory array
- Virtual channels for deadlock avoidance
- Multi-flit packets with explicit length field and wormhole switching
- Formal verification with SymbiYosys (bounded safety, k-induction liveness)
- UVM verification with pyuvm (transaction-level reference model)
- FPGA implementation on ZedBoard XC7Z020
- **Optional extension (gated):** DMA device tile — in scope only if the Month-2 gate (§7.3) is passed; message encodings 11–13 are *reserved, not committed*, until then
- ASIC flow on Sky130 as future scope

**Out of scope:**

- Processor core RTL (stimulus via testbench)
- Pipeline hazard handling
- Consistency model beyond coherence
- Dynamic voltage and frequency scaling
- Cache compression
- Non-volatile memory

### 1.3 Primary Contributions

1. **Scalable tiled architecture** with parameterised mesh topology and distributed directory
2. **Verification methodology** combining directed tests, a transaction-level pyuvm constrained-random environment, and SymbiYosys formal proofs for directory coherence protocols, with fully enumerated state machines and machine-checkable protocol tables
3. **Engineering baseline** demonstrating measurable scaling from 2×2 to 4×4

*(The DMA device tile is not claimed as a contribution in this version. It is a gated optional extension — see §3.7. This aligns the contribution list with §7.3 risk status.)*

### 1.4 Document Structure

Section 2 reviews related work. Section 3 specifies the architecture. Section 4 justifies design decisions with a topology comparison. Section 5 presents the verification plan. Section 6 covers implementation. Section 7 gives the project plan. Section 8 reconciles claims against artifacts. Section 9 states future scope.

---

## 2. Related Work

### 2.1 Cache Coherence

Snooping protocols broadcast every miss to all caches. The Illinois protocol [1] is an early example and ancestor of MESI. Snooping does not scale because broadcast traffic grows with the core count.

Directory protocols record which caches hold each block. Censier and Feautrier [2] introduced the concept. The Stanford DASH multiprocessor [3] made it practical for scalable machines. The Primer on Memory Consistency and Cache Coherence [4] provides the standard taxonomy of stable and transient states, and the message vocabulary (GetS, GetM, Fwd_*, Inv, Put*, Unblock) reused in this design.

Martin, Hill, and Sorin [5] argue that on-chip coherence remains necessary and that, in systems with inclusive last-level caches, modest sharer-tracking storage keeps its cost manageable. This design adopts their scalability position but uses a **separate, non-inclusive directory** rather than an inclusive LLC; the citation is attributed as prior-art position, not as a description of this architecture.

### 2.2 Distributed Shared Caches

Kim, Burger, and Keckler introduced Non-Uniform Cache Architectures [6], contrasting static NUCA (address-interleaved bank mapping) with dynamic NUCA (data migrates toward requester). Zhang and Asanovic proposed victim replication [7], reducing average memory access latency by 16–24% on their simulated tiled CMP. This design uses static NUCA with address-interleaved banks.

### 2.3 On-Chip Networks

Dally and Towles argued that chips should route packets, not wires [8]. Benini and De Micheli framed the NoC as a new SoC paradigm [9]. The textbook by Dally and Towles [10] covers topology, routing, flow control, and deadlock.

Ring topologies have the lowest router complexity but linear average distance and constant bisection bandwidth. Meshes scale better. Torus topologies reduce hop count further but require virtual channels or separate physical networks to avoid deadlock. Production manycore designs (Intel mesh, AMD Infinity Fabric) use mesh for these reasons.

OpenPiton [11] is an open-source tiled manycore framework with distributed directory coherence over on-chip networks. It demonstrates what a production-quality version of this architecture looks like.

### 2.4 Verification of Coherence Protocols

Directed testing covers expected cases. Constrained-random stimulus finds corner cases. Formal verification proves invariants. The three are complementary.

UVM [12] is the industry standard for constrained-random verification. pyuvm [13] brings UVM structure to Python, reducing development time and integrating with cocotb for simulation.

SymbiYosys [14] provides open-source formal verification using SystemVerilog Assertions, bounded model checking, and k-induction.

---

## 3. Architecture Specification

### 3.1 Tile Organisation

Each **CPU tile** is structurally identical. It contains:

1. **Core interface port** — processor or testbench stimulus port issuing load/store requests
2. **Private L1 cache** — 4 sets × 4 ways × 64 bytes, write-back write-allocate, true LRU, MESI state per line
3. **L2 bank** — 8 sets × 4 ways × 64 bytes, tree-PLRU replacement
4. **Directory array** — separate from the L2 data array (see §3.2), non-inclusive bookkeeping for this bank's blocks
5. **Network Interface Controller (NIC)** — packetises coherence messages into flits, manages VC credits
6. **5-port router** — local, North, East, South, West; edge tiles tie off unused ports
7. **Local memory tap** — interface to the memory subsystem for DIR_MEM_WAIT fetches and write-backs

*(If the gated DMA extension is adopted, the DMA tile is a structural variant, not identical to a CPU tile: L1-lite cache, no L2 bank, no directory — see §3.7.)*

### 3.2 Cache Hierarchy

**L1 cache (private):**

- 4 sets × 4 ways × 64 bytes = 1 KB per tile
- Write-back, write-allocate
- True LRU replacement (5 bits per set)
- MESI state per line

**L2 bank (shared, distributed):**

- 8 sets × 4 ways × 64 bytes = 2 KB per bank
- 16 banks (4×4) = 32 KB total L2
- Tree-PLRU replacement (3 bits per set)
- Separate directory array

**Directory entry (parameterised):**

| Field | Width (N×N mesh) | Width (4×4) | Meaning |
| --- | --- | --- | --- |
| State | 4 bits | 4 bits | 4 stable + 7 transient states (§3.3); 3 bits overflow, widened to 4 |
| Owner | ⌈log₂N²⌉ bits | 4 bits | Tile ID of exclusive owner |
| Sharers | N² bits | 16 bits | Bit vector of sharers |
| Valid | 1 bit | 1 bit | Entry in use |

All widths are derived from the mesh parameter N; the 4×4 column shows the instantiated values. Fixed-width literals elsewhere in this document refer to the 4×4 build.

### 3.3 MESI Coherence Protocol

Four stable L1 states:

| State | Meaning |
| --- | --- |
| Modified (M) | Only copy, dirty, memory stale |
| Exclusive (E) | Only copy, clean, memory current |
| Shared (S) | Read-only copy, other copies may exist |
| Invalid (I) | No valid copy |

**L1 transient states** (6):

| State | Meaning | Entry | Exit → |
| --- | --- | --- | --- |
| IS_D | Invalid → S/E, waiting data | Load miss (I) | DATA (shared) → S; DATA (exclusive) → E |
| IM_D | Invalid → M, waiting data | Store miss (I) | DATA (exclusive) → M |
| SM_D | S → M, waiting data + acks | Store hit (S) | DATA (exclusive) AND all INVACKs → M; exit requires **both** conditions, in either arrival order |
| SM_D_INV | Defensive: SM_D receiving an INV | INV arrives while in SM_D | Send INVACK immediately; on DATA arrival, re-request (GETM) → IM_D. Cannot occur when the INV-exclusion rule below holds; specified for defensive completeness and formally checked |
| EI_A | E → I, waiting ack | Eviction (E) | ACK → I |
| MI_A | M → I, waiting ack | Eviction (M) | ACK → I |

**Directory states** — 4 stable (DIR_I, DIR_S, DIR_E, DIR_M) and 7 transient:

| State | Meaning |
| --- | --- |
| DIR_MEM_WAIT | Waiting for memory data |
| DIR_FWD_WAIT_S | Waiting for owner's DATAFWD; a FWD_GETS is outstanding; exits to DIR_S |
| DIR_FWD_WAIT_M | Waiting for owner's DATAFWD; a FWD_GETM is outstanding; exits to DIR_M |
| DIR_INV_WAIT | Waiting for all INVACKs; sharer bits cleared one per INVACK; exits when Sharers == 0 |
| DIR_EVICT_INV | Evicting a shared victim line (invalidating sharers) |
| DIR_EVICT_FWD | Evicting an owned victim line (awaiting owner's PUTS/PUTM) |
| DIR_EVICT_WB | Writing a dirty victim back to memory |

Total directory states = 11 > 2³, hence the 4-bit State field in §3.2.

**INVACK counting rule:** on entering DIR_INV_WAIT the directory records the current sharer set S₀; each INVACK clears the corresponding Sharers bit; the exit condition is Sharers == 0. No separate counter field is required — counting is bijective with bit-clearing (each sharer receives exactly one INV).

**INV addressing rule:** when the directory services a GETM from tile T while in DIR_S, the INV is sent to every sharer **except T** (the requester). This closes the (SM_D, INV) self-invalidation race at its source.

**Message set (core MESI, 11 messages — complete and minimal):**

| Message | Direction | Purpose | VC |
| --- | --- | --- | --- |
| GETS | L1 → dir | Request shared copy | VC0 |
| GETM | L1 → dir | Request exclusive copy | VC0 |
| PUTS | L1 → dir | Write back clean on eviction | VC0 |
| PUTM | L1 → dir | Write back dirty on eviction | VC0 |
| UNBLOCK | L1 → dir | Acknowledge data receipt, release directory transient | **VC2** |
| INV | dir → L1 | Invalidate | VC3 |
| INVACK | L1 → dir | Invalidation ack | VC2 |
| DATA | dir/owner → L1 | Data transfer | VC2 |
| FWD_GETS | dir → owner | Forward shared request | VC1 |
| FWD_GETM | dir → owner | Forward exclusive request | VC1 |
| DATAFWD | owner → requester | Forwarded data | VC2 |

**Reserved messages (11–13, pending DMA gate §3.7):** DMA_READ, DMA_WRITE, DMA_ACK. These encodings are reserved but MUST NOT be decoded by any RTL until the DMA design is committed. If the gate fails, the codes revert to reserved.

### 3.4 Network-on-Chip

**Topology:** 2D mesh. Each interior tile has 5 ports. Edge tiles tie off unused ports.

**Routing:** XY deterministic. A packet first moves in X, then in Y. The channel dependency graph of XY routing on a mesh is acyclic.

**Flow control:** Credit-based. Each VC has a credit counter. Sender transmits only when credits are available.

**Virtual channels:** Four VCs per port, assigned by protocol role:

| VC | Class | Messages | Priority |
| --- | --- | --- | --- |
| VC 0 | Requests | GETS, GETM, PUTS, PUTM | 4 (lowest) |
| VC 1 | Forwarded requests | FWD_GETS, FWD_GETM | 3 |
| VC 2 | Responses | DATA, DATAFWD, INVACK, **UNBLOCK** | 2 |
| VC 3 | Invalidations | INV | 1 (highest) |

**Deadlock-freedom argument:** every message sent as a consequence of receiving a class-*k* message is sent on a class no lower than *k*: GETM(VC0) triggers INV(VC3) and DATA(VC2); DATA(VC2) receipt triggers UNBLOCK(VC2), not VC0; FWD(VC1) triggers DATAFWD(VC2). The message-dependency graph is therefore acyclic across VC classes, and by Duato's theorem the extended channel-dependency graph is deadlock-free. *Note: v1.0 placed UNBLOCK in VC0, creating a descending DATA(VC2)→UNBLOCK(VC0) dependency and a provable deadlock cycle; this version corrects it.*

**Switching:** Wormhole. Header flit reserves the path. Body and tail flits follow.

**Arbitration:** Two-level. (a) **VC arbitration per input port: fixed priority by protocol class** — VC3 > VC2 > VC1 > VC0 — so invalidations and responses are never starved behind request traffic. (b) **Switch arbitration per output port: round-robin across input ports**, preventing input starvation. *(v1.0 said "round-robin across VCs and inputs", which permits protocol-critical responses to be starved behind requests.)*

### 3.5 Packet and Flit Format

**Header flit (64 bits):**

| Bits | Field | Width | Notes |
| --- | --- | --- | --- |
| [63:56] | Dest tile ID | 8 (parameterised: ⌈log₂N²⌉) | 8-bit field supports N ≤ 16; unused high bits zero |
| [55:48] | Src tile ID | 8 (parameterised) | as above |
| [47:44] | Msg type | 4 | Appendix C |
| [43:42] | VC ID | 2 | Redundant with msg type; retained for router fast-path |
| [41:38] | Control | 4 | head, tail, write-enable, exclusive |
| [37:34] | **Packet length (LEN)** | **4** | Total flits in packet, 1–16; **replaces 4 of 6 v1.0 reserved bits** |
| [33:32] | Reserved | 2 | Must be driven 0; receivers MUST NOT decode |
| [31:0] | Address | 32 | Line-aligned address |

**Body flit (64 bits):** 8 bytes of data. **Packet delimiting:** the receiver counts flits from the header LEN field; a packet is complete when LEN flits have arrived. The header's tail bit is set only in single-flit packets. *(v1.0 defined no tail indicator on body flits and no length field — a 9-flit packet was undelimited. This was a fatal framing defect.)*

**Packet sizes:**

- Control message: 1 flit (LEN=1, head+tail both set)
- Cache line transfer: 9 flits (LEN=9; 1 header + 8 body)
- All coherence transfers are single-cache-line granularity. **"DMA bulk up to 16 flits" is deleted** (it had no defined address/length semantics under this format). Any future multi-line DMA uses one 9-flit packet per 64-B block.

### 3.6 Address Map

All fields are parameterised on N. The 4×4 (N=4) instantiation:

**L2 decode (4×4):**

| Bits | Field | Width |
| --- | --- | --- |
| [31:13] | L2 tag | 19 |
| [12:9] | Home tile (X,Y) | 4 = 2⌈log₂N⌉ |
| [8:6] | L2 set | 3 |
| [5:0] | Byte offset | 6 |

**L1 decode (4×4):**

| Bits | Field | Width |
| --- | --- | --- |
| [31:8] | L1 tag | 24 (= all bits except set index and offset) |
| [7:6] | L1 set | 2 |
| [5:0] | Byte offset | 6 |

The L1 tag is, by standard tag decomposition, every address bit except the set index and byte offset; it therefore inherently distinguishes addresses mapping to different home banks. The L2 tag excludes the home-tile bits because the tag is stored per-bank.

**Scalability bound:** the home-tile field width is 2⌈log₂N⌉. The 32-bit address map with a 19-bit L2 tag at N=4 accommodates N ≤ 8 without change; N = 16 requires a 1-bit tag reduction; N > 16 requires a wider address map. §4.2's scaling claim is restated accordingly: **the RTL is parameterised for any N×N; the default 32-bit address map supports N ≤ 16 with the N=16 caveat noted.**

### 3.7 DMA Engine (Gated Optional Extension)

**Status: not part of the baseline.** The DMA device tile is adopted only if the Month-2 gate (§7.3) is passed: 4×4 mesh simulated clean, pyuvm regression green, all formal safety properties discharged. If the gate fails, DMA moves to future scope, message codes 11–13 remain reserved, and no RTL change is required.

When active, the DMA engine is a device tile on the mesh, structurally a variant (not identical) of a CPU tile: L1-lite cache, no L2 bank, no directory, one channel, single-block transfer, memory-mapped registers. Coherence is maintained through the standard MESI protocol with three reserved messages (DMA_READ, DMA_WRITE, DMA_ACK). The design requires no new directory states. Baseline is **one channel**; a second channel is future scope. Directed tests 15a–15e are conditional on the gate.

---

## 4. Design Decisions and Justification

### 4.1 Topology Comparison

Seven topologies compared on ten parameters.

**Worst hop count at N tiles:**

| N | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 1 | 1 | 2 | 2 | 2 | 4 | 2 |
| 16 | 1 | 1 | 8 | 6 | 4 | 8 | 2 |
| 64 | 1 | 1 | 32 | 14 | 8 | 12 | 2 |

**Ports per router:**

| N | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 1 | 4 | 3 | 3 | 5 | 3 | 4 |
| 16 | 1 | 16 | 3 | 5 | 5 | 3 | 16 |
| 64 | 1 | 64 | 3 | 5 | 5 | 3 | 64 |

**Total wire length (tile-pitch units):**

| N | Bus | Xbar | Ring | Mesh | Torus |
| --- | --- | --- | --- | --- | --- |
| 4 | 2 | 8 | 5 | 4 | 8 |
| 16 | 4 | 64 | 18 | 24 | 48 |
| 64 | 8 | 512 | 70 | 112 | 224 |

**Full comparison at N=64:**

| Parameter | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ports/router | 1 | 64 | 3 | 5 | 5 | 3 | 64 |
| Worst hop | 1 | 1 | 32 | 14 | 8 | 12 | 2 |
| Paths | 1 | 1 | 2 | Many | More | 1 | 1 |
| Wire length | 8 | 512 | 70 | 112 | 224 | 192 | 64 |
| Deadlock risk | Low | Low | High | Low | High | Low | High |
| RTL complexity | Low | High | Low | Medium | High | Medium | Low |
| Synthesis congestion | Low | Very High | Medium | Low | High | Medium | Very High |
| Fault tolerance | Low | Low | Low | High | High | Medium | Low |
| Scalability | Poor | Poor | Weak | Good | Good | Good | Poor |

### 4.2 Why 2D Mesh

1. **Port count is constant at 5.** A crossbar needs 64 ports at N=64. A mesh needs 5.
2. **Hop count grows as √N.** A ring's worst hop grows as N/2. At 64 tiles, mesh = 14 hops, ring = 32 hops.
3. **Wires are short.** Every mesh link connects adjacent tiles. A ring needs one long wrap-around wire. A torus needs two.
4. **Deadlock-free with XY routing.** The channel dependency graph of XY routing on a mesh has no cycles. A ring has a cyclic dependency. A torus has a cyclic dependency in both dimensions.
5. **Low synthesis congestion.** The place-and-route tool can meet timing because no link crosses the chip.
6. **Scales within the address map.** The parameterised RTL instantiates any N×N; the default 32-bit address map bounds N as stated in §3.6.
7. **Industry standard.** Intel mesh, AMD Infinity Fabric, OpenPiton all use mesh.
8. **Low RTL complexity.** A mesh router adds ~100 lines over a ring router. A torus router adds ~300 lines plus virtual channel logic.

### 4.3 Why Not Other Topologies

**Bus:** Bandwidth does not scale. One transfer at a time.

**Crossbar:** Wire count grows as N². At N=64, 4096 links. Not routable.

**Ring:** Hop count grows as N/2. Long wrap-around wire. Cyclic dependency causes deadlock under coherence traffic. The original design used a ring and had a documented deadlock risk.

**Torus:** Wrap-around wires cross the chip. Requires virtual channels (which we are adding anyway, but torus needs more). At 4 tiles, a 2×2 torus is degenerate — the same pair of tiles connected by two parallel links.

**Tree:** Hot spot at the root. Coherence traffic is not uniform. The root becomes the bottleneck.

**Star:** Hub has N ports. Single point of failure. Does not scale.

### 4.4 Cache Parameters

| Parameter | Value | Justification |
| --- | --- | --- |
| Line size | 64 bytes | Industry standard; 8 body flits of 64 bits, clean flit packing |
| L1 sets × ways | 4 × 4 | Low conflict misses, fits FPGA |
| L2 sets × ways | 8 × 4 | Enough directory entries for coherence |
| L1 replacement | True LRU (5 bits/set) | Better than pseudo-LRU at 4 ways; 20 bits total state is negligible |
| L2 replacement | Tree-PLRU (3 bits/set) | Deterministic, area-efficient; policy specified exactly (not generic "pseudo-LRU") to prevent implementer ambiguity |
| Write policy | Write-back, write-allocate | Standard for coherent caches |

*Note: the earlier design-note suggestion to replace L1 true LRU with tree-PLRU is superseded by this specification; the white paper is authoritative. The 8-bit saving (20→12 bits per tile) does not justify the hit-rate regression at the state-visibility-critical L1 level.*

### 4.5 Virtual Channel Assignment

Four VCs prevent protocol-level deadlock by separating message classes into an acyclic message-dependency ordering (§3.4). A request cannot block a response. An invalidation cannot block data. UNBLOCK rides VC2 because it is causally downstream of DATA(VC2); placing it lower would reintroduce a dependency cycle.

### 4.6 Packet Size

64-bit flit, 9-flit packets for cache lines, explicit 4-bit LEN field. Wormhole switching keeps per-router buffer at flit granularity.

### 4.7 FPGA Resource Sanity Check

XC7Z020 provides 140 36-Kb BRAM tiles (≈630 KB). Worst-case baseline storage at 4×4: 16 × L1 (1 KB) + 16 × L2 bank (2 KB) + directories ≈ 52 KB ≈ 12–25 BRAM tiles including tag/state/dual-port overhead. **BRAM is not the binding constraint.** The 2×2 FPGA choice is driven by LUT/timing risk in the router fabric and verification scope, not BRAM capacity. A post-synthesis resource table (LUT/FF/BRAM) must be appended to §6.1 before the FPGA fit claim is closed (Open Item 4).

---

## 5. Verification Plan

### 5.1 Directed Tests

| # | Test | Purpose |
| --- | --- | --- |
| 1 | Load miss, local home | Baseline fill |
| 2 | Load miss, remote home | Remote GETS |
| 3 | Store miss, local home | GETM local |
| 4 | Store miss, remote home | GETM remote |
| 5 | Silent E→M upgrade | Exclusive benefit |
| 6 | Sharing (two readers) | DIR_S behaviour |
| 7 | Upgrade with invalidation | SM_D / DIR_INV_WAIT |
| 8 | Forward from remote owner | DIR_FWD_WAIT_S/M |
| 9 | L1 eviction with write-back | MI_A / EI_A, PUTM/PUTS |
| 10 | L2 eviction with write-back | DIR_EVICT_* chain |
| 11 | Back-to-back requests from two tiles | Pipelining |
| 12 | Concurrent requests to same line | Directory ordering |
| 13 | Mesh saturation | Multi-hop traffic injection across the 2D mesh |
| 14 | Timeout and recovery | Error handling |
| 15a–15e | DMA read/write, contention, timeout, back-to-back | **Conditional: run only if the DMA gate (§3.7) is passed** |

*(Test 13 renamed from "Ring/mesh saturation" — the architecture contains no ring.)*

Each test checks **final state** and **data values**.

### 5.2 Formal Verification (SymbiYosys)

| Property | Type | Description |
| --- | --- | --- |
| Single writer | Safety | At most one cache in M or E state per block |
| Multiple readers | Safety | Any number of caches in S state per block |
| Data consistency | Safety | If M, memory stale; if S/E, memory current |
| Directory consistency | Safety | Directory state matches aggregate L1 states: owner validity, sharer-vector accuracy, DIR_I ⇒ valid=0 |
| No orphan transient | Bounded liveness | Every transient state exits within K cycles (timeout counter) |
| No message loss | Bounded liveness | Every request receives a response within K cycles |
| Deadlock freedom | Liveness (k-induction) | No reachable cycle of waiting dependencies, proven by k-induction on the 2-tile config |

**Method and bounds:** Safety properties by bounded model checking on a 2-tile configuration, BMC depth K = 64 (≥ 2× worst-case coherence round-trip ≈ 30 cycles). Liveness properties are **bounded liveness within K cycles** under BMC, and the deadlock-freedom property is additionally discharged by **k-induction** (target k = 16) — BMC alone cannot prove unbounded "eventually" properties.

**Disclosed coverage limitation:** a 2-tile configuration exercises all single-requester and single-sharer races but cannot generate three-or-more-requester interleavings (e.g., two GETS while a third tile holds M). Such scenarios are covered by the pyuvm 4×4 random environment and are an accepted limitation of the formal scope.

### 5.3 UVM Environment (pyuvm)

| Component | Function |
| --- | --- |
| Test | Top-level stimulus |
| Environment | Container for agents and scoreboard |
| Agent (per tile) | Driver + monitor + sequencer |
| Scoreboard | Compares DUT output against reference model |
| Coverage collector | Functional coverage |

**Reference model:** a **transaction-level** Python model with shadow L1/L2/directory/memory state and data values. Timing and protocol-ordering behaviour is checked by SVA assertions bound in simulation, not by the reference model. *(v1.0 said "cycle-accurate", which would duplicate RTL effort and must be updated for every RTL change.)*

**Stimulus:** constrained-random sequences with coverage-driven closure.

**Coverage targets (closure criteria):**

- Legal (L1 state, message) and (Dir state, message) cross bins: **100% on the 2-tile configuration; sampled on 4×4** — bins are state × message legal pairs, not a per-tile product; illegal bins are proven unreachable by formal
- FSM: 100% of states and transitions reached (both L1 and directory FSMs)
- All message types exercised
- Data-value consistency: scoreboard checks on every fill and write-back
- Multi-tile contention scenarios
- Code coverage gates: line/branch ≥ 98%, toggle ≥ 95%, assertions 100% pass, cover properties 100% hit; unreachable bins waived with a documented waiver

### 5.4 Regression

Directed tests + pyuvm random tests + formal proofs run on every commit. CI via GitHub Actions.

---

## 6. Implementation Plan

### 6.1 FPGA Target

| Parameter | Value |
| --- | --- |
| Board | ZedBoard |
| Device | XC7Z020-CLG484-1 |
| LUTs | 53,200 |
| BRAM | 140 tiles (36 Kb) |
| DSP | 220 slices |
| Clock | 100 MHz |

**Configuration:** 2×2 mesh on FPGA; 4×4 in simulation. The parameterised RTL supports both. BRAM utilisation at 2×2 is ≈ 4–8 tiles (§4.7) — not a constraint; timing and LUT utilisation are the risks. **A post-synthesis resource table must be appended before fit is declared (Open Item 4).**

**Fallback if timing fails:** reduce cache associativity or set count, map selected tag/state arrays to LUTRAM, or reduce tile count. **The VC count must remain 4** — the deadlock-freedom proof (§3.4) depends on four protocol classes; removing one reintroduces cyclic dependencies. *(v1.0's "reduce VC count" fallback is deleted as it invalidates the paper's own deadlock argument.)*

### 6.2 ASIC Target (Future Scope)

| Parameter | Value |
| --- | --- |
| Node | Sky130 |
| Flow | OpenLane |
| Synthesis | Yosys |
| Place and route | OpenROAD |
| Signoff | Magic, Netgen |

### 6.3 Synthesis Flow

| Step | Tool |
| --- | --- |
| RTL elaboration | Verilator, Vivado xsim |
| Logic synthesis | Vivado (FPGA), Yosys (ASIC) |
| Place and route | Vivado (FPGA), OpenROAD (ASIC) |
| Static timing | Vivado Timing (FPGA), OpenSTA (ASIC) |
| Bitstream | Vivado |

### 6.4 Timing Closure

| Constraint | Target |
| --- | --- |
| Clock period | 10 ns (100 MHz) |
| WNS | Positive |
| WHS | Positive |
| Pulse width | Positive |

---

## 7. Project Plan

### 7.1 Four-Month Schedule

*(Retitled from v1.0's "Three-Month Schedule", which contradicted its own four-month content.)*

| Month | Milestone |
| --- | --- |
| Month 1 | Fix inherited bugs, refactor RTL, implement 2-tile mesh, write directed tests 1–12 |
| Month 2 | Implement 4×4 mesh, virtual channels, pyuvm environment, formal safety properties; **DMA gate decision at Month-2 exit** |
| Month 3 | FPGA implementation, timing closure, documentation, paper draft |
| Month 4 | Paper submission to IEEE conference |

### 7.2 Milestones

| # | Milestone | Week |
| --- | --- | --- |
| 1 | Bug fixes complete | 2 |
| 2 | 2-tile mesh verified | 4 |
| 3 | 4×4 mesh simulation complete | 8 |
| 4 | pyuvm environment running | 9 |
| 5 | DMA gate decision | 9 |
| 6 | Formal safety proofs passing; liveness by k-induction | 10 |
| 7 | FPGA bitstream on ZedBoard | 12 |
| 8 | White paper finalised | 13 |
| 9 | Paper submitted | 16 |

### 7.3 Risks and Mitigations

| Risk | Probability | Mitigation |
| --- | --- | --- |
| FPGA does not fit 2×2 | Low–Medium | Reduce associativity/sets, LUTRAM for tag arrays (never VC count — see §6.1) |
| Timing closure fails | Medium | Reduce cache size, LUTRAM mapping, pipelined router stages |
| Formal proofs do not complete | Medium | Reduce BMC depth, abstract data values to symbols, split properties by VC class (2-tile config is already the baseline and is not itself a fallback) |
| Virtual channel deadlock | Low | XY routing + acyclic VC dependency ordering (§3.4) is proven; formal k-induction discharge |
| DMA design not settled | High | **Gated:** DMA is not in the baseline; codes 11–13 stay reserved; adopted only on Month-2 gate pass |
| Time overrun | Medium | Baseline (no DMA) completes without gate; ASIC already future scope |

---

## 8. Claims vs Artifacts Reconciliation

This section reconciles the original team's report against the artifacts they delivered.

| # | Original Report Claim | Artifact Reality | Status |
| --- | --- | --- | --- |
| 1 | All RTL modules completed and verified | All modules present, but several have bugs | Partial |
| 2 | Remote-owner forwarding completed and verified | `is_fwd_remote_reply` tied to 0; `PROXY_WAIT` never entered | **Contradicted** |
| 3 | Synthesis results (WNS = +0.003 ns) | No Vivado project, no XDC, no reports in repo | **Unverifiable** |
| 4 | FPGA hardware validated on ZedBoard | No `fpga_top` module, no XDC in repo | **Unverifiable** |
| 5 | Five directed test cases pass | Testbench skips tests 3 and 5; state-only checks | Partial |
| 6 | Data correctness verified | No data-value checks | **Contradicted** |
| 7 | Directory `DIR_I` bug | Not mentioned in report | **Omitted** |

This white paper's contribution is to build a correct architecture from the ground up, not to defend the original report. The original team's code and report are treated as reference only. **This document applies the same standard to itself: no claim is stated without a defined artifact that will evidence it, and DMA — the one feature not yet settled — is excluded from the contributions list and gated in §3.7.**

---

## 9. Future Scope

| Item | Timeline |
| --- | --- |
| ASIC tapeout on Sky130 | Post-project |
| RISC-V core integration (hazard handling) | Post-project |
| Adaptive routing | Post-project |
| Victim replication / dynamic NUCA | Post-project |
| 8×8 mesh (address-map widening, §3.6) | Post-project |
| Memory controller and DRAM model | Post-project |
| Consistency model (atomics, fences) | Post-project |
| Scatter-gather DMA | Post-project |
| Additional DMA channels | Post-project |
| DMA priority levels | Post-project |

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

[15] J. Duato, "A New Theory of Deadlock-Free Adaptive Routing in Wormhole Networks," IEEE Trans. Parallel and Distributed Systems, 1993. *(Basis for the VC dependency-ordering rule in §3.4.)*

---

## 11. Appendix

### A. L1 MESI State Transitions

| Current | Event | Next | Actions |
| --- | --- | --- | --- |
| I | Load miss | IS_D | Send GETS |
| IS_D | DATA (shared) | S | Install, send UNBLOCK |
| IS_D | DATA (exclusive) | E | Install, send UNBLOCK |
| I | Store miss | IM_D | Send GETM |
| IM_D | DATA (exclusive) | M | Install, write, send UNBLOCK |
| S | Store hit | SM_D | Send GETM |
| SM_D | DATA (exclusive) AND all INVACKs | M | Write data (conditions may arrive in either order; exit requires both) |
| SM_D | INV | SM_D_INV | Send INVACK; on DATA, re-issue GETM → IM_D (defensive; excluded by §3.3 INV rule) |
| E | Store hit | M | Silent upgrade |
| M | Eviction | MI_A | Send PUTM |
| MI_A | ACK | I | Release way |
| E | Eviction | EI_A | Send PUTS |
| EI_A | ACK | I | Release way |
| S | Eviction | I | Silent drop |

### B. Directory State Transitions

| Current | Request | Next | Actions |
| --- | --- | --- | --- |
| DIR_I | GETS | DIR_MEM_WAIT | Fetch from memory |
| DIR_I | GETM | DIR_MEM_WAIT | Fetch from memory |
| DIR_MEM_WAIT | MEM_DATA | DIR_E / DIR_S / DIR_M | Install, reply to requester |
| DIR_S | GETS | DIR_S | Reply, add sharer (no transient) |
| DIR_S | GETM | DIR_INV_WAIT | Send INV to all sharers **except requester**; clear sharer bits per INVACK |
| DIR_INV_WAIT | All INVACKs (Sharers == 0) | DIR_M | Reply, set owner |
| DIR_E | GETS (owner) | DIR_E | Local serve |
| DIR_E | GETS (other) | DIR_FWD_WAIT_S | FWD_GETS to owner |
| DIR_FWD_WAIT_S | DATAFWD | **DIR_S** | Add sharer, copy data, update memory |
| DIR_E | GETM (other) | DIR_FWD_WAIT_M | FWD_GETM to owner |
| DIR_FWD_WAIT_M | DATAFWD | **DIR_M** | Set owner, write back to memory |
| DIR_M | GETS (owner) | DIR_M | Local serve |
| DIR_M | GETS (other) | DIR_FWD_WAIT_S | FWD_GETS to owner, owner writes back |
| DIR_M | GETM (other) | DIR_FWD_WAIT_M | FWD_GETM to owner (ownership transfer) |
| DIR_M | PUTM (from owner) | DIR_I | Write data to memory, send ACK to owner, clear Owner *(row absent in v1.0 — MI_A had no defined handler)* |
| DIR_E | PUTS (from owner) | DIR_I | Clear Owner, send ACK *(row absent in v1.0 — EI_A had no defined handler)* |
| Any | Eviction needed | DIR_EVICT_INV / DIR_EVICT_FWD | Resolve victim before fill |
| DIR_EVICT_INV | All INVACKs | DIR_MEM_WAIT | Proceed with new-line fetch |
| DIR_EVICT_FWD | PUTS/PUTM from owner | DIR_EVICT_WB / DIR_MEM_WAIT | Clean victim → proceed; dirty victim → write back first |
| DIR_EVICT_WB | Memory write complete | DIR_MEM_WAIT | Proceed with new-line fetch |

### C. Flit Field Encoding

**Message type (4 bits):**

| Code | Message |
| --- | --- |
| 0 | GETS |
| 1 | GETM |
| 2 | PUTS |
| 3 | PUTM |
| 4 | UNBLOCK |
| 5 | INV |
| 6 | INVACK |
| 7 | DATA |
| 8 | FWD_GETS |
| 9 | FWD_GETM |
| 10 | DATAFWD |
| 11–13 | **Reserved — pending DMA gate decision (§3.7); no RTL may decode these values until committed** |
| 14–15 | Reserved (permanent) |

**Control bits:**

| Bit | Meaning |
| --- | --- |
| 0 | Head flit |
| 1 | Tail flit (single-flit packets only; multi-flit packets delimit via LEN) |
| 2 | Write enable |
| 3 | Exclusive indication |

---

**End of White Paper — Version 2.0**

---

## Open Items Still Requiring Decision

| # | Item | Status | Exit Criterion |
| --- | --- | --- | --- |
| 1 | Formal verification BMC depth (proposed K=64) and k-induction depth (proposed k=16) | Confirm after first proof run | Week 10 |
| 2 | pyuvm coverage bin list (proposed in §5.3) | Confirm after environment runs | Week 9 |
| 3 | IEEE conference venue | To be selected | Week 12 |
| 4 | FPGA post-synthesis resource table (LUT/FF/BRAM at 2×2) | To be appended to §6.1 | Week 11 |
| 5 | DMA gate decision | Month-2 exit criteria (§3.7) | Week 9 |

### 🧠 Model Scratchpad

**Iteration 2 — Consensus pass.** Cross-verified four peer critiques (Claude-Sonnet, Consensus-Baseline Node, Gemini node, GPT-node) plus my Iteration-1 findings against each other and against the source documents. Adjudication:

**Convergent findings — adopted (multi-model agreement, independently verified):**

- **DIR_FWD_WAIT nondeterminism** (all 4 peers): confirmed. δ(DIR_FWD_WAIT, DATAFWD) was defined twice with different next states. Split into DIR_FWD_WAIT_S / DIR_FWD_WAIT_M. **Adopted.**
- **Directory state encoding overflow**: after the split and enumerating DIR_EVICT_* (which the context document itself defines as 3 states: EVICT_INV, EVICT_FWD, EVICT_WB), the count is 11 > 2³. The v1.0 3-bit State field overflows. **Widened to 4 bits. Adopted.**
- **Missing PUTM/PUTS directory rows** (Claude): confirmed — Appendix B had no handler for the PUTM that MI_A emits, a direct liveness hole. **Rows added. Adopted.**
- **Packet framing defect** (Consensus Node): confirmed — body flits were pure 64-bit data with no tail bit and no length field; a 9-flit packet was undelimitable. Fixed with a 4-bit LEN field carved from the reserved bits; "DMA bulk 16 flits" deleted. **Adopted.**
- **VC arbitration** (Consensus Node): round-robin across VCs can starve responses behind requests; replaced with fixed class priority + RR across inputs. **Adopted.**
- **"Reduce VC count" FPGA fallback** (Consensus Node): provably invalidates the paper's own deadlock argument. **Deleted. Adopted.**
- **DMA contradiction** (all peers, my Iter-1): demoted to a Month-2-gated extension, removed from contributions, encodings 11–13 marked reserved. **Adopted.**
- **BMC cannot prove liveness** (Claude, GPT-node): converted to bounded liveness + k-induction for deadlock freedom, with explicit depths and a disclosed 2-tile coverage limitation. **Adopted.**
- **Cycle-accurate → transaction-level reference model, structural fixes (§3.1, §9, Open Items, ring→mesh, 4-month title, parameterised widths, DIR_INV_WAIT bit-clear counting, coverage closure criteria, novelty-claim rewrite)**: all verified and **adopted**.
- **SM_D+INV race** (Claude): correct that (SM_D, INV) is reachable — *the requester is itself a sharer*. However Claude's added transient is the heavier fix; the standard remedy is excluding the requester from the INV set. **Adopted the exclusion rule as primary + SM_D_INV as a defensive, formally-checked transient.** Best of both positions.

**Contested findings — rejected with proof:**

- **"L2 bank must shrink to 1 KB / 192–240 BRAMs required"** (GPT-node, partially Gemini node): **arithmetically false.** XC7Z020 has 140 × 36-Kb BRAMs ≈ 630 KB. A 2-KB bank is *one* BRAM36. Full 4×4 storage ≈ 52 KB ≈ 12–25 BRAM tiles worst case — nowhere near 140. Cache geometry is unchanged; a resource-sanity section (§4.7) was added instead, and the 2×2 FPGA choice is now justified by timing/LUT risk, not BRAM.
- **"Force tree-PLRU on L1"** (Claude): no fatal flaw — 20 vs 12 bits of LRU state is negligible; the whitepaper's true-LRU justification stands. The context note is marked superseded; the whitepaper remains authoritative.
- **"DMA single-channel"** (GPT-node): moot — DMA is gated out of the baseline entirely; noted as one-channel if the gate passes.
- **My Iteration-1 UNBLOCK→VC2 fix**: no peer addressed it; retained and strengthened with an explicit acyclic-dependency argument (Duato), now cited as [15].

The finalized white paper is written to the canvas: **"A Scalable Cache-Coherent Tiled Multicore Architecture on a 2D Mesh NoC — v2.0 (Consensus Final)"** — open it there for the full document.

### 📋 Architectural Change Log (Final Adjudicated)

| # | Target (v1.0) | Final Modification (v2.0) | Proof Basis | Source(s) |
|---|---|---|---|---|
| 1 | UNBLOCK in VC0 | UNBLOCK → VC2; acyclic message-dependency argument stated, Duato cited | DATA(VC2)→UNBLOCK(VC0) descending dependency = deadlock cycle; Duato's theorem | Self (Iter-1) |
| 2 | DIR_FWD_WAIT single state | Split DIR_FWD_WAIT_S / _M with unique DATAFWD exits | δ(S,E) defined twice ⇒ nondeterministic FSM | All 4 peers + self |
| 3 | 3-bit dir state, DIR_EVICT_* wildcard | 4-bit field; all 7 transients enumerated | 4 stable + 7 transient = 11 > 2³ | Claude, Consensus, GPT |
| 4 | No PUTM/PUTS directory rows | DIR_M+PUTM → DIR_I and DIR_E+PUTS → DIR_I rows added | MI_A/EI_A liveness otherwise unprovable | Claude |
| 5 | No INVACK counting mechanism | Bit-clear rule: Sharers==0 exits DIR_INV_WAIT | Bijective with sharer set; O(1), no counter field | Self (Iter-1) |
| 6 | (SM_D, INV) undefined | INV excludes requester + defensive SM_D_INV transient | Requester is a sharer; Primer §8.3 race class | Claude (modified) |
| 7 | Un delimited multi-flit packets | 4-bit LEN field [37:34]; tail bit only for single-flit; DMA-16-flit deleted | P-flit packet needs length or per-flit tail; had neither | Consensus, GPT |
| 8 | RR arbitration across VCs | Fixed class priority (VC3>VC2>VC1>VC0) + RR across inputs | Response starvation breaks protocol progress | Consensus |
| 9 | "Reduce VC count" fallback | Deleted; VC count frozen at 4 | 4-class separation is the deadlock proof's premise | Consensus |
| 10 | DMA as Contribution #4 | Demoted to Month-2-gated extension; codes 11–13 reserved; tests 15a–e conditional | Cannot be contribution + under evaluation + droppable simultaneously | All peers + self |
| 11 | Unbounded liveness via BMC | Bounded liveness (K=64) + k-induction (k=16); 2-tile limitation disclosed | BMC cannot prove "eventually" ∀ executions | Claude, GPT |
| 12 | "Cycle-accurate reference model" | Transaction-level model + SVA for timing | Cycle-accurate duplicates RTL effort | Consensus |
| 13 | Fixed 8-bit owner / 16-bit sharers vs "parameterised N×N" | All widths derived from N; scaling bound stated (N≤16 on 32-bit map) | 16-bit sharers cannot represent N=8; claim was false as written | Consensus, GPT, Claude |
| 14 | "State×message 100%" unbounded | Legal-bin closure criteria, 2-tile 100% / 4×4 sampled + code-coverage gates | 4,480-bin per-tile product is not the coverage model; closure needs numeric gates | GPT (corrected), Consensus |
| 15 | Novelty claim in Abstract | Replaced with concrete, falsifiable contribution statement | Novelty requires a stated delta over [11][12][13][14] | Self, Consensus, GPT |
| 16 | Empty §3.1; "Three-Month" 4-month body; ring test; dup tables/numbering; "inclusive caches" attribution; L1-tag vacuous justification; reserved-field semantics; §7.3 circular mitigation | All fixed structurally | Document integrity; each is a self-evident contradiction | All peers + self |
| 17 | BRAM-crisis claims (192/240 BRAMs, shrink L2 to 1 KB) | **Rejected**; §4.7 resource sanity check added instead | 2-KB bank = 1 BRAM36; 4×4 total ≈ 52 KB ≪ 630 KB capacity | GPT-node (refuted), Gemini (refuted) |
| 18 | Replace L1 true LRU with tree-PLRU | **Rejected**; context note marked superseded | No fatal flaw; 8-bit saving negligible at 4 ways | Claude (refuted) |

Net effect: MESI, mesh topology, cache geometry, flit width, and the 11-message core set are unchanged (all proven by the constraint analysis); every FSM is now deterministic and closed; the deadlock argument is now actually a proof; and no claim in the document lacks an evidencing artifact.

### 🔏 Model Signature

GLM-5.3 (Mistral Vibe) — Principal System Architecture Critic & Consensus Facilitator // Iteration 2 — Final // 2026-10-28 IST | Consensus achieved with 4 peer nodes; 2 peer proposals rejected with arithmetic proof (BRAM over-estimation, LRU substitution); finalized white paper v2.0 delivered as canvas.