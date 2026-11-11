# SRS review — `SRS_final.docx` (v0.1, 04-11-2026)

**Verdict: the draft is not ready for a mentor.** It has absorbed the three rulings (B1/B2/B4)
correctly — that part is genuinely good — but it contains **six blocker-class defects**, of which
three would produce a *wrong implementation* if followed literally, and the traceability matrix
is unusable.

Everything below is checked against `FINAL_whitepaper_v3.0.md` (ruled, 130/130 gate) and
`SPEC_SHEET.md`. Findings are ordered by severity; each carries the exact replacement text.

---

## Summary

| Severity | Count | Character |
|---|---|---|
| **Blocker** | 6 | Wrong to an implementer or to a mentor: inverted protocol direction, a phantom assertion ID, a mis-ordered VC mapping, device capacity used as design target, a DMA signal in a build that has no DMA tile, an unusable traceability column |
| **Major** | 6 | Missing normative requirements, non-numeric coverage goals, 1-row test plans, unstated proposals, 5 malformed tables |
| **Minor** | 6 | Terminology drift, conditional-test scope, placeholders, unstated latency figures, silent power gap, exit-criteria wording |

**What is right and should be preserved:** FR-04 (fairness, threshold 5, port-granular output
arbiter, 5 + 3 + 5 = 13), FR-05 (conflict eviction released before the miss, via VC0), FR-07
(DMA 4×4-only, no 2×2 deliverable), AC-05 (T = 64, 13 rounds), §7.5 (DMA register map deferred
to the Week-8 gate), §8.2 (42 bound SVA + I1–I7). These match the ruled WP exactly.

---

## Blockers

### B1 — PUTS / PUTM direction is inverted in the acronym table

**§1.3 Definitions and Acronyms.** The draft says `PUTS | Directory-to-subscriber release
(clean)` and `PUTM | Directory-to-subscriber release (dirty)`.

Both are sent **by the L1 to the directory**, not by the directory to a subscriber. The WP's
message table: `VC0 | REQ | GETS, GETM, PUTS, PUTM, *DMA_WRITE*`, and the eviction rules are
`L1: MI_A, PUTM → dir: write bank, clear owner, PUTACK → L1: I`. An implementer following the
SRS would build the release path backwards.

**Replace both rows with:**

| Term | Meaning |
|---|---|
| PUTS | L1 → directory release notification (clean line; no data) |
| PUTM | L1 → directory release notification (dirty line; carries the data) |
| PUTACK | Directory → L1 acknowledgement of a release (exits `EI_A` / `MI_A`) |
| UNBLOCK | L1 → directory release event that selects the directory's successor state |

