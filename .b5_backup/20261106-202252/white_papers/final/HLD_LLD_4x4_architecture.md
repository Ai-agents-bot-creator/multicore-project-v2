# HLD / LLD Diagrams — 4×4 Full Architecture

**Sole source:** `FINAL_whitepaper_v3.0.md` (v3.0, Unified Final). Every block, edge, field, state, and
number below is taken from that document. Nothing is invented.

Companion file: `HLD_LLD_2x2_FPGA.md` (FPGA-emulation configuration: 2×2 mesh, formal config, FPGA top,
resource budget, timing constraints). Identical microarchitecture; only parameters and field widths differ.

## Legend

| Marker | Meaning |
|---|---|
| ⚠ | Not specified in the white paper (WP). Shown so it is visible, **not** silently invented. |
| [gated] | DMA content: only built if the Week-8 gate passes (§3.11, §7.1). |
| R1–R4 | Adjudicated rulings given by the document owner during diagram generation (recorded in §13 spirit): |

**R1 — Local same-tile miss path.** An L1 miss on a line homed at its own tile goes
`L1 → intra-tile mux → local L2/directory controller` directly, with **no** router/NIC traversal.
(Directed tests 1 vs 2 distinguish local-home from remote-home exactly this way.)

**R2 — L2 bank access model.** One **single serialized bank port** behind a bank arbiter; all three
sources (local L1 fills, remote NoC requests, memory-tap fills/write-backs) queue. Service/queue order is
**⚠ not specified in WP**.

**R3 — Fill / dirty-data path: bank first, tap on bank miss.** `DIR_MEM_WAIT` reads the L2 data array
first and reads the tap only on a bank miss; `PUTM`/`DATAFWD` write the bank (dirty lives in the bank);
`DIR_EVICT/WRITE_BACK` writes bank → tap; in `DIR_M` the owner's L1 is authoritative and the bank copy is
stale (§3.2 inclusion policy). This is the only reading under which §3.2, §3.9 and Appendix B are all
simultaneously true.

**R4 — Tap is not on the NoC datapath.** `NIC ↔ router` connect **directly**; the memory tap connects only
to the L2 controller (fill / write-back). The legacy §3.9/§3.1 sentence "also passes non-memory packets to
and from the NIC" is treated as superseded wording and is flagged ⚠ wherever the tap appears.

R1–R4 are now normative in the white paper at §3.12 ("Resolved ambiguities"); this file and the WP agree.

## Diagram index

| ID | Title | Level |
|---|---|---|
| HLD-1 | 4×4 mesh system | HLD |
| HLD-2 | CPU tile internal blocks and datapaths | HLD |
| HLD-3 | DMA device tile variant [gated] | HLD |
| HLD-4 | Message / class / VC plane | HLD |
| HLD-5 | Verification environment | HLD |
| LLD-1 | Router microarchitecture (RC/VA/SA/ST, credits, arbitration) | LLD |
| LLD-2 | L1 MESI controller FSM | LLD |
| LLD-3 | Directory controller FSM + DTR | LLD |
| LLD-4 | NIC datapath | LLD |
| LLD-5 | Intra-tile request path and L2 bank access | LLD |
| LLD-6 | Memory tap | LLD |
| LLD-7 | Address decode and stored-tag decomposition (4×4) | LLD |
| LLD-8 | Header flit map and packet framing | LLD |

---

# HLD-1: 4×4 Mesh System

