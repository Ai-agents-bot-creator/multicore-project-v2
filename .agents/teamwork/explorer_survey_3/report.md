# Environment, Toolchain, and Workspace Survey Report

**Date**: 2026-11-05  
**Investigator**: explorer_survey_3 (`teamwork_explorer`)  
**Workspace**: `/mnt/Code/visualstudio/Design-arch_multi-core`  
**Target Isolated Workspace**: `~/teamwork_projects/clean_room_verification`  

---

## 1. Executive Summary

This survey establishes the technical baseline, toolchain verification, file integrity checks, and isolation automation plan for the clean-room verification of the multi-core cache hierarchy RTL.

- **Integrity**: `pd/v1/verify_patch_set.py` checksum matches `4c4370f50882e82399b65076147bf112` exactly, and executing it against the specification package yields `130/130 checks passed`.
- **RTL Baseline**: All three RTL under test files (`rtl/pkg/tile_pkg.sv`, `rtl/l1/l1_mesi_ctrl.sv`, `rtl/directory/dir_ctrl.sv`) exist with verified md5 checksums. `rtl_frozen/` does not yet exist and will be created.
- **Clean-Room Isolation**: `tb/l1_dir` exists and is confirmed present for quarantine to `tb_self_test/l1_dir`. Zero test code was viewed or inspected, preserving clean-room integrity.
- **Target Workspace**: `~/teamwork_projects/clean_room_verification` does not yet exist and will be initialized strictly with authorized specifications and frozen RTL.
- **Toolchain Discovery**:
  - `iverilog`: v13.0 (stable) available at `/usr/bin/iverilog`.
  - `cocotb`: v2.1.0 available at `/home/durgesh/.local/share/pipx/venvs/cocotb/bin/python`.
  - `sby` and `yosys`: Available at `/home/durgesh/.local/oss-cad-suite/bin` (`SBY v0.70-9-g79fc9ed`, `Yosys 0.70+336`).
  - SMT solvers: `z3` (v4.15.5), `boolector`, `bitwuzla`, `yices` all available in `oss-cad-suite`.
  - SystemVerilog in Yosys: Native `read_slang` in Yosys compiles `tile_pkg.sv`, `l1_mesi_ctrl.sv`, and `dir_ctrl.sv` with zero errors. BMC was verified end-to-end with `sby` using `read_slang` + `z3`.

---

## 2. Toolchain and Environment Investigation

### 2.1 Tool Matrix & Exact Paths

| Tool | Desired Version | Installed Version | Binary Path | Environment / Notes |
|---|---|---|---|---|
| **Icarus Verilog** (`iverilog`) | 13.0 | 13.0 (stable) | `/usr/bin/iverilog` | Preprocessor and VVP target v13.0. Note: oss-cad-suite has v14.0 devel, so `/usr/bin` should take precedence. |
| **Cocotb** | 2.1.0 | 2.1.0 | `/home/durgesh/.local/share/pipx/venvs/cocotb/bin/python`<br>`/home/durgesh/.local/bin/cocotb-config` | Installed via pipx Python 3.14 venv. Exact 2.1.0 release. Note: oss-cad-suite has 2.1.0.dev0. |
| **SymbiYosys** (`sby`) | Any / Latest | v0.70-9-g79fc9ed | `/home/durgesh/.local/oss-cad-suite/bin/sby` | Full BMC / temporal assertion formal verification harness. |
| **Yosys** | Any / Latest | 0.70+336 | `/home/durgesh/.local/oss-cad-suite/bin/yosys` | Includes `read_slang` SystemVerilog AST frontend and `synthprop`. |
| **SMT Solvers** | z3, etc. | z3 4.15.5, boolector, bitwuzla, yices | `/home/durgesh/.local/oss-cad-suite/bin/` | All available for `sby` engines. |

### 2.2 Recommended PATH Configuration for Implementers

To satisfy both the cocotb 2.1.0 + iverilog 13.0 requirement and the sby/yosys requirement without conflicts, use the following PATH ordering:

