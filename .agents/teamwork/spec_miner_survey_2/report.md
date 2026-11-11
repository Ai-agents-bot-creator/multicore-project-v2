# Specification Mining Report: Formal SVA, BMC K=64, Protocol Rulings B1/B2/B4, Tech Stack & Mutation Testing

**Agent:** `spec_miner_survey_2`  
**Date:** 2026-11-05  
**Clean-Room Status:** Verified clean-room compliant. No test source code in `tb/self_test/`, `tb/l1_dir/`, or scratch directories was accessed. All findings are derived exclusively from authorized specification files (`ORIGINAL_REQUEST.md`, `FINAL_whitepaper_v3.0.md`, `RULINGS_B1_B2_B4.md`, `docs/01_DECISION_LOG.md`, `docs/04_TECH_STACK.md`, `docs/06_VERIFICATION_PLAN.md`, `docs/09_VERIFICATION_PROVES.md`, `BUILD_ORDER.md`, `SLICE_16_1.md`, `WORK_BREAKDOWN_16.md`, and `rtl/pkg/tile_pkg.sv`).

---

## Executive Summary

This report establishes the authoritative verification specifications for clean-room independent acceptance testing of the multi-core cache hierarchy RTL. It provides comprehensive formal definitions and invariants for SystemVerilog Assertions (SVA) categories A1.1, A1.2, A1.3, A2.2, A2.6, A3.1, and A7.x; details the SymbiYosys (`sby`) Bounded Model Checking (BMC) environment at depth $K=64$; explains architectural rulings B1, B2, and B4 and their normative RTL/TB constraints; defines the pinned toolchain constraints (cocotb 2.1.0, iverilog 13.0, python environment, sby options); and constructs a specification-derived mutation testing suite with positive and dual negative controls (`positive | neg1 | neg2 | expected vs actual`).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | SVA Invariant | **A1.1 (SWMR / Single Writer)** | At most one L1 cache may hold a cache line in state `M` across all tiles at any time. | Line address $A$, all L1 tag/state arrays | SVA assertion pass/fail | Assertion failure if $\sum_{i} (L1[i].\text{state}[A] == M) > 1$ | `FINAL_whitepaper_v3.0.md` §5.2; `docs/09_VERIFICATION_PROVES.md` §2 |
| 2 | SVA Invariant | **A1.2 (Exclusive Exclusivity)** | At most one L1 cache may hold line $A$ in state `E` or `M`. | Line address $A$, all L1 tag/state arrays | SVA assertion pass/fail | Assertion failure if $\sum_{i} (L1[i].\text{state}[A] \in \{E, M\}) > 1$ | `FINAL_whitepaper_v3.0.md` §5.2; `docs/09_VERIFICATION_PROVES.md` §2 |
| 3 | SVA Invariant | **A1.3 (Shared Validity / No E/M alongside S)** | If any tile holds line $A$ in state `S`, no tile holds line $A$ in state `E` or `M`. | Line address $A$, all L1 tag/state arrays | SVA assertion pass/fail | Assertion failure if $(\exists i: L1[i]=S) \land (\exists j: L1[j] \in \{E,M\})$ | `FINAL_whitepaper_v3.0.md` §5.2, §3.3 rule 9 |
| 4 | SVA Invariant | **A2.2 (Directory Sharer Accuracy)** | When directory state is `DIR_S`, the `Sharers` bitmask matches the exact set of tiles holding line $A$ in `S`. | Line address $A$, directory entry, all L1 states | SVA assertion pass/fail | Assertion failure if stale sharer bit exists or sharer bit missing | `FINAL_whitepaper_v3.0.md` §5.2, §3.3 rule 2 |
| 5 | SVA Invariant | **A2.6 (Directory Owner In Sharers)** | When directory state is `DIR_E` or `DIR_M`, `Owner < TILE_COUNT` and `Sharers == {Owner}`. | Line address $A$, directory state, owner, sharer mask | SVA assertion pass/fail | Assertion failure if `Owner >= TILE_COUNT` or `Sharers != (1 << Owner)` | `FINAL_whitepaper_v3.0.md` §5.2, §16.1 |
| 6 | SVA Invariant | **A3.1 (Virtual Channel Preservation)** | VC ID assigned at source NIC from message class is strictly preserved across all router hops; no router may rewrite VC. | Flit header `hdr.vc` [43:42] across router ports | Router flit output `hdr.vc` | Assertion failure if egress VC != ingress VC | `FINAL_whitepaper_v3.0.md` §3.5, §4.6, §5.2, App E; `docs/09_VERIFICATION_PROVES.md` §2 |
| 7 | SVA Invariant | **A7.x (FSM Legality & Single-Exit)** | Every $(state, event)$ pair in L1/Directory FSM is defined; transient states (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`) exit strictly on `UNBLOCK` (VC2). | FSM current state, received message / internal event | Next state, output actions | Assertion failure on undefined transition, illegal state, or intermediate exit | `FINAL_whitepaper_v3.0.md` §3.3, §3.7, §5.2, §16.1, App A/B |
| 8 | Formal BMC | **BMC Depth K=64 with SymbiYosys** | Bounded model checking on 2×2 mesh up to $K=64$ cycles (matching derived maximum transaction round trip $T=64$). | Synchronous 100 MHz clock, active-low reset, formal constraints | Proof trace / counter-example | SBY returns `FAIL` with trace if safety property violated within 64 cycles | `FINAL_whitepaper_v3.0.md` §5.3, §12 #1; `docs/04_TECH_STACK.md` |
| 9 | Protocol Ruling | **Ruling B1 (Fairness Bound Composition)** | Router fairness bound is derived as $5 \text{ (age escape)} + 3 \text{ (sibling VCs)} + 5 \text{ (input ports)} = 13$ cycles (11 at corner); output arbiter is port-granular. | Flits at router VC FIFOs, per-(port, VC) 3-bit age counter | Port grants, switch traversals | Starvation / priority inversion exceeding 13 rounds violates Premise F | `RULINGS_B1_B2_B4.md` §B1; `FINAL_whitepaper_v3.0.md` §3.5 |
| 10 | Protocol Ruling | **Ruling B2 (Conflict Eviction Prioritization)** | Conflict eviction is not deferred: PLRU victim is released before issuing miss request on VC0; sub-step of miss transient; no second transient; no MSHRs. | Cache set full on load/store miss, dirty/clean victim | `PUTM` (9 flits) or `PUTS` (1 flit) on VC0 before `GETS`/`GETM` | Set-full deadlock if eviction deferred behind miss | `RULINGS_B1_B2_B4.md` §B2; `FINAL_whitepaper_v3.0.md` §3.3 rule 10 |
| 11 | Protocol Ruling | **Ruling B4 (DMA 4×4 Simulation Only)** | Committed 2×2 FPGA build has 4 CPU tiles and 0 DMA tiles; DMA is 4×4 sim-only Week-8 gated; DMA opcodes 1100–1101 reserved in 2×2. | Top-level configuration, message type decode | System tile instantiation, DTR pending op | Elaboration error / A8.4 failure if DMA enabled or injected in 2×2 | `RULINGS_B1_B2_B4.md` §B4; `FINAL_whitepaper_v3.0.md` §3.11 |
| 12 | Tech Stack | **cocotb 2.1.0 Pinning & LogicArray Semantics** | cocotb pinned to 2.1.0 with iverilog 13.0; signal values return `LogicArray` (not integer); requires explicit `int(dut.sig.value)`. | Python test harness, cocotb triggers | Simulation values, checks | TypeError or subtle boolean comparison bugs if compared directly as integers | `docs/01_DECISION_LOG.md` (R4); `docs/04_TECH_STACK.md` |
| 13 | Tech Stack | **cocotb NBA Region Settlement** | Clocked tests require `await Timer(1, unit="ps")` after `RisingEdge(clk)` to observe non-blocking assignment (NBA) register updates. | Clock edge trigger, register probe | Settled signal values | Stale pre-edge register values observed if sampled without delta-cycle settle | `docs/AI_SCRATCHPAD.md` lines 347–370 |
| 14 | Mutation Testing | **Non-Vacuous Mutation Qualification** | Every acceptance test must prove non-vacuousness via dual negative controls (`neg1`, `neg2`) and discrimination against zero-emitting stubs. | Injected protocol and data faults | Test PASS/FAIL matrix matching expectation | Tests passing against dummy/unimplemented stubs are flagged as vacuous | `ORIGINAL_REQUEST.md` R2/R3; `docs/06_VERIFICATION_PLAN.md` §5 |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | A1.3 / Rule 9 | `GETS` forward completed with corrupted `DATA(excl=1)` instead of `excl=0`. | Requester installs line in `E` while old owner downgraded to `S`; two tiles hold line concurrently in `S` and `E`, triggering immediate violation of A1.3 and A2.6. |
| 2 | A1.1 / Rule 8 | Old owner fails to downgrade to `I` on `FWD_GETM`, remaining in `M`. | Two tiles simultaneously hold line in `M` once requester completes install, causing immediate violation of A1.1. |
| 3 | A2.2 / Rule 2 | L1 silently evicts clean line in state `S` without dispatching `PUTS`. | Stale sharer bit remains in directory; directory `DIR_S` sharer mask deviates from actual sharer set, violating A2.2; subsequent `GETM` will deadlock in `DIR_INV_WAIT` waiting for phantom sharer. |
| 4 | A2.6 / DTR | On `FWD_GETM`, directory commits `DIR_M` on `UNBLOCK` but fails to update `Owner = requester`. | Directory holds old owner in `Owner` field while sharer bit was updated, violating A2.6 (`Owner ∈ Sharers` and `Sharers == {Owner}`). |
| 5 | A7.x / Single-Exit | Directory in `DIR_FWD_WAIT` receives intermediate `DATAFWD` flit. | DTR stores data and updates pending status, but SRAM directory state MUST remain `DIR_FWD_WAIT`; premature transition to `DIR_S` or `DIR_M` before `UNBLOCK` violates A7.x single-exit rule. |
| 6 | Ruling B1 | 4 VCs contend at input port with age counters $[5, 3, 5, 2]$ under equal fixed priority. | VC arbiter must grant oldest counter ($5$); between the two tied counters of value $5$, tie is broken by fixed class priority (RESP > INV > FWD > REQ). If arbiter ignores age counter, lower-priority VC starves. |
| 7 | Ruling B2 | Set full; miss on line $B$ requires eviction of dirty victim $A$ in state `M`. | L1 stays in `IS_D`/`IM_D`; issues `PUTM(A)` on VC0; waits for `PUTACK(A)`; only upon `PUTACK` receipt issues `GETS(B)`/`GETM(B)` on VC0. If miss request is sent concurrently or before `PUTACK`, home bank deadlocks. |
| 8 | Ruling B2 / N12 | While victim $A$ release (`PUTM`) is in flight, directory forwards `FWD_GETS(A)` to tile. | L1 in `IS_D`/`IM_D` detects victim release is already in flight and answers with defensive `INVACK` (VC2); directory absorbs `INVACK` and `PUTM` in `DIR_FWD_WAIT` without opening orphan transient. |
| 9 | Ruling B4 | Stimulus injects `DMA_WRITE` (opcode `1100`) or targets home tile $\ge 4$ on 2×2 mesh. | Header decode triggers assertion failure (A8.4); opcode rejected as reserved; 2×2 DTR treats opcode `100` (`POP_DMA`) as unreachable. |
| 10 | cocotb 2.1.0 | Testbench asserts `if dut.q.value == 1:` without casting to `int()`. | Comparison evaluates to `False` even when signal is binary 1 because `LogicArray` object does not equal integer `1`. Must use `int(dut.q.value) == 1`. |

---

## 1. SystemVerilog Assertions Requirements

The specification defines **42 bound SystemVerilog Assertions (SVA)** non-invasively bound to the RTL via `bind`, partitioned into 8 orthogonal categories (A1–A8), plus 7 formal-only network invariants (I1–I7). The specific assertions assigned for exhaustive specification mining are detailed below:

### 1.1 A1.1 — Single-Writer Multiple-Reader (SWMR) Invariant
- **Normative Clauses:** `FINAL_whitepaper_v3.0.md` §3.3, §4.6, §5.2 (Table line 626), §16.1; `docs/09_VERIFICATION_PROVES.md` §2 line 21.
- **Target Module & Scope:** `l1_mesi_ctrl.sv` / `tile.sv`, scoped across all L1 cache arrays for every valid cache line.
- **Formal Definition:**
  $$\forall \text{line address } A, \quad \left( \sum_{i=0}^{\text{TILE\_COUNT}-1} \mathbb{I}(L1[i].\text{state}[A] == \text{L1\_M}) \right) \le 1$$
  Equivalently: If tile $T_i$ holds line $A$ in state `M`, then $\forall j \neq i$, tile $T_j$ holds state `I`:
  $$(L1[i].\text{state}[A] == \text{L1\_M}) \implies \left( \forall j \neq i, \; L1[j].\text{state}[A] == \text{L1\_I} \right)$$
- **Expected Invariant:** At most one L1 cache in the entire system may hold line $A$ in Modified (`M`) state at any clock cycle.
- **RTL & Protocol Dependencies:** Kept true by the directory serialization, invalidations to all sharers on `GETM`, owner downgrade to `I` on `FWD_GETM`, and exclusive-bit control.

### 1.2 A1.2 — Exclusive Exclusivity
- **Normative Clauses:** `FINAL_whitepaper_v3.0.md` §5.2 line 626; `docs/09_VERIFICATION_PROVES.md` §2 line 22; `docs/AI_SCRATCHPAD.md` line 179.
- **Target Module & Scope:** All L1 cache controllers across the mesh.
- **Formal Definition:**
  $$\forall \text{line address } A, \quad \left( \sum_{i=0}^{\text{TILE\_COUNT}-1} \mathbb{I}(L1[i].\text{state}[A] \in \{\text{L1\_E}, \text{L1\_M}\}) \right) \le 1$$
- **Expected Invariant:** At most one tile may hold line $A$ in state `E` or `M`. No two tiles may hold exclusive ownership or modified ownership simultaneously.
- **Failure Mode Guarded:** Catches erroneous generation of the DATA exclusive bit (`excl=1`) by `dir_ctrl` when another copy is already held.

### 1.3 A1.3 — Shared Validity (No E or M alongside S)
- **Normative Clauses:** `FINAL_whitepaper_v3.0.md` §3.3 rule 9, §5.2 line 627, §16.1, §16.2; `docs/09_VERIFICATION_PROVES.md` §2 line 23.
- **Target Module & Scope:** All L1 cache arrays.
- **Formal Definition:**
  $$\forall \text{line address } A, \quad \left( \exists i : L1[i].\text{state}[A] == \text{L1\_S} \right) \implies \left( \forall j : L1[j].\text{state}[A] \notin \{\text{L1\_E}, \text{L1\_M}\} \right)$$
- **Expected Invariant:** The presence of any Shared (`S`) copy strictly forbids the existence of any Exclusive (`E`) or Modified (`M`) copy for that cache line anywhere in the system.
- **Protocol Mechanism:** When an owner in `E` or `M` receives `FWD_GETS`, it must downgrade to `S`. If the downgrade fails, or if the directory issues `DATA(excl=1)` to the requester while the old owner remains in `S`, A1.3 is violated immediately.

### 1.4 A2.2 — Directory Sharer Accuracy
- **Normative Clauses:** `FINAL_whitepaper_v3.0.md` §3.3 rule 2, §5.2 line 631, §16.1; `docs/09_VERIFICATION_PROVES.md` §2 line 27–28.
- **Target Module & Scope:** `dir_ctrl.sv` / directory tag and state array.
- **Formal Definition:**
  $$\forall \text{line address } A \text{ mapped to home bank } H, \quad (\text{dir}[A].\text{state} == \text{DIR\_S}) \implies \forall k \in [0, \text{TILE\_COUNT}-1], \; \left( \text{dir}[A].\text{sharers}[k] == 1 \iff L1[k].\text{state}[A] == \text{L1\_S} \right)$$
- **Expected Invariant:** In `DIR_S`, the directory `Sharers` bitmask must precisely equal the set of L1 caches currently holding line $A$ in state `S`. There can be neither stale sharer bits (due to silent eviction) nor missing sharer bits (due to untracked grants).
- **Consequence of Violation:** Stale sharer bits cause `DIR_INV_WAIT` to hang forever during store upgrades, causing system deadlock.

### 1.5 A2.6 — Directory Owner Qualification and Alignment
- **Normative Clauses:** `FINAL_whitepaper_v3.0.md` §3.2, §5.2 line 635, §16.1, §16.2; `RULINGS_B1_B2_B4.md` line 8.
- **Target Module & Scope:** `dir_ctrl.sv` (directory state, owner register, sharer vector).
- **Formal Definition:**
  $$\forall \text{line address } A, \quad (\text{dir}[A].\text{state} \in \{\text{DIR\_E}, \text{DIR\_M}\}) \implies \left( \text{dir}[A].\text{owner} < \text{TILE\_COUNT} \;\land\; \text{dir}[A].\text{sharers} == (1 \ll \text{dir}[A].\text{owner}) \right)$$
- **Expected Invariant:** Whenever directory state is `DIR_E` or `DIR_M`, `Owner` must be a valid tile ID ($< 4$ on 2×2), and `Sharers` must be the singleton mask containing exactly the `Owner`. In all other directory states (`DIR_I`, `DIR_S`), `Owner` is ignored and must never be read by RTL.

### 1.6 A3.1 — Virtual Channel Preservation and Invariance
- **Normative Clauses:** `FINAL_whitepaper_v3.0.md` §3.5, §4.6 (Layer 1), §5.2 line 637, Appendix E line 1116; `docs/09_VERIFICATION_PROVES.md` §2 line 32.
- **Target Module & Scope:** `nic.sv` and `router.sv` across all network ports.
- **Formal Definition:**
  $$\forall \text{flit } F \text{ injected at source NIC with } \text{VC} = \text{class}(F.\text{msg}), \quad \forall \text{router hops } h, \; F.\text{hdr.vc} == \text{assigned\_VC}$$
- **Expected Invariant:** The virtual channel ID (`hdr.vc`, bits [43:42]) assigned at the source NIC is immutable throughout the packet's traversal of the mesh. No router may re-encode, remap, or modify the VC field.
- **Deadlock Guarantee Role:** This invariant ensures physical channel disjointness across the 4 VCs, which is the foundational premise for Layer 1 acyclic routing in §4.6.

### 1.7 A7.x — State Machine Legality, Determinism & Single-Exit
- **Normative Clauses:** `FINAL_whitepaper_v3.0.md` §3.3 (single-exit rule), §3.7 (DTR), §5.2 line 640, §16.1, Appendix A, Appendix B; `RULINGS_B1_B2_B4.md` §B2 (P-B2.4).
- **Target Module & Scope:** `l1_mesi_ctrl.sv` and `dir_ctrl.sv`.
- **Composition (4 Assertions):**
  1. **A7.1 (Complete Transition Legality):** Every legal $(state, event)$ pair in L1 (9 states × 14 messages/events) and Directory (8 states × 14 messages/events) maps to a strictly defined next state. Undefined transitions trigger an immediate illegal state assertion.
  2. **A7.2 (Directory Single-Exit Rule):** Transient directory states (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`) exit strictly and exclusively upon receipt of `UNBLOCK` (VC2). Intermediate events (`MEM_DATA`, `DATAFWD`, `INVACK`, `PUTM`, `PUTS`) advance DTR sub-state and counters only, and NEVER modify the directory SRAM state directly.
  3. **A7.3 (Successor Selection Determinism):** On `UNBLOCK` exit from `DIR_FWD_WAIT`, `DTR.pending_op` deterministically selects the successor state: `POP_GETS` $\implies$ `DIR_S`; `POP_GETM` $\implies$ `DIR_M`.
  4. **A7.4 (Transient Confinement & Sub-Step Ordering):** Conflict eviction executes as an internal sub-step of `IS_D`/`IM_D` without opening a secondary transient; `DIR_EVICT` is entered solely from `DIR_MEM_WAIT` and exits solely back to `DIR_MEM_WAIT` upon commit.

