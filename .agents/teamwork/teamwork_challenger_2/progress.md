# Progress: Challenger 2 (Directed Races, Mutation Controls & SVA Stress Verification)

**Last visited**: 2026-11-09T14:20:00Z  
**Status**: COMPLETED  

## Tasks
- [x] 1. Reconnaissance & Testbench Inspection
  - [x] Inspect `tb_acceptance/l1_dir/` files (directed upgrade-race tests)
  - [x] Inspect `tb_acceptance/mutations/test_mutations.py` (mutants Mut-05..Mut-08)
  - [x] Inspect `tb_acceptance/sva/` (formal top, SVA assertions, SBY file, netlist)
- [x] 2. Challenge 1: Directed Upgrade-Race Stress
  - [x] Run `test_f_concurrent_upgrade_abort` empirically
  - [x] Verify Tile 1 immediate abort in `L1_SM_D` upon same-line INV (Tile remains in SM_D via same-state self-edge, does not abort to I)
  - [x] Verify INVACK transmitted immediately on VC2 (CONFIRMED at cycle 10)
  - [x] Verify non-blocking completion without deadlock/stall (FAILED on RTL: deadlocks in DIR_INV_WAIT)
  - [x] Verify strictly and exactly ONE holder in M (FAILED on RTL: m_count=0; ref model passes)
  - [x] Run `test_f_concurrent_upgrade_decline_reissue` empirically (DISCOVERED: runs only against Python ref model, bypasses RTL)
  - [x] Verify clean decline of stale grant and transition to M only upon re-issuing (Ref model verified; RTL has no decline path)
- [x] 3. Challenge 2: Mutation Negative Controls
  - [x] Execute all 4 negative controls in `tb_acceptance/mutations/test_mutations.py` (all 4 PASS)
  - [x] Verify non-vacuity of detection mechanisms (Mut-05 non-vacuous, Mut-06 non-vacuous in isolation)
  - [x] Challenge if any injected fault can sneak through undetected (Mut-07 and Mut-08 do not test RTL; test only Python model)
- [x] 4. Challenge 3: SVA Assertion Count & Vacuity
  - [x] Confirm netlist has 45 live assertion cells and 25 assumption cells (CONFIRMED in design_prep.il)
  - [x] Evaluate the protocol harness assumption `assume(UNBLOCK -> L1 in {S,E,M})` (Over-constrains internal DUT signals, hides premature UNBLOCK bugs, and prunes Ruling B7.2 decline path)
  - [x] Verify BMC K=64 progress (Bitwuzla at step 18; Boolector stalled at step 33)
- [x] 5. Synthesis & Handoff Report
  - [x] Compile comprehensive empirical findings into `handoff.md`
  - [x] Formulate verdict (REJECT)
  - [x] Message orchestrator with findings and verdict
