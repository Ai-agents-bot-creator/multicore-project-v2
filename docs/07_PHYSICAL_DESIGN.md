# 07 — Physical Design & FPGA Implementation

> **Document Purpose**: Hardware synthesis and physical implementation specification for FPGA emulation on the Xilinx Zynq-7000 (ZedBoard), defining clocking, reset, IO budgets, and static timing constraints.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — precise numerical budgets, concise constraint statements, and unambiguous implementation parameters.

## Target Platform
- **Device**: AMD Xilinx Zynq-7000 SoC (`XC7Z020-CLG484-1`) on ZedBoard.
- **Clock Frequency**: 100 MHz (Target Clock Period: 10.0 ns).
- **Emulation Topology**: 2×2 mesh (4 CPU Tiles, all corner positions with unused ports tied off).

## Synthesis & Implementation Constraints
- Target Toolchain: Vivado 2026.1 / pinned release.
- Static Timing Constraints:
  - Setup Uncertainty: 0.2 ns
  - Hold Uncertainty: 0.1 ns
  - I/O Delays: Max 2.0 ns / Min 0.5 ns
  - Reset Synchronizer: Declared false path in XDC.
  - Slack Requirements: WNS ≥ 0.0 ns, WHS ≥ 0.0 ns, WPWS ≥ 3.750 ns.
- Critical Path Optimization:
  1. Pipeline split between L2 tag compare and directory state lookup.
  2. Router 4-stage pipeline (RC/VA/SA/ST) separating arbitration from crossbar traversal.
  3. Registered decoder outputs on the NIC to cache boundaries.

## Resource Budget (2×2 Configuration)

| Resource | Target | Ceiling | Available | Notes |
|---|---|---|---|---|
| LUTs | < 20,000 | 40,000 | 53,200 | Coherence fabric only; no processor core |
| FFs | < 25,000 | 50,000 | 106,400 | |
| BRAM36 | 28 | 80 | 140 | Unconstrained at 2×2 — BRAM is not the binding resource |
| DSP48 | 0 | 0 | 220 | No arithmetic paths in coherence fabric |
| Power | — | 50 mW | — | Estimated on-chip core power |

- **Power**: ≤ 50 mW estimated on-chip core power.

