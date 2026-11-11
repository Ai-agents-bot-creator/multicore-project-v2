# BRIEFING — 2026-11-09T14:25:00Z

## Mission
Investigate testbench helper `assert_a2_2` in `tb_acceptance/l1_dir/test_l1_dir.py`, formulate generalized code fix across all configured tiles (0..3), verify full regression passes 15/15, and confirm checker rigor.

## 🔒 My Identity
- Archetype: explorer
- Roles: testbench helper fix & full regression strategy
- Working directory: /home/durgesh/teamwork_projects/clean_room_verification
- State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_r2_2/
- Original parent: a51a5a34-58bc-4867-bb5d-12b335e78d2a
- Milestone: M2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in production repo unless testing in working directory, propose clean diff/patch in handoff
- Rigorous verification of assertion A2.2 checker: no loosening, no masking
- Full regression must pass 15/15 tests in tb_acceptance/l1_dir/

## Current Parent
- Conversation ID: a51a5a34-58bc-4867-bb5d-12b335e78d2a
- Updated: 2026-11-09T14:25:00Z

## Investigation State
- **Explored paths**:
  - `tb_acceptance/l1_dir/test_l1_dir.py` (lines 115-230, 650-830)
  - `tb_acceptance/l1_dir/l1_dir_tb_wrapper.sv`
  - `tb_acceptance/ref_model/slice_ref_model.py` (lines 230-245, 630-735)
  - `tb_acceptance/mutations/test_mutations.py`
  - `rtl_frozen/directory/dir_ctrl.sv` (lines 180-210)
- **Key findings**:
  - `assert_a2_2` hardcoded tile 0 and 1 inspection and ignored tiles 2 and 3.
  - In F8 Sub-case D, Tile 2 is the 3rd reader; the directory serves from bank with no transient in DIR_S and sets bit 2. While DATA is in flight, Tile 2 is in `L1_IS_D`. Upon install, Tile 2 is in `L1_S`. Both were omitted by the old helper, causing false `A2_2b VIOLATION`.
  - In `test_f8` Sub-case D, `ref.rule5_shared_data_installation(2, line_c, ...)` was omitted, causing `ref.l1_addr[2]` to remain unset and triggering a secondary scoreboard mismatch.
  - Fix dynamically inspects all configured tiles (`_get_l1_state`, `_get_all_l1_states`), checks all tiles in `strict_holders` and `detected_inflight`, and passes full regression 15/15.
  - Mut-05 negative control is confirmed killed by A2.2a; no loosening or masking occurs.
- **Unexplored areas**: None within the scope of testbench helper and regression.

## Key Decisions Made
- Implemented `_get_l1_state` and `_get_all_l1_states` to dynamically detect all tile states across various wrapper architectures (`u_l1_{t}`, `t{t}_l1_state`, `u_tile[t]`, `tile[t]`).
- Generalized `assert_a2_2` to include all tiles in `strict_holders` for `L1_S` and in `detected_inflight` for release (`L1_I`) or in-flight grant (`L1_IS_D`, `L1_SM_D`).
- Verified full regression passes 15/15 in `tb_acceptance/l1_dir` and 4/4 in `tb_acceptance/mutations`.

## Artifact Index
- DISPATCH.md — Task assignment from orchestrator
- BRIEFING.md — Working memory and status
- progress.md — Liveness log
- handoff.md — Final investigation report