---

## 2. Formal Bounded Model Checking (BMC) at Depth K=64 with SymbiYosys

### 2.1 Configuration and Scope
- **Evaluation Configuration:** 2×2 mesh (4 tiles: Tile 0=(0,0), Tile 1=(0,1), Tile 2=(1,0), Tile 3=(1,1)).
- **Minimum Model Justification:** A 4-tile model is the mathematical minimum required to exercise:
  - Multi-sharer invalidation fan-out (2 sharers + 1 requester).
  - Two distinct home tiles and 2-bit home tile decode.
  - Concurrent forward and invalidation interleavings.
- **Coverage Boundary (Disclosed):** Interior 5-port router (requires $\ge 9$ tiles) and $\ge 3$ sharers with distinct homes simultaneously (requires $\ge 5$ tiles) cannot be covered on 2×2 and are deferred to 4×4 simulation.

### 2.2 Derivation of Bounded Depth K=64
- **Longest Coherence Transaction:**
  $$\text{GETM (VC0)} \longrightarrow \text{INV (VC3)} \longrightarrow \text{INVACK (VC2)} \longrightarrow \text{DATA (VC2)} \longrightarrow \text{UNBLOCK (VC2)}$$
  This sequence requires **5 full fabric traversals**.
- **Latency Breakdown on 2×2 Mesh:**
  - Worst-case Manhattan distance on 2×2: $2 \text{ hops}$.
  - Router pipeline depth: $4 \text{ stages (RC/VA/SA/ST)} = 4 \text{ cycles/hop}$.
  - Fabric traversal latency: $5 \text{ traversals} \times 2 \text{ hops} \times 4 \text{ cycles/hop} = 40 \text{ cycles}$.
  - Local controller, NIC serialization/deserialization, and memory-tap overhead: $\le 24 \text{ cycles}$.
  - Worst-case round-trip bound: $T = 40 + 24 = 64 \text{ cycles}$.
