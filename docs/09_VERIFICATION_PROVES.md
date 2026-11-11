# 09 — Verification Proves & Formal Evidence

> **Document Purpose**: Formal verification repository and proof ledger logging discharged SystemVerilog Assertions, inductive safety lemmas, bounded liveness proofs, and testbench simulation traces.  
> **Writing Standard**: Formatted with explicit adherence to ~80% ASD-STE100 (Simplified Technical English) language standards — direct mathematical assertions, standardized verification outcomes, and strict procedural descriptions.

## 1. Formal Verification Strategy

The verification environment combines SystemVerilog Assertions (SVA), bounded model checking (BMC), structural k-induction, and transaction-level reference model validation in Cocotb / PyUVM.

- **Toolchain**: SymbiYosys (sby) with YosysHQ formal solvers (Z3 / Boolector), Icarus Verilog 13.0, and Cocotb 2.1.0.
- **Safety Horizon**: Bounded Model Checking (BMC) with engine depth $K = 64$ clock cycles.
- **Liveness Horizon**: Bounded liveness verified under fairness bound $T = 64$ formal cycles ($T = 150$ simulation cycles).
- **Deadlock Proof**: Three-layer structural lemma (XY acyclic routing + VC separation + request-response acyclic dependency graph) discharged via $k$-induction ($k = 16$).
- **Assertion Corpus**: 42 formal SVA assertions distributed over 8 orthogonal categories (A1–A8).

---

## 2. Invariant & Safety Proofs

### Category A1 — Coherence Invariants (Single-Writer, Multiple-Reader)
- **A1.1 (SWMR Invariant)**: For any memory line address $A$, if tile $T_i$ holds line $A$ in state `M`, then $\forall j \neq i$, tile $T_j$ holds state `I`. Formally proved under BMC $K = 64$.
- **A1.2 (Exclusive Exclusivity)**: At most one tile may hold line $A$ in state `E` or `M`.
- **A1.3 (Shared Validity)**: If tile $T_i$ holds line $A$ in state `S`, then no tile $T_j$ holds line $A$ in state `M` or `E`.
- **A1.4 (Clean Copy Agreement)**: When multiple sharers exist in state `S`, all read copies match the home L2 bank / backing store data.

### Category A2 — Directory State Consistency
- **A2.1 (Sharer Vector Precision)**: The directory sharer bitmask $\text{Sharers}[N^2-1:0]$ precisely matches the set of L1 caches holding state `S` or `E`.
- **A2.2 (Owner Field Alignment)**: When directory state is `DIR_E` or `DIR_M`, `Owner[1:0]` corresponds exactly to the tile holding the cache line.
- **A2.3 (Transient Single-Exit Rule)**: All directory transients (`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT`, `DIR_EVICT`) exit strictly upon receipt of `UNBLOCK` (VC2).

### Category A3 — Virtual Channel & Packet Type Safety
- **A3.1 (VC Preservation)**: Virtual channel ID assigned at the source NIC is strictly preserved across all router hops; no router may re-encode VC.
- **A3.2 (Message-Class VC Invariance)**:
  - $\text{VC0} \implies \{\text{GETS}, \text{GETM}, \text{PUTS}, \text{PUTM}\}$
  - $\text{VC1} \implies \{\text{FWD\_GETS}, \text{FWD\_GETM}\}$
  - $\text{VC2} \implies \{\text{DATA}, \text{DATAFWD}, \text{INVACK}, \text{UNBLOCK}, \text{PUTACK}\}$
  - $\text{VC3} \implies \{\text{INV}\}$
- **A3.3 (Inter-Class Edge Ascent)**: Protocol transaction chains advance monotonically across VCs ($\text{VC0} \to \text{VC1} \to \text{VC2}$ or $\text{VC0} \to \text{VC3} \to \text{VC2}$), preventing cyclic buffer dependencies.

### Category A4 / A5 — Framing and Credit Flow Control
- **A4.1 (Length Integrity)**: Control packets are exactly 1 flit ($\text{LEN}=1$); cache-line data packets are exactly 9 flits ($\text{LEN}=9$).
- **A5.1 (Buffer Occupancy Bound)**: Credit counter in range $[0, 4]$. Counter never underflows below 0 or overflows above FIFO depth 4.

---

## 3. Liveness & Deadlock Freedom

### Layer 1: Routing Deadlock Freedom
- Routing follows dimension-order deterministic $XY$ (X dimension first, then Y dimension).
- The channel dependency graph $\mathcal{D}_{XY}$ contains no cycles: channels are strictly ordered by coordinate monotonic progression.

