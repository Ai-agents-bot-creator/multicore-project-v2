# BRIEFING — 2026-11-05T19:42:00Z

## Mission
Investigate Assertion A3.1 failure and packet framing, and design a concrete, Slang-synthesizable fix strategy for packet flit sequence tracking.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, synthesis, read-only investigation
- Working directory: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_fix_2
- Original parent: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Milestone: Milestone 3 Remediation (Assertion A3.1 Framing Fix)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strictly observe clean-room isolation: NEVER read, copy, or inspect any files from `/mnt/Code/visualstudio/Design-arch_multi-core/tb/self_test/`, `/mnt/Code/visualstudio/Design-arch_multi-core/tb/l1_dir/`, or scratch directories. The frozen RTL in `rtl_frozen/` is a read-only black box.
- Output path discipline: write only to `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m3_fix_2`

## Current Parent
- Conversation ID: b25d00b4-87e5-4b35-8417-bffe75bad4d9
- Updated: 2026-11-05T19:30:48Z

## Investigation State
- **Explored paths**:
  - `rtl_frozen/pkg/tile_pkg.sv`: flit framing encodings, `HDR_HEAD` (41), `HDR_TAIL` (40), `HDR_LEN` (37:32), `msg_to_len()`, `msg_to_vc()`
  - `rtl_frozen/l1/l1_mesi_ctrl.sv`: lines 126-140 (`mk_hdr`), 523-544 (TX flit output)
  - `rtl_frozen/directory/dir_ctrl.sv`: lines 115-126 (`mk_hdr`), 620-642 (TX flit output)
  - `tb_acceptance/sva/cache_coherence_sva.sv`: lines 110-125 (A3.1 un-framed evaluations)
  - `tb_acceptance/sva/sva_formal_top.sv`: egress interconnect, FIFO arbiter, response demux
- **Key findings**:
  - A3.1 failure root cause: Assertion A3.1 checks `flit[HDR_HEAD]` unconditionally without tracking packet flit index. In multi-flit packets (9 flits: DATA, PUTM, DATAFWD), body flits 1..8 contain raw 64-bit cache line data. Bit 41 (`HDR_HEAD`) in payload data triggers false header evaluations.
  - Body flit 8 does NOT have `HDR_TAIL` injected; bit 40 is data payload. `HDR_TAIL` is only present on Flit 0 of 1-flit packets (`len == 1`).
  - Sequence tracker must use packed 2D registers (`logic [TILE_COUNT-1:0][3:0] l1_req_rem`, `logic [3:0] dir_rsp_rem`) to ensure Yosys synthesizes DFFs rather than unwritten `$mem_v2` memory cells.
  - SBY empirical proof: Validated with Boolector BMC. Zero false alarms on payload bit 41=1, while catching true VC mutations at step 3.
- **Unexplored areas**: None. Remediation plan fully confirmed.

## Key Decisions Made
- Down-counter `flit_rem` (4-bit) chosen: handles 1-flit and 9-flit packets symmetrically with a single register.
- Packed 2D vectors chosen to avoid Yosys memory inference.
- Assertion A3.1 guarded by `(rem == 0) && flit[HDR_HEAD]`.

## Artifact Index
- DISPATCH.md — record of initial dispatch message
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- handoff.md — final analysis and strategy handoff report