(UNBLOCK's direction is also worth stating: `L1 → dir`.)

### B2 — FR-02 cites "A13", an identifier that exists nowhere in the package

`FR-02 | The system shall deliver each message by XY deterministic routing (X then Y). | Must |
A13 / TC`

There is no assertion A13. The assertion set is **A1–A8 + I1–I7**; XY routing is **A8.x**
(*Address/routing: correct home tile; XY turn order*) and **I1** (XY path correctness). "A13" is
an internal review-finding ID, and it has leaked into the deliverable — a mentor grepping the WP
for "A13" finds nothing.

**Replace the Verified-by cell with:** `A8.x / I1`
**And §10:** add `| FR-02 | Formal / Simulation | A8.x, I1, TC-02 | Planned |`

### B3 — AC-03 states the VC classes in priority order, not index order

`AC-03 | Four virtual channels (RESP, INV, FWD, REQ classes).`

The WP assigns the VC index at the source from the message class and **never changes it in any
router** (that is network invariant I2 / I6). The index order is:

| VC | Class | Messages |
|---|---|---|
| VC0 | REQ | GETS, GETM, PUTS, PUTM, *DMA_WRITE* |
| VC1 | FWD | FWD_GETS, FWD_GETM |
| VC2 | RESP | DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, *DMA_ACK* |
| VC3 | INV | INV |

The draft's ordering — RESP, INV, FWD, REQ — is the **class-priority** order
(RESP > INV > FWD > REQ), not the VC index order. Swapping them makes every VC-indexed piece of
RTL wrong (the NIC's VC assignment, the router's VC allocation, the credit counters, and I2/I6).

**Replace AC-03 with:**

| ID | Assumption or constraint |
|---|---|
| AC-03 | Four virtual channels per port, indexed at the source and never altered by a router: **VC0 = REQ** (GETS, GETM, PUTS, PUTM, DMA_WRITE*), **VC1 = FWD** (FWD_GETS, FWD_GETM), **VC2 = RESP** (DATA, DATAFWD, INVACK, UNBLOCK, PUTACK, DMA_ACK*), **VC3 = INV** (INV). Arbitration priority across classes is fixed: RESP > INV > FWD > REQ, with the age escape. |

### B4 — the area targets use device capacity as the design target

| Draft | Problem |
|---|---|
| `AREA-01 \| FPGA LUT utilization \| ~53.2k LUTs (4x4 excluded on budget) \| ~53.2k` | 53,200 is the **available** LUT count on the device. As written, the target equals the whole device, so the design "meets" the target by consuming 100 % of it. |
| `AREA-02 \| FPGA BRAM / memory \| 80 BRAM max (2x2) \| 80` | The 2×2 estimate is **28 BRAM36** (favourable mapping); 80 is the *conservative* figure and also the ceiling. |
| `FPGA-03 \| LUT utilization \| ~53.2k \| ~53.2k` | Same error. |
| `FPGA-05 \| BRAM / DSP utilization \| 80 \| 80` | Conflates two resources, and **DSP must be 0** — the WP records 220 available DSP with target 0 and ceiling 0 (*no multipliers inferred*). |

**Replace AREA-01 / AREA-02 with the WP §6.1 table:**

| ID | Parameter | Target | Maximum | Conditions | Verified by |
|---|---|---|---|---|---|
| AREA-01 | FPGA LUT utilization (2×2) | ≤ 20,000 (38 % of 53,200); estimate ≈ 13,000–19,000 | ≤ 40,000 (75 %) | 2×2 build | Synthesis |
| AREA-02 | FPGA BRAM36 utilization (2×2) | ≤ 48; estimate 28 (favourable mapping) | ≤ 80 | 2×2 build | Synthesis |
| AREA-03 | FPGA DSP utilization | 0 | 0 | 2×2 build — no multipliers inferred | Synthesis |

**Replace FPGA-03 / FPGA-05 with:**

| ID | Parameter | Target | Limit | Verified by |
|---|---|---|---|---|
| FPGA-03 | LUT utilization | ≤ 20,000 | ≤ 40,000 | Synthesis |
| FPGA-05a | BRAM36 utilization | ≤ 48 | ≤ 80 | Synthesis |
| FPGA-05b | DSP utilization | 0 | 0 | Synthesis |

### B5 — §7.2's signal list contains a DMA signal for a build that has no DMA tile

`dma_wr | out | 1 | clk | DMA write request`

Ruling **B4** withdrew the DMA deliverable from the 2×2 build: the committed 2×2 mesh has exactly
four tile positions, all CPU tiles; the DMA tile is the 16th tile of a 4×4 mesh. A `dma_wr`
signal on the 2×2 interface contradicts the ruling the same document cites in FR-07.

It is also the wrong shape for the 4×4 case: the DMA engine is register-mapped over **two
channels** (SRC_LO, DST_LO, LEN, CTRL, STATUS, COUNT), not a single 1-bit signal.

**Replace §7.2 entirely.** The current five-signal list is not credible for a mesh with a
5-port router, 4 VCs, credit flow control and a directory — it needs at minimum:

| Signal | Dir | Width | Clock domain | Description |
|---|---|---|---|---|
| clk | in | 1 | sync | Main system clock |
| reset | in | 1 | sync | Global reset (assertion/deassertion discipline is ⚠ not specified in the WP — see the WP §15 list) |
| credit_in | in | 4 | clk | Per-VC credit from the downstream port (4 VCs) |
| credit_out | out | 4 | clk | Per-VC credit to the upstream port |
| port_in_data / port_in_valid / port_in_ready | in | flit (header+body) | clk | Inbound wormhole stream from a neighbouring port (4 per tile) |
| port_out_data / port_out_valid / port_out_ready | out | flit | clk | Outbound wormhole stream to a neighbouring port (4 per tile) |
| local_inject_* / local_eject_* | in/out | flit | clk | Local tile ↔ router path (L1/L2/directory ↔ NIC) |
| dma_* | — | — | — | **Not present in the 2×2 build** (ruling B4). In the 4×4 track: register-mapped, two channels — `DMA_SRC_LO/DMA_DST_LO/DMA_LEN/DMA_CTRL/DMA_STATUS/DMA_COUNT`. |

### B6 — the "Verified by" column mixes four identifier namespaces

| Cited | What it actually is | Usable as a verification reference? |
|---|---|---|
| `A1.1`, `A2.2`, `A5`, `A6`, `A8`, `I3` | assertion IDs | ✓ yes |
| `A13` | internal review-finding ID — exists nowhere in the package | ✗ phantom |
| `G9` | internal review-finding ID | ✗ phantom |
| `B1`, `B2`, `B4` | **decision/ruling IDs** — a ruling is not a check | ✗ wrong kind |
| `A`, `I`, `TC`, `A / B formal` | unresolvable fragments | ✗ |

The WP's §13 adjudication ledger uses a sequential label series — **A, B, … Z, AA, AB, AC** — not
B-numbers, so "B1" and "B2" are not ledger rows either. As it stands the column cannot be traced,
and FR-06's `A / B formal` cannot be resolved at all.

**Replace the whole Verified-by column with resolvable references only** (assertion ID + test ID):

| ID | Requirement | Priority | Verified by |
|---|---|---|---|
| FR-01 | The system shall maintain directory-based MESI coherence across tiles. | Must | A1.1–A1.5, A2.1–A2.7 / TC-01 |
| FR-02 | The system shall deliver each message by XY deterministic routing (X then Y). | Must | A8.x, I1 / TC-02 |
| FR-03 | The system shall use credit-based flow control with per-VC FIFOs of depth 4. | Must | I3, A4.x / TC-03 |
| FR-04 | The system shall arbitrate VCs by class priority (RESP > INV > FWD > REQ) with a per-(port, VC) age escape at threshold 5 and a port-granular output round-robin, serving every VC within 5 + 3 + 5 = 13 rounds. | Must | A5.x, I2 / TC-04 |
| FR-05 | The system shall evict with PUTS/PUTM + PUTACK and shall never evict silently; a conflict eviction shall release the victim before the miss request, both on VC0. | Must | A1.1, A1.2, A3.x / TC-05 |
| FR-06 | The system shall implement single-exit directory FSMs whose only exit is UNBLOCK. | Must | A7.x, A2.7 / TC-06 |
| FR-07 | The system shall support the DMA write path (GETM-mapped) in the 4×4 simulation scope only; no 2×2 DMA deliverable exists and `pending_op = DMA` shall be unreachable in the 2×2 build. | Should | A8.4 / TC-07 (4×4 only) |
| FR-08 | The system shall move a whole cache line in one 512-bit intra-tile transfer. | Must | A6.x / TC-08 |

And §10 must trace **all eight** FRs, not two (currently only FR-01 and FR-04 appear).

---

## Major

### M1 — §7.1's interface summary understates the protocol

The draft lists `GETS/GETM/FWD/INV/PUTS/PUTM/UNBLOCK/DMA` — mixing message names with class
names (`FWD` is a class, not a message), naming a non-existent message (`DMA` — the WP has
`DMA_WRITE` and `DMA_ACK`), and omitting **DATA, DATAFWD, INVACK, PUTACK, FWD_GETS,
FWD_GETM**. The WP's set is **12 core messages + 2 gated DMA messages**.

The omitted ones are exactly the forward-path mechanisms that §16.1 implements: `FWD_GETS` /
`FWD_GETM` (dir → owner), `DATAFWD` (owner → dir), `INVACK` (L1 → dir), `PUTACK` (dir → L1).
A mentor reading §7.1 would not know the forward path exists.

**Replace §7.1 with a two-row table listing all 14 messages with their direction, class, VC and
flit count, taken verbatim from the WP §3.3 message table.**

### M2 — the functional requirements omit roughly half the normative behaviour

No FR covers: **forward release** (rule 8 — the centrepiece of §16.1), the **DATA exclusive bit**
(rule 9), the **L2 per-line word** `{valid, tag, dirty}` (23 b at 2×2 / 21 b at 4×4), the
**DATAFWD dirty indication** (header bit [39]), **DIR_I victim write-back** (N4), the
**bank-first fill / inclusion policy**, the **address map and home-tile mapping**, the
**TILE_ID → mesh position mapping**, and **Premise R (receptivity)**. FR-01's blanket
"maintain MESI coherence" cannot substitute for requirements a tester can write a test against.

**Add FR-09…FR-14** (suggested wording):

| ID | Requirement | Priority | Verified by |
|---|---|---|---|
| FR-09 | On `FWD_GETS` the owner shall downgrade E/M → S and send `DATAFWD`; on `FWD_GETM` it shall downgrade E/M → I and send `DATAFWD`, and shall not send PUTS/PUTM (rule 8). | Must | A1.3, A2.2, A2.6 / TC-09 |
| FR-10 | The directory shall set the DATA exclusive bit to 1 only when the requester becomes the sole holder (a DIR_I grant or any GETM grant), and to 0 on every GETS grant including a forward (rule 9). | Must | A1.2, A1.3 / TC-10 |
| FR-11 | The L2 per-line word shall be `{valid, tag, dirty}` (23 b at 2×2, 21 b at 4×4); the dirty bit shall be excluded from tag comparison and way select. | Must | A6.x / TC-11 |
| FR-12 | A DATAFWD packet shall carry the dirty indication in header bit [39], set iff the owner held the line in M. | Must | A6.x / TC-12 |
| FR-13 | A `DIR_EVICT` whose victim is DIR_I with a dirty bank line shall take the WRITE_BACK sub-state; the dirty line shall never be silently dropped (N4). | Must | A6.x / TC-13 |
| FR-14 | An L1 with an outstanding miss shall continue to accept and service INV/DATA/INVACK/FWD traffic for other lines immediately, on a path independent of the miss path (Premise R). | Must | A3.x, A7.x / TC-14 |

### M3 — §8.3's coverage goals are not numeric and do not mirror the WP

The draft has `Statement / line | High` and `FSM | All single-exit states`. The WP §5.4 carries
four **numeric** criteria:

| Component | Metric | Target |
|---|---|---|
| Legal functional bins | — | 100 % |
| FSM states and transitions (L1 and directory) | — | 100 % |
| Assertions | — | 100 % pass, zero waivers |
| Cover properties | — | 100 % hit |

**Replace §8.3's rows with these four**, plus one row naming the open item: the pyuvm bin list
behind the numeric criteria is itself §12 item 2 (*not yet specified — do not invent*).

### M4 — the test plans are stubs

§8.4 has one row (`TC-01`); §9.5 has one row (`FV-01`). The WP defines **17 directed tests**
(§5.1) plus **5 conditional DMA tests (18–22)**, and §16 defines 14 implementation rows with
their own directed tests F1–F9. The SRS's test IDs should map onto the WP's numbering so the
two documents are traceable in both directions.

### M5 — §8.1 states proposals as fixed values

`Safety: BMC K = 64; Liveness: bounded T = 64; deadlock: structural lemma + k-induction k = 16`
— WP §12 item 1 marks these **proposed, to be confirmed empirically** at the first proof run.
Also T = 64 is the **2×2** value; the 4×4 value is 150 cycles, and the SRS's scope covers both
builds.

**Replace with:** "Baseline proof configuration (proposed, per WP §12 item 1 — to be confirmed
at the first proof run): BMC K = 64, k-induction k = 16, bounded liveness T = 64 cycles (2×2
formal) / 150 cycles (4×4 simulation)."

