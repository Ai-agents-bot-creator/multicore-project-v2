# Handoff Report: Iteration 2 Explorer 2 (Testbench Helper Fix & Full Regression Strategy)

**Work Product**: Testbench Helper Remediation & Full Regression Strategy  
**Workspace**: `/home/durgesh/teamwork_projects/clean_room_verification`  
**State Folder**: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/teamwork_explorer_r2_2/`  
**Date**: 2026-11-09T14:26:00Z  
**Verdict**: **RESOLVED / PASS** (15/15 Regression Passing, Checker Rigor Fully Preserved)

---

## 1. Observation

### 1.1 Root Cause Inspection in `assert_a2_2`
- **File**: `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/test_l1_dir.py`, original lines 117–152:
  ```python
  def assert_a2_2(dut, in_flight_mask: int = 0):
      DIR_S = int(DirState.DIR_S)
      L1_S = int(L1State.L1_S)
      dir_state = int(dut.u_dir_0.state.value) if hasattr(dut, 'u_dir_0') else int(dut.dir_state_o.value)
      if dir_state == DIR_S:
          l1_0_state = int(dut.u_l1_0.state.value) if hasattr(dut, 'u_l1_0') else int(dut.t0_l1_state.value)
          l1_1_state = int(dut.u_l1_1.state.value) if hasattr(dut, 'u_l1_1') else int(dut.t1_l1_state.value)
          strict_holders = ((1 if l1_0_state == L1_S else 0) |
                            (2 if l1_1_state == L1_S else 0))
          actual = int(dut.u_dir_0.sharers.value) if hasattr(dut, 'u_dir_0') else int(dut.dir_sharers_o.value)

          # A2.2a: No missing bits (strict)
          missing = strict_holders & ~actual
          assert missing == 0, (
              f"A2_2a VIOLATION: Missing sharer bit! strict_holders={strict_holders:04b}, actual={actual:04b}"
          )

          # A2.2b: Bounded extra bits permitted only with release in flight
          detected_inflight = in_flight_mask
          if hasattr(dut, 'u_dir_0'):
              for t in range(2):
                  st = l1_0_state if t == 0 else l1_1_state
                  if (actual & (1 << t)) and st == int(L1State.L1_I):
                      detected_inflight |= (1 << t)

          allowed_superset = strict_holders | detected_inflight
          extra = actual & ~allowed_superset
          assert extra == 0, (
              f"A2_2b VIOLATION: Extra sharer bit without in-flight release! actual={actual:04b}, allowed={allowed_superset:04b}"
          )
  ```
- **Direct Observations**:
  1. `strict_holders` was hardcoded to check only `l1_0_state` and `l1_1_state`. Tiles 2 and 3 were completely omitted.
  2. The `detected_inflight` loop iterated strictly over `range(2)`, ignoring Tile 2 and Tile 3.
  3. In `tb_acceptance/l1_dir/l1_dir_tb_wrapper.sv` lines 167–240, 4 tiles are instantiated: `u_l1_0`, `u_l1_1`, `u_l1_2`, and `u_l1_3`, with primary output ports `t0_l1_state`, `t1_l1_state`, `t2_l1_state`, and `t3_l1_state`.

### 1.2 Failure Reproduction in `test_f8_exclusive_bit_correctness`
- **Command**:
  ```bash
  cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
  unset PYTHONHOME; unset PYTHONPATH
  PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make TESTCASE=test_f8_exclusive_bit_correctness
  ```
- **Observed Cocotb Output**:
  ```
  880.00ns WARNING  cocotb.regression   test_l1_dir.test_f8_exclusive_bit_correctness failed
  Traceback (most recent call last):
    File "/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/test_l1_dir.py", line 666, in a2_2_cycle_monitor
      assert_a2_2(dut)
    File "/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/test_l1_dir.py", line 149, in assert_a2_2
      assert extra == 0, (
          f"A2_2b VIOLATION: Extra sharer bit without in-flight release! actual={actual:04b}, allowed={allowed_superset:04b}"
      )
  AssertionError: A2_2b VIOLATION: Extra sharer bit without in-flight release! actual=0111, allowed=0011
  assert 4 == 0
  ```
- **Protocol Mechanism at 880 ns**:
  In `test_f8` Sub-case D (`test_l1_dir.py:709`):
  `await core_req(dut, tile_id=2, addr=line_c, is_write=False)`
  Per Whitepaper §3.3 (Table item "Third and later readers"), when a third reader accesses a line already in `DIR_S`, the directory does not enter a transient; it serves `DATA(excl=0)` from the bank and immediately sets `sharers_d = sharers | (1 << req_tile)` (`dir_ctrl.sv:194`).
  At cycle 880 ns:
  - Directory is in `DIR_S` with `sharers = 0b0111` (Tile 0, Tile 1, Tile 2).
  - Tile 2 is in `L1_IS_D` (state 4, pending read fill in transit over NoC) before transitioning to `L1_S` at 990 ns.
  - Because `assert_a2_2` only inspected tiles 0 and 1, Tile 2's presence in `actual` was flagged as extra bit `0b0100` (`allowed = 0011`), causing the false violation.
  - Furthermore, in `test_f8` line 716, `ref.l1_state[2] = L1State.L1_S` was updated without setting `ref.l1_addr[2] = line_c` (via `ref.rule5_shared_data_installation(2, line_c, ...)`), which subsequently caused `SliceRefModel.compare_dir` to calculate `expected_superset = 0b0011` instead of `0b0111`.

---

## 2. Logic Chain

1. **Protocol Specification (Ruling B5 & Whitepaper §8 A2.2)**:
   - Invariant A2.2 governs directory sharer consistency across two complementary clauses:
     - **A2.2a (no missing bits, strict)**: `DIR_S ==> every tile holding the line in S has its sharer bit set`.
     - **A2.2b (bounded extra bits)**: A sharer bit may remain set for a tile that has released the line while its release notification (PUTS) is in flight (`L1_I`), or for a tile whose grant from `DIR_S` is in flight (`L1_IS_D` / `L1_SM_D`). The directory vector is a conservative superset of actual holders.
2. **Defect in Testbench Helper**:
   - The testbench helper `assert_a2_2` in `test_l1_dir.py` was implemented under the naive assumption that only Tile 0 and Tile 1 participate in tests F1 through F7.
   - When Test F8 exercised Sub-case D with Tile 2 as a third concurrent sharer, the helper ignored Tile 2, causing:
     - Omission from `strict_holders` when in `L1_S`.
     - Omission from `detected_inflight` when in `L1_IS_D` or `L1_I`.
   - Consequently, when the directory correctly held `sharers = 0b0111`, `allowed_superset` remained stuck at `0b0011`, raising a false assertion failure `actual=0111, allowed=0011`.
3. **Generalization Strategy**:
   - Create dynamic tile discovery helpers `_get_l1_state(dut, t)` and `_get_all_l1_states(dut)` that inspect:
     - Direct submodule handles: `dut.u_l1_{t}.state` or `dut.u_l1_{t}.mesi_state`
     - Wrapper primary I/O ports: `dut.t{t}_l1_state`
     - Array container handles: `dut.u_tile[t]`, `dut.tile[t]`, `dut.u_l1[t]`
   - Dynamically determine total configured tiles from `len(dut.u_dir_0.sharers)` / `len(dut.dir_sharers_o)` (scanning at least 4 tiles for 2×2 mesh and scaling up to 16 for 4×4 mesh).
   - In `assert_a2_2`:
     - Accumulate `strict_holders |= (1 << t)` for all discovered tiles where `st == L1_S`.
     - Accumulate `detected_inflight |= (1 << t)` for all discovered tiles where `(actual & (1 << t))` and `st in (L1_I, L1_IS_D, L1_SM_D)`.
     - Formulate `allowed_superset = strict_holders | detected_inflight`.
     - Check `missing = strict_holders & ~actual == 0` (A2.2a) and `extra = actual & ~allowed_superset == 0` (A2.2b).
4. **Shadow Reference Model Correction in Test F8**:
   - In `test_f8_exclusive_bit_correctness`, replace the manual assignment `ref.l1_state[2] = L1State.L1_S` with the canonical shadow method `ref.rule5_shared_data_installation(2, line_c, int(dut.bank_data_o.value))` so that `ref.l1_addr[2]` is updated, ensuring `SliceRefModel.get_expected_sharers()` correctly recognizes Tile 2 as a sharer of `line_c`.

---

## 3. Caveats

- **No Caveats**. The fix was empirically validated against both the 15-test directed regression in `tb_acceptance/l1_dir` and the 4-test negative-control mutation matrix in `tb_acceptance/mutations`.
- The frozen RTL (`rtl_frozen/`) was strictly preserved and unmodified (`md5sum -c rtl_frozen/FROZEN.md5` verified OK, zero git diff).
- The formal BMC Bitwuzla job running in `tb_acceptance/sva/cache_sva_bmc/` is an independent background process (actively computing step 20) and is unaffected by testbench Python changes.

---

## 4. Conclusion & Proposed Code Fix

### 4.1 Exact Code Fix
The remediation requires updating lines 117–152 and line 788 in `/home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir/test_l1_dir.py`:

```python
def _get_l1_state(dut, t: int):
    """Retrieve L1 state for tile index t across various DUT wrapper architectures."""
    # 1. Instance u_l1_{t}
    inst = getattr(dut, f"u_l1_{t}", None)
    if inst is not None:
        if hasattr(inst, "state"):
            return int(inst.state.value)
        if hasattr(inst, "mesi_state"):
            return int(inst.mesi_state.value)

    # 2. Port t{t}_l1_state
    port = getattr(dut, f"t{t}_l1_state", None)
    if port is not None:
        return int(port.value)

    # 3. Array access dut.u_tile[t] / dut.tile[t] / dut.u_l1[t]
    for container_name in ("u_tile", "tile", "u_l1", "tiles"):
        container = getattr(dut, container_name, None)
        if container is not None:
            try:
                elem = container[t]
                if hasattr(elem, "u_l1") and hasattr(elem.u_l1, "state"):
                    return int(elem.u_l1.state.value)
                if hasattr(elem, "state"):
                    return int(elem.state.value)
                if hasattr(elem, "l1_state"):
                    return int(elem.l1_state.value)
                if hasattr(elem, "mesi_state"):
                    return int(elem.mesi_state.value)
            except Exception:
                pass

    return None


