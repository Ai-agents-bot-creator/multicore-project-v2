# HLD / LLD Diagrams — 2×2 FPGA Emulation Configuration

**Sole source:** `FINAL_whitepaper_v3.0.md` (v3.0, Unified Final). Companion to
`HLD_LLD_4x4_architecture.md`, which holds the full microarchitecture (router, NIC, L1/directory FSMs,
bank path, tap, flit and address formats). **The RTL is parameterised: at 2×2 only field widths and
counts change, not topology, FSMs, or pipeline structure.** FSM diagrams are therefore referenced, not
duplicated; every 2×2-specific item is derived from §3.6 (2×2 address map), §5.3 (formal configuration),
§6.1 (FPGA target, resource budget), §6.4 (timing closure), and §13 (adjudication ledger).

## Legend

| Marker | Meaning |
|---|---|
| ⚠ | Not specified in the white paper (WP) — shown, never invented. |
| [gated] | DMA content: only built if the Week-8 gate passes (§3.11, §7.1). |

The four adjudicated rulings R1–R4 (local-miss direct path, single serialized bank port, bank-first fill,
NIC↔router direct) are normative in the white paper at §3.12 and are inherited unchanged by the 2×2
configuration.

## Diagram index

| ID | Title | Level |
|---|---|---|
| HLD-F1 | 2×2 mesh (FPGA + formal configuration) | HLD |
| HLD-F2 | FPGA top level, ZedBoard XC7Z020 | HLD |
| HLD-F3 | Formal verification configuration, 2×2 | HLD |
| LLD-F1 | 2×2 parameter deltas vs 4×4 | LLD |
| LLD-F2 | Per-tile and per-configuration resource budget | LLD |
| LLD-F3 | Timing constraint set and critical paths (XDC content) | LLD |

---

# HLD-F1: 2×2 Mesh (FPGA emulation + formal configuration)

All four tiles are **corner tiles**: 3 active ports each (LOCAL + 2 mesh links), from the *same* 5-port
router module with the other two ports tied off (§3.5 — "3" at N=4 in §4.1 is the count of active ports,
not a different router).

```mermaid
flowchart TB
    subgraph MESH22["2x2 mesh - 4 identical CPU tiles - committed FPGA target and formal configuration"]
        direction TB
        subgraph ROW0["mesh row Y0"]
            direction LR
            Q00["position 0,0<br/>CPU tile, corner<br/>5-port module, 3 ports active"] ~~~ Q01["position 1,0<br/>CPU tile, corner<br/>5-port module, 3 ports active"]
        end
        subgraph ROW1["mesh row Y1"]
            direction LR
            Q10["position 0,1<br/>CPU tile, corner<br/>5-port module, 3 ports active"] ~~~ Q11["position 1,1<br/>CPU tile, corner<br/>5-port module, 3 ports active"]
        end
        Q00 <--> Q01
        Q10 <--> Q11
        Q00 <--> Q10
        Q01 <--> Q11
    end
    SAME["Each CPU tile is internally IDENTICAL to the 4x4 CPU tile of<br/>HLD-2 in HLD_LLD_4x4_architecture.md: same eight blocks, same<br/>direct local-miss path, single serialized bank port, NIC to router direct."]
    SAMEPORT["NOT limited to 2 links: the router is ONE 5-port module (LOCAL, N, S, E, W)<br/>instantiated at every tile position, here too. Only 2 of the 4 mesh ports are<br/>active at a 2x2 corner; the unused 2 are tied off and pruned by synthesis.<br/>The same RTL scales to any N x N, bounded at N <= 16 by the directory.<br/>2x2 is the FPGA emulation choice, not an architectural limit."]
    WRITEPOL["Write policy - L1 and L2 both WRITE-BACK.<br/>L1: write-back, write-allocate - WP 3.2.<br/>L2 bank: write-back, write-allocate - WP 3.2.<br/>Write-through would send a coherence transaction per store and would<br/>make the silent E to M upgrade impossible - WP 4.4."]
    HOP["Worst-case Manhattan distance: 2 hops - WP 5.3.<br/>Router pipeline 4 cycles per hop."]
    HOME2["Address map: home tile is 2 bits at addr 12:11, tag at 31:13,<br/>L2 set at 10:8, L1 set at 7:6 - L1 and L2 indices remain disjoint."]
    NOTCOV["Formal coverage boundary, disclosed - WP 5.3:<br/>all 2x2 tiles are corners, so the interior 5-port router case is NOT covered,<br/>and 3 or more sharers at distinct homes are NOT covered.<br/>Both are deferred to the 4x4 simulation campaign, not claimed equivalent."]
    DMA22["DMA device tile at 2x2: the WP states the DMA slot arithmetic only for<br/>4x4 (15+1, 30 KB, one reserved home code) - WP 3.11.<br/>A 2x2 DMA configuration is NOT SPECIFIED IN WP."]
    MESH22 --- SAME
    MESH22 --- SAMEPORT
    MESH22 --- WRITEPOL
    MESH22 --- HOP
    MESH22 --- HOME2
    MESH22 --- NOTCOV
    MESH22 --- DMA22
```

