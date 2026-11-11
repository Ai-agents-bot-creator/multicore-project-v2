## 2026-11-09T13:44:33Z
You are Worker SRS Generator 1.
Your mission is to author and implement the elevated, improved SRS document `SRS_final_v2.docx` and upgrade the automated verification script `verify_srs.py` to ensure complete, rigorous verification.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mandatory reading:
Read ORIGINAL_REQUEST.md at:
/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/ORIGINAL_REQUEST.md
Read PROJECT.md at:
/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/PROJECT.md

Investigation & Reference Inputs:
- Spec Miner analysis & handoff:
  /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_spec_miner_1/analysis.md
  /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_spec_miner_1/handoff.md
- Template Explorer analysis, handoff, and prototype script:
  /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_template_1/analysis.md
  /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_template_1/handoff.md
  /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_template_1/test_expanded_verify.py
- Standards Explorer analysis & handoff:
  /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_standards_1/analysis.md
  /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_standards_1/handoff.md
- Source artifacts:
  - Baseline DOCX: /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx
  - Ground truth spec: /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/FINAL_whitepaper_v3.0.md
  - Template DOCX: /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/SRS/SRS_Template_final.docx
  - Student Guide PDF: /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/SRS/SRS Template Student Guide.pdf
  - Current verification script: /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py

Exclusive Write Ownership:
- `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final_v2.docx`
- `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py`
- `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_srs_generator_1/`

Your Implementation Tasks:
1. Author `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final_v2.docx` using a Python script (with `python-docx`):
   - Rebuild Table 1 (Metadata table) per template: Project Title (`Cache-Coherent Tiled Mesh Multicore`), Group (`Group 16 (PGCP VLSI)`), Members (`Durgesh Kolhe, Sai Charan, Additya, Joshna`), Group Mentor (`Mr. Hemat`), Version / Date (`v2.0 / 09-11-2026`).
   - Fix Table 22 (Approval table): Replace `[Name]` with `Mr. Hemat` (Group Mentor).
   - Functional Requirements: Incorporate requirements FR-15 through FR-20 into Table 7 (Detailed Functional Requirements) and Table 3 (Functional Requirements Summary), covering:
     * FR-15: Same-line INV abort in IS_D/IM_D/SM_D with immediate INVACK and re-issue (Ruling B6, WP §3.3 rule 6, row AH).
     * FR-16: Directory controller per-VC receive queueing (4 queues: RESP > INV > FWD > REQ) and UNBLOCK completion rule for aborted accesses (Ruling B7, row AI).
     * FR-17: Request re-issue ordering at back of VC0 queue bounding progress under Lemma L2 (Ruling B8, row AJ).
     * FR-18: Memory consistency vs coherence serialization contract (WP §3.10).
     * FR-19: Transient race handling (evict-during-forward race N5/N12, silent transitions, Tree-PLRU determinism, VC preservation).
     * FR-20: Inclusive L2 with local shortcut / bypass and miss retry upon invalidation races.
   - Non-Functional & PPA Targets:
     * PERF-01: Target 100 MHz (10.0 ns), Minimum 50 MHz (20.0 ns) on ZedBoard XC7Z020.
     * PERF-02: Throughput (>= 1 flit/cycle per node peak injection, sustained load saturation >= 0.25 flits/node/cycle under uniform random traffic).
     * FPGA-01: 100 MHz (10.0 ns) target on ZedBoard XC7Z020.
     * FPGA-02: Timing closure margins: WNS >= 0 ns, WHS >= 0 ns, WPWS >= 3.750 ns, TNS = 0.
     * Section 5 & PWR-01..03: Delete false claim that "WP contains no power data". Set total on-chip power budget <= 50 mW per WP §6.4 (measured via report_power post-implementation, estimated with Xilinx Power Estimator).
     * Section 6 & Table 10: Add AREA-04 for Flip-Flop resource target (target <= 25,000 / 24%, ceiling <= 50,000 / 47%) per WP §6.1.
     * Explicitly specify PPA trade-off priority: Correctness > Area > Frequency > Power.
   - Interfaces & Signals:
     * Table 7.2 (and Table 12/13/18): Remove erroneous `port_in_ready` and `port_out_ready`. Flow control is credit-based (`credit_in[3:0]`, `credit_out[3:0]`). Add `TILE_ID[1:0]` module input, explicit `flit_vc[1:0]` virtual channel lines, and explicit 64-bit flit widths (`flit_in[63:0]`, `flit_out[63:0]`).
     * Table 19 Pin mapping: Populate ZedBoard clock pin `Y9`, reset button `P16` (BTNC) / slide switch `F22` (SW0).
     * Restore Table 11a (Interface Summary) and Table 14 (Timing Budget).
     * Restore Section 7.5 DMA Register Map table (Table 15: `SRC_LO 0x00, DST_LO 0x04, LEN 0x08, CTRL 0x0C, STATUS 0x10, COUNT 0x14`), annotated as 4x4 simulation-only and Month-2 (Week-8) gated per Ruling B4.
   - Verification & Coverage:
     * Section 8.3 (Table 15): Restore Statement (>= 90%), Branch (>= 85%), and Toggle (>= 85%) coverage goals alongside functional coverage (100%).
     * Link FV-13 to AC-01 and FV-14 to FPGA-06.
     * Include SVA assertion coverage for network invariants I1 through I7.
   - Traceability Matrix (Table 21):
     * Expand Table 21 from 14 rows to 44 rows covering all requirement IDs: FR-01..FR-20, AC-01..AC-05, PERF-01..PERF-06, PWR-01..PWR-03, AREA-01..AREA-04, FPGA-01..FPGA-05b. Each row must link to verification method, evidence/test ID, and status.
   - Table XML Formatting:
     * Apply `w:tblHeader` on row 0 and `w:cantSplit` on all rows across every table in the document so tables paginate cleanly.

2. Upgrade `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py`:
   - Incorporate the 25 expanded checks designed in `test_expanded_verify.py` so `verify_srs.py` runs 66 comprehensive checks.
   - Ensure `verify_srs.py --srs /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final_v2.docx` runs and reports `RESULT: PASS - 66/66 SRS checks passed`.
   - Maintain backward compatibility so `--srs /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx` continues to pass the baseline 41 checks (e.g. baseline flag or clear failure on the new strict checks).

3. Deliverables:
   - Output files:
     `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final_v2.docx`
     `/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/verify_srs.py`
   - Detailed changes log:
     `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_srs_generator_1/changes.md`
   - Self-contained handoff report:
     `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/worker_srs_generator_1/handoff.md`
   Use send_message to report when complete.
