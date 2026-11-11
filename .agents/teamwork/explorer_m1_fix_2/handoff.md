# Handoff Report: WAKE_UP.sh Step 2 Hardening Strategy

- **Agent**: `explorer_m1_fix_2` (`teamwork_explorer`)
- **Roles**: analyst, synthesizer
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_2`
- **Date**: 2026-11-05T18:10:00Z
- **Target Recipient**: Orchestrator (`b25d00b4-87e5-4b35-8417-bffe75bad4d9`) and subsequent Implementer agent

---

## 1. Observation

1. **Vulnerability in `WAKE_UP.sh` Step 2**:
   In `/mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh` lines 49–51:
   ```bash
   md5sum rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv > rtl_frozen/FROZEN.md5
   echo "Generated rtl_frozen/FROZEN.md5:"
   cat rtl_frozen/FROZEN.md5
   ```
   Step 2 overwrites `rtl_frozen/FROZEN.md5` directly from the current files in `rtl/` without checking against an immutable golden manifest.

2. **Source RTL Hash Mismatch / Drift in `dir_ctrl.sv`**:
   Executing `md5sum rtl/pkg/tile_pkg.sv rtl/l1/l1_mesi_ctrl.sv rtl/directory/dir_ctrl.sv` in `/mnt/Code/visualstudio/Design-arch_multi-core`:
   ```text
   b6ece1864f1ce6ddf5b6976775d34485  rtl/pkg/tile_pkg.sv
   d63be56146cfd7f2c9f3682caf918809  rtl/l1/l1_mesi_ctrl.sv
   acc52411a8b20d2c82771d4c8a28e187  rtl/directory/dir_ctrl.sv
   ```
   Authoritative golden baseline hashes specified in project dispatch and clean-room workspace (`~/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5`):
   ```text
   b6ece1864f1ce6ddf5b6976775d34485  rtl/pkg/tile_pkg.sv
   d63be56146cfd7f2c9f3682caf918809  rtl/l1/l1_mesi_ctrl.sv
   4b8cca8381166c83ee61440ee2e45220  rtl/directory/dir_ctrl.sv
   ```
   `rtl/directory/dir_ctrl.sv` has drifted from `4b8cca8381166c83ee61440ee2e45220` to `acc52411a8b20d2c82771d4c8a28e187`.

3. **Exact Difference in `rtl/directory/dir_ctrl.sv`**:
   `diff -u /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/dir_ctrl.sv rtl/directory/dir_ctrl.sv`:
   ```diff
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
   Removing lines 37 and 661 returns the file's MD5 checksum exactly to `4b8cca8381166c83ee61440ee2e45220`.

4. **Sandbox Negative and Positive Validation**:
   In a standalone sandbox (`/tmp/`):
   - With hardened Step 2 and drifted `dir_ctrl.sv`: execution terminated with exit code `1`, printing `ERROR: Checksum mismatch for source RTL 'rtl/directory/dir_ctrl.sv'! Expected: 4b8cca8381166c83ee61440ee2e45220 Actual: acc52411a8b20d2c82771d4c8a28e187`, and aborted snapshotting.
   - With hardened Step 2 and golden `dir_ctrl.sv`: execution succeeded with exit code `0`, all 4 steps logged `PASS`, and 3 consecutive runs proved idempotency.

---

## 2. Logic Chain

1. **From Observation 1 to Vulnerability Definition**:
   Because Step 2 dynamically recomputes MD5 checksums on every run and writes them into `FROZEN.md5`, Step 4 (`md5sum -c rtl_frozen/FROZEN.md5`) only tests that the filesystem read back what was just written. It provides zero protection against unauthorized changes in `rtl/`.
2. **From Observation 2 and 3 to Exploit Confirmation**:
   Because `rtl/directory/dir_ctrl.sv` was modified to expose `rxq_cnt_o`, running `WAKE_UP.sh` under its current implementation silently overwrote `rtl_frozen/` and `FROZEN.md5` with the mutated hash (`acc52411a8b20d2c82771d4c8a28e187`), diverging from the clean-room environment.
3. **From Observations 1–4 to Placement in Step 2**:
   Hardening must be placed in Step 2 *before* copying files. If placed only in Step 4, `WAKE_UP.sh` would have already overwritten `rtl_frozen/` with corrupted files before failing. Placing validation in Step 2 ensures `rtl_frozen/` is never modified unless the source matches the golden baseline.
4. **From Observation 4 to Remediation Feasibility**:
   The sandbox test proves that reverting lines 37 and 661 of `rtl/directory/dir_ctrl.sv` plus injecting the Step 2 validation loop into `WAKE_UP.sh` resolves the drift, detects future tampering with exit code 1, and restores clean-room reset integrity with exit code 0.

---

## 3. Caveats

- **Explorer Read-Only Constraint**: In strict adherence to the teamwork explorer role, no project source files (`WAKE_UP.sh`, `rtl/directory/dir_ctrl.sv`) were modified directly by this agent. All code modifications are documented for the implementer agent.
- **Clean-Room Isolation**: Quarantined test source directories (`tb/self_test/`, `tb/l1_dir/`, etc.) were NOT read or inspected.
- **Milestone Scope**: This hardening focuses exclusively on M1 isolation integrity. Subsequent testbench developments (M2–M5) in `clean_room_verification` must reference the golden RTL (`4b8cca8381166c83ee61440ee2e45220`), which does not expose `rxq_cnt_o`.

---

## 4. Conclusion

The architectural hardening of `WAKE_UP.sh` requires two concrete actions:
1. **Revert uncommitted modifications in `rtl/directory/dir_ctrl.sv`**:
   Remove lines 37 and 661 to restore golden baseline MD5 `4b8cca8381166c83ee61440ee2e45220`.
2. **Harden Step 2 in `WAKE_UP.sh`**:
   Embed the golden baseline constants and pre-snapshot validation loop:
   - `GOLDEN_TILE_PKG_MD5="b6ece1864f1ce6ddf5b6976775d34485"`
   - `GOLDEN_L1_MESI_CTRL_MD5="d63be56146cfd7f2c9f3682caf918809"`
   - `GOLDEN_DIR_CTRL_MD5="4b8cca8381166c83ee61440ee2e45220"`
   Aborting with exit code `1` before snapshotting if any checksum deviates.

Full technical details, git diffs, and sandbox verification logs are provided in `report.md`.

---

## 5. Verification Method

Once the implementer applies the changes, verify using the following commands:

1. **Verify Source RTL Checksums**:
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

2. **Verify `WAKE_UP.sh` Normal and Idempotent Execution**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core
   ./WAKE_UP.sh
   ./WAKE_UP.sh
   ```
   Both runs must exit `0` and report `PASS` on all 4 steps.

3. **Verify Negative Tamper Detection**:
   ```bash
   (DIR=$(mktemp -d) && cp -r pd rtl WAKE_UP.sh "$DIR" && cd "$DIR" && \
    echo "// tamper" >> rtl/directory/dir_ctrl.sv && ./WAKE_UP.sh; rm -rf "$DIR")
   ```
   Must exit with code `1` and print:
   `ERROR: Golden baseline hash mismatch for source RTL 'rtl/directory/dir_ctrl.sv'!`

4. **Verify Parity with Clean-Room Workspace**:
   ```bash
   diff -u /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5 \
           /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
   ```
   Must produce empty output (100% identical).