```mermaid
flowchart TB
    subgraph MESH["4x4 2D mesh - 16 identical CPU tiles (WP 3.1, 3.5)"]
        direction TB
        subgraph ROW0["mesh row Y0"]
            direction LR
            P00["position 0,0<br/>CPU tile<br/>3 active ports"] ~~~ P01["position 1,0<br/>CPU tile<br/>5-port router"] ~~~ P02["position 2,0<br/>CPU tile<br/>5-port router"] ~~~ P03["position 3,0<br/>CPU tile<br/>3 active ports"]
        end
        subgraph ROW1["mesh row Y1"]
            direction LR
            P10["position 0,1<br/>CPU tile<br/>4 active ports"] ~~~ P11["position 1,1<br/>CPU tile<br/>5 ports active"] ~~~ P12["position 2,1<br/>CPU tile<br/>5 ports active"] ~~~ P13["position 3,1<br/>CPU tile<br/>4 active ports"]
        end
        subgraph ROW2["mesh row Y2"]
            direction LR
            P20["position 0,2<br/>CPU tile<br/>4 active ports"] ~~~ P21["position 1,2<br/>CPU tile<br/>5 ports active"] ~~~ P22["position 2,2<br/>CPU tile<br/>5 ports active"] ~~~ P23["position 3,2<br/>CPU tile<br/>4 active ports"]
        end
        subgraph ROW3["mesh row Y3"]
            direction LR
            P30["position 0,3<br/>CPU tile<br/>3 active ports"] ~~~ P31["position 1,3<br/>CPU tile<br/>5-port router"] ~~~ P32["position 2,3<br/>CPU tile<br/>5-port router"] ~~~ P33["position 3,3<br/>CPU tile<br/>3 active ports"]
        end
        P00 <--> P01
        P01 <--> P02
        P02 <--> P03
        P10 <--> P11
        P11 <--> P12
        P12 <--> P13
        P20 <--> P21
        P21 <--> P22
        P22 <--> P23
        P30 <--> P31
        P31 <--> P32
        P32 <--> P33
        P00 <--> P10
        P01 <--> P11
        P02 <--> P12
        P03 <--> P13
        P10 <--> P20
        P11 <--> P21
        P12 <--> P22
        P13 <--> P23
        P20 <--> P30
        P21 <--> P31
        P22 <--> P32
        P23 <--> P33
    end
    NOTE1["One 5-port router module (LOCAL, N, S, E, W) at every position.<br/>Unused edge and corner ports are tied off and pruned by synthesis - WP 3.5."]
    NOTE2["XY deterministic routing, X first then Y.<br/>VC assigned at source NIC, never changed by any router - WP 3.5, 4.6 Layer 1."]
    NOTE3["Tile IDs in flit headers are logical (8-bit field).<br/>Tile-ID to mesh-position mapping: tile T at (X,Y) sits at mesh row Y, column X;<br/>X = 0 at the west edge, Y = 0 at the south edge; TILE_ID = N*X + Y - WP 3.6."]
    NOTE4["DMA variant [gated]: one position becomes a DMA device tile<br/>(no L2 bank, no directory, no tap) - its home code is reserved - WP 3.6, 3.11."]
    MESH --- NOTE1
    MESH --- NOTE2
    MESH --- NOTE3
    MESH --- NOTE4
```

---

# HLD-2: CPU Tile Internal Blocks and Datapaths

The tile contains the eight blocks of §3.1. The four diagram rulings (R1–R4) are drawn explicitly.

```mermaid
flowchart TB
    CORE["1 Core / stimulus interface<br/>master port: load / store / flush<br/>no fence or atomic opcode"]
    L1["2 L1 cache - private<br/>4 sets x 4 ways x 64 B = 1 KB<br/>write-back write-allocate, tree-PLRU 3 b/set, MESI per line"]
    MUX["8 Intra-tile mux<br/>routes local vs remote requests<br/>routes incoming packets by message type"]
    NIC["5 NIC<br/>packetisation, class to VC assignment,<br/>TX/RX FIFOs, credit management"]
    ROUTER["6 Router - one 5-port module<br/>LOCAL, N, S, E, W - 4 VCs per port - 4-stage RC/VA/SA/ST"]
    DIR["Directory / L2 controller + DTR<br/>one outstanding transaction per bank - WP 3.7"]
    DARR["4 Directory array - separate from data and tag arrays<br/>32 entries x 24 b used, padded to 32 b"]
    BANK["3 L2 data bank - shared distributed<br/>8 sets x 4 ways x 64 B = 2 KB, tree-PLRU 3 b/set"]
    TAP["7 Memory tap - behavioural backing store<br/>256 MB home slice, 1 cycle, one per CPU tile"]

    CORE --> L1
    L1 --> MUX
    MUX -->|"local home: addr 14:11 equals tile id<br/>direct path, no NoC traversal - ruling R1"| DIR
    MUX -->|"remote home: off-tile request"| NIC
    NIC -->|"remote REQ / UNBLOCK / INVACK / DATAFWD<br/>destined to this tile as home"| DIR
    NIC -->|"INV, FWD_GETS, FWD_GETM, DATA, PUTACK<br/>destined to this tile as holder"| L1
    DIR <--> DARR
    DIR -->|"single serialized bank port - ruling R2<br/>fills, remote requests, tap traffic all queue"| BANK
    DIR -->|"read on bank miss during DIR_MEM_WAIT;<br/>write on DIR_EVICT WRITE_BACK - ruling R3"| TAP
    NIC <-->|"direct connection - ruling R4<br/>tap is not a pass-through on this path"| ROUTER
    ROUTER <-->|"N port"| WN["north mesh link"]
    ROUTER <-->|"E port"| WE["east mesh link"]
    ROUTER <-->|"S port"| WS["south mesh link"]
    ROUTER <-->|"W port"| WW["west mesh link"]
    BANK -.->|"PUTM / DATAFWD dirty data written into the bank<br/>dirty line lives in the owner L1 while DIR_M,<br/>bank copy is stale - WP 3.2 inclusion policy"| DIR
    BANK -.->|"cold miss: bank tag miss during DIR_MEM_WAIT<br/>then the tap supplies the line - ruling R3"| TAP
```

