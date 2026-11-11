## 2026-11-05T17:28:14Z
From: b25d00b4-87e5-4b35-8417-bffe75bad4d9
Priority: MESSAGE_PRIORITY_HIGH

You are spec_miner_survey_1, a teamwork_spec_miner subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Your task:
Read /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md and the authorized white papers:
- /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/FINAL_whitepaper_v3.0.md
- /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SLICE_16_1.md
- /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/WORK_BREAKDOWN_16.md

Extract and document in detail:
1. Slice architecture and slice rules 1 through 11 (MESI state transitions, directory actions, tile_pkg definitions, request/response protocols).
2. Directed test requirements for F1 through F9 (the exact sequence of transactions, L1 cache states, directory states, expected responses, and test intent).
3. Shadow reference model specifications: how slice rules 1-11 must be implemented in a Python cycle-by-cycle model comparing against the DUT.
4. Mutation testing expectations proposed directly from the specification.

Write your findings to:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/report.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/handoff.md

When complete, notify parent (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9) using send_message.
