### 🧠 Model Scratchpad
**Iteration 2 — Multi-agent synthesis.** Corpus contains six independent peer critiques (Claude, Baseline Critic, Gemini, GLM-5.3, Qwen3.7, GLM-z.ai) plus the original white-paper + context documents. All peers independently flag the same fatal cluster: incomplete eviction path (missing PUTACK / PUTM consumption), non-deterministic `DIR_FWD_WAIT`, DMA status contradiction, fixed-width directory fields that break the “parameterised N×N” claim, undefined multi-flit termination, equal-priority VC2/VC3, and True-LRU vs Tree-PLRU inconsistency. No peer disputes the core architecture (2-D mesh + directory MESI + 4 VCs + private L1 + static-NUCA L2).  

**Consensus resolution rules applied:**
- Fatal protocol incompleteness → mandatory fix (PUTACK, split FWD states, SM_D+INV race).
- Parameterisation claim → widths derived from `N` / `TILE_ID_WIDTH`.
- DMA → demoted to optional extension with gate; encoding slots reserved.
- Verification claims → safety via BMC, liveness via structural layered proof (XY + class separation) + bounded fairness; 2-tile limitation explicitly disclosed.
- Resource risk → 2×2 FPGA is the only hardware target; BRAM contingency stated.
- LRU → Tree-PLRU (3 bits/set) for both L1 and L2 (area parity, <0.5 % hit-rate delta at 4-way).
- Document hygiene → schedule title, open-item numbering, ring residue, duplicate future-scope rows, novelty softening.

All retained elements (mesh topology justification, MESI selection under C1–C10, 64 B lines, message-set minimality of the core 11 messages) are ratified by every peer. No new functional features introduced.

### 📋 Architectural Change Log
**Final consensus modifications (ordered by severity).**

| # | Target | Final Modification | Reason & Proof |
|---|--------|--------------------|---------------|
| 1 | §3.3 Message set + Appendix B | Add **PUTACK** (dir→L1, 1 flit, code 14, VC2). Add directory rows: `DIR_E + PUTS → DIR_I + PUTACK`; `DIR_M + PUTM → write-back + DIR_I + PUTACK`. PUTS remains 1-flit (clean). | EI_A/MI_A currently have no consuming event → orphan transient (violates own “No Orphan Transient” invariant). Peer consensus (Claude, GLM-z.ai, Baseline). |
| 2 | Appendix B `DIR_FWD_WAIT` | Split → `DIR_FWD_WAIT_S` (GETS) / `DIR_FWD_WAIT_M` (GETM). Or keep single state + 1-bit request-type latch in controller. | Same (state,event) maps to two next-states → non-deterministic FSM (unsynthesizable). All peers flag. |
| 3 | L1 transients (Appendix A) | Add `SM_INV` (or `SI_M`): entered on INV while in SM_D; send INVACK, retain outstanding GETM, exit to M on exclusive DATA. Clarify SM_D exit = exclusive DATA only (directory already counted INVACKs). | Race documented in Primer §8.3; current set leaves `(SM_D, INV)` undefined. Claude + GLM. |
| 4 | Directory State field & transients | Normative encoding: 3-bit state = {DIR_I, DIR_S, DIR_E, DIR_M, DIR_MEM_WAIT, DIR_FWD_WAIT, DIR_INV_WAIT, DIR_EVICT}. Sub-states of EVICT + S/M discriminator live in controller transaction record. Expand `DIR_EVICT_*` fully. | 3 bits = 8 codes; wildcard + split FWD would overflow. Peers converge on this exact layout. |
| 5 | §3.2 / §3.5 / Abstract widths | `TILE_ID_WIDTH = ⌈log₂(N²)⌉`; `OWNER_WIDTH = TILE_ID_WIDTH`; `SHARER_WIDTH = N²` (full-map). Explicit bound: full-map is normative only for N≤16; larger N requires hierarchical/coarse directory (future). Dest/src fields use TILE_ID_WIDTH. | Fixed 8/16-bit fields falsify “parameterised N×N”. Arithmetic: N=8 needs 64-bit sharers. All peers. |
| 6 | §3.5 Packet format | Header reserved[5:0] = packet length in flits (1–63). Body flits pure 64-bit payload. Router decrements counter. | Current format has tail only in header → 9-flit line packet is undelimited. Length-in-header is the only option that preserves 9-flit size and pure body. Consensus. |
| 7 | §3.4 Arbitration | VC arbitration: strict priority RESP (VC2) > INV (VC3) > FWD (VC1) > REQ (VC0). Switch arbitration: round-robin across input ports per output. | Equal “High” + RR across VCs allows INV to block DATA/INVACK → protocol deadlock under load (Dally–Seitz). Fixed class priority required by every peer. |
| 8 | DMA status (Abstract, §1.2–1.3, §3.7, §5.1, §7.3, Appendix C) | Demote to “Optional Device Tile — Month-2 gate”. Remove from primary contributions. Encoding slots 11–13 marked Reserved. Keep single-block (exactly 9 flits) semantics if gate passes; no new directory states. | Simultaneous “contribution / under evaluation / high-risk drop” is the exact credibility defect §8 condemns. Unanimous peer resolution. |
| 9 | §3.2 / §4.4 LRU | Both L1 and L2 use Tree-PLRU (3 bits/set). | True LRU costs 5 bits/set; Tree-PLRU <0.5 % hit-rate delta at 4-way (standard result). Context document already recommends replacement; peers enforce consistency. |
| 10 | §5.2 Formal method | Safety (single-writer, data consistency, directory consistency, no orphan transient) → BMC (K≥32) on 2-tile. Liveness (no message loss, deadlock freedom) → structural layered proof (XY acyclicity + 4-class separation + receptivity rule) + bounded fairness. Explicitly disclose 2-tile limitation for ≥3-requester races. | BMC cannot prove unbounded liveness (Biere et al.). Structural proof already exists in corpus and is N-independent. |
| 11 | §3.1 Tile Organisation | Complete the list: (1) core/testbench interface, (2) private L1 (4×4×64 B, Tree-PLRU, MESI), (3) L2 bank + directory array, (4) NIC, (5) 5-port router, (6) local memory tap. Note DMA tile is structural variant (no L2/directory). | Section header promises content that is absent. |
| 12 | §6.1 FPGA | Target = 2×2 only. Explicit BRAM risk statement + mitigation (LUTRAM for tags/directory or reduced associativity). Remove “reduce VC count” fallback. | 4×4 exceeds 140 BRAM36; reducing VCs breaks deadlock freedom. |
| 13 | Document hygiene | §7.1 retitle “Four-Month Schedule”; Open Items renumber 1–4 and resolve or mark deferred; Test 13 → “Mesh saturation”; Future Scope table de-duplicated; Abstract novelty claim softened to “integrated open verification methodology combining directed tests, pyuvm, and SymbiYosys”. | Pure textual contradictions flagged by every peer. |

