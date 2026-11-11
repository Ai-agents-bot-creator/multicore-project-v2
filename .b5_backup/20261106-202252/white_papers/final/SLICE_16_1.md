# §16.1 Implementation Slice — Forward Release (L1 FSM + Directory Controller)

**Goal:** make work-breakdown row §16.1 green end-to-end — RTL + SVA + reference-model shadow — so the first §8 "Planned — milestone N" claim converts into evidence. This slice also unblocks §16.2 (exclusive bit), §16.4 (DATAFWD dirty bit) and §16.6 (evict-during-forward).

**Normative source:** `FINAL_whitepaper_v3.0.md` §3.3 (rules 1–10), §3.4, §3.7, Appendix A, Appendix B, §4.6 (A1/A2/A7); `SPEC_SHEET.md` §7/§16.

**Effort:** 3–4 days baseline (L1 side 1 day, directory side 2–3 days), Week 10 gate.

---

## 1. L1 MESI controller (`l1_mesi_ctrl`)

### 1.1 States and transitions touched

Stable: `I, S, E, M`. Transient: `IS_D, IM_D, SM_D, EI_A, MI_A` (unchanged counts). No new L1 states are added — forward release is handled as a transition *out of* E/M, not as a new state.

| Current | Event | Next | Actions |
|---|---|---|---|
| `E` | Store hit | `M` | Silent upgrade; no message (Appendix B note 1 — the L1 is authoritative for E-vs-M) |
| `E` | `FWD_GETS` (VC1) | `S` | Send `DATAFWD` (clean data) to the home directory; downgrade E→S; the owner becomes a sharer |
| `M` | `FWD_GETS` (VC1) | `S` | Send `DATAFWD` (dirty data) to the home directory; downgrade M→S; the owner becomes a sharer |
| `E` | `FWD_GETM` (VC1) | `I` | Send `DATAFWD` (clean data) to the home directory; downgrade to I (ownership transfer) |
| `M` | `FWD_GETM` (VC1) | `I` | Send `DATAFWD` (dirty data) to the home directory; downgrade to I (ownership transfer) |
| `I` | `FWD_GETS`/`FWD_GETM` (VC1) | `I` | Send `INVACK` (VC2) — defensive; covers the evict-during-forward race (N5, N12) |
| `EI_A` | `FWD_GETS`/`FWD_GETM` (VC1) | `EI_A` | Send `INVACK` (VC2) — the owner has already released the line (PUTS sent) (N12) |
| `MI_A` | `FWD_GETS`/`FWD_GETM` (VC1) | `MI_A` | Send `INVACK` (VC2) — the owner has already sent PUTM, which satisfies the forward's data obligation (N12) |

### 1.2 Receptivity (Premise R)

An L1 with an outstanding miss on line A must still accept and service `INV`/`DATA`/`INVACK`/`FWD` for **other** lines immediately, on a path independent of the miss path. `FWD` for the *same* line as the outstanding miss cannot occur (Lemma L1, §4.6). This is the property that lets the forward path run while a miss is in flight on another line.

### 1.3 Deferred eviction (rule 10)

An L1 with an outstanding miss does not begin a replacement eviction; a needed eviction is deferred until the miss completes. MSHRs are future scope (§9). This keeps the single-FSM model implementable without a per-tile transaction queue.

### 1.4 DATA exclusive bit (rule 9) — consumer side

The L1 installs `E` on `DATA(excl=1)` and `S` on `DATA(excl=0)` (Appendix A, `IS_D`). The directory is responsible for setting the bit (§16.2); the L1 only consumes it. A wrong bit places an E copy alongside an S copy and violates A1.3/A2.6 — this is the failure mode the §16.2 assertions guard.

### 1.5 Dirty indication on DATAFWD (N3b) — producer side

When the owner holds the line in M, the `DATAFWD` packet's header bit [39] is set (dirty); when in E it is clear. The NIC sets this bit from the owner's L1 state; the directory consumes it to set/clear the bank dirty bit. The L1 must expose its current MESI state to the NIC on the forward path.

---

## 2. Directory controller (`dir_ctrl`)

### 2.1 States and transitions touched

Stable: `DIR_I, DIR_S, DIR_E, DIR_M`. Transient: `DIR_MEM_WAIT, DIR_FWD_WAIT, DIR_INV_WAIT, DIR_EVICT`.

#### Forward entries (GETS)

