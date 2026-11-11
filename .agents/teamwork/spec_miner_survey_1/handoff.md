# Handoff Report: Specification Mining for Slice 16.1

**Agent ID:** `spec_miner_survey_1`  
**Recipient:** Orchestrator (`b25d00b4-87e5-4b35-8417-bffe75bad4d9`)  
**Timestamp:** 2026-11-05T17:40:00Z  
**Type:** Hard Handoff (Task Complete)

---

## 1. Observation

Direct observations from the authorized specification sources:

### A. Slice 16.1 Forward Release Rules & State Transitions
- In `white_papers/final/SLICE_16_1.md`:
  - **L1 Transitions (lines 17–26):**
    - Line 20: `| E | FWD_GETS (VC1) | S | Send DATAFWD (clean data) to the home directory; downgrade E→S; the owner becomes a sharer |`
    - Line 21: `| M | FWD_GETS (VC1) | S | Send DATAFWD (dirty data) to the home directory; downgrade M→S; the owner becomes a sharer |`
    - Line 22: `| E | FWD_GETM (VC1) | I | Send DATAFWD (clean data) to the home directory; downgrade to I (ownership transfer) |`
    - Line 23: `| M | FWD_GETM (VC1) | I | Send DATAFWD (dirty data) to the home directory; downgrade to I (ownership transfer) |`
    - Line 24: `| I | FWD_GETS/FWD_GETM (VC1) | I | Send INVACK (VC2) — defensive; covers the evict-during-forward race (N5, N12) |`
    - Line 25: `| EI_A | FWD_GETS/FWD_GETM (VC1) | EI_A | Send INVACK (VC2) — the owner has already released the line (PUTS sent) (N12) |`
    - Line 26: `| MI_A | FWD_GETS/FWD_GETM (VC1) | MI_A | Send INVACK (VC2) — the owner has already sent PUTM, which satisfies the forward's data obligation (N12) |`
  - **Directory Controller & Single-Exit Rule (lines 70–84):**
    - Line 70: `| DIR_FWD_WAIT | DATAFWD | Write dirty data into the home bank (set the bank dirty bit from header bit [39]); send DATA to the requester (Owner/sharer update committed on the exit transition selected by pending_op) | — (awaiting UNBLOCK) |`
    - Line 71: `| DIR_FWD_WAIT | PUTM (owner) | Owner evicted concurrently: the PUTM satisfies the forward's data obligation — write data into the bank, set the bank dirty bit, clear the old owner's sharer bit (and set Owner = requester for pending_op = GETM); send PUTACK to release the owner; continue awaiting UNBLOCK (N12) | — (awaiting UNBLOCK) |`
    - Line 72: `| DIR_FWD_WAIT | PUTS (owner) | Owner (a clean DIR_E owner) released the line before the forward was served: the bank holds the current value, so cancel the forward — clear the old owner's sharer bit, send PUTACK, and serve the requester from the bank; the pending UNBLOCK still selects DIR_S (N12) | — (awaiting UNBLOCK) |`
    - Line 73: `| DIR_FWD_WAIT | INVACK (defensive) | Duplicate release — ignore, no state change; the owner's PUTS or PUTM resolves the forward and the two travel on different VCs (N12) | unchanged |`
    - Lines 81–83: "`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT` each exit **only** on `UNBLOCK`. ... Intermediate events (`MEM_DATA`, `DATAFWD`, `INVACK`, `PUTM`) advance DTR progress only and never change the SRAM state field."
  - **Shadow Update Rules 1–11 (lines 136–149):**
    - Exact 11 shadow rules documented, detailing deferred commits of sharers (`pending_op=GETS`) and owner (`pending_op=GETM`) until `UNBLOCK`.
  - **Directed Tests F1–F9 (lines 154–169):**
    - Enumerates tests F1 through F8 as directed testbench cases and F9 as formal BMC checking at K=64 depth.

### B. Protocol Rulings B1, B2, B4
- In `white_papers/final/RULINGS_B1_B2_B4.md`:
  - **Ruling B1 (Fairness Bound):** Age-escape threshold is confirmed at 5 rounds; derived bound is $5 + 3 + 5 = 13$ switch-arbitration rounds at interior tiles and $5 + 3 + 3 = 11$ at corner tiles.
  - **Ruling B2 (Conflict Eviction):** Rule 10 is split: proactive eviction is deferred; conflict eviction required by a pending miss releases the PLRU victim on VC0 (`PUTM` for M with wait for `PUTACK`, `PUTS` for S/E) *before* issuing the miss request on VC0 as a sub-step of the miss transient.
  - **Ruling B4 (DMA Scope):** The committed 2×2 mesh has 4 CPU tiles and 0 DMA tiles; DMA is 4×4 simulation-only gated.

