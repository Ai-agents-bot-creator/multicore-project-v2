# Hard Handoff Report: Challenger M1-2 (Clean-Room Isolation Empirical Challenge)

- **Agent**: `challenger_m1_2` (`teamwork_challenger`)
- **Roles**: critic, specialist
- **Date**: 2026-11-05T17:50:00Z
- **Target Workspace**: `/home/durgesh/teamwork_projects/clean_room_verification`
- **Source Workspace**: `/mnt/Code/visualstudio/Design-arch_multi-core`
- **Verdict**: **CHALLENGE** (RTL bit-for-bit divergence between clean room and source repository)

---

## 1. Observation

### 1.1 Unauthorized Files, Hidden Files, Symlinks, and Legacy Testbenches
- **Hidden Files Search**:
  - Command: `find /home/durgesh/teamwork_projects/clean_room_verification -name ".*"`
  - Output: Empty (0 files found).
- **Symlinks Search**:
  - Command: `find /home/durgesh/teamwork_projects/clean_room_verification -type l`
  - Output: Empty (0 symlinks found).
- **Legacy Test / Scratch / Quarantine Scan**:
  - Command: `find /home/durgesh/teamwork_projects/clean_room_verification -iname "*test*" -o -iname "*tb*" -o -iname "*quarantine*" -o -iname "*legacy*" -o -iname "*scratch*"`
  - Output: Empty (0 files found).
- **Non-regular Files Scan**:
  - Command: `find /home/durgesh/teamwork_projects/clean_room_verification ! -type f ! -type d`
  - Output: Empty (0 special files found).
- **Filesystem Isolation**:
  - Command: `df -T /mnt/Code/visualstudio/Design-arch_multi-core /home/durgesh/teamwork_projects/clean_room_verification`
  - Output: `/mnt/Code` is `fuseblk` and `/home/durgesh` is `ext4` (physically separate filesystems; cross-filesystem hard links impossible).
- **Git Repository Isolation**:
  - Command: `cd /home/durgesh/teamwork_projects/clean_room_verification && git status`
  - Output: `fatal: not a git repository (or any of the parent directories): .git`

### 1.2 Verification of 7 Authorized Specification Files Bit-for-Bit
Every authorized specification file was compared using `cmp`, `md5sum`, and `sha256sum` against `/mnt/Code/visualstudio/Design-arch_multi-core`:

| Specification File | Clean-Room MD5 | Source Repo MD5 | SHA256 Match | `cmp` Result | Status |
|---|---|---|---|---|---|
| `white_papers/final/FINAL_whitepaper_v3.0.md` | `903802d4a96b8ec367f23476fa0fec3e` | `903802d4a96b8ec367f23476fa0fec3e` | `6816243d...` | Identical | PASS |
| `white_papers/final/SLICE_16_1.md` | `d2fb55799608b92fbb0bc95b181c19f8` | `d2fb55799608b92fbb0bc95b181c19f8` | `93255848...` | Identical | PASS |
| `white_papers/final/WORK_BREAKDOWN_16.md` | `f925a781ac171c0c8ef6c2ae24c43c25` | `f925a781ac171c0c8ef6c2ae24c43c25` | `512f6ee2...` | Identical | PASS |
| `white_papers/final/RULINGS_B1_B2_B4.md` | `8dae3f6144d2434586e91a5aaa31a61b` | `8dae3f6144d2434586e91a5aaa31a61b` | `b3f61d67...` | Identical | PASS |
| `docs/01_DECISION_LOG.md` | `4a276b120a44f6ebca9fc466ff335cc3` | `4a276b120a44f6ebca9fc466ff335cc3` | `37d8d8d0...` | Identical | PASS |
| `docs/04_TECH_STACK.md` | `ac770556e48c1d989c2c923b1a57d74e` | `ac770556e48c1d989c2c923b1a57d74e` | `738eaf14...` | Identical | PASS |
| `BUILD_ORDER.md` | `5f5cdbd74e8fe4428311cad58343d5a3` | `5f5cdbd74e8fe4428311cad58343d5a3` | `c8e324bb...` | Identical | PASS |

No extraneous specification or documentation files exist in `~/teamwork_projects/clean_room_verification`. Exactly these 7 files exist.