```bash
export PATH="/home/durgesh/.local/share/pipx/venvs/cocotb/bin:/usr/bin:/home/durgesh/.local/oss-cad-suite/bin:$PATH"
```

Verification of this combined PATH:
- `which iverilog` -> `/usr/bin/iverilog` (v13.0 stable)
- `python3 -c "import cocotb; print(cocotb.__version__)"` -> `2.1.0`
- `which sby` -> `/home/durgesh/.local/oss-cad-suite/bin/sby` (v0.70)
- `which yosys` -> `/home/durgesh/.local/oss-cad-suite/bin/yosys` (v0.70)
- `which z3` -> `/home/durgesh/.local/oss-cad-suite/bin/z3` (v4.15.5)

### 2.3 SystemVerilog Synthesis Note for SVA / Formal Verification

In Yosys, traditional `read_verilog -sv` encounters a syntax error on modern SystemVerilog constructs in `tile_pkg.sv` (line 192). However, the embedded `read_slang` frontend handles modern SV packages and assertions cleanly.

In `.sby` configuration files, the `[script]` section should specify:
```ini
[script]
read_slang pkg/tile_pkg.sv l1/l1_mesi_ctrl.sv <assertion_files>
prep -top <top_module>
```
Tested and verified: `sby` with `smtbmc z3` completes BMC verification cleanly (PASS, rc=0).

---

## 3. Repository Files and Checksum Verification

### 3.1 Verifier Script Integrity

- **Target**: `pd/v1/verify_patch_set.py`
- **Expected Checksum**: `4c4370f50882e82399b65076147bf112`
- **Observed Checksum**: `4c4370f50882e82399b65076147bf112`
- **Status**: **MATCH (100% Verified)**
- **Verification Run**: `python3 pd/v1/verify_patch_set.py --dir /mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/`
  - Output: `RESULT: PASS - 130/130 checks passed`

### 3.2 RTL Baseline Checksums

The RTL modules under test for Slice 16:

| File Path | MD5 Checksum | Size (bytes) | Status |
|---|---|---|---|
| `rtl/pkg/tile_pkg.sv` | `b6ece1864f1ce6ddf5b6976775d34485` | 13,382 | Verified |
| `rtl/l1/l1_mesi_ctrl.sv` | `d63be56146cfd7f2c9f3682caf918809` | 33,687 | Verified |
| `rtl/directory/dir_ctrl.sv` | `4b8cca8381166c83ee61440ee2e45220` | 37,294 | Verified |

- `rtl_frozen/`: Currently does not exist. Needs creation by `WAKE_UP.sh`.
- `rtl_frozen/FROZEN.md5`: Will be generated during snapshotting and validated via `md5sum -c`.

### 3.3 Clean-Room Isolation & Quarantine Status

- `tb/l1_dir`: **EXISTS**.
- Clean-room protocol: No files inside `tb/l1_dir` or any test directories were read or inspected. Only directory existence was confirmed via `ls -d`.
- `tb_self_test`: Does not exist yet. `WAKE_UP.sh` will move `tb/l1_dir` to `tb_self_test/l1_dir` and generate `tb_self_test/README.md`.

### 3.4 Authorized Specification Files Verification

All authorized specification files required by R1 exist with verified integrity:

| File | MD5 Checksum | Status |
|---|---|---|
| `white_papers/final/FINAL_whitepaper_v3.0.md` | `903802d4a96b8ec367f23476fa0fec3e` | Verified |
| `white_papers/final/SLICE_16_1.md` | `d2fb55799608b92fbb0bc95b181c19f8` | Verified |
| `white_papers/final/WORK_BREAKDOWN_16.md` | `f925a781ac171c0c8ef6c2ae24c43c25` | Verified |
| `white_papers/final/RULINGS_B1_B2_B4.md` | `8dae3f6144d2434586e91a5aaa31a61b` | Verified |
| `docs/01_DECISION_LOG.md` | `4a276b120a44f6ebca9fc466ff335cc3` | Verified |
| `docs/04_TECH_STACK.md` | `ac770556e48c1d989c2c923b1a57d74e` | Verified |
| `BUILD_ORDER.md` | `5f5cdbd74e8fe4428311cad58343d5a3` | Verified |

