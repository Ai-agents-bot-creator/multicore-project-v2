# 00 — Architecture & Microarchitecture Specification

> **Document Purpose**: Definitive technical specification and microarchitecture reference for the cache-coherent tiled multicore fabric, detailing cache hierarchies, coherence protocols, interconnect routing, and address mapping.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — direct declarative phrasing, unambiguous numeric citations, and strict active-voice descriptions.

## Scope

This document covers the coherence fabric only: L1/L2 caches, directory, NIC, router, mem_tap, and the
integration tiles. Processor-core RTL is **out of scope** (WP §1.4). Stimulus is provided via JTAG
testbench bridge on FPGA and cocotb directed tests in simulation.

**Configurations in scope**:
- **2×2** (4 CPU tiles) — ZedBoard XC7Z020 FPGA target @ 100 MHz.
- **4×4** (16 tiles) — simulation and scaling target; DMA tile gated on Week-8 gate (Ruling B4).

## Module Map

| Module | File | Build # | Description |
|---|---|---|---|
| `tile_pkg` | `rtl/pkg/tile_pkg.sv` | 0 | Single-source-of-truth parameter package |
| `l2_bank` | `rtl/l2/l2_bank.sv` | 1 | 8×4 tag+data SRAM; {valid,tag,dirty} per line; tree-PLRU |
| `l1_mesi_ctrl` | `rtl/l1/l1_mesi_ctrl.sv` | 2 | L1 MESI FSM; 9 states; forward release; conflict eviction |
| `dir_ctrl` | `rtl/directory/dir_ctrl.sv` | 3 | Directory FSM; 8 states; single-exit rule; DTR |
| `nic` | `rtl/nic/nic.sv` | 4 | Network interface; flit packetizer / depacketizer; credit mgr |
| `router` | `rtl/router/router.sv` | 5 | 5-port wormhole router; XY routing; 4-VC; age-escape arb |
| `mem_tap` | `rtl/mem_tap/mem_tap.sv` | 6 | Behavioural DDR tap; home-node memory model |
| `intra_tile_mux` | `rtl/tile/intra_tile_mux.sv` | 7 | Intra-tile arbitration bus |
| `cpu_tile` | `rtl/tile/cpu_tile.sv` | 8 | Full CPU tile integrator |
| `mesh_top` | `rtl/mesh/mesh_top.sv` | 9 | N×N mesh instantiation with TILE_ID and corner tie-offs |
| `fpga_top` | `syn/fpga/fpga_top.sv` | 10 | FPGA wrapper; JTAG bridge; clock / reset |
| `dma_tile` | `rtl/dma/dma_tile.sv` | 11 | **Gated 4×4 only** — DMA engine tile (Week-8 gate) |

## System Overview
- **Architecture**: Cache-Coherent Tiled Multicore on a 2D Mesh Network-on-Chip (NoC).
- **Configurations**:
  - **2×2 (4 CPU Tiles)**: Target for ZedBoard XC7Z020 FPGA implementation @ 100 MHz (10 ns clock).
  - **4×4 (16 Tiles)**: Simulation and scaling configuration (16 CPU tiles or 15 CPU + 1 DMA tile).
- **Topology**: 2D Mesh with XY deterministic wormhole packet routing.
- **Flit Format**: 64-bit flit; 1-flit control packets, 9-flit cache-line packets (1 header + 8 data flits).
- **Line Granularity**: 64 Bytes (512 bits) per cache line.

## Coherence & Memory Hierarchy
- **Coherence Protocol**: Directory-based MESI (4 stable L1 states + 5 transient states; 4 stable directory states + 4 transient states).
- **L1 Cache (Private)**:
  - 1 KB per tile (4 sets × 4 ways × 64 B).
  - Write-back, write-allocate.
  - Tree-PLRU replacement (3 bits/set).
- **L2 Bank (Shared, Distributed)**:
  - Static-NUCA distributed address interleaved across tiles.
  - 2 KB bank per CPU tile (8 sets × 4 ways × 64 B). Total L2: 8 KB (2×2), 32 KB (4×4).
  - Write-back, write-allocate; Tree-PLRU replacement (3 bits/set).
  - Per-line word: `{valid, tag, dirty}` (23 bits at 2×2, 21 bits at 4×4).
  - **Bank Port Interface (R3 — frozen)**:
    - `req`: `valid`, `is_write`, `addr[31:0]`, `wdata[511:0]`, `wstrb[63:0]`, `source : bank_src_e`
    - `rsp`: `valid`, `rdata[511:0]`, `rstrb[63:0]`, `rlast`
    - `status`: `dtr_busy` (one transaction per bank, N4/N5)
    - `source` enum: `SRC_TAP` (mem_tap), `SRC_REMOTE` (NoC), `SRC_L1` (local L1) — R2 arbiter input
- **Directory**:
  - Separate full-map tracking array (32 entries per bank, 10 bits used @ 2×2, 24 bits used @ 4×4).
  - Directory Transaction Record (DTR) per bank tracks pending operations (5 codes) and evictions (4 sub-states).
- **Virtual Channels (4 VCs per port)**:
  - VC0: `REQ` (GETS, GETM, PUTS, PUTM, DMA_WRITE)
  - VC1: `FWD` (FWD_GETS, FWD_GETM)
  - VC2: `RESP` (DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, DMA_ACK)
  - VC3: `INV` (INV)
  - Flow control: 4-bit credit counter (FIFO depth = 4 flits per VC).
- **Router Microarchitecture**:
  - 5-port module (LOCAL, N, S, E, W).
  - 4-stage pipeline: Route Compute (RC) → VC Allocation (VA) → Switch Arbitration (SA) → Switch Traversal (ST).
  - Arbitration: RESP > INV > FWD > REQ with 5-round age-escape threshold, port-granular output round-robin (derived 13-round fairness bound).

## L2 Bank Arbitration (R2 / R3)

The L2 bank serves three request sources: memory tap (fills/write-backs), remote NoC requests, and local L1 requests. The service order is **not fixed by the specification** (WP §12 item 9). 

- **R2 (Provisional)**: Default priority `tap > remote > L1` via `BANK_ARB_TAP_FIRST = 1` in `tile_pkg.sv`. Parameterised to allow `L1 > remote > tap` if profiling shows L1 starvation.
- **R3 (Frozen)**: Port interface includes `source_sel : bank_src_e` as the arbiter input; priority logic lives outside the bank.
- Open item: OI-4 — resolve if L1 starvation observed in simulation.