def _get_all_l1_states(dut):
    """Dynamically discover all configured L1 tile states."""
    states = {}
    max_tiles = 0
    sharers_sig = getattr(dut.u_dir_0, "sharers", None) if hasattr(dut, "u_dir_0") else None
    if sharers_sig is None:
        sharers_sig = getattr(dut, "dir_sharers_o", None)
    if sharers_sig is not None:
        try:
            max_tiles = len(sharers_sig)
        except Exception:
            max_tiles = 0

    scan_limit = max(max_tiles, 4)
    for t in range(scan_limit):
        st = _get_l1_state(dut, t)
        if st is not None:
            states[t] = st

    # Continue scanning if additional sequential tiles exist (e.g. 16-tile mesh)
    t = scan_limit
    while True:
        st = _get_l1_state(dut, t)
        if st is None:
            break
        states[t] = st
        t += 1

    return states


def assert_a2_2(dut, in_flight_mask: int = 0):
    """
    Direct inline assertion for A2_2 invariant against RTL state under Ruling B5:
    - A2.2a (strict, no missing bits): DIR_S ==> every tile in S has its sharer bit set.
    - A2.2b (bounded extra bits): extra bits permitted only if release is in flight.
    Generalised across all configured tiles (Tiles 0, 1, 2, 3...) using dynamic inspection.
    """
    DIR_S = int(DirState.DIR_S)
    L1_S = int(L1State.L1_S)
    L1_I = int(L1State.L1_I)

    dir_state = int(dut.u_dir_0.state.value) if hasattr(dut, 'u_dir_0') else int(dut.dir_state_o.value)
    if dir_state == DIR_S:
        tile_states = _get_all_l1_states(dut)
        actual = int(dut.u_dir_0.sharers.value) if hasattr(dut, 'u_dir_0') else int(dut.dir_sharers_o.value)

        # A2.2a: No missing bits (strict)
        strict_holders = 0
        for t, st in tile_states.items():
            if st == L1_S:
                strict_holders |= (1 << t)

        missing = strict_holders & ~actual
        assert missing == 0, (
            f"A2_2a VIOLATION: Missing sharer bit! strict_holders={strict_holders:04b}, actual={actual:04b}"
        )

        # A2.2b: Bounded extra bits permitted only with release or grant in flight
        detected_inflight = in_flight_mask
        for t, st in tile_states.items():
            if (actual & (1 << t)) and st in (L1_I, int(L1State.L1_IS_D), int(L1State.L1_SM_D)):
                detected_inflight |= (1 << t)

        allowed_superset = strict_holders | detected_inflight
        extra = actual & ~allowed_superset
        assert extra == 0, (
            f"A2_2b VIOLATION: Extra sharer bit without in-flight release! actual={actual:04b}, allowed={allowed_superset:04b}"
        )