---

## 4. Target Workspace and Automation Specification

### 4.1 Target Workspace Status

- Directory: `/home/durgesh/teamwork_projects/clean_room_verification`
- Status: Does not exist yet. Needs creation and population.

### 4.2 Exact Steps for `WAKE_UP.sh`

The script `/mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh` will implement the 4-step reset:

1. **Step 1: Check Verifier Checksum**
   - Verify `md5sum pd/v1/verify_patch_set.py` against `4c4370f50882e82399b65076147bf112`.
   - Exit non-zero immediately if hash does not match.

2. **Step 2: Snapshot RTL under Test**
   - Create directories:
     ```bash
     mkdir -p rtl_frozen/pkg rtl_frozen/l1 rtl_frozen/directory
     ```
   - Copy RTL files:
     ```bash
     cp rtl/pkg/tile_pkg.sv rtl_frozen/pkg/tile_pkg.sv
     cp rtl/l1/l1_mesi_ctrl.sv rtl_frozen/l1/l1_mesi_ctrl.sv
     cp rtl/directory/dir_ctrl.sv rtl_frozen/directory/dir_ctrl.sv
     ```
   - Generate `rtl_frozen/FROZEN.md5`:
     ```bash
     md5sum rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv rtl_frozen/directory/dir_ctrl.sv > rtl_frozen/FROZEN.md5
     ```

3. **Step 3: Quarantine Existing Self-Tests**
   - Create quarantine root:
     ```bash
     mkdir -p tb_self_test
     ```
   - Move `tb/l1_dir` into `tb_self_test/l1_dir` (handle idempotently if already moved):
     ```bash
     if [ -d "tb/l1_dir" ]; then
         mv tb/l1_dir tb_self_test/l1_dir
     fi
     ```
   - Create `tb_self_test/README.md` documenting clean-room quarantine rules:
     "This directory contains quarantined self-tests. The clean-room verification protocol strictly forbids reading or inspecting test source code from this directory or any existing self-tests."

4. **Step 4: Validation Gate**
   - Validate checksum file:
     ```bash
     md5sum -c rtl_frozen/FROZEN.md5
     ```
   - Output confirmation status: `WAKE_UP: 4-step reset cleanly completed.`

### 4.3 Exact Steps for Workspace Copy to `~/teamwork_projects/clean_room_verification`

1. **Initialize Directory**:
   ```bash
   TARGET="$HOME/teamwork_projects/clean_room_verification"
   SRC="/mnt/Code/visualstudio/Design-arch_multi-core"
   mkdir -p "$TARGET"
   mkdir -p "$TARGET/white_papers/final"
   mkdir -p "$TARGET/docs"
   ```

2. **Copy Authorized Specifications Only**:
   ```bash
   cp "$SRC/white_papers/final/FINAL_whitepaper_v3.0.md" "$TARGET/white_papers/final/"
   cp "$SRC/white_papers/final/SLICE_16_1.md" "$TARGET/white_papers/final/"
   cp "$SRC/white_papers/final/WORK_BREAKDOWN_16.md" "$TARGET/white_papers/final/"
   cp "$SRC/white_papers/final/RULINGS_B1_B2_B4.md" "$TARGET/white_papers/final/"
   cp "$SRC/docs/01_DECISION_LOG.md" "$TARGET/docs/"
   cp "$SRC/docs/04_TECH_STACK.md" "$TARGET/docs/"
   cp "$SRC/BUILD_ORDER.md" "$TARGET/"
   ```

3. **Copy Frozen RTL Snapshot and Checksums**:
   ```bash
   cp -r "$SRC/rtl_frozen" "$TARGET/"
   ```

4. **Validate Frozen RTL Integrity in Target Workspace**:
   ```bash
   cd "$TARGET" && md5sum -c rtl_frozen/FROZEN.md5
   ```

5. **Clean-Room Boundary Check**:
   - Verify that NO files from `tb_self_test`, `tb/`, or scratch directories exist in `$TARGET`.
   - Confirm only authorized specification docs and frozen RTL reside in `$TARGET`.
