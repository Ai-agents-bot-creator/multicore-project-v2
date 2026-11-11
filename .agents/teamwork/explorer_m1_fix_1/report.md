# Comprehensive Analysis & Fix Strategy Report: `dir_ctrl.sv` Clean-Room Baseline Restoration

- **Agent**: `explorer_m1_fix_1` (`teamwork_explorer`)
- **Working Directory**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/explorer_m1_fix_1`
- **Date**: 2026-11-05T17:55:00Z
- **Target DUT**: Directory Controller (`rtl/directory/dir_ctrl.sv`)
- **Baseline Checksum**: `4b8cca8381166c83ee61440ee2e45220` (Pristine clean-room baseline)
- **Mutated Checksum**: `acc52411a8b20d2c82771d4c8a28e187` (Current in source repository)

---

## 1. Executive Summary

Milestone 1 gate checks resulted in a **REQUEST_CHANGES** verdict from `reviewer_m1_2` and a **CHALLENGE** from `challenger_m1_2` due to an integrity breach:
1. `rtl/directory/dir_ctrl.sv` in the source repository `/mnt/Code/visualstudio/Design-arch_multi-core` was modified at `2026-11-05 23:14:06`, injecting an extra observability port `output logic [2:0] rxq_cnt_o` and continuous assignment `assign rxq_cnt_o = rxq_cnt;`. This changed the file's MD5 checksum from `4b8cca8381166c83ee61440ee2e45220` to `acc52411a8b20d2c82771d4c8a28e187`.
2. The isolated clean-room workspace at `/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv` preserves the true baseline `4b8cca8381166c83ee61440ee2e45220`. Consequently, the clean-room acceptance test workspace and the source repository are out of sync and testing different RTL designs.
3. The reset automation script `WAKE_UP.sh` suffers from a **self-certifying snapshot vulnerability**: it unconditionally copies `rtl/` into `rtl_frozen/` and dynamically generates `FROZEN.md5` without validating the incoming RTL against immutable golden baseline checksums. Running `./WAKE_UP.sh` after the mutation silently certified the modified RTL as "PASS".

This report details the exact diff, analyzes its functional and architectural impact, explains why this change strictly violates clean-room verification rules, and provides an exact, turnkey fix strategy for the worker agent to revert `dir_ctrl.sv` and harden `WAKE_UP.sh`.

---

## 2. RTL Diff Analysis (`dir_ctrl.sv`)

### 2.1 Checksum & File Metric Comparison

| File Location | MD5 Checksum | Size (Bytes) | Line Count | Status |
|---|---|---|---|---|
| `/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv` | `4b8cca8381166c83ee61440ee2e45220` | 26,207 | 668 | **Authoritative Baseline** |
| `/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/dir_ctrl.sv` | `4b8cca8381166c83ee61440ee2e45220` | 26,207 | 668 | **Authoritative Baseline** |
| `/mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv` | `acc52411a8b20d2c82771d4c8a28e187` | 26,274 | 670 | **Mutated (+67 bytes)** |
| `/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/directory/dir_ctrl.sv` | `acc52411a8b20d2c82771d4c8a28e187` | 26,274 | 670 | **Mutated (+67 bytes)** |
| `/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/dir_ctrl.sv` | `acc52411a8b20d2c82771d4c8a28e187` | 26,274 | 670 | **Mutated (+67 bytes)** |

### 2.2 Verbatim Contextual Diff

Executing `diff -u` between the clean-room baseline and the current source repository RTL produces:

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

### 2.3 Detailed Examination of Injected Code

1. **Port Declaration (Line 37 in mutated file)**:
   ```systemverilog
   output logic [2:0] rxq_cnt_o,
   ```
   Inserted immediately following `output logic rxq_empty_o,` inside the module port list of `dir_ctrl`.
2. **Signal Assignment (Line 661 in mutated file)**:
   ```systemverilog
   assign rxq_cnt_o    = rxq_cnt;
   ```
   Inserted in the continuous assignment block exposing internal register `rxq_cnt` (the mailbox receive queue occupancy counter, range `0..4`) directly out to the module boundary.

---

## 3. Root Cause & Impact Analysis

### 3.1 Timeline Reconstruction

1. **22:51:07**: Authoritative RTL files (`tile_pkg.sv`, `l1_mesi_ctrl.sv`, `dir_ctrl.sv`) generated and settled with clean-room baseline hashes:
   - `tile_pkg.sv`: `b6ece1864f1ce6ddf5b6976775d34485`
   - `l1_mesi_ctrl.sv`: `d63be56146cfd7f2c9f3682caf918809`
   - `dir_ctrl.sv`: `4b8cca8381166c83ee61440ee2e45220`
2. **23:11:54**: `worker_m1` initialized the clean-room workspace at `/home/durgesh/teamwork_projects/clean_room_verification`, copying the baseline `dir_ctrl.sv` (`4b8cca8381166c83ee61440ee2e45220`) and generating clean-room `rtl_frozen/FROZEN.md5`.
3. **23:14:06**: In `/mnt/Code/visualstudio/Design-arch_multi-core`, `rtl/directory/dir_ctrl.sv` was edited in-place to expose `rxq_cnt_o`. This alteration was likely introduced while experimenting with formal verification SVA assertions or queue occupancy tracking.
4. **23:19:49**: `./WAKE_UP.sh` was re-run in `/mnt/Code/visualstudio/Design-arch_multi-core`. Because `WAKE_UP.sh` blindly copied `rtl/` to `rtl_frozen/` and generated a new `FROZEN.md5`, it adopted `acc52411a8b20d2c82771d4c8a28e187` and declared all steps `PASS`.
5. **23:20–23:22**: Independent audits by `reviewer_m1_2` and `challenger_m1_2` flagged the checksum mismatch and issued `REQUEST_CHANGES` / `CHALLENGE`.

### 3.2 Violation of Core Verification Contracts

The injection of `rxq_cnt_o` violates several fundamental project rules:
1. **Read-Only Black Box Mandate**:
   - `ORIGINAL_REQUEST.md §R1` explicitly commands: *"The frozen RTL is a read-only black box. RTL under test must NEVER be modified."*
   - `PROJECT.md §Architecture`: *"The frozen RTL is a read-only black box. RTL under test must NEVER be modified."*
   Modifying the RTL under test to expose internal state invalidates black-box clean-room verification.
2. **Specification & Interface Contract Deviation**:
   - `white_papers/final/SLICE_16_1.md` and `docs/04_TECH_STACK.md` define the top-level interfaces. `rxq_cnt_o` is not part of the specified directory controller contract.
   - Grep verification across `docs/` and `white_papers/` shows **zero occurrences** of `rxq_cnt_o`.
3. **Split-Brain Workspace State**:
   - The clean-room acceptance test workspace (`~/teamwork_projects/clean_room_verification`) is running against `4b8cca8381166c83ee61440ee2e45220`.
   - The repository `/mnt/Code/visualstudio/Design-arch_multi-core` was running against `acc52411a8b20d2c82771d4c8a28e187`.
   - Any test or wrapper written against one environment would fail or misbehave in the other.
4. **Integration Hazards**:
   - Any higher-level module or test wrapper instantiating `dir_ctrl` with named port mappings or strict port binding without `rxq_cnt_o` would fail linting or compile checks if `rxq_cnt_o` is unexpectedly present.

### 3.3 Root Cause of Detection Failure in `WAKE_UP.sh`

In `WAKE_UP.sh`:
- Step 1 rigorously verifies `pd/v1/verify_patch_set.py` against `4c4370f50882e82399b65076147bf112`.
- Step 2 creates `rtl_frozen/` and executes:
  ```bash
  md5sum rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv > rtl_frozen/FROZEN.md5
  ```
- Step 4 checks:
  ```bash
  md5sum -c rtl_frozen/FROZEN.md5
  ```
This is circular validation: Step 4 checks `rtl_frozen` against the file produced in Step 2 from `rtl/`. If `rtl/` is modified, Step 2 stamps the new hash into `FROZEN.md5`, and Step 4 reports `OK`.
To be an effective security gate, `WAKE_UP.sh` must validate `rtl/` against immutable reference hashes **before** performing the snapshot.

---

## 4. Comprehensive Fix Strategy

To resolve the review failure and restore clean-room integrity, the implementation agent must execute a 5-step fix sequence:

```
[Step 1: Revert RTL] ────► [Step 2: Harden WAKE_UP.sh] ────► [Step 3: Execute WAKE_UP.sh]
                                                                        │
