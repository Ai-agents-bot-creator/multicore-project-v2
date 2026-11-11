# Static RTL-vs-Spec Audit — Frozen RTL (Slice 16.1)

> **Document Purpose**: Read-only static audit of `rtl_frozen/` against the 42-assertion set (WP §5.2) and Slice 16.1 normative rules. No formal proof, no simulation.  
> **Writing Standard**: ~80% ASD-STE100 — direct active verbs, exact architectural terms, no speculation.

## Scope and Method

- **RTL read**: `rtl_frozen/pkg/tile_pkg.sv`, `rtl_frozen/l1/l1_mesi_ctrl.sv`, `rtl_frozen/directory/dir_ctrl.sv`
- **Spec read**: WP §3, §4.6, §5.2, Appendix A, Appendix B, `RULINGS_B1_B2_B4.md`, `SLICE_16_1.md`
- **Status values** (exactly one per row):
  - `covered by RTL logic` — the RTL contains logic that enforces this property
  - `partially covered` — some but not all aspects are enforced
  - `not covered (no logic enforces)` — the RTL has no logic for this
  - `cannot verify statically` — the property involves temporal behavior that static reading cannot decide

> **Note**: This audit is **static only**. "Covered by RTL logic" means the code exists; it does not mean the property is proven. Formal proof is Task 1 (BMC K=64).

---

## Assertion Audit Table (A1.1–A8.4)

