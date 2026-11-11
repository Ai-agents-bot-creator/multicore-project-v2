# Tech Stack & Dependencies

> **Document Purpose**: Authoritative inventory of development languages, synthesis toolchains, formal solvers, simulation engines, licenses, and version-pinning rationales for the project.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — concise tabular taxonomy, technical accuracy, and clear active descriptions.

| Tool / Dependency | Version / Target | Purpose / Scope | License | Why Chosen |
|---|---|---|---|---|
| **SystemVerilog** | IEEE 1800-2017 | RTL implementation and assertions (SVA) | Open Standard | Synthesis & verification standard |
| **Vivado** | 2026.1 | FPGA synthesis, implementation, timing closure | Proprietary (AMD Xilinx) | Targets ZedBoard XC7Z020 @ 100 MHz |
| **SymbiYosys (sby)** | Latest / Pinned | Formal verification (BMC K=64, k-induction k=16) | ISC License | Open-source formal model checking |
| **cocotb** | **2.1.0 (pinned)** | Python simulation harness; co-sim with iverilog | BSD | Proven with tb/smoke/ |
| **pyuvm** | Python 3.14 | Constrained-random & transaction reference model | Apache-2.0 | TLM reference verification |
| **Icarus Verilog** | **13.0 (stable, v13_0)** | Simulation backend for cocotb | GPL | Fast local simulation |
| **Verilator** | Present, not used | Linting only (`verilator --lint-only`) | LGPL | Not used for cocotb sim |

> **Pin notice**: cocotb is pinned to 2.1.0; iverilog to 13.0. Do not upgrade without re-running `tb/smoke/` and confirming green.