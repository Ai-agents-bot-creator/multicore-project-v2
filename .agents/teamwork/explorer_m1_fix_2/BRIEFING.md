# BRIEFING — 2026-11-05T18:12:00Z

## Mission
Analyze WAKE_UP.sh and design a hardening mechanism so Step 2 validates source RTL against golden baseline hashes before snapshotting.

## 🔒 My Identity
- Archetype: explorer
- Roles: teamwork_explorer
- Working directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2
- Original parent: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Milestone: Milestone 1 (M1 Fix 2)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify project source code
- CRITICAL CLEAN-ROOM RESTRICTION: The team must NOT read or inspect test source code from tb/self_test/, tb/l1_dir/, or any scratch test directories. The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification.
- Output reports must be written only to working directory (.agents/teamwork/explorer_m1_fix_2/)
- Report back via send_message to orchestrator (conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9)

## Current Parent
- Conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Updated: 2026-11-05T17:55:00Z

## Investigation State
- **Explored paths**:
  - `WAKE_UP.sh` (identified vulnerability: dynamic checksum regeneration without baseline comparison)
  - `PROJECT.md` & `ORIGINAL_REQUEST.md` (clean-room requirements, invariant specifications)
  - `challenger_m1_1/handoff.md` (reproduced findings on `dir_ctrl.sv` drift: `acc52411a8b20d2c82771d4c8a28e187` vs golden `4b8cca8381166c83ee61440ee2e45220`)
  - `clean_room_verification/rtl_frozen/` (confirmed golden baseline hashes)
- **Key findings**:
  - `rtl/directory/dir_ctrl.sv` drift caused by addition of `rxq_cnt_o` (lines 37 and 661). Removing these lines restores MD5 `4b8cca8381166c83ee61440ee2e45220`.
  - Hardening Step 2 before snapshotting stops invalid RTL from contaminating `rtl_frozen/`.
  - Standalone sandbox testing confirmed exit code 1 on drift and exit code 0 on clean golden state with idempotency across 3 runs.
- **Unexplored areas**: None for M1 Fix 2.

## Key Decisions Made
- Validated golden baseline hashes:
  - `tile_pkg.sv`: `b6ece1864f1ce6ddf5b6976775d34485`
  - `l1_mesi_ctrl.sv`: `d63be56146cfd7f2c9f3682caf918809`
  - `dir_ctrl.sv`: `4b8cca8381166c83ee61440ee2e45220`
- Designed pre-snapshot validation loop in Step 2 with formatted diagnostic messages matching Step 1.
- Documented remediation instructions and diff patch for implementer agent in `report.md` and `handoff.md`.

## Artifact Index
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2/BRIEFING.md — Persistent situational awareness
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2/progress.md — Liveness heartbeat
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2/report.md — Detailed analysis report
- /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2/handoff.md — 5-component handoff report
