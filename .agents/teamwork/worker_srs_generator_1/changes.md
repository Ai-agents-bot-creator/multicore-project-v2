# Detailed Changes Log — SRS Final v2 Elevation & Verification Upgrade

**Date:** 2026-11-09  
**Agent:** Worker SRS Generator 1 (`worker_srs_generator_1`)  
**Target Files:**
- `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final_v2.docx` (Created)
- `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py` (Upgraded)

---

## 1. Modifications in `SRS_final_v2.docx`

### 1.1 Document Header & Metadata Table (Table 1)
- **Title Block Paragraphs (P1–P5):**
  - Updated `Group:` from empty string to `Group 16 (PGCP VLSI)`.
  - Normalized `Members:` formatting to `Durgesh Kolhe, Sai Charan, Additya, Joshna`.
  - Set `Group Mentor:` to `Mr. Hemat`.
  - Updated `Version / Date:` to `v2.0 / 09-11-2026`.
- **Rebuilt Table 1 (5×2 Metadata Table per Student Guide & Template):**
  - Row 1: `Project title | Cache-Coherent Tiled Mesh Multicore`
  - Row 2: `Group | Group 16 (PGCP VLSI)`
  - Row 3: `Members | Durgesh Kolhe, Sai Charan, Additya, Joshna`
  - Row 4: `Group Mentor | Mr. Hemat`
  - Row 5: `Version / Date | v2.0 / 09-11-2026`
- **Document Control Table (Table 2):**
  - Added formal revision entry for `v2.0` dated `09-11-2026` documenting full template compliance, rulings B6–B8, standards alignment (ISO/IEC/IEEE 29148), 100 MHz clock closure, 50 mW power budget, AREA-04 FF target, PPA priority order, credit-based link signals, ZedBoard pin mappings, restored subsystem interface summary, timing budget, DMA register map, code coverage targets, 44-row traceability matrix, and XML pagination formatting.

### 1.2 Section 2: Overall Description
- **Section 2.1 (System Context):**
  - Replaced paragraph disclaimer with concrete text definition of `Figure 2.1 System Context (HLD-F2)`: ZedBoard XC7Z020 FPGA top-level block diagram defining DUT boundaries (Tiles 00, 01, 10, 11) and external connections (100 MHz oscillator Pin Y9, reset synchronizer Pin P16/F22, behavioural memory tap, on-board JTAG stimulus bridge, diagnostic LEDs LD0–LD3).
- **Section 2.3 (Assumptions and Constraints - Table 6):**
  - `AC-01`: Added static hardwired `TILE_ID[1:0]` input requirement per tile.
  - `AC-02`: Explicitly stated credit-based flow control with depth 4 flits per VC.
  - `AC-03`: Reinforced 4 virtual channels with index order VC0=REQ, VC1=FWD, VC2=RESP, VC3=INV and priority order RESP > INV > FWD > REQ.
  - `AC-04`: Specified 64-byte (512-bit) line width and 64-bit flit datapath.
  - `AC-05`: Formal proof bound T=64 cycles (2x2) / 150 cycles (4x4 simulation) and 13-round fairness bound.