- **Soundness Requirement:** Any BMC depth $K < T = 64$ is mathematically unsound: a full remote coherence transaction could not complete within the bounded execution window, causing bounded liveness and completion properties to pass vacuously. Depth $K = 64$ guarantees complete transaction observability.

### 2.3 Solvers and Execution Modes
- **Tool:** SymbiYosys (`sby`).
- **Engines:**
  - Primary SMT solvers: Boolector (`smtbmc boolector` / `bitwuzla`) and Z3 (`smtbmc z3`).
  - Yices2 (`smtbmc yices`) for fast invariant induction.
- **Operating Modes:**
  - `mode bmc`, `depth 64`: Discharges the 38 bound safety assertions (A1, A2, A3, A4, A6, A7, A8) and formal network invariants I1–I7.
  - `mode prove` (k-induction), `depth 16`: Discharges the structural deadlock freedom lemma premises (Layer 1 XY routing, Layer 2 inter-class edge ascent, Layer 3 credit bounds).

### 2.4 Clocks, Resets, and Formal Assumptions
- **Clock:** Single synchronous 100 MHz clock domain across all 4 tiles.
- **Reset Sequence:** Active-low reset `rst_n`. In formal harnesses:
  - Cycle 0: `assume(!rst_n);`
  - Cycle $\ge 1$: `assume(rst_n);`
  - Past valid guards: All `$past()` checks gated by `!$initstate && rst_n`.
