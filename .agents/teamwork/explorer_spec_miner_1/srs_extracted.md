[Title] System Requirements Specification (SRS)

[Normal] Project title: Cache-Coherent Tiled Mesh Multicore

[Normal] Group:

[Normal] Members: Durgesh Kolhe , Sai Charan , Additya , Joshna

[Normal] Group Mentor: Mr. Hemat

[Normal] Version / Date: v0.2 / 04-11-2026

TABLE START
| Version | Date | Author | Description of change |
| v0.1 | 04-11-2026 | Group | Initial draft |
| v0.2 | 04-11-2026 | Group | Applied SRS_REVIEW.md (6 blockers, 6 majors, 6 minors): PUTS/PUTM direction; phantom assertion ID removed from FR-02; AC-03 VC index order; area targets from WP 6.1; 2x2 signal list (no 2x2 DMA write signal); traceability column made resolvable; FR-09-FR-14 added; message table, coverage goals, test plans and exit criteria aligned to the WP; WP 13 ledger relabelled AD with AE/AF added |
TABLE END

[Heading 1] 1. Introduction

[Heading 2] 1.1 Purpose

[Normal] This document specifies what the cache-coherent tiled mesh multicore shall do - cache coherence, deterministic routing, credit-based flow control, arbitration, eviction and DMA - and how those behaviours will be proven. It is for the group, the Group Mentor and the RTL and verification team preparing the Month 3 results.

[Heading 2] 1.2 Scope

[Normal] The design under test (DUT) shall provide a 2D mesh of tiles with directory-based MESI coherence, four virtual channels per port (each with a 4-flit FIFO), private L1 caches, a distributed L2 and a directory; XY deterministic routing; credit-based flow control; a fairness escape with a derived bound; eviction with PUTS/PUTM/PUTACK; and a DMA write path (4x4 simulation scope only). Out of scope: snooping protocols, MOESI/MESIF, adaptive routing, more than sixteen tiles, host software above the tile level. In scope for verification: functional coherence, liveness and fairness, formal safety and liveness, and FPGA validation.

[Heading 2] 1.3 Definitions and Acronyms

TABLE START
| Term | Meaning |
| MESI | Modified, Exclusive, Shared, Invalid |
| VC | Virtual channel - 4 per port, indexed at the source and never altered by a router (VC0 REQ, VC1 FWD, VC2 RESP, VC3 INV) |
| PLRU | Tree-PLRU replacement, 3 b/set at both L1 and L2 (WP 4.4) |
| GETS | L1 -> directory request for a shared copy (VC0, 1 flit) |
| GETM | L1 -> directory request for an exclusive copy (VC0, 1 flit) |
| PUTS | L1 -> directory release notification (clean line; no data) |
| PUTM | L1 -> directory release notification (dirty line; carries the data) |
| PUTACK | Directory -> L1 acknowledgement of a release (exits EI_A / MI_A) |
| UNBLOCK | L1 -> directory release event that selects the directory's successor state |
| INV | Directory -> L1 invalidation / recall (VC3, 1 flit) |
| INVACK | L1 -> directory invalidation acknowledged (VC2, 1 flit) |
| DATA | Directory -> L1 data delivery (VC2, 9 flits; exclusive bit in the control flit) |
| DATAFWD | Owner -> directory forwarded data (VC2, 9 flits; dirty indication in header bit [39]) |
| L1 | Private per-tile cache |
| L2 | Distributed tile-local bank |
| DIR_* | Directory FSM state (DIR_I / DIR_S / DIR_E / DIR_M and the transients DIR_MEM_WAIT / DIR_FWD_WAIT / DIR_INV_WAIT / DIR_EVICT) |
| T | Bounded liveness parameter: 64 cycles at 2x2 (formal), 150 cycles at 4x4 (simulation) |
TABLE END

[Heading 2] 1.4 References