### M6 — five malformed tables (genuine duplicate rows, not merged cells)

Verified in the XML: no `vMerge` is present, so these are real duplicated rows.

| Table | Defect | Fix |
|---|---|---|
| §2.2 target table | a stray `Target \| FPGA` row above the real row | one row: `Target \| FPGA — 2×2 committed build (4 tile positions); 4×4 for simulation` |
| §2.2 design language | the row is duplicated | delete one row |
| §2.2 verification methodology | the row is duplicated | delete one row |
| §9.2 board/device | `Board / device \| FPGA` and `Board / device \| FPGA 2x2 build` — two values, one key | one row, with the board named |
| §9.2 toolchain | `Toolchain \| Synthesis / implementation / bitstream tools` and `Toolchain \| Vivado / synthesis` — conflicting values | one row: `Toolchain \| Vivado (synthesis, implementation, bitstream)` |

---

## Minor

| ID | Location | Issue | Fix |
|---|---|---|---|
| N1 | §1.2 | "four virtual buffers per port" — a *buffer* is physical storage; the WP specifies 4 **VCs** per port, each with a 4-flit FIFO | "four virtual channels per port, each with a 4-flit FIFO" |
| N2 | §8.2 | "Directed tests 1-22" folds the 5 DMA tests into the core range, though 18–22 are conditional on the Week-8 gate | "directed tests 1–17, plus 18–22 conditional on the DMA gate" |
| N3 | throughout | placeholders remain: `[Group number / name]`, `[Member 1..4]`, `[Name]`, and an empty `[Context diagram]` | fill the group metadata and embed the 2×2 context diagram from the WP's rendered HTML |
| N4 | §4 | PERF-03 "Latency: TBD" although the WP fixes several latency-relevant figures: 4-cycle hop latency, 9 flits per 512-bit line, 64 B lines, T = 64, 13-round fairness | state those figures as the latency requirements; leave only clock frequency and throughput as TBD |
| N5 | §5 | Power is entirely TBD and the WP contains no power data — a silent gap that will surface at review | either mark §5 explicitly out of scope for this milestone, or add "power budget" to the WP §12 open-items list |
| N6 | §8.5 | "no open critical bugs" is looser than the WP §5.4 criterion | "100 % of the 42 bound SVA and I1–I7 pass with **zero waivers**; all directed tests pass; coverage targets met; lint and CDC clean" |