---

# HLD-3: DMA Device Tile Variant [gated] (§3.11, §3.1)

A structural **variant**, not an identical tile: a consumer of coherence, not a provider.

```mermaid
flowchart LR
    subgraph DMA_TILE["DMA device tile - gated at Week 8 (WP 3.11)"]
        ENGINE["DMA engine - two channels"]
        REGS["Memory-mapped register file<br/>per channel: SRC_LO 0x00, DST_LO 0x04, LEN 0x08 (must be 64),<br/>CTRL 0x0C, STATUS 0x10, COUNT 0x14"]
        L1L["L1-lite cache<br/>2 sets x 2 ways x 64 B"]
        DNIC["NIC - same class to VC mapping as CPU tiles"]
        DROUTER["Router - same 5-port module"]
        ENGINE --> REGS --> L1L --> DNIC --> DROUTER
    end
    MESH_LINK["Mesh link to the rest of the 4x4 fabric"]
    DROUTER <--> MESH_LINK
    ABSENT["ABSENT by construction:<br/>no L2 bank, no directory, no memory tap"]
    MSGS["Messages [gated]:<br/>DMA_WRITE code 1100, REQ, VC0, 9 flits (write with inline data)<br/>DMA_ACK code 1101, RESP, VC2, 1 flit<br/>DMA_READ is NOT DEFINED - a DMA read is a GETS issued by the L1-lite,<br/>distinguished only by the source tile ID - WP 3.3"]
    SLOTS["Tile-slot cost at 4x4: 15 CPU tiles + 1 DMA tile = 15 L2 banks = 30 KB.<br/>16-bit sharer vector exactly saturated (15 CPU L1s + 1 DMA L1-lite).<br/>The DMA slot's home-tile code is reserved / unmapped - assertion A8.4."]
    DMA_TILE --- MSGS
    DMA_TILE --- SLOTS
    ABSENT -.-> DMA_TILE
```

---

# HLD-4: Message / Class / VC Plane (§3.3, §3.5, §4.5, §4.6)

```mermaid
flowchart LR
    subgraph CLS["Four message classes to four virtual channels - VC count frozen at 4"]
        direction TB
        VC0["VC0 - REQ<br/>GETS 0000, GETM 0001, PUTS 0010, PUTM 0011<br/>[gated] DMA_WRITE 1100<br/>1 flit, except PUTM = 9 flits"]
        VC1["VC1 - FWD<br/>FWD_GETS 1000, FWD_GETM 1001<br/>1 flit each"]
        VC2["VC2 - RESP<br/>DATA 0111 (9), DATAFWD 1010 (9), INVACK 0110,<br/>UNBLOCK 0100, PUTACK 1011<br/>[gated] DMA_ACK 1101<br/>1 flit, except DATA and DATAFWD = 9"]
        VC3["VC3 - INV<br/>INV 0101<br/>1 flit"]
    end
    FIFO["Per-port FIFO: depth 4 flits per VC.<br/>Credit-based flow control: 4-bit credit counter initialised to 4."]
    PRIO["Arbitration priority within an input port:<br/>RESP greater than INV greater than FWD greater than REQ,<br/>overridden by the age escape: waited at least 8 rounds, grant next."]
    RANK["Deadlock rank (Layer 2, WP 4.6): REQ 0, FWD 1, INV 2, RESP 3.<br/>Every inter-class causal edge ascends; RESP is terminal.<br/>UNBLOCK and PUTACK ride VC2 because they are causally downstream of DATA / PUT.<br/>INVACK rides VC2 although caused by INV(VC3) - the INV to INVACK case is exactly why<br/>the naive lower-numbered-VC rule is not used."]
    RESV["Codes 1110 and 1111 reserved - not decoded by any RTL."]
    CLS --- FIFO
    CLS --- PRIO
    CLS --- RANK
    CLS --- RESV
```

---

# HLD-5: Verification Environment (§5)

