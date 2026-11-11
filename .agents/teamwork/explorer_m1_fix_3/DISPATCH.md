# Dispatch: Explorer M1 Fix 3

- Role: teamwork_explorer
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_3
- Target: Milestone 1 Workspace Synchronization and Re-verification Procedure

Context:
Milestone 1 gate check failed due to desynchronization between `/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen` and `~/teamwork_projects/clean_room_verification/rtl_frozen`.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m1_2/handoff.md

Tasks:
1. Formulate the end-to-end remediation procedure for a fresh worker to execute:
   - Reverting `rtl/directory/dir_ctrl.sv` to baseline `4b8cca8381166c83ee61440ee2e45220`
   - Hardening `WAKE_UP.sh` with golden RTL hash checking
   - Re-running `WAKE_UP.sh` in `/mnt/Code/visualstudio/Design-arch_multi-core`
   - Re-verifying `md5sum -c rtl_frozen/FROZEN.md5` in both repositories
   - Verifying identical checksums across both repos
2. Do NOT implement changes (Explorer is read-only). Write recommendations in report.md and handoff.md.
3. Report back via send_message.


## 2026-11-05T17:54:35Z
You are explorer_m1_fix_3, a teamwork_explorer subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_3

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_3/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m1_2/handoff.md

Design the end-to-end synchronization and re-verification workflow for the worker to ensure bit-for-bit parity across /mnt/Code/visualstudio/Design-arch_multi-core and ~/teamwork_projects/clean_room_verification without violating clean-room isolation. Do not edit files yourself.
Write report.md and handoff.md in your working directory.
Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
