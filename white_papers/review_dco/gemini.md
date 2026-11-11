# FINAL PROPOSED WHITE PAPER AND ARCHITECTURAL JUSTIFICATION

**Title:** A Parameterised, Cache-Coherent 2D Mesh Multicore Architecture: Specification, Formal Verification Methodology, and FPGA Implementation

**Status:** Peer-Consensus Finalized Draft

**Target Configuration:** 4×4 Mesh (Simulation) / 2×2 Mesh (Xilinx Zynq-7000 XC7Z020 FPGA Synthesis)

---

## Abstract

This white paper provides the complete architectural specification, protocol design, verification methodology, and hardware implementation plan for a cache-coherent tiled multicore processor. The architecture integrates private L1 caches, distributed shared L2 banks with non-inclusive directory controllers, a wormhole-routed 2D mesh Network-on-Chip (NoC), and an optional coherent Direct Memory Access (DMA) device tile. The system implements a directory-based MESI coherence protocol. Verification is structured around a rigorous hybrid methodology combining constrained-random stimuli in `pyuvm`, a transaction-level reference model, bound-checked SystemVerilog Assertions (SVA), and formal property verification via SymbiYosys. Synthesis and implementation targets are bounded for the Xilinx Zynq-7000 XC7Z020 FPGA.

---

## 1. Introduction and Scope

### 1.1 Executive Summary

Tiled multicore architectures connected via packet-switched NoCs represent the standard paradigm for scalable multi-processor System-on-Chips (SoCs). Designing such a system requires balancing cache hierarchy latency, coherence protocol complexity, NoC deadlock avoidance, and physical FPGA resource constraints. This document reconciles architectural theory with RTL implementation reality, establishing a fully specified baseline.

### 1.2 Scope and Parameterisation

* **Topology:** Parameterised $N \times N$ 2D mesh (configured for $4 \times 4$ simulation and $2 \times 2$ hardware synthesis on the XC7Z020 FPGA).
* **Coherence:** Directory-based MESI protocol with full-map sharer tracking.
* **Memory Model:** Sequential consistency for data access; explicit fences are out of scope.
* **DMA Engine:** Symmetric non-CPU master tile integrated under the standard coherence protocol, configured as an optional/contingent extension.

### 1.3 Primary Contributions

1. **Parameterised Tiled RTL Architecture:** A modular core-tile and memory-tile design supporting scalable $N \times N$ integration.
2. **Deterministic Deadlock-Free NoC:** A 4-virtual-channel (VC) 2D mesh utilizing deterministic XY routing combined with protocol-class message separation.
3. **Integrated Verification Methodology:** A complete verification environment uniting a transaction-level reference model, 42 bound SVA assertions, and formal property checking.
4. **FPGA Resource and Timing Closure Baseline:** Bounded synthesis and implementation strategies targeting resource-constrained low-cost FPGA fabric.

### 1.4 Document Structure

* Section 2: Background and Related Architecture
* Section 3: Detailed Architectural Specification
* Section 4: Architectural Trade-Offs and Topology Justification
* Section 5: Verification Plan and Formal Methodology
* Section 6: FPGA Implementation and Synthesis Target
* Section 7: Project Schedule, Milestones, and Risk Mitigation
* Section 8: Predecessor Design Reconciliation
* Section 9: Future Scope
* Section 10: References
* Section 11: Appendices (FSM Transition Tables & Flit Encodings)

---

## 2. Background and Related Architecture

### 2.1 Tiled Architectures and Distributed Directories

Scalable multicore processors replace shared buses with direct interconnects. Distributed shared cache (DSC) architectures partition the physical address space across banking nodes, using directory controllers to maintain cache coherence without broadcast overhead.

### 2.2 Coherence Protocol Selection: MESI vs. Alternatives

A rigorous constraint-driven selection process evaluated MSI, MESI, MESIF, and MOESI:

* **MSI** lacks an Exclusive (E) state, forcing clean cache-line replacements to issue unnecessary write-backs.
* **MOESI/MESIF** introduce Owner or Forwarder states that reduce remote miss latency in shared interconnects but require complex hand-off state machines and additional protocol message types, violating our minimality constraint.
* **MESI** provides the optimal balance: it eliminates silent clean write-backs via the Exclusive state while maintaining a lean, well-understood 4-state machine that maps cleanly onto directory bit vectors.

### 2.3 Network-on-Chip (NoC) Interconnects

Packet-switched 2D meshes provide superior wire scaling, modular layout, and predictable electrical characteristics compared to crossbars or rings at moderate-to-large node counts ($N \ge 16$). Wormhole flow control minimizes buffer storage requirements within router nodes.

### 2.4 Verification Paradigms

Unit-level directed testing is insufficient for distributed coherence protocols due to asynchronous race conditions. Industrial best practices mandate a hybrid approach: directed tests for baseline functionality, constrained-random stimulus for corner-case discovery, and formal property checking for exhaustive invariant proof.

---

## 3. Detailed Architectural Specification

### 3.1 Tile Organisation

Each CPU tile is structurally identical and instantiated across the $N \times N$ grid. It contains:

1. **Core Interface / Testbench Stimulus Port:** Issues load/store requests.
2. **Private L1 Data Cache:** 4 sets $\times$ 4 ways $\times$ 64 bytes = 1 KB capacity, supporting MESI protocol.
3. **L2 Distributed Shared Cache Bank:** 8 sets $\times$ 4 ways $\times$ 64 bytes = 2 KB capacity per bank, coupled with a dedicated directory array.
4. **Network Interface Controller (NIC):** Translates core/cache requests into NoC flit packets and vice versa.
5. **5-Port 2D Mesh Router:** Implements wormhole routing, virtual channel allocation, and switch arbitration.
6. **Local Memory Tap (`mem_tap`):** Provides a 1-cycle behavioral memory slice (256 MB addressable space per tile).

*Note:* The optional DMA device tile is a structural variant that replaces the L2 bank and directory with an L1-lite streaming interface.

### 3.2 Cache Geometry and Directory Entry Format

