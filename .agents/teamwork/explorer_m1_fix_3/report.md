# Milestone 1: Workspace Synchronization & Re-Verification Technical Report

**Agent**: `explorer_m1_fix_3` (`teamwork_explorer`)  
**Date**: 2026-11-05T17:58:00Z  
**Target Workspaces**:  
- Source Repository: `/mnt/Code/visualstudio/Design-arch_multi-core`
- Clean-Room Workspace: `/home/durgesh/teamwork_projects/clean_room_verification`  
**Reference Handoff**: `challenger_m1_2/handoff.md`  

---

## 1. Executive Summary & Root Cause Analysis

During Milestone 1 gate verification, `challenger_m1_2` challenged the workspace setup due to bit-for-bit checksum divergence between the source repository and the clean-room workspace:
- **Clean-room `rtl_frozen/directory/dir_ctrl.sv`**: MD5 `4b8cca8381166c83ee61440ee2e45220` (26,207 bytes)
- **Source repository `rtl/directory/dir_ctrl.sv`**: MD5 `acc52411a8b20d2c82771d4c8a28e187` (26,274 bytes)

### Root Cause
1. **RTL Mutation**: Two lines of code (`output logic [2:0] rxq_cnt_o,` and `assign rxq_cnt_o = rxq_cnt;`) were added to `rtl/directory/dir_ctrl.sv` in the source repository at 23:14:06 (to expose internal queue occupancy for SVA). This occurred after the clean room was initially populated with the unmutated baseline (`4b8cca8381166c83ee61440ee2e45220`).
2. **Circular Validation in `WAKE_UP.sh`**: Step 2 of `WAKE_UP.sh` copied `rtl/` into `rtl_frozen/` and dynamically generated `FROZEN.md5` directly from the copied files without checking against pre-established golden hashes. Step 4 ran `md5sum -c rtl_frozen/FROZEN.md5`, which checked self-consistency but could never catch modified RTL.
3. **Black Box Violation**: Modifying the DUT RTL violates the core clean-room isolation principle: *the frozen RTL is an immutable read-only black box*. Any internal observability required for verification (SVA / formal / testbenches) must be achieved through hierarchical binds or testbench taps, never by altering the synthesizable port list of the frozen DUT.

---

## 2. Checksum and State Analysis

### Current State Matrix

| File Path | Golden Expected MD5 | Clean-Room Current MD5 | Source Repo Current MD5 | Status |
|---|---|---|---|---|
| `pd/v1/verify_patch_set.py` | `4c4370f50882e82399b65076147bf112` | N/A (not in clean room) | `4c4370f50882e82399b65076147bf112` | **PASS** |
| `rtl/pkg/tile_pkg.sv` | `b6ece1864f1ce6ddf5b6976775d34485` | `b6ece1864f1ce6ddf5b6976775d34485` | `b6ece1864f1ce6ddf5b6976775d34485` | **PASS** |
| `rtl/l1/l1_mesi_ctrl.sv` | `d63be56146cfd7f2c9f3682caf918809` | `d63be56146cfd7f2c9f3682caf918809` | `d63be56146cfd7f2c9f3682caf918809` | **PASS** |
| `rtl/directory/dir_ctrl.sv` | `4b8cca8381166c83ee61440ee2e45220` | `4b8cca8381166c83ee61440ee2e45220` | `acc52411a8b20d2c82771d4c8a28e187` | **FAIL (DIVERGENCE)** |
| `rtl_frozen/FROZEN.md5` | Golden Manifest (3 files) | Matches baseline hashes | Matches mutated `acc52411...` | **FAIL (DIVERGENCE)** |

### Verified Bit-for-Bit Specifications in Clean Room
All 7 authorized specification files in `~/teamwork_projects/clean_room_verification` match the source repository bit-for-bit:
1. `white_papers/final/FINAL_whitepaper_v3.0.md` (`903802d4a96b8ec367f23476fa0fec3e`)
2. `white_papers/final/SLICE_16_1.md` (`d2fb55799608b92fbb0bc95b181c19f8`)
3. `white_papers/final/WORK_BREAKDOWN_16.md` (`f925a781ac171c0c8ef6c2ae24c43c25`)
4. `white_papers/final/RULINGS_B1_B2_B4.md` (`8dae3f6144d2434586e91a5aaa31a61b`)
5. `docs/01_DECISION_LOG.md` (`4a276b120a44f6ebca9fc466ff335cc3`)
6. `docs/04_TECH_STACK.md` (`ac770556e48c1d989c2c923b1a57d74e`)
7. `BUILD_ORDER.md` (`5f5cdbd74e8fe4428311cad58343d5a3`)

