# Lint Sweep — Frozen RTL (Slice 16.1)

> **Document Purpose**: Factual record of lint tool runs against `rtl_frozen/`. No PASS/FAIL verdict — facts only.  
> **Writing Standard**: ~80% ASD-STE100 — direct active verbs, exact tool output quoted.

## Tool Discovery

```
$ command -v verible-verilog-lint slang verilator iverilog
/usr/bin/iverilog
/usr/bin/verilator
(no verible-verilog-lint in PATH)
(no slang linter in PATH; slang frontend available via Yosys for formal only)
```

| Tool | Version |
|---|---|
| Icarus Verilog | 13.0 (stable) |
| Verilator | 5.054 2026-11-01 rev v5.054 |

---

## Icarus Verilog 13.0 — L1 MESI Controller

**Command**:
```
cd /mnt/Code/visualstudio/Design-arch_multi-core && iverilog -g2012 -Wall -Irtl_frozen/pkg -o /tmp/opencode/lint_frozen_l1.vvp rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv
```

**Exit code**: 0

**Output**:
```
rtl_frozen/l1/l1_mesi_ctrl.sv:512: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'noc_rsp_flit[63:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:513: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'noc_rsp_flit[63:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:130: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'a[31:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:532: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:533: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:534: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:535: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:536: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:537: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:538: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/l1/l1_mesi_ctrl.sv:539: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
```

**Classification**: **Icarus limitation** (11 occurrences). Icarus 13 does not fully support constant part-selects in `always_comb`/`always_ff` sensitivity lists. The RTL uses `noc_rsp_flit[HDR_MSG_HI:HDR_MSG_LO]` etc. for header field extraction — correct SystemVerilog, but Icarus conservatively widens sensitivity to the full vector. No functional impact; Verilator and formal tools handle these correctly.

---

## Icarus Verilog 13.0 — Directory Controller

**Command**:
```
cd /mnt/Code/visualstudio/Design-arch_multi-core && iverilog -g2012 -Wall -Irtl_frozen/pkg -o /tmp/opencode/lint_frozen_dir.vvp rtl_frozen/pkg/tile_pkg.sv rtl_frozen/directory/dir_ctrl.sv
```

**Exit code**: 0

**Output**:
```
rtl_frozen/directory/dir_ctrl.sv:613: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'noc_req_flit[63:0]').
rtl_frozen/directory/dir_ctrl.sv:614: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'noc_req_flit[63:0]').
rtl_frozen/directory/dir_ctrl.sv:630: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/directory/dir_ctrl.sv:631: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/directory/dir_ctrl.sv:632: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/directory/dir_ctrl.sv:633: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/directory/dir_ctrl.sv:634: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/directory/dir_ctrl.sv:635: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/directory/dir_ctrl.sv:636: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
rtl_frozen/directory/dir_ctrl.sv:637: sorry: constant selects in always_* processes are not fully supported (the process will be sensitive to all bits in 'tx_cur_data[511:0]').
```

**Classification**: **Icarus limitation** (10 occurrences). Same root cause as L1 — constant part-selects in sensitivity lists.

---

## Verilator 5.054 — L1 MESI Controller

**Command**:
```
cd /mnt/Code/visualstudio/Design-arch_multi-core && verilator --lint-only -Wall -Wno-fatal -Irtl_frozen/pkg --top-module l1_mesi_ctrl rtl_frozen/pkg/tile_pkg.sv rtl_frozen/l1/l1_mesi_ctrl.sv
```

**Exit code**: 0

**Warning count**: 24 (1 UNUSEDSIGNAL, 2 UNUSEDSIGNAL, 21 UNUSEDPARAM)

**Key warnings**:

| Category | Count | Sample |
|---|---|---|
| UNUSEDSIGNAL | 3 | `rx_data[511:448]`, `rx_we`, `conflict` |
| UNUSEDPARAM | 21 | `SHARER_W`, `L1_SETS`, `L1_WAYS`, `L2_SET_W`, `L2_LINES`, `L1_SET_LO`, `L2_SET_LO`, `L2_SET_HI`, `L1_TAG_W`, `L2_LINE_W`, `PLRU_BITS`, `DIR_USED_W`, `DIR_ENTRY_W`, `NUM_VCS`, `VC_DEPTH`, `CREDIT_W`, `BODY_FLITS`, `LINE_PKT_LEN`, `NUM_PORTS`, `BANK_ARB_TAP_FIRST`, `AGE_THRESH`, `AGE_W` |

