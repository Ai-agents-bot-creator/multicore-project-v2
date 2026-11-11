# Formal Assertion Scope — the K=64 harness, as an ID list

**Scope of this file.** The formal item is *"BMC over the declared assertion subset, under the documented assumptions"*. This file publishes that subset as an **ID list** — not a count. A count ("42 properties / 36 cells") is not a scope.

**How the list was produced.** The IDs below were extracted from the **elaborated design** of the run in `tb_rtl_evidence/sby_k64/l1_dir/`, not from prose: the `$check` cells in `model/design.il`, each with the `attribute \src` that names the harness source line it came from. The extraction is reproducible:

```bash
cd tb_rtl_evidence/sby_k64/l1_dir
grep -cE 'cell \$check' model/design.il     # 36
grep -c 'parameter \\FLAVOR "assert"' model/design.il    # 32
grep -c 'parameter \\FLAVOR "assume"' model/design.il    # 4
```

**Result: 36 `$check` cells = 32 asserts + 4 assumes.** The 32 asserts are 31 property cells from `sva_l1_dir.sv` plus 1 environment-sanity assert (`env_no_ovf`) from `fml_l1_dir.sv`. The 4 assumes are all in `fml_l1_dir.sv`.

**The two sets must not be confused.**

- The **specification set** is the 42 bound properties (`FINAL_whitepaper_v3.0.md` §5.2: A1–A8) plus the 7 formal-only network invariants I1–I7 (§5.2, note: 42 + 7 = 49 total).
- The **harness subset** is what this K=64 run actually checks. It is legitimately smaller than the specification set — the harness is a 2-tile, single-line slice, and the router/NIC/L2-array parts of the specification (A4, A6, A8, I1–I7) are not in this slice at all.

---

## 1. The harness subset — every ID, with its source line

Each row is traceable to a line in the harness source. IDs are the **harness** IDs (what the elaborated design contains); the specification ID each implements is given where the source makes the correspondence explicit.

