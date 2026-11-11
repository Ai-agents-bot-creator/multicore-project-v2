# 05 — Data Safety & IP Boundaries

> **Document Purpose**: Security and intellectual property protocol defining confidentiality boundaries, licensing compliance, third-party library rules, and sensitive data protection.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — imperative procedural statements, clear prohibitions, and unambiguous legal/technical terms.

## Proprietary IP & Confidentiality
- **Source of Truth**: Based on academic reference specifications, custom SystemVerilog RTL, and formal assertions.
- **Third-Party IP**: No closed-source, encrypted, or NDA-encumbered IP macros are included.
- **Target Libraries**:
  - FPGA: AMD Xilinx 7-Series / Zynq-7000 primitive libraries (RAMB36E1, LUT, FF).
  - ASIC (Future Scope): Open-source Skywater 130nm (`sky130_fd_sc_hd`).

## Environment & Secrets Management
- No local hardcoded absolute secrets, credentials, or private keys shall be committed into git.
- Build and simulation logs with machine-specific telemetry must remain out of release branches.

## Licensing
- Project codebase and custom verification environment licensed under Apache-2.0 / MIT as declared in project manifest.

