# BRIEFING — 2026-11-05T19:42:00Z

## Mission
Investigate formal top harness architecture in `sva_formal_top.sv` and design a concrete, complete fix strategy for stimulus generation and non-vacuity proofs (formal reachability/cover) for Milestone 3 Remediation.

## 🔒 My Identity
- Archetype: explorer
- Roles: Stimulus Architecture & Non-Vacuity Explorer
- Working directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_fix_1
- Original parent: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Milestone: Milestone 3 Remediation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement changes in `tb_acceptance/`
- Strictly observe clean-room isolation: NEVER read, copy, or inspect any files from `/mnt/Code/visualstudio/Design-arch_multi-core/tb/self_test/`, `/mnt/Code/visualstudio/Design-arch_multi-core/tb/l1_dir/`, or scratch directories. The frozen RTL in `rtl_frozen/` is a read-only black box.
- Do NOT recommend approaches listed in `DEAD_ENDS.md`.

## Current Parent
- Conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Updated: 2026-11-05T19:41:01Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`, `DEAD_ENDS.md`
  - Forensic auditor report (`auditor_m3_1/handoff.md`), challenger reports (`challenger_m3_1`, `challenger_m3_2`)
  - Target files: `tb_acceptance/sva/sva_formal_top.sv`, `cache_coherence_sva.sv`, `cache_sva.sby`
  - RTL frozen files: `tile_pkg.sv`, `l1_mesi_ctrl.sv`, `dir_ctrl.sv`
- **Key findings**:
  1. Undriven unpacked array declarations in `sva_formal_top.sv` (`logic core_req_valid [TILE_COUNT]`) cause Slang/Yosys to synthesize `$mem_v2` memory cells with `WR_PORTS=0`.
  2. Because of `assume(core_req_valid[k] == 0)` at `!rst_n`, the transition relation `(= state next_state)` locks `core_req_valid` to 0 for all 64 steps, resulting in 100% vacuous BMC.
  3. Declaring top-level input ports (`in_core_req_valid`, `in_core_req_is_write`, `in_core_evict_valid`) and driving packed internal wires eliminates all stimulus `$mem_v2` cells completely.
  4. Driving `core_req_addr` and `core_req_wdata` with continuous assignments eliminates 2048-bit wide unpacked memories and replaces them with constants (`32'h0000_1000` and `512'b0`).
  5. Active stimulus immediately uncovers the latent framing bug in A3.1 at step 12 where payload bit 41 of multi-flit `DATA` packets is mistaken for a header flit.
  6. SBY `mode cover` reaches `cov_req_0` at step 2, `cov_l1_is_d` and `cov_l1_im_d` at step 3, and `cov_dir_mem` at step 8 in 27s, proving non-vacuity.
- **Unexplored areas**: None. Investigation complete and empirically verified.

## Key Decisions Made
- Expose primary input ports on `sva_formal_top` as the primary stimulus interface.
- Prune 512-bit data memory by continuous assignment to reduce SMT state size.
- Incorporate comprehensive cover matrix and dual SBY target configuration for non-vacuity verification.

## Artifact Index
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_fix_1/DISPATCH.md` — Inbound message log
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_fix_1/BRIEFING.md` — Working state and identity
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_fix_1/progress.md` — Liveness heartbeat and milestone tracking
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_fix_1/handoff.md` — Final structured report
