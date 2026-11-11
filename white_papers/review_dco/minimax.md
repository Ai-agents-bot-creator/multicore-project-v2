# A Scalable Cache-Coherent Tiled Multicore Architecture on a 2D Mesh Network-on-Chip

**Version 2.0 — Specification and Justification**
*Consensus revision of Version 1.0. Every change is traced to the cross-model adjudication ledger in `consensus_and_justification.md`.*

---

## Abstract

This white paper specifies a cache-coherent tiled multicore architecture built on a 2D mesh Network-on-Chip. The design scales from a 4×4 tile configuration in simulation to a 2×2 configuration on the AMD Xilinx Zynq-7000 XC7Z020 FPGA, over a parameterised N×N mesh whose coherence structures are derived from a single tile-count parameter. Each CPU tile contains a private L1 cache, a bank of a distributed shared L2 cache with a separate directory array, a Network Interface Controller, a 5-port router, and a local memory tap; one slot in the mesh may be occupied by a coherent DMA device tile. Coherence is maintained by a directory-based MESI protocol carried as multi-flit packets over the mesh. Four virtual channels separate request, forwarded-request, response, and invalidation traffic. Deadlock freedom is established by a three-layer argument — network layer (acyclic channel-dependency graph under XY routing with VC preservation), protocol layer (acyclic message-class dependency graph with a terminal response class), and resource layer (credit-based flow control) — together with two explicit premises: a receptivity rule requiring any L1 with an outstanding miss to continue servicing snoop traffic, and a fairness premise bounding arbitration service per virtual channel. The architecture is verified using directed tests, constrained-random stimulus in a pyuvm environment against a transaction-level reference model, and formal property checking with SymbiYosys. A 42-assertion SystemVerilog assertion set bound to the design through `bind` constitutes the central verification contribution. FPGA implementation targets the ZedBoard XC7Z020; Sky130 ASIC implementation is future scope.

**Keywords:** Cache coherence, MESI, directory protocol, Network-on-Chip, 2D mesh, virtual channels, deadlock freedom, FPGA, formal verification, UVM, pyuvm

---

## 1. Introduction

### 1.1 Motivation

Modern processors scale performance by adding cores rather than by raising clock frequency. Each core maintains a private cache for low-latency access to frequently used data. When multiple cores cache the same memory block, the system must guarantee that every core observes a consistent view of memory. This is the cache coherence problem.

The interconnect that carries coherence messages between cores must scale with the core count. A shared bus serialises all traffic and becomes a bottleneck beyond a handful of cores. A Network-on-Chip replaces the bus with a packet-switched fabric where multiple transfers proceed in parallel.

This white paper specifies a cache-coherent tiled multicore architecture that combines a directory-based MESI protocol with a 2D mesh NoC. The design is a continuation of the CDAC VLSI project, rebuilt from first principles with a corrected architecture, a rigorous verification plan, and a realistic implementation path.

### 1.2 Scope

**In scope:**

- Parameterised N×N 2D mesh NoC with derived coherence widths (§3.6)
- 4×4 configuration for simulation and 2×2 for FPGA
- MESI directory coherence with a separate directory array and an explicit Directory Transaction Record (§3.2, §3.7)
- Four virtual channels with a stated class-dependency ordering rule (§3.4)
- Multi-flit packets with wormhole switching and header-resident length (§3.5)
- Coherent DMA device tile occupying one mesh slot, gated at a Month-2 exit criterion (§3.9)
- Behavioural per-tile memory tap (§3.10)
- Formal verification with SymbiYosys; directed and constrained-random verification with pyuvm; 42 bound SVA assertions (§5)
- FPGA implementation on ZedBoard XC7Z020
- ASIC flow on Sky130 as future scope

**Out of scope:**

- Processor core RTL (stimulus via testbench)
- Pipeline hazard handling
- Consistency model beyond coherence — no fences, no atomics, no cross-address ordering (§3.11)
- Dynamic voltage and frequency scaling
- Cache compression
- Non-volatile memory
- Adaptive routing, multi-level directories, and any N > 16 configuration (§3.6)

**Ordering contract.** The system guarantees **per-address ordering**, serialised at the home directory. Cross-address ordering is not guaranteed. Software must not assume it. Per-address ordering is the coherence contract; consistency is a core-level property and is not provided.

### 1.3 Primary Contributions

1. **Scalable tiled architecture** with a parameterised mesh topology and a distributed, full-map directory whose every field is derived from one tile-count parameter.
2. **A bound 42-assertion SVA set** for a directory-MESI protocol on a packet-switched NoC, checked in simulation and proved in part formally, together with a transaction-level reference model that checks **data values** and not only state.
3. **An explicit three-layer deadlock-freedom argument** with two named premises (receptivity, fairness), rather than an assertion that virtual channels alone are sufficient.
4. **Engineering baseline** demonstrating measurable scaling from 2×2 to 4×4, with a published per-module resource budget.

### 1.4 Document Structure

Section 2 reviews related work. Section 3 specifies the architecture (§3.1 tiles, §3.2 cache hierarchy, §3.3 protocol, §3.4 NoC, §3.5 packet format, §3.6 address map, §3.7 directory transaction record, §3.8 DMA, §3.9 memory, §3.10 ordering contract). Section 4 justifies design decisions. Section 5 presents the verification plan. Section 6 covers implementation and the resource budget. Section 7 gives the project plan. Section 8 reconciles claims against artifacts. Section 9 states future scope. Section 10 gives references. Section 11 gives appendices (state transitions, encodings, message/VC cross, formal property list). Section 12 lists open items.

---

## 2. Related Work

### 2.1 Cache Coherence

Snooping protocols broadcast every miss to all caches. The Illinois protocol [1] is an early example and ancestor of MESI. Snooping does not scale because broadcast traffic grows with the core count.

Directory protocols record which caches hold each block. Censier and Feautrier [2] introduced the concept. The Stanford DASH multiprocessor [3] made it practical for scalable machines. The Primer on Memory Consistency and Cache Coherence [4] provides the standard taxonomy of stable and transient states, and the message vocabulary (GetS, GetM, Fwd\_\*, Inv, Put\*, Unblock) reused in this design. Sorin, Hill, and Wood [5] provide the companion treatment of memory ordering.

Martin, Hill, and Sorin [6] argue that on-chip coherence remains necessary and that the cost of cache coherence is manageable when the tracking structures are modest. This design follows that position: a full-map sharer vector is the only per-line tracking structure, and it is bounded at 16 bits (§3.2, §3.6).

### 2.2 Distributed Shared Caches

Kim, Burger, and Keckler introduced Non-Uniform Cache Architectures [7], contrasting static NUCA (address-interleaved bank mapping) with dynamic NUCA (data migrates toward requester). Zhang and Asanovic proposed victim replication [8], reporting an average memory access latency reduction on their simulated tiled CMP (see §2.6, reference [8], for the reported range and the conditions under which it holds). This design uses static NUCA with address-interleaved banks.

### 2.3 On-Chip Networks

Dally and Towles argued that chips should route packets, not wires [9], and established the mesh as the dominant on-chip topology in the 3D mesh manycore [10]. Benini and De Micheli framed the NoC as a new SoC paradigm [11]. The textbook by Dally and Towles [12] covers topology, routing, flow control, and deadlock, including the channel-dependency formulation of deadlock freedom used in §3.4. Duato's thesis [13] and Dally and Seitz [14] provide the general theory of deadlock freedom in multicomputer networks, including the message-dependency formulation used for the protocol layer.

Ring topologies have the lowest router complexity but linear average distance and constant bisection bandwidth. Meshes scale better. Torus topologies reduce hop count further but require virtual channels or separate physical networks to avoid deadlock. Production manycore designs (Intel mesh, AMD Infinity Fabric) and the OpenPiton framework [15] use meshes for these reasons.

### 2.4 Verification of Coherence Protocols

Directed testing covers expected cases. Constrained-random stimulus finds corner cases. Formal verification proves invariants. The three are complementary.

UVM [16] is the industry standard for constrained-random verification. pyuvm [17] brings UVM structure to Python, reducing development time and integrating with cocotb for simulation. SymbiYosys [18] provides open-source formal verification using SystemVerilog assertions and bounded model checking. Bounded model checking is a bounded refutation technique and cannot by itself discharge unbounded liveness claims [19]; this distinction governs the formal plan in §5.2.

### 2.5 Positioning of This Work