| Current | Event | Action | Next |
|---|---|---|---|
| `DIR_E` | `GETS, other` | Enter `DIR_FWD_WAIT`; `pending_op = GETS`; send `FWD_GETS`; the old owner downgrades E/M→S; directory records old owner + requester as sharers | `DIR_S` on `UNBLOCK` |
| `DIR_M` | `GETS, other` | Enter `DIR_FWD_WAIT`; `pending_op = GETS`; send `FWD_GETS`; the old owner downgrades M→S; directory records old owner + requester as sharers | `DIR_S` on `UNBLOCK` (after `DATAFWD` update) |

#### Forward entries (GETM)

| Current | Event | Action | Next |
|---|---|---|---|
| `DIR_E` | `GETM, other` | Enter `DIR_FWD_WAIT`; `pending_op = GETM`; send `FWD_GETM`; the old owner downgrades to I; directory clears old owner's sharer bit and sets `Owner = requester` | `DIR_M` on `UNBLOCK` |
| `DIR_M` | `GETM, other` | Enter `DIR_FWD_WAIT`; `pending_op = GETM`; send `FWD_GETM`; the old owner downgrades to I; directory clears old owner's sharer bit and sets `Owner = requester` | `DIR_M` on `UNBLOCK` (ownership transfer) |

#### Forward data arrival

| Current | Event | Action | Next |
|---|---|---|---|
| `DIR_FWD_WAIT` | `DATAFWD` | Write dirty data into the home bank (set the bank dirty bit from header bit [39]); send `DATA` to the requester (Owner/sharer update committed on the exit transition selected by `pending_op`) | — (awaiting `UNBLOCK`) |
| `DIR_FWD_WAIT` | `PUTM (owner)` | Owner evicted concurrently: the `PUTM` satisfies the forward's data obligation — write data into the bank, set the bank dirty bit, clear the old owner's sharer bit (and set `Owner = requester` for `pending_op = GETM`); send `PUTACK` to release the owner; continue awaiting `UNBLOCK` (N12) | — (awaiting `UNBLOCK`) |
| `DIR_FWD_WAIT` | `PUTS (owner)` | Owner (a clean DIR_E owner) released the line before the forward was served: the bank holds the current value, so cancel the forward — clear the old owner's sharer bit, send `PUTACK`, and serve the requester from the bank; the pending `UNBLOCK` still selects `DIR_S` (N12) | — (awaiting `UNBLOCK`) |
| `DIR_FWD_WAIT` | `INVACK` (defensive) | Duplicate release — ignore, no state change; the owner's `PUTS` or `PUTM` resolves the forward and the two travel on different VCs (N12) | unchanged |

#### Silent-upgrade eviction

| Current | Event | Action | Next |
|---|---|---|---|
| `DIR_E` | `PUTM (owner)` | Owner silently upgraded to M then evicted: write data into the home bank (set dirty bit), clear `Owner` (and its sharer bit); send `PUTACK` | `DIR_I` |

#### Single-exit rule (§3.3)

`DIR_MEM_WAIT`, `DIR_FWD_WAIT`, `DIR_INV_WAIT` each exit **only** on `UNBLOCK`. `DIR_EVICT` is entered only from `DIR_MEM_WAIT` (a pending fill needing a victim way) and exits back to `DIR_MEM_WAIT`. Intermediate events (`MEM_DATA`, `DATAFWD`, `INVACK`, `PUTM`) advance DTR progress only and never change the SRAM state field.