Zero legacy testbenches, hidden files, or symlinks exist in the clean room. The ONLY remediation required is bringing `dir_ctrl.sv` and `WAKE_UP.sh` back to golden alignment.

---

## 3. Detailed Technical Solutions for Worker Execution

### 3.1 Reversion of `rtl/directory/dir_ctrl.sv`
The baseline file has MD5 `4b8cca8381166c83ee61440ee2e45220`.  
Investigation confirmed that removing the two lines containing `rxq_cnt_o` restores the file to the exact byte-for-byte baseline:

```bash
# In /mnt/Code/visualstudio/Design-arch_multi-core:
sed -i '/rxq_cnt_o/d' rtl/directory/dir_ctrl.sv
```
*Alternative foolproof method*:
```bash
cp /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv rtl/directory/dir_ctrl.sv
```

Immediately verify:
```bash
md5sum rtl/directory/dir_ctrl.sv
# Expected output: 4b8cca8381166c83ee61440ee2e45220  rtl/directory/dir_ctrl.sv
```

---

### 3.2 Hardening `WAKE_UP.sh`
The reset script must be hardened so it enforces golden RTL immutability before copying and asserts golden integrity after snapshotting.

#### Proposed Hardened Implementation for `WAKE_UP.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

# WAKE_UP.sh — Hardened 4-Step Clean-Room Reset Script
# Automates environment verification, golden RTL validation, snapshotting, and test quarantine.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "========================================================"
echo "Starting Clean-Room Reset Protocol (WAKE_UP.sh)"
echo "Working directory: $REPO_ROOT"
echo "========================================================"

# Expected Golden Checksums
EXPECTED_VERIFIER_MD5="4c4370f50882e82399b65076147bf112"
EXPECTED_TILE_PKG_MD5="b6ece1864f1ce6ddf5b6976775d34485"
EXPECTED_L1_MESI_CTRL_MD5="d63be56146cfd7f2c9f3682caf918809"
EXPECTED_DIR_CTRL_MD5="4b8cca8381166c83ee61440ee2e45220"

verify_file_md5() {
    local file="$1"
    local expected="$2"
    if [ ! -f "$file" ]; then
        echo "ERROR: Required file '$file' not found!" >&2
        exit 1
    fi
    local actual
    actual=$(md5sum "$file" | awk '{print $1}')
    if [ "$actual" != "$expected" ]; then
        echo "ERROR: Golden checksum mismatch for $file!" >&2
        echo "  Expected: $expected" >&2
        echo "  Actual:   $actual" >&2
        echo "  Clean-room rule violation: RTL under test must remain an immutable read-only black box." >&2
        exit 1
    fi
    echo "  [PASS] $file ($actual)"
}

# Step 1: Verify pd/v1/verify_patch_set.py checksum
echo "[Step 1/4] Verifying pd/v1/verify_patch_set.py checksum..."
verify_file_md5 "pd/v1/verify_patch_set.py" "$EXPECTED_VERIFIER_MD5"
echo "Step 1 PASS: Verifier matches expected golden hash."

# Step 2: Validate Source RTL against Golden Baseline & Snapshot into rtl_frozen/
echo "[Step 2/4] Verifying source RTL integrity and snapshotting into rtl_frozen/..."
verify_file_md5 "rtl/pkg/tile_pkg.sv" "$EXPECTED_TILE_PKG_MD5"
verify_file_md5 "rtl/l1/l1_mesi_ctrl.sv" "$EXPECTED_L1_MESI_CTRL_MD5"
verify_file_md5 "rtl/directory/dir_ctrl.sv" "$EXPECTED_DIR_CTRL_MD5"

mkdir -p rtl_frozen/pkg rtl_frozen/l1 rtl_frozen/directory

# Copy hierarchical structure
cp -p rtl/pkg/tile_pkg.sv rtl_frozen/pkg/tile_pkg.sv
cp -p rtl/l1/l1_mesi_ctrl.sv rtl_frozen/l1/l1_mesi_ctrl.sv
cp -p rtl/directory/dir_ctrl.sv rtl_frozen/directory/dir_ctrl.sv

# Copy flat files to support flat directory layouts
cp -p rtl/pkg/tile_pkg.sv rtl_frozen/tile_pkg.sv
cp -p rtl/l1/l1_mesi_ctrl.sv rtl_frozen/l1_mesi_ctrl.sv
cp -p rtl/directory/dir_ctrl.sv rtl_frozen/dir_ctrl.sv

# Generate canonical rtl_frozen/FROZEN.md5
cat <<EOF > rtl_frozen/FROZEN.md5
${EXPECTED_TILE_PKG_MD5}  rtl_frozen/pkg/tile_pkg.sv
${EXPECTED_L1_MESI_CTRL_MD5}  rtl_frozen/l1/l1_mesi_ctrl.sv
${EXPECTED_DIR_CTRL_MD5}  rtl_frozen/directory/dir_ctrl.sv
EOF