| # | Harness ID | Spec ID | Source | What it checks |
|---|---|---|---|---|
| 1 | `a1_1` | A1.1 | `sva_l1_dir.sv:63` | not two L1s in `L1_M` |
| 2 | `a1_2` | A1.2 | `sva_l1_dir.sv:64` | not two L1s in `L1_E` |
| 3 | `a1_3` | A1.3 | `sva_l1_dir.sv:65` | no E/M holder alongside an S holder |
| 4 | `a1_4a` | A1.4 | `sva_l1_dir.sv:66` | `L1_M` excludes the other tile |
| 5 | `a1_4b` | A1.4 | `sva_l1_dir.sv:67` | `L1_M` (tile 1) excludes the other tile |
| 6 | `a2_1` | A2.1 | `sva_l1_dir.sv:71` | `DIR_I` iff no L1 holds the line |
| 7 | `a2_2` | A2.2 | `sva_l1_dir.sv:74` | `DIR_S` ⇒ sharers are exactly the S copies |
| 8 | `a2_3` | A2.3 | `sva_l1_dir.sv:77` | `DIR_E`/`DIR_M` ⇒ the only holder is Owner |
| 9 | `a2_4` | A2.4 | `sva_l1_dir.sv:81` | `DIR_I` ⇒ sharers and owner cleared |
| 10 | `a2_6` | A2.6 | `sva_l1_dir.sv:83` | `DIR_E`/`DIR_M` ⇒ Owner < NT and sharers = {Owner} |
| 11 | `a2_6b` | A2.6 (auxiliary) | `sva_l1_dir.sv:86` | no sharer bit names a tile outside the instance |
| 12 | `a2_7` | A2.7 | `sva_l1_dir.sv:88` | a `DIR_*_WAIT` transient implies `pending_op != POP_NONE` |
| 13 | `a3_1_data` | A3.x | `sva_l1_dir.sv:94` | no DATA without a pending request |
| 14 | `a3_1_dst` | A3.x | `sva_l1_dir.sv:95` | DATA goes to the requesting tile |
| 15 | `a3_1_fwd_state` | A3.x | `sva_l1_dir.sv:100` | a FWD exists only while an owner exists |
| 16 | `a3_1_fwd_dst` | A3.x | `sva_l1_dir.sv:102` | a FWD goes to the owner |
| 17 | `a7_dir_exit` | A7 | `sva_l1_dir.sv:110` | a directory transient exits only on UNBLOCK from the requester |
| 18 | `a7_0_isd` | A7 | `sva_l1_dir.sv:118` | tile 0 `L1_IS_D` exits legally |
| 19 | `a7_0_imd` | A7 | `sva_l1_dir.sv:120` | tile 0 `L1_IM_D` exits legally |
| 20 | `a7_0_smd` | A7 | `sva_l1_dir.sv:122` | tile 0 `L1_SM_D` exits legally |
| 21 | `a7_0_eia` | A7 | `sva_l1_dir.sv:124` | tile 0 `L1_EI_A` exits legally |
| 22 | `a7_0_mia` | A7 | `sva_l1_dir.sv:125` | tile 0 `L1_MI_A` exits legally |
| 23 | `a7_0_data` | A7 | `sva_l1_dir.sv:143` | tile 0's miss transient leaves only on DATA |
| 24 | `a7_0_ack` | A7 | `sva_l1_dir.sv:150` | tile 0's evict transient leaves only on PUTACK |
| 25 | `a7_1_isd` | A7 | `sva_l1_dir.sv:129` | tile 1 `L1_IS_D` exits legally |
| 26 | `a7_1_imd` | A7 | `sva_l1_dir.sv:131` | tile 1 `L1_IM_D` exits legally |
| 27 | `a7_1_smd` | A7 | `sva_l1_dir.sv:133` | tile 1 `L1_SM_D` exits legally |
| 28 | `a7_1_eia` | A7 | `sva_l1_dir.sv:135` | tile 1 `L1_EI_A` exits legally |
| 29 | `a7_1_mia` | A7 | `sva_l1_dir.sv:136` | tile 1 `L1_MI_A` exits legally |
| 30 | `a7_1_data` | A7 | `sva_l1_dir.sv:147` | tile 1's miss transient leaves only on DATA |
| 31 | `a7_1_ack` | A7 | `sva_l1_dir.sv:153` | tile 1's evict transient leaves only on PUTACK |
| 32 | `env_no_ovf` | environment | `fml_l1_dir.sv:236` | the stand-in interconnect does not drop flits |

**32 asserts**, all listed. There is no A5 cell in the harness: A5 is the *bounded-liveness* category (WP §5.2), and this campaign is a BMC safety run — A5 is not checkable by BMC and is not claimed here.

## 2. The four assumptions

| # | Harness ID | Source | Restriction |
|---|---|---|---|
| A1 | `env_dir_credit` | `fml_l1_dir.sv:241` | `assume(!dir_oflow)` |
| A2 | `env_dir_rx_msg` | `fml_l1_dir.sv:246` | the directory receives only L1→directory message types |
| A3 | `env_dir_dst` | `fml_l1_dir.sv:256` | the directory's response destination is a valid tile of this instance |
| A4 | `env_unblk_installed` | `fml_l1_dir.sv:266` | a UNBLOCK from the requester implies that tile holds the line in {S,E,M} |

**What becomes unproven if each assumption is false.**

- **A1 (`assume(!dir_oflow)` — the R5 / open-item-8 NIC credit gap).** The real NIC credit-gates the directory's mailbox; this slice has no NIC, so the environment is constrained to the contract that would keep the mailbox from overrunning. *If the assumption is false, the mailbox can overrun, the FIFO's contents become meaningless, and every `a2_*`/`a7_*` result that depends on the directory's view of the line (sharers, owner, pending_op) becomes unreliable* — the harness can manufacture a counterexample in which the FIFO has been corrupted and the property under test is not the one that actually failed. A `dir_oflow` occurrence in the trace invalidates the run, not just one property. This is a **state-space restriction, not a proof**; §16.9 (NIC credit management) must land before the result can be quoted unconditionally.
- **A4 (`env_unblk_installed` — UNBLOCK only after the data is installed).** WP §3.3 rule 6 / Appendix A: the requester emits UNBLOCK only on the DATA-install exit of `IS_D`/`IM_D`/`SM_D`, i.e. after it has received DATA and installed the line. *If the assumption is false, the harness may drive an UNBLOCK from a requester that never received DATA; the directory would then exit its transient and record an owner for a line nobody holds, so `a2_3` (owner validity) and `a2_7` (transient well-formedness) would fail for a reason that is an artefact of the harness rather than a defect in the RTL.* This assumption is what caused the earlier depth-128 `a2_2` counterexample to be reclassified as a harness artefact.

