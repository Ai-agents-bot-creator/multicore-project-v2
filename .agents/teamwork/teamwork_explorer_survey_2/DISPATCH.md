## Dispatch Task — Survey Agent 2 (Reference Model & Directed/Mutation Tests)

Working directory: /home/durgesh/teamwork_projects/clean_room_verification
State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_survey_2/
Original Request file: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md

### Objective
Explore and survey the reference model and test suites:
1. Reference Model in `tb_acceptance/ref_model/slice_ref_model.py`:
   - Inspect receive path and virtual channels (VC0 REQ, VC1 FWD, VC2 RESP, VC3 INV).
   - Check pop priority order: target is `RESP(2) > INV(3) > FWD(1) > REQ(0)`.
   - Check B8.1 re-issued aborted request ordering: target is enter at back of queue (FIFO per Lemma L2).
   - Check termination of accept and decline paths.
2. Directed Upgrade-Race Test Suite:
   - Locate and inspect `test_f_concurrent_upgrade_abort` and `test_f_concurrent_upgrade_decline_reissue`.
   - Check behavior on same-line INVs (immediate abort with INVACK on VC2, completion without stall, exactly one holder in M).
3. Mutation Matrix:
   - Identify mutation test scripts and matrix test cases.
   - Check negative controls: Mut-05, Mut-06, Mut-07, and Mut-08 re-insert at head.
   - Check baseline unmutated execution.
4. Report exact file paths, test commands, current pass/fail status, and details for implementation/verification.

Write your complete findings and handoff report to:
`/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_survey_2/handoff.md`


## 2026-11-09T13:23:13Z
Sender: a51a5a34-58bc-4867-bb5d-12b335e78d2a
Priority: MESSAGE_PRIORITY_HIGH

You are Survey Agent 2 (Reference Model & Directed/Mutation Tests Explorer).

Working directory: /home/durgesh/teamwork_projects/clean_room_verification
State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_survey_2/
Original Request file: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md

You MUST read /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md and /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_survey_2/DISPATCH.md before starting.

Task:
Explore and survey the reference model and test suites:
1. Reference Model in `tb_acceptance/ref_model/slice_ref_model.py`:
   - Inspect receive path and virtual channels (VC0 REQ, VC1 FWD, VC2 RESP, VC3 INV).
   - Check pop priority order: target is `RESP(2) > INV(3) > FWD(1) > REQ(0)`.
   - Check B8.1 re-issued aborted request ordering: target is enter at back of queue (FIFO per Lemma L2).
   - Check termination of accept and decline paths.
2. Directed Upgrade-Race Test Suite:
   - Locate and inspect `test_f_concurrent_upgrade_abort` and `test_f_concurrent_upgrade_decline_reissue`.
   - Check behavior on same-line INVs (immediate abort with INVACK on VC2, completion without stall, exactly one holder in M).
3. Mutation Matrix:
   - Identify mutation test scripts and matrix test cases.
   - Check negative controls: Mut-05, Mut-06, Mut-07, and Mut-08 re-insert at head.
   - Check baseline unmutated execution.
4. Report exact file paths, test commands, current pass/fail status, and details for implementation/verification.

Write your complete findings and handoff report to:
/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_survey_2/handoff.md

Once complete, notify me via send_message with a brief message pointing to your report.
