## 2026-11-05T17:28:22Z
You are spec_miner_survey_2, a teamwork_spec_miner subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_2

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.

Your task:
Read /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md and the authorized specification files:
- /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/RULINGS_B1_B2_B4.md
- /mnt/Code/visualstudio/Design-arch_multi-core/docs/01_DECISION_LOG.md
- /mnt/Code/visualstudio/Design-arch_multi-core/docs/04_TECH_STACK.md
- /mnt/Code/visualstudio/Design-arch_multi-core/BUILD_ORDER.md

Extract and document in detail:
1. SystemVerilog Assertions requirements: A1.1, A1.2, A1.3, A2.2, A2.6, A3.1, A7.x (clauses, formal definitions, expected invariants).
2. Formal Bounded Model Checking (BMC) at depth K=64 with SymbiYosys (`sby`): requirements, engines, properties, clocks/resets assumptions.
3. Rulings B1, B2, B4: exact architectural rulings and how they constrain the design / verification.
4. Toolchain and tech stack versions and requirements: cocotb 2.1.0, iverilog 13.0, python environment, sby options.
5. Mutation testing requirements derived from spec rules and invariants.

Write your findings to:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_2/report.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_2/handoff.md

When complete, notify parent (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9) using send_message.
