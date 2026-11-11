# Handoff Report: Empirical Challenge for M1 Hardened WAKE_UP.sh

- Agent: `challenger_m1_fix_1`
- Role: `critic, specialist (teamwork_challenger)`
- Target: `WAKE_UP.sh`
- Working Directory: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/challenger_m1_fix_1`
- Parent: `b25d00b4-87e5-4b35-8417-bffe75bad4d9`
- Verdict: **APPROVED** (Passed all empirical stress tests)

---

## 1. Observation

### Observation 1: Normal Execution of `WAKE_UP.sh`
Ran `./WAKE_UP.sh` in the repository root.
- **Exit code**: `0`
- **Output**:
```text
========================================================
Starting Clean-Room Reset Protocol (WAKE_UP.sh)
Working directory: /mnt/Code/visualstudio/Design-arch_multi-core
========================================================
[Step 1/4] Verifying pd/v1/verify_patch_set.py checksum...
Step 1 PASS: pd/v1/verify_patch_set.py matches 4c4370f50882e82399b65076147bf112
[Step 2/4] Validating source RTL against golden baseline hashes...
  Validated rtl/pkg/tile_pkg.sv matches golden baseline (b6ece1864f1ce6ddf5b6976775d34485)
  Validated rtl/l1/l1_mesi_ctrl.sv matches golden baseline (d63be56146cfd7f2c9f3682caf918809)
  Validated rtl/directory/dir_ctrl.sv matches golden baseline (4b8cca8381166c83ee61440ee2e45220)
Snapshotting RTL under test into rtl_frozen/...
Generated rtl_frozen/FROZEN.md5:
b6ece1864f1ce6ddf5b6976775d34485  rtl_frozen/pkg/tile_pkg.sv
d63be56146cfd7f2c9f3682caf918809  rtl_frozen/l1/l1_mesi_ctrl.sv
4b8cca8381166c83ee61440ee2e45220  rtl_frozen/directory/dir_ctrl.sv
Step 2 PASS: RTL snapshot created and verified against golden baseline.
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

### Observation 2: Idempotency (3 Consecutive Runs)
Ran `./WAKE_UP.sh && echo "RUN 1 PASS" && ./WAKE_UP.sh && echo "RUN 2 PASS" && ./WAKE_UP.sh && echo "RUN 3 PASS"`.
- **Exit code**: `0`
- All 3 consecutive runs completed with all 4 steps reporting `PASS` without errors or degradation.
- Quarantining step reported `tb_self_test/l1_dir already quarantined.` gracefully on subsequent runs.

### Observation 3: Negative Tamper Testing (Sandboxed)
Constructed an isolated sandbox test suite simulating tampering across all critical files:
1. **Mutate `rtl/pkg/tile_pkg.sv`**:
   - Exit code: `1`
   - Output: `ERROR: Checksum mismatch for source RTL 'rtl/pkg/tile_pkg.sv'!` followed by `ERROR: Source RTL validation failed against golden baseline (1 error(s)). RTL under test must NEVER be modified. Snapshot aborted!`
2. **Mutate `rtl/l1/l1_mesi_ctrl.sv`**:
   - Exit code: `1`
   - Output: `ERROR: Checksum mismatch for source RTL 'rtl/l1/l1_mesi_ctrl.sv'!` followed by snapshot abort.
3. **Mutate `rtl/directory/dir_ctrl.sv`**:
   - Exit code: `1`
   - Output: `ERROR: Checksum mismatch for source RTL 'rtl/directory/dir_ctrl.sv'!` followed by snapshot abort.
4. **Delete `rtl/pkg/tile_pkg.sv`**:
   - Exit code: `1`
   - Output: `ERROR: Source RTL file 'rtl/pkg/tile_pkg.sv' not found!` followed by snapshot abort.
5. **Delete `rtl/l1/l1_mesi_ctrl.sv`**:
   - Exit code: `1`
   - Output: `ERROR: Source RTL file 'rtl/l1/l1_mesi_ctrl.sv' not found!` followed by snapshot abort.
6. **Delete `rtl/directory/dir_ctrl.sv`**:
   - Exit code: `1`
   - Output: `ERROR: Source RTL file 'rtl/directory/dir_ctrl.sv' not found!` followed by snapshot abort.
7. **Mutate `pd/v1/verify_patch_set.py`**:
   - Exit code: `1`
   - Output: `ERROR: Checksum mismatch for pd/v1/verify_patch_set.py! Expected: 4c4370f50882e82399b65076147bf112`
8. **Delete `pd/v1/verify_patch_set.py`**:
   - Exit code: `1`
   - Output: `ERROR: Verifier script 'pd/v1/verify_patch_set.py' not found!`
9. **Snapshot Integrity on Tamper**:
   - Pre-existing `rtl_frozen/FROZEN.md5` and snapshot directories were confirmed uncorrupted and untouched when source RTL validation failed.
