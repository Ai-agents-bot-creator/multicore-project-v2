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