### 1.3 Section 3: Functional Requirements (Table 7)
- Preserved `FR-01` through `FR-14` verbatim.
- Added 6 new normative functional requirements (`FR-15` through `FR-20`):
  - **`FR-15` (Same-line INV abort):** When an L1 controller with an outstanding read miss (`IS_D`) or write miss (`IM_D`/`SM_D`) receives an incoming invalidation (`INV`) matching the miss address, it immediately aborts the miss, acknowledges the invalidation via `INVACK` on VC2, and re-issues the miss request on VC0 (Ruling B6, WP §3.3 rule 6, row AH). Verified by `A3.x, A7.x / TC-15`.
  - **`FR-16` (Directory per-VC receive queueing & UNBLOCK completion):** Directory controller maintains per-VC receive queueing with four independent arrival queues prioritized in descending fabric priority order (`RESP > INV > FWD > REQ`); aborted accesses complete via `UNBLOCK` to guarantee no transient state remains unexited (Ruling B7, row AI). Verified by `A2.x, A6.x / TC-16`.
  - **`FR-17` (FIFO re-issue ordering & Lemma L2 bounded progress):** An aborted access re-issues as a new request enqueued strictly at the back of the directory request queue (FIFO within VC0), bounding progress under Lemma L2 and preventing livelock (Ruling B8, row AJ). Verified by `A5.x, I4 / TC-17`.
  - **`FR-18` (Memory consistency vs coherence boundary):** Directory serializes transactions per-address at the home bank; cross-address memory consistency models (SC, TSO), memory fences/barriers, and atomic instructions are outside the hardware contract (WP §3.10). Verified by `A2.x, A6.x / TC-01`.
  - **`FR-19` (Transient race handling):** L1 evictions concurrent with forwards (`EI_A`/`MI_A`) transmit defensive `INVACK`; L1 state E silently transitions to M on local store hit and asserts dirty bit [39] on downgrade `DATAFWD`; 3-bit Tree-PLRU replacement selects victim deterministically; routers preserve VC index without alteration (WP §3.3, §3.5, §5.3; invariants I2, I6). Verified by `A1.x, A6.x, I2, I6 / TC-09, TC-12, FV-04, FV-06`.
  - **`FR-20` (Inclusive L2 shortcut & miss retry):** Inclusive L2 cache with local shortcut/bypass for on-tile accesses; if an invalidation race occurs while miss in flight, L2 retries miss upon invalidation completion (WP §3.1, §3.3). Verified by `A2.x, A6.x / TC-01, TC-14`.

### 1.4 Section 4: Performance Requirements (Table 8)
- `PERF-01`: Replaced `TBD` with target `100 MHz (10.0 ns)` and minimum `50 MHz (20.0 ns)` on ZedBoard XC7Z020 slow corner (0.95V, 85°C), verified by STA.
- `PERF-02`: Replaced `TBD` with target `>= 1 flit/cycle per node peak injection; sustained load saturation >= 0.25 flits/node/cycle` and minimum `>= 0.15 flits/node/cycle under uniform random traffic`, verified by pyuvm throughput testbench.

### 1.5 Section 5: Power Requirements (Table 9)
- Removed false statement claiming "WP contains no power data".
- Integrated normative power budget from WP §6.4: Total on-chip power budget `<= 50 mW` at 100 MHz on ZedBoard XC7Z020 (estimated via XPE pre-synthesis, measured via `report_power` post-implementation).
- Explicitly documented that dynamic power management modes (clock/power gating) and 4x4 ASIC dissipation are out of scope for this milestone.
- Updated Table 9:
  - `PWR-01`: Dynamic power `<= 35 mW` target, `<= 50 mW` max at 100 MHz, alpha=0.125.
  - `PWR-02`: Leakage power `<= 15 mW` target, `<= 25 mW` max at 25°C.
  - `PWR-03`: Total power `<= 50 mW` target, `<= 75 mW` max (WP §6.4).

### 1.6 Section 6: Area Requirements (Table 10)
- Added `AREA-04`: `FPGA FF utilization (2x2) | <= 25,000 (23.5 % of 106,400) | <= 50,000 (47.0 %) | 2x2 build | Synthesis` (WP §6.1).
- Codified normative PPA conflict resolution clause:
  *"The binding PPA trade-off priority order shall be: Correctness > Area > Frequency > Power. Specifically, functional correctness and coherence safety take precedence over all physical metrics, followed by FPGA resource fit (LUT <= 40,000, BRAM <= 80), timing closure (100 MHz target, WNS >= 0), and power consumption (<= 50 mW)."*