### 1.3 RTL Bit-for-Bit Verification and Frozen Checksums Discrepancy
Comparison between `~/teamwork_projects/clean_room_verification/rtl_frozen` and `/mnt/Code/visualstudio/Design-arch_multi-core/rtl/`:

- **`pkg/tile_pkg.sv`**:
  - Clean-Room MD5: `b6ece1864f1ce6ddf5b6976775d34485` (9,133 bytes)
  - Source Repo MD5: `b6ece1864f1ce6ddf5b6976775d34485` (9,133 bytes)
  - Result: `cmp` MATCH.
- **`l1/l1_mesi_ctrl.sv`**:
  - Clean-Room MD5: `d63be56146cfd7f2c9f3682caf918809` (22,919 bytes)
  - Source Repo MD5: `d63be56146cfd7f2c9f3682caf918809` (22,919 bytes)
  - Result: `cmp` MATCH.
- **`directory/dir_ctrl.sv`**:
  - Clean-Room MD5: `4b8cca8381166c83ee61440ee2e45220` (26,207 bytes)
  - Source Repo `rtl/directory/dir_ctrl.sv` MD5: `acc52411a8b20d2c82771d4c8a28e187` (26,274 bytes)
  - Source Repo `rtl_frozen/directory/dir_ctrl.sv` MD5: `acc52411a8b20d2c82771d4c8a28e187` (26,274 bytes)
  - Result: **MISMATCH**!
  - `cmp` output:
    `/mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv differ: byte 1579, line 37`
  - Verbatim `diff -u` between clean room and source repo:
    ```diff
    --- /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv 2026-11-05 22:51:07.224485400 +0530
    +++ /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv 2026-11-05 23:14:06.332802800 +0530
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

### 1.4 Checksum Manifest Discrepancy (`FROZEN.md5`)
- Command: `cat /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5`
  Output:
  ```text
  b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
  d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
  4b8cca8381166c83ee61440ee2e45220  rtl_frozen/directory/dir_ctrl.sv
  ```
- Command: `cat /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5`
  Output:
  ```text
  b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
  d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
  acc52411a8b20d2c82771d4c8a28e187  rtl_frozen/directory/dir_ctrl.sv
  ```
- Internal validation in clean room:
  - Command: `cd /home/durgesh/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5`
  - Output:
    ```text
    rtl_frozen/pkg/tile_pkg.sv: OK
    rtl_frozen/l1/l1_mesi_ctrl.sv: OK
    rtl_frozen/directory/dir_ctrl.sv: OK
    ```
  - Exit code: 0.

### 1.5 Execution Context Sensitivity of `FROZEN.md5`
- Command: `cd /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen && md5sum -c FROZEN.md5`
- Output:
  ```text
  md5sum: rtl_frozen/pkg/tile_pkg.sv: No such file or directory
  rtl_frozen/pkg/tile_pkg.sv: FAILED open or read
  md5sum: rtl_frozen/l1/l1_mesi_ctrl.sv: No such file or directory
  rtl_frozen/l1/l1_mesi_ctrl.sv: FAILED open or read
  md5sum: rtl_frozen/directory/dir_ctrl.sv: No such file or directory
  rtl_frozen/directory/dir_ctrl.sv: FAILED open or read
  md5sum: WARNING: 3 listed files could not be read
  ```
- Exit code: 1.
- Reason: `FROZEN.md5` stores paths relative to the clean-room project root (`rtl_frozen/...`) rather than relative to the directory containing `FROZEN.md5`.

---

## 2. Logic Chain

1. **Isolation & Specification Integrity Confirmed (Observations 1.1 & 1.2)**:
   - Observation 1.1 proves that `~/teamwork_projects/clean_room_verification` is free of any legacy testbenches, hidden files, or symlinks.
   - Observation 1.2 proves that all 7 authorized specification files exist and are byte-for-byte identical to the repository versions with identical MD5 and SHA256 hashes.

2. **RTL Desynchronization & Frozen State Invalidation (Observations 1.3 & 1.4)**:
   - Observation 1.3 demonstrates that `rtl_frozen/directory/dir_ctrl.sv` in `clean_room_verification` differs from `rtl/directory/dir_ctrl.sv` in the repository.
   - The file in the repository was edited at `2026-11-05 23:14:06` to add `rxq_cnt_o`, after `worker_m1` populated `clean_room_verification` at `2026-11-05 23:11-23:12`.
   - Running `WAKE_UP.sh` in the source repository at `23:14:06` recalculated `rtl_frozen/FROZEN.md5` to reflect `acc52411a8b20d2c82771d4c8a28e187`.
   - As a result, the clean-room workspace has MD5 `4b8cca8381166c83ee61440ee2e45220` while the source repo has `acc52411a8b20d2c82771d4c8a28e187`.
   - Dispatch Step 3 explicitly mandates: *"Verify rtl_frozen/ matches original RTL bit-for-bit"*. This condition fails.

3. **Violation of the Read-Only Black Box Principle**:
   - The modification made to `rtl/directory/dir_ctrl.sv` at 23:14:06 added an output port (`rxq_cnt_o`) to facilitate formal assertions.
   - However, the clean-room rules state: *"The frozen RTL is a read-only black box. Violating this will invalidate the clean-room verification"*.
   - Either the RTL in `rtl/` was improperly mutated after freezing, OR the clean room was not updated to track an authorized RTL change. Either way, the two locations are inconsistent.

4. **WAKE_UP.sh Blind Re-freezing Vulnerability**:
   - Step 2 of `WAKE_UP.sh` computes `md5sum rtl_frozen/... > rtl_frozen/FROZEN.md5` without comparing against a baseline golden hash.
   - Consequently, running `WAKE_UP.sh` after modifying RTL silently blesses the modifications without any gate detection.

---

## 3. Caveats

- In accordance with the prompt's strict clean-room isolation mandate, no testbench source code in `tb_self_test/`, `tb/l1_dir/`, or scratch directories was opened or inspected.
- The clean-room copy of `dir_ctrl.sv` (`4b8cca8381166c83ee61440ee2e45220`) is self-consistent with the clean-room `rtl_frozen/FROZEN.md5`. The failure is the bit-for-bit divergence between the clean room and the source repository RTL.

---

## 4. Conclusion

**Verdict**: **CHALLENGE**

Although the clean-room workspace is clean of unauthorized files and contains all 7 authorized specification files bit-for-bit, it fails the mandatory requirement:
- **`rtl_frozen/` in `~/teamwork_projects/clean_room_verification` does NOT match the source repository's `rtl/` bit-for-bit**.
- `clean_room_verification/rtl_frozen/directory/dir_ctrl.sv` (MD5 `4b8cca8381166c83ee61440ee2e45220`) diverges from `rtl/directory/dir_ctrl.sv` and `rtl_frozen/directory/dir_ctrl.sv` in the repository (MD5 `acc52411a8b20d2c82771d4c8a28e187`).
- Clean-room `rtl_frozen/FROZEN.md5` does not match the source repository `rtl_frozen/FROZEN.md5`.

**Actionable Remediations**:
1. The orchestrator must decide whether `rxq_cnt_o` in `rtl/directory/dir_ctrl.sv` is authorized:
   - If unauthorized: Revert `rtl/directory/dir_ctrl.sv` to the clean-room version (`4b8cca8381166c83ee61440ee2e45220`), re-run `./WAKE_UP.sh` in the source repository, and verify that both source repo and clean room share `4b8cca8381166c83ee61440ee2e45220`.
   - If authorized: Sync the clean-room workspace `~/teamwork_projects/clean_room_verification/rtl_frozen/` and `FROZEN.md5` to `acc52411a8b20d2c82771d4c8a28e187`.
2. Hardcode expected MD5 values for frozen RTL in `WAKE_UP.sh` (similar to `verify_patch_set.py`) so future runs cannot silently re-freeze mutated RTL.

---

## 5. Verification Method

To independently reproduce this finding:

1. **Verify Checksum Mismatch between Clean Room and Source Repo**:
   ```bash
   cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
   # Output: differ: byte 1579, line 37 (exit code 1)
   ```

2. **Verify Checksums**:
   ```bash
   md5sum /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
   # Expected: acc52411a8b20d2c82771d4c8a28e187
   md5sum /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
   # Expected: 4b8cca8381166c83ee61440ee2e45220
   ```

3. **Verify FROZEN.md5 Mismatch**:
   ```bash
   diff -u /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5 /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
   # Output shows 4b8cca8381166c83ee61440ee2e45220 vs acc52411a8b20d2c82771d4c8a28e187
   ```
