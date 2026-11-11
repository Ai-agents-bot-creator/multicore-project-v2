# Dispatch Assignment: Worker M2 (Directed Tests F1-F8 & Shadow Reference Model)

- Role: teamwork_worker
- Working Directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m2
- Scope: Milestone 2 in `~/teamwork_projects/clean_room_verification`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from `tb/self_test/`, `tb/l1_dir/`, or any scratch test directories. The frozen RTL in `~/teamwork_projects/clean_room_verification/rtl_frozen/` is a read-only black box. Violating this will invalidate clean-room verification.

Authorized References to Consult:
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md`
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/report.md`
- Authorized spec files in `~/teamwork_projects/clean_room_verification/`:
  - `white_papers/final/SLICE_16_1.md`
  - `white_papers/final/FINAL_whitepaper_v3.0.md`
  - `white_papers/final/RULINGS_B1_B2_B4.md`
  - `docs/04_TECH_STACK.md`
  - `rtl_frozen/pkg/tile_pkg.sv`
  - `rtl_frozen/l1/l1_mesi_ctrl.sv`
  - `rtl_frozen/directory/dir_ctrl.sv`

Exclusive Write Ownership:
- `~/teamwork_projects/clean_room_verification/tb_acceptance/ref_model/`
- `~/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/`

Tasks:
1. In `~/teamwork_projects/clean_room_verification/tb_acceptance/ref_model/`:
   - Build `slice_ref_model.py`: Python shadow reference model strictly implementing Slice 16.1 Rules 1–11 (`SLICE_16_1.md` §4, `report.md` §1.4).
   - Maintain tile L1 state (I, S, E, M, transients), Directory state (`DIR_I`, `DIR_S`, `DIR_E`, `DIR_M`, `DIR_FWD_WAIT`, `DIR_MEM_WAIT`, etc.), DTR registers, home bank arrays, and scoreboard comparison methods.
   - Implement cycle-by-cycle / transaction tracking and report `mismatch_count` (target: 0).
2. In `~/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/`:
   - Build clean-room directed tests F1 through F8 using cocotb 2.1.0 and iverilog 13.0:
     - F1: Forward, Clean Owner (E -> S downgrade, clean DATAFWD, DATA excl=0, UNBLOCK -> DIR_S)
     - F2: Forward, Dirty Owner (M -> I downgrade, dirty DATAFWD, DATA excl=1, UNBLOCK -> DIR_M)
     - F3: Forward, GETS from DIR_M (M -> S downgrade, dirty DATAFWD, dirty bank write, DATA excl=0, UNBLOCK -> DIR_S)
     - F4: Forward, GETM from DIR_E (E -> I downgrade, clean DATAFWD, DATA excl=1, UNBLOCK -> DIR_M)
     - F5: Silent Upgrade then Eviction (E -> M locally, PUTM to DIR_E, bank dirty, PUTACK -> I)
     - F6: Evict-During-Forward, Clean Owner (PUTS arriving in DIR_FWD_WAIT, forward cancellation, defensive INVACK ignored, bank serves requester -> DIR_S)
     - F7: Evict-During-Forward, Dirty Owner (PUTM arriving in DIR_FWD_WAIT, forward data obligation satisfied, PUTACK, DATA excl=1 -> DIR_M)
     - F8: Exclusive-Bit Correctness (sub-cases A, B, C, D verifying bit [38] sole-holder rule)
   - Construct testbench wrapper and Makefile using iverilog 13.0 (`-g2012`) and cocotb 2.1.0.
   - Note: Recommended PATH: `export PATH="/home/durgesh/.local/share/pipx/venvs/cocotb/bin:/usr/bin:/home/durgesh/.local/oss-cad-suite/bin:$PATH"`.
   - In cocotb 2.1.0: use `await Timer(1, unit="ps")` (not `units=`), cast `LogicArray` properly, do not use removed binary module.
3. Run directed tests F1 through F8 against the frozen RTL and record execution results and scoreboard mismatch counts against the shadow reference model.
4. Document all results and commands in `handoff.md` and report back via send_message.


## 2026-11-05T18:15:13Z
You are worker_m2, a teamwork_worker subagent.
Your working directory is: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL CLEAN-ROOM RESTRICTION:
The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL in ~/teamwork_projects/clean_room_verification/rtl_frozen/ is a read-only black box. Violating this will invalidate the clean-room verification.

Read:
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_m2/DISPATCH.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
- /mnt/Code/visualstudio/Design-arch_multi-core/PROJECT.md
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/report.md

Implement Milestone 2 in ~/teamwork_projects/clean_room_verification:
1. Build tb_acceptance/ref_model/slice_ref_model.py implementing Slice Rules 1–11.
2. Build tb_acceptance/l1_dir/ directed tests F1 through F8 with cocotb 2.1.0 and iverilog 13.0, integrated with the shadow reference model.
3. Run the tests, record execution outcomes and reference model cycle-by-cycle / transaction mismatch counts.
4. Document all commands, code files, and results in handoff.md.
5. Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9).
