# Empirical Challenge Report: WAKE_UP.sh and Clean-Room Isolation

- **Agent**: `challenger_m1_1` (`teamwork_challenger`)
- **Roles**: critic, specialist
- **Date**: 2026-11-05T17:50:00Z
- **Verdict**: **APPROVE WITH CRITICAL CHALLENGES**

---

## 1. Observation

### Observation 1: Normal Execution of `WAKE_UP.sh`
- Command: `cd /mnt/Code/visualstudio/Design-arch_multi-core && ./WAKE_UP.sh`
- Verbatim stdout/stderr:
  ```text
  ========================================================
  Starting Clean-Room Reset Protocol (WAKE_UP.sh)
  Working directory: /mnt/Code/visualstudio/Design-arch_multi-core
  ========================================================
  [Step 1/4] Verifying pd/v1/verify_patch_set.py checksum...
  Step 1 PASS: pd/v1/verify_patch_set.py matches 4c4370f50882e82399b65076147bf112
  [Step 2/4] Snapshotting RTL under test into rtl_frozen/...
  Generated rtl_frozen/FROZEN.md5:
  b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
  d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
  acc52411a8b20d2c82771d4c8a28e187  rtl_frozen/directory/dir_ctrl.sv
  Step 2 PASS: RTL snapshot created.
  [Step 3/4] Quarantining existing self-tests into tb_self_test/...
  tb_self_test/l1_dir already quarantined.
  Step 3 PASS: Quarantine complete and tb_self_test/README.md created.
  [Step 4/4] Validating frozen RTL checksums...
  rtl_frozen/pkg/tile_pkg.sv: OK
  rtl_frozen/l1/l1_mesi_ctrl.sv: OK
  rtl_frozen/directory/dir_ctrl.sv: OK
  Step 4 PASS: Checksum validation succeeded.
  ========================================================
  WAKE_UP: 4-step reset cleanly completed.
  ========================================================
  ```
- Exit code: `0`. All 4 steps reported `PASS`.

### Observation 2: Idempotency Testing
- Command: Consecutive executions in loop:
  ```bash
  for i in {1..3}; do ./WAKE_UP.sh; done
  ```
- Result: Each run succeeded with exit code `0` and identical output. In Step 3, `tb_self_test/l1_dir already quarantined.` was logged without error.

### Observation 3: Negative Stress Testing (Sandbox)
Executed an isolated battery of 6 failure/tamper tests in `/tmp/wake_up_sandbox`:
1. **Tampered `pd/v1/verify_patch_set.py` content**:
   - Exit code: `1`
   - Output:
     ```text
     ERROR: Checksum mismatch for pd/v1/verify_patch_set.py!
       Expected: 4c4370f50882e82399b65076147bf112
       Actual:   68f308060004b7f8e33776272a637cca
     ```
2. **Missing `pd/v1/verify_patch_set.py`**:
   - Exit code: `1`
   - Output: `ERROR: Verifier script 'pd/v1/verify_patch_set.py' not found!`
3. **Dummy / altered hash in `EXPECTED_VERIFIER_MD5`**:
   - Exit code: `1`
   - Output: `ERROR: Checksum mismatch for pd/v1/verify_patch_set.py!`
4. **Missing source RTL (`rtl/l1/l1_mesi_ctrl.sv`)**:
   - Exit code: `1`
   - Output: `cp: cannot stat 'rtl/l1/l1_mesi_ctrl.sv': No such file or directory`
5. **Corrupted frozen RTL during validation (tampering after snapshot)**:
   - Exit code: `1`
   - Output:
     ```text
     rtl_frozen/pkg/tile_pkg.sv: FAILED
     rtl_frozen/l1/l1_mesi_ctrl.sv: OK
     rtl_frozen/directory/dir_ctrl.sv: OK
     md5sum: WARNING: 1 computed checksum did NOT match
     ```

### Observation 4: Checksum Discrepancy between Source and Clean-Room Target
- Command:
  ```bash
  diff -u rtl_frozen/FROZEN.md5 /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
  ```
- Output:
  ```diff
  --- rtl_frozen/FROZEN.md5
  +++ /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
  @@ -1,3 +1,3 @@
   b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
   d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
  -acc52411a8b20d2c82771d4c8a28e187  rtl_frozen/directory/dir_ctrl.sv
  +4b8cca8381166c83ee61440ee2e45220  rtl_frozen/directory/dir_ctrl.sv
  ```
- Inspection of `diff -u rtl/directory/dir_ctrl.sv /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/dir_ctrl.sv`:
  ```diff
  @@ -34,7 +34,6 @@
       output pending_op_t pending_op_o,
       output logic [TILE_ID_W-1:0] req_tile_o,
       output logic rxq_empty_o,
  -    output logic [2:0] rxq_cnt_o,
       output msg_type_t rx_msg_o,
       output logic [TILE_ID_W-1:0] rx_src_o,
       output logic        rx_oflow_o,
  @@ -658,7 +657,6 @@
     assign pending_op_o = pending_op;
     assign req_tile_o   = req_tile;
     assign rxq_empty_o  = rxq_empty;
  -  assign rxq_cnt_o    = rxq_cnt;
     assign rx_msg_o     = msg_type_t'(h_msg);
     assign rx_src_o     = h_src;
     assign dtr_busy    = (state != DIR_I);
  ```
  The clean-room workspace was snapshot at 23:11 with hash `4b8cca8381166c83ee61440ee2e45220`. Subsequently at 23:14, `rtl/directory/dir_ctrl.sv` in the source repository was modified to expose `rxq_cnt_o`, producing hash `acc52411a8b20d2c82771d4c8a28e187`.

