# Dispatch: Challenger M2-1

- Role: teamwork_challenger
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m2_1
- Milestone: M2 (Directed Tests F1-F8 & Shadow Reference Model)

Empirical Challenge Scope:
1. Empirically verify the directed tests in `~/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir`:
   - Run `make clean && make` with cocotb 2.1.0 + iverilog 13.0.
   - Verify every test F1 to F8 passes cleanly.
2. Adversarial stress test the testbench or stimulus:
   - In a temporary subshell, inject an intentional mismatch into stimulus or expectations and verify that the testbench actually catches it and reports FAIL (i.e. proves the test suite is not a no-op/always-pass facade).
3. Confirm empirical correctness and report findings.

Write your verdict in `handoff.md`.
Report back via send_message.
## 2026-11-05T18:34:28Z
You are challenger_m2_1, a teamwork_challenger subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m2_1

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m2_1/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m2/handoff.md

Empirically test directed test suite:
1. Run tests with cocotb 2.1.0 + iverilog 13.0.
2. In a temporary subshell, inject an intentional mismatch into stimulus or expected state to prove the testbench is sensitive and genuinely fails.

Write your findings and verdict in handoff.md.
Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