* **L1 Data Cache:** 1 KB capacity, 4 sets, 4 ways, 64-byte block size. Replacement policy: Tree-based Pseudo-LRU (3 bits per set).
* **L2 Cache Bank:** 2 KB capacity, 8 sets, 4 ways, 64-byte block size. Replacement policy: Tree-based Pseudo-LRU.
* **Directory Entry Format (32-bit aligned for BRAM/SRAM efficiency):**
* **State Field (3 bits):** Encodes stable states (`DIR_I`, `DIR_S`, `DIR_E`, `DIR_M`) and primary transients (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`, `DIR_EVICT`).
* **Owner Field (4 bits):** Identifies the unique owner tile ID when in state `DIR_M` (parameterised for up to 16 tiles).
* **Sharers Bit Vector (16 bits):** Full-map tracking for up to 16 tiles.
* **Valid Bit (1 bit):** Indicates entry allocation.



### 3.3 Protocol Message Set and Transient States

The coherence protocol operates over a minimal set of 14 message types:

1. `GETS`: Read request from L1.
2. `GETM`: Read-exclusive/write request from L1.
3. `PUTS`: Clean line eviction from L1.
4. `PUTM`: Dirty line write-back from L1.
5. `INV`: Invalidation request from directory to sharers.
6. `INVACK`: Invalidation acknowledgment from sharer to directory.
7. `DATA`: Data response from directory/memory to L1.
8. `DATAFWD`: Forwarded data from current owner to requester.
9. `FWD_GETS`: Forwarded read request to current owner.
10. `FWD_GETM`: Forwarded write request to current owner.
11. `PUTACK`: Eviction acknowledgment from directory to L1.
12. `DMA_READ`: Stream read request from DMA device.
13. `DMA_WRITE`: Stream write request from DMA device.
14. `DMA_ACK`: Completion acknowledgment for DMA operations.

*L1 Transient States:* `IS_D` (Invalid-to-Shared, waiting for data), `IM_D` (Invalid-to-Modified, waiting for data), `SM_D` (Shared-to-Modified, waiting for upgrade/data), `EI_A` (Exclusive-to-Invalid, waiting for eviction ack), `MI_A` (Modified-to-Invalid, waiting for write-back ack).

*Directory Transient States:* `DIR_MEM_WAIT` (waiting for memory fetch), `DIR_FWD_WAIT` (waiting for owner forward response), `DIR_INV_WAIT` (waiting for invalidation acknowledgments), `DIR_EVICT` (handling line replacement races).

### 3.4 NoC Router Architecture and Virtual Channels

* **Topology:** 2D Mesh with deterministic XY routing (packets traverse X-dimension first, then Y-dimension).
* **Switching & Flow Control:** Wormhole routing with credit-based flow control (buffer depth: 4 flits per VC, 20 VCs per router).
* **Virtual Channels & Deadlock Avoidance:** 4 virtual channels assigned by message class to guarantee strict acyclic channel dependency:
* **VC0 (Requests):** `GETS`, `GETM`, `PUTS`, `PUTM`, `DMA_READ`, `DMA_WRITE`.
* **VC1 (Forwards):** `FWD_GETS`, `FWD_GETM`, `INV`.
* **VC2 (Responses):** `DATA`, `DATAFWD`, `INVACK`, `PUTACK`, `DMA_ACK`.
* **VC3 (High-Priority Invalidation/Control):** Reserved for urgent invalidation traffic.


* **Arbitration Policy:** Fixed priority across VCs ($\text{VC2} > \text{VC3} > \text{VC1} > \text{VC0}$) to prevent response and invalidation starvation, combined with round-robin arbitration across physical input ports.

### 3.5 Packet and Flit Format

Packets are composed of variable-length flits (1 header flit + $N$ body flits). All flits are 64 bits wide plus sideband control signals.

* **Header Flit (64 bits):**
* `[63:60]` Message Type (4 bits, encoding up to 16 opcodes).
* `[59:52]` Destination Tile ID (8 bits).
* `[51:44]` Source Tile ID (8 bits).
* `[43:42]` Virtual Channel ID (2 bits).
* `[41:38]` Reserved / Control flags (4 bits).
* `[37:32]` Packet Length in Flits (6 bits, encoding payload size up to 63 flits).
* `[31:0]` Physical Address (32 bits).


* **Body Flit (64 bits):** Pure 64-bit data payload (8 bytes per flit). Standard cache-line transfer requires 1 header + 8 body flits = 9 flits total.

### 3.6 Address Decoding and Bank Interleaving

Physical addresses (32 bits) are mapped across distributed L2 banks using range-based interleaving:

* **For $4 \times 4$ Configuration:**
* Byte Offset: `[5:0]` (6 bits for 64-byte line).
* L1 Set Index: `[7:6]` (2 bits for 4 L1 sets).
* L2 Set Index: `[10:8]` (3 bits for 8 L2 sets, disjoint from L1 set index).
* Home Tile (Bank) ID: `[14:11]` (4 bits, selecting one of 16 tile banks).
* Tag Field: `[31:15]` (17 bits).



### 3.7 DMA Subsystem Integration

The DMA engine operates as a symmetric non-CPU master tile. It interfaces directly with the NoC via an L1-lite controller, issuing standard coherence requests (`GETS` / `GETM`) to allocate and manipulate lines in the global shared address space without requiring specialized directory states.

---

## 4. Architectural Trade-Offs and Topology Justification

### 4.1 Topology Comparison Matrix

| Parameter | 2D Mesh | Torus | Ring | Crossbar | Bus | Fat-Tree |
| --- | --- | --- | --- | --- | --- | --- |
| **Wiring Complexity** | Low ($O(N)$) | Medium | Low ($O(N)$) | High ($O(N^2)$) | Low ($O(1)$) | Medium ($O(N \log N)$) |
| **Average Hop Count** | Medium ($\frac{2\sqrt{N}}{3}$) | Low ($\frac{\sqrt{N}}{2}$) | High ($\frac{N}{4}$) | Constant (1) | Constant (1) | Low ($\log N$) |
| **Max Ports/Router** | 5 | 5 | 3 | $N+1$ | $N+1$ | 4 |
| **Deadlock Risk** | Low (XY Routing) | High (Wraparound) | High (Cyclic) | None | None | Low |
| **Extensibility** | Excellent | Good | Poor | Poor | Poor | Good |

### 4.2 Why 2D Mesh Wins for $N \le 16$

The 2D mesh provides an optimal trade-off between wire routing congestion and hop latency. Unlike crossbars, its area does not scale quadratically. Unlike tori, it avoids complex wraparound wires that introduce critical path timing bottlenecks on FPGA interconnects.

### 4.3 Why Ring and Bus Were Rejected

* **Ring Interconnects:** Rejected due to cyclic channel dependencies that heighten deadlock vulnerability and poor diameter scaling ($O(N)$ hop count).
* **Shared Bus:** Rejected due to severe bandwidth saturation at $N \ge 4$ and electrical capacitive loading limitations.

### 4.4 Cache Parameterisation Justification

* **4-Way Associativity:** Provides an optimal balance between hit rate and multiplexer/comparator complexity in FPGA LUT logic compared to direct-mapped or 8-way structures.
* **Tree-PLRU Replacement:** Reduces LRU state storage to 3 bits per set (a 40% savings over True LRU) with a negligible hit-rate penalty (<0.5%).

### 4.5 Deadlock Freedom Proof Framework

Deadlock freedom is established via a three-layer induction:

1. **Routing Level:** Deterministic XY routing on a 2D mesh produces an acyclic channel dependency graph.
2. **Protocol Level:** Strict virtual channel message-class separation ($\text{REQ} \to \text{FWD} \to \text{RESP} \to \text{INV}$) prevents protocol-level cyclic wait conditions.
3. **Resource Level:** Credit-based flow control bounds buffer occupancy, preventing physical queue exhaustion.

---

## 5. Verification Plan and Formal Methodology

### 5.1 Directed Test Suite

The test plan comprises 15 core scenarios executed across simulation and formal engines:

1. Single-tile read/write hit and miss.
2. Multi-tile shared read access (MESI 'S' state verification).
3. Exclusive cache line acquisition and silent write.
4. Read-exclusive upgrade race (`IS_D` and `SM_D` transitions).
5. L2 eviction of clean lines (PUTS flow).
6. L2 eviction of dirty lines (PUTM write-back flow).
7. Remote invalidation storms (INV / INVACK completion).
8. Forwarded request handling (`DIR_FWD_WAIT` convergence).
9. Concurrent multi-tile requests to the same cache line.
10. L1/L2 buffer full and backpressure recovery.
11. NoC multi-hop routing stress test under uniform random traffic.
12. Corner-case deadlock injection test.
13. Mesh NoC bandwidth saturation test.
14. Coherent DMA stream transfer (Read/Write/Ack validation).
15. Transient state timeout recovery validation.

### 5.2 Formal Verification Properties (SymbiYosys)

Formal verification targets safety and bounded liveness invariants on a 2×2 tile baseline configuration using SymbiYosys (`sby`):

* **Single-Writer / Multiple-Reader Invariant:** $\forall \text{addr}, \sum \text{Sharers} > 0 \implies \text{Owner} = \emptyset \land \text{State} \neq M$.
* **Data Consistency:** If a cache holds a line in Modified state, memory and other caches hold stale data; the L2 bank or owner holds the authoritative value.
* **No Orphan Transients:** Every directory and cache transient state (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`) guarantees exit to a stable state within bounded time ($K \le 40$ cycles).
* **No Message Loss:** All injected NoC flits are delivered exactly once to their intended destination without corruption.

