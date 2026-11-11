You are implementing a hardware design project. A supervisor has reviewed your work and issued
the following work order. Work through the tasks in order. Each task states the exact change and
how to verify it. Report back after each task with what you changed and the command output that
proves it.

Repo root: /mnt/Code/visualstudio/Design-arch_multi-core
Spec package: white_papers/final/   (WP, SPEC_SHEET, both LLD .md, diagrams_rendered.html,
                                    WORK_BREAKDOWN_16.md, SLICE_16_1.md)
Gate:          pd/v1/verify_patch_set.py
RTL:           rtl/   Docs: docs/

================================================================================
TASK 1 — Replace the gate with the canonical file (DO THIS FIRST)
================================================================================
Your repo copy of the gate is a fork (md5 d3e8afd1...) whose check count changes with the
--build-script flag, which makes the count-guard checks (J1/J2) fail spuriously.

  1. Copy the delivered verify_patch_set.py over pd/v1/verify_patch_set.py.
     Expected md5: 4c4370f50882e82399b65076147bf112
  2. Confirm the build script sits next to it (pd/v1/build_diagrams_html.py). If it does not,
     pass the path explicitly with --build-script.
  3. Run:
       python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py
     Expect: RESULT: PASS - 130/130 checks passed, exit code 0

  The count must now be 130 whether or not --build-script is passed. That invariance is the
  point of this file. Do not edit the gate to make a number look right.

================================================================================
TASK 2 — Fix one constant in rtl/pkg/tile_pkg.sv
================================================================================
Current (wrong):
    localparam int L1_TAG_W    = ADDR_W - L1_SET_LO;       // 24 always

The comment says 24 but the expression yields 26. The L1 set index is [7:6], so those two bits
are index, not tag. WP §3.6: the L1 stored tag is addr[31:8] = 24 b in both configurations.

Replace with:
    localparam int L1_TAG_W    = ADDR_W - (L1_SET_HI + 1);   // 24 always: stored tag = addr[31:8]

Verify: every other width in the file is already correct (L2 address tag 21 b / 19 b, per-line
word 23 b / 21 b, directory entry 10 b / 24 b, home addr[12:11] / addr[14:11], message codes
0000-1101, VC0 REQ / VC1 FWD / VC2 RESP / VC3 INV, header layout with 6-bit LEN at [37:32],
DTR codes 000 NONE .. 100 DMA, age threshold 5). Re-read the whole file and confirm each against
white_papers/final/FINAL_whitepaper_v3.0.md §3.2, §3.3, §3.6, §3.8 and Appendix C. Report any
other discrepancy you find rather than silently fixing it.

================================================================================
TASK 3 — Fix one cross-reference in the white paper
================================================================================
In white_papers/final/FINAL_whitepaper_v3.0.md, Appendix C, the header-fl bit table, the VC ID
row currently reads:

  | [43:42] | VC ID | 2 | **Checked field**: must equal class(msg); asserted by the NIC and by
  formal invariant I3, never used as a routing input |

I3 is the credit invariant. The VC check is I2 (`flit.VC == class(flit.msg)`) — see the numbered
list in §5.3: I1 XY path, I2 flit.VC == class(flit.msg), I3 credit invariant.

Change "invariant I3" to "invariant I2" in that row only. Then re-run the gate (Task 1 command)
and confirm 130/130 still passes.

================================================================================
TASK 4 — Run the documentation checker over docs/ and fix what it reports
================================================================================
A checker ships with the documentation skill (Task 5). Install the skill first, then:

    python3 ~/.skills/hw-design-docs/scripts/check_docs.py --docs docs \
        --wp white_papers/final/FINAL_whitepaper_v3.0.md \
        --build-order BUILD_ORDER.csv

Fix every FAIL it reports. WARNs (leftover placeholders such as TBD/TODO) are worth fixing too,
except the group metadata placeholders (group number, member names, mentor name) which the
supervisor fills in personally — leave those and report them.

================================================================================
TASK 5 — Install the documentation skill globally (backup copy requested)
================================================================================
Unzip the delivered hw-design-docs.zip into the backup folder:

    mkdir -p /mnt/code/visualstudio/ai_skills
    unzip -o hw-design-docs.zip -d /mnt/code/visualstudio/ai_skills/

Then install it so it is available as a global skill:

    mkdir -p ~/.skills
    cp -r /mnt/code/visualstudio/ai_skills/hw-design-docs ~/.skills/