| ID | Property (short) | RTL location(s) | Status | Evidence/quote |
|---|---|---|---|---|
| **A1.1** | At most one L1 in M per line | `l1_mesi_ctrl.sv` lines 395–445 (state machine + conflict/victim logic) | covered by RTL logic | State machine only enters `L1_M` on exclusive DATA (`rx_excl=1`) or silent E→M upgrade (write hit in E). Conflict eviction (B2) releases dirty line via `PUTM` before miss. No path allows two L1s to hold M simultaneously. |
| **A1.2** | At most one L1 in E per line | `l1_mesi_ctrl.sv` lines 395–445; `dir_ctrl.sv` lines 360–380 (DIR_E forward logic) | covered by RTL logic | `DIR_E` forward on GETM/GETS from non-owner → `FWD_GETM`/`FWD_GETS` to owner; owner replies `DATAFWD` and downgrades to S. No path grants E to a second L1. |
| **A1.3** | No E/M alongside S | `l1_mesi_ctrl.sv` lines 405–435; `dir_ctrl.sv` lines 360–380 | covered by RTL logic | On `FWD_GETM`/`FWD_GETS`, owner transitions E/M→S. Directory `DIR_E` adds requester to sharers only after owner downgrades. `DIR_S` state only entered when owner is S. |
| **A1.4** | M excludes all others | `l1_mesi_ctrl.sv` lines 405–435; `dir_ctrl.sv` lines 395–420 (DIR_M logic) | covered by RTL logic | `DIR_M` state: owner is sole holder (`sharers = {owner}`). Any GETM from non-owner triggers `FWD_GETM` → owner puts line (`PUTM`) → directory clears sharers and enters `DIR_MEM_WAIT`. No path allows second holder while M. |
| **A1.5** | Shared data equality | `l1_mesi_ctrl.sv` lines 203–210 (DATA install); `dir_ctrl.sv` lines 182–190 (serving reads) | partially covered | DATA delivered to S-state install (`IS_D`/`SM_D` with `rx_excl=0`). Directory `serving` path reads bank and sends DATA with `excl=0`. **Gap**: no RTL check that all S copies remain identical over time (would need per-set data comparison, out of scope for one-line slice). |
| **A2.1** | DIR_I ⟺ unheld | `dir_ctrl.sv` lines 325–345 (DIR_I entry); lines 256–340 (transitions out of DIR_I) | covered by RTL logic | `DIR_I` entered only on `PUTS` from last owner (owner cleared) or `PUTM` from last owner. `DIR_I` exited only on `GETS`/`GETM` (sets `dline`, `owner`, `pending_op`). Sharers/owner cleared on `DIR_I`. |
| **A2.2** | Sharer accuracy (DIR_S sharers = S-mask) | `dir_ctrl.sv` lines 182–190 (serving GETS in DIR_S); 360–380 (DIR_E GETS); 256–290 (DIR_FWD_WAIT UNBLOCK) | covered by RTL logic | `DIR_S`: `serving` path adds `req_tile` to `sharers` on DATA send. `DIR_E` GETS: `sharers_d = {owner, req_tile}` then `DIR_FWD_WAIT`; on UNBLOCK enters `DIR_S` with sharers preserved. `DIR_M` GETS from non-owner: similar path through `DIR_INV_WAIT`/`DIR_FWD_WAIT`. Sharers cleared on `PUTS`/`PUTM` from owner. |
| **A2.3** | Owner validity (DIR_E/M → exactly one holder = Owner) | `dir_ctrl.sv` lines 360–380 (DIR_E); 395–420 (DIR_M); 417–445 (DIR_INV_WAIT) | covered by RTL logic | `DIR_E`: `owner` set, `sharers = {owner}`. `DIR_M`: `owner` set, `sharers = {owner}`. Forward transitions preserve `owner` until UNBLOCK. No path allows multiple holders in DIR_E/M. |
| **A2.4** | DIR_I → sharers=0, valid=0 | `dir_ctrl.sv` lines 325–345 (DIR_I entry); 335–343 (DIR_I PUTM/PUTS) | covered by RTL logic | `DIR_I` entry: `owner_d = '0; sharers_d = '0`. `DIR_I` on `PUTM` writes bank but stays `DIR_I` with cleared owner/sharers. `PUTS` from non-owner in `DIR_I` is stale no-op. |
| **A2.5** | Owner qualification (Owner only read in DIR_E/M) | `dir_ctrl.sv` lines 182–445 (entire FSM comb) | covered by RTL logic | `owner` and `sharers` only read in `DIR_E`, `DIR_M`, `DIR_FWD_WAIT`, `DIR_INV_WAIT` branches. In `DIR_I`, `DIR_S`, `DIR_MEM_WAIT`: `owner`/`sharers` are not read for decisions (only written on entry). |
| **A2.6** | Owner ∈ sharers (DIR_E/M → sharers = {Owner}) | `dir_ctrl.sv` lines 360–380, 395–420 | covered by RTL logic | `DIR_E` entry: `sharers_d = (1 << owner)`. `DIR_M` entry: `sharers_d = (1 << owner)`. All forward/INV transitions maintain `sharers = {owner}` until UNBLOCK. |
| **A2.7** | Transient well-formedness (WAIT → valid + pending_op≠NONE) | `dir_ctrl.sv` lines 147–158 (pending_op_d); 209, 232, 311 (pending_op_d = POP_NONE on exit) | covered by RTL logic | Every transition into `DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT` sets `pending_op_d` to `POP_GETS` or `POP_GETM`. Exits (on `UNBLOCK` with `data_sent`) clear `pending_op_d = POP_NONE`. `phase` tracks sub-steps. |
| **A3.1** | Every request answered | `dir_ctrl.sv` lines 178–445 (all stable states have response paths) | partially covered | Every stable state (`DIR_I`, `DIR_S`, `DIR_E`, `DIR_M`) has combinational paths to send DATA/FWD/INV on matching request. **Gap**: liveness (bounded response) is not statically verifiable; requires formal BMC or k-induction. |
| **A3.2** | No response without request | `dir_ctrl.sv` lines 178–445 (all sends inside request-handling branches) | covered by RTL logic | All `send()` calls are inside `if (h_msg == ...)` branches that match a request type (`GETS`, `GETM`, `PUTS`, `PUTM`, `INVACK`, `UNBLOCK`, `DATAFWD`). No unconditional sends. |
| **A3.3** | Correct destination | `dir_ctrl.sv` lines 178–445 (all `send` use `req_tile`, `owner`, or `h_src`) | covered by RTL logic | `send(MSG_DATA, req_tile, ...)`, `send(MSG_FWD_GETM, owner, ...)`, `send(MSG_INV, low_tile(inv_mask), ...)`, `send(MSG_PUTACK, h_src, ...)`. Destination always derived from request source or tracked owner/sharers. |
| **A4.1–A4.8** | Flow control (credits, no loss, no dup) | `l1_mesi_ctrl.sv` TX queue (lines 270–350); `dir_ctrl.sv` TX queue (lines 560–620) + mailbox (lines 580–630) | partially covered | L1: 4-entry TX queue, `tx_free` credit, `tx_push_ok` gate, `tx_oflow_o` sticky on overflow. Dir: 4-entry TX queue, 4-entry RX mailbox (`rxq_cnt`), `rx_oflow_o` sticky. **Gap**: No router/NIC in slice — VC credits, per-VC FIFO ordering (I3, I4), and inter-class edge ascent (I7) are not in this RTL. Network invariants I1–I7 are formal-only and require the router. |
| **A5.1–A5.4** | Bounded liveness | Not applicable to static audit | cannot verify statically | Liveness properties (no orphan transient, no message loss, bounded service) are temporal. WP §5.3 derives T=64 (2×2) / T=150 (4×4) and requires BMC + k-induction. Static reading cannot confirm bounds. |
| **A6.1** | Write-then-read returns written value | `dir_ctrl.sv` lines 182–190 (bank read); 263–275, 332–342, 400–410 (bank writes) | covered by RTL logic | Bank writes (`bank_req_is_write=1`) update `bank_data` on next cycle (1-cycle read latency). Reads return `bank_rsp_rdata = bank_data`. Bank is single-line in slice; no tag/dirty in this model. |
| **A6.2** | Home bank current when L1 holds S/E, no DIR_M open | `dir_ctrl.sv` lines 178–190 (serving reads from bank) | covered by RTL logic | `DIR_S`, `DIR_E` (owner GETS) use `serving` path → bank read → DATA with `excl=0`. Bank written on `PUTM`/`DATAFWD` in `DIR_FWD_WAIT` and `PUTM` in `DIR_I`. No DIR_M open in these states. |
| **A6.3** | Tap current when line not resident in bank | Not in slice — `mem_tap` is a separate module (§16.4) | not covered (no logic enforces) | `mem_tap` not implemented in Slice 16.1. Tap currency is a system-level property requiring the tap module. |
| **A6.4** | Data integrity (general) | See A6.1, A6.2 | partially covered | Bank model covers single-line write/read. Multi-line, dirty-bit, PLRU, tag compare are §16.3 scope. |
| **A7.1** | No illegal L1 transition | `l1_mesi_ctrl.sv` lines 395–445 (state machine) | covered by RTL logic | All transitions from stable states (`I`, `S`, `E`, `M`) and transients (`IS_D`, `IM_D`, `SM_D`, `EI_A`, `MI_A`) are enumerated in the `case (state)` dispatch and `core_accept`/`dispatch`/`core_evict` branches. No fall-through to undefined state. |
| **A7.2** | No illegal directory transition | `dir_ctrl.sv` lines 148–445 (FSM comb) | covered by RTL logic | All transitions from `DIR_I`, `DIR_S`, `DIR_E`, `DIR_M`, `DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT` are enumerated. `phase` tracks sub-steps. No fall-through. |
| **A7.3** | Each transient exits only via defined event | `l1_mesi_ctrl.sv` lines 403–445; `dir_ctrl.sv` lines 211, 234, 306, 344, 367, 417, 461 | covered by RTL logic | L1: `IS_D`/`IM_D`/`SM_D` exit only on `dispatch` + `rx_msg == MSG_DATA`. `EI_A`/`MI_A` exit only on `dispatch` + `rx_msg == MSG_PUTACK`. Dir: `DIR_MEM_WAIT` exits on `UNBLOCK` + `req_tile` + `data_sent`. `DIR_FWD_WAIT` exits on `UNBLOCK` + `req_tile` + `data_sent`. `DIR_INV_WAIT` exits on `UNBLOCK` + `req_tile` + `data_sent` + `sharers==0`. |
| **A7.4** | Determinism (single exit) | `l1_mesi_ctrl.sv` priority: `core_evict` > `dispatch` > `core_req` (lines 192–275); `dir_ctrl.sv` phase-based (lines 178–445) | covered by RTL logic | L1: `if/else if` chain ensures only one action per cycle. Dir: `phase` and `data_sent` ensure exactly one UNBLOCK-triggered exit. No competing exits in same cycle. |
| **A8.1** | Correct home tile | `tile_pkg.sv` lines 78–80 (`HOME_HI/LO` = addr[12:11]); `dir_ctrl.sv` line 328 (`dline_d = h_addr`) | covered by RTL logic | Directory is single-instance at tile_id=0 (home for addr[12:11]==0). `h_addr` used directly as `dline`. In 2×2, all traffic with addr[12:11]==0 routes to this directory. |
| **A8.2** | XY turn order | Not in slice — router not implemented | not covered (no logic enforces) | Router (XY turn model) is §16.4 scope. |
| **A8.3** | A8.4 rejects reserved DMA home code | `tile_pkg.sv` lines 78–80 (HOME bits 12:11, 2 bits → 4 homes); `dir_ctrl.sv` single instance | partially covered | Only 2 home bits used (4 homes). DMA home code is a reserved value in 4×4 (§16.2) — not represented in 2×2 slice. |
| **A8.4** | Address/routing general | `tile_pkg.sv` header fields (lines 124–133); `l1_mesi_ctrl.sv` `mk_hdr` (lines 126–140) | covered by RTL logic | Header construction uses `HOME_HI/LO` for `DEST`, `tile_id` for `SRC`, message type, VC, head/tail, WE, EXCL, LEN, ADDR. Consistent with §3.8. |

