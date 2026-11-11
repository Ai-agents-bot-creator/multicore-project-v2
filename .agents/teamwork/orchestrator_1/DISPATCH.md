## 2026-11-09T13:21:16Z
For the testbench/verification agent working in /home/durgesh/teamwork_projects/clean_room_verification: execute production clean-room verification for the multi-core cache hierarchy under Ruling B7 and B8, completing the formal BMC to full depth K=64 and compiling the final verification report.

Working directory: /home/durgesh/teamwork_projects/clean_room_verification
Integrity mode: development

## Requirements

### R1. Complete Formal BMC to Depth K=64
Execute SymbiYosys formal BMC on the clean-room SVA suite to the full depth of K=64 steps. Verify that all 45 assertion cells remain live without vacuity and that zero violations occur. Incorporate and document the formal harness assumption `assume(UNBLOCK from req_tile → L1 state ∈ {S,E,M})` justified by citation to the L1 protocol specification.

### R2. Reference Model 4-VC Priority and Re-issue Ordering Verification
Verify that the reference model in `tb_acceptance/ref_model/slice_ref_model.py` maintains four distinct virtual channels (VC0 REQ, VC1 FWD, VC2 RESP, VC3 INV) with pop priority strictly ordered as `RESP(2) > INV(3) > FWD(1) > REQ(0)`. Confirm that B8.1 re-issued aborted requests enter at the back of the queue (FIFO ordering per Lemma L2) without livelock or starvation, and that both the accept and decline paths terminate cleanly.

### R3. Mutation Matrix and Directed Test Suite Execution
Execute the directed upgrade-race tests (`test_f_concurrent_upgrade_abort` and `test_f_concurrent_upgrade_decline_reissue`) to confirm that same-line INVs trigger an immediate abort with INVACK on VC2, complete without stalling, and terminate with exactly one holder in M. Confirm that the derived mutation matrix (count derived from tests) passes all negative controls (including Mut-05, Mut-06, Mut-07, and Mut-08 re-insert at head) while the unmutated baseline passes.

### R4. Lockstep Documentation and Comprehensive Reporting
Confirm that `docs/` and `tb_acceptance/docs/` reflect Ruling B8 and ledger rows AH, AI, AJ copied verbatim from the specification, and that the package verifier passes 134 checks cleanly. Provide the complete report addressing all items from Task 0 through Task 8 with trace and test evidence.

## Verification Resources
- Use the existing verification scripts, testbenches, and harnesses in the workspace and repository (`apply_b78_repo.py`, `verify_landing.py`, `tb_acceptance/`, and `pd/v1/verify_patch_set.py`).

## Acceptance Criteria

### Formal BMC and Assertions
- [ ] Formal BMC reaches full depth K = 64 with 45 live assertion cells and 0 violations reported.
- [ ] SVA assertion count remains strictly 42 across existing categories (A2.x, A3.x, A7.x).
- [ ] Formal harness assumption `assume(UNBLOCK from req_tile → L1 state ∈ {S,E,M})` is documented and justified by protocol citation.

### Reference Model and Directed Tests
- [ ] Reference model directory receive path uses 4 queues popped in priority order `RESP > INV > FWD > REQ`.
- [ ] Directed tests for both the accept and decline paths pass with exactly one tile in M.
- [ ] Mutation matrix derived count matches matrix tests with all negative controls passing and baseline unmutated passing.

### Package Gate and Documentation
- [ ] Package verifier runs 134 checks and passes (`RESULT: PASS`).
- [ ] Decision log, problem log, verification plan, and scratchpad updated in lockstep with rows AH, AI, and AJ verbatim.
- [ ] Final report delivers answers and supporting evidence for Task 0 through Task 8.

---

Orchestrator Coordination Details:
Working directory: /home/durgesh/teamwork_projects/clean_room_verification
State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/orchestrator_1/
Original Request file: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md


## 2026-11-09T13:28:09Z