### 1.7 Section 7: Interface Requirements
- **Section 7.1:** Restored **Table 11a (Subsystem Interface Summary)** defining Core/Stimulus Master Port, Memory Tap Interface, Inter-Tile Router Links, and JTAG Stimulus Bridge before the Message Set table.
- **Section 7.2 (Signal List - Table 12):**
  - Removed erroneous combinatorial `port_in_ready` and `port_out_ready`.
  - Added static hardwired `TILE_ID[1:0]` module input.
  - Specified explicit credit flow control lines: `credit_in[3:0]` and `credit_out[3:0]`.
  - Defined explicit 64-bit flit widths: `flit_in[63:0]` and `flit_out[63:0]`.
  - Defined explicit 2-bit VC lines: `flit_in_vc[1:0]` and `flit_out_vc[1:0]`.
- **Section 7.3 (Clocks and Resets - Table 13):**
  - Set `clk` frequency to `100 MHz (10.0 ns period)` on ZedBoard Pin `Y9`.
  - Specified `reset` as synchronized active-high reset on Pins `P16` (BTNC) / `F22` (SW0) with false path in XDC.
- **Section 7.4 (Timing Budget & Interface Rules):**
  - Restored **Table 14 (Timing Budget & Interface Rules)** specifying clock period (10.0 ns), setup uncertainty (0.2 ns), hold uncertainty (0.1 ns), WNS >= 0 ns, WHS >= 0 ns, WPWS >= 3.750 ns, TNS = 0, credit-based flow control (depth 4), and reset synchronizer.
- **Section 7.5 (Register Map):**
  - Restored **Table 15 (4x4 Gated DMA Channel Register Map)** enumerating 6 channel registers: `SRC_LO (0x00)`, `DST_LO (0x04)`, `LEN (0x08)`, `CTRL (0x0C)`, `STATUS (0x10)`, `COUNT (0x14)`. Explicitly annotated as 4x4 simulation-only and Week-8 gated per Ruling B4.

### 1.8 Section 8: Verification Requirements
- **Section 8.1 / 8.5:** Documented the full formal property configuration: 38 bound safety assertions (A1.1-A1.5, A2.1-A2.7, A3, A4, A6, A7, A8), bounded liveness T=64 cycles (2x2) / 150 cycles (4x4), and all 7 network invariants (`I1` XY routing, `I2` VC class match, `I3` credit conservation, `I4` per-VC FIFO ordering, `I5` delivery/protocol termination, `I6` VC preservation, `I7` inter-class edge ascent).
- **Section 8.3 (Coverage Goals - Table 15):**
  - Restored code coverage targets: Statement / Line coverage (`>= 90 %`), Branch coverage (`>= 85 %`), Toggle coverage (`>= 85 %`) alongside functional coverage (100% bins, 100% FSM transitions, 100% assertion pass with zero waivers).
- **Section 8.4 (Directed Test Plan - Table 16):**
  - Added `TC-15` (Same-line INV abort in IS_D/IM_D/SM_D), `TC-16` (Directory per-VC receive queue priority), and `TC-17` (FIFO re-issue ordering under Lemma L2).

### 1.9 Section 9: FPGA Validation Requirements
- **Section 9.3 (Implementation Targets - Table 18):**
  - `FPGA-01`: Target `100 MHz (10.0 ns)`, Limit `50 MHz (20.0 ns)`.
  - `FPGA-02`: Timing closure margins `WNS >= 0 ns, WHS >= 0 ns, WPWS >= 3.750 ns, TNS = 0`.
  - `FPGA-04`: Added FF utilization target `<= 25,000 (23.5 %)`, limit `<= 50,000 (47.0 %)`.
  - `FPGA-06`: Added JTAG stimulus bridge operational requirement.
- **Section 9.4 (Pin Mapping - Table 19):**
  - Populated ZedBoard package pins: `clk` on Pin `Y9` (LVCMOS33 100 MHz oscillator), `reset` on Pin `P16` (BTNC) / Pin `F22` (SW0), and diagnostic status LEDs on Pins `T22, T21, U22, U21`.
- **Section 9.5 (FPGA Test Plan - Table 20):**
  - Linked `FV-13` to requirement ID `AC-01`.
  - Linked `FV-14` to requirement ID `FPGA-06`.

