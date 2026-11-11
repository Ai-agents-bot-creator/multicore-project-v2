# Problem Log

> **Document Purpose**: Systematic post-mortem ledger recording every hardware defect, reproduction method, root cause analysis, resolution patch, verification proof, and engineering lesson learned.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — structured 6-field chain, direct causal analysis, and unambiguous technical vocabulary.

Format: Symptom → Reproduction → Root cause → Resolution → Verification → Lesson

## P-001: L1_TAG_W computed as 26 b instead of 24 b

**Symptom**: `L1_TAG_W = ADDR_W - L1_SET_LO` evaluates to 32-6=26, but WP §3.6 states the stored L1 tag is addr[31:8] = 24 bits.

**Reproduction**: Read `rtl/pkg/tile_pkg.sv` line 42. The comment says "24 always" but the expression yields 26 because `L1_SET_LO = 6` is the low bit of the *index*, not one past the high bit.

**Root cause**: The L1 set index occupies bits [7:6] (two bits). The tag starts at bit 8, so width = ADDR_W - (L1_SET_HI + 1) = 32 - 8 = 24. Using `L1_SET_LO` instead of `L1_SET_HI + 1` double-counted the index bits.

**Resolution**: Changed expression to `ADDR_W - (L1_SET_HI + 1)` where `L1_SET_HI = 7`. Comment updated to `// 24 always: stored tag = addr[31:8]`.

**Verification**: `verilator --lint-only -Wno-UNUSEDPARAM -Wno-DECLFILENAME rtl/pkg/tile_pkg.sv` exits 0 clean after the fix.

**Lesson**: When deriving a field width from an address map, use the *high* bit position of the excluded field plus 1, not the low bit position.

## P-002: WP Appendix C VC ID row cited wrong invariant (I3 instead of I2)

**Symptom**: Appendix C header-flit table row [43:42] reads "formal invariant I3" for the VC check. I3 is the credit invariant. The VC check is I2.

**Reproduction**: `grep "43:42" white_papers/final/FINAL_whitepaper_v3.0.md` shows "formal invariant I3". §5.3 line 648 of the WP lists: "I1 XY path; I2 flit.VC==class(flit.msg); I3 credit invariant".

**Root cause**: Copy-paste error when writing the Appendix C table; I3 was used where I2 was intended.

**Resolution**: Changed "invariant I3" to "invariant I2" in that row only. Re-rendered `diagrams_rendered.html` via `pd/v1/build_diagrams_html.py`. Updated `cross-check-snapshot/`.

**Verification**: `grep "43:42" white_papers/final/FINAL_whitepaper_v3.0.md` now reads "formal invariant I2"; package gate (live, post-B5) `python3 pd/v1/verify_patch_set.py --dir white_papers/final --build-script pd/v1/build_diagrams_html.py` → RESULT: PASS 131/131, exit 0.

**Lesson**: Invariant cross-references must be checked against the numbered list in §5.3 at the time of writing, not assumed from memory.

## P-003: Concurrent owner eviction breaks per-cycle sharer equality (old A2.2, ruling B5)

**Symptom**: A BMC counterexample (depth 128) and a directed test both reach the same ordering: the owner of a line evicts while a forward to another tile is outstanding. The directory exits `DIR_FWD_WAIT` and commits a sharer set that still names the owner, although the owner has already released the line. The old A2.2 wording ("sharers equal the S-mask exactly, no stale bits") fails at that instant: `u_sva.a2_2` fails at step 48 with `dir_state=DIR_S, sharers=0001` while the named tile holds no S copy.