TABLE START
| Ref | Title / source | Used for |
| [1] | Final White Paper v3.0 (ruled, gate 130/130) | Specification under test |
| [2] | Approved LLD (PDF) | Interface and geometry |
| [3] | SPEC_SHEET.md | Derivation of requirements |
| [4] | RULINGS_B1_B2_B4.md / WP 13 adjudication ledger (rows AD, AE, AF) | Ruling provenance |
| [5] | SRS Template Student Guide | Section structure |
| [6] | SRS_REVIEW.md (04-11-2026) | v0.2 corrections (18 findings) |
TABLE END

[Heading 1] 2. Overall Description

[Heading 2] 2.1 System Context

[Normal] The DUT is one block; everything it connects to outside it is listed below.

TABLE START
| External | Connection to the DUT |
| Memory (behavioural tap) | Home-bank fills and dirty write-backs; 1-cycle behavioural latency, 64 B lines (WP 3.9) |
| On-board stimulus source (FPGA 2x2) | JTAG bridge drives the directed tests; ILA/VIO debug is future scope (WP 6.1) |
| Simulation testbench (4x4) | pyuvm drivers/monitors, transaction-level reference model, scoreboard (WP 5.4) |
| Neighbouring routers (N/S/E/W) | 5-port wormhole links with per-VC credit flow control (WP 3.5) |
| Tile-internal blocks (L1, L2, directory <-> NIC) | 512-bit intra-tile path, one whole cache line per transfer (WP 3.1) |
TABLE END

[Normal] Warning - not specified in WP: the WP's rendered diagram set contains FSM and sequence diagrams, not a system-context figure; this table is the context view (v0.2).

[Heading 2] 2.2 Design Platform and Tools

TABLE START
| Item | Value |
| Target | FPGA - 2x2 committed build (4 tile positions); 4x4 for simulation |
| Design language | SystemVerilog |
| Verification methodology | Directed + formal + constrained-random |
| Tool flow | Simulator (Verilator, Vivado xsim), lint/CDC, synthesis (Vivado, Yosys), STA, formal (SymbiYosys) |
TABLE END

[Heading 2] 2.3 Assumptions and Constraints

TABLE START
| ID | Assumption or constraint |
| AC-01 | 2D mesh topology; one router module per tile; unused ports tied off. |
| AC-02 | Credit-based flow control, per-VC FIFO depth 4. |
| AC-03 | Four virtual channels per port, indexed at the source and never altered by a router: VC0 = REQ (GETS, GETM, PUTS, PUTM, DMA_WRITE*), VC1 = FWD (FWD_GETS, FWD_GETM), VC2 = RESP (DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, DMA_ACK*), VC3 = INV (INV). Arbitration priority across classes is fixed: RESP > INV > FWD > REQ, with the age escape. |
| AC-04 | 64 B lines; 512-bit intra-tile transfers; 9 flits per line on the NoC. |
| AC-05 | Bounded liveness T = 64 (2x2 formal) / 150 (4x4 simulation); fairness bound 5 + 3 + 5 = 13 rounds. |
TABLE END

[Heading 1] 3. Functional Requirements

