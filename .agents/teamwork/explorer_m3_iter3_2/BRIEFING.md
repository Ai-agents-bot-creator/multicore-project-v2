# BRIEFING — 2026-11-06T01:30:00Z

## Mission
Inspect formal assumptions in sva_formal_top.sv and assertions in cache_coherence_sva.sv (A1.1-A1.3, A2.2, A2.6, A3.1, A7.1-A7.4), evaluate tautologies, sensitivity, non-vacuity, and recommend harness adjustments for clean BMC depth 64 execution.

## 🔒 My Identity
- Archetype: explorer
- Roles: formal testbench and SVA property explorer
- Working directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_iter3_2
- Original parent: be241bc4-e291-4439-8a29-a04573a62cec
- Milestone: Milestone 3 Iteration 3

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Inspect SVA formal top harness and property file
- Recommend fix strategy only; do not write or modify implementation code

## Current Parent
- Conversation ID: be241bc4-e291-4439-8a29-a04573a62cec
- Updated: 2026-11-06T01:23:49Z

## Investigation State
- **Explored paths**:
  - `white_papers/final/` (FINAL_whitepaper_v3.0.md, SLICE_16_1.md, WORK_BREAKDOWN_16.md, RULINGS_B1_B2_B4.md)
  - `clean_room_verification/tb_acceptance/sva/` (sva_formal_top.sv, cache_coherence_sva.sv, cache_sva.sby, sby_output.log, cache_sva_bmc/logfile.txt)
  - `clean_room_verification/rtl_frozen/` (tile_pkg.sv, l1_mesi_ctrl.sv, dir_ctrl.sv)
  - `Design-arch_multi-core/tb_rtl_evidence/sby_k64/` (l1_dir.sby, run_fix.log, fml_l1_dir.sv, sva_l1_dir.sv)
  - Prior reviews/audits (challenger_m3_1, auditor_m3_1, reviewer_m3_1, reviewer_m3_2)
- **Key findings**:
  - Assumptions in `sva_formal_top.sv` are sound, legal, and correctly model Slice 16.1 core stalling during transient misses.
  - Assertions A1.1, A1.2, A1.3, A3.1, A7.2, A7.3 are genuine, sensitive, non-tautological protocol invariants.
  - A7.1 has a pure mathematical tautology (`dir_state <= DIR_EVICT` for 3-bit unsigned vector <= 7).
  - A2.6 has a tautological sub-clause (`dir_owner < TILE_COUNT` for 2-bit unsigned wire < 4), though second conjunct is genuine.
  - A7.4 is structurally sound but vacuously true in Slice 16.1 because `DIR_EVICT` is unreachable in RTL.
  - A2.2 has a critical distributed race hazard: during proactive clean eviction from `L1_S`, L1 immediately drops to `L1_I` while `PUTS` is in flight in the network, during which `dir_sharers` still has that tile's bit set, creating a risk of false failure at deeper steps unless in-flight `PUTS` is accounted for or traffic is bounded.
  - `core_req_addr` is set to `32'h0000_1000` (bit 12=1 -> home tile 2), while comment states `bits [12:11] == 2'd0` (home tile 0).
  - Solver runtime analysis reveals Boolector takes ~45-60+ min at K=64 due to 4 unrolled tiles and 16-entry FIFOs; alternate solvers (`bitwuzla`, `yices`) or FIFO sizing (10-12) can substantially mitigate solver runtime.
- **Unexplored areas**: None; all required items investigated.

## Key Decisions Made
- Completed systematic audit of all 4 assumptions and all 10 assertions.
- Formulated concrete remediation recommendations for harness adjustments and solver execution strategy.

## Artifact Index
- DISPATCH.md — incoming dispatch log
- BRIEFING.md — persistent state briefing
- progress.md — activity heartbeat
- handoff.md — 5-component handoff report