```mermaid
flowchart TB
    DUT["DUT: 4x4 mesh RTL (simulation)<br/>2x2 mesh RTL (formal and FPGA)"]
    subgraph SIM["Simulation - Verilator + pyuvm / cocotb"]
        direction TB
        TEST["Test - top-level stimulus, directed 1-17 (+18-22 gated)"]
        ENV["Environment"]
        AGENT["Agent per tile: driver, monitor, sequencer"]
        RMODEL["Reference model - TRANSACTION-level Python MESI model<br/>shadow L1 / L2 / directory / address to data map / outstanding set<br/>computes state AND data after each transaction"]
        SCORE["Scoreboard - compares after every transaction:<br/>L1 state, L1 data, L2 state, L2 data, dir state, dir owner,<br/>dir sharers, memory contents"]
        COV["Coverage collector - numeric closure: 100 percent legal bins,<br/>100 percent FSM states and transitions, 98 percent line / branch,<br/>95 percent toggle, 238 state x message cross terms"]
        TEST --> ENV --> AGENT --> SCORE
        RMODEL --> SCORE
        COV --> SCORE
    end
    subgraph SVA["SVA simulation - Vivado xsim, bind"]
        direction TB
        BIND["42 assertions bound via bind - non-invasive"]
        CATS["A1 MESI invariants 5, A2 directory 7, A3 message protocol 6,<br/>A4 flow control 8, A5 bounded liveness 4, A6 data integrity 4,<br/>A7 FSM legality 4, A8 address and routing 4"]
        BIND --- CATS
    end
    subgraph FORMAL["Formal - Yosys / SymbiYosys on the 2x2 model"]
        direction TB
        BMC["Safety: BMC, depth K = 64, plus mode prove k-induction<br/>A1, A2, A3, A4, A6, A7, A8"]
        LIVE["Bounded liveness with derived bound T = 64 cycles,<br/>under Premise F: no orphan transient, no message loss,<br/>bounded service within 8 arbitration rounds"]
        DEAD["Deadlock lemma of WP 4.6, premises confirmed by k-induction at k = 16"]
        INV["Formal-only network invariants I1 to I7 - not part of the 42<br/>XY path, VC equals class, credit invariant, no send at zero credit,<br/>per-VC FIFO order, delivery or termination,<br/>VC preservation - no router rewrites the header VC, inter-class edge ascent"]
        BMC --- LIVE
        DEAD --- INV
    end
    CI["CI: GitHub Actions, all toolchains pinned<br/>directed + random + bound SVA + formal on every commit"]
    DUT --> SIM
    DUT --> SVA
    DUT --> FORMAL
    SIM --- CI
    SVA --- CI
    FORMAL --- CI
```

---

# LLD-1: Router Microarchitecture (§3.5, §4.6)

```mermaid
flowchart LR
    subgraph IN["Input side - 5 ports: LOCAL, N, S, E, W"]
        direction TB
        FIFOS["Per port, per VC input FIFO<br/>4 ports x 4 VCs x 4 flits x 64 b = 5120 b = 640 B per router"]
        CREDIT_IN["Credit counter per VC: 4 bit, init = downstream FIFO depth 4.<br/>Transmit only when credit available; credit returns when downstream FIFO advances."]
        FIFOS --- CREDIT_IN
    end
    RC["Stage 1 RC - route compute<br/>XY: X first then Y, no Y to X turn<br/>reads header dest field 63:56"]
    VA["Stage 2 VA - VC allocation<br/>VC index taken from header 43:42, never rewritten<br/>VC preservation keeps per-VC channel sets disjoint"]
    SA["Stage 3 SA - two-level switch arbitration<br/>Level 1 per input VC: fixed class priority RESP greater than INV greater than FWD greater than REQ,<br/>age escape - a VC waiting at least 8 rounds is granted next<br/>Level 2 per output port: round-robin across input ports"]
    ST["Stage 4 ST - switch traversal through 5x5 crossbar<br/>4 cycles of hop latency per router"]
    subgraph OUT["Output side"]
        direction TB
        XBAR["Wormhole: header reserves the path, body flits follow,<br/>output released when the header LEN count completes"]
        CREDIT_OUT["Credit return to upstream router"]
        XBAR --- CREDIT_OUT
    end
    IN --> RC --> VA --> SA --> ST --> OUT
    TIE["Unused edge and corner ports tied off;<br/>synthesis prunes the tied-off logic."]
    DEADLOCK["Deadlock freedom does not depend on the arbiter.<br/>Layer 1: XY plus VC preservation, acyclic CDG per VC."]
    IN --- TIE
    SA --- DEADLOCK
```

---

# LLD-2: L1 MESI Controller FSM (Appendix A)

