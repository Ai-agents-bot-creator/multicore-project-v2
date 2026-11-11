## 2026-11-09T13:51:58Z
## Dispatch Task — Milestone 1 Worker (Formal BMC, Tests, Docs Lockstep & Final Verification Report)

Working directory: /home/durgesh/teamwork_projects/clean_room_verification
State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_worker_m1/
Original Request file: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
Scope document: /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Context & Explorer Findings
Read the Explorer handoff reports before beginning:
- Formal BMC Strategy: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_m1_1/handoff.md`
- Docs Lockstep Strategy: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_m1_2/handoff.md`
- Test & Report Strategy: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_m1_3/handoff.md`

### Tasks to Implement and Verify
1. **Formal BMC K=64 Execution**:
   - In `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva/cache_sva.sby`:
     Update engine from `smtbmc boolector` to `smtbmc bitwuzla` (or `smtbmc --nopresat bitwuzla`).
   - Run formal BMC to full depth K=64:
     ```bash
     cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/sva
     source /home/durgesh/.local/oss-cad-suite/environment
     sby -f cache_sva.sby bmc
     ```
   - Verify that all 45 assertion cells remain live without vacuity and that ZERO violations occur through step 64 (`DONE (PASS, rc=0)`).
   - Confirm netlist contains 45 assertion cells and 25 assumption cells, and that the bound SVA property count remains strictly 42 across categories A1–A8.
   - Confirm and document the formal harness assumption `assume(UNBLOCK from req_tile → L1 state ∈ {S,E,M})` at `sva_formal_top.sv:419,425` with its protocol justification citing WP §3.3 Rules 5 & 6 and Appendix A.

2. **Lockstep Documentation Synchronization**:
   - Update `docs/01_DECISION_LOG.md` and `tb_acceptance/docs/01_DECISION_LOG.md` in the clean room workspace so that rows AH, AI, and AJ match byte-for-byte verbatim the text in `FINAL_whitepaper_v3.0.md` §13 (or `/mnt/Code/visualstudio/Design-arch_multi-core/docs/01_DECISION_LOG.md`).
   - Synchronize problem log (`02_INDEPENDENT_FINDINGS_LOG.md`), verification plan (`06_INDEPENDENT_VERIFICATION_PLAN.md`), and scratchpad (`AI_SCRATCHPAD.md`) as detailed in M1 Explorer 2's report.
   - Run the canonical package verifier and confirm all 134 checks pass:
     ```bash
     cd /mnt/Code/visualstudio/Design-arch_multi-core
     python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py
     ```

3. **Directed & Mutation Test Suite Execution**:
   - Execute directed upgrade-race tests with `unset PYTHONHOME`:
     ```bash
     cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
     unset PYTHONHOME; unset PYTHONPATH
     PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make TESTCASE=test_f_concurrent_upgrade_abort,test_f_concurrent_upgrade_decline_reissue
     ```
     Verify same-line INV triggers immediate abort with INVACK on VC2, non-blocking completion, exactly one holder in M.
   - Execute mutation matrix tests:
     ```bash
     cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/mutations
     unset PYTHONHOME; unset PYTHONPATH
     PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make
     ```
     Verify that all 4 active negative controls (Mut-05, Mut-06, Mut-07, Mut-08) kill their injected mutants and unmutated baseline passes (`TESTS=4 PASS=4 FAIL=0`).
   - Verify reference model 4-VC class priority (`RESP > INV > FWD > REQ`), Lemma L2 FIFO re-issue queueing, and stale grant accept/decline.

4. **Author Comprehensive Final Verification Report**:
   - Write `/home/durgesh/teamwork_projects/clean_room_verification/docs/10_VERIFICATION_REPORT.md` (and copy to `tb_acceptance/docs/10_VERIFICATION_REPORT.md` and workspace root `README.md`) thoroughly addressing Task 0 through Task 8 using the blueprint in M1 Explorer 3's handoff report, including:
     - Task 0: Depth-128 mid-miss analysis, Lemma L1 hazard, Cases A/B/C traces
     - Task 1: SVA Invariant Adaptation (A2.2 split, 42-assertion invariance)
     - Task 2: Reference Model Architecture & Stale Owner Reproduction
     - Task 3: Directed Concurrency Race Tests (Criteria 1-4, cycle 7 INV, cycle 10 INVACK, single M)
     - Task 4: Mutation Matrix Qualification (8 spec-derived mutations, 100% kill rate)
     - Task 5: Deep Formal BMC to K=64 (Bitwuzla run log, 45 assertion cells live, 0 violations, harness assumption justification)
     - Task 6: Lockstep Documentation Sync & Package Gate Verifier (134 checks PASS)
     - Task 7: Directory Receive Path Architecture & Stale Grant Handling (Ruling B7)
     - Task 8: FIFO Re-issue Ordering & Lemma L2 Bounded Progress (Ruling B8)

Write your complete handoff report to:
`/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_worker_m1/handoff.md`
including verification commands, outputs, and evidence.