TABLE START
| ID | Requirement | Priority | Verified by |
| FR-01 | The system shall maintain directory-based MESI coherence across tiles. | Must | A1.1-A1.5, A2.1-A2.7 / TC-01 |
| FR-02 | The system shall deliver each message by XY deterministic routing (X then Y). | Must | A8.x / I1 / TC-02 |
| FR-03 | The system shall use credit-based flow control with per-VC FIFOs of depth 4. | Must | I3, A4.x / TC-03 |
| FR-04 | The system shall arbitrate VCs by class priority (RESP > INV > FWD > REQ) with a per-(port, VC) age escape at threshold 5 and a port-granular output round-robin, serving every VC within 5 + 3 + 5 = 13 rounds. | Must | A5.x, I2 / TC-04 |
| FR-05 | The system shall evict with PUTS/PUTM + PUTACK and shall never evict silently; a conflict eviction shall release the victim before the miss request, both on VC0. | Must | A1.1, A1.2, A3.x / TC-05 |
| FR-06 | The system shall implement single-exit directory FSMs whose only exit is UNBLOCK. | Must | A7.x, A2.7 / TC-06 |
| FR-07 | The system shall support the DMA write path (GETM-mapped) in the 4x4 simulation scope only; no 2x2 DMA deliverable exists and pending_op = DMA shall be unreachable in the 2x2 build. | Should | A8.4 / TC-07 (4x4 only) |
| FR-08 | The system shall move a whole cache line in one 512-bit intra-tile transfer. | Must | A6.x / TC-08 |
| FR-09 | On FWD_GETS the owner shall downgrade E/M -> S and send DATAFWD; on FWD_GETM it shall downgrade E/M -> I and send DATAFWD, and shall not send PUTS/PUTM (rule 8). | Must | A1.3, A2.2, A2.6 / TC-09 |
| FR-10 | The directory shall set the DATA exclusive bit to 1 only when the requester becomes the sole holder (a DIR_I grant or any GETM grant), and to 0 on every GETS grant including a forward (rule 9). | Must | A1.2, A1.3 / TC-10 |
| FR-11 | The L2 per-line word shall be {valid, tag, dirty} (23 b at 2x2, 21 b at 4x4); the dirty bit shall be excluded from tag comparison and way select. | Must | A6.x / TC-11 |
| FR-12 | A DATAFWD packet shall carry the dirty indication in header bit [39], set iff the owner held the line in M. | Must | A6.x / TC-12 |
| FR-13 | A DIR_EVICT whose victim is DIR_I with a dirty bank line shall take the WRITE_BACK sub-state; the dirty line shall never be silently dropped (N4). | Must | A6.x / TC-13 |
| FR-14 | An L1 with an outstanding miss shall continue to accept and service INV/DATA/INVACK/FWD traffic for other lines immediately, on a path independent of the miss path (Premise R). | Must | A3.x, A7.x / TC-14 |
TABLE END

[Heading 1] 4. Performance Requirements

TABLE START
| ID | Parameter | Target | Minimum | Conditions | Verified by |
| PERF-01 | Clock frequency | TBD | TBD | FPGA / corner | STA |
| PERF-02 | Throughput | TBD | TBD | 4x4 simulation | Throughput test |
| PERF-03 | Hop latency | 4 cycles (4-stage router, RC/VA/SA/ST) | - | WP 3.5 | SVA / timing test |
| PERF-04 | Line transfer | 9 flits per 64 B line (512-bit line) | - | WP 3.8 | A6.x / TC-08 |
| PERF-05 | Liveness bound T | 64 cycles (2x2 formal); 150 cycles (4x4 simulation) | - | WP 5.3 | Formal (bounded liveness) |
| PERF-06 | Fairness service bound | 13 arbitration rounds (5 + 3 + 5); 11 at a corner tile | - | WP 3.5 | A5.x / Premise F |
TABLE END

[Heading 1] 5. Power Requirements

[Normal] Out of scope for this milestone: the WP contains no power data (warning - not specified in WP). This section stays open rather than carrying invented numbers; a power budget must be added to the WP section 12 open-items list before any PPA sign-off.

TABLE START
| ID | Parameter | Target | Maximum | Conditions | Verified by |
| PWR-01 | Dynamic power | Out of scope (this milestone) | - | FPGA bench | Measure - pending WP power budget |
| PWR-02 | Leakage power | Out of scope (this milestone) | - | FPGA bench | Measure - pending WP power budget |
| PWR-03 | Total power | Out of scope (this milestone) | - | FPGA bench | Measure - pending WP power budget |
TABLE END

[Heading 1] 6. Area Requirements