A2 and A3 are **environment-shape** restrictions (which message types may arrive, which destinations may be targeted). If either is false, a counterexample may reflect an impossible environment rather than an RTL defect; they constrain what the harness may do, not what the RTL may do.

## 3. The specification set that is NOT in this harness

Every ID below is in the specification set (WP §5.2) and **not** in the K=64 harness. The third column says where it is covered instead — that is a claim about *where the property is exercised*, and each entry is checked against the repo, not assumed.

| Spec ID | Count | In the K=64 harness? | Where it is covered instead |
|---|---|---|---|
| A1.5 — shared data equality | 1 | **no** | not implemented in the harness; the data-equality property is a bank/L2-array concern (the slice has no second data copy to compare) |
| A2.5 — owner qualification | 1 | **no** | not SVA-expressible (coding style: Owner is not read outside `DIR_E`/`DIR_M`); recorded in the harness source itself as `sva_l1_dir.sv:11-12` ("A2.5 ... is a coding-style property, not an SVA-expressible one"), checked by code review, not by an assertion. Not to be confused with **R5** in `docs/01_DECISION_LOG.md`, which is the NIC-credit *assumption* (A1 in the table above), not this property |
| A3.2–A3.6 — the rest of the message-protocol category | 5 | **no** | the harness checks the DATA/FWD half of A3 (`a3_1_*`); the request-side half is exercised by the directed tests and the transaction-level reference model, not asserted |
| A4.1–A4.8 — flow control (credits) | 8 | **no** | **not implemented at all**: there is no router/NIC in this slice (`rtl/nic/` and `rtl/router/` are empty directories; WP §3.8 nic.sv is future scope), so there are no credit counters to bound |
| A5.1–A5.4 — bounded liveness | 4 | **no** | not checkable by BMC; the orphan-transient bound is checked in the directed tests and the reference model (WP §5.3, bound *T*) |
| A6.1–A6.4 — data integrity (L2 array, memory) | 4 | **no** | **not implemented at all**: the slice has no L2 array and no memory tap (`rtl/mem_tap/` is empty; `rtl/l2/` has a bank and an L2 controller, neither in the formal slice); the bank is a single-line stub in the harness |
| A7 — the four category-level IDs | 4 | **partly** | the harness implements A7 as **15 per-state/per-tile cells** (rows 17–31), not as 4 category IDs; the category-to-cell mapping is 1:many |
| A8.1–A8.4 — address/routing | 4 | **no** | **not implemented at all**: no NIC and no router in this slice, so there is no home-tile decode or XY turn order to check |
| I1–I7 — network invariants | 7 | **no** | **not implemented at all**: these are formal-only properties of the router/NIC (XY path, VC preservation, credit invariant, delivery-or-termination, per-VC FIFO ordering, inter-class edge ascent), none of which exist in this slice |

**Counts.** Specification set: 42 bound properties + 7 invariants = 49. Harness subset: 32 asserts + 4 assumptions = 36 cells. These two numbers are **not** comparable — the subset is a strict, published subset, and the gap is itemised above rather than hidden in a count.

## 4. The status of the formal item

The formal item is **OPEN**, not green. It is *BMC over the declared assertion subset (rows 1–32 above), under the documented assumptions (A1–A4 above)*, and the K=64 depth is the target — the depth actually reached is reported from the solver's own output, never rounded up.

See `tb_rtl_evidence/FORMAL_K64.md` for the run's raw output and the depth reached.