echo "Generated canonical rtl_frozen/FROZEN.md5:"
cat rtl_frozen/FROZEN.md5
echo "Step 2 PASS: RTL verified against golden hashes and snapshot created."

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

# Step 4: Validate frozen RTL checksums
echo "[Step 4/4] Validating frozen RTL checksums..."
md5sum -c rtl_frozen/FROZEN.md5

# Also verify flat snapshot integrity
verify_file_md5 "rtl_frozen/tile_pkg.sv" "$EXPECTED_TILE_PKG_MD5"
verify_file_md5 "rtl_frozen/l1_mesi_ctrl.sv" "$EXPECTED_L1_MESI_CTRL_MD5"
verify_file_md5 "rtl_frozen/dir_ctrl.sv" "$EXPECTED_DIR_CTRL_MD5"
echo "Step 4 PASS: Checksum validation succeeded."

echo "========================================================"
echo "WAKE_UP: 4-step reset cleanly completed."
echo "========================================================"
```

---

## 4. End-to-End Worker Remediation Workflow

A fresh worker assigned to execute this fix should follow this exact sequence:

```
[Worker Workflow]
 ├── Step 1: Revert rtl/directory/dir_ctrl.sv to baseline 4b8cca8381166c83ee61440ee2e45220
 ├── Step 2: Replace WAKE_UP.sh with the hardened golden verification script
 ├── Step 3: Make executable and run ./WAKE_UP.sh in /mnt/Code/visualstudio/Design-arch_multi-core
 ├── Step 4: Verify md5sum -c rtl_frozen/FROZEN.md5 in both repos
 └── Step 5: Execute bit-for-bit parity check (cmp & diff) across both workspaces
```

### Exact Terminal Commands for Worker:

```bash
# === STEP 1: Revert rtl/directory/dir_ctrl.sv ===
cd /mnt/Code/visualstudio/Design-arch_multi-core
sed -i '/rxq_cnt_o/d' rtl/directory/dir_ctrl.sv
# Verify hash
ACTUAL_DIR_MD5=$(md5sum rtl/directory/dir_ctrl.sv | awk '{print $1}')
if [ "$ACTUAL_DIR_MD5" != "4b8cca8381166c83ee61440ee2e45220" ]; then
    echo "ERROR: Reversion failed, hash is $ACTUAL_DIR_MD5" && exit 1
fi

# === STEP 2: Harden WAKE_UP.sh ===
# Update WAKE_UP.sh with hardened script (Section 3.2)
chmod +x WAKE_UP.sh

# === STEP 3: Execute WAKE_UP.sh ===
./WAKE_UP.sh

# === STEP 4: Verify FROZEN.md5 in both workspaces ===
# In source repo:
cd /mnt/Code/visualstudio/Design-arch_multi-core
md5sum -c rtl_frozen/FROZEN.md5

# In clean-room workspace:
cd /home/durgesh/teamwork_projects/clean_room_verification
md5sum -c rtl_frozen/FROZEN.md5

# === STEP 5: Verify Cross-Repository Bit-for-Bit Parity ===
diff -u /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/FROZEN.md5 \
        /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/FROZEN.md5

cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/pkg/tile_pkg.sv \
    /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/pkg/tile_pkg.sv

cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/l1/l1_mesi_ctrl.sv \
    /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/l1/l1_mesi_ctrl.sv

cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/directory/dir_ctrl.sv \
    /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/directory/dir_ctrl.sv

cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/tile_pkg.sv \
    /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/tile_pkg.sv

cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/l1_mesi_ctrl.sv \
    /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/l1_mesi_ctrl.sv

cmp /mnt/Code/visualstudio/Design-arch_multi-core/rtl_frozen/dir_ctrl.sv \
    /home/durgesh/teamwork_projects/clean_room_verification/rtl_frozen/dir_ctrl.sv
```

---

## 5. Clean-Room Isolation & Safety Compliance

1. **Zero Testbench Inspection**: Neither this investigation nor the worker workflow touches or reads files in `tb_self_test/`, `tb/l1_dir/`, or scratch directories. Clean-room isolation remains 100% intact.
2. **Read-Only Black Box Principle**: Reverting `dir_ctrl.sv` removes unauthorized port modifications, ensuring that acceptance testing in M2-M5 operates against the pristine, unmutated design under test.
3. **Hardened Gate**: By hardcoding the golden baseline hashes into `WAKE_UP.sh`, future workers cannot accidentally mutate RTL or snapshot out-of-spec code.