- **Environment Assumptions (`assume`):**
  - Core stimulus generates well-formed addresses within 32-bit address space.
  - Premise R (Receptivity): L1 network sinks do not indefinitely stall responses.
  - Credits initialised to FIFO depth ($4$) and link credit inputs bounded in $[0, 4]$.
  - Static `TILE_ID` inputs hardwired per tile ($0, 1, 2, 3$).

---

## 3. Architectural Protocol Rulings B1, B2, B4

### 3.1 Ruling B1 — Fairness Bound Composition: $13 = 5 + 3 + 5$
- **Exact Ruling Text:**
  - A round is exactly one router clock cycle. All arbiters (input-port VC arbiter, output-port switch arbiter) arbitrate once per cycle; all counters advance once per round.
  - Age-escape threshold is confirmed at **5 rounds** (replaces the unconfirmed working value of 8).
  - Derived end-to-end bound:
    $$5 \text{ (age escape)} + 3 \text{ (sibling VCs at input port)} + 5 \text{ (input ports at switch)} = 13 \text{ switch-arbitration rounds}$$
  - Corner tile bound: Only 3 ports active $\implies 5 + 3 + 3 = 11 \text{ rounds}$. (Reconciles the specification's published corner bound of 11: $8 + 3 + 3 = 14 \ne 11$, whereas $5 + 3 + 3 = 11 \checkmark$).
  - **Output switch arbiter is PORT-GRANULAR, NOT VC-AWARE:** Round-robin across input ports ($\le 5$), never across input-port $\times$ VC pairs ($20$ candidates). A VC-aware arbiter would yield $5 + 3 + 20 = 28$ rounds, voiding the bound.
  - Oldest counter wins the age escape; ties are broken by fixed class priority ($\text{RESP} > \text{INV} > \text{FWD} > \text{REQ}$).
- **RTL Implementation Constraints:**
  - Age counter: 3 bits per (input port, VC), saturating at 5 (`AGE_THRESH = 5`).
  - Input-port VC arbiter requires a 4-input priority comparator across 3-bit values.
  - Switch arbiter must arbitrate strictly among input ports.
- **Verification Constraints:** Verifier checks K1–K5; formal BMC proves flit latency $\le 13$ cycles under Premise F.

### 3.2 Ruling B2 — Conflict Eviction Concurrent with Outstanding Miss
- **Exact Ruling Text:**
  - Rule 10 is partitioned into two mutually exclusive cases:
    1. **Proactive Eviction:** Tile-initiated release or recall. DEFERRED while a miss is outstanding.
    2. **Conflict Eviction:** The victim way replacement required by the pending miss itself when the cache set is full. **NOT DEFERRED.**
  - **Pre-Release Mechanism:** The L1 releases the PLRU victim **BEFORE** dispatching the miss request:
    - Dirty victim in `M`: Send `PUTM` (VC0, 9 flits) $\to$ wait for `PUTACK`.
    - Clean victim in `S` or `E`: Send `PUTS` (VC0, 1 flit); `E` waits for `PUTACK`, `S` does not wait.
  - **Single Transient Invariant:** Victim release is an internal sub-step of the miss transient. L1 stays in `IS_D` or `IM_D`. No second transient is opened. `MI_A`/`EI_A` are reserved for proactive evictions. **One transient per tile holds; NO MSHRs.**
  - **Deadlock Removal via VC0 Ordering:** Both release (`PUTM`/`PUTS`) and miss (`GETS`/`GETM`) travel on **VC0 (REQ)**. Per-VC FIFO order (I4) guarantees the home bank receives and completes the victim write-back before processing the miss request.
  - **Evict-During-Forward Race (N12):** If a `FWD` arrives for the victim while in flight, L1 replies with defensive `INVACK` (VC2); directory's `DIR_FWD_WAIT` absorbs both `INVACK` and `PUTM`.
- **RTL & TB Constraints:** L1 miss logic must gate miss issue until victim release completes; reference model must implement shadow rule 11.

### 3.3 Ruling B4 — DMA Scope: 2×2 Build Has No DMA Tile
- **Exact Ruling Text:**
  - The committed 2×2 FPGA build contains **4 CPU tiles, 0 DMA tiles, 0 DMA home codes, and no DMA sharer arithmetic**.
  - The DMA track is a **4×4 simulation-only study**, gated on the Week-8 gate. It never enters the 2×2 build.
  - The committed 2×2 mesh has exactly 4 tile positions ($2\times 2$). Adding a DMA tile would create an irregular 5-tile topology, breaking the BRAM/LUT budget and address map.
  - In 2×2 RTL:
    - DTR `pending_op = POP_DMA` (code `100`) is reserved and **strictly unreachable**.
    - Enabling DMA in a 2×2 build must trigger an elaboration/configuration assertion.
    - Message codes `1100` (`DMA_WRITE`) and `1101` (`DMA_ACK`) remain Reserved.
- **Verification Constraints:** Verifier check K8 guards 4×4-only DMA scope; acceptance test suite for 2×2 does not include DMA stimulus.

---

## 4. Toolchain and Tech Stack Versions & Requirements

| Component | Pinned Version / Setting | Critical Operational Requirements & Constraints |
|---|---|---|
| **cocotb** | **2.1.0 (pinned)** | 1. **LogicArray Semantics:** `dut.<sig>.value` returns a `LogicArray`, not an integer. Must cast: `int(dut.<sig>.value) == expected`.<br>2. **NBA Settle Timing:** Clocked tests must execute `await Timer(1, unit="ps")` after `RisingEdge(clk)` before sampling registered outputs.<br>3. **Timer Syntax:** Use `unit="ps"` or `unit="ns"`. Avoid deprecated `units=`.<br>4. **Removed Modules:** `cocotb.binary` is removed in 2.x; use standard bitwise/LogicArray operations. |
| **Icarus Verilog** | **13.0 (stable, v13_0)** | 1. Used as primary cocotb backend (`SIM=iverilog`).<br>2. Flags: `-g2012` for SystemVerilog-2012 support.<br>3. Must compile `tile_pkg.sv` before modules that import it. |
| **Python** | **Python 3.14 / Pinned Env** | Installed via `pipx` to comply with PEP 668 externally managed environment rules. PyUVM utilized for TLM reference models. |
| **SymbiYosys (`sby`)** | **Pinned / YosysHQ** | 1. `.sby` configuration must specify `[options]` (`mode bmc`, `depth 64`).<br>2. `[engines]` must target `smtbmc boolector` or `smtbmc z3`.<br>3. Non-invasive SVA binding via `bind` in SystemVerilog. |
| **Verilator** | **Verilator 5.x** | **Linting only** (`verilator --lint-only -Wall`). Strictly not used for cocotb simulation execution. |

---

## 5. Mutation Testing Requirements

### 5.1 Methodology and Non-Vacuousness Proof
Acceptance testing requires independent mutation testing derived directly from normative specification rules. The purpose of mutation testing is to prove that the test suite is **discriminating and non-vacuous** — ensuring tests fail when a fault is present and pass only when the protocol is faithfully implemented, eliminating false-positive passes against dead or zero-emitting stubs.

### 5.2 Control Architecture
Every mutation test evaluates three distinct stimulus/response paths:
1. **Positive Test:** Exercises the compliant protocol flow under normal operating conditions. (Must PASS on compliant RTL; FAILS against stub).
2. **Negative Control 1 (`neg1`):** Injects a structural or protocol fault (e.g. omitted message, dropped acknowledge, or skipped downgrade). Must be caught by assertion or check.
3. **Negative Control 2 (`neg2`):** Injects a data integrity or control-bit fault (e.g. corrupted dirty bit, inverted exclusive bit, or wrong VC). Must be caught by assertion or check.

### 5.3 Specification-Derived Mutation Matrix

| Mutation ID | Target Spec Clause | Injected Fault Description | Positive Control | Negative Control 1 (`neg1`) | Negative Control 2 (`neg2`) | Expected vs Actual Outcome |
|---|---|---|---|---|---|---|
| **MUT-1 (Exclusive Bit)** | §3.3 Rule 9; §16.2; A1.3; A2.6 | Directory grants `excl=1` on `GETS` forward grant (or grants `excl=0` on sole-holder clean fill). | Forward GETS grants `excl=0`; installs `S`. | Shared forward returns `excl=1`; installs `E` alongside existing `S`. | Sole-holder DIR_I grant returns `excl=0`; installs `S` instead of `E`. | Expected: Positive PASS, neg1 FAIL (A1.3/A2.6 fires), neg2 FAIL (silent upgrade fails). |
| **MUT-2 (Forward Downgrade)** | §3.3 Rule 8; §16.1; A1.1; A1.3 | Old owner suppresses state downgrade on `FWD_GETS` (stays in `M`/`E`) or on `FWD_GETM` (stays in `M`). | Owner downgrades $M \to S$ on `FWD_GETS` and sends `DATAFWD`. | Owner stays in $M$ on `FWD_GETS`. | Owner stays in $M$ on `FWD_GETM`. | Expected: Positive PASS, neg1 FAIL (A1.3 fires), neg2 FAIL (A1.1 two writers fires). |
| **MUT-3 (Silent Eviction)** | §3.3 Rule 2; §16.1; A2.2 | L1 drops clean `S` or `E` line silently without dispatching `PUTS`. | Clean eviction sends `PUTS`; directory clears sharer bit. | Silent drop from $S$; directory retains stale bit. | Subsequent store miss to same line wedges in `DIR_INV_WAIT`. | Expected: Positive PASS, neg1 FAIL (A2.2 fires), neg2 FAIL (timeout $T > 64$). |
| **MUT-4 (Fairness / Age Escape)** | Ruling B1; Premise F; A5.1 | Age-escape counter disabled or switch arbiter made VC-aware. | High REQ traffic served within 13 cycles via age escape. | Age counter tied to 0; heavy RESP/INV traffic starves REQ $> 13$ cycles. | Switch arbiter set to 20-candidate VC-aware round-robin. | Expected: Positive PASS, neg1 FAIL (Premise F bound violated), neg2 FAIL (latency $> 13$). |
| **MUT-5 (Conflict Eviction Order)** | Ruling B2; Rule 10; Deadlock | Conflict eviction deferred behind miss request instead of pre-releasing on VC0. | Victim released on VC0 with `PUTM`/`PUTACK` before `GETS` dispatched. | `GETS` dispatched while set full without releasing victim. | `PUTM` and `GETS` dispatched out of order on different VCs. | Expected: Positive PASS, neg1 FAIL (set-full deadlock), neg2 FAIL (home bank out-of-order stall). |
| **MUT-6 (INVACK Idempotence)** | §3.3 Rule 4; §16.1; A2.1 | Directory counts INVACKs with increment counter instead of bitmask clearing. | Bitmask clears exactly the responding sharer bit. | Duplicate/late INVACK double-decrements counter. | Concurrent PUTS and INVACK cause counter underflow. | Expected: Positive PASS, neg1 FAIL (premature `DIR_M` entry), neg2 FAIL (A2.1 mismatch). |
| **MUT-7 (DATAFWD Dirty Bit)** | §3.8 [39]; §16.4; A6.x | Header bit [39] corrupted: cleared when owner dirty ($M$), or set when owner clean ($E$). | Dirty owner sets bit 39; bank dirty bit set to 1. | Dirty owner clears bit 39; bank left clean (dirty data lost on eviction). | Clean owner sets bit 39; bank falsely marked dirty. | Expected: Positive PASS, neg1 FAIL (A6.x data loss), neg2 FAIL (unnecessary write-back). |
| **MUT-8 (2×2 DMA Rejection)** | Ruling B4; §3.11; A8.4 | Stimulus injects `DMA_WRITE` (opcode `1100`) into 2×2 mesh router/directory. | 4 CPU tiles execute standard MESI traffic cleanly. | `DMA_WRITE` injected into 2×2 tile. | Illegal DMA home tile ID addressed. | Expected: Positive PASS, neg1 FAIL (A8.4 configuration assertion fires), neg2 FAIL (router drops packet). |

---

## 6. Synthesis and Traceability Matrix

| Specification Item | Primary Source File & Line | Target Module | Verification Mechanism | Status |
|---|---|---|---|---|
| **A1.1** | `FINAL_whitepaper_v3.0.md` line 626 | `l1_mesi_ctrl.sv` | SVA Simulation + BMC K=64 | Fully Specified |
| **A1.2** | `FINAL_whitepaper_v3.0.md` line 626 | `l1_mesi_ctrl.sv` | SVA Simulation + BMC K=64 | Fully Specified |
| **A1.3** | `FINAL_whitepaper_v3.0.md` line 627 | `l1_mesi_ctrl.sv` | SVA Simulation + BMC K=64 | Fully Specified |
| **A2.2** | `FINAL_whitepaper_v3.0.md` line 631 | `dir_ctrl.sv` | SVA Simulation + BMC K=64 | Fully Specified |
| **A2.6** | `FINAL_whitepaper_v3.0.md` line 635 | `dir_ctrl.sv` | SVA Simulation + BMC K=64 | Fully Specified |
| **A3.1** | `FINAL_whitepaper_v3.0.md` line 637 | `router.sv`, `nic.sv` | SVA Simulation + k-induction ($k=16$) | Fully Specified |
| **A7.x** | `FINAL_whitepaper_v3.0.md` line 640 | `l1_mesi_ctrl.sv`, `dir_ctrl.sv` | SVA Simulation + BMC K=64 | Fully Specified |
| **BMC K=64** | `FINAL_whitepaper_v3.0.md` §5.3 line 669 | 2×2 Mesh Top | SymbiYosys (`sby`) | Fully Specified |
| **Ruling B1** | `RULINGS_B1_B2_B4.md` line 13 | `router.sv` | Router testbench + BMC | Fully Specified |
| **Ruling B2** | `RULINGS_B1_B2_B4.md` line 77 | `l1_mesi_ctrl.sv`, `dir_ctrl.sv` | Directed tests F6, F7 + BMC | Fully Specified |
| **Ruling B4** | `RULINGS_B1_B2_B4.md` line 149 | Top Topologies | Elaboration check + A8.4 | Fully Specified |
| **cocotb 2.1.0** | `docs/04_TECH_STACK.md` line 11 | Acceptance Testbenches | Python Harness / iverilog 13.0 | Pinned & Proven |
| **Mutations** | `ORIGINAL_REQUEST.md` line 37 | `tb_acceptance/mutations/` | Matrix Runner (`run_all.py`) | Fully Specified |

---
