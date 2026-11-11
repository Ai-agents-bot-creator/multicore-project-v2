# BRIEFING — 2026-11-05T17:35:15Z

## Mission
Survey, mine, and rigorously document formal SVA requirements (A1.1, A1.2, A1.3, A2.2, A2.6, A3.1, A7.x), SymbiYosys BMC depth K=64 setup, architectural rulings B1/B2/B4, toolchain/tech stack specs, and mutation testing requirements under clean-room restrictions.

## 🔒 My Identity
- Archetype: teamwork_spec_miner
- Roles: SPECIFICATION MINER
- Working directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_2
- Original parent: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Milestone: spec_mining_phase_1

## 🔒 Key Constraints
- CRITICAL CLEAN-ROOM RESTRICTION: The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.
- Sole job is to discover and document features by probing authoritative specification; do NOT implement anything (read-only regarding implementation/tests).
- Output files must be written only to working directory: `.agents/teamwork/spec_miner_survey_2/report.md` and `.agents/teamwork/spec_miner_survey_2/handoff.md`.
- Liveness heartbeat updated in `progress.md`.

## Current Parent
- Conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Updated: 2026-11-05T17:35:15Z

## Task Summary
- **What to build**: Specification discovery report detailing SystemVerilog Assertions (A1.1, A1.2, A1.3, A2.2, A2.6, A3.1, A7.x), SymbiYosys BMC K=64 formal verification, Rulings B1/B2/B4, Tech stack (cocotb 2.1.0, iverilog 13.0, python, sby), and mutation testing requirements.
- **Success criteria**: Complete and detailed extraction in report.md and handoff.md, referencing authoritative specification documents.
- **Interface contracts**: Authorized specs: ORIGINAL_REQUEST.md, FINAL_whitepaper_v3.0.md, RULINGS_B1_B2_B4.md, docs/01_DECISION_LOG.md, docs/04_TECH_STACK.md, BUILD_ORDER.md.
- **Code layout**: Pure metadata in `.agents/teamwork/spec_miner_survey_2/`.

## Key Decisions Made
- Strictly respected clean-room boundaries; zero access to tb/self_test/, tb/l1_dir/, or scratch test directories.
- Extracted and fully defined SVA assertions A1.1, A1.2, A1.3, A2.2, A2.6, A3.1, A7.x with formal mathematical invariants and protocol triggers.
- Fully derived BMC K=64 horizon and documented SymbiYosys engines, options, and clock/reset requirements.
- Analyzed and synthesized Rulings B1, B2, B4 and their precise RTL/verification constraints.
- Catalogued cocotb 2.1.0 LogicArray/Timer requirements, iverilog 13.0 flags, and constructed an 8-row spec-derived mutation matrix with positive and dual negative controls.

## Artifact Index
- DISPATCH.md — Initial dispatch prompt
- BRIEFING.md — Working memory & state
- progress.md — Liveness heartbeat & task tracking
- report.md — Complete specification mining report
- handoff.md — Standard 5-component handoff report