## Task: Deep Verify, Question, and Improve the SRS for a Cache-Coherent Tiled Mesh Multicore

### Context

The project is a **cache-coherent tiled mesh multicore** system — directory-based MESI coherence, 2D mesh with XY routing, 4 virtual channels, wormhole switching, credit-based flow control. There's a 2×2 committed FPGA build and a 4×4 simulation-only track.

### Files and Locations

- **SRS document (DOCX):** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx`
- **SRS template (DOCX):** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/SRS/SRS_Template_final.docx`
- **SRS template student guide (PDF):** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/SRS/SRS Template Student Guide.pdf`
- **Previous SRS review:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_REVIEW.md`
- **Verification script:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py`
- **Whitepaper (the ground truth spec):** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/FINAL_whitepaper_v3.0.md`
- **Spec sheet:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SPEC_SHEET.md`
- **HLD/LLD documents:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/HLD_LLD_4x4_architecture.md` and `HLD_LLD_2x2_FPGA.md`
- **Work breakdown:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/WORK_BREAKDOWN_16.md`
- **Slice doc:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SLICE_16_1.md`
- **Rulings:** `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/RULINGS_B1_B2_B4.md`, `RULINGS_B7.md`, `RULINGS_B8.md`

### Current Status

The SRS (`SRS_final.docx`) currently **passes all 41/41 automated verification checks** in `verify_srs.py`. A prior review found 6 blocker, 6 major, and 6 minor defects — all have been fixed. The SRS is at v0.2.

### What You Must Do

1. **Read the SRS DOCX** (use python-docx to extract all content including tables), the **template** (DOCX), the **student guide** (PDF), and the **whitepaper** (the ground truth spec). Compare the SRS against both the template structure and the whitepaper's normative content.

2. **Deep Verify the SRS** against the whitepaper:
   - Check every functional requirement (FR-01 through FR-14) against the whitepaper's rules and protocol descriptions
   - Verify all performance, area, and interface requirements match the whitepaper's numbers exactly
   - Check that the VC mapping, message set, FSM states, assertion IDs, and test plan all align with the whitepaper
   - Verify the signal list is complete and correct for both 2×2 and 4×4 builds
   - Check traceability matrix completeness — every requirement must trace to verification evidence
   - Look for any remaining inconsistencies, phantom references, or technical errors

3. **Use the internet to question the SRS** — research best practices for:
   - Directory-based MESI coherence protocol SRS documents
   - IEEE 830 / ISO/IEC/IEEE 29148 SRS standards compliance
   - Cache coherence verification methodologies (formal verification, SVA, coverage-driven)
   - FPGA validation requirements for NoC/mesh architectures
   - Industry-standard SRS structure for hardware/RTL projects
   Compare the SRS against these standards and identify gaps.

4. **Improve the SRS** — produce a corrected, improved DOCX file:
   - Fix any errors found in steps 2-3
   - Add any missing sections or requirements identified by standards comparison
   - Improve clarity, completeness, and testability of requirements
   - Ensure all tables are properly formatted with no duplicates
   - Fill in any remaining placeholders where the whitepaper provides the data
   - Output the improved SRS as a new DOCX file at `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final_v2.docx`

5. **Update the verification script** if needed to cover any new checks, and run it against the improved SRS to confirm it passes.

6. **Produce a review report** documenting all findings, changes made, and remaining open items.

### Skills to Use

- `/technical-writing` skill at `/home/durgesh/.gemini/config/skills/technical-writing/SKILL.md`
- `/system-design` skill at `/home/durgesh/.gemini/config/skills/system-design/SKILL.md`  
- `/docx` skill at `/home/durgesh/.gemini/config/skills/docx/SKILL.md`
- `/deep-research` skill at `/home/durgesh/.gemini/config/skills/deep-research/SKILL.md`

### Execution Details
- Working directory: `/mnt/Code/visualstudio/Design-arch_multi-core`
- State folder: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/orchestrator_1`
- Original request path: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md`