`pending_op` encoding: `000 NONE, 001 GETS, 010 GETM, 011 PUT, 100 DMA` (5 used; `EVICT` is held in the 2-bit evict sub-state, not in `pending_op`, because the pending fill's GETS/GETM survives the `DIR_EVICT` excursion).

### 2.2 DATA exclusive bit (§16.2, rule 9)

Set `excl = 1` on a `DIR_I` grant (GETS or GETM) and on every `GETM` grant including a forward; set `excl = 0` on every `GETS` grant including a forward (the old owner has downgraded to S). The L1 installs E on `excl=1` and S on `excl=0`.

### 2.3 DIR_I victim write-back (§16.5, N4)

In `DIR_EVICT`, when the victim's directory entry is `DIR_I` **and** the bank line's dirty bit is set, take the `WRITE_BACK` sub-state (bank → tap). Otherwise the victim needs no write-back. This is the only path that prevents a dirty bank line from being silently dropped.

---

## 3. SVA / formal assertions (A1, A2, A7)

The 42 bound SVA are grouped into eight categories A1–A8. The categories that gate this slice:

| Category | Count | What it checks (relevant to §16.1) |
|---|---|---|
| **A1.x** | 5 | MESI invariants, scoped to the L1 arrays: at most one L1 in M (A1.1) and at most one in E (A1.2); S excludes any E/M copy (A1.3); shared data equality (A1.5) |
| **A2.x** | 7 | Sharer-vector consistency: sharers = S-mask (A2.2); exactly one holder, equal to Owner (A2.3); owner ∈ sharers, sharers = {Owner} (A2.6); DIR_I ⟹ sharers = 0 and valid = 0 (A2.4) |
| **A3.x** | 6 | Message protocol: every request answered, no response without a request, correct destination. The defensive `INVACK` is still a response to a received `FWD`, so it must satisfy A3.1 |
| **A5.x** | 4 | No orphan transient (bounded liveness): every transient exits within T |
| **A7.x** | 4 | State-machine legality: every (state, event) pair maps to a defined next state; no undefined transitions; `DIR_FWD_WAIT` has exactly one exit (`UNBLOCK`) and `pending_op` selects the successor |

**Specific assertions this slice must keep green:**

- **A1.1** — at most one L1 holds a line in M at any time. The forward path is the only place a second M could appear; the exclusive-bit rule (§16.2) and the owner's downgrade to I on `FWD_GETM` are what keep it true.
- **A1.3** — a line in S excludes any E or M copy. The old owner's downgrade E/M→S on `FWD_GETS` is what keeps it true; if the downgrade is missed, an E copy survives alongside S.
- **A2.2** — sharers = S-mask. The directory records old owner + requester as sharers on `FWD_GETS` and clears the old owner's bit on `FWD_GETM`.
- **A2.6** — owner ∈ sharers (when the directory is in DIR_E or DIR_M). On a `FWD_GETM` the owner changes from old to requester; the directory must update the `Owner` field and the sharer bit together.
- **A3.x** — `DIR_FWD_WAIT` has exactly one exit (`UNBLOCK`); `pending_op` selects `DIR_S` (GETS) or `DIR_M` (GETM). The `DATAFWD`/`PUTM`/`PUTS`/`INVACK` rows must not change the SRAM state field.
- **A7.x** — every (state, event) pair in the directory FSM is defined, including the four new `DIR_FWD_WAIT` rows and the `DIR_E | PUTM` row.
- **A5.x** — no orphan transient: every transient exits within T = 64 cycles (2×2 formal). The evict-during-forward races (N12) are the new orphan-transient risks; the defensive `INVACK` and the `PUTM`/`PUTS` absorption rows are what close them.

**Bounded liveness (Premise F):** every transient exits within T; every request receives a response within T; every VC with pending traffic is served within 13 arbitration rounds (8-round age escape + ≤5 rounds of output-port round-robin).

---

## 4. Reference-model shadow

The transaction-level reference model (§5.4) must shadow, for every transaction:

| Shadow structure | Field(s) this slice touches |
|---|---|
| Per tile/set/way L1 | `state` (I/S/E/M), `tag`, `data`, `MESI state` |
| Per bank/set/way L2 | `state` (valid), `tag`, `dirty` bit, `data` |
| Per bank directory entry | `state` (DIR_I/S/E/M/…), `owner`, `sharers`, `valid` |
| Per bank DTR | `pending_op`, `pending requester`, `evict sub-state`, `evict victim`, `victim dirty` |
| Global address→data map (the tap) | updated only on `DIR_EVICT/WRITE_BACK`; a bank-resident line is authoritative at the bank (§3.9) |
| Outstanding transaction set | used to detect lost messages and orphan transients |

**Shadow update rules for this slice:**

1. On `FWD_GETS` (DIR_E or DIR_M origin): the old owner's L1 state → S; the directory entry → `DIR_FWD_WAIT`; `pending_op = GETS`. The sharer bits are **deferred** — they commit on the exit transition (Appendix B).
2. On `FWD_GETM` (DIR_E or DIR_M origin): the old owner's L1 state → I; the directory entry → `DIR_FWD_WAIT`; `pending_op = GETM`. The old owner's sharer bit and `Owner = requester` are **deferred** — they commit on the exit transition (Appendix B).
3. On `DATAFWD` (header bit [39] clear, clean data): bank data written; bank dirty bit = 0; no L1 state change on the requester yet (waits for `DATA`).
4. On `DATAFWD` (header bit [39] set, dirty data): bank data written; bank dirty bit = 1; no L1 state change on the requester yet (waits for `DATA`).
5. On `DATA` to the requester with `excl = 0`: requester installs the line in S and sends `UNBLOCK` (VC2).
6. On `DATA` to the requester with `excl = 1`: requester installs the line in M and sends `UNBLOCK` (VC2).
7. On `PUTM` in `DIR_FWD_WAIT`: bank data written; bank dirty bit = 1; old owner's sharer bit cleared; `PUTACK` sent; for `pending_op = GETM`, `Owner = requester` (committed here, since the owner released the line instead of downgrading).
8. On `PUTS` in `DIR_FWD_WAIT`: bank untouched (holds current value); old owner's sharer bit cleared; `PUTACK` sent; requester served from bank.
9. On `UNBLOCK` with `pending_op = GETS`: directory entry → `DIR_S`; **sharer bits for old owner + requester committed** (shadow rule 1's deferral resolves here).
10. On `UNBLOCK` with `pending_op = GETM`: directory entry → `DIR_M`; **`Owner = requester` committed** (shadow rule 2's deferral resolves here).
11. On the L1's victim release (`PUTM` for an M victim, `PUTS` for an S/E victim): the victim's L1 state → I (for an M victim, after `PUTACK`); the home bank's dirty bit is set on `PUTM`; the victim's sharer bit is cleared by the directory when the release is processed (the `DIR_E + PUTM` row); the requester's miss request is issued only afterwards.

The scoreboard compares after every transaction: L1 state, L1 data, L2 state, L2 data, dir state, dir owner, dir sharers, memory (tap) contents. A mismatch on any of these fails the slice.

---

## 5. Test plan (directed tests)

| # | Test | What it exercises |
|---|---|---|
| F1 | Forward, clean owner (DIR_E + GETS from another tile) | `FWD_GETS`, owner E→S, bank write (clean), sharer bits, `DIR_S` on `UNBLOCK` |
| F2 | Forward, dirty owner (DIR_M + GETM from another tile) | `FWD_GETM`, owner M→I, bank write (dirty), `Owner = requester`, `DIR_M` on `UNBLOCK` |
| F3 | Forward, GETS from DIR_M (dirty owner, shared result) | `FWD_GETS`, owner M→S, bank write (dirty), sharer bits, `DIR_S` on `UNBLOCK` |
| F4 | Forward, GETM from DIR_E (clean owner, exclusive result) | `FWD_GETM`, owner E→I, bank write (clean), `Owner = requester`, `DIR_M` on `UNBLOCK` |
| F5 | Silent upgrade then eviction (`DIR_E + PUTM`) | Owner E→M silently, then evicts: `PUTM` → `DIR_I`, bank dirty, `PUTACK` |
| F6 | Evict-during-forward, clean owner | Owner in E, dir sends `FWD_GETS`, owner concurrently evicts (EI_A) → defensive `INVACK`; directory absorbs `PUTS` in `DIR_FWD_WAIT` |
| F7 | Evict-during-forward, dirty owner | Owner in M, dir sends `FWD_GETM`, owner concurrently evicts (MI_A) → defensive `INVACK`; directory absorbs `PUTM` in `DIR_FWD_WAIT` |
| F8 | Exclusive-bit correctness | Forward of a `GETS` grants `excl=0` (requester installs S); forward of a `GETM` grants `excl=1` (requester installs M). **Pending §16.2** — requires the directory-side exclusive-bit generation; if §16.2 is not co-landed, mark F8 as pending rather than green |
| F9 | A1.1 / A1.3 / A2.2 / A2.6 on the forward path | Formal (BMC, K = 64) + simulation |

Tests F1–F8 are directed (§5.1 style); F9 is the formal run. All must pass before the slice is green.

---

## 6. Exit criteria

The slice is green when:

1. **RTL** — `l1_mesi_ctrl` and `dir_ctrl` implement every row in §2.1 and §1.1; the L1 exposes its MESI state to the NIC for header bit [39].
2. **SVA** — A1.1, A1.3, A2.2, A2.6, A3.x, A5.x, A7.x all pass in simulation (BMC K = 64 for safety).
3. **Reference model** — the scoreboard shows zero mismatches on F1–F8 and on the formal run (F9).
4. **Verifier** — `python3 verify_patch_set.py --dir . --build-script build_diagrams_html.py` still reports 130/130 (no spec regression).

Until all four are green, §8's "Forward release implemented" claim stays "Planned — milestone N".