### 5.3 Simulation Environment (`pyuvm` & SVA)

* **Reference Model:** A transaction-level golden reference model implemented in Python (`pyuvm`), maintaining shadow state for all L1s, L2 banks, directories, and memory slices.
* **Assertions:** 42 SystemVerilog Assertions (SVA) across 8 categories (MESI invariants, directory invariants, message protocol, flow control, bounded liveness, data integrity, FSM legality, address decoding), bound non-invasively to the RTL via `bind` statements.
* **Coverage Targets:** 100% functional coverage closure on state-message cross-products for the 2-tile baseline, with structural branch/line coverage $\ge 98\%$.

### 5.4 Continuous Integration Pipeline

Automated regression testing is executed via GitHub Actions on every pull request, invoking Verilator for fast transaction-level simulation, Vivado Xsim for SVA assertion checks, and SymbiYosys for formal property proofs.

---

## 6. FPGA Implementation and Synthesis Target

### 6.1 FPGA Resource Budget (Xilinx Zynq-7000 XC7Z020)

* **Device Limits:** 53,200 LUTs, 106,400 Flip-Flops, 140 36Kb BRAM primitives.
* **Target Configuration:** $2 \times 2$ Mesh (4 tiles total) for hardware synthesis.
* **Resource Allocation Estimate:**
* Logic (LUTs): $\approx 18,500$ ($35\%$ utilization).
* Registers (FFs): $\approx 22,000$ ($21\%$ utilization).
* Block RAM (BRAM36): $\approx 52$ primitives ($37\%$ utilization, utilizing LUTRAM for selected L1 tag/data arrays to respect BRAM bounds).