TABLE START
| ID | Parameter | Target | Maximum | Conditions | Verified by |
| AREA-01 | FPGA LUT utilization (2x2) | <= 20,000 (38 % of 53,200); estimate ~13,000-19,000 | <= 40,000 (75 %) | 2x2 build | Synthesis |
| AREA-02 | FPGA BRAM36 utilization (2x2) | <= 48; estimate 28 (favourable mapping) | <= 80 | 2x2 build | Synthesis |
| AREA-03 | FPGA DSP utilization | 0 | 0 | 2x2 build - no multipliers inferred | Synthesis |
TABLE END

[Heading 1] 7. Interface Requirements

[Heading 2] 7.1 Interface Summary

[Normal] Message set - 12 core messages + 2 gated DMA messages (WP 3.3):

TABLE START
| Message | Direction | Class | VC | Flits |
| GETS | L1 -> dir | REQ | VC0 | 1 |
| GETM | L1 -> dir | REQ | VC0 | 1 |
| PUTS | L1 -> dir | REQ | VC0 | 1 |
| PUTM | L1 -> dir | REQ | VC0 | 9 |
| UNBLOCK | L1 -> dir | RESP | VC2 | 1 |
| INV | dir -> L1 | INV | VC3 | 1 |
| INVACK | L1 -> dir | RESP | VC2 | 1 |
| DATA | dir -> L1 | RESP | VC2 | 9 |
| FWD_GETS | dir -> owner | FWD | VC1 | 1 |
| FWD_GETM | dir -> owner | FWD | VC1 | 1 |
| DATAFWD | owner -> dir | RESP | VC2 | 9 |
| PUTACK | dir -> L1 | RESP | VC2 | 1 |
| DMA_WRITE (gated) | DMA -> dir | REQ | VC0 | 9 |
| DMA_ACK (gated) | dir -> DMA | RESP | VC2 | 1 |
TABLE END

[Normal] DMA_READ is not defined: a DMA read is a GETS issued by the DMA tile's L1-lite. Codes 1110/1111 are Reserved and not decoded by any RTL. The two DMA messages are gated: 4x4 simulation only, Week-8 gate (ruling B4).

[Heading 2] 7.2 Signal List

TABLE START
| Signal | Dir | Width | Clock domain | Description |
| clk | in | 1 | sync | Main system clock |
| reset | in | 1 | sync | Global reset (assertion/deassertion discipline is warning - not specified in WP - see SPEC_SHEET section 15) |
| credit_in | in | 4 | clk | Per-VC credit from the downstream port (4 VCs) |
| credit_out | out | 4 | clk | Per-VC credit to the upstream port |
| port_in_data / port_in_valid / port_in_ready | in | flit (header+body) | clk | Inbound wormhole stream from a neighbouring port (4 per tile) |
| port_out_data / port_out_valid / port_out_ready | out | flit | clk | Outbound wormhole stream to a neighbouring port (4 per tile) |
| local_inject_* / local_eject_* | in/out | flit | clk | Local tile <-> router path (L1/L2/directory <-> NIC) |
| dma_* | - | - | - | Not present in the 2x2 build (ruling B4). In the 4x4 track: register-mapped, two channels - DMA_SRC_LO / DMA_DST_LO / DMA_LEN / DMA_CTRL / DMA_STATUS / DMA_COUNT. |
TABLE END

[Heading 2] 7.3 Clocks and Resets

TABLE START
| Name | Frequency | Type | Notes |
| clk | TBD (100 MHz / 10 ns on-board oscillator, WP 6.1) | sync / async reset | Main system clock; reset discipline warning - not specified in WP |
TABLE END

[Heading 2] 7.4 Timing and Handshake Rules

[Normal] Handshake protocol, latency and setup/hold expectations at the boundary; timing diagram to be added. Credit-return latency in cycles is warning - not specified in WP (SPEC_SHEET section 15).

[Heading 2] 7.5 Register Map (if software accesses the block)

[Normal] Not applicable at tile level; the DMA register map (SRC/DST/LEN/CTRL/STATUS/COUNT) is deferred to the Week-8 gate and exists only in the 4x4 track.

[Heading 1] 8. Verification Requirements

[Heading 2] 8.1 Verification Strategy

