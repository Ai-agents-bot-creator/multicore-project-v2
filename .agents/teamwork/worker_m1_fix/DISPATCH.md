# Dispatch: Worker M1 Fix (Remediation)

- Role: teamwork_worker
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m1_fix
- Scope: Execute Milestone 1 Remediation

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_1/report.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2/report.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_3/report.md

Tasks:
1. Revert `rtl/directory/dir_ctrl.sv` back to baseline `4b8cca8381166c83ee61440ee2e45220` by removing `output logic [2:0] rxq_cnt_o,` (line 37) and `assign rxq_cnt_o = rxq_cnt;` (line 661). Verify `md5sum rtl/directory/dir_ctrl.sv` is exactly `4b8cca8381166c83ee61440ee2e45220`.
2. Harden `WAKE_UP.sh`: Add golden baseline MD5 checks in Step 2:
   - `rtl/pkg/tile_pkg.sv`: `b6ece1864f1ce6ddf5b6976775d34485`
   - `rtl/l1/l1_mesi_ctrl.sv`: `d63be56146cfd7f2c9f3682caf918809`
   - `rtl/directory/dir_ctrl.sv`: `4b8cca8381166c83ee61440ee2e45220`
   Fail with non-zero exit code if any source RTL file deviates from the golden hash.
3. Run `./WAKE_UP.sh` in `/mnt/Code/visualstudio/Design-arch_multi-core` and verify all 4 steps report PASS and exit code is 0.
4. Verify bit-for-bit parity:
   - Compare `rtl_frozen/FROZEN.md5` with `~/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5`.
   - Ensure `md5sum -c rtl_frozen/FROZEN.md5` succeeds in both locations.
5. Write handoff report in `handoff.md` and report back via send_message.


## 2026-11-05T18:01:17Z
[Message] timestamp=2026-11-05T18:01:17Z sender=b25d00b4-87e5-4b35-8417-bffe75bad4d9 priority=MESSAGE_PRIORITY_HIGH
Execute the remediation:
1. Revert rtl/directory/dir_ctrl.sv to golden baseline 4b8cca8381166c83ee61440ee2e45220 (remove rxq_cnt_o). Verify md5sum is 4b8cca8381166c83ee61440ee2e45220.
2. Harden WAKE_UP.sh by adding golden baseline verification for source RTL in Step 2:
   - rtl/pkg/tile_pkg.sv == b6ece1864f1ce6ddf5b6976775d34485
   - rtl/l1/l1_mesi_ctrl.sv == d63be56146cfd7f2c9f3682caf918809
   - rtl/directory/dir_ctrl.sv == 4b8cca8381166c83ee61440ee2e45220
3. Run ./WAKE_UP.sh in /mnt/Code/visualstudio/Design-arch_multi-core. Verify all 4 steps pass with exit code 0.
4. Verify bit-for-bit parity of rtl_frozen/FROZEN.md5 between /mnt/Code/visualstudio/Design-arch_multi-core and ~/teamwork_projects/clean_room_verification.
5. Document all commands and results in handoff.md.
6. Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