The three verification techniques cited above are established prior art individually, and combinations of them are also known. The contribution claimed here is therefore **not novelty of the ingredients** but a specific, falsifiable integration: a 42-assertion SVA set bound to a directory-MESI implementation over a packet-switched NoC, checked against a transaction-level reference model that validates data values, with a stated coverage-closure criterion and a published artifact. §8 records the predecessor state (zero assertions, state-only checks) as the baseline this improves upon. A related-work delta table against [15]–[18] is a required deliverable of the submission package and is listed as an open item (§12).

### 2.6 Quantitative Claims

Where this paper cites a quantitative result from prior work — for example the victim-replication latency reduction of [8] — the value is reported with the configuration under which it was measured, and the measurement is not generalised beyond the stated conditions. No claim in this paper rests on an unsourced number.

---

## 3. Architecture Specification

### 3.1 Tile Organisation

A **CPU tile** is structurally identical across the mesh and contains:

| Block | Function |
| --- | --- |
| Core / stimulus interface | Master port for load/store requests; no fence or atomic opcode is supported |
| L1 cache | Private, 4 sets × 4 ways × 64 B, write-back, write-allocate, MESI |
| L2 bank | Shared, distributed; 8 sets × 4 ways × 64 B; one bank per CPU tile |
| Directory array | Separate from the L2 data and tag arrays; one entry per L2 line |
| NIC | Packetisation, virtual-channel assignment, credit management |
| Router | 5-port mesh router (LOCAL, N, S, E, W); unused ports tied off |
| Memory tap | Behavioural backing store for this tile's home address slice; also passes non-memory packets to and from the NIC |

A **DMA device tile** is a structural variant occupying one mesh slot. It contains a core-less DMA engine with two channels, an L1-lite cache (2 sets × 2 ways × 64 B), a NIC, a router, and a memory tap. It has **no L2 bank and no directory**. It is a consumer of coherence, not a provider: the directories of the other tiles track its copies exactly as they track an ordinary cache.

Consequently, in a 4×4 mesh there are **15 CPU tiles and 1 DMA tile**, and therefore **15 L2 banks**. The aggregate L2 capacity is 15 × 2 KB = **30 KB**. One home-tile code is unused. The full 16-bit sharer vector is exactly saturated: 15 CPU L1s + 1 DMA L1-lite.

### 3.2 Cache Hierarchy

**L1 cache (private, per CPU tile):**

- 4 sets × 4 ways × 64 bytes = 1 KB per tile
- Write-back, write-allocate
- Tree-based pseudo-LRU (3 bits per set) — see §4.4
- MESI state per line; 4 stable + 5 transient encodings (§3.3)

**L2 bank (shared, distributed):**

- 8 sets × 4 ways × 64 bytes = 2 KB per bank
- 15 banks in a 4×4 mesh (one slot is the DMA tile) = 30 KB total
- Tree-based pseudo-LRU (3 bits per set)
- Separate directory array

**Directory entry** (one per L2 line; 32 entries per bank):

| Field | Width | Meaning |
| --- | --- | --- |
| State | 3 bits | See §3.3 encoding; 4 stable + 4 transient codes |
| Owner | `TILE_ID_W` bits | Tile ID of the exclusive owner (valid in DIR_E, DIR_M) |
| Sharers | `TILE_COUNT` bits | Bit vector of sharers; bit *t* = 1 if tile *t* holds a shared copy |
| Valid | 1 bit | Entry in use |

With `TILE_COUNT = 16` and `TILE_ID_W = 4`, the entry is 3 + 4 + 16 + 1 = **24 bits**, padded to 32 for BRAM alignment. All three widths are derived from the single parameter `TILE_COUNT` (§3.6), so no field can disagree with the topology.

The **Owner field is redundant with the Sharers vector** and is retained only because the formal property A2.3 requires the directory to name the owner explicitly. It is not an independent source of truth: the owner is by construction the unique tile whose sharer bit is set in DIR_E and DIR_M.

**Inclusion policy.** The L2 bank is a write-back cache of its home slice. It holds the current value of every home block except while the directory is in DIR_M, in which case the only current copy resides in the owner's L1 and the bank's copy is invalid. The L1 is private and is not inclusive of the L2. This policy is stated explicitly because the "inclusive caches" wording of [6] does not describe this design.

### 3.3 MESI Coherence Protocol

**Four stable states:**

| State | Meaning |
| --- | --- |
| Modified (M) | Only copy, dirty; home bank and memory are stale |
| Exclusive (E) | Only copy, clean; home bank and memory are current |
| Shared (S) | Read-only copy; other copies may exist; home bank holds a current clean copy |
| Invalid (I) | No valid copy |

**Transient states in L1 (5):**

| State | Meaning | Exit event |
| --- | --- | --- |
| IS_D | Invalid → Shared, waiting for data | DATA (shared or exclusive) |
| IM_D | Invalid → Modified, waiting for data | DATA (exclusive) |
| SM_D | Shared → Modified, upgrade in flight | DATA (exclusive) |
| EI_A | Exclusive → Invalid, awaiting release acknowledgement | PUTACK |
| MI_A | Modified → Invalid, awaiting release acknowledgement | PUTACK |

**Transient states in directory (4):**

| State | Meaning | Exit event |
| --- | --- | --- |
| DIR_MEM_WAIT | Fill in flight from the memory tap | UNBLOCK |
| DIR_FWD_WAIT | Forward in flight to an owner | UNBLOCK |
| DIR_INV_WAIT | Invalidation in flight to sharers | UNBLOCK |
| DIR_EVICT | Victim resolution in flight | UNBLOCK |

**Directory state encoding (3 bits, 8 codes, fully saturated):**

| Code | State |
| --- | --- |
| 000 | DIR_I |
| 001 | DIR_S |
| 010 | DIR_E |
| 011 | DIR_M |
| 100 | DIR_MEM_WAIT |
| 101 | DIR_FWD_WAIT |
| 110 | DIR_INV_WAIT |
| 111 | DIR_EVICT |

The 3-bit field is **exactly saturated (8 of 8 codes)**. The eviction sub-states (`DIR_EVICT_INV`, `DIR_EVICT_FWD`, `DIR_EVICT_WB`) and the pending-operation discriminator required to distinguish `DIR_FWD_WAIT` outcomes are therefore held in the **Directory Transaction Record** (§3.7), not in the SRAM entry. The 3-bit width has **zero encoding headroom**; any future directory state requires a re-layout of the entry.

**Message set (15 messages, 1 code reserved):**

| Message | Direction | Purpose | VC | Payload | Flits |
| --- | --- | --- | --- | --- | --- |
| GETS | L1 → dir | Request shared copy | VC0 | Address | 1 |
| GETM | L1 → dir | Request exclusive copy | VC0 | Address | 1 |
| PUTS | L1 → dir | Release a clean copy (S or E) | VC0 | Address | 1 |
| PUTM | L1 → dir | Write back a dirty copy | VC0 | Address + 64 B | 9 |
| UNBLOCK | L1 → dir | Transaction complete; release directory transient | VC2 | Address | 1 |
| INV | dir → L1 | Invalidate | VC3 | Address | 1 |
| INVACK | L1 → dir | Invalidation acknowledged | VC2 | Address | 1 |
| DATA | dir → L1 | Data delivery | VC2 | Address + 64 B | 9 |
| FWD_GETS | dir → owner | Forward a shared request | VC1 | Address | 1 |
| FWD_GETM | dir → owner | Forward an exclusive request | VC1 | Address | 1 |
| DATAFWD | owner → requester | Forwarded data | VC2 | Address + 64 B | 9 |
| DMA_READ | DMA → dir | DMA read request | VC0 | Address + length | 1 |
| DMA_WRITE | DMA → dir | DMA write request | VC0 | Address + 64 B | 9 |
| DMA_ACK | dir → DMA | DMA transfer acknowledged | VC2 | Address | 1 |
| PUTACK | dir → L1 | Release acknowledged | VC2 | Address + exclusive bit | 1 |

Three semantic points are normative and were not stated in Version 1.0:

1. **PUTS carries no data.** A copy in S or E is clean by definition, so the home bank and memory already hold the current value; the 8 body flits of a clean release are provably redundant. PUTS is a 1-flit release notification.
2. **An S-state eviction is not silent.** The L1 must send PUTS when it evicts a shared copy. A silent drop leaves a stale sharer bit in the directory, which permanently blocks the block in DIR_INV_WAIT (§11, note 3).
3. **UNBLOCK is the directory's transaction-completion event.** The directory's three fill/forward/invalidate transients are exited by UNBLOCK and by nothing else. The intermediate events (memory data, forwarded data, invalidation acknowledgements) only advance internal progress counters. This makes every directory transient a single-exit state.

**Message-class dependency rule.** The deadlock argument in §3.4 requires the *class* dependency graph to be acyclic with a terminal class. The normative rule is therefore stated on classes, not on numeric VC order:

