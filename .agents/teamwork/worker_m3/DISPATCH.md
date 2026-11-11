# Dispatch Assignment: Worker M3 (SVA & Formal BMC at K=64)

- Role: teamwork_worker
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m3
- Scope: Milestone 3 in `~/teamwork_projects/clean_room_verification`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from `tb/self_test/`, `tb/l1_dir/`, or any scratch test directories. The frozen RTL in `~/teamwork_projects/clean_room_verification/rtl_frozen/` is a read-only black box. Violating this will invalidate clean-room verification.

Authorized References to Consult:
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md`
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_2/report.md`
- Authorized specs in `~/teamwork_projects/clean_room_verification/`:
  - `white_papers/final/SLICE_16_1.md`
  - `white_papers/final/FINAL_whitepaper_v3.0.md`
  - `white_papers/final/RULINGS_B1_B2_B4.md`
  - `docs/04_TECH_STACK.md`
  - `rtl_frozen/pkg/tile_pkg.sv`
  - `rtl_frozen/l1/l1_mesi_ctrl.sv`
  - `rtl_frozen/directory/dir_ctrl.sv`

Exclusive Write Ownership:
- `~/teamwork_projects/clean_room_verification/tb_acceptance/sva/`

Tasks:
1. In `~/teamwork_projects/clean_room_verification/tb_acceptance/sva/`:
   - Implement SystemVerilog Assertions module (`cache_coherence_sva.sv`) covering:
     - A1.1: Single Writer Multiple Readers (SWMR)
     - A1.2: Exclusive Exclusivity
     - A1.3: Shared Validity (no E or M alongside S)
     - A2.2: Directory Sharer Accuracy
     - A2.6: Directory Owner Qualification and Alignment
     - A3.1: Virtual Channel Preservation and Invariance
     - A7.x: State Machine Legality, Single-Exit on UNBLOCK, Successor Selection Determinism
   - Implement formal verification harness (`sva_formal_top.sv`) instantiating the frozen RTL with 100MHz clock, reset, and legal protocol stimulus assumptions.
   - Implement SymbiYosys configuration (`cache_sva.sby`):
     - Mode: `bmc`
     - Depth: `64`
     - Engine: `smtbmc z3` (or `smtbmc boolector`)
     - Script: use `read_slang` with Yosys for SystemVerilog AST parsing.
     - Note: Recommended PATH: `export PATH="/usr/bin:/home/durgesh/.local/oss-cad-suite/bin:$PATH"`
2. Execute `sby -f cache_sva.sby` at depth K=64.
3. Capture the raw SymbiYosys output log in `~/teamwork_projects/clean_room_verification/tb_acceptance/sva/sby_output.log`.
4. Document all commands, assertion definitions, and formal BMC results in `handoff.md`.
5. Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).

## 2026-11-05T18:42:52Z
You are worker_m3, a teamwork_worker subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m3

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL in ~/teamwork_projects/clean_room_verification/rtl_frozen/ is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m3/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_2/report.md

Implement Milestone 3 in ~/teamwork_projects/clean_room_verification:
1. In tb_acceptance/sva/, build cache_coherence_sva.sv covering assertions:
   - A1.1 (SWMR), A1.2 (Exclusivity), A1.3 (Shared validity)
   - A2.2 (Sharer precision), A2.6 (Owner in sharers)
   - A3.1 (VC preservation)
   - A7.x (State machine legality, single-exit on UNBLOCK, successor determinism)
2. Build formal top harness sva_formal_top.sv and SymbiYosys configuration cache_sva.sby at depth K=64 using read_slang and SMT solver.
3. Execute `sby -f cache_sva.sby` at depth K=64 and capture raw output in tb_acceptance/sva/sby_output.log.
4. Document all commands, assertion definitions, and formal verification results in handoff.md.
5. Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
