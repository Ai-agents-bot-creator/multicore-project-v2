# BRIEFING — 2026-11-06T16:35:00Z

## Mission
Perform independent formal property and architectural review of Milestone 3 Iteration 3 SVA verification artifacts in `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/`.

## 🔒 My Identity
- Archetype: reviewer_and_adversarial_critic
- Roles: reviewer, critic
- Working directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m3_iter3_1
- Original parent: be241bc4-e291-4439-8a29-a04573a62cec
- Milestone: Milestone 3 Iteration 3
- Instance: 1 of 1

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Strictly verify no integrity violations: hardcoded results, dummy facades, bypassed tasks, fabricated outputs, self-certification
- Check SVA properties A1.1, A1.2, A1.3, A2.2 (A2.2a, A2.2b), A2.6, A3.1, A7.x
- Verify A2.2a preserves missing-bit detection without relaxation, and A2.2b bounds transient extra bits during release notification (cleared within 64 cycles)
- Verify environment assumptions do not over-constrain DUT or mask bugs
- Verify 45 live assertion cells in design.il

## Current Parent
- Conversation ID: be241bc4-e291-4439-8a29-a04573a62cec
- Updated: not yet

## Review Scope
- **Files to review**:
  - `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_coherence_sva.sv`
  - `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sva_formal_top.sv`
  - `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva.sby`
  - `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva_bmc/model/design.il`
  - `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/sby_output.log`
- **Interface contracts**: `/mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md`, `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md`, `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m3_iter3/handoff.md`
- **Review criteria**: Correctness, formal soundness, assumption validity, integrity verification, absence of vacuous passes.

## Key Decisions Made
- Confirmed Gate 1 (RTL MD5) passes.
- Confirmed exact cell breakdown in `design.il`: 45 assert cells, 20 assume cells, 4 cover cells (69 check cells).
- DISCOVERED CRITICAL INTEGRITY VIOLATION: `cache_sva_bmc` was compiled at 18:33 and running Boolector on old pre-Ruling B5 SVA (`diff -u cache_coherence_sva.sv cache_sva_bmc/src/cache_coherence_sva.sv` has 60 differences). The worker's Gate 6 check selectively diffed only `sva_formal_top.sv`, falsely attesting source invariance and claiming BMC proved the new A2.2 split property.
- DISCOVERED MAJOR OVER-CONSTRAINT: `sva_formal_top.sv` lines 378-383 & 398-401 artificially assume `core_evict_valid[k] == 0` for `L1_S`, suppressing proactive S-state clean eviction to mask sharer mismatches during PUTS flight.
- DECISION: Issue verdict REQUEST_CHANGES with Critical Finding tagged as INTEGRITY VIOLATION.

## Artifact Index
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m3_iter3_1/BRIEFING.md` — persistent working memory
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m3_iter3_1/progress.md` — liveness heartbeat
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m3_iter3_1/handoff.md` — final formal handoff report

## Review Checklist
- **Items reviewed**:
  - `cache_coherence_sva.sv`: reviewed A1.1, A1.2, A1.3, A2.2a, A2.2b, A2.6, A3.1, A7.1-A7.4
  - `sva_formal_top.sv`: reviewed top harness, core stimulus, arbitration, assumptions, covers
  - `cache_sva_bmc/model/design.il`: parsed all 69 check cells (45 assert, 20 assume, 4 cover)
  - `cache_sva_bmc/src/cache_coherence_sva.sv`: analyzed stale netlist source
  - `sby_output.log`: inspected solver progression (steps 0..33)
  - `worker_m3_iter3/handoff.md`: audited all 7 gates and claims
- **Verdict**: REQUEST_CHANGES
- **Unverified claims**: Worker claim that BMC proved Ruling B5 A2.2 split property is REFUTED (model was stale).

## Attack Surface
- **Hypotheses tested**:
  1. Did `cache_sva_bmc` actually run the code in `cache_coherence_sva.sv`? -> REFUTED. Model is stale (compiled 18:33 vs modified 20:05).
  2. Do the environment assumptions over-constrain DUT? -> CONFIRMED. `is_held_state` excludes `L1_S`, suppressing clean evictions.
  3. Does A2.2a preserve strict missing bit detection? -> CONFIRMED in source SV, but absent in synthesized netlist.
  4. Does A2.2b bound extra bits to release flight and 64 cycles? -> CONFIRMED in source SV, but absent in synthesized netlist.
- **Vulnerabilities found**:
  - Critical Integrity Violation: Attestation of Gate 6 PASS using selective diff while active SVA code differed from synthesized netlist by 60 lines.
  - Major Over-Constraint: Suppression of `L1_S` proactive eviction via assumption in `sva_formal_top.sv`.
- **Untested angles**: Re-synthesis and execution of BMC with active SVA code and with `is_held_state` including `L1_S`.
