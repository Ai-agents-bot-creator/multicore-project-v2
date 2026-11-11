# Dispatch: Explorer M1 Fix 2

- Role: teamwork_explorer
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2
- Target: Milestone 1 WAKE_UP.sh Hardening Strategy

Context:
Milestone 1 reviewers and challengers noted that `WAKE_UP.sh` dynamically overwrites `rtl_frozen/` and `FROZEN.md5` without comparing against immutable golden baseline hashes.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m1_1/handoff.md

Tasks:
1. Analyze `WAKE_UP.sh` implementation.
2. Recommend how to harden Step 2 or Step 4 of `WAKE_UP.sh` to validate the source RTL files against the golden baseline hashes:
   - `rtl/pkg/tile_pkg.sv`: `b6ece1864f1ce6ddf5b6976775d34485`
   - `rtl/l1/l1_mesi_ctrl.sv`: `d63be56146cfd7f2c9f3682caf918809`
   - `rtl/directory/dir_ctrl.sv`: `4b8cca8381166c83ee61440ee2e45220`
3. Do NOT implement changes (Explorer is read-only). Write recommendations in report.md and handoff.md.
4. Report back via send_message.


## 2026-11-05T17:54:25Z
From: b25d00b4-87e5-4b35-8417-bffe75bad4d9
Content:
You are explorer_m1_fix_2, a teamwork_explorer subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m1_1/handoff.md

Analyze WAKE_UP.sh and design a hardening mechanism so Step 2 validates the source RTL against golden baseline hashes (tile_pkg: b6ece1864f1ce6ddf5b6976775d34485, l1_mesi_ctrl: d63be56146cfd7f2c9f3682caf918809, dir_ctrl: 4b8cca8381166c83ee61440ee2e45220) before snapshotting. Do not edit files yourself.
Write report.md and handoff.md in your working directory.
Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