**Retained without change (peer-ratified):** 2-D mesh topology + XY routing, MESI selection under the ten constraints, 64-byte lines, 4 VCs with the four protocol classes, static NUCA address interleaving, core 11-message MESI set (plus PUTACK), write-back/write-allocate, parameterised N×N RTL structure, 2×2 FPGA / 4×4 simulation split.

### 🔏 Model Signature
[Architect-Critique-Node] — Principal System Architecture Critic & Consensus Facilitator | Iteration 2 Synthesis | 2026-10-28T11:42:00+05:30

---

**Finalized White-Paper Skeleton (normative text after application of the Change Log)**

**Title** remains.  
**Abstract** — replace novelty sentence with: “The contribution is a complete, open, reproducible verification methodology that integrates directed tests, a pyuvm constrained-random environment, and SymbiYosys formal proofs for a directory-based MESI protocol carried over a packet-switched 2-D mesh.” DMA sentence becomes “An optional coherent DMA device tile is defined as a Month-2 gated extension.”

**§1.2 Scope** — FPGA target locked to 2×2; 4×4 simulation only. DMA listed under “Optional / gated”.

**§1.3 Contributions** — remove item 4 (DMA); keep the three remaining.

**§3.1** — insert the six-component list above.

**§3.2** — L1/L2 geometry unchanged; replacement = Tree-PLRU both levels; directory entry widths parameterised as above; State field = 3 bits encoding the eight states listed in Change #4.

**§3.3** — message set = core 11 MESI messages + PUTACK; DMA messages reserved. L1 transients include SM_INV. Directory transitions complete (PUTACK rows + split FWD states).

**§3.4** — arbitration policy as Change #7.

**§3.5** — header reserved[5:0] = length; body pure payload.

**§3.6** — address map retained (home tile bits inside L1 tag by definition); widths derived from N.

**§3.7** — rewritten as “Optional DMA Device Tile (Month-2 gate)”.

**§5.2** — formal method rewritten per Change #10; properties list expanded with “No orphan transient” and refined directory consistency.

**§6.1** — 2×2 only + BRAM contingency; VC-count reduction removed.

**§7** — Four-Month Schedule; risks table updated (DMA gate, formal depth already baseline).

**Appendices A/B/C** — fully expanded transition tables, exact encodings, reserved DMA codes.

All other sections (Related Work, Design Decisions, Project Plan milestones, Claims-vs-Artifacts, Future Scope) remain after the hygiene fixes. The resulting document is internally consistent, protocol-complete, resource-realistic, and verification-sound.