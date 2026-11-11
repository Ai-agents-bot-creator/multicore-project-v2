# Hard Handoff Report: Explorer M1 Fix 1 (`dir_ctrl.sv` Reversion Strategy)

- **Agent**: `explorer_m1_fix_1` (`teamwork_explorer`)
- **Roles**: investigation, synthesis
- **Date**: 2026-11-05T17:55:00Z
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_1`
- **Target DUT**: `rtl/directory/dir_ctrl.sv`
- **Handoff Type**: Hard (Investigation & Fix Strategy Complete)

---

## 1. Observation

### Observation 1: RTL Checksum Mismatches & Workspace Desynchronization
- Executed command:
  ```bash
  md5sum /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv \
         /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/directory/dir_ctrl.sv \
         /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/dir_ctrl.sv \
         /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv \
         /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/dir_ctrl.sv
  ```
- Verbatim output:
  ```text
  acc52411a8b20d2c82771d4c8a28e187  /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
  acc52411a8b20d2c82771d4c8a28e187  /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/directory/dir_ctrl.sv
  acc52411a8b20d2c82771d4c8a28e187  /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/dir_ctrl.sv
  4b8cca8381166c83ee61440ee2e45220  /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
  4b8cca8381166c83ee61440ee2e45220  /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/dir_ctrl.sv
  ```

### Observation 2: Exact RTL Diff Between Source Repo and Clean-Room Baseline
- Executed command:
  ```bash
  diff -u /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv \
          /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
  ```
- Verbatim output:
  ```diff
  --- /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv	2026-11-05 22:51:07.224485400 +0530
  +++ /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv	2026-11-05 23:14:06.332802800 +0530
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

### Observation 3: Divergence in `FROZEN.md5` Checksum Manifests
- Source repo `rtl_frozen/FROZEN.md5`:
  ```text
  b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
  d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
  acc52411a8b20d2c82771d4c8a28e187  rtl_frozen/directory/dir_ctrl.sv
  ```
- Clean-room `rtl_frozen/FROZEN.md5`:
  ```text
  b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
  d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
  4b8cca8381166c83ee61440ee2e45220  rtl_frozen/directory/dir_ctrl.sv
  ```

### Observation 4: Analysis of `WAKE_UP.sh` Blind Re-freezing Logic
- In `/mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh`:
  - Lines 18-32: Explicitly checks `VERIFIER="pd/v1/verify_patch_set.py"` against hardcoded `EXPECTED_VERIFIER_MD5="4c4370f50882e82399b65076147bf112"`.
  - Lines 49: `md5sum rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv > rtl_frozen/FROZEN.md5` directly overwrites `FROZEN.md5` from current `rtl/` content without prior verification.
  - Lines 81: `md5sum -c rtl_frozen/FROZEN.md5` only checks the newly generated file, self-certifying any modified RTL.

### Observation 5: Specification Invariant Mandate
- `PROJECT.md:14`: *"Isolation Constraint: The team must NOT read or inspect test source code from tb/, tb_self_test/, tb/l1_dir/, or scratch test suites. The frozen RTL is a read-only black box. RTL under test must NEVER be modified."*
- `ORIGINAL_REQUEST.md:9-10, 30`: *"The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification."*

---

## 2. Logic Chain

1. **Clean-Room Baseline Defined (Observation 1 & 5)**:
   The clean-room workspace at `/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen` was snapshot with authoritative hash `4b8cca8381166c83ee61440ee2e45220`. Per project constraints, the frozen RTL is a read-only black box that must not be modified.

2. **Root Cause of Failure Identified (Observation 2 & 3)**:
   At 23:14:06, `rtl/directory/dir_ctrl.sv` in the source repository was modified to add `output logic [2:0] rxq_cnt_o` (line 37) and `assign rxq_cnt_o = rxq_cnt;` (line 661). This increased file size by 67 bytes (from 26,207 to 26,274 bytes) and changed its MD5 to `acc52411a8b20d2c82771d4c8a28e187`.

