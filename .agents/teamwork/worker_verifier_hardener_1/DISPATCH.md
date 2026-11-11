# Dispatch: Worker Verifier Hardener 1
State folder: /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_verifier_hardener_1


## 2026-11-09T14:11:02Z
You are Worker Verifier Hardener 1.
Your mission is to harden `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py` to eliminate the 8 false-negative blind spots discovered during adversarial mutation testing by Challenger 1.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mandatory reading:
Read ORIGINAL_REQUEST.md at:
/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
Read Challenger 1 Challenge Report at:
/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_srs_1/challenge.md
Read Reviewer 2 Observations at:
/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/reviewer_srs_2/review.md

Exclusive Write Ownership:
- `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py`
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_verifier_hardener_1/`

Your Tasks:
Apply the hardening patches detailed in `challenge.md` to `verify_srs.py`:
1. Add check `T13` (XML Table Formatting): Using `docx.Document`, assert that for every table in `doc.tables`, row 0 has `w:tblHeader` in `r._tr.xpath('./w:trPr/w:tblHeader')`, and every row has `w:cantSplit` in `r._tr.xpath('./w:trPr/w:cantSplit')`.
2. Harden Message Direction check `B1c`: Locate the Message table specifically (`rows[0][0].strip().lower() == "message"`) and assert that `PUTACK` direction (column 1) contains `dir -> l1` or `dir -> requester`.
3. Harden Power check `N5b`: Check the row with `PWR-03` specifically and assert that the target cell (column 2) contains `<= 50` or `<= 50 mw`.
4. Harden Flip-Flop check `T05`: Check the row with `AREA-04` specifically and assert that the target cell (column 2) contains `25,000` or `25000`.
5. Harden DSP check `B4d`: Check the row with `AREA-03` specifically and assert that both target and ceiling cells equal `0`.
6. Harden Mentor check `T11`: Locate the Approval table (`rows[0][0].strip().lower() == "role"` or contains `"mentor"`) and verify `Mr. Hemat` in the mentor row.
7. Harden Timing check `T03`: Assert that `setup uncertainty`, `0.2`, and `wns` all appear in Section 7.4 / Table 15 (Timing Budget).
8. Harden DMA check `T04`: Locate the DMA register table (`rows[0][1].strip().lower() == "name"` and `rows[0][0].strip().lower() in ("offset", "address")) and verify all 6 register names (`SRC_LO, DST_LO, LEN, CTRL, STATUS, COUNT`).
9. Fix Traceability requirement extraction: Ensure regex includes `AC-\d+` so that `len(all_defined_reqs)` correctly reflects all 45 defined requirements.
10. Test execution:
    - Execute `python3 verify_srs.py --srs /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final_v2.docx`. Verify exit code 0 and all checks pass cleanly.
    - Execute `python3 verify_srs.py --srs /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx --baseline`. Verify exit code 0 and 41/41 baseline checks pass cleanly.

Deliverables:
- Updated `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py`
- Changes and test logs in `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_verifier_hardener_1/changes.md`
- Self-contained handoff report in `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_verifier_hardener_1/handoff.md`
Use send_message to report when complete.
