# Dispatch Log

## 2026-11-05T17:26:00Z

Clean-room independent verification of the multi-core cache hierarchy RTL against specifications in an isolated workspace, using frozen RTL snapshots without inspecting or copying from existing self-test testbenches.

Working directory: ~/teamwork_projects/clean_room_verification
Integrity mode: demo
The team must NOT: Read test source code to understand expected behaviour before implementing

## Requirements

### R1. Setup and Isolation
- In `/mnt/Code/visualstudio/Design-arch_multi-core`:
  - Verify that `md5sum pd/v1/verify_patch_set.py` matches `4c4370f50882e82399b65076147bf112`.
  - Snapshot the RTL under test (`rtl/pkg/tile_pkg.sv`, `rtl/l1/l1_mesi_ctrl.sv`, `rtl/directory/dir_ctrl.sv`) into `rtl_frozen/` and generate `rtl_frozen/FROZEN.md5`.
  - Quarantine existing self-tests by moving `tb/l1_dir` into `tb_self_test/l1_dir` and creating `tb_self_test/README.md`.
  - Create and make executable `WAKE_UP.sh` automating these steps.
- In `~/teamwork_projects/clean_room_verification`:
  - Copy only the authorized specification files from `/mnt/Code/visualstudio/Design-arch_multi-core`:
    - `white_papers/final/FINAL_whitepaper_v3.0.md`
    - `white_papers/final/SLICE_16_1.md`
    - `white_papers/final/WORK_BREAKDOWN_16.md`
    - `white_papers/final/RULINGS_B1_B2_B4.md`
    - `docs/01_DECISION_LOG.md`
    - `docs/04_TECH_STACK.md`
    - `BUILD_ORDER.md`
  - Copy `rtl_frozen/` and `rtl_frozen/FROZEN.md5`.
  - Verify `md5sum -c rtl_frozen/FROZEN.md5` passes before proceeding.
  - Do NOT copy or read any files from `tb/self_test/`, `tb/l1_dir/`, or scratch directories. The frozen RTL is a read-only black box.

### R2. Clean-Room Acceptance Test Suite (tb_acceptance/)
Build an independent test suite from scratch in `tb_acceptance/` derived solely from the specifications:
- `tb_acceptance/l1_dir/`: Directed tests F1 through F9 using cocotb 2.1.0 and iverilog 13.0.
- `tb_acceptance/sva/`: SystemVerilog Assertions (A1.1, A1.2, A1.3, A2.2, A2.6, A3.1, A7.x) and formal Bounded Model Checking (BMC) at depth K=64 using SymbiYosys (`sby`).
- `tb_acceptance/ref_model/`: Python shadow reference model mirroring slice rules 1–11, comparing cycle-by-cycle against the DUT and reporting mismatch count.
- `tb_acceptance/mutations/`: Independent mutation tests proposed directly from the specification.
- `tb_acceptance/run_all.py`: Unified test runner that executes all tests and outputs a matrix: `test name | PASS/FAIL | spec clause it verifies`.

### R3. Reporting and Defect Citation
- Provide a summary report covering F-test coverage, assertion coverage, and overall PASS/FAIL matrix.
- For each test failure (if any), cite the exact specification line violated by the RTL in README.md without modifying the RTL.
- Include a mutation matrix reporting: `mutation | positive | neg1 | neg2 | expected vs actual`.
- Include formal verification BMC results at K=64 with SymbiYosys output.
- Report reference-model cycle-by-cycle mismatch count (target: 0 for a green baseline).
- Document any checks that could not be built due to specification ambiguity or tool availability as "not specified".

## Acceptance Criteria

### Isolation and Setup Integrity
- [ ] `WAKE_UP.sh` executes the 4-step reset cleanly in `/mnt/Code/visualstudio/Design-arch_multi-core`.
- [ ] `rtl_frozen/FROZEN.md5` passes validation (`md5sum -c rtl_frozen/FROZEN.md5`).
- [ ] `~/teamwork_projects/clean_room_verification` contains only the authorized specification files and frozen RTL; no files from `tb_self_test/` or existing testbenches are present.
- [ ] RTL in `rtl_frozen/` is unmodified.

### Acceptance Test Execution
- [ ] `tb_acceptance/run_all.py` executes all directed tests F1 through F9 and outputs a matrix with test name, PASS/FAIL status, and spec clause cited.
- [ ] Formal BMC at K=64 executes via SymbiYosys for assertions A1.1, A1.2, A1.3, A2.2, A2.6, A3.1, A7.x, with raw sby output captured.
- [ ] Python shadow reference model executes cycle-by-cycle against DUT and reports mismatch count.
- [ ] Mutation matrix reports positive and negative outcomes against spec expectations.
- [ ] For each failing test (if any), the README quotes the exact specification line violated.