[Step 5: Document]   ◄──── [Step 4: Cross-Workspace Verification] ◄─────┘
```

### Step 1: Revert `rtl/directory/dir_ctrl.sv` to Pristine Baseline
Revert `/mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv` to match `/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv`.
- Either copy directly from the pristine clean-room snapshot:
  ```bash
  cp -p /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv \
        /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
  ```
- Or remove lines 37 and 661 using the diff patch provided in Section 5.1.
- Target MD5: `4b8cca8381166c83ee61440ee2e45220` (exactly 26,207 bytes).

### Step 2: Harden `WAKE_UP.sh` with Golden Baseline Hash Verification
Update `WAKE_UP.sh` to validate `rtl/pkg/tile_pkg.sv`, `rtl/l1/l1_mesi_ctrl.sv`, and `rtl/directory/dir_ctrl.sv` against their authoritative baseline hashes **prior** to snapshotting.
- Golden Baseline Hashes to hardcode:
  - `EXPECTED_TILE_PKG_MD5="b6ece1864f1ce6ddf5b6976775d34485"`
  - `EXPECTED_L1_MESI_MD5="d63be56146cfd7f2c9f3682caf918809"`
  - `EXPECTED_DIR_CTRL_MD5="4b8cca8381166c83ee61440ee2e45220"`
- If any file deviates, `WAKE_UP.sh` must abort immediately with a non-zero exit code (`exit 1`) and display the expected vs actual checksums.

### Step 3: Execute `./WAKE_UP.sh` in the Source Repository
Run `./WAKE_UP.sh` from `/mnt/Code/visualstudio/Design-arch_multi-core`.
- Refreshes both hierarchical (`rtl_frozen/directory/dir_ctrl.sv`) and flat (`rtl_frozen/dir_ctrl.sv`) frozen snapshots.
- Re-generates `rtl_frozen/FROZEN.md5` with `4b8cca8381166c83ee61440ee2e45220`.
- Verifies that all 4 steps exit 0 and log `PASS`.

### Step 4: Perform Cross-Workspace Bit-for-Bit Verification
Confirm that:
1. `cmp` between source repository `rtl/directory/dir_ctrl.sv` and clean-room `rtl_frozen/directory/dir_ctrl.sv` outputs 0 differences.
2. `diff -u` between `/mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5` and `/home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5` outputs 0 differences.
3. `cd /home/durgesh/teamwork_projects/clean_room_verification && md5sum -c rtl_frozen/FROZEN.md5` passes with exit code 0.

### Step 5: Update Attestations
Update `worker_m1/handoff.md` (or generate `worker_m1_fix_1/handoff.md`) with reproducible logs reflecting the restored `4b8cca8381166c83ee61440ee2e45220` hash.

---

## 5. Concrete Code & Script Proposals for Implementer

### 5.1 Reversion Patch for `rtl/directory/dir_ctrl.sv`

```diff
--- a/rtl/directory/dir_ctrl.sv
+++ b/rtl/directory/dir_ctrl.sv
@@ -34,7 +34,6 @@ module dir_ctrl import tile_pkg::*; (
     output pending_op_t pending_op_o,
     output logic [TILE_ID_W-1:0] req_tile_o,
     output logic rxq_empty_o,
-    output logic [2:0] rxq_cnt_o,
     output msg_type_t rx_msg_o,
     output logic [TILE_ID_W-1:0] rx_src_o,
     output logic        rx_oflow_o,
@@ -658,7 +657,6 @@ module dir_ctrl import tile_pkg::*; (
   assign pending_op_o = pending_op;
   assign req_tile_o   = req_tile;
   assign rxq_empty_o  = rxq_empty;
-  assign rxq_cnt_o    = rxq_cnt;
   assign rx_msg_o     = msg_type_t'(h_msg);
   assign rx_src_o     = h_src;
   assign dtr_busy    = (state != DIR_I);
```

### 5.2 Proposed Hardened `WAKE_UP.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# WAKE_UP.sh — 4-Step Clean-Room Reset Script
# Automates environment verification, golden baseline enforcement, RTL snapshotting, and test quarantine.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "========================================================"
echo "Starting Clean-Room Reset Protocol (WAKE_UP.sh)"
echo "Working directory: $REPO_ROOT"
echo "========================================================"

# Step 1: Verify pd/v1/verify_patch_set.py checksum
echo "[Step 1/4] Verifying pd/v1/verify_patch_set.py checksum..."
VERIFIER="pd/v1/verify_patch_set.py"
EXPECTED_VERIFIER_MD5="4c4370f50882e82399b65076147bf112"

if [ ! -f "$VERIFIER" ]; then
    echo "ERROR: Verifier script '$VERIFIER' not found!" >&2
    exit 1
fi

ACTUAL_VERIFIER_MD5=$(md5sum "$VERIFIER" | awk '{print $1}')
if [ "$ACTUAL_VERIFIER_MD5" != "$EXPECTED_VERIFIER_MD5" ]; then
    echo "ERROR: Checksum mismatch for $VERIFIER!" >&2
    echo "  Expected: $EXPECTED_VERIFIER_MD5" >&2
    echo "  Actual:   $ACTUAL_VERIFIER_MD5" >&2
    exit 1
fi
echo "Step 1 PASS: $VERIFIER matches $EXPECTED_VERIFIER_MD5"

# Step 2: Validate baseline RTL checksums & snapshot into rtl_frozen/
echo "[Step 2/4] Validating source RTL against golden baselines and snapshotting into rtl_frozen/..."

EXPECTED_TILE_PKG_MD5="b6ece1864f1ce6ddf5b6976775d34485"
EXPECTED_L1_MESI_MD5="d63be56146cfd7f2c9f3682caf918809"
EXPECTED_DIR_CTRL_MD5="4b8cca8381166c83ee61440ee2e45220"

for item in "rtl/pkg/tile_pkg.sv:$EXPECTED_TILE_PKG_MD5" \
            "rtl/l1/l1_mesi_ctrl.sv:$EXPECTED_L1_MESI_MD5" \
            "rtl/directory/dir_ctrl.sv:$EXPECTED_DIR_CTRL_MD5"; do
    FILE="${item%%:*}"
    EXP="${item##*:}"
    if [ ! -f "$FILE" ]; then
        echo "ERROR: RTL file '$FILE' not found!" >&2
        exit 1
    fi
    ACT=$(md5sum "$FILE" | awk '{print $1}')
    if [ "$ACT" != "$EXP" ]; then
        echo "ERROR: Golden baseline mismatch for $FILE!" >&2
        echo "  Expected: $EXP" >&2
        echo "  Actual:   $ACT" >&2
        echo "Clean-room violation: RTL under test must NEVER be modified!" >&2
        exit 1
    fi
done
echo "Golden baseline verified: all source RTL files match clean-room reference."

mkdir -p rtl_frozen/pkg rtl_frozen/l1 rtl_frozen/directory

# Copy hierarchical structure
cp -p rtl/pkg/tile_pkg.sv rtl_frozen/pkg/tile_pkg.sv
cp -p rtl/l1/l1_mesi_ctrl.sv rtl_frozen/l1/l1_mesi_ctrl.sv
cp -p rtl/directory/dir_ctrl.sv rtl_frozen/directory/dir_ctrl.sv

# Also copy flat files to support flat directory layouts
cp -p rtl/pkg/tile_pkg.sv rtl_frozen/tile_pkg.sv
cp -p rtl/l1/l1_mesi_ctrl.sv rtl_frozen/l1_mesi_ctrl.sv
cp -p rtl/directory/dir_ctrl.sv rtl_frozen/dir_ctrl.sv

# Generate rtl_frozen/FROZEN.md5
md5sum rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv > rtl_frozen/FROZEN.md5
echo "Generated rtl_frozen/FROZEN.md5:"
cat rtl_frozen/FROZEN.md5
echo "Step 2 PASS: RTL snapshot created and verified against golden baselines."

# Step 3: Quarantine existing self-tests
echo "[Step 3/4] Quarantining existing self-tests into tb_self_test/..."
mkdir -p tb_self_test
if [ -d "tb/l1_dir" ]; then
    mv tb/l1_dir tb_self_test/l1_dir
    echo "Moved tb/l1_dir -> tb_self_test/l1_dir"
elif [ -d "tb_self_test/l1_dir" ]; then
    echo "tb_self_test/l1_dir already quarantined."
else
    echo "Notice: Neither tb/l1_dir nor tb_self_test/l1_dir found."
fi

cat <<'EOF' > tb_self_test/README.md
# Quarantined Self-Tests

This directory contains quarantined legacy self-tests moved from `tb/l1_dir`.

## Clean-Room Isolation Protocol
Under clean-room verification rules:
- Engineers and verification agents MUST NOT read, inspect, or copy test source code from this directory (`tb_self_test/`) or any prior test suites.
- Acceptance tests must be independently developed from authoritative specification documents alone.
- RTL under test in `rtl_frozen/` is treated strictly as a read-only black box.
EOF
echo "Step 3 PASS: Quarantine complete and tb_self_test/README.md created."

# Step 4: Verify md5sum -c rtl_frozen/FROZEN.md5
echo "[Step 4/4] Validating frozen RTL checksums..."
md5sum -c rtl_frozen/FROZEN.md5
echo "Step 4 PASS: Checksum validation succeeded."

echo "========================================================"
echo "WAKE_UP: 4-step reset cleanly completed."
echo "========================================================"
```

---

## 6. Verification and Invalidation Criteria

### 6.1 Independent Verification Commands

1. **Verify `rtl/directory/dir_ctrl.sv` Restored**:
   ```bash
   md5sum /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv
   # MUST return: 4b8cca8381166c83ee61440ee2e45220
   ```
2. **Verify Bit-for-Bit Match Across Workspaces**:
   ```bash
   cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl/directory/dir_ctrl.sv \
       /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv
   # MUST exit 0 with no differences.
   ```
3. **Verify `WAKE_UP.sh` Execution**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core && ./WAKE_UP.sh
   # Step 2 MUST print:
   # b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
   # d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
   # 4b8cca8381166c83ee61440ee2e45220  rtl_frozen/directory/dir_ctrl.sv
   # Entire script MUST exit 0.
   ```
4. **Verify `FROZEN.md5` Parity**:
   ```bash
   diff -u /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5 \
           /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5
   # MUST output 0 differences.
   ```
5. **Verify Tamper Guard in `WAKE_UP.sh`**:
   ```bash
   # Test in a sandbox: appending a comment to dir_ctrl.sv must cause WAKE_UP.sh to fail at Step 2
   (DIR=$(mktemp -d) && cp -r /mnt/Code/visualstudio/Design-arch_multi-core/{pd,rtl,WAKE_UP.sh} "$DIR" && \
    cd "$DIR" && echo "// tamper" >> rtl/directory/dir_ctrl.sv && ! ./WAKE_UP.sh; rm -rf "$DIR")
   # MUST exit 1 with "Golden baseline mismatch for rtl/directory/dir_ctrl.sv!".
   ```

### 6.2 Invalidation Conditions
This analysis and strategy would be invalidated if:
- The orchestrator or supervisor explicitly issues a new ruling authorizing an interface change to `dir_ctrl.sv` to add `rxq_cnt_o`.
- The clean room `rtl_frozen/` is found to be corrupt (verified: clean room is pristine and uncorrupted).