3. **Vulnerability in Reset Mechanism Identified (Observation 4)**:
   `WAKE_UP.sh` has a hardcoded check for `verify_patch_set.py` but lacks checks for RTL files. When `./WAKE_UP.sh` was re-run, it blindly copied the modified `dir_ctrl.sv` into `rtl_frozen/` and generated a new `FROZEN.md5`, allowing an unauthorized RTL modification to masquerade as valid.

4. **Split-Brain Workspace State (Observation 1 & 3)**:
   Acceptance tests developed in `~/teamwork_projects/clean_room_verification` execute against `4b8cca8381166c83ee61440ee2e45220` (where `rxq_cnt_o` does not exist), while tests in `/mnt/Code/visualstudio/Design-arch_multi-core` run against `acc52411a8b20d2c82771d4c8a28e187`.

5. **Fix Path Deduced**:
   - Reverting lines 37 and 661 in `rtl/directory/dir_ctrl.sv` restores the file bit-for-bit to MD5 `4b8cca8381166c83ee61440ee2e45220`.
   - Hardcoding the golden hashes (`b6ece1864f1ce6ddf5b6976775d34485`, `d63be56146cfd7f2c9f3682caf918809`, `4b8cca8381166c83ee61440ee2e45220`) into `WAKE_UP.sh` closes the vulnerability and prevents future regressions.

---

## 3. Caveats

- In strict compliance with clean-room isolation rules, zero test code files in `tb_self_test/`, `tb/l1_dir/`, or scratch directories were inspected.
- In accordance with the Explorer read-only role constraint, no source code files (`rtl/directory/dir_ctrl.sv` or `WAKE_UP.sh`) were edited during this investigation. Implementation must be carried out by a worker agent.
- `~/teamwork_projects/clean_room_verification` is already in a clean, baseline state; no changes are required inside the clean-room directory itself.

---

## 4. Conclusion

The M1 failure was caused by an unauthorized injection of `rxq_cnt_o` into `rtl/directory/dir_ctrl.sv` at 23:14:06 and the lack of golden RTL checksum verification in `WAKE_UP.sh`.

### Turnkey Action Plan for Worker:
1. **Revert `rtl/directory/dir_ctrl.sv`**:
   Execute:
   ```bash
   cp -p /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv \
         /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
   ```
   Confirm MD5 is `4b8cca8381166c83ee61440ee2e45220`.
2. **Update `WAKE_UP.sh`**:
   Add golden baseline checks for `rtl/pkg/tile_pkg.sv`, `rtl/l1/l1_mesi_ctrl.sv`, and `rtl/directory/dir_ctrl.sv` before copying (see complete script in `report.md §5.2`).
3. **Execute `./WAKE_UP.sh`**:
   Run in `/mnt/Code/visualstudio/Design-arch_multi-core` and verify `rtl_frozen/FROZEN.md5` matches `4b8cca8381166c83ee61440ee2e45220`.
4. **Attestation Refresh**:
   Update handoff documentation with verified outputs.

---

## 5. Verification Method

To independently verify the fix once implemented:

1. **Verify Baseline Checksums**:
   ```bash
   md5sum /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
   # MUST return: 4b8cca8381166c83ee61440ee2e45220
   ```

2. **Verify Bit-for-Bit Identity Across Workspaces**:
   ```bash
   cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv \
       /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
   # MUST return 0 (no difference)
   ```

3. **Verify WAKE_UP.sh Golden Hash Enforcement**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core && ./WAKE_UP.sh
   # Step 2 MUST print:
   # b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
   # d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
   # 4b8cca8381166c83ee61440ee2e45220  rtl_frozen/directory/dir_ctrl.sv
   ```

4. **Verify FROZEN.md5 Parity**:
   ```bash
   diff -u /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5 \
           /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
   # MUST output empty diff
   ```
