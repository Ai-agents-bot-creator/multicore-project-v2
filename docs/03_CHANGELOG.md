# Changelog

> **Document Purpose**: Version-controlled chronicle of milestone completions, architectural refactorings, and module progress across the hardware engineering lifecycle.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — short itemized clauses, clear past-tense action verbs, and unambiguous component naming.

All notable changes and implementation iterations for the Cache-Coherent Tiled Multicore project will be documented here.

## Milestones

| Milestone | Target Date | Status |
|---|---|---|
| M0 — Spec package + gate 134/134 | Week 1 | ✅ Done (2026-11-04) |
| M1 — l2_bank + l2_ctrl green | Week 2 | Pending |
| M2 — l1_mesi_ctrl + dir_ctrl co-landed | Week 3-4 | Pending |
| M3 — nic + router + mem_tap green | Week 5 | Pending |
| M4 — cpu_tile + mesh_top + fpga_top | Week 6 | Pending |
| M5 — FPGA validation (JTAG bridge) | Week 7 | Pending |
| M6 — DMA tile (4×4, Week-8 gate) | Week 8 | Gated |

## [Unreleased] - 2026-11-04
### Added
- Created standardized project documentation structure (`docs/01_DECISION_LOG.md`, `02_PROBLEM_LOG.md`, `03_CHANGELOG.md`, `04_TECH_STACK.md`).
- Installed `doc-generator` skill into `.gemini/config/skills/` and workspace `.agents/skills/`.
- Created RTL folder hierarchy (`rtl/pkg`, `rtl/l1`, `rtl/l2`, `rtl/directory`, `rtl/nic`, `rtl/router`, `rtl/mem_tap`, `rtl/tile`, `rtl/mesh`).
- Created testbench hierarchy (`tb/directed`, `tb/sva`, `tb/ref_model`).
- Implemented `rtl/pkg/tile_pkg.sv` containing single source of truth for parameterised types, addresses, states, and messages.

## [2026-11-05] — Toolchain Verification & Bank Port Freeze
### Added
- **Toolchain verified**: cocotb 2.1.0 + Icarus Verilog 13.0 proven end-to-end via `tb/smoke/` (ALU combinational + DFF async reset with 2 negative controls).
- **Criterion 1 demonstrated**: Smoke test passes with positive + negative controls.
- **Doc checker hardened**: `check_docs.py` now has count-drift guard (EXPECTED_CHECKS=47); fails if any check silently skipped.
- **R3 — L2 bank port frozen**: Added `bank_src_e` enum (SRC_TAP, SRC_REMOTE, SRC_L1) and frozen port signature to `tile_pkg.sv`.
- **Created `rtl/l2/l2_bank.sv`**: Stub implementation (all outputs = 0) for port freeze.
- **L1/dir testbench scaffold** (`tb/l1_dir/`): Stubs for `l1_mesi_ctrl` + `dir_ctrl`, F1 positive test + 2 negative controls (both pass, proving scaffold has teeth).
- **Scaffold mutation-tested**: Original negatives passed vacuously against the zero stub; `test_f1_forward.py` restructured (negative controls now PASS only while their fault is present) and proven against 3 stub mutations — 9/9 expected outcomes, including positive rejecting a dirty DATAFWD.
- **R4 — cocotb 2.1.0 pinned**: Documented in decision log with migration notes.


## [2026-11-10] — v7: Formal Scope Publication, VC0 FIFO-Order Case, Canonical Lint & Constraints
### Added
- **Formal scope published as an ID list**: added `tb_rtl_evidence/FORMAL_SCOPE.md`. The file lists all 36 live `$check` cells (32 asserts + 4 assumes) with the harness source line of each, the four assumptions with a one-sentence "what becomes unproven if the assumption is false", and an itemised table of the specification IDs that are **not** in the harness with where each is covered instead.
- **Three-tile VC0 FIFO-order directed case**: added `tb_rtl_evidence/directed_vc0_fifo/` (`tb_directed_vc0_fifo.sv`, `directed_vc0_fifo.py`, `Makefile`). Three tiles put two pending REQs for the same line on VC0 at once (proved from the directory's own queue pointers: `cnt=2 rd=1 wr=3`). Checks B8.1.1 (anti-vacuity), B8.1.2 (FIFO order, I4) and B8.1.3 (the line completes).
- **Canonical 25-rule lint**: added `lint/coding_rules.json` and `lint/check_rules.py`. The set is 3 tool-driven rules (Verilator ×2, Icarus ×1) plus 22 source-level rules. Wired into the per-module gate (`docs/06_VERIFICATION_PLAN.md` §3, `docs/BUILD_ORDER.md`).
- **FPGA constraints, split board/design**: added `syn/fpga/zc702_board.xdc` (board: package pins and IOSTANDARDs) and `syn/fpga/design.xdc` (design: clock period and reset wiring).
- **BMC status file**: added `tb_rtl_evidence/FORMAL_K64_STATUS.md` — the observed state of the K=64 run on the landed RTL.

### Changed
- **Mutation matrix extended to five columns**: `tb_self_test/l1_dir/run_mutations.py` gained the `vc0_fifo` column. The count is derived from the matrix: **20/20** (4 variants × 5 tests). MUT-D (head insertion) is now killed by the FIFO-order detector itself — the mutant still completes the line (`sharers=0b111`, all three L1s in `L1_S`), so the kill is the ordering property and not a stall.
- **B8.1 coverage status recorded**: `tb_rtl_evidence/SUMMARY.md`, `docs/06_VERIFICATION_PLAN.md` (§9) and `docs/01_DECISION_LOG.md` now carry the wording "B8.1 (re-issue ordering) — RTL status: NOT RTL-VERIFIED", with the reason (accept-only RTL; the re-issue never occurs) and the open item (implement the decline path).
- **BMC K=64 re-run on the landed RTL**: the run executes as a systemd user unit so a machine restart cannot kill it (the v6 run was lost twice to restarts). The item is **OPEN** at the depth actually reached.

### Fixed
- **`WAKE_UP.sh` repointed at `rtl/`**: removed the hard-coded golden hashes (which predated the B6/B7.1/B8 landings and made the script fail on a correct tree), removed the `rtl_frozen/` snapshot creation (that directory belongs to the clean-room agent), made the RTL check read the live `rtl/FROZEN.md5`, and stopped Step 3 from clobbering an existing `tb_self_test/README.md`.
- **`.gitignore` pattern widened**: `sim_build*/` now covers every build directory variant (the v6 commit had staged `sim_build_mut/cmds.f` twice).
- **Stale formal copies deleted**: removed `tb/sva/` (a superseded duplicate of the live harness `tb_rtl_evidence/sby_k64/`, holding pre-B6/B7.1 RTL copies). No gate read it.