### 1.10 Section 10: Traceability and Acceptance Matrix (Table 21)
- Expanded Table 21 from 14 rows to **44 comprehensive rows** covering every requirement ID:
  - `FR-01` through `FR-20` (20 rows)
  - `AC-01` through `AC-05` (5 rows)
  - `PERF-01` through `PERF-06` (6 rows)
  - `PWR-01` through `PWR-03` (3 rows)
  - `AREA-01` through `AREA-04` (4 rows)
  - `FPGA-01` through `FPGA-05b` (6 rows)
- Linked each requirement to its verification method (Formal, Simulation, STA, Synthesis, Review, Tool Report), verification evidence / test ID, and status (`Planned` or `Planned (Week-8 Gate)`).

### 1.11 Section 11: Approval Table (Table 22)
- Row 2: Replaced unresolved `[Name]` placeholder with `Mr. Hemat` (Group Mentor).
- Updated Prepared by to `Group 16` (`Durgesh Kolhe, Sai Charan, Additya, Joshna`).
- Set sign-off milestone to `Planned for final sign-off at Week 14 bitstream deliverable`.

### 1.12 Universal Table XML Pagination Formatting
- Programmatically applied `w:tblHeader` on Row 0 of all 26 tables in the document.
- Programmatically applied `w:cantSplit` on all rows of all 26 tables.

---

## 2. Upgrades to `verify_srs.py`

- Upgraded test suite from 41 baseline checks to **66 comprehensive automated checks**:
  - Maintained all 41 original checks (`B1a..e`, `B2a..b`, `B3a..e`, `B4a..e`, `B5a..b`, `B6a..b`, `M1a`, `M2-09..14`, `M3a..b`, `M4a..b`, `M5a..b`, `M6a..b`, `N1a`, `N2a`, `N4a`, `N5a`, `N6a`).
  - Added 25 expanded verification checks:
    * `M2-01` through `M2-08`: Normative keyword verification for `FR-01` through `FR-08`.
    * `B6c`: 100% traceability coverage across all defined requirements (`FR`, `PERF`, `PWR`, `AREA`, `FPGA`).
    * `M1b`: Exact 14-row count verification for Section 7.1 Message Table.
    * `M3c`: Code coverage targets verification (statement, branch, toggle).
    * `M4c`: FPGA test plan unlinked check (no `-` or blank requirement IDs).
    * `N5b`: Numeric on-chip power budget grounding in WP §6.4 (`<= 50 mW`).
    * `T01`: `PERF-01` 100 MHz clock frequency target verification (not TBD).
    * `T02`: `FPGA-01` 100 MHz on-board target frequency verification (not TBD).
    * `T03`: Section 7.4 timing rules parameter verification (WNS, setup/hold uncertainties).
    * `T04`: Section 7.5 DMA register map enumeration (`SRC_LO`, `DST_LO`, `LEN`, `CTRL`, `STATUS`, `COUNT`).
    * `T05`: Section 6 Flip-Flop resource target verification (`<= 25,000`).
    * `T06`: Section 6 PPA trade-off priority order definition verification.
    * `T07`: Complete SVA category verification (`A1` through `A8`).
    * `T08`: Complete network invariant verification (`I1` through `I7`).
    * `T09`: Core control and credit signal verification (`clk`, `reset`, `credit_in`, `credit_out`).
    * `T10`: Template placeholder detection (`[Name]`, `[Group]`, `TODO`, `FIXME`).
    * `T11`: Group Mentor approval resolution verification (`Mr. Hemat`).
    * `T12`: Metadata Group name validity verification (`Group 16 (PGCP VLSI)`).
- Added `--baseline` command-line argument:
  - Running with `--baseline` executes the 41 original checks for backward compatibility (`SRS_final.docx` passes 41/41).
  - Running without `--baseline` executes the full 66 checks (`SRS_final_v2.docx` passes 66/66; `SRS_final.docx` fails 10 strict checks as expected).
