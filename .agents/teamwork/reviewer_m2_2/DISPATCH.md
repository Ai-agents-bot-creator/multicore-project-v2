# Dispatch: Reviewer M2-2

- Role: teamwork_reviewer
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m2_2
- Milestone: M2 (Directed Tests F1-F8 & Shadow Reference Model)

Review Scope:
Verify that `slice_ref_model.py` in `~/teamwork_projects/clean_room_verification/tb_acceptance/ref_model/`:
1. Faithfully implements Slice 16.1 Rules 1–11.
2. Evaluates cycle-by-cycle / transaction states and reports mismatch count (target: 0).
3. Test imports and self-test verification:
   `python3 -c "import sys; sys.path.insert(0, '/home/durgesh/teamwork_projects/clean_room_verification'); from tb_acceptance.ref_model import SliceRefModel; m = SliceRefModel(); assert m.report()['mismatch_count'] == 0; print('REF_MODEL_OK')"`
4. Verify frozen RTL snapshot was not modified (`md5sum -c rtl_frozen/FROZEN.md5`).

Write your verdict (APPROVE or REQUEST_CHANGES) in `handoff.md`.
Report back via send_message.

## 2026-11-05T18:34:20Z
You are reviewer_m2_2, a teamwork_reviewer subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m2_2

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_m2_2/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m2/handoff.md

Verify shadow reference model in ~/teamwork_projects/clean_room_verification/tb_acceptance/ref_model/:
1. Verify slice_ref_model.py against Slice Rules 1–11.
2. Verify self-test execution (0 mismatches).
3. Verify md5sum -c rtl_frozen/FROZEN.md5 passes.

Write your verdict (APPROVE or REQUEST_CHANGES) in handoff.md.
Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
