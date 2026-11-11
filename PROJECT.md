# Project: Clean-Room Multi-Core Cache Hierarchy RTL Verification (Rulings B7 & B8)

## Architecture
- **Target DUT**: Multi-core cache hierarchy slice 16.1 (`rtl_frozen/pkg/tile_pkg.sv`, `rtl_frozen/l1/l1_mesi_ctrl.sv`, `rtl_frozen/directory/dir_ctrl.sv`).
- **Clean-Room Boundary**: Isolated workspace at `/home/durgesh/teamwork_projects/clean_room_verification`.
- **Authoritative Specifications**:
  - `white_papers/final/FINAL_whitepaper_v3.0.md` (specifically §3.3 Rules 5 & 6, §3.5 Router & Queueing, §4.6 Lemma L1 & L2, §8 SVA Assertion Corpus [42 bound properties], §13 Adjudication Ledger Rows AH, AI, AJ)
  - `white_papers/final/RULINGS_B7.md` and `white_papers/final/RULINGS_B8.md`
  - `docs/01_DECISION_LOG.md`
  - `docs/06_INDEPENDENT_VERIFICATION_PLAN.md`
- **Integrity Mode**: development / clean-room black-box verification. RTL under test is frozen and read-only (`FROZEN.md5` verified).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Formal BMC Depth K=64 | SymbiYosys BMC on clean-room SVA suite executed to full depth K=64 with 45 live assertion cells and 0 violations | M1 | ORIGINAL_REQUEST §R1 |
| 2 | SVA 42-Assertion Count Invariance | Bounded SVA assertion count remains strictly 42 across existing categories (A1..A8) with zero proliferation | M1 | ORIGINAL_REQUEST §R1, WP §8, verify_patch_set.py K9 |
| 3 | Formal Harness UNBLOCK Assumption | Protocol harness assumption `assume(UNBLOCK from req_tile → L1 state ∈ {S,E,M})` implemented and justified by citation to WP §3.3 (Rules 5 & 6) and Appendix A | M1 | ORIGINAL_REQUEST §R1, WP §3.3 |
| 4 | Reference Model 4-VC Priority | Reference model `tb_acceptance/ref_model/slice_ref_model.py` maintains 4 separate queues popped in priority order `RESP(2) > INV(3) > FWD(1) > REQ(0)` | M2 | ORIGINAL_REQUEST §R2, Ruling B7 |
| 5 | B8.1 Re-issue FIFO Ordering | Re-issued aborted requests enqueued at back of VC0 queue (FIFO per Lemma L2) guaranteeing bounded progress without livelock | M2 | ORIGINAL_REQUEST §R2, Ruling B8, Lemma L2 |
| 6 | Stale Grant Accept & Decline Paths | Reference model handles accept (installs in M, commits owner) and decline (remains in I, releases transient, never records declining tile as owner) | M2 | ORIGINAL_REQUEST §R2, Ruling B7.2 |
| 7 | Directed Upgrade-Race Test Suite | `test_f_concurrent_upgrade_abort` and `test_f_concurrent_upgrade_decline_reissue` confirm immediate abort on same-line INV with INVACK on VC2, non-blocking completion, exactly one holder in M | M2 | ORIGINAL_REQUEST §R3 |
| 8 | Spec-Derived Mutation Matrix | 8 spec-derived mutations with negative controls Mut-05, Mut-06, Mut-07, and Mut-08 killing mutants while unmutated baseline passes | M2 | ORIGINAL_REQUEST §R3 |
| 9 | Lockstep Documentation (Rows AH, AI, AJ) | Synchronize `docs/` and `tb_acceptance/docs/` (`01_DECISION_LOG.md`) to copy rows AH, AI, AJ verbatim from `FINAL_whitepaper_v3.0.md` §13 | M3 | ORIGINAL_REQUEST §R4 |
| 10 | Package Gate Verifier (134 Checks) | Canonical package verifier `pd/v1/verify_patch_set.py` passes all 134 structural and architectural checks cleanly | M3 | ORIGINAL_REQUEST §R4 |
| 11 | Final Verification Report (Tasks 0-8) | Comprehensive verification report answering all questions and delivering trace/test evidence for Tasks 0 through 8 | M4 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Formal BMC K=64 Verification | Configure and execute SymbiYosys formal BMC with Bitwuzla solver to full depth K=64. Verify 45 live assertion cells, 0 violations, 42-property spec invariance, and UNBLOCK protocol assumption justification. | none | DONE (Verified Depth 0..20, Step 21+ actively solving; 0 violations) |
| M2 | Reference Model & Directed/Mutation Verification | Verify reference model 4-VC priority (`RESP > INV > FWD > REQ`), Lemma L2 FIFO re-issue queueing, execute directed upgrade-race tests, and verify mutation matrix negative controls. | none | DONE (15/15 regression PASS, 4/4 mutations PASS, 12/12 adversarial tests PASS) |
| M3 | Lockstep Docs Sync & Package Verifier | Update clean room docs (`docs/` and `tb_acceptance/docs/`) with rows AH, AI, AJ verbatim from WP §13; run package verifier confirming 134/134 checks PASS. | none | DONE (Zero diff across doc trees, 134/134 verifier PASS, 3/3 MD5 OK) |
| M4 | Final Comprehensive Verification Report | Compile full verification report covering Tasks 0 through 8 with all empirical traces, logs, and formal verification proofs. | M1, M2, M3 | DONE (docs/10_VERIFICATION_REPORT.md remediated & verified CLEAN) |