### Observation 5: In-Place Hash Regeneration in `WAKE_UP.sh`
- Line 49 of `WAKE_UP.sh`:
  ```bash
  md5sum rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv > rtl_frozen/FROZEN.md5
  ```
  Step 2 overwrites `rtl_frozen/FROZEN.md5` directly from the current files in `rtl/`. It does not compare against a pre-established immutable golden hash manifest for the RTL.

---

## 2. Logic Chain

1. **Step-by-Step Reset Validation**:
   - Observations 1 and 2 prove that `WAKE_UP.sh` correctly executes all 4 steps, terminates with exit code 0, and exhibits repeatable idempotency without race conditions or erroring on pre-existing quarantined directories.
2. **Defensive Error Detection**:
   - Observation 3 proves that `WAKE_UP.sh` enforces cryptographic integrity on `pd/v1/verify_patch_set.py` and halts under `set -euo pipefail` whenever verifier scripts are tampered with, missing, or when frozen files are altered.
3. **Identification of Drift**:
   - Observation 4 establishes that `rtl/directory/dir_ctrl.sv` was changed after `clean_room_verification` was initialized by `worker_m1`. This causes the clean-room workspace (`~/teamwork_projects/clean_room_verification/rtl_frozen`) and the source repository (`/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen`) to run on two different versions of `dir_ctrl.sv`.
4. **Failure to Detect Future RTL Mutations in Reset**:
   - Observation 5 reveals that because Step 2 dynamically recomputes `FROZEN.md5` on every run, running `WAKE_UP.sh` will overwrite `rtl_frozen/` and overwrite `FROZEN.md5` without alerting the user that the RTL was modified.

---

## 3. Caveats

- We did not modify any source code in `rtl/` or `WAKE_UP.sh`, strictly adhering to review-only constraints.
- We did not read or inspect any quarantined test code in `tb/l1_dir` or `tb_self_test/`, strictly maintaining clean-room isolation.
- Acceptance tests (M2–M5) have not yet been run against either snapshot; the decision on which RTL hash is authoritative rests with the orchestrator.

---

## 4. Conclusion & Challenges

### Verdict: APPROVE WITH CRITICAL CHALLENGES

`WAKE_UP.sh` successfully satisfies all M1 functional requirements:
- Exits 0 under normal run with all 4 steps reporting PASS.
- Fully idempotent across multiple consecutive runs.
- Detects tamper and missing files cleanly with non-zero exit codes.

### Critical Challenges:

#### [CRITICAL] Challenge 1: RTL Checksum Drift between Repositories
- **Assumption Challenged**: The frozen RTL under test in `~/teamwork_projects/clean_room_verification/rtl_frozen` is identical to the snapshot generated by `WAKE_UP.sh`.
- **Finding**: They differ.
  - Source repo `dir_ctrl.sv`: `acc52411a8b20d2c82771d4c8a28e187` (includes `output logic [2:0] rxq_cnt_o`)
  - Clean-room repo `dir_ctrl.sv`: `4b8cca8381166c83ee61440ee2e45220` (omits `rxq_cnt_o`)
- **Blast Radius**: Verification benches in `clean_room_verification` referencing `rxq_cnt_o` will fail to compile or bind. If tests assume the source tree RTL, they will diverge from the clean-room snapshot.
- **Recommended Mitigation**:
  Synchronize `clean_room_verification/rtl_frozen` by copying the updated snapshot from `/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/` and updating its `FROZEN.md5` to `acc52411a8b20d2c82771d4c8a28e187`, OR if the edit to `dir_ctrl.sv` was unintended, revert `rtl/directory/dir_ctrl.sv` back to `4b8cca8381166c83ee61440ee2e45220` and re-run `WAKE_UP.sh`.

#### [HIGH] Challenge 2: Dynamic Regeneration vs Golden Manifest Validation
- **Assumption Challenged**: Step 4 validates RTL against an immutable freeze baseline.
- **Finding**: Step 2 overwrites `rtl_frozen/FROZEN.md5` from `rtl/` on every run. If someone modifies `rtl/` in the future, `WAKE_UP.sh` silently snapshots the modified RTL and recalculates a new hash. Step 4 only checks against the hash generated seconds earlier in Step 2.
- **Blast Radius**: Silent violations of "RTL under test must NEVER be modified."
- **Recommended Mitigation**: Embed expected golden hashes in `WAKE_UP.sh` (or check against an immutable manifest such as `docs/manifests/rtl_manifest.md5`), failing if `rtl/` has deviated from the golden baseline.

---

## 5. Verification Method

1. **Verify Normal & Idempotent Run**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core
   ./WAKE_UP.sh
   ./WAKE_UP.sh
   # Both must exit 0 and log all 4 steps PASS
   ```

2. **Verify Checksum Drift**:
   ```bash
   diff -u /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5 \
           /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
   # Line 3 shows acc52411a8b20d2c82771d4c8a28e187 vs 4b8cca8381166c83ee61440ee2e45220
   ```

3. **Verify Sandbox Tamper Detection**:
   ```bash
   # Run in temporary subshell with tampered verify_patch_set.py
   (DIR=$(mktemp -d) && cp -r pd rtl WAKE_UP.sh "$DIR" && cd "$DIR" && \
    echo "# tamper" >> pd/v1/verify_patch_set.py && ./WAKE_UP.sh; rm -rf "$DIR")
   # Must exit 1 with checksum mismatch error
   ```