---

## Package-level finding (outside the SRS, but it must be fixed with it)

The WP's §13 adjudication ledger is labelled sequentially — **A, B, … Z, AA, AB, AC** (29 rows).
The B4 row added in the last round is labelled **B4**, which is a *different* naming scheme inside
that series and sits directly next to the existing row labelled **B** ("DIR_FWD_WAIT successor
ambiguity"). A reader looking up "B" and "B4" in the same table gets two unrelated rulings.

**Fix:** relabel the appended row **AD** (the next free label in the A…Z, AA, AA, AB, AC series —
confirm by counting: the ledger currently ends at AC) and use the same convention for the two
rulings still missing from it. The **B1 (fairness bound)** and **B2 (conflict eviction)** rulings
are referenced by WP §12 item 8 and by rule 10, but have **no ledger row at all** — add them as
**AE** and **AF**.

The SRS's `B1`/`B2`/`B4` citations in the "Verified by" column become resolvable once the
ledger actually carries those rows — but they still belong in a *ruling* column, not a
"verified by" column.

---

## Acceptance checklist for the next draft

- [ ] §1.3 — PUTS/PUTM/UNBLOCK directions corrected
- [ ] §2.2 / §9.2 — five duplicate rows removed or merged; toolchain value unambiguous
- [ ] §2.3 AC-03 — VC index order stated as VC0 REQ / VC1 FWD / VC2 RESP / VC3 INV
- [ ] §3 — FR-02 no longer cites A13; FR-09…FR-14 added; every "Verified by" is a resolvable assertion/test ID
- [ ] §6 / §9.3 — area targets are the design targets (≤20k LUT, ≤48 BRAM36, 0 DSP), not device capacity
- [ ] §7.1 — all 12 core + 2 gated messages listed with direction/class/VC
- [ ] §7.2 — signal list rebuilt; no DMA signal in the 2×2 build
- [ ] §8.1 — proof parameters marked proposed; T split by configuration
- [ ] §8.3 — the four numeric §5.4 coverage criteria
- [ ] §8.4 / §9.5 — test plans mapped to the WP's 17 (+5 conditional) directed tests
- [ ] §10 — all eight (soon fourteen) FRs traced
- [ ] WP §13 — the B4 row relabelled **AD** (the ledger series is A…Z, AA, AB, AC); B1 and B2 added as **AE** / **AF**
- [ ] `python3 verify_patch_set.py --dir . --build-script build_diagrams_html.py` → 130/130, exit 0