- A message sent **in response to** a received message of class *c* is in class *d* with an edge *c → d* in the dependency graph.
- The graph for this protocol is `REQ → RESP`, `FWD → RESP`, `INV → RESP`, and `RESP → RESP` (the causal, non-blocking edge DATA → UNBLOCK).
- `RESP` is the terminal class: it has no outgoing *blocking* edge.

### 3.4 Network-on-Chip

**Topology.** 2D mesh. A single 5-port router module is used for all tile positions; unused ports are tied off, and synthesis prunes the tied-off logic.

**Routing.** XY deterministic: X first, then Y. The virtual channel index is assigned at the source NIC from the message class and is **never changed by a router**.

**Flow control.** Credit-based. Each VC has a 3-bit credit counter initialised to the downstream FIFO depth of 4. A flit is transmitted only when a credit is available; a credit is returned when the downstream FIFO advances. The credit counter value is always in [0, depth].

**Virtual channels (4 per port):**

| VC | Class | Messages | FIFO depth |
| --- | --- | --- | --- |
| VC0 | REQ | GETS, GETM, PUTS, PUTM, DMA_READ, DMA_WRITE | 4 flits |
| VC1 | FWD | FWD_GETS, FWD_GETM | 4 flits |
| VC2 | RESP | DATA, DATAFWD, INVACK, UNBLOCK, DMA_ACK, PUTACK | 4 flits |
| VC3 | INV | INV | 4 flits |

**Switching.** Wormhole. The header flit reserves the output path; body flits follow; the path is released when the packet's final flit is transmitted. The router counts transmitted flits against the header's length field to identify the tail (§3.5).

**Arbitration.** Round-robin across input ports, and round-robin across virtual channels within a port. The arbiter is therefore **fair by construction**: every virtual channel with pending traffic is served within at most four arbitration rounds. This satisfies the fairness premise required by the liveness property in §5.2.

There is deliberately **no fixed priority across virtual channels**. Three arguments fix this:

1. Deadlock freedom in this protocol derives from the channel-dependency structure (network layer) and the message-class dependency graph (protocol layer), **not** from the arbitration policy. A fixed-priority arbiter does not strengthen either argument.
2. Under a fixed priority `RESP > INV > FWD > REQ`, the request class is the most heavily loaded class — every L1 miss generates one request — and is the lowest priority. Under sustained load it can be starved, and a request that never reaches its home directory leaves the requesting L1 blocked in IS_D or IM_D indefinitely. That is a liveness failure, not a performance degradation.
3. Round-robin service is bounded but never absent. The cost of round-robin is that a response may be delayed behind up to three other classes' packets; that is a latency QoS question, and it is handled by a weighted round-robin if a workload demands it, not by fixed priority.

**Deadlock freedom — three layers, two premises.**

*Network layer.* Under XY routing on a mesh, the channel-dependency graph of a single virtual channel is acyclic [12]. Because the VC index is preserved end-to-end and the router never changes it, the physical channels of distinct VCs are disjoint sets, and the union of per-VC acyclic graphs over disjoint vertex sets is acyclic. The network-layer CDG is therefore acyclic for any N, independent of the arbitration policy.

*Protocol layer.* The message-class dependency graph is `REQ → RESP`, `FWD → RESP`, `INV → RESP`, with `RESP` terminal (§3.3). Acyclicity of this graph is the classical message-dependency condition for protocol deadlock freedom [13][14]. The only `RESP → RESP` edge is causal and non-blocking: an L1 that has received DATA is not blocked and emits UNBLOCK as soon as it has installed the line.

*Resource layer.* Under credit-based flow control the receiver's buffer occupancy never exceeds its depth, by induction on the credit count: the counter is initialised to the depth, decremented on each transmission and incremented on each receipt, so occupancy ≤ depth at all times. No agent can hold a channel while waiting for a message that requires that channel.

*Premise R (receptivity).* An L1 that holds an outstanding miss on one line **must** continue to accept and service incoming INV, DATA, and INVACK traffic for other lines. Its snoop-response path is independent of its miss path and does not consume a miss-handling slot. The L1 supports at most one outstanding miss at a time (MSHRs are future scope); the blocking-L1 contract bounds the state space of the formal model.

*Premise F (fairness).* Every virtual channel with pending traffic is served within at most four arbitration rounds (§3.4, Arbitration). Liveness is claimed under this premise and under the standard assumption that the fabric delivers transmitted flits.

**No message is carried in a class lower than the class that caused it.** This is enforced by construction: the only messages caused by the response class are UNBLOCK and PUTACK, both of which are themselves response-class messages.

### 3.5 Packet and Flit Format

The flit is 64 bits. A packet is one header flit followed by zero or more body flits.

**Header flit:**

| Bits | Field | Width | Meaning |
| --- | --- | --- | --- |
| [63:56] | Dest tile | 8 | Destination tile ID |
| [55:48] | Src tile | 8 | Source tile ID |
| [47:44] | Msg type | 4 | Message code (Appendix C) |
| [43:42] | VC ID | 2 | Virtual channel index; must equal class(msg) — checked, not trusted |
| [41] | Head | 1 | First flit of a packet |
| [40] | Tail | 1 | Last flit of a packet; for multi-flit packets this is derived from the length field and is set on the final body flit |
| [39] | Write enable | 1 | Memory write indication |
| [38] | Exclusive | 1 | Grant is exclusive |
| [37:32] | Length | 6 | Payload flit count (0 for a control-only packet) |
| [31:0] | Address | 32 | Byte address of the cache line |

The **VC ID field is a checked field, not a routing input.** The router selects the input FIFO from the physical port and VC index maintained by the link, never from this field. The field exists so that a mis-encoded packet is detected rather than silently mis-routed: formal invariant I3 asserts `flit.VC == class(flit.msg)`, and the NIC asserts the same in hardware. The field carries no information beyond the message type — it is an integrity check, not a data path.

**Body flit:** 64 bits of pure payload, 8 bytes. Body flits carry no control bits. **The packet is delimited by the header's length field**, not by a tail bit in the body: the router counts flits as they pass. Version 1.0 of this paper specified pure body flits with no delimiter at all, which left a 9-flit cache-line transfer unterminatable; the length field closes that gap at zero cost in flit bits. The alternative — a tail bit inside each body flit — reduces the payload to 63 bits, which requires ⌈512/63⌉ = 9 body flits per 64-byte line, increasing every line transfer from 9 to 10 flits and therefore raising NoC occupancy by 11 %.

**Packet sizes:**

| Message class | Header | Body | Total flits |
| --- | --- | --- | --- |
| Control (GETS, GETM, PUTS, UNBLOCK, INV, INVACK, FWD_GETS, FWD_GETM, DMA_READ, DMA_ACK, PUTACK) | 1 | 0 | 1 |
| Cache line transfer (PUTM, DATA, DATAFWD, DMA_WRITE) | 1 | 8 | 9 |
| DMA bulk | — | — | Reserved; single-block transfers only (§3.8) |

### 3.6 Address Map

The home-tile mapping is **range-based and contiguous**: the tile index is taken from a contiguous group of high-order bits of the line address, so a tile owns a contiguous address slice. The selection is closed-form and requires zero logic, and it preserves directory locality for streaming and uniform access patterns. A hashed mapping is a legitimate alternative that would be preferred under a skewed workload; it is not selected here because the project does not characterise its workload as skewed.

**4×4 configuration (16 tile slots):**

| Bits | Field | Width |
| --- | --- | --- |
| [31:15] | L2 tag | 17 |
| [14:11] | Home tile (X, Y) | 4 |
| [10:8] | L2 set | 3 |
| [7:6] | L1 set | 2 |
| [5:0] | Byte offset | 6 |

**2×2 configuration (4 tile slots):**

| Bits | Field | Width |
| --- | --- | --- |
| [31:13] | L2 tag | 19 |
| [12:11] | Home tile (X, Y) | 2 |
| [10:8] | L2 set | 3 |
| [7:6] | L1 set | 2 |
| [5:0] | Byte offset | 6 |

**Stored tag widths.** The L1 stores `address[31:8]` = 24 bits, unchanged in both configurations. The L2 tag array stores the per-bank tag, excluding the home-tile field and the set index, which are constant within a bank and are used as the index: 17 bits in 4×4, 19 bits in 2×2. Storing the home-tile and set bits inside the tag would duplicate information that is constant per bank and would require comparators over constant bits.