10. **Multiple Simultaneous Tampering**:
    - Tested mutating all 3 RTL files simultaneously: script properly accumulated and reported all 3 checksum mismatches (`(3 error(s))`) before aborting with exit code 1.
11. **Frozen RTL Tamper in Step 4**:
    - Verified `md5sum -c rtl_frozen/FROZEN.md5` triggers bash `set -e` failure and exits 1 if frozen files are modified.
12. **Out-of-Directory Invocation**:
    - Ran `(cd /tmp && /mnt/Code/visualstudio/Design-arch_multi-core/WAKE_UP.sh)`: successfully resolved `REPO_ROOT` and executed with exit code 0.

### Observation 4: Baseline RTL Hash Preservation
Verified actual repository source RTL hashes remain unmodified:
- `rtl/pkg/tile_pkg.sv`: `b6ece1864f1ce6ddf5b6976775d34485` (OK)
- `rtl/l1/l1_mesi_ctrl.sv`: `d63be56146cfd7f2c9f3682caf918809` (OK)
- `rtl/directory/dir_ctrl.sv`: `4b8cca8381166c83ee61440ee2e45220` (OK)
- `pd/v1/verify_patch_set.py`: `4c4370f50882e82399b65076147bf112` (OK)

---

## 2. Logic Chain

1. **Clean-Room Enforcement**:
   - Step 1 checks `pd/v1/verify_patch_set.py` against its authoritative md5 hash before any operations take place.
   - Step 2 matches every source RTL file against authoritative golden baseline hashes before touching `rtl_frozen/`. If any file differs or is missing, `WAKE_UP.sh` terminates immediately with non-zero exit code, guaranteeing that tampered RTL can never be snapshotted into `rtl_frozen/`.
2. **Idempotency**:
   - In Step 3, if `tb/l1_dir` has already been quarantined to `tb_self_test/l1_dir`, `WAKE_UP.sh` detects `[ -d "tb_self_test/l1_dir" ]` and skips the move without error.
   - In Step 2 and Step 4, snapshots and hash lists are overwritten cleanly and verified.
   - 3 consecutive runs completed with exit code 0, confirming idempotency.
3. **Negative Tamper Resilience**:
   - Empirical test suite verified 100% detection rate (10/10 tests) for modified RTL, deleted RTL, corrupted verifier script, and corrupted frozen files.
   - In all failure scenarios, the script exits immediately with exit code 1 and descriptive diagnostics.

---

## 3. Caveats

- **Self-Test Directory Re-creation Edge Case**:
  If an external actor manually creates a new `tb/l1_dir` while `tb_self_test/l1_dir` already exists, bash `mv tb/l1_dir tb_self_test/l1_dir` moves `tb/l1_dir` inside `tb_self_test/l1_dir/l1_dir`. This does not occur during normal idempotent runs because once moved, `tb/l1_dir` does not exist.
- **Clean-Room Strictness**:
  Per instructions, no files under `tb/self_test/` or `tb/l1_dir/` were read or inspected during this verification.

---

## 4. Conclusion

`WAKE_UP.sh` is **robust, idempotent, and tamper-resistant**. It strictly enforces the clean-room integrity contract:
- Successfully executes all 4 steps and exits `0`.
- Demonstrates clean idempotency across repeated runs.
- Reliably detects any unauthorized tampering or deletion in source RTL and verifier tools, aborting before snapshot generation.
- **VERDICT: PASS / APPROVED for Milestone M1 Remediation Gate.**

---

## 5. Verification Method

To independently verify these findings, run:

1. **Normal run & Idempotency**:
   ```bash
   ./WAKE_UP.sh
   ./WAKE_UP.sh
   ./WAKE_UP.sh
   ```
   *Expected: Exit code 0 on all runs with Step 1-4 PASS.*

2. **Negative tamper check in sandbox**:
   ```bash
   TMPDIR=$(mktemp -d /tmp/chk.XXXXXX)
   mkdir -p "$TMPDIR"/pd/v1 "$TMPDIR"/rtl/pkg "$TMPDIR"/rtl/l1 "$TMPDIR"/rtl/directory "$TMPDIR"/tb_self_test/l1_dir
   cp WAKE_UP.sh "$TMPDIR"/
   chmod +x "$TMPDIR"/WAKE_UP.sh
   cp pd/v1/verify_patch_set.py "$TMPDIR"/pd/v1/
   cp rtl/pkg/tile_pkg.sv "$TMPDIR"/rtl/pkg/
   cp rtl/l1/l1_mesi_ctrl.sv "$TMPDIR"/rtl/l1/
   cp rtl/directory/dir_ctrl.sv "$TMPDIR"/rtl/directory/
   echo "// tamper" >> "$TMPDIR"/rtl/l1/l1_mesi_ctrl.sv
   "$TMPDIR"/WAKE_UP.sh
   echo "Exit code: $?"
   rm -rf "$TMPDIR"
   ```
   *Expected: Step 2 error output, exit code 1.*