### 6.2 Physical Verification and Toolchains

* **Synthesis & Implementation:** Xilinx Vivado ML Standard (v2023.2).
* **ASIC Flow Equivalency (Open-Source):** Yosys for synthesis, OpenLane / OpenSTA for static timing analysis and physical verification (Magic/Netgen for DRC/LVS).
* **Constraint Management:** Fully constrained via explicit XDC files enforcing clock definitions ($10\,\text{ns}$ period / $100\,\text{MHz}$ target), input/output delays, and multi-cycle false paths on reset synchronisers.

### 6.3 Simulation Toolchain

* **Verilator:** Used for high-performance cycle-approximate functional regression.
* **Vivado Xsim / VCS:** Used for gate-level and SVA assertion verification.

### 6.4 Timing Closure Strategy

Target operating frequency: $100\,\text{MHz}$ ($10\,\text{ns}$ clock period). Critical paths are mitigated through pipelining across three router stages and registering L2 directory tag-compare logic.

---

## 7. Project Schedule, Milestones, and Risk Mitigation

### 7.1 Sixteen-Week (Four-Month) Schedule

* **Month 1 (Weeks 1–4):** RTL implementation of Core, L1/L2 caches, Directory Controller, and 5-port Router.
* **Month 2 (Weeks 5–8):** Integration of NoC mesh, NIC, memory tap, and establishment of `pyuvm` verification environment.
* **Month 3 (Weeks 9–12):** Formal verification property campaigns, directed test execution, and FPGA $2 \times 2$ synthesis/timing closure.
* **Month 4 (Weeks 13–16):** Full regression closure, hardware debugging on Zynq-7000 board, and white paper / paper freeze.

### 7.2 Key Milestones

1. Week 4: L1/L2 and Router unit tests passing.
2. Week 8: $4 \times 4$ NoC traffic simulation and reference model scoreboard operational.
3. Week 11: SymbiYosys formal safety properties passing on 2-tile configuration.
4. Week 14: FPGA bitstream generation and hardware validation on XC7Z020.
5. Week 16: Final documentation freeze and release.

### 7.3 Risk Management Matrix

| Risk Description | Probability | Impact | Mitigation Strategy |
| --- | --- | --- | --- |
| **Formal proofs do not converge** | Medium | High | Reduce state space by abstracting data values, narrowing assertion scope, or bounding model depth. |
| **FPGA BRAM budget exceeded** | Medium | Medium | Map L1 tags and NoC FIFO buffers to distributed LUTRAM rather than BRAM primitives. |
| **DMA integration delay** | High | Low | Isolate DMA tile as an optional stretch goal; drop to single-channel operation or remove if schedule slips. |
| **Timing closure failure at 100MHz** | Low | High | Insert pipeline registers in router crossbar arbitration and L2 tag lookup paths. |

---

## 8. Predecessor Design Reconciliation