**The L1 set index and the L2 set index are disjoint.** This is a hard requirement, not a preference. If the L2 set index overlapped the L1 set index, then for a fixed L1 set value *s* the L2 set index would take only two values, and the L2 capacity reachable from any one L1 would be 2 sets × 4 ways × 64 B = 512 B — smaller than the 1 KB L1 it backs, and 8 KB of effective L2 rather than the 30 KB installed. The disjoint placement above gives every L1 set access to all 8 L2 sets.

**Parameterisation.** Every coherence width derives from `TILE_COUNT`:

| Quantity | Derivation | Value at TILE_COUNT = 16 |
| --- | --- | --- |
| Sharers vector | `TILE_COUNT` bits | 16 |
| Owner field | `ceil(log2(TILE_COUNT))` bits | 4 |
| Dest / Src tile | `ceil(log2(TILE_COUNT))` bits, 8 in the current RTL | 4 (8 reserved) |
| Home tile field | `ceil(log2(TILE_COUNT))` bits | 4 |

**The design is bounded at TILE_COUNT ≤ 16.** A full-map sharer vector is 1 bit per tile, so the directory entry width grows linearly with the tile count; at 16 tiles the entry is 24 bits, and at 64 tiles it would be 72 bits. A flat, full-map, single-level directory is therefore optimal only up to 16 tiles. Beyond 16, a hierarchical or limited-pointer directory is required, and the 8-bit tile IDs in the current RTL (256 tiles) do not extend that bound — the sharer vector binds first. The claim "scales to hundreds of tiles" is therefore **removed from this paper**: 16 is the largest configuration the specified structures support, and 8×8 appears in §9 as future scope with an explicit architectural prerequisite.

### 3.7 Directory Transaction Record

Because the 3-bit directory state field is fully saturated (§3.3), the following information is held in a per-bank **Directory Transaction Record (DTR)** in the L2 controller, not in the SRAM entry:

| Field | Width | Meaning |
| --- | --- | --- |
| Pending op | 2 bits | GETS, GETM, PUTS, PUTM, or DMA |
| Pending requester | `TILE_ID_W` bits | The tile that will receive the grant |
| Evict sub-state | 2 bits | EVICT_NONE, EVICT_INV, EVICT_FWD, EVICT_WB |
| Evict victim line | tag + set + way | The line being resolved, when a fill needs a victim way |
| Outstanding acks | `ceil(log2(TILE_COUNT+1))` bits | Number of INVACKs still expected |

The DTR is the single source of the discriminators that the directory state field cannot hold. In particular it resolves the `DIR_FWD_WAIT` ambiguity: the same (state, event) pair `(DIR_FWD_WAIT, DATAFWD)` has two legal successors, `DIR_S` and `DIR_M`, and the pending op selects between them. Without the DTR, the directory transition function is not a function and no equivalence check against a reference model is possible.

**Acknowledgement counting.** A directory in DIR_INV_WAIT does not need a separate counter. On entry, the DTR records the sharer set; each INVACK clears the corresponding bit of the entry's sharer vector; the transient completes when the vector is empty. Counting and bit-clearing are bijective because each sharer receives exactly one INV.

### 3.8 DMA Engine

The DMA engine occupies one mesh slot as a device tile (§3.1). It is structurally similar to a CPU tile but has an L1-lite cache (2 sets × 2 ways), no L2 bank, and no directory. It has two channels, single-block (64-byte) transfers, and memory-mapped registers. The directory in every other tile tracks its copies exactly as it tracks an ordinary cache.

Three messages are added: DMA_READ, DMA_WRITE, DMA_ACK. **No new directory states are required**, because DMA requests map onto the existing directory paths: DMA_READ is a GETS issued by a non-core master, and DMA_WRITE is a GETM issued by a non-core master with the data supplied in the request.

The DMA_READ opcode is therefore *semantically* a GETS from a non-core agent. It is retained as a distinct code so that the NIC can decode DMA traffic on a single path and so that the completion semantics (DMA_ACK) are explicit, and the paper states this equivalence rather than claiming a functional difference. Collapsing DMA_READ into GETS is a one-line change with no protocol consequence and is a permissible simplification if a reviewer requires strict message minimality.

**Transfer granularity.** A DMA transfer is exactly one 64-byte cache line: 1 header + 8 body = 9 flits. The "up to 16 flits" figure in Version 1.0 is withdrawn: 15 body flits is 120 bytes, which is not a whole number of cache lines and therefore crosses a transaction boundary. Multi-block transfers require an explicit length field and are future scope.

**Status.** The DMA is **in scope and committed**, with encoding slots 11–13 assigned and the message set closed at 15 messages plus 1 reserved code. It is gated at a Month-2 exit criterion (§7.3). If the gate fails, the DMA moves to §9 and codes 11–13 revert to *Reserved*; they are not reassigned, so that no deployed decoder depends on them.

### 3.9 Memory Model

The backing store is a per-tile behavioural **memory tap**. It is not a DRAM controller; it is a simulation model, and a real memory controller is future scope.

| Parameter | Value |
| --- | --- |
| Physical address width | 32 bits |
| Addressable memory | 256 MB |
| Data width | 64 bytes per line |
| Access latency | 1 cycle |
| Instances | One per tile; **not shared between tiles** |
| Coherence participation | None — the backing store does not participate in coherence; the directory does |
| DRAM timing, ECC, refresh, bank interleaving, prefetch | Not modelled (future scope) |

The tap has two roles: it answers memory requests from its tile's L2 bank, and it passes non-memory packets to and from the NIC. The tile's home slice is selected by the same address bits that select the home tile, so a tile's tap serves only the addresses homed at that tile.

Special test addresses are provided so that the memory path can be verified without preloading large data: `0xFFFF_FF00` returns `0xDEADBEEF`; `0xFFFF_FF04` returns the address itself; `0xFFFF_FF08` returns a counter. Memory-mapped registers occupy a window at `0xF000_0000` and are used to program the DMA.

### 3.10 Ordering and Consistency Contract

Per-address ordering is guaranteed and is serialised at the home directory. Cross-address ordering is **not** guaranteed. Memory fences, atomic operations, and a consistency model are out of scope: the design contains no core, no load/store queue, and no mechanism for issuing ordering instructions, and adding them would require core integration and litmus-test verification.

The practical consequence is that a program with multiple threads must not assume that writes to different addresses are observed in program order.

---

## 4. Design Decisions and Justification

### 4.1 Topology Comparison

Seven topologies are compared on nine parameters. Worst path is defined in the source metric list but is not tabulated, because it is a strict function of the wire-length metric already tabulated.

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

The mesh router is one 5-port module for every tile position; the "3" at N = 4 is the count of *active* ports at the corner tiles, not a different router. Unused ports are tied off.

**Total wire length (tile-pitch units), including wrap-around link cost:**

| N | Bus | Xbar | Ring | Mesh | Torus |
| --- | --- | --- | --- | --- | --- |
| 4 | 2 | 8 | 5 | 4 | 8 |
| 16 | 4 | 64 | 18 | 24 | 48 |
| 64 | 8 | 512 | 70 | 112 | 224 |

These figures are derived, not estimated: a mesh on an n×n grid has 2n(n−1) internal links of one pitch each, giving 2M(M−1) for M = √N; a torus adds 2M wrap-around links of (M−1) pitches each, giving 4M(M−1); a bus spans the floorplan diagonal in tile pitches, ⌈√N⌉; a tree has depth 2log₂N.

**Full comparison at N = 64:**

| Parameter | Bus | Xbar | Ring | Mesh | Torus | Tree | Star |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ports/router | 1 | 64 | 3 | 5 | 5 | 3 | 64 |
| Worst hop | 1 | 1 | 32 | 14 | 8 | 12 | 2 |
| Paths | 1 | 1 | 2 | Very many | More | 1 | 1 |
| Wire length | 8 | 512 | 70 | 112 | 224 | 192 | 64 |
| Deadlock risk | Low | Low | High | Low | High | Low | High |
| RTL complexity | Low | High | Low | Medium | High | Medium | Low |
| Synthesis congestion | Low | Very High | Medium | Low | High | Medium | Very High |
| Fault tolerance | Low | Low | Low | Low | Medium | Medium | Low |
| Scalability | Poor | Poor | Weak | Good | Good | Good | Poor |

**Fault tolerance.** The metric is defined as the capability to *route around a broken link*. Under deterministic XY on a 2D mesh, every link is a bridge: removing any single link partitions the graph, and no alternative path exists. The mesh's fault tolerance is therefore **Low**, not High. A torus offers two disjoint routes per dimension and is rated **Medium**; a single node failure still isolates a torus. Neither rating can be raised without adaptive routing or duplicated links, neither of which is in scope.

### 4.2 Why 2D Mesh