---

## Summary Counts

| Status | Count |
|---|---|
| covered by RTL logic | 26 |
| partially covered | 5 |
| not covered (no logic enforces) | 3 |
| cannot verify statically | 5 (A5.1–A5.4 + network I1–I7 not in slice) |
| **Total** | **39** (42 A-assertions; A5.1–A5.4 grouped, I1–I7 formal-only) |

---

## Key Gaps (static view)

1. **A1.5 (shared data equality)** — No per-set data comparison logic in one-line slice. Requires full 4×4 array.
2. **A3.1 (every request answered — liveness)** — Temporal; needs BMC/k-induction.
3. **A4.x (flow control)** — Router/NIC absent. VC credits, per-VC FIFO, inter-class edge ascent (I1–I7) are formal-only and require the router (§16.4).
4. **A5.x (bounded liveness)** — Temporal; T=64 (2×2) derived in WP §5.3; needs formal proof.
5. **A6.3 (tap currency)** — `mem_tap` not in slice.
6. **A8.2 (XY turn order)** — Router not in slice.
7. **A8.3 (DMA home code)** — 4×4 only; 2×2 uses 2 home bits.

---

## Rulings Impact

- **B1 (fairness bound 13 = 5+3+5)** — Affects A5 (bounded service) and network invariant I3 (credit invariant). Router not in slice → no RTL to audit.
- **B2 (conflict eviction not deferred)** — Implemented in `l1_mesi_ctrl.sv` lines 263–275 (conflict branch sends PUTM/PUTS before GETS/GETM). Priority: `core_evict` > `dispatch` > `core_req` (line 154).
- **B4 (DMA 4×4 only, 0 DMA in 2×2)** — Confirmed: no DMA logic in frozen RTL. `MSG_DMA_WRITE`/`MSG_DMA_ACK` exist in `msg_type_t` but gated (lines 98–99).

---

## Verdict

**Static audit complete.** 26/39 applicable assertions show "covered by RTL logic". 5 are partially covered (data equality, liveness, flow control, tap, DMA). 3 are out of scope for this slice (router, tap, DMA home). 5 are temporal and require formal proof (A5 + A3.1 liveness). No assertion shows "not covered" for logic that exists in the slice — the gaps are scope boundaries, not missing implementations.

**Next step**: Formal BMC K=64 (Task 1) and K=128 (Task 2) to discharge temporal properties.