### Layer 2: Protocol Deadlock Freedom
- Virtual network stratification into 4 physical virtual channels breaks message-dependent dependency loops:
  $$\text{REQ (VC0)} \longrightarrow \text{FWD (VC1)} \longrightarrow \text{RESP (VC2)}$$
  $$\text{REQ (VC0)} \longrightarrow \text{INV (VC3)} \longrightarrow \text{RESP (VC2)}$$
- `RESP` traffic on VC2 terminates unconditionally into L1/L2 sinks with no downstream flit generation that can stall.

### Layer 3: Router Starvation Freedom & Fairness Bound (Ruling B1)
- **Fairness Bound Premise F**:
  Every pending flit is granted within a bounded number of switch arbitration cycles:
  - Interior tile bound: $5 \text{ (age escape)} + 3 \text{ (sibling VCs)} + 5 \text{ (input ports)} = 13 \text{ cycles}$.
  - Corner tile bound: $5 \text{ (age escape)} + 3 \text{ (sibling VCs)} + 3 \text{ (active ports)} = 11 \text{ cycles}$.
- Port-granular output scheduling prevents VC-monopolization.

### Conflict Eviction Liveness (Ruling B2)
- Conflict evictions intrinsic to a miss execute victim release (`PUTM`/`PUTS`) on VC0 *before* the miss request (`GETS`/`GETM`) is enqueued. Per-VC FIFO order at the NIC guarantees serialization at the home bank, completely removing the cyclic deadlock of set-full replacement.

---

## 4. Directed & PyUVM Proof Logs

### Smoke & Unit Test Execution
- **`tb/smoke/test_clocked.py`**:
  - `test_dff_async`: Asynchronous reset assertion, edge propagation, and hold time verified. Status: **PASS (1/1)**.
- **`tb/l1_dir/test_f1_forward.py`**:
  - Co-landing regression test for Slice 16.1 (3 tests):
    - `test_f1_forward_positive`: Verification of 3-hop forward intervention (`GETS` $\to$ `FWD_GETS` $\to$ `DATAFWD`).
    - `test_f1_forward_negative_skip_fwd`: Injected fault verifying assertion catches missing forward. Status: **PASS**.
    - `test_f1_forward_negative_dirty_bit`: Injected fault verifying dirty bit corruption detection. Status: **PASS / Tracing**.

---

## 5. Formal Proof Results Matrix

| Property ID | Target Module | Verification Method | Engine / Depth | Status |
|---|---|---|---|:---:|
| **INV-SWMR** | L1 / Directory | SVA + Formal BMC | Z3 / $K=64$ | **PROVED** |
| **INV-EXCL** | Tile Coherence | SVA + Formal BMC | Boolector / $K=64$ | **PROVED** |
| **INV-SHARER** | Directory Array | SVA + Formal BMC | Z3 / $K=64$ | **PROVED** |
| **I1..I7 (NoC)** | 5-Port Router | Invariant Induction | $k=16$ | **PROVED** |
| **A5.1 (Credit)** | Router Link | SVA Credit Counter | BMC $K=64$ | **PROVED** |
| **A6.1 (XY Route)**| Router Arbiter | SVA XY Decode | BMC $K=64$ | **PROVED** |
| **F-DEADLOCK** | Full Mesh | Structural Proof + Lemma | Mathematical | **DISCHARGED** |

---

## 6. Discharged Defects & Counter-Examples

1. **Defect F1 (DIR_FWD_WAIT Successor Ambiguity)**:
   - *Issue*: Single transition table entry could not distinguish `GETS` vs `GETM` forward return.
   - *Resolution*: Added `pending_op` discriminator in Directory Transaction Record (DTR); single exit on `UNBLOCK`.
2. **Defect F2 (Orphan Transients on Clean/Dirty Eviction)**:
   - *Issue*: `EI_A` / `MI_A` transients hung without acknowledgement.
   - *Resolution*: Formally integrated `PUTACK` (code `1011`, VC2, 1 flit).
3. **Defect F3 (Packet Framing Inefficiency)**:
   - *Issue*: Per-flit tail bit caused payload penalty and misalignment.
   - *Resolution*: Header `LEN` [37:32] indicates packet length (1 to 9 flits). Payload flits are 100% data.
4. **Defect B2 (Conflict Eviction Deadlock)**:
   - *Issue*: Set-full conflict miss stalled waiting for victim way when evictions were deferred.
   - *Resolution*: Split Rule 10 into proactive (deferred) vs conflict (pre-released on VC0).

