# Quarantined Self-Tests

This directory contains quarantined legacy self-tests moved from `tb/l1_dir`.

## Clean-Room Isolation Protocol
Under clean-room verification rules:
- Engineers and verification agents MUST NOT read, inspect, or copy test source code from this directory (`tb_self_test/`) or any prior test suites.
- Acceptance tests must be independently developed from authoritative specification documents alone.
- RTL under test in `rtl_frozen/` is treated strictly as a read-only black box.