**Reproduction**: `tb_rtl_evidence/sby_k128/l1_dir/engine_0/trace.vcd` decoded by `/tmp/opencode/parse_trace.py` (fails at t = 470, trace ends #490); directed test `tb_rtl_evidence/directed_owner_evict/` (2 orderings); `grep -n "a2_2" tb_rtl_evidence/sby_k128/l1_dir/logfile.txt` → `failed assertion fml_l1_dir.u_sva.a2_2 at sva_l1_dir.sv:74.5-75.65 step 48`.

**Root cause**: Three-way VC reasoning: the owner's release `PUTS` travels on VC0, the requester's `UNBLOCK` on VC2, and no FIFO order relates messages on different virtual channels. The directory can absorb the `UNBLOCK` first, exit `DIR_FWD_WAIT`, and commit a sharer set that still includes the owner while the `PUTS` is in flight. The transient is inherent to an asynchronous release notification, not an RTL defect: the directory absorbs the `PUTS`, clears the bit and self-corrects, and data integrity is unaffected. The old A2.2 wording assumed instantaneous message delivery and is therefore unachievable per cycle.

**Resolution**: Ruling B5 (applied to the spec package; `white_papers/final/`): A2.2 becomes two clauses under one assertion ID — A2.2a "no missing bits" (strict: `DIR_S` ⟹ every tile holding the line in S has its bit set) and A2.2b "bounded extra bits" (a stale bit only while that tile's `PUTS`/`PUTM` is in flight, cleared within T = 64). The committed set on the `DIR_FWD_WAIT` exit excludes a tile that has already released the line (B5.3); the vector is a conservative superset, never a subset (B5.2); no RTL change for the Case-C bookkeeping lag (B5.4). Rejected alternatives: routing `PUTS` on VC1 (breaks invariant I2, VC = class) and adding `PUTACK` to S-state evictions (extra round trip, deadlock risk).

**Verification**: Directed test: 2 orderings, golden `TESTS=2 PASS=2` in `tb_rtl_evidence/directed_owner_evict/evidence/`. Negative control `dir_ctrl_mut.sv` (line 314 `sharers_d = sharers & ~(1 << req_tile)` drops a *missing* bit): `PASS=0 FAIL=2` with the fault present in the log (`A2_2A_FAIL t=24 missing=0001`) — the control asserts the fault is present, not that the symptom is absent. Depth-128 trace decode (T4.5): state path `DIR_I → MEM_WAIT(80) → DIR_E(260) → FWD_WAIT(270) → DIR_S(470) → INV_WAIT(480)`; exactly one forward (`FWD_GETS s0->d1 vc1` at t=280, target tile in `EI_A`, i.e. evicting, not mid-miss); **zero INV messages in the whole trace** — so for this trace the answer to the §12 item 12 question is "no hazard observed, transient only". Package gate 131/131, docs gate 47/47.

**Review finding (recorded with this entry)**: A2.2a is **vacuously true in a mid-miss window** — when no tile holds the line in S (every candidate tile mid-miss, `L1_IM_D`/`L1_SM_D`), both sides of the implication hold trivially, so sharer accuracy does not constrain the directory in that window. The related question — may the directory send an INV or FWD to a tile with an outstanding miss on the same line (Lemma L1)? — is **open as §12 item 12** and is not covered by B5. The K=64 BMC run with assertions live (Task 0) must report its evidence before B5 can be closed; B5 stays open until then.

**Lesson**: A per-cycle equality property over messages that cross clock/VC boundaries encodes a delivery assumption the hardware does not guarantee; state it one-sided (never a missing bit) and bound the other side by the message flight time.

## P-004: Concurrent-upgrade race sends a same-line INV to a mid-miss tile (ruling B6)

**Symptom**: The concurrent-upgrade race — two sharers of one line upgrade at the same time — makes the directory issue an INV to a tile that is itself mid-miss (`L1_SM_D`) on that line. §3.3 rule 6 and Lemma L1 (§4.6) both declared a same-line message impossible, so the §4.6 deadlock-freedom proof rested on a false premise. This answers §12 item 12's open question ("may the directory send an INV to a tile with an outstanding miss on the same line?") with **yes**.

**Reproduction**: `tb_rtl_evidence/directed_upgrade_race/` — Phase A: tile 1 `GETS` → `DIR_E` owner=1. Phase B: tile 0 `GETS` → `DIR_S`, sharers=0b11 (both S). Phase C: both stores issued in the same cycle → both S-store-hits send `GETM` → the directory pops one, enters `DIR_INV_WAIT`, and sends INV to the other sharer — which is in `L1_SM_D`. Golden log (`golden_run.log`): `B6_1 t=8 INV delivered to tile 0 in SM_D (mid-miss) dir_state=INV_WAIT`.

**Root cause**: The directory excludes only the *requester* (`req_tile`) from the INV sweep. In the race the second sharer has already sent its own `GETM` and is waiting in `SM_D`, so it receives a same-line INV while its miss is open. The old premise ("a same-line INV cannot occur") was false; the race is inherent to two concurrent upgrades.

**Resolution**: Ruling B6 (WP row AH): a same-line INV in `IS_D`/`IM_D`/`SM_D` **aborts the outstanding miss** — the L1 invalidates its copy, answers INVACK immediately, and re-issues the access once it holds the line again; deferral is forbidden (it deadlocks against the one-outstanding-transaction-per-bank directory). Lemma L1 restated to "no same-line message is *serviced*", with the abort as the single exception. RTL: `rtl/l1/l1_mesi_ctrl.sv` gains the abort path (same-state self-edge per Appendix A row 1007 — no new FSM state) plus the `abort_o` observability port (v4 Task 1). Formal harness: `env_unblk_installed` assumption (UNBLOCK from the requester implies its L1 is in `{S,E,M}` — the real L1 never sends UNBLOCK before DATA install; v4 Task 0).

**Verification**: v4 Task 0 — BMC K=64 with assertions live (32 assertions + 4 assumptions, live count 36 `$check`). v4 Task 3 — golden directed run: B6.1 (INV reaches the mid-miss tile, t=8), B6.2 (`abort_o` t=10, INVACK t=11). Negative control `l1_mesi_ctrl_defer_inv.sv` (same-name replacement that holds a same-line INV during a miss): B6.1 passes — the fault is present — and B6.2 fails with `DEFER-INV FAULT PRESENT`, i.e. the control asserts the fault is present, not that the symptom is absent. Lint 6/6.

**Follow-on finding (recorded with this entry)**: the same test shows B6.3 (both stores complete) **failing on golden RTL**: the directory stalls in `DIR_INV_WAIT` with `rxq` head = the second tile's `GETM` while the `INVACK` sits behind it (`RXQ cnt=2 head_msg=GETM`), because `DIR_INV_WAIT` pops only `INVACK`/`PUTS`/`PUTM`/`UNBLOCK` and the slice's rxq is arrival-ordered. WP §3.5 line 287 fixes VC arbitration **inside the router** (RESP > INV > FWD > REQ), but the directory controller's per-VC RX pop order is not specified, and the directed slice's round-robin merge does not model it. Escalated as a challenge in the v4 report §8 — not fixed here (a FAIL is data). **Resolved by ruling B7.1 — see P-005**: the per-VC receive path landed in v5, and the golden rerun completes (B6.3 both stores: tile1 t=28, tile0 t=61; B6.4 exactly one M).

**Lesson**: When a spec declares an event impossible, build the directed test that creates the event before trusting any proof that depends on it; and check that the testbench's interconnect model carries the ordering properties the real fabric has (per-VC priority), or the test will find the model's deadlock instead of the design's.

## P-005: Directory receive path was arrival-ordered — a queued GETM head-blocks the INVACK (ruling B7)

**Symptom**: With ruling B6's abort implemented, the directed upgrade-race test still stalls: the directory sits in `DIR_INV_WAIT` with the mailbox diagnostic `RXQ cnt=2 head_msg=GETM` — the second tile's `GETM` at the head, the `INVACK` behind it — while `DIR_INV_WAIT` pops only `INVACK`/`PUTS`/`PUTM`/`UNBLOCK`. Neither store completes and zero tiles end in M. The verification team's reference model reproduced the same state, independently confirming a deadlock witness rather than a transient stall.

**Reproduction**: `cd tb_rtl_evidence/directed_upgrade_race && make` on post-B6 RTL (v4): `B6_1 t=8` (INV to the mid-miss tile), `B6_2 abort t=10 / INVACK t=11`, then the stall — `RXQ rd=2 wr=0 cnt=2 head_msg=GETM inv_mask=0b0 pending_req=1`, `final_dir=INV_WAIT`, both L1s `SM_D` at timeout (v4 `golden_run.log`).

**Root cause**: A genuine specification gap: WP §3.5 fixed the class priority **RESP > INV > FWD > REQ inside the router** (§3.5 item 1) and said nothing about the **directory controller's receive path**, so a single arrival-ordered directory queue was specification-conformant as written — and deadlock-prone: while a transient is open the directory pops only the messages it accepts, so any request that arrived before the required response (here `GETM` ahead of `INVACK`) head-of-line blocks the message that must complete the transient.

**Resolution**: Ruling B7.1 (WP §3.5, ledger row AI): the home tile's receive path holds **one queue per VC** and pops them by the same class priority as the fabric, so a response is never head-of-line blocked behind an earlier request; the transient's own expected message class still wins within its transient (the FSM still pops only what it accepts, so `DIR_INV_WAIT` sees its `INVACK` first among acceptable messages). RTL: `rtl/directory/dir_ctrl.sv` — the single arrival-ordered mailbox becomes four per-VC queues (`rxq_* [4][RXQ_DEPTH]`, depth 4 each), push classified by `msg_to_vc()` at publish, and a fixed-priority combinational arbiter selects `h_vc` (RESP > INV > FWD > REQ); the FSM accept sets are unchanged and per-VC FIFO ordering (I4) holds inside each queue. Ruling B7.2 (completion/decline of the abandoned request) required no further change: the tile accepts the stale grant — the parked access is re-driven by the DATA-install path — so the directory's transient always exits. §12 item 13 (bounded progress under repeated aborts) was recorded **open** by B7 — ruling **B8** (§4.6 Lemma L2, FIFO re-issue ordering: a re-issued access is a new request, enqueued at the back) **closes** it.

**Verification**: v5 Task 3.6 — golden rerun after B7.1: B6.1 (t=8) and B6.2 (abort t=10, INVACK t=11) unchanged; **B6.3 now passes** — both stores complete within the 600-cycle window (tile1 t=28, tile0 t=61); **B6.4** exactly one M (`l1_0=M l1_1=I`, `final_dir=M sharers=1`); at the end all four VC queues are empty (`vc_cnt[REQ,FWD,RESP,INV]=[0,0,0,0]`). Negative control unchanged: the defer-INV mutant is still caught — B6.1 passes (fault present) and B6.2 fails `DEFER-INV FAULT PRESENT` (`mutant_run.log`). Surrounding gates after the mailbox change: lint 6/6, directed owner-evict 2/2, F2–F8 8/8, mutation matrix 9/9, package gate 133/133.

**Lesson**: a priority discipline stated for one component (the router) leaves every other component's ordering unspecified — and any component whose pop set depends on its state needs class-priority arbitration across its input queues, or a state-dependent pop set becomes a head-of-line deadlock.

