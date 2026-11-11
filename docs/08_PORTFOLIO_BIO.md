# 08 — Portfolio Bio & Interview Talking Points

> **Document Purpose**: Professional career narrative, technical resume synthesis, and defensible interview talking points covering all architectural, verification, and hardware design achievements.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — direct active voice, quantifiable metrics, concise technical terms, and zero unverifiable assertions.

## Project Headline
**Cache-Coherent Tiled Multicore on a 2D Mesh Network-on-Chip (SystemVerilog & Formal Verification)**

## Core Narrative
Designed and verified a parameterisable, scalable multicore architecture integrating private L1 caches, a distributed shared L2 cache, and a distributed directory MESI coherence protocol interconnected by a packet-switched 2D mesh on FPGA and simulation targets.

## High-Impact Interview Talking Points
1. **Coherence Protocol Nuance (MESI with Forward Releases & Transient Resolving)**:
   - Implemented a 9-state L1 controller and an 8-state directory controller featuring single-exit transient rules (`UNBLOCK`).
   - Integrated forward release paths (`FWD_GETS`/`FWD_GETM`) routing clean/dirty data (`DATAFWD`) through the home bank prior to requester delivery to preserve strict cache inclusion and ordering.
   - Handled complex race conditions (e.g., evict-during-forward, evict-during-invalidate) using defensive `INVACK`s and idempotent bit-clearing sharer tracking.
2. **Three-Layer Deadlock Freedom Guarantee**:
   - Eliminated protocol and network deadlocks without speculative buffering.
   - Proved mathematically and verified formally: Layer 1 (dimension-order XY routing + strict virtual channel preservation), Layer 2 (acyclic message-class hierarchy across 4 VCs: REQ → FWD → RESP / INV), Layer 3 (credit-based flow control bounding FIFO buffers to ≤ depth).
3. **Router Microarchitecture & Fair Arbitration**:
   - Designed a 4-stage pipelined 5-port wormhole router (RC/VA/SA/ST).
   - Solved request starvation via an age-escape counter mechanism (5-round threshold) combined with port-granular round-robin output arbitration, yielding a mathematically provable 13-round worst-case latency bound.
4. **Rigorous Verification Integration**:
   - Bound a 42-property SystemVerilog Assertion (SVA) suite non-invasively to RTL instances for formal safety analysis (SymbiYosys BMC, $K=64$).
   - Built a transaction-level shadow reference model in Python (`pyuvm`/`cocotb`) validating end-to-end data value integrity against the hardware test harness across a 238-term coverage cross.
5. **Hardware Implementation & FPGA Timing Closure**:
   - Targeted ZedBoard XC7Z020 FPGA at 100 MHz clock frequency.
   - Budgeted BRAM and LUT footprints to fit comfortably within 35% utilization, closing static timing with positive slack ($WNS \ge 0$).
6. **Aerospace & Industrial Documentation Rigor (~80% ASD-STE100 Compliance)**:
   - Authored an exhaustive 12-document architecture and verification suite strictly conforming to ~80% ASD-STE100 (Simplified Technical English) format.
   - Eliminates ambiguity in hardware requirements, formal lemma statements, problem log field chains, and executive project deliverables through active voice and standardized vocabulary.