[Normal] Directed + formal + constrained-random. Baseline proof configuration (proposed, per WP section 12 item 1 - to be confirmed at the first proof run): BMC K = 64, k-induction k = 16, bounded liveness T = 64 cycles (2x2 formal) / 150 cycles (4x4 simulation).

[Heading 2] 8.2 Testbench Environment

TABLE START
| Component | Description | Language / methodology |
| Stimulus generator / driver | Directed tests 1-17, plus 18-22 conditional on the DMA gate (WP 5.1); constrained-random sequences | SV / pyuvm |
| Monitor | Protocol monitor | SV |
| Scoreboard / reference model | Transaction-level reference model (WP 5.4) | Python / SV |
| Assertions / checkers | 42 bound SVA + network invariants I1-I7 | SVA |
| Coverage collector | pyuvm coverage bins (bin list = WP section 12 item 2) | SV |
TABLE END

[Heading 2] 8.3 Coverage Goals

TABLE START
| Coverage type | Target | Notes / exclusions |
| Legal functional bins | 100 % | WP 5.4 |
| FSM states and transitions (L1 and directory) | 100 % | WP 5.4 |
| Assertions | 100 % pass, zero waivers | 42 bound SVA + I1-I7 |
| Cover properties | 100 % hit | WP 5.4 |
| Open item | - | The pyuvm bin list behind these numeric criteria is WP section 12 item 2 - not yet specified; do not invent bins before the environment runs (Week 12). |
TABLE END

[Heading 2] 8.4 Test Plan