---

# HLD-F2: FPGA Top Level, ZedBoard XC7Z020 (§6.1, §6.4, §9)

```mermaid
flowchart TB
    CLK["Clock: 100 MHz, 10 ns period - WP 6.1 / 6.4"]
    RST["Reset synchroniser<br/>false path declared in the XDC"]
    subgraph TOP["fpga_top - XC7Z020-CLG484-1"]
        direction TB
        CHIP["2x2 mesh, 4 CPU tiles<br/>LUT ceiling 40 000, target at or below 20 000 of 53 200<br/>FF target at or below 25 000 of 106 400<br/>BRAM36 28 to 80 of 140, DSP 0"]
        STIM["Core / stimulus interface - master port for load, store, flush<br/>The on-board stimulus SOURCE (host bridge, VIO, or free-running generator)<br/>is NOT SPECIFIED IN WP. ILA/VIO debug infrastructure is listed as<br/>future scope in WP 9."]
        CHIP --- STIM
    end
    CLK --> TOP
    RST --> TOP
    BITS["Bitstream deliverable - milestone 9, Week 14.<br/>Power at or below 50 mW, Xilinx Power Estimator pre-synthesis,<br/>report_power post-implementation."]
    FALLBACK["Fallback order if fit or timing fails - WP 6.1:<br/>reduce cache associativity or set count, map tag/state arrays to LUTRAM,<br/>pipeline the router crossbar, reduce FPGA tile count.<br/>The VC count is FROZEN at 4 and is never a fallback variable."]
    TOP --- BITS
    TOP --- FALLBACK
```

---

# HLD-F3: Formal Verification Configuration, 2×2 (§5.3, Appendix E)

```mermaid
flowchart TB
    MODEL["Formal model: the 2x2 mesh, 4 tiles<br/>minimum that exercises a multi-sharer fan-out of 2 sharers plus 1 requester<br/>and the 2-bit home decode - WP 5.3"]
    subgraph PROPS["Property set"]
        direction TB
        SAFE["Safety, BMC proved: A1.1 to A1.5, A2.1 to A2.7, A3, A4, A6, A7, A8<br/>= 38 bound safety assertions"]
        LIVE2["Bounded liveness: no orphan transient and no message loss,<br/>each within T = 64 cycles, under Premise F<br/>derivation 5 traversals x 2 hops x 4 cycles = 40 fabric + up to 24 overhead"]
        DEAD2["Deadlock lemma of WP 4.6 - premises confirmed by k-induction at k = 16:<br/>VC index preserved, inter-class edges ascend, credit invariant holds"]
        INV2["Formal-only network invariants I1 to I7 - NOT part of the 42 bound SVA<br/>XY path, VC equals class, credit invariant, no send at zero credit,<br/>per-VC FIFO ordering, delivery or protocol termination"]
        SAFE --- LIVE2
        DEAD2 --- INV2
    end
    ENGINES["Engines: mode bmc, depth K = 64, at least 2x the bound T,<br/>plus mode prove, k-induction, as the primary engine where tractable.<br/>A BMC depth below T would be unsound - a full remote transaction could not<br/>complete and every liveness property would pass vacuously."]
    BOUNDARY["Coverage boundary, disclosed not hidden - WP 5.3 table:<br/>covered at 2x2: single-sharer invalidation, single-owner forward,<br/>silent E to M upgrade, multi-sharer fan-out, DIR-M with two concurrent GETS,<br/>two distinct home tiles.<br/>NOT covered: interior 5-port router, 9 tiles minimum; 3 or more sharers at<br/>distinct homes simultaneously - both deferred to 4x4 simulation."]
    OPEN["NOT SPECIFIED IN WP: the RTL mechanism that counts T for orphan-transient<br/>detection is open item 7, Week 10. The age-escape threshold of 8 rounds is<br/>open item 8, to be confirmed against measured VC load."]
    MODEL --> PROPS --> ENGINES
    PROPS --- BOUNDARY
    PROPS --- OPEN
```

