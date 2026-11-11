// tile_pkg.sv — single source of truth for all parameterised widths & encodings
// Derived from: FINAL_whitepaper_v3.0.md §3.2, §3.3, §3.6, §3.8, SPEC_SHEET.md §1–§10
`ifndef TILE_PKG_SV
`define TILE_PKG_SV

package tile_pkg;

  // ──────────────────────────────────────────────
  // Mesh dimension — change this ONE parameter
  // ──────────────────────────────────────────────
  parameter int N = 2;                         // 2 → 2×2 FPGA, 4 → 4×4 sim

  // Derived
  localparam int TILE_COUNT  = N * N;
  localparam int TILE_ID_W   = $clog2(TILE_COUNT);  // 2 (2×2), 4 (4×4)
  localparam int SHARER_W    = TILE_COUNT;

  // ──────────────────────────────────────────────
  // Cache geometry (fixed across configs)
  // ──────────────────────────────────────────────
  localparam int LINE_BYTES  = 64;
  localparam int LINE_BITS   = LINE_BYTES * 8;       // 512
  localparam int ADDR_W      = 32;
  localparam int OFFSET_W    = 6;                    // [5:0]
  localparam int L1_SET_W    = 2;                    // [7:6]
  localparam int L1_SETS     = 4;
  localparam int L1_WAYS     = 4;
  localparam int L2_SET_W    = 3;                    // [10:8]
  localparam int L2_SETS     = 8;
  localparam int L2_WAYS     = 4;
  localparam int L2_LINES    = L2_SETS * L2_WAYS;   // 32

  // Address field positions (§3.6)
  localparam int L1_SET_LO   = 6;
  localparam int L1_SET_HI   = 7;
  localparam int L2_SET_LO   = 8;
  localparam int L2_SET_HI   = 10;
  localparam int HOME_LO     = 11;
  localparam int HOME_HI     = HOME_LO + TILE_ID_W - 1;  // 12 (2×2), 14 (4×4)

  // Stored tags (§3.6 — L2 tag is NON-CONTIGUOUS)
  localparam int L1_TAG_W    = ADDR_W - (L1_SET_HI + 1);   // 24 always: stored tag = addr[31:8]
  // L2 address tag = {addr[31:HOME_HI+1], addr[7:6]}
  localparam int L2_ADDR_TAG_W = (ADDR_W - HOME_HI - 1) + L1_SET_W;
  // L2 per-line word = valid + L2_ADDR_TAG_W + dirty (N3a, N13)
  localparam int L2_LINE_W   = 1 + L2_ADDR_TAG_W + 1;

  // PLRU tree bits per set (4-way)
  localparam int PLRU_BITS   = 3;

  // ──────────────────────────────────────────────
  // Directory entry (§3.2, SPEC_SHEET §4)
  // ──────────────────────────────────────────────
  localparam int DIR_USED_W  = 3 + TILE_ID_W + TILE_COUNT + 1;  // 10 (2×2), 24 (4×4)
  localparam int DIR_ENTRY_W = 32;  // BRAM-aligned

  // Directory state codes (3 bits, §3.3)
  typedef enum logic [2:0] {
    DIR_I         = 3'b000,
    DIR_S         = 3'b001,
    DIR_E         = 3'b010,
    DIR_M         = 3'b011,
    DIR_MEM_WAIT  = 3'b100,
    DIR_FWD_WAIT  = 3'b101,
    DIR_INV_WAIT  = 3'b110,
    DIR_EVICT     = 3'b111
  } dir_state_t;

  // L1 MESI states (4 stable + 5 transient)
  typedef enum logic [3:0] {
    L1_I    = 4'd0,
    L1_S    = 4'd1,
    L1_E    = 4'd2,
    L1_M    = 4'd3,
    L1_IS_D = 4'd4,
    L1_IM_D = 4'd5,
    L1_SM_D = 4'd6,
    L1_EI_A = 4'd7,
    L1_MI_A = 4'd8
  } l1_state_t;

  // ──────────────────────────────────────────────
  // Message types (4 bits, §3.3 / Appendix C)
  // ──────────────────────────────────────────────
  typedef enum logic [3:0] {
    MSG_GETS      = 4'b0000,
    MSG_GETM      = 4'b0001,
    MSG_PUTS      = 4'b0010,
    MSG_PUTM      = 4'b0011,
    MSG_UNBLOCK   = 4'b0100,
    MSG_INV       = 4'b0101,
    MSG_INVACK    = 4'b0110,
    MSG_DATA      = 4'b0111,
    MSG_FWD_GETS  = 4'b1000,
    MSG_FWD_GETM  = 4'b1001,
    MSG_DATAFWD   = 4'b1010,
    MSG_PUTACK    = 4'b1011,
    MSG_DMA_WRITE = 4'b1100,  // gated
    MSG_DMA_ACK   = 4'b1101,  // gated
    MSG_RSVD0     = 4'b1110,
    MSG_RSVD1     = 4'b1111
  } msg_type_t;

  // VC IDs (2 bits, §3.5)
  typedef enum logic [1:0] {
    VC_REQ  = 2'd0,
    VC_FWD  = 2'd1,
    VC_RESP = 2'd2,
    VC_INV  = 2'd3
  } vc_id_t;

  localparam int NUM_VCS     = 4;
  localparam int VC_DEPTH    = 4;   // flits per VC FIFO
  localparam int CREDIT_W    = 4;   // credit counter width (§13 AC)

  // ──────────────────────────────────────────────
  // Flit format (64 bits, §3.8)
  // ──────────────────────────────────────────────
  localparam int FLIT_W      = 64;
  localparam int BODY_FLITS  = 8;   // per cache-line packet
  localparam int LINE_PKT_LEN = 9;  // 1 header + 8 body

  // Header field positions
  localparam int HDR_DEST_HI = 63, HDR_DEST_LO = 56;
  localparam int HDR_SRC_HI  = 55, HDR_SRC_LO  = 48;
  localparam int HDR_MSG_HI  = 47, HDR_MSG_LO  = 44;
  localparam int HDR_VC_HI   = 43, HDR_VC_LO   = 42;
  localparam int HDR_HEAD     = 41;
  localparam int HDR_TAIL     = 40;
  localparam int HDR_WE       = 39;   // write-enable / DATAFWD dirty bit
  localparam int HDR_EXCL     = 38;
  localparam int HDR_LEN_HI  = 37, HDR_LEN_LO  = 32;
  localparam int HDR_ADDR_HI = 31, HDR_ADDR_LO =  0;

  // ──────────────────────────────────────────────
  // Router (§3.5)
  // ──────────────────────────────────────────────
  localparam int NUM_PORTS   = 5;   // LOCAL, N, S, E, W
  typedef enum logic [2:0] {
    PORT_LOCAL = 3'd0,
    PORT_N     = 3'd1,
    PORT_S     = 3'd2,
    PORT_E     = 3'd3,
    PORT_W     = 3'd4
  } port_id_t;

  // Bank arbiter service order (§12 item 9: "not fixed by this specification — R2")
  // ponytail: fixed priority, provisional; change to 0 for local-first if profiling shows starvation
  localparam int BANK_ARB_TAP_FIRST = 1;  // 1 = tap>remote>L1 (default), 0 = L1>remote>tap

  // Age-escape threshold (ruling B1)
  localparam int AGE_THRESH  = 5;
  localparam int AGE_W       = 3;   // counter width (0–5 fits in 3 bits)

  // ──────────────────────────────────────────────
  // DTR (§3.7)
  // ──────────────────────────────────────────────
  typedef enum logic [2:0] {
    POP_NONE = 3'b000,
    POP_GETS = 3'b001,
    POP_GETM = 3'b010,
    POP_PUT  = 3'b011,
    POP_DMA  = 3'b100   // gated, unreachable at 2×2
  } pending_op_t;

  typedef enum logic [1:0] {
    EVICT_NONE          = 2'b00,
    EVICT_INV_SHARERS   = 2'b01,
    EVICT_RECALL_OWNER  = 2'b10,
    EVICT_WRITE_BACK    = 2'b11
  } evict_sub_t;

  // ──────────────────────────────────────────────
  // L2 Bank interface (R3 — frozen port shape)
  // ──────────────────────────────────────────────
  typedef enum logic [1:0] {
    SRC_TAP     = 2'd0,
    SRC_REMOTE  = 2'd1,
    SRC_L1      = 2'd2
  } bank_src_e;

  // req:  valid, is_write, addr[ADDR_W-1:0], wdata[511:0], wstrb[63:0], source : bank_src_e
  // rsp:  valid, rdata[511:0], rstrb[63:0], rlast
  // status: dtr_busy    (one transaction per bank, N4/N5)
  // Note: source_sel is the R2 arbiter input; priority lives in BANK_ARB_TAP_FIRST

  // ──────────────────────────────────────────────
  // Helpers
  // ──────────────────────────────────────────────
  function automatic vc_id_t msg_to_vc(msg_type_t m);
    case (m)
      MSG_GETS, MSG_GETM, MSG_PUTS, MSG_PUTM, MSG_DMA_WRITE: return VC_REQ;
      MSG_FWD_GETS, MSG_FWD_GETM:                             return VC_FWD;
      MSG_UNBLOCK, MSG_INVACK, MSG_DATA, MSG_DATAFWD,
      MSG_PUTACK, MSG_DMA_ACK:                                 return VC_RESP;
      MSG_INV:                                                 return VC_INV;
      default:                                                 return VC_REQ;
    endcase
  endfunction

  function automatic logic [5:0] msg_to_len(msg_type_t m);
    case (m)
      MSG_PUTM, MSG_DATA, MSG_DATAFWD, MSG_DMA_WRITE: return 6'd9;
      default:                                          return 6'd1;
    endcase
  endfunction

endpackage

`endif