```mermaid
stateDiagram-v2
    direction TB
    [*] --> I
    I --> IS_D : Load miss, send GETS on VC0
    IS_D --> S : DATA shared, install, send UNBLOCK on VC2
    IS_D --> E : DATA exclusive, install, send UNBLOCK on VC2
    I --> IM_D : Store miss, send GETM on VC0
    IM_D --> M : DATA exclusive, install, write, send UNBLOCK on VC2
    S --> SM_D : Store hit, send GETM on VC0
    SM_D --> M : DATA exclusive, write store data, send UNBLOCK on VC2
    E --> M : Store hit, silent upgrade, no message, L1 authoritative for E vs M
    M --> MI_A : Eviction, send PUTM on VC0, 9 flits with dirty line
    MI_A --> I : PUTACK, release the way
    E --> EI_A : Eviction, send PUTS on VC0, 1 flit, no data
    EI_A --> I : PUTACK, release the way
    S --> I : Eviction, send PUTS on VC0, 1 flit, NOT silent
    S --> I : INV received, send INVACK on VC2
    E --> I : INV received, send INVACK on VC2
    M --> I : INV received, send PUTM dirty data then INVACK on VC2
    I --> I : INV received, send INVACK on VC2, defensive, covers evict during invalidate
    E --> S : FWD_GETS received on VC1, send DATAFWD clean, downgrade E to S, owner becomes a sharer, rule 8
    M --> S : FWD_GETS received on VC1, send DATAFWD dirty, downgrade M to S, owner becomes a sharer, rule 8
    E --> I : FWD_GETM received on VC1, send DATAFWD clean, downgrade to I, ownership transfer, rule 8
    M --> I : FWD_GETM received on VC1, send DATAFWD dirty, downgrade to I, ownership transfer, rule 8
    I --> I : FWD received on VC1, send INVACK on VC2, defensive, covers evict during forward, N5
    EI_A --> EI_A : FWD received on VC1, send INVACK on VC2, defensive, owner already released the line, N12
    MI_A --> MI_A : FWD received on VC1, send INVACK on VC2, defensive, owner already sent PUTM, N12
    note right of SM_D
        SM_D exits on DATA alone. INVACKs go to the directory
        and never reach the requester, so they cannot be an
        exit condition here. The SM-D to INV race is closed at
        source by rule 3, INV excludes the requester.
    end note
    note right of I
        Premise R, receptivity, applies in every state including
        transients: INV, DATA, INVACK or FWD for a DIFFERENT line is
        serviced immediately on a path independent of the miss
        path and does not disturb the outstanding miss.
        At most one outstanding miss per L1, MSHRs are future scope.
    end note
    note left of MI_A
        Any transient: timeout greater than T is an error,
        assertion A5, directed test 17, orphan-transient
        detection. T = 150 cycles at 4x4 in regression.
    end note
```

---

# LLD-3: Directory Controller FSM + DTR (Appendix B, §3.3, §3.7)

The 3-bit SRAM state field holds exactly 8 codes. Eviction sub-states and the GETS/GETM discriminator
live in the per-bank **DTR**, not in the SRAM entry. Every transient has **exactly one exit event**.