---

# LLD-F1: 2×2 Parameter Deltas vs 4×4 (§3.2, §3.6, §5.3, §13)

Everything derives from `TILE_COUNT = N²` (§3.6 parameter table).

```mermaid
flowchart TB
    subgraph W["Widths that CHANGE at 2x2"]
        direction TB
        TC["TILE_COUNT = 4"]
        IDW["TILE_ID_W = ceil(log2 4) = 2<br/>logical width of dest and src header fields<br/>the 8-bit header fields 63:56 and 55:48 stay as reserved-width fields with unused high bits zero"]
        SH["SHARER_W = 4 - full-map vector, bit t equals 1 iff tile t holds a shared copy"]
        DE["Directory entry: 3 + 2 + 4 + 1 = 10 bits USED,<br/>stored padded to 32 bits for BRAM alignment - WP 6.1 per-tile table"]
        TAG["Stored L2 tag = addr 31:13 concatenated with addr 7:6 = 21 bits,<br/>still non-contiguous - WP 3.6"]
        HM["Home field at addr 12:11, 2 bits; L2 tag field at addr 31:13, 19 bits.<br/>L2 set 10:8 and L1 set 7:6 are unchanged and remain disjoint."]
        TC --- IDW --- SH --- DE --- TAG --- HM
    end
    subgraph S["Structures that DO NOT change"]
        direction TB
        L1G["L1: 4 sets x 4 ways x 64 B = 1 KB, tree-PLRU 3 b per set"]
        L2G["L2 bank: 8 sets x 4 ways x 64 B = 2 KB, tree-PLRU 3 b per set"]
        MSG["Message set: 12 core plus 2 gated, codes 0000 to 1101, 1110/1111 reserved"]
        VCS["4 VCs, depth 4 each, credit counters 4-bit init 4, VC count frozen"]
        FSM["L1 and directory FSMs: identical to the 4x4 diagrams<br/>LLD-2 and LLD-3 in HLD_LLD_4x4_architecture.md - only widths differ"]
        FLIT["64-bit flit, header map and LEN framing: identical - LLD-8, 4x4 file"]
        L1G --- L2G --- MSG --- VCS --- FSM --- FLIT
    end
    LAT["Latency constants at 2x2: worst Manhattan distance 2 hops,<br/>router pipeline 4 cycles per hop, formal bound T = 64 cycles.<br/>The 4x4 simulation bound is T = 150 cycles at 6 hops."]
    W --- LAT
    S --- LAT
```

---

# LLD-F2: Resource Budget, 2×2 (§6.1)

First-order estimate; synthesis must confirm (§12 item 5 — the fit claim stays open until then).