Check your agent's own documentation for the global skills directory if it is not ~/.skills, and
put it there as well. The skill is: SKILL.md + references/doc-templates.md +
scripts/check_docs.py. Do not add README/CHANGELOG/install.sh/.env/.gitignore files to it.

================================================================================
TASK 6 — Then start the RTL: §16.1 and §16.2 co-landed
================================================================================
Only after Tasks 1-5 are green. Build order and scope are fixed by BUILD_ORDER.csv and the
supervisor's corrected order in BUILD_ORDER.md:

  1. l2_bank   (2 d)   — per-line word {valid, tag, dirty}; tree-PLRU; 512-bit path
  2. l2_ctrl   (1 d)   — bank access port; DTR (one transaction per bank)
  3. l1_mesi_ctrl (4-5 d) — 9 states; rules 2,5,8,9,10; forward release; CONFLICT EVICTION
  4. dir_ctrl  (4-5 d) — 8 states; single-exit rule (UNBLOCK); N4/N5/N12; rulings B1/B4
  5. nic (1 d) → 6. router (2 d) → 7. mem_tap (0.5 d) → 8. cpu_tile (1 d) → 9. mesh_top (1 d)

  Why l2_bank/l2_ctrl come before the directory: the directory side writes the bank (fill path,
  DIR_E + PUTM write-back, dirty-bit set/clear). Do not write dir_ctrl against an undefined bank
  interface — freeze the port first.

  Why §16.1 and §16.2 co-land: the exclusive bit is generated by the directory (rule 9) and
  consumed by the L1. Test F8 is meaningless without both, and A1.2 ("at most one L1 in E") is
  the assertion that catches a wrongly generated bit.

  Mandatory behaviours, from the ruled spec:
   - Forward release: FWD_GETS -> owner downgrades E/M to S and sends DATAFWD; FWD_GETM -> owner
     downgrades E/M to I and sends DATAFWD. No PUTS/PUTM on the forward path (rule 8).
   - Conflict eviction (ruling B2): if the incoming line's set is full, the victim is released
     BEFORE the miss request is issued — dirty (M) -> PUTM and wait for PUTACK; clean (S/E) ->
     PUTS (E waits for PUTACK, S does not). It is a sub-step of the miss transient: the L1 stays
     in IS_D/IM_D, no second transient, no MSHRs. PUTM/PUTS and the later GETS/GETM both travel
     on VC0, so the per-VC FIFO ordering preserves release-before-miss at the source.
   - Receptivity (Premise R): an L1 with an outstanding miss still services INV/DATA/INVACK/FWD
     for other lines immediately.
   - Age escape threshold 5 rounds; the output switch arbiter is port-granular, never VC-aware.
   - DMA tile: gated on the Week-8 gate exit, 4x4 simulation only. No DMA tile, DMA signal or
     DMA path in the 2x2 build.

A module is green only when all four hold:
  1. RTL unit green (lint clean, unit tests pass)
  2. SVA category clean (BMC K = 64)
  3. Reference-model shadow agrees (zero mismatches on the module's directed tests)
  4. python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py
     still reports 130/130, exit 0

================================================================================
RULES
================================================================================
- Do not hand-edit verify_patch_set.py to make a count match. If a check fails, fix the artifact
  the check is about. The count guards (J1/J2) exist to catch exactly that.
- If the gate's count legitimately changes (a check is added or removed), update every quoted
  count in WORK_BREAKDOWN_16.md and SLICE_16_1.md in the same change, then re-run the gate. The
  guards will fail until you do.
- If a number is not in the spec, write "not specified" and log it as an open item. Never
  interpolate, and never carry a number over from another configuration.
- Processor cores are OUT of scope (WP §1.4). The 2x2 area budget (~13-19k LUTs, 28-80 BRAM36)
  covers the coherence fabric only. Do not instantiate an RV32I core, imem or dmem. If you want
  one, raise it — it invalidates the committed area numbers.
- If you change a diagram source .md, re-render the HTML with build_diagrams_html.py in the same
  change. The gate's S2c check compares the rendered HTML byte-for-byte against a fresh render.
- Keep docs/ in lockstep: a ruling lands in 01_DECISION_LOG.md, a defect in 02_PROBLEM_LOG.md, a
  new module in 00 and 03, a verification delta in 06.
- Report anything you could not do, and why. A short honest report beats a green tick on work
  that did not happen.