**Classification**:
- `UNUSEDSIGNAL` (3): **Real issue** — signals declared but not read. `rx_data[511:448]` upper bits never used (flit reassembly only uses lower 448 bits for 8-body-flit packets). `rx_we` and `conflict` declared in comb but not consumed. Should be removed or used.
- `UNUSEDPARAM` (21): **Style / scope artifact** — parameters defined in `tile_pkg.sv` for the full 4×4 system (sets, ways, PLRU, router VCs, bank arbiter, age counter). The one-line slice does not use them. Correct to keep in package for future modules; could be `localparam` in the module instead.

---

## Verilator 5.054 — Directory Controller

**Command**:
```
cd /mnt/Code/visualstudio/Design-arch_multi-core && verilator --lint-only -Wall -Wno-fatal -Irtl_frozen/pkg --top-module dir_ctrl rtl_frozen/pkg/tile_pkg.sv rtl_frozen/directory/dir_ctrl.sv
```

**Exit code**: 0

**Warning count**: 22 (1 UNUSEDSIGNAL, 21 UNUSEDPARAM)

**Key warnings**:

| Category | Count | Sample |
|---|---|---|
| UNUSEDSIGNAL | 1 | `rx_data[511:448]` |
| UNUSEDPARAM | 21 | Same package parameters as L1 (21 total) |

**Classification**:
- `UNUSEDSIGNAL` (1): **Real issue** — `rx_data[511:448]` upper bits unused (same reason as L1).
- `UNUSEDPARAM` (21): **Style / scope artifact** — same as L1.

---

## Summary Table

| Tool | Module | Exit | Warnings | Real issues | Icarus limitation | Style/scope |
|---|---|---|---|---|---|---|
| Icarus 13 | l1_mesi_ctrl | 0 | 11 | 0 | 11 | 0 |
| Icarus 13 | dir_ctrl | 0 | 10 | 0 | 10 | 0 |
| Verilator 5.054 | l1_mesi_ctrl | 0 | 24 | 3 | 0 | 21 |
| Verilator 5.054 | dir_ctrl | 0 | 22 | 1 | 0 | 21 |
| **Total** | | | **67** | **4** | **21** | **42** |

---

## Real Issues Requiring Attention (if scope expands)

1. **`rx_data[511:448]` unused** (L1 + Dir): The 9-flit packet uses 1 header + 8 body flits = 1×64 + 8×64 = 576 bits, but the body flits carry 8×56 = 448 data bits (64-bit flit with 8 header bits). Upper 64 bits of `rx_data` never filled. Consider shrinking to `[447:0]` or documenting the 576-bit reassembly model.

2. **`rx_we` unused** (L1): Declared in RX reassembly (line 96) but never read. The header `WE` bit (`HDR_WE`) is extracted to `rx_hdr_we` and used in `send()` calls; `rx_we` appears redundant.

3. **`conflict` unused** (L1): Declared in comb decision tree (line 165) but the `hit`/`conflict` computation is not used in the final `send()` logic — the B2 conflict path uses explicit `else` branches instead. Could be removed or the `hit` check unified.

---

## Notes

- All tools exit 0 (success). No errors.
- No additional linters available (verible, slang standalone).
- The 42 UNUSEDPARAM warnings are a consequence of the package being written for the full system while the slice exercises only a subset. They do not indicate RTL defects.
- The 21 Icarus "sorry" messages are a known Icarus 13 limitation with constant part-selects in sensitivity lists; Verilator and Yosys/Slang handle them correctly.

---

## Log Files

Full outputs saved under `tb_rtl_evidence/lint/`:
- `iverilog_l1.log`
- `iverilog_dir.log`
- `verilator_l1.log`
- `verilator_dir.log`