```mermaid
flowchart TB
    subgraph TILE["Per CPU tile - BRAM36"]
        direction TB
        B_L1D["L1 data, 16 lines x 64 B: 1 to 4"]
        B_L1T["L1 tag, 16 x 24 b: 0 to 1, LUTRAM capable"]
        B_L2D["L2 data, 32 lines x 64 B: 1 to 8"]
        B_L2T["L2 tag, 32 x 21 b stored at 2x2: 0 to 1, LUTRAM capable"]
        B_DIR["Directory, 32 x 32 b: 1"]
        B_RF["Router input FIFOs, 5 ports x 4 VCs x 4 x 64 b: 3"]
        B_NIC["NIC FIFOs: 1 to 2"]
        B_LRU["LRU state: registers, 0"]
        B_TOT["Total per CPU tile: 7 to 20 BRAM36"]
        B_L1D --- B_L1T --- B_L2D --- B_L2T --- B_DIR --- B_RF --- B_NIC --- B_LRU --- B_TOT
    end
    subgraph CFG["Per configuration - BRAM36"]
        direction TB
        C_FAV["2x2, 4 CPU tiles, favourable array mapping: 28"]
        C_CON["2x2, 4 CPU tiles, conservative array mapping: 80"]
        C_44["reference only, 4x4, 16 CPU tiles: 112 to 320 - exceeds the device"]
        C_FAV --- C_CON --- C_44
    end
    subgraph LUTS["LUT and FF budget"]
        direction TB
        L_R["Router about 2200 to 2500 LUTs<br/>5x5 crossbar about 1600, VC allocation and arbitration about 400, control about 200"]
        L_C["L1, L2 and directory controller about 700 per tile"]
        L_N["NIC about 300 per tile"]
        L_T["2x2 total about 13000 to 19000 LUTs, 25 to 36 percent of 53200"]
        L_R --- L_C --- L_N --- L_T
    end
    DEV["Device: XC7Z020 - 53200 LUT, 106400 FF, 140 BRAM36 about 630 KB, 220 DSP.<br/>Ceilings: LUT at or below 40000, FF at or below 50000, BRAM at or below 70, DSP 0.<br/>BRAM is NOT a constraint at 2x2, 28 to 80 of 140 - WP 6.1."]
    BRAMRULE["BRAM36 configures as 1024x36 or 512x72, so a 2 KB bank of 32 lines x 64 B<br/>is 1 BRAM36 with one 64-bit port, 4 with four parallel way ports, or 8 for a<br/>full 512-bit line read. The inherited 15-BRAM-per-bank figure is an<br/>arithmetic error, WP 6.1 and WP 13 item R."]
    TILE --- DEV
    CFG --- DEV
    LUTS --- DEV
    CFG --- BRAMRULE
```

---

# LLD-F3: Timing Constraint Set and Critical Paths, XDC Content (§6.4)

```mermaid
flowchart TB
    subgraph CON["Constraints - XDC is a named deliverable, milestone 10, Week 14"]
        direction TB
        T_CLK["Clock: 10 ns, 100 MHz"]
        T_SU["Setup uncertainty: 0.2 ns"]
        T_HD["Hold uncertainty: 0.1 ns"]
        T_IO["I/O delay: 2.0 ns max, 0.5 ns min"]
        T_FP["Reset synchroniser: false path declared"]
        T_RETIMING["Retiming enabled except on the reset synchroniser,<br/>handshake paths and state registers"]
        T_CLK --- T_SU --- T_HD --- T_IO --- T_FP --- T_RETIMING
    end
    subgraph TARGETS["Sign-off targets"]
        direction TB
        G_WNS["WNS at or above 0 ns"]
        G_WHS["WHS at or above 0 ns"]
        G_WPWS["WPWS at or above 3.750 ns"]
        G_TNS["TNS equals 0"]
        G_FAIL["Failing endpoints equals 0"]
        G_WNS --- G_WHS --- G_WPWS --- G_TNS --- G_FAIL
    end
    subgraph CRIT["Known critical paths and mitigations - WP 6.4"]
        direction TB
        K1["1 L2 tag compare to directory state decision<br/>mitigation: split tag compare and directory lookup into separate pipeline stages"]
        K2["2 Router arbitration to crossbar output<br/>mitigation: the 4-stage pipeline RC VA SA ST already separates arbitration from traversal"]
        K3["3 NIC packet decode to cache interface<br/>mitigation: register the decoder output"]
        K1 --- K2 --- K3
    end
    RISK["Risks named in WP 7.3: timing closure failure at 100 MHz is Medium probability<br/>with mitigations reduce cache size, LUTRAM mapping, an additional router pipeline<br/>stage, floorplanning.<br/>Open item 4: router pipeline depth 3 vs 4 stages closes at RTL freeze, Week 4."]
    CON --> TARGETS
    CON --- CRIT
    CON --- RISK
```

---

*End of 2×2 FPGA diagram set. All FSM and datapath microarchitecture is drawn once, in the 4×4 file;
this file adds only what the WP states uniquely for the 2×2 configuration.*
