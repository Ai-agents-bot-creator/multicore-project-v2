# Dispatch Assignment: Worker M1 (Setup and Isolation)

- Role: teamwork_worker
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m1
- Scope: Milestone 1 (Setup and Clean-Room Isolation)

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from `tb/self_test/`, `tb/l1_dir/`, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Authorized references to read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_survey_3/report.md

Exclusive Write Ownership:
- `/mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh`
- `/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/`
- `/mnt/Code/visualstudio/Design-arch_multi-core/tb_self_test/`
- `~/teamwork_projects/clean_room_verification/`

TASKS:
1. In `/mnt/Code/visualstudio/Design-arch_multi-core`:
   - Create `WAKE_UP.sh` with executable permissions (`chmod +x WAKE_UP.sh`).
   - The script must perform 4 clean reset steps:
     Step 1: Check `md5sum pd/v1/verify_patch_set.py` against `4c4370f50882e82399b65076147bf112`. Fail if mismatch.
     Step 2: Snapshot `rtl/pkg/tile_pkg.sv`, `rtl/l1/l1_mesi_ctrl.sv`, `rtl/directory/dir_ctrl.sv` into `rtl_frozen/` and generate `rtl_frozen/FROZEN.md5`.
     Step 3: Quarantine existing self-tests: ensure `tb_self_test/` exists, move `tb/l1_dir` into `tb_self_test/l1_dir` (handling idempotency if already moved), and create `tb_self_test/README.md` explaining clean-room quarantine.
     Step 4: Verify `md5sum -c rtl_frozen/FROZEN.md5` passes.
   - Run `./WAKE_UP.sh` and verify it runs cleanly to completion with exit code 0.
2. In `~/teamwork_projects/clean_room_verification`:
   - Create directory `~/teamwork_projects/clean_room_verification` (and subdirectories `white_papers/final/`, `docs/`, `rtl_frozen/`).
   - Copy only the authorized specification files:
     - `white_papers/final/FINAL_whitepaper_v3.0.md`
     - `white_papers/final/SLICE_16_1.md`
     - `white_papers/final/WORK_BREAKDOWN_16.md`
     - `white_papers/final/RULINGS_B1_B2_B4.md`
     - `docs/01_DECISION_LOG.md`
     - `docs/04_TECH_STACK.md`
     - `BUILD_ORDER.md`
   - Copy `rtl_frozen/` and `rtl_frozen/FROZEN.md5`.
   - Verify `cd ~/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5` passes.
   - Verify that NO files from `tb_self_test/` or `tb/` or scratch directories were copied.
3. Document all commands executed and results in `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m1/handoff.md`.
4. Report back with `send_message`.


## 2026-11-05T17:36:59Z
You are worker_m1, a teamwork_worker subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Read your task assignment in:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m1/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md

Implement Milestone 1:
1. In /mnt/Code/visualstudio/Design-arch_multi-core:
   - Create executable WAKE_UP.sh (4-step reset script: verify pd/v1/verify_patch_set.py md5 == 4c4370f50882e82399b65076147bf112; snapshot rtl/pkg/tile_pkg.sv, rtl/l1/l1_mesi_ctrl.sv, rtl/directory/dir_ctrl.sv into rtl_frozen/ and generate rtl_frozen/FROZEN.md5; quarantine tb/l1_dir into tb_self_test/l1_dir and create tb_self_test/README.md; verify md5sum -c rtl_frozen/FROZEN.md5).
   - Execute ./WAKE_UP.sh and confirm it passes.
2. In ~/teamwork_projects/clean_room_verification:
   - Create the directory structure.
   - Copy ONLY authorized specification files:
     white_papers/final/FINAL_whitepaper_v3.0.md, SLICE_16_1.md, WORK_BREAKDOWN_16.md, RULINGS_B1_B2_B4.md, docs/01_DECISION_LOG.md, docs/04_TECH_STACK.md, BUILD_ORDER.md.
   - Copy rtl_frozen/ and rtl_frozen/FROZEN.md5.
   - Verify md5sum -c rtl_frozen/FROZEN.md5 in ~/teamwork_projects/clean_room_verification passes.
   - Verify no files from tb/ or tb_self_test/ were copied.
3. Write your report and hard handoff in /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m1/handoff.md.
4. Notify orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9) via send_message.