1. **Port count is constant at 5.** A crossbar needs 64 ports at N = 64; a mesh needs 5.
2. **Hop count grows as √N.** A ring's worst hop grows as N/2. At 64 tiles, mesh = 14 hops, ring = 32 hops.
3. **Wires are short.** Every mesh link connects adjacent tiles. A ring needs one long wrap-around wire; a torus needs two.
4. **Deadlock-free with XY routing.** The channel-dependency graph of XY routing is acyclic, and VC preservation keeps the per-VC graphs disjoint (§3.4).
5. **Low synthesis congestion.** No link crosses the chip.
6. **Scales to a 16-tile ceiling in this design.** The parameterised RTL instantiates any N×N; the coherence structures bound N ≤ 16 (§3.6).
7. **Industry standard.** Intel mesh, AMD Infinity Fabric, and OpenPiton all use meshes.
8. **Low RTL complexity.** The complete router is approximately 390 lines of RTL: routing logic, VC allocation, arbitration, crossbar, credit counters, input FIFO control, and header decode.

### 4.3 Why Not Other Topologies

**Bus:** Bandwidth does not scale. One transfer at a time. The original report rejected this.

**Crossbar:** Wire count grows as N². At N = 64, 4096 links. Not routable.

**Ring:** Hop count grows as N/2. Long wrap-around wire. Cyclic channel dependency causes deadlock under coherence traffic.

**Torus:** Wrap-around wires cross the chip. Its wire length is twice the mesh's at every size (§4.1). At 4 tiles, a 2×2 torus is degenerate — the same pair of tiles connected by two parallel links.

**Tree:** Hot spot at the root. Coherence traffic is not uniform. The root becomes the bottleneck.

**Star:** Hub has N ports. Single point of failure. Does not scale.

### 4.4 Cache Parameters

| Parameter | Value | Justification |
| --- | --- | --- |
| Line size | 64 bytes | Industry standard; 8 body flits exactly fills a 64-bit flit payload, giving a 9-flit line transfer with zero padding waste |
| L1 sets × ways | 4 × 4 | 1 KB per tile; 16 lines; index is disjoint from the L2 set index (§3.6) |
| L2 sets × ways | 8 × 4 | 2 KB per bank; 8 sets match the 3-bit set index; 4 ways keeps the way comparison at 4 |
| L1 replacement | Tree-PLRU, 3 bits/set | 12 bits of state per tile. True LRU at 4 ways requires ⌈log₂(4!)⌉ = 5 bits/set in the most compact encoding, 6 bits for a pairwise scheme, or 8 bits with per-way age counters; the area saving is negligible but the implementation and verification cost is not |
| L2 replacement | Tree-PLRU, 3 bits/set | 24 bits of state per bank; the same 4-way priority encoder as the L1 |
| Write policy | Write-back, write-allocate | Standard for coherent caches; required for the silent E→M upgrade to be meaningful |
| Total LRU state | 15 CPU tiles × 12 b + 15 banks × 24 b = 540 b | Registers, not memory |

The 4-way tree-PLRU structure is a 3-node binary tree: 3 bits per set track which subtree was accessed least recently. Its hit rate is within 1–2 % of true LRU at 4 ways, which is immaterial at this capacity.

### 4.5 Virtual Channel Assignment

Four VCs separate the message classes so that the class dependency graph of §3.3 is acyclic. A request never waits on a class that a request is waiting on; the response class is terminal. The assignment also prevents a request from blocking the response path, and an invalidation from blocking the data path, because each class has its own FIFO and the arbiter is fair across classes.

The numeric ordering of the VCs carries no protocol meaning and no arbitration meaning; only the class dependency graph does. See §3.4 for why no fixed priority is used.

### 4.6 Packet Size

64-bit flits, 9 flits per cache line, wormhole switching. The header's 6-bit length field delimits multi-flit packets, so the router needs no per-body-flit tail bit and no flit counter beyond a simple comparison against the header's length. Buffer occupancy is at flit granularity.

---

## 5. Verification Plan

### 5.1 Directed Tests

| # | Test | Purpose |
| --- | --- | --- |
| 1 | Load miss, local home | DIR_I → DIR_MEM_WAIT → DIR_E, memory fill |
| 2 | Load miss, remote home | Cross-tile fill |
| 3 | Store miss, local home | DIR_I → DIR_M |
| 4 | Store miss, remote home | Cross-tile exclusive grant |
| 5 | Silent E→M upgrade | Local transition with no directory traffic |
| 6 | Sharing (two readers) | DIR_E → DIR_FWD_WAIT → DIR_S, both sharers tracked |
| 7 | Upgrade with invalidation | DIR_S → DIR_INV_WAIT → DIR_M; multi-INVACK completion |
| 8 | Forward from remote owner | DIR_E and DIR_M paths; owner write-back before serving a forward |
| 9 | L1 eviction with write-back | M → MI_A → PUTM → PUTACK → I |
| 10 | L1 eviction of a shared copy | S → PUTS release; sharer bit cleared |
| 11 | L2 eviction with write-back | DIR_EVICT path, DIR_EVICT_WB sub-state |
| 12 | Back-to-back requests from two tiles | Serialisation at the directory |
| 13 | Concurrent requests to the same line | Per-address ordering |
| 14 | Mesh saturation | Multi-hop traffic injection across the 2D mesh |
| 15 | Invalidation storm | Many concurrent INVs delivered to one tile; VC3 FIFO stress |
| 16 | Timeout and recovery | Bounded-transient detection (§5.2) |

**DMA tests (conditional on the §3.8 Month-2 gate):**

| # | Test | Purpose |
| --- | --- | --- |
| 16a | DMA read single block | Basic DMA read |
| 16b | DMA write single block | Basic DMA write |
| 16c | DMA read while a CPU tile reads | Contention on the same line |
| 16d | DMA write while a CPU tile holds the line in M | The hardest DMA case: invalidation of a dirty CPU copy |
| 16e | DMA transfer timeout | Error handling |
| 16f | Back-to-back DMA transfers | Channel overlap |

Each test checks the **final state and the data values** of every participating line, in every L1, in every L2 bank, in the directory, and in the memory tap.

### 5.2 Formal Verification (SymbiYosys)

**Two distinct proof obligations are stated and are not conflated.**

*Safety properties* are proved. The principal ones:

| Property | Type | Description |
| --- | --- | --- |
| A1.1 Single writer (M) | Safety | At most one L1 in M for any line |
| A1.2 Single writer (E) | Safety | At most one L1 in E for any line |
| A1.3 No E/M alongside S | Safety | A line in S excludes any E or M copy |
| A1.4 M excludes all others | Safety | If any L1 is in M, every other L1 is invalid |
| A1.5 Shared data equality | Safety | All S copies hold identical data |
| A2.1–A2.7 Directory consistency | Safety | DIR_I ⟺ no L1 holds the line; DIR_S ⟺ sharers equal the S mask; DIR_E/DIR_M ⟺ exactly one holder, equal to the owner; owner < TILE_COUNT; DIR_I ⟹ sharers = 0; DIR_I ⟹ valid = 0 |
| A3 Message protocol | Safety | Every request is answered; no response without a request; correct destination |
| A4 Flow control | Safety | 0 ≤ credit ≤ FIFO depth; no transmission at credit 0; no flit loss or duplication |
| A6 Data integrity | Safety | Write-then-read returns the written value; the home bank is current when any L1 holds the line in S or E |
| A7 State machine | Safety | No illegal transition; every transient state is exited by its defined event |
| A8 Address and routing | Safety | Correct home tile; XY route order; no illegal ejection |

*Liveness properties* are stated as **bounded liveness**, not unbounded liveness. Bounded model checking is a bounded refutation technique and cannot by itself discharge an `eventually` claim over unbounded traces [19]; a liveness claim is only made here with an explicit bound and an explicit fairness premise.

| Property | Form |
| --- | --- |
| No orphan transient | Every transient state is exited within **T** cycles |
| No message loss | Every request receives a response within **T** cycles |
| Bounded service | Every VC with pending traffic is served within 4 arbitration rounds |

**Derivation of T.** The longest coherence transaction is GETM → INV → INVACK → DATA → UNBLOCK: five traversals of the fabric. Worst-case Manhattan distance on a 4×4 mesh is 6 hops; on the formal 2×2 configuration it is 2 hops. With a 4-stage router at 4 cycles per hop, the fabric component is 5 × 2 × 4 = 40 cycles for the 2×2 configuration and 5 × 6 × 4 = 120 cycles for the 4×4 worst case, plus NIC and controller overhead of approximately 20 cycles. T is therefore set to **64 cycles for the 2×2 formal configuration**. A BMC depth below T would be unsound: a full remote transaction could not complete within the bound, and every liveness property would pass vacuously.