This architecture addresses and resolves several structural defects identified in the legacy predecessor design:

1. **Unbounded Transient Hangs:** Resolved by adding explicit timeout detection mechanisms and orphan transient assertion checks.
2. **Directory State Non-Determinism:** Resolved by splitting ambiguous transient states (`DIR_FWD_WAIT_S` vs. `DIR_FWD_WAIT_M`).
3. **Unconstrained Physical Synthesis:** Replaced unversioned tool scripts with fully version-pinned toolchains and explicit XDC constraints.
4. **Missing Eviction Acknowledgments:** Introduced the explicit `PUTACK` protocol message to safely complete L1 eviction sequences.

---

## 9. Future Scope

* **Hierarchical Directories:** Scale beyond 16 tiles using directory caching or clustered directory trees.
* **Advanced Coherence:** Exploration of MOESI extensions for dirty sharing.
* **Dynamic Voltage and Frequency Scaling (DVFS):** Per-tile power gating and voltage regulation for energy-efficient IoT deployment.
* **Scatter-Gather DMA:** Expanded multi-channel DMA engine supporting non-contiguous memory transfers.

---

## 10. References

1. C. J. Newcomer et al., *A Primer on Memory Consistency and Cache Coherence*, 2nd ed., Morgan & Claypool, 2020.
2. W. J. Dally and B. Towles, *Principles and Practices of Interconnection Networks*, Morgan Kaufmann, 2004.
3. M. Taylor et al., "Evaluation of the OpenPiton Manycore Architecture," *IEEE Micro*, 2016.
4. A. Biere et al., "Symbolic Model Checking without BDDs," *TACAS*, 1999.
5. Xilinx Inc., *Zynq-7000 SoC Data Sheet: Overview*, DS190, 2018.

---

## 11. Appendices

### Appendix A: L1 Controller FSM Transient State Transitions

* `IS_D + DATA (exclusive)` $\to$ `E` (Install line, complete load).
* `IM_D + DATA (exclusive)` $\to$ `M` (Install line, complete store).
* `SM_D + DATA (exclusive)` $\to$ `M` (Upgrade line, complete store).
* `EI_A + PUTACK` $\to$ `I` (Release entry).
* `MI_A + PUTACK` $\to$ `I` (Complete write-back release).

### Appendix B: Directory Controller State Transition Rules

* `DIR_I + GETS` $\to$ `DIR_S` (Fetch from memory, send `DATA`, set sharer bit).
* `DIR_I + GETM` $\to$ `DIR_M` (Fetch from memory, send `DATA`, set owner ID).
* `DIR_S + GETM` $\to$ `DIR_INV_WAIT` (Send `INV` to all sharers, wait for `INVACK`).
* `DIR_INV_WAIT + INVACK (last)` $\to$ `DIR_M` (Send `DATA` to requester, set owner ID).
* `DIR_M + FWD_GETS` $\to$ `DIR_FWD_WAIT_S` (Forward request to owner, wait for `DATAFWD`).
* `DIR_FWD_WAIT_S + DATAFWD` $\to$ `DIR_S` (Update memory/cache, send `DATA` to requester, add sharer).
* `DIR_M + PUTM` $\to$ `DIR_MEM_WAIT` (Receive write-back data, write to memory, send `PUTACK`, clear owner, transition to `DIR_I`).

### Appendix C: Flit Message Type Encodings (4-Bit Field)

* `0000`: `GETS`
* `0001`: `GETM`
* `0010`: `PUTS`
* `0011`: `PUTM`
* `0100`: `INV`
* `0101`: `INVACK`
* `0110`: `DATA`
* `0111`: `DATAFWD`
* `1000`: `FWD_GETS`
* `1001`: `FWD_GETM`
* `1010`: `PUTACK`
* `1011`: `DMA_READ` *(Reserved — pending DMA integration finalization)*
* `1100`: `DMA_WRITE` *(Reserved — pending DMA integration finalization)*
* `1101`: `DMA_ACK` *(Reserved — pending DMA integration finalization)*
* `1110` – `1111`: Reserved for future extensions