```mermaid
stateDiagram-v2
    direction TB
    [*] --> DIR_I
    DIR_I --> DIR_MEM_WAIT : GETS, set pending_op GETS, fetch, bank first then tap on miss
    DIR_I --> DIR_MEM_WAIT : GETM, set pending_op GETM, fetch, bank first then tap on miss
    DIR_MEM_WAIT --> DIR_MEM_WAIT : MEM_DATA, send DATA to requester, no state change
    DIR_MEM_WAIT --> DIR_E : UNBLOCK with pending_op GETS, sole clean grant enables silent upgrade
    DIR_MEM_WAIT --> DIR_M : UNBLOCK with pending_op GETM
    DIR_S --> DIR_S : GETS, reply DATA from bank, add sharer, no transient
    DIR_S --> DIR_INV_WAIT : GETM from T, clear T bit, send INV to sharers except T
    DIR_INV_WAIT --> DIR_INV_WAIT : INVACK, clear that sharer bit, idempotent
    DIR_INV_WAIT --> DIR_INV_WAIT : late PUTS from an already INVed tile, bit already clear
    DIR_INV_WAIT --> DIR_INV_WAIT : Sharers equal 0, send DATA exclusive to requester, no state change
    DIR_INV_WAIT --> DIR_M : UNBLOCK with owner T, sole exit event
    DIR_E --> DIR_E : GETS from owner, reply DATA from the home bank
    DIR_E --> DIR_FWD_WAIT : GETS from other, set pending_op GETS, send FWD_GETS; old owner downgrades E/M to S
    DIR_E --> DIR_FWD_WAIT : GETM from other, set pending_op GETM, send FWD_GETM; old owner downgrades to I
    DIR_E --> DIR_I : PUTS from owner, clear Owner, send PUTACK
    DIR_E --> DIR_I : PUTM from owner (silent-upgrade eviction), write data into bank, clear Owner, send PUTACK
    DIR_M --> DIR_M : GETS from owner, reply DATA, owner is authoritative
    DIR_M --> DIR_FWD_WAIT : GETS from other, set pending_op GETS, send FWD_GETS; old owner downgrades M to S
    DIR_M --> DIR_FWD_WAIT : GETM from other, set pending_op GETM, send FWD_GETM; old owner downgrades to I
    DIR_M --> DIR_I : PUTM from owner, write data into bank, clear Owner, send PUTACK
    DIR_FWD_WAIT --> DIR_FWD_WAIT : DATAFWD, write dirty data into the bank, send DATA to requester
    DIR_FWD_WAIT --> DIR_FWD_WAIT : PUTM from owner, satisfies the forward, write bank, set dirty, clear old owner bit, send PUTACK, N12
    DIR_FWD_WAIT --> DIR_FWD_WAIT : PUTS from owner, cancel the forward, bank holds the current value, serve requester from bank, send PUTACK, N12
    DIR_FWD_WAIT --> DIR_FWD_WAIT : INVACK defensive, duplicate release, ignore, no state change, N12
    DIR_FWD_WAIT --> DIR_S : UNBLOCK with pending_op GETS
    DIR_FWD_WAIT --> DIR_M : UNBLOCK with pending_op GETM
    DIR_S --> DIR_S : PUTS from a sharer, clear that bit, send PUTACK
    DIR_S --> DIR_I : PUTS from the last sharer, send PUTACK
    state DIR_EVICT {
        state "victim shared, INV to sharers" as INV_SHARERS
        state "victim owned, INV to owner" as RECALL_OWNER
        state "victim dirty, bank to tap" as WRITE_BACK
        INV_SHARERS --> INV_SHARERS : INVACK, clear that sharer bit
        INV_SHARERS --> WRITE_BACK : final INVACK, victim dirty
        INV_SHARERS --> DIR_MEM_WAIT : final INVACK, victim clean, resolved
        RECALL_OWNER --> WRITE_BACK : PUTM plus INVACK from owner, victim dirty
        RECALL_OWNER --> DIR_MEM_WAIT : final INVACK, victim clean, resolved
        WRITE_BACK --> DIR_MEM_WAIT : bank to tap write committed, proceed with the pending fill
    }
    state "entered from ANY state when a fill requires a victim way" as VictimNeeded
    VictimNeeded --> DIR_EVICT : enter, sub-state chosen by victim directory state (INV_SHARERS if shared, RECALL_OWNER if owned, WRITE_BACK if DIR_I with a dirty bank line, N4)
    note right of DIR_EVICT
        Eviction sub-states NONE, INV_SHARERS, RECALL_OWNER,
        WRITE_BACK are held in the DTR 2-bit field, together
        with evict victim and victim dirty. The 3-bit SRAM
        state field has zero encoding headroom.
    end note
    note left of DIR_FWD_WAIT
        DIR-FWD-WAIT with UNBLOCK has two legal successors;
        DTR pending_op selects DIR-S for GETS or DIR-M for GETM,
        so the transition function is a function.
        Single-exit rule: MEM_DATA, DATAFWD, INVACK and PUTM
        advance DTR progress only and never change the SRAM
        state field on their own.
    end note
```

---

# LLD-4: NIC Datapath (§3.1, §3.3, §3.5, §3.8)

```mermaid
flowchart LR
    subgraph TX["Transmit path"]
        direction TB
        REQ_IN["Requests from local L1 or DMA L1-lite<br/>GETS, GETM, PUTS, PUTM, UNBLOCK, INVACK, DATAFWD"]
        PKT["Packetiser: build header flit<br/>dest 63:56, src 55:48, msg 47:44, VC 43:42, head 41, tail 40,<br/>WE 39, exclusive 38, LEN 37:32, address 31:0"]
        C2VC["Class to VC assignment at the source - never changed downstream<br/>REQ to VC0, FWD to VC1, RESP to VC2, INV to VC3"]
        TXF["TX FIFO, depth 4 per VC<br/>LEN set to 1 for control, 9 for PUTM"]
        CRED["Credit gate: send only when a credit for the downstream<br/>FIFO of the chosen VC is available"]
        REQ_IN --> PKT --> C2VC --> TXF --> CRED
    end
    LOC["Router LOCAL port"]
    subgraph RX["Receive path"]
        direction TB
        RXF["RX FIFO, depth 4 per VC"]
        DEC["Message type decoder 47:44"]
        TO_DIR["To local L2 directory controller<br/>GETS, GETM, PUTS, PUTM, UNBLOCK, INVACK, DATAFWD<br/>these are the messages whose direction is to the home directory"]
        TO_L1["To local L1 or DMA register file<br/>INV, FWD_GETS, FWD_GETM, DATA, PUTACK, DMA_ACK<br/>these are the messages whose direction is to a holder"]
        RXF --> DEC
        DEC --> TO_DIR
        DEC --> TO_L1
    end
    CRED --> LOC
    LOC --> RXF
    TO_DIR --> MUX_OUT["Intra-tile mux, message-type routing"]
    TO_L1 --> MUX_OUT
    CHK["Checked field: header VC 43:42 must equal class of msg 47:44.<br/>Asserted by the NIC and by formal invariant I3.<br/>Never used as a routing input."]
    LEN["Wormhole framing: the router counts flits against header LEN 37:32<br/>and releases the output when the count completes.<br/>Body flits are pure payload, no control bits."]
    LOC --- CHK
    LOC --- LEN
```