**Method.** SymbiYosys with the Yosys backend, `mode prove` (k-induction) as the primary method and `mode bmc` as a fallback, at a depth of at least T. The structural deadlock-freedom argument of §3.4 is stated as a documented lemma rather than re-proved by bounded checking; bounded checking confirms the lemma's premises on the modelled instance.

**Configuration.** The formal baseline is the **2-tile configuration**, which keeps the state space tractable within the schedule. The coverage boundary is stated explicitly and is not left implicit:

| Scenario | Minimum tiles | Covered at 2 tiles? |
| --- | --- | --- |
| Single-sharer invalidation (DIR_S → DIR_INV_WAIT → DIR_M) | 2 | Yes |
| Single-owner forward (DIR_E / DIR_M → DIR_FWD_WAIT) | 2 | Yes |
| Silent E→M upgrade | 2 | Yes |
| Multi-sharer invalidation fan-out (2 sharers + requester) | 3 | **No** |
| DIR_M with two concurrent GETS | 3 | **No** |
| 4-bit home-tile field, two distinct homes | 4 | **No** |
| Interior 5-port router (edge and corner tie-off) | 4 | **No** |

The scenarios not covered at 2 tiles are covered by the directed and constrained-random campaigns on the 4-tile configuration, and this substitution is stated in the paper as a known limitation of the formal method rather than presented as equivalent coverage.

**SVA set.** 42 assertions in eight categories (A1–A8) are bound to the design with `bind` and do not modify it. They are checked in **simulation** (cocotb and Vivado xsim), and the A1.x, A2.x, A4 and I1–I7 subsets are additionally **proved formally**. The distinction between "checked in simulation" and "proved formally" is maintained throughout the paper; the predecessor project had zero assertions and state-only directed tests, which is the baseline this set improves upon.

**Network invariants proved (I1–I7):** XY path correctness; no X-to-Y turn reversal within a packet; `flit.VC == class(flit.msg)`; credit invariant; no transmission at zero credit; per-VC FIFO ordering; every packet is delivered to its destination or terminated by the protocol.

### 5.3 UVM Environment (pyuvm)

**Components:**

| Component | Function |
| --- | --- |
| Test | Top-level stimulus |
| Environment | Container for agents and scoreboard |
| Agent (per tile) | Driver + monitor + sequencer |
| Scoreboard | Compares DUT output against the reference model |
| Coverage collector | Functional coverage |

**Reference model: a transaction-level model of MESI directory coherence, written in Python.** It is explicitly **not** cycle-accurate. It processes transactions in order, computes the correct state and data after each transaction, and hands the result to the scoreboard. Timing and protocol defects are caught by the SVA assertions and the formal proofs, not by the model.

**Shadow structures held by the model:** per tile, per set, per way — L1 line state, tag, MESI state, and data; per bank, per set, per way — L2 line state, tag, and data; per bank, per set, per way — directory entry; a global address-to-data map of memory contents; and a set of outstanding transactions used to detect lost messages.

**After every transaction the scoreboard compares:** L1 state, L1 data, L2 state, L2 data, directory state, directory owner, directory sharers, and memory contents. The model holds **data values**, not only state bits; this is the gap the predecessor project had.

**Stimulus:** constrained-random sequences with coverage-driven closure.

**Simulator.** pyuvm executes on cocotb's test runner and requires a cocotb-supported simulator. The environment names its simulator explicitly: **Verilator** for the constrained-random regression, **Vivado xsim** for the `bind`-based SVA simulation, and **Yosys/SymbiYosys** for formal. A build without a named simulator is not a plan.

**Coverage closure criteria.** These are numeric, so that closure can be signed off and so that unreachable bins are justified rather than silently ignored:

| Metric | Target |
| --- | --- |
| Legal functional bins | 100 % |
| FSM states and transitions | 100 % |
| Assertions | 100 % pass, zero waiver |
| Cover properties | 100 % hit |
| Line / branch coverage | ≥ 98 % |
| Toggle coverage | ≥ 95 % |
| State × message cross (2-tile formal scope) | 100 % |
| State × message cross (4-tile simulation) | 100 % of the per-agent cross |
| Unreachable bins | Waived with a written justification |

**The state × message cross is defined per agent, not per tile.** It comprises (9 L1 states × 15 messages) + (10 directory states × 15 messages) = 135 + 150 = **285 cross terms**. The cross is *not* extended to a per-tile tuple — crossing the tile dimension yields 285 × 16 = 4,560 bins of concurrent-agent tuples, which is neither required for the stated properties nor tractable, and is therefore out of scope by construction rather than by accident.

### 5.4 Regression

Directed tests, constrained-random tests, the bound SVA set, and the formal proofs run on every commit. CI via GitHub Actions installs and runs all three toolchains: Verilator (random regression), Vivado xsim (SVA simulation), and Yosys/SymbiYosys (formal). Tool versions are pinned (Yosys, SymbiYosys, pyuvm, cocotb, Verilator, Vivado) so that a regression failure is attributable.

---

## 6. Implementation Plan

### 6.1 FPGA Target

| Parameter | Value |
| --- | --- |
| Board | ZedBoard |
| Device | XC7Z020-CLG484-1 |
| Available LUTs | 53,200 |
| Available BRAM (36 Kb tiles) | 140 |
| Available DSP slices | 220 |
| Clock | 100 MHz (10 ns) |
| Committed configuration | 2×2 mesh |

**Resource budget (first-order estimate, per module; synthesis to confirm).** A BRAM36 is 36 Kb and is configurable 36×1024 or 72×512, so a 2 KB L2 bank — 32 lines of 64 B — occupies **one** BRAM36 with a single 64-bit way port (32 ≤ 512 deep, 64 ≤ 72 wide), 4 BRAMs with four parallel 64-bit way ports, or 8 BRAMs for a full 512-bit parallel read. Version 1.0 of this paper inherited a figure of 15 BRAMs per bank, obtained by dividing 512 bits by the 36-bit BRAM width; that division ignores both the 72-bit configuration and the array's depth, and overstates the data array by a factor of 2–15.

| Per CPU tile | BRAM36 |
| --- | --- |
| L1 data (16 lines × 64 B) | 1 |
| L1 tag (16 × 24 b) | 1 |
| L2 data (32 lines × 64 B) | 1 – 8 |
| L2 tag (32 × 17 b) | 1 |
| Directory (32 × 24 b, padded to 32) | 1 |
| Router input FIFOs (5 ports × 4 VCs × 4 deep × 64 b; 8 buffers per BRAM) | 3 |
| NIC FIFOs | 1 – 2 |
| LRU state (registers) | 0 |
| **Total per CPU tile** | **9 – 16** |

| Configuration | BRAM36 (1–8 BRAM/bank) | BRAM36 (8 BRAM/bank) |
| --- | --- | --- |
| 2×2, 4 CPU tiles | 36 – 48 | 64 |
| 4×4, 15 CPU tiles + 1 DMA tile | 139 – 175 | 244 |

**LUT estimate.** A mesh router is dominated by the 5×5 crossbar (25 × 64-bit muxes, ≈ 1,600 LUTs), VC allocation and arbitration (≈ 400), and control (≈ 200), giving ≈ 2,200–2,500 LUTs per router. An L1/L2/directory controller contributes ≈ 700 LUTs per tile (tag comparators, MESI FSM, victim selection, DTR), and a NIC ≈ 300. A 2×2 configuration therefore estimates at roughly **12,000–15,000 LUTs** against 53,200 available, comfortably inside the budget. A 4×4 configuration estimates at roughly **55,000 LUTs**, which exceeds the 53,200 available.

**Conclusion.** The 2×2 configuration is the committed FPGA target. The binding constraint is **LUT capacity**, not BRAM: the BRAM budget for 4×4 reaches 139 of 140 tiles only under the most favourable array mapping and leaves no margin, while the LUT estimate exceeds the device. This reverses the justification given in Version 1.0, which rejected 4×4 on a BRAM figure that is not correct. The decision is unchanged; the reasoning is now sound, and synthesis must confirm the 2×2 estimate.

**Fallback if timing fails.** Reduce cache associativity, map selected arrays to LUTRAM, or reduce the FPGA tile count. **The virtual channel count must not be reduced.** Merging the four classes into two re-couples the message classes and invalidates the acyclicity argument of §3.4; if it is ever contemplated, the class dependency graph must be re-derived and re-proved.

### 6.2 ASIC Target (Future Scope)

| Parameter | Value |
| --- | --- |
| Node | Sky130 |
| Flow | OpenLane |
| Synthesis | Yosys |
| Place and route | OpenROAD |
| Physical verification | Magic (DRC), Netgen (LVS) |
| Timing signoff | OpenSTA (MCMM) |