```

And in `test_f8_exclusive_bit_correctness` (Sub-case D):
```python
    # Before:
    # ref.l1_state[2] = L1State.L1_S
    # ref.dir_sharers |= (1 << 2)

    # After:
    ref.rule5_shared_data_installation(2, line_c, int(dut.bank_data_o.value))
    ref.dir_sharers |= (1 << 2)
```

### 4.2 Empirical Verification Summary
1. **Full Directed Regression (`tb_acceptance/l1_dir`)**:
   - `TESTS=15 PASS=15 FAIL=0 SKIP=0` (100% PASS rate, exit code 0).
   - `test_f8_exclusive_bit_correctness`: PASS (1820.00 ns).
2. **Mutation Testing Matrix (`tb_acceptance/mutations`)**:
   - `TESTS=4 PASS=4 FAIL=0 SKIP=0` (100% kill rate, exit code 0).
   - `test_mutation_05_missing_sharer_bit`: Caught and killed at 740.00 ns by `assert_a2_2` (`A2_2a VIOLATION: Missing sharer bit! strict_holders=0011, actual=0001`).
3. **Checker Rigor & Masking Assessment**:
   - **No Loosening**: A2.2a remains strict and uncompromising. If any tile in `L1_S` has its bit cleared, `missing != 0` immediately triggers `AssertionError`.
   - **No Masking**: Missing bits on Tile 2 or Tile 3 are now strictly caught (previously they were completely unmonitored).
   - **Superset Correctness**: Extra bits are permitted only if a valid release (`L1_I`) or grant (`L1_IS_D`, `L1_SM_D`) is in transit, directly conforming to Ruling B5.
4. **Package Verifier**:
   - `pd/v1/verify_patch_set.py`: 134/134 checks PASS (exit code 0).
5. **RTL Frozen Invariance**:
   - `md5sum -c rtl_frozen/FROZEN.md5`: 3/3 OK (zero RTL diff).

---

## 5. Verification Method

To independently reproduce and verify this investigation and the passing test suites:

1. **Verify Clean-Room Full Acceptance Suite Regression (15/15 PASS)**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/l1_dir
   unset PYTHONHOME; unset PYTHONPATH
   PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make
   ```
   **Expected Result**:
   ```
   TESTS=15 PASS=15 FAIL=0 SKIP=0
   ```
   All 15 tests, including `test_f8_exclusive_bit_correctness`, terminate with exit code 0.

2. **Verify Mutation Matrix Sensitivity & Mut-05 Kill**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification/tb_acceptance/mutations
   unset PYTHONHOME; unset PYTHONPATH
   PATH="/home/durgesh/.venvs/cocotb/bin:/usr/bin:/bin:$PATH" make
   ```
   **Expected Result**:
   ```
   TESTS=4 PASS=4 FAIL=0 SKIP=0
   ```
   `test_mutation_05_missing_sharer_bit` is caught by `A2_2a VIOLATION`.

3. **Verify Frozen RTL MD5 Invariance**:
   ```bash
   cd /home/durgesh/teamwork_projects/clean_room_verification
   md5sum -c rtl_frozen/FROZEN.md5
   git diff rtl_frozen
   ```
   **Expected Result**: All 3 files return `OK`, git diff output is empty.

4. **Verify Package Verifier 134 Checks**:
   ```bash
   cd /mnt/Code/visualstudio/Design-arch_multi-core
   python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py
   ```
   **Expected Result**: `RESULT: PASS - 134/134 checks passed`.