---

# LLD-5: Intra-tile Request Path and L2 Bank Access (§3.1, §3.7, rulings R1–R3)

```mermaid
flowchart TB
    subgraph SRC["Request sources - all queue, ruling R2"]
        direction LR
        S1["Local L1 miss on a line homed at this tile<br/>arrives via the intra-tile mux, no NoC traversal - R1"]
        S2["Remote NoC request<br/>GETS, GETM, PUTS, PUTM, DMA_WRITE from the NIC RX path"]
        S3["Controller-internal traffic<br/>DIR_MEM_WAIT fill read, DIR-EVICT WRITE_BACK bank to tap"]
    end
    Q["Pending request handling per bank<br/>the queue is the bank's request queue, behind the single serialized L2 port - WP 3.2, 3.7;<br/>queue depth and service order: NOT SPECIFIED IN WP - open item 9, Week 4"]
    ARB["Bank arbiter - single logical access at a time<br/>one outstanding directory transaction per bank - WP 3.7"]
    CTRL["Directory controller + DTR"]
    subgraph ARRAYS["Serialized bank resources"]
        direction TB
        DARR2["Directory array, 32 entries x 24 b used, padded to 32 b"]
        TAGD["L2 tag array, 32 entries x 21 b per-line word<br/>valid + 19 b address tag + dirty"]
        DATAD["L2 data array, 32 lines x 64 B"]
        DARR2 --- TAGD --- DATAD
    end
    TAP2["Memory tap, 1 cycle"]
    S1 --> Q
    S2 --> Q
    S3 --> Q
    Q --> ARB --> CTRL
    CTRL --> ARRAYS
    HITPATH["Bank tag hit: line served from the L2 data array.<br/>PUTM and DATAFWD write dirty data into the bank here."]
    MISSPATH["Bank tag miss during DIR_MEM_WAIT: read the tap,<br/>install the line into the victim way, DIR-EVICT first if the<br/>victim is valid - the fill always installs, otherwise the<br/>inclusion policy of WP 3.2 would be violated."]
    STALE["While DIR_M with a dirty owner, the bank copy is stale:<br/>the owner's L1 is the only current copy - WP 3.2."]
    ARRAYS --- HITPATH
    ARRAYS --- MISSPATH
    TAP2 --- MISSPATH
    TAP2 --- STALE
    CTRL <-->|"DIR-EVICT WRITE_BACK: read bank, write tap - ruling R3"| TAP2
```

---

# LLD-6: Memory Tap (§3.9, ruling R4)

```mermaid
flowchart TB
    subgraph TAP["Memory tap - per CPU tile, not shared, simulation model"]
        direction TB
        MEM["Behavioural backing store<br/>32-bit physical address, 256 MB window at 0x0000_0000, sparse beyond<br/>64 B per line, access latency 1 cycle"]
        RPORT["Fill port: answers cold misses of its own L2 bank<br/>DIR_MEM_WAIT reads the bank first, tap only on bank miss - ruling R3"]
        WPORT["Write-back port: DIR-EVICT WRITE_BACK, bank to tap, 1 cycle"]
        MEM --- RPORT
        MEM --- WPORT
    end
    BANK2["Local L2 bank controller"]
    RPORT <--> BANK2
    WPORT <--> BANK2
    SCOPE["Serves only addresses homed at this tile.<br/>Serves the home slice only. Coherence participation: NONE -<br/>the backing store does not participate, the directory does."]
    REGIONS["Address regions: memory 0x0000_0000 to 0x0FFF_FFFF,<br/>unmapped 0x1000_0000 to 0xEFFF_FFFF caught by A8,<br/>DMA registers 0xF000_0000 to 0xF000_FFFF gated,<br/>test addresses 0xFFFF_FF00 / FF04 / FF08 return DEADBEEF / the address / a counter."]
    WARN["NOT SPECIFIED IN WP, flagged per ruling R4:<br/>the legacy sentence that the tap also passes non-memory packets<br/>to and from the NIC is treated as superseded wording.<br/>The NIC connects directly to the router LOCAL port instead."]
    NOTMODEL["Not modelled, future scope: DRAM timing, ECC, refresh,<br/>bank interleaving, prefetch. Replaced by a real controller per WP 9."]
    TAP --- SCOPE
    TAP --- REGIONS
    TAP --- WARN
    TAP --- NOTMODEL
```