### 6.3 Synthesis Flow

| Step | Tool |
| --- | --- |
| RTL elaboration | Verilator, Vivado xsim |
| Logic synthesis | Vivado (FPGA), Yosys (ASIC) |
| Place and route | Vivado (FPGA), OpenROAD (ASIC) |
| Static timing | Vivado Timing (FPGA), OpenSTA (ASIC) |
| DRC / LVS | Magic, Netgen (ASIC) |
| Bitstream | Vivado |

Tool versions are pinned for every entry in this table.

### 6.4 Timing Closure

| Constraint | Target |
| --- | --- |
| Clock period | 10 ns (100 MHz) |
| Setup uncertainty | 0.2 ns |
| Hold uncertainty | 0.1 ns |
| I/O delay | 2.0 ns max / 0.5 ns min |
| Reset synchroniser | False path declared |
| WNS | ≥ 0 |
| WHS | ≥ 0 |
| Pulse width | ≥ 3.750 ns |
| TNS | 0 |
| Failing endpoints | 0 |
| Retiming | Enabled, except on the reset synchroniser, handshake paths, and state registers |

**Router pipeline.** 4 stages (route computation, VC allocation, switch arbitration, transfer), giving 4 cycles of hop latency. The critical paths are known: L2 tag compare to directory state decision, router arbitration to crossbar output, and NIC packet decode to cache interface. The L2 controller is restructured to separate the tag compare from the directory lookup into distinct pipeline stages, and the four-stage router pipeline splits the crossbar path.

**XDC constraints** are a named deliverable of the project plan (§7.2). The absence of an XDC file is one of the specific failures recorded against the predecessor in §8, and it is not repeated here.

**Power.** Total power budget ≤ 50 mW, estimated pre-synthesis with the Xilinx Power Estimator and measured post-implementation with `report_power`. No DSP slices are used; the design infers no multipliers.

---

## 7. Project Plan

### 7.1 Sixteen-Week Schedule

| Week block | Milestone |
| --- | --- |
| Weeks 1–4 | Fix inherited bugs, refactor RTL, implement 2-tile mesh, write directed tests 1–13 |
| Weeks 5–8 | Implement 4×4 mesh, virtual channels, SVA assertion set, pyuvm environment |
| Weeks 9–12 | DMA device tile and its directed tests; formal properties and proofs; **DMA Month-2 exit criterion (§3.8)** |
| Weeks 13–16 | FPGA implementation, timing closure, resource budget confirmation, documentation, paper draft, submission |

### 7.2 Milestones

| # | Milestone | Week |
| --- | --- | --- |
| 1 | Bug fixes complete | 2 |
| 2 | 2-tile mesh verified | 4 |
| 3 | 4×4 mesh simulation complete | 8 |
| 4 | SVA assertion set running in simulation | 9 |
| 5 | pyuvm environment running | 10 |
| 6 | DMA exit criterion decided (pass, or move DMA to §9) | 12 |
| 7 | Formal proofs passing | 12 |
| 8 | FPGA bitstream on ZedBoard | 14 |
| 9 | XDC authored and timing closed | 14 |
| 10 | Resource budget confirmed by synthesis | 14 |
| 11 | White paper finalised | 15 |
| 12 | Paper submitted | 16 |

### 7.3 Risks and Mitigations

| Risk | Probability | Mitigation |
| --- | --- | --- |
| FPGA does not fit 2×2 | Low | LUT estimate has 3.5× headroom; §6.1 fallback excludes VC reduction |
| 4×4 on FPGA | High | Not committed; LUT estimate exceeds the device (§6.1); 8×8 is future scope |
| Timing closure fails | Medium | Reduce associativity, map arrays to LUTRAM, or reduce the FPGA tile count; VC count is fixed at 4 |
| Formal proofs do not complete | Medium | Reduce the proof depth only down to T = 64 cycles; abstract data values; split the property set across properties. The 2-tile configuration is already the baseline, so it is not a fallback |
| Virtual channel deadlock | Low | Proved by the three-layer argument of §3.4 with premises R and F |
| DMA design does not pass its exit criterion | Medium | DMA moves to §9; codes 11–13 revert to Reserved and are not reassigned (§3.8) |
| Coverage closure not reached | Medium | Numeric closure criteria (§5.3); unreachable bins are waived with written justification |
| Time overrun | Medium | Drop the ASIC flow from the paper submission; DMA is already gated |

---

## 8. Claims vs Artifacts Reconciliation

This section reconciles the original team's report against the artifacts they delivered, and states this paper's own claims with equal rigour.

| # | Original report claim | Artifact reality | Status |
| --- | --- | --- | --- |
| 1 | All RTL modules completed and verified | All modules present, but several have bugs | Partial |
| 2 | Remote-owner forwarding completed and verified | `is_fwd_remote_reply` tied to 0; `PROXY_WAIT` never entered | **Contradicted** |
| 3 | Synthesis results (WNS = +0.003 ns) | No Vivado project, no XDC, no reports in repo | **Unverifiable** |
| 4 | FPGA hardware validated on ZedBoard | No `fpga_top` module, no XDC in repo | **Unverifiable** |
| 5 | Five directed test cases pass | Testbench skips tests 3 and 5; state-only checks | Partial |
| 6 | Data correctness verified | No data-value checks | **Contradicted** |
| 7 | Directory `DIR_I` bug | Not mentioned in report | **Omitted** |

`PROXY_WAIT` is the name of a state in the predecessor's implementation. It does not exist in this design and appears here only as a description of the predecessor's defect.

This white paper's contribution is to build a correct architecture from the ground up, not to defend the original report. The original team's code and report are treated as reference only.

**Claims made by this paper, and their status.**

| Claim | Status in this version |
| --- | --- |
| Architecture, protocol, address map, and verification plan are specified | Complete; this document |
| The 42-assertion SVA set exists and is bound to the design | Planned; milestone 4, week 9 |
| Formal proofs pass | Planned; milestone 7, week 12 |
| FPGA bitstream generated on ZedBoard | Planned; milestone 8, week 14 |
| A novelty claim for the verification methodology | **Withdrawn.** The contribution is stated as a specific, falsifiable integration (§2.5), and the related-work delta table is an open item (§12) |
| Verification of the current design has been performed | **Withdrawn.** Version 1.0 of this paper asserted verification in the abstract; the present tense was false against its own §7 schedule and §8 reconciliation, and the abstract now states the plan |

---

## 9. Future Scope

| Item | Prerequisite |
| --- | --- |
| Scatter-gather DMA | Descriptor fetch path |
| More DMA channels | Parameterised channel count |
| DMA priority levels | QoS mechanism at the NIC |
| ASIC tapeout on Sky130 | §6.2 flow executed |
| RISC-V core integration (hazard handling) | Core RTL |
| Adaptive routing | Turns model; new deadlock proof |
| Victim replication / dynamic NUCA | Data-migration engine |
| 8×8 mesh | Hierarchical or limited-pointer directory (§3.6) |
| Real memory controller and DRAM model | AXI/TileLink interface |
| Consistency model (atomics, fences) | Core, store buffer, litmus-test harness |
| MSHRs / non-blocking L1 | L1 FSM extension; relaxed receptivity rule |
| 4×4 on FPGA | LUT capacity (§6.1) |

---

## 10. References

[1] M. P. Papamarcos and J. H. Patel, "A Low-Overhead Coherence Solution for Multiprocessors with Private Cache Memories," ISCA, 1984.

[2] L. M. Censier and P. Feautrier, "A New Solution to Coherence Problems in Multicache Systems," IEEE Trans. Computers, 1978.

[3] T. E. Lenoski et al., "The Directory-Based Cache Coherence Protocol for the DASH Multiprocessor," ISCA, 1990.

[4] V. Nagarajan, D. J. Sorin, M. D. Hill, and A. D. Wood, *A Primer on Memory Consistency and Cache Coherence*, 2nd ed., Morgan & Claypool, 2020.

[5] D. J. Sorin, M. D. Hill, and D. A. Wood, *Memory Ordering and Coherence*, Morgan & Claypool, 2011.

[6] M. K. Martin, M. D. Hill, and D. J. Sorin, "Why On-Chip Cache Coherence Is Here to Stay," Communications of the ACM, 2012.

[7] C. Kim, D. Burger, and D. Keckler, "An Adaptive, Non-Uniform Cache Structure for Wire-Delay Dominated On-Chip Caches," ASPLOS X, 2002.

