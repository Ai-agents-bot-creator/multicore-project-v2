# HLD / LLD — 2x2 Implementation (FPGA)

**Source of truth:** `whitepaper_v3.0.md` (v3.0, Unified Final). Implementation-focused pair for the presentation.

| # | Diagram | Level |
|---|---|---|
| HLD | 2x2 mesh on the committed implementation target (ZedBoard XC7Z020 / `fpga_top`) | HLD |
| LLD | Per-tile internal coherence datapath (MESI, L2 bank, memory tap, rulings R1-R4) | LLD |

Companion sets: `HLD_LLD_4x4_architecture.md` (microarchitecture) and `HLD_LLD_2x2_FPGA.md` (full 2x2 set).

---

## Diagram 1 — HLD: 2x2 mesh on the implementation target

```mermaid
flowchart TB
    subgraph SOC["ZedBoard - fpga_top - device XC7Z020-CLG484-1"]
        direction TB
        subgraph MESH["2x2 mesh - committed FPGA and formal configuration"]
            direction TB
            subgraph ROW0["mesh row Y0"]
                direction LR
                T00["tile 0,0<br/>corner<br/>3 active ports"]
                T01["tile 1,0<br/>corner<br/>3 active ports"]
            end
            subgraph ROW1["mesh row Y1"]
                direction LR
                T10["tile 0,1<br/>corner<br/>3 active ports"]
                T11["tile 1,1<br/>corner<br/>3 active ports"]
            end
            T00 --- T01
            T10 --- T11
            T00 --- T10
            T01 --- T11
        end
        HOP["worst-case Manhattan distance 2 hops<br/>router pipeline 4 cycles per hop<br/>formal bound T = 64 cycles at 2x2"]
        COV["2x2 formal scope: multi-sharer fan-out covered (2 sharers + 1 requester)<br/>interior 5-port router and 3+ sharers at distinct homes deferred to 4x4 campaign"]
    end
```

---

## Diagram 2 — LLD: per-tile coherence datapath

```mermaid
flowchart TB
    CORE["Core / stimulus interface<br/>master port: load / store / flush"]
    L1["L1 cache - private<br/>4 sets x 4 ways x 64 B = 1 KB<br/>MESI + tree-PLRU, write-back / write-allocate"]
    MUX["Intra-tile mux"]
    NIC["NIC"]
    ROUTER["Router - 5-port module<br/>4 stages RC / VA / SA / ST, 4 VCs per port"]
    CTRL["Directory controller + DTR"]
    DARR["Directory array - full map, one entry per line<br/>10 b used at 2x2 (3 + owner + sharers + valid), padded to 32 b"]
    BANK["L2 data bank - shared<br/>8 sets x 4 ways x 64 B = 2 KB"]
    TAP["Memory tap - behavioural backing store, 1 cycle"]

    CORE --> L1
    L1 --> MUX
    MUX -->|"local home: direct to local L2, no NoC - R1"| CTRL
    MUX -->|"remote home: off-tile request"| NIC
    NIC -->|"to this tile as home"| CTRL
    NIC -->|"to this tile as holder"| L1
    CTRL -->|"directory state / DTR"| DARR
    CTRL -->|"single serialized bank port - R2"| BANK
    CTRL -->|"bank first, tap on bank miss - R3"| TAP
    BANK -.->|"PUTM / DATAFWD dirty data into bank - R3"| CTRL
    BANK -.->|"DIR_EVICT / WRITE_BACK bank to tap - R3"| TAP
    NIC -.->|"direct to router LOCAL port - R4"| ROUTER
```

*R1-R4 are the adjudicated rulings of WP section 3.12. Items marked not specified in the WP are shown, never invented.*

---

*End of 2x2 implementation presentation diagram pair. shortcut: PPT pair carries only the HLD mesh+FPGA and the LLD intra-tile datapath; resource budget, formal engine detail and FSM views live in the companion files — upgrade path: re-add from `HLD_LLD_2x2_FPGA.md` when the deck widens.*