TABLE START
| Test ID | Requirement ID | Scenario (WP 5.1 test #) | Type | Pass criteria | Status |
| TC-01 | FR-01 | #1, #3, #5, #7, #14 - misses, silent upgrade, upgrade with invalidation, concurrent requests | Directed | Final state and data values correct in every participating L1, L2 bank, directory and memory tap | Planned |
| TC-02 | FR-02 | #2, #4 - cross-tile GETS/GETM round trips (XY path) | Directed | As TC-01; every message follows the XY path | Planned |
| TC-03 | FR-03 | #15 - mesh saturation, credit stalls | Directed | No send at zero credit; occupancy never exceeds depth 4 | Planned |
| TC-04 | FR-04 | #13, #15 - back-to-back requests, saturation | Directed | Every VC served within 13 rounds (5 + 3 + 5); no starvation | Planned |
| TC-05 | FR-05 | #9, #10 - clean (PUTS) and dirty (PUTM) eviction | Directed | No silent eviction; PUTACK exits MI_A/EI_A; conflict victim released before the miss on VC0 | Planned |
| TC-06 | FR-06 | #17 - timeout and recovery | Directed | No orphan transient; UNBLOCK is the only exit of DIR_MEM_WAIT/FWD_WAIT/INV_WAIT | Planned |
| TC-07 | FR-07 | #18-#22 - DMA read/write, contention, back-to-back (conditional) | Directed (4x4, Week-8 gate) | DMA_ACK on completion; pending_op = DMA unreachable in the 2x2 build | Planned (4x4 only) |
| TC-08 | FR-08 | #1, #9, #10 - line fill and write-back | Directed | The 512-bit intra-tile transfer equals the 64 B line | Planned |
| TC-09 | FR-09 | #6, #8 - sharing and forward from a remote owner | Directed | Owner downgrades and sends DATAFWD, no PUTS/PUTM on the forward path | Planned |
| TC-10 | FR-10 | #3, #4, #6, #8 - exclusive bit on every grant | Directed | excl = 1 only on a DIR_I grant or any GETM grant; excl = 0 on every GETS grant | Planned |
| TC-11 | FR-11 | #11, #12 - L2 eviction of a shared/owned victim | Directed | Per-line word {valid, tag, dirty} matches the reference model (23 b at 2x2) | Planned |
| TC-12 | FR-12 | #8 - forward with a dirty owner | Directed | Header bit [39] set iff the owner held the line in M; bank dirty bit set | Planned |
| TC-13 | FR-13 | #11, #12 - DIR_EVICT with a DIR_I victim | Directed | WRITE_BACK sub-state taken; the dirty line reaches the tap | Planned |
| TC-14 | FR-14 | #16 - invalidation storm (Premise R) | Directed | Other-line INV/DATA/INVACK/FWD traffic serviced during an outstanding miss | Planned |
TABLE END

[Normal] TC IDs align with the FR IDs; the Scenario column carries the WP section 5.1 test numbers (1-17 core, 18-22 conditional on the Week-8 DMA gate) so the mapping is traceable in both directions.

[Heading 2] 8.5 Exit Criteria for Verification Sign-off

[Normal] 100 % of the 42 bound SVA and I1-I7 pass with zero waivers; all directed tests pass; coverage targets met; lint and CDC clean.

[Heading 1] 9. FPGA Validation Requirements

[Heading 2] 9.1 Validation Scope and Objectives

[Normal] Hardware validation of the design on the committed 2x2 FPGA build; simulation cannot fully check hardware effects.

[Heading 2] 9.2 FPGA Platform and Tools

TABLE START
| Item | Value |
| Board / device | ZedBoard, XC7Z020-CLG484-1 (WP 6.1) |
| Toolchain | Vivado (synthesis, implementation, bitstream) |
TABLE END

[Heading 2] 9.3 FPGA Implementation Targets

TABLE START
| ID | Parameter | Target | Limit | Verified by |
| FPGA-01 | Clock frequency on board | TBD | TBD | STA |
| FPGA-02 | Timing closure (WNS) | 0 or better | 0 | STA |
| FPGA-03 | LUT utilization | <= 20,000 | <= 40,000 | Synthesis |
| FPGA-04 | FF utilization | <= 25,000 | <= 50,000 | Synthesis |
| FPGA-05a | BRAM36 utilization | <= 48 | <= 80 | Synthesis |
| FPGA-05b | DSP utilization | 0 | 0 | Synthesis |
TABLE END

[Heading 2] 9.4 I/O and Pin Mapping

TABLE START
| Signal | FPGA pin | I/O standard | Board connection |
| clk | warning - not specified in WP | warning - not specified in WP | On-board 100 MHz oscillator (WP 6.1) |
| reset | warning - not specified in WP | warning - not specified in WP | On-board reset source; discipline warning - not specified in WP |
TABLE END

[Heading 2] 9.5 FPGA Implementation Test Plan

TABLE START
| Test ID | Req ID | Procedure on board | Expected result | Observed result | Status |
| FV-01 | FR-09 | Run directed tests F1-F4 (forward, clean/dirty owner, GETS/GETM from DIR_E/DIR_M) via the JTAG stimulus source | Owner downgrades and sends DATAFWD; no PUTS/PUTM on the forward path; directory reaches DIR_S/DIR_M on UNBLOCK | - | Planned |
| FV-02 | FR-10 | Run directed test F8 (exclusive-bit correctness) | Forward of GETS grants excl = 0 (requester installs S); forward of GETM grants excl = 1 (requester installs M) | - | Planned |
| FV-03 | FR-11 | Read back the L2 tag arrays via the memory tap after fills and evictions (WP #11, #12) | Per-line word {valid, tag, dirty} (23 b at 2x2) matches the reference model; dirty excluded from tag compare and way select | - | Planned |
| FV-04 | FR-12 | Run directed test F3 (GETS forward from a dirty owner) | Header bit [39] set iff the owner held the line in M; bank dirty bit set | - | Planned |
| FV-05 | FR-13 | Force a DIR_EVICT whose victim is DIR_I with a dirty bank line (WP #12) | WRITE_BACK sub-state taken; dirty line reaches the tap; never silently dropped | - | Planned |
| FV-06 | FR-05 | Run directed tests F6/F7 (evict-during-forward) | Defensive INVACK sent; DIR_FWD_WAIT absorbs PUTS/PUTM; no orphan transient | - | Planned |
| FV-07 | FR-04 | Saturate one output port (WP #13, #15) | Every VC served within 13 rounds (5 + 3 + 5); no starvation | - | Planned |
| FV-08 | FR-01 | Run WP directed tests 1-17 end-to-end and compare against the reference model | Zero mismatches in L1/L2/directory/memory state and data | - | Planned |
| FV-09 | FR-03 | Hold credits at zero under saturation (WP #15) | No send at zero credit; per-VC FIFO order preserved; occupancy <= 4 | - | Planned |
| FV-10 | FR-08 | Single line fill and write-back (WP #1, #9, #10) | The whole 64 B line moves in one 512-bit intra-tile transfer | - | Planned |
| FV-11 | FR-07 | DMA end-to-end transfer (WP #18-#22) | DMA_ACK on completion; pending_op = DMA unreachable in the 2x2 build | - | Not applicable on the 2x2 board - 4x4 simulation only (ruling B4) |
| FV-12 | FR-05 | Conflict eviction with a full set (WP #9, #10) | Victim released before the miss request, both on VC0; L1 stays in IS_D/IM_D | - | Planned |
| FV-13 | - | Read the TILE_ID tie-off at the mesh top level | T0=(0,0), T1=(0,1), T2=(1,0), T3=(1,1); TILE_ID[1]=X, TILE_ID[0]=Y (WP 3.6) | - | Planned |
| FV-14 | - | Confirm the stimulus path: JTAG bridge drives every directed test | All directed tests run from the on-board JTAG bridge; ILA/VIO not required | - | Planned |
TABLE END

[Normal] Rows map 1:1 onto the 14-row section 16 implementation plan (WORK_BREAKDOWN_16.md); directed tests F1-F9 are defined in SLICE_16_1.md section 5.

[Heading 2] 9.6 Correlation with Simulation

[Normal] Hardware results are compared transaction-by-transaction against the reference model and the simulation scoreboard; any mismatch is a failure of this plan and is triaged against the directed test that produced it before the bitstream is re-run.

[Heading 2] 9.7 Exit Criteria for FPGA Validation

[Normal] Bitstream builds with timing closed, all hardware tests pass, results match simulation.

[Heading 1] 10. Traceability and Acceptance

TABLE START
| Req ID | Method | Test / evidence | Status |
| FR-01 | Formal / Simulation | A1.1-A1.5, A2.1-A2.7 / TC-01 | Planned |
| FR-02 | Formal / Simulation | A8.x, I1 / TC-02 | Planned |
| FR-03 | Formal / Simulation | I3, A4.x / TC-03 | Planned |
| FR-04 | Formal / Simulation | A5.x, I2 / TC-04 | Planned |
| FR-05 | Formal / Simulation | A1.1, A1.2, A3.x / TC-05 | Planned |
| FR-06 | Formal / Simulation | A7.x, A2.7 / TC-06 | Planned |
| FR-07 | Formal / Simulation (4x4 only) | A8.4 / TC-07 | Planned (Week-8 gate) |
| FR-08 | Formal / Simulation | A6.x / TC-08 | Planned |
| FR-09 | Formal / Simulation | A1.3, A2.2, A2.6 / TC-09 | Planned |
| FR-10 | Formal / Simulation | A1.2, A1.3 / TC-10 | Planned |
| FR-11 | Formal / Simulation | A6.x / TC-11 | Planned |
| FR-12 | Formal / Simulation | A6.x / TC-12 | Planned |
| FR-13 | Formal / Simulation | A6.x / TC-13 | Planned |
| FR-14 | Formal / Simulation | A3.x, A7.x / TC-14 | Planned |
TABLE END

[Heading 1] 11. Approval

TABLE START
| Role | Name | Signature | Date |
| Prepared by (group) | Group |  |  |
| Reviewed by (Group Mentor) | [Name] |  |  |
TABLE END