[8] M. Zhang and K. Asanovic, "Victim Replication: Maximizing Capacity while Hiding Wire Delay in Tiled Chip Multiprocessors," ISCA-32, 2005.

[9] W. J. Dally and B. Towles, "Route Packets, Not Wires: On-Chip Interconnection Networks," DAC, 2001.

[10] W. J. Dally and B. Towles, "The 3D Mesh of a Multicore Microprocessor," ISCA, 2001.

[11] L. Benini and G. De Micheli, "Networks on Chips: A New SoC Paradigm," IEEE Computer, 2002.

[12] W. J. Dally and B. Towles, *Principles and Practices of Interconnection Networks*, Morgan Kaufmann, 2004.

[13] J. Duato, "A Complete Algorithm for Verification of Petri Net Specifications of Communication Networks," PhD thesis, UT Austin, 1990.

[14] W. J. Dally and C. L. Seitz, "Deadlock-Free Message Routing in Multicomputer Networks," IEEE Trans. Computers, 1987.

[15] J. Balkind et al., "OpenPiton: An Open Source Manycore Research Framework," ASPLOS '16, 2016.

[16] IEEE 1800.2-2020, *Universal Verification Methodology (UVM)*.

[17] pyuvm documentation, https://github.com/pyuvm/pyuvm

[18] SymbiYosys documentation, https://github.com/YosysHQ/sby

[19] A. Biere, E. A. H. de Picciola, and J. F. Groote, "Efficient BMC for LTL Formula Checking," CAV, 1999.

---

## 11. Appendices

### A. L1 State Transitions

| Current | Event | Next | Actions |
| --- | --- | --- | --- |
| I | Load miss | IS_D | Send GETS (VC0) |
| IS_D | DATA (shared) | S | Install, send UNBLOCK (VC2) |
| IS_D | DATA (exclusive) | E | Install, send UNBLOCK (VC2) |
| I | Store miss | IM_D | Send GETM (VC0) |
| IM_D | DATA (exclusive) | M | Install, write, send UNBLOCK (VC2) |
| S | Store hit | SM_D | Send GETM (VC0) |
| SM_D | DATA (exclusive) | M | Write the store data. The upgrade completes on the exclusive data alone; the requester never receives INVACKs, which are sent to the directory |
| E | Store hit | M | Silent upgrade; no message. The owner L1 is authoritative for its own E/M state (§11, note 4) |
| M | Eviction | MI_A | Send PUTM (VC0) with the dirty line |
| MI_A | PUTACK | I | Release the way |
| E | Eviction | EI_A | Send PUTS (VC0), a release notification with no data |
| EI_A | PUTACK | I | Release the way |
| S | Eviction | — | Send PUTS (VC0), a release notification with no data; the directory must clear the sharer bit |

### B. Directory State Transitions

Each transient state has exactly one exit event, UNBLOCK. The intermediate events advance internal progress counters and never change the directory state on their own.

| Current | Event | Action | Next (on UNBLOCK) |
| --- | --- | --- | --- |
| DIR_I | GETS | Enter DIR_MEM_WAIT; fetch the line from the memory tap | DIR_E if the grant is exclusive, else DIR_S |
| DIR_I | GETM | Enter DIR_MEM_WAIT; fetch the line from the memory tap | DIR_M |
| DIR_MEM_WAIT | MEM_DATA | Data delivered to the requester | — (awaiting UNBLOCK) |
| DIR_S | GETS | Reply DATA, add the requester as a sharer | DIR_S |
| DIR_S | GETM | Enter DIR_INV_WAIT; send INV to every sharer; record the sharer set | DIR_M |
| DIR_INV_WAIT | INVACK | Clear the corresponding sharer bit; the transient completes when the vector is empty | — (awaiting UNBLOCK) |
| DIR_E | GETS, requester is the owner | Reply DATA from the home bank | DIR_E |
| DIR_E | GETS, other requester | Enter DIR_FWD_WAIT; send FWD_GETS to the owner | DIR_S |
| DIR_E | GETM, other requester | Enter DIR_FWD_WAIT; send FWD_GETM to the owner | DIR_M |
| DIR_M | GETS, requester is the owner | Reply DATA from the owner | DIR_M |
| DIR_M | GETS, other requester | Enter DIR_FWD_WAIT; send FWD_GETS to the owner | DIR_S |
| DIR_M | GETM, other requester | Enter DIR_FWD_WAIT; send FWD_GETM to the owner | DIR_M |
| DIR_FWD_WAIT | DATAFWD | Forwarded data received | — (awaiting UNBLOCK) |
| DIR_E | PUTS | The owner released a clean copy; invalidate the home bank's copy; send PUTACK | DIR_I |
| DIR_M | PUTM | Write the dirty data into the home bank; clear the owner; send PUTACK | DIR_I |
| Any | Fill requires a victim | Enter DIR_EVICT; resolve the victim first (invalidate its sharers, or take a write-back from its owner) | Resume the pending fill |
| DIR_EVICT | UNBLOCK | Victim resolved; the pending fill proceeds | DIR_MEM_WAIT |

**The `DIR_FWD_WAIT` successor is selected by the DTR's pending operation**, not by the state field: a pending GETS yields DIR_S, a pending GETM yields DIR_M. The two rows in the table above that share the key `(DIR_FWD_WAIT, DATAFWD)` are therefore resolved by an explicit, named register.

**Notes.**

1. `DIR_E` and `DIR_M` record the *last known* state of a sole owner. Because the L1 performs a silent E→M upgrade without notifying the directory, the owner's L1 state is authoritative for E-versus-M. An owner that receives a forward while holding the line in M writes back before serving it; the directory must therefore handle a PUTM arriving while in DIR_FWD_WAIT.
2. The 3-bit state field has no spare code. A future directory state requires widening the entry.
3. An S-state eviction **must** be signalled. A silent drop leaves a stale sharer bit, and the block can then never complete DIR_INV_WAIT, because an INV sent to a tile that no longer holds the line has no defined response.
4. The "No orphan transient" invariant is what makes the liveness property in §5.2 meaningful, and it is what the predecessor's `PROXY_WAIT` dead state violated.

### C. Flit and Message Encodings

**Message type (4 bits):**

| Code | Message | Class | VC | Flits |
| --- | --- | --- | --- | --- |
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
| 1011 | DMA_READ | REQ | VC0 | 1 |
| 1100 | DMA_WRITE | REQ | VC0 | 9 |
| 1101 | DMA_ACK | RESP | VC2 | 1 |
| 1110 | PUTACK | RESP | VC2 | 1 |
| 1111 | Reserved | — | — | — |

**Control bits:**

| Bit | Meaning |
| --- | --- |
| 0 | Head flit |
| 1 | Tail flit |
| 2 | Write enable |
| 3 | Exclusive indication |

### D. Message × Virtual Channel Cross

| Class | VC | Messages | Count |
| --- | --- | --- | --- |
| REQ | VC0 | GETS, GETM, PUTS, PUTM, DMA_READ, DMA_WRITE | 6 |
| FWD | VC1 | FWD_GETS, FWD_GETM | 2 |
| RESP | VC2 | DATA, DATAFWD, INVACK, UNBLOCK, DMA_ACK, PUTACK | 6 |
| INV | VC3 | INV | 1 |
| **Total** | | | **15** |

**Coverage cross:** (9 L1 states × 15 messages) + (10 directory states × 15 messages) = 135 + 150 = **285 terms**.

### E. Formal Property List

**Safety (proved):** A1.1–A1.5, A2.1–A2.7, A3.1–A3.3, A4.1–A4.4, A6.1–A6.2, A7.1–A7.2, A8.1–A8.2, I1–I7.

**Bounded liveness (proved under the fairness premise):** every transient state is exited within T = 64 cycles; every request receives a response within T; every VC with pending traffic is served within 4 arbitration rounds.

---

## 12. Open Items Still Requiring Decision

| # | Item | Status | Owner / closure |
| --- | --- | --- | --- |
| 1 | Formal verification depth beyond T = 64 | To be decided after the first proof run | Week 12 |
| 2 | Coverage closure beyond the §5.3 numeric criteria | To be set after the environment runs | Week 12 |
| 3 | Related-work delta table against [15]–[18] | To be written | Week 15 |
| 4 | Router pipeline depth (3-stage vs 4-stage) | To be closed at RTL freeze; this paper specifies 4 | Week 4 |
| 5 | FPGA fit verification (2×2 LUT and BRAM budget) | To be confirmed by synthesis | Week 14 |
| 6 | IEEE conference venue | To be selected | Week 15 |
| 7 | Timeout detection mechanism for transients | To be specified; bounded by T | Week 10 |

---

**End of White Paper — Version 2.0**