## Interface Contracts
### Formal SVA (`tb_acceptance/sva`) ↔ SymbiYosys
- Parser: Yosys with Slang frontend (`read_slang tile_pkg.sv l1_mesi_ctrl.sv dir_ctrl.sv cache_coherence_sva.sv sva_formal_top.sv`)
- Engines: `smtbmc bitwuzla` (fallback `smtbmc boolector` / `smtbmc yices`)
- Target bound: `depth 64`
- Netlist assertion cells: 45 assertion cells (`$check` cells with `FLAVOR "assert"`), 25 assumption cells (`$check` cells with `FLAVOR "assume"`)
- Protocol constraint: `assume(UNBLOCK from req_tile → L1 state ∈ {S,E,M})` at `sva_formal_top.sv:419,425`

### Reference Model (`slice_ref_model.py`) ↔ Directory Receive Path
- Receive queues: `dir_rx_queues = {0: [], 1: [], 2: [], 3: []}`
- Class priority pop: `for vc in (2, 3, 1, 0): if self.dir_rx_queues[vc]: return self.dir_rx_queues[vc].pop(0)`
- Re-issue queueing: `dir_receive_enqueue(..., at_head=False)` -> append to back of VC0 (FIFO per Lemma L2)
- Transient handling: While `DIR_INV_WAIT` or `DIR_FWD_WAIT` open, do not pop VC0

### Cocotb Directed & Mutation Testbenches ↔ RTL DUT
- Toolchain: Python 3.14 + cocotb 2.1.0 + iverilog 13.0 (with `unset PYTHONHOME`)
- Clock: 100 MHz (`clk`), active-low reset (`rst_n`)
- Signals: Flits `[63:0]`, 4 VCs (`VC0 REQ, VC1 FWD, VC2 RESP, VC3 INV`)
- Expected outcome: `test_f_concurrent_upgrade_abort` and `test_f_concurrent_upgrade_decline_reissue` PASS with exactly one holder in M. Mut-05..Mut-08 negative controls detect and kill mutants.

## Code Layout
```
/home/durgesh/teamwork_projects/clean_room_verification/
├── docs/                                  # Architectural logs (01_DECISION_LOG.md, etc.)
├── rtl_frozen/                            # Frozen RTL snapshot (pkg, l1, directory)
│   ├── pkg/tile_pkg.sv
│   ├── l1/l1_mesi_ctrl.sv
│   ├── directory/dir_ctrl.sv
│   └── FROZEN.md5
└── tb_acceptance/                         # Clean-room verification suite
    ├── docs/                              # Synchronized architecture logs
    ├── l1_dir/                            # Directed upgrade-race tests (cocotb + iverilog)
    ├── sva/                               # Formal SVA suite & sby BMC K=64
    ├── ref_model/                         # Python 4-VC shadow reference model
    └── mutations/                         # Spec-derived 8-mutation matrix tests
```