---

# LLD-7: Address Decode and Stored-Tag Decomposition, 4×4 (§3.6)

```mermaid
flowchart TB
    subgraph ADDR["Physical address 31:0 - 4x4 configuration"]
        direction LR
        B1["31:15 - L2 tag field, 17 b"]
        B2["14:11 - home tile X,Y, 4 b"]
        B3["10:8 - L2 set index, 3 b"]
        B4["7:6 - L1 set index, 2 b"]
        B5["5:0 - byte offset, 6 b"]
        B1 --- B2 --- B3 --- B4 --- B5
    end
    DISJ["The L1 set index 7:6 and the L2 set index 10:8 are DISJOINT - hard requirement.<br/>With an overlapping layout only 2 of 8 L2 sets are reachable per L1 set,<br/>so one L1 set would be backed by 512 B, less than the 1 KB L1 itself."]
    subgraph STORED["Stored tag widths"]
        direction TB
        L1T["L1, every tile: index 7:6, stored tag addr 31:8 = 24 b"]
        L2T["L2, per bank: index 10:8, home bits constant per bank and excluded.<br/>Address tag = addr 31:15 concatenated with addr 7:6 = 19 b, NON-CONTIGUOUS.<br/>per-line word = valid + 19 b address tag + dirty = 21 b.<br/>The 7:6 bits must be compared: storing 31:15 alone would alias lines<br/>differing only in 7:6 into the same way.<br/>valid distinguishes an empty way from a resident line - an empty all-zero tag<br/>would otherwise alias the line at address 0; dirty = bank copy newer than the tap.<br/>valid and dirty are state, not identity: excluded from the tag comparison."]
        L1T --- L2T
    end
    HOME["Home decode is closed-form, zero logic, contiguous address slice per tile.<br/>The bit order of X and Y inside the 4-bit home field is SPECIFIED: {X,Y} with X in the<br/>higher-order bits, so TILE_ID = 4*X + Y equals addr 14:11 directly - WP 3.6, WP 13 item Y."]
    SCALE["Full-map sharer vector: 1 bit per tile, so 24 b used at 16 tiles, 74 b at 64 tiles.<br/>A flat single-level directory is optimal only up to 16 tiles: N is bounded at 16.<br/>The 8-bit tile-ID fields do not extend that bound."]
    DMARES["DMA-enabled build: the DMA slot has no directory, so its home code is<br/>reserved and unmapped. Requests decoding to it are a protocol error, A8.4.<br/>Costs 1/16 of the decode space."]
    ADDR --- DISJ
    STORED --- HOME
    STORED --- SCALE
    STORED --- DMARES
```

---

# LLD-8: Header Flit Map and Packet Framing (§3.8, Appendix C)

```mermaid
flowchart TB
    subgraph HDR["Header flit, 64 bits"]
        direction TB
        F1["63:56 - dest tile, 8 b, logical TILE_ID_W, unused high bits zero"]
        F2["55:48 - src tile, 8 b"]
        F3["47:44 - msg type, 4 b, 12 core codes plus 2 gated, 1110 and 1111 reserved"]
        F4["43:42 - VC ID, 2 b, CHECKED field, must equal class of msg, never a routing input"]
        F5["41 - head, 40 - tail, set only on single-flit packets"]
        F6["39 - write enable, 38 - exclusive indication"]
        F7["37:32 - LEN, 6 b, total flits in the packet, 1 to 63"]
        F8["31:0 - address, line address of the transaction"]
        F1 --- F2 --- F3 --- F4 --- F5 --- F6 --- F7 --- F8
    end
    BODY["Body flit: 64 bits of pure payload, no control bits.<br/>The packet is delimited by the header LEN count, so body flits keep<br/>100 percent payload bandwidth."]
    SIZES["Packet sizes: control = 1 flit, GETS, GETM, PUTS, UNBLOCK, INV, INVACK,<br/>FWD-GETS, FWD-GETM, PUTACK, DMA-ACK.<br/>Cache line = 9 flits, PUTM, DATA, DATAFWD, DMA-WRITE.<br/>All coherence transfers are single-cache-line granularity."]
    HDR --- BODY
    HDR --- SIZES
```

---

*End of 4×4 architecture diagram set. Every ⚠ marker corresponds to a genuine gap in the white paper and
was deliberately not filled in.*
