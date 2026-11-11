# Dispatch: Challenger M2-2

- Role: teamwork_challenger
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m2_2
- Milestone: M2 (Directed Tests F1-F8 & Shadow Reference Model)

Empirical Challenge Scope:
1. Empirically verify `slice_ref_model.py`:
   - Test all 11 shadow rules programmatically with edge case stimulus.
   - Inject intentional state corruptions into the reference model and verify `compare_l1`, `compare_dir`, and `compare_bank` detect them and increment `mismatch_count`.
2. Check clean-room isolation boundary: verify zero test code was copied from `tb/` or `tb_self_test/`.
3. Confirm empirical correctness and report findings.

Write your verdict in `handoff.md`.
Report back via send_message.
## 2026-11-05T18:34:35Z
You are challenger_m2_2, a teamwork_challenger subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m2_2

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m2_2/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m2/handoff.md

Empirically test slice_ref_model.py:
1. Exercise all 11 shadow rules with unit stimulus.
2. In a temporary subshell, inject intentional state corruption and verify scoreboard compare methods detect it and record mismatches.
3. Verify clean-room isolation boundary.

Write your findings and verdict in handoff.md.
Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