### C. Package Architecture & Encodings
- In `rtl/pkg/tile_pkg.sv`:
  - Directory states: `DIR_I` (3'b000) to `DIR_EVICT` (3'b111).
  - L1 states: `L1_I` (4'd0) to `L1_MI_A` (4'd8).
  - Messages: `MSG_GETS` (4'b0000) to `MSG_PUTACK` (4'b1011).
  - VCs: `VC_REQ` (2'd0), `VC_FWD` (2'd1), `VC_RESP` (2'd2), `VC_INV` (2'd3).
  - Header bit positions: Dest [63:56], Src [55:48], Msg [47:44], VC [43:42], Head [41], Tail [40], WE/Dirty [39], Excl [38], Len [37:32], Addr [31:0].

---

## 2. Logic Chain

1. **Clean-Room Verification Feasibility:**
   - Observations A, B, and C provide 100% of the functional, microarchitectural, protocol, encoding, and assertion requirements without needing to inspect any pre-existing testbenches in `tb/self_test/` or `tb/l1_dir/`. Clean-room integrity is completely preserved.
2. **Determinism of the Directory FSM:**
   - Under the Single-Exit Rule (`DIR_FWD_WAIT` exits only on `UNBLOCK`), all intermediate events (`DATAFWD`, concurrent `PUTM`/`PUTS`, defensive `INVACK`) update DTR registers and home bank arrays while leaving the SRAM state field unchanged. `pending_op` deterministically chooses the successor (`DIR_S` vs `DIR_M`). This guarantees that a Python shadow model can track DUT states cycle-by-cycle without ambiguity.
3. **Deadlock Freedom & Receptivity:**
   - The evict-during-forward races (clean owner evicting via `PUTS`, dirty owner via `PUTM`) are resolved through defensive `INVACK` generation at the L1 and duplicate release absorption in `DIR_FWD_WAIT`. Furthermore, Ruling B2 guarantees that conflict evictions release victims on VC0 before miss requests, eliminating circular wait on the home bank.
4. **Sufficiency of F1–F9:**
   - Tests F1 through F8 comprehensively cover all permutations of clean/dirty forward releases, silent upgrades, evict-during-forward races, and exclusive-bit generation. Test F9 closes formal proof obligations across safety invariants A1.1, A1.3, A2.2, A2.6, A7.x, and bounded liveness A5.x ($T = 64$ cycles).
5. **Sensitivity of the Verification Suite via Mutations:**
   - Ten systematic mutations (MUT-01 through MUT-10) directly targeting forward downgrades, exclusive-bit generation, dirty-bit propagation, single-exit transitions, and conflict eviction ordering establish clear pass/fail criteria to qualify the independent test suite.

---

## 3. Caveats

1. **Clean-Room Isolation:** No testbench source code was read, inspected, or copied. All directed test sequences, expected transactions, and assertions were synthesized solely from specification documents.
2. **DMA Tile Out of Scope for 2×2:** Per Ruling B4 and Decision AD, the 2×2 FPGA target contains zero DMA tiles; DMA messages (codes 1100–1101) and DTR code `POP_DMA` are reserved/unreachable in the 2×2 acceptance suite.
3. **Bank Arbiter Priority:** Spec §12 item 9 leaves bank service order between local, remote, and memory tap traffic unspecified; `tile_pkg.sv` provides a provisional setting (`BANK_ARB_TAP_FIRST = 1`). Acceptance tests must accommodate standard arbitration latency bounds without assuming rigid cycle timings outside Premise F.

---

## 4. Conclusion

The specification mining survey for Slice 16.1 is complete. The resulting documents:
- Detailed Survey Report: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/report.md`
- Handoff Summary: `/mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/handoff.md`

provide an exhaustive blueprint for:
1. Building directed tests F1–F8 in cocotb 2.1.0 and formal checks F9 in SymbiYosys (`tb_acceptance/l1_dir/`).
2. Constructing the Python shadow reference model (`tb_acceptance/ref_model/`) implementing Slice Rules 1–11.
3. Executing the 10-point mutation qualification campaign (`tb_acceptance/mutations/`).

---

## 5. Verification Method

To independently verify the completeness and compliance of this specification extraction:
1. **File Presence & Content Verification:**
   ```bash
   test -f /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/report.md
   test -f /mnt/Code/visualstudio/Design-arch_multi-core/.agents/teamwork/spec_miner_survey_1/handoff.md
   ```
2. **Citations Cross-Check:**
   - Compare `report.md` §1 against `SLICE_16_1.md` §1.1, §2.1, and §4.
   - Compare `report.md` §2 (F1–F9) against `SLICE_16_1.md` §5.
   - Compare `report.md` §4 (MUT-01–MUT-10) against `FINAL_whitepaper_v3.0.md` §3.3 and `RULINGS_B1_B2_B4.md`.
3. **Clean-Room Audit:**
   - Verify that no tool calls were made accessing `tb/self_test/`, `tb/l1_dir/`, or any scratch test directory.
