# Hard Handoff Report: Explorer M1 Fix 3 (Workspace Synchronization & Re-Verification Plan)

- **Agent**: `explorer_m1_fix_3` (`teamwork_explorer`)
- **Roles**: explorer, analyst
- **Date**: 2026-11-05T17:59:00Z
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_3`
- **Target Workspaces**:
  - `/mnt/Code/visualstudio/Design-arch_multi-core`
  - `/home/durgesh/teamwork_projects/clean_room_verification`
- **Status**: COMPLETE (Read-only investigation & remediation workflow designed)

---

## 1. Observation

### 1.1 Verbatim Discrepancy Between Workspaces
- Clean-room file `~/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv`:
  - MD5: `4b8cca8381166c83ee61440ee2e45220` (26,207 bytes)
- Source repository file `/mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv`:
  - MD5: `acc52411a8b20d2c82771d4c8a28e187` (26,274 bytes)
- Source repository file `/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/directory/dir_ctrl.sv`:
  - MD5: `acc52411a8b20d2c82771d4c8a28e187` (26,274 bytes)
- Verbatim `diff -u`:
  ```diff
  --- /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
  +++ /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
  @@ -34,6 +34,7 @@
       output pending_op_t pending_op_o,
       output logic [TILE_ID_W-1:0] req_tile_o,
       output logic rxq_empty_o,
  +    output logic [2:0] rxq_cnt_o,
       output msg_type_t rx_msg_o,
       output logic [TILE_ID_W-1:0] rx_src_o,
       output logic        rx_oflow_o,
  @@ -657,6 +658,7 @@
     assign pending_op_o = pending_op;
     assign req_tile_o   = req_tile;
     assign rxq_empty_o  = rxq_empty;
  +  assign rxq_cnt_o    = rxq_cnt;
     assign rx_msg_o     = msg_type_t'(h_msg);
     assign rx_src_o     = h_src;
     assign dtr_busy    = (state != DIR_I);
  ```

### 1.2 In-Memory Reversion Hash Verification
- Command:
  ```bash
  grep -v "rxq_cnt_o" /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv | md5sum
  ```
- Result:
  ```text
  4b8cca8381166c83ee61440ee2e45220  -
  ```
- This confirms that stripping `rxq_cnt_o` restores the exact bit-for-bit baseline of the clean-room snapshot.

### 1.3 `WAKE_UP.sh` Circular Snapshot Vulnerability
- Lines 48-51 in `/mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh`:
  ```bash
  md5sum rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv > rtl_frozen/FROZEN.md5
  ```
- Lines 80-82:
  ```bash
  md5sum -c rtl_frozen/FROZEN.md5
  ```
- Observation: `WAKE_UP.sh` lacked any pre-copy check against golden hashes, allowing mutated files in `rtl/` to be snapshotted and dynamically signed without triggering an error.

### 1.4 Status of Other RTL and Specification Files
- `rtl/pkg/tile_pkg.sv`: MD5 `b6ece1864f1ce6ddf5b6976775d34485` (identical across both workspaces).
- `rtl/l1/l1_mesi_ctrl.sv`: MD5 `d63be56146cfd7f2c9f3682caf918809` (identical across both workspaces).
- All 7 authorized specifications in `~/teamwork_projects/clean_room_verification` (`FINAL_whitepaper_v3.0.md`, `SLICE_16_1.md`, `WORK_BREAKDOWN_16.md`, `RULINGS_B1_B2_B4.md`, `01_DECISION_LOG.md`, `04_TECH_STACK.md`, `BUILD_ORDER.md`) match the source repo with identical MD5/SHA256 hashes.
- Clean room has 0 legacy test files, 0 symlinks, and 0 hidden files.

---

## 2. Logic Chain

1. **Isolation Mandate**: Milestone 1 requires complete parity between the frozen RTL under test and the clean-room snapshot, with frozen RTL treated as an immutable read-only black box (Observation 1.4 & PROJECT.md §R1).
2. **Identification of Defect**: `rtl/directory/dir_ctrl.sv` in `/mnt/Code/visualstudio/Design-arch_multi-core` was modified with `rxq_cnt_o`, producing hash `acc52411a8b20d2c82771d4c8a28e187`, while the clean room preserves the unmutated baseline `4b8cca8381166c83ee61440ee2e45220` (Observation 1.1).
3. **Defect Reversibility**: Removing the two `rxq_cnt_o` lines returns the file to `4b8cca8381166c83ee61440ee2e45220` down to the exact byte (Observation 1.2).
4. **Root Cause in Tooling**: `WAKE_UP.sh` permitted this divergence because it computed `FROZEN.md5` dynamically without checking pre-conditions against golden hashes (Observation 1.3).
5. **Remediation Sufficiency**:
   - Reverting `rtl/directory/dir_ctrl.sv` to `4b8cca8381166c83ee61440ee2e45220`.
   - Hardening `WAKE_UP.sh` with explicit golden checksum assertions (`b6ece1...`, `d63be5...`, `4b8cca...`).
   - Re-running `WAKE_UP.sh`.
   - Re-verifying `md5sum -c rtl_frozen/FROZEN.md5` and executing cross-repo `cmp` checks.
   This guarantees complete bit-for-bit parity without violating clean-room boundaries.

---

## 3. Caveats

- In strict compliance with clean-room protocol, no testbench source code in `tb/`, `tb_self_test/`, or scratch directories was opened or inspected.
- This agent acted purely in a read-only exploratory capacity. No project source files or scripts were modified. Implementation must be carried out by a designated worker agent.

---

## 4. Conclusion

The divergence reported by Challenger M1-2 is completely understood and directly fixable:
1. Revert `rtl/directory/dir_ctrl.sv` to baseline `4b8cca8381166c83ee61440ee2e45220`.
2. Update `WAKE_UP.sh` to enforce golden checksums (`verify_file_md5`) for all 3 RTL files before snapshotting and upon frozen validation.
3. Re-run `WAKE_UP.sh` in the source repository.
4. Verify `md5sum -c rtl_frozen/FROZEN.md5` in both repositories and confirm bit-for-bit identity across all files.

Full detailed instructions and the hardened `WAKE_UP.sh` script are documented in `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_3/report.md`.

---

## 5. Verification Method

To verify the remediation when executed by the worker:

1. **Verify Golden RTL Checksums in Source Repo**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core
   md5sum rtl/pkg/tile_pkg.sv rtl/l1/l1_mesi_ctrl.sv rtl/directory/dir_ctrl.sv
   ```
   Must output:
   ```text
   b6ece1864f1ce6ddf5b6976775d34485  rtl/pkg/tile_pkg.sv
   d63be56146cfd7f2c9f3682caf918809  rtl/l1/l1_mesi_ctrl.sv
   4b8cca8381166c83ee61440ee2e45220  rtl/directory/dir_ctrl.sv
   ```

2. **Verify Reset Script Execution**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core
   ./WAKE_UP.sh
   # Must complete cleanly with exit code 0 and all 4 steps PASSing.
   ```

3. **Verify Checksum Validation in Both Repos**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core && md5sum -c rtl_frozen/FROZEN.md5
   cd /home/durgesh/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5
   # Both must report OK for all 3 files with exit code 0.
   ```

4. **Verify Bit-for-Bit Identity Across Workspaces**:
   ```bash
   diff -u /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5 /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
   cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/directory/dir_ctrl.sv /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
   # Both commands must produce zero output and exit code 0.
   ```
