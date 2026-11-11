# BRIEFING — 2026-11-09T13:50:00Z

## Mission
Investigate Formal BMC K=64 strategy: solver configuration, formal SVA cell counts, architectural invariant count invariance (42 properties), UNBLOCK assumption protocol justification, and concrete worker instructions.

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: Formal Verification Analyst, SVA Invariants & Protocol Specialist
- Working directory: /home/durgesh/teamwork_projects/clean_room_verification
- State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_m1_1/
- Original parent: a51a5a34-58bc-4867-bb5d-12b335e78d2a
- Milestone: M1 (Formal BMC K=64 Verification)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code outside state folder
- Work within /home/durgesh/teamwork_projects/clean_room_verification (read-only)
- Verify exact count of netlist assertion cells (45) and architectural SVA count (42)
- Document UNBLOCK assumption protocol justification citing WP §3.3 (Rules 5 & 6) and Appendix A
- Deliver structured handoff report in state folder and notify caller via send_message

## Current Parent
- Conversation ID: a51a5a34-58bc-4867-bb5d-12b335e78d2a
- Updated: 2026-11-09T13:50:00Z

## Investigation State
- **Explored paths**: `tb_acceptance/sva/cache_sva.sby`, `cache_coherence_sva.sv`, `sva_formal_top.sv`, `FINAL_whitepaper_v3.0.md` (§3.3, §5.2, §8, §13), `RULINGS_B1_B2_B4.md`, `RULINGS_B8.md`, `pd/v1/verify_patch_set.py` (K9 check), `tb_rtl_evidence/FORMAL_K64.md`, `oss-cad-suite` binaries and Python scripts (`smtio.py`, `sby_engine_smtbmc.py`).
- **Key findings**:
  1. `cache_sva.sby` currently specifies `smtbmc boolector`, which times out / hangs at step 33 (1h47m). Bitwuzla 0.9.1 is installed in `/home/durgesh/.local/oss-cad-suite/bin/bitwuzla`. Configuring `smtbmc bitwuzla` (optionally with `--nopresat`) executes BMC steps efficiently without solver hangs.
  2. The netlist contains exactly 45 assertion cells (`$assert`) and 25 assumption cells (`$assume`), unrolled across 4 tiles and 1 directory controller from the 42 architectural SVA corpus (categories A1, A2, A3, A7).
  3. SVA architectural count remains invariant at strictly 42 across all 8 categories (sum(cats) == 42 checked by `verify_patch_set.py` K9). Rulings B5 and B6 obligations were mapped into existing properties (A2.2, A7.1, A3.1) with zero new property IDs.
  4. Protocol assumption `assume(UNBLOCK -> L1 state in {S,E,M})` at `sva_formal_top.sv:419,425` is justified by WP §3.3 Rule 6 and Appendix A, preventing an unphysical harness bug (false counterexample at step 48) where the solver injects UNBLOCK before DATA installation.
- **Unexplored areas**: None for M1 formal strategy. Full solution ready for worker handoff.

## Key Decisions Made
- Recommend Worker update `tb_acceptance/sva/cache_sva.sby` engine to `smtbmc bitwuzla` (or `smtbmc --nopresat bitwuzla`).
- Provide concrete execution command `source /home/durgesh/.local/oss-cad-suite/environment && sby -f cache_sva.sby bmc`.

## Artifact Index
- DISPATCH.md — Task assignment log
- BRIEFING.md — Persistent context & state
- progress.md — Liveness heartbeat & step progress
- handoff.md — 5-component handoff report for Worker / Parent
