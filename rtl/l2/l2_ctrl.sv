// l2_ctrl.sv — L2 bank controller + Directory Transaction Record (DTR)
// §16.3 (N3a, N13): bank access port and arbitration
// §3.7: DTR — one outstanding transaction per bank, 5 pending_op codes
// WP §3.2: "single serialized access port; service order not fixed"
// Spec: WP §3.2, §3.7, WORK_BREAKDOWN_16.md §16.3, §16.5

`include "tile_pkg.sv"

module l2_ctrl
  import tile_pkg::*;
(
  input  logic                        clk,
  input  logic                        rst_n,

  // ── Requests from three sources (all go through the serialized bank port) ──
  // 1. Local L1 fill request (from l1_mesi_ctrl)
  input  logic                        l1_req_valid,
  input  logic [ADDR_W-1:0]           l1_req_addr,
  input  logic                        l1_req_we,       // 1 = write-back from L1
  input  logic                        l1_req_dirty,
  input  logic [LINE_BITS-1:0]        l1_req_wdata,
  output logic                        l1_req_ready,
  // Fill data returned to L1 on a hit
  output logic                        l1_resp_hit,
  output logic [LINE_BITS-1:0]        l1_resp_data,

  // 2. Remote (NoC) fill request (from NIC, decoded by dir_ctrl)
  input  logic                        rem_req_valid,
  input  logic [ADDR_W-1:0]           rem_req_addr,
  input  logic                        rem_req_we,
  input  logic                        rem_req_dirty,
  input  logic [LINE_BITS-1:0]        rem_req_wdata,
  output logic                        rem_req_ready,
  output logic                        rem_resp_hit,
  output logic [LINE_BITS-1:0]        rem_resp_data,
  output logic                        rem_resp_dirty, // current dirty bit

  // 3. Memory-tap fill/write-back (from mem_tap)
  input  logic                        tap_req_valid,
  input  logic [ADDR_W-1:0]           tap_req_addr,
  input  logic                        tap_req_we,
  input  logic                        tap_req_dirty,
  input  logic [LINE_BITS-1:0]        tap_req_wdata,
  output logic                        tap_req_ready,

  // ── DTR interface (to dir_ctrl) ───────────────────────────────────────────
  output logic                        dtr_busy,       // 1 = transaction in flight
  output pending_op_t                 dtr_pending_op, // current pending op code
  output logic [ADDR_W-1:0]           dtr_addr,       // address of pending transaction
  input  logic                        dtr_set_valid,  // dir_ctrl sets DTR
  input  pending_op_t                 dtr_set_op,
  input  logic [ADDR_W-1:0]           dtr_set_addr,
  input  logic                        dtr_clear,      // dir_ctrl clears DTR on UNBLOCK

  // ── Victim info (to dir_ctrl, to decide write-back) ──────────────────────
  output logic                        victim_valid,
  output logic                        victim_dirty,
  output logic [L2_ADDR_TAG_W-1:0]   victim_tag,
  output logic [LINE_BITS-1:0]        victim_data
);

  // ─── Arbitration — service order provisional (§12 item 9; BANK_ARB_TAP_FIRST in tile_pkg) ──
  // ponytail: fixed priority; provisional ruling OI-4; adjust when profiling shows starvation.
  typedef enum logic [1:0] {
    SRC_NONE = 2'd0,
    SRC_L1   = 2'd1,
    SRC_REM  = 2'd2,
    SRC_TAP  = 2'd3
  } src_t;

  src_t winner;

  always_comb begin
    if (BANK_ARB_TAP_FIRST) begin
      if (tap_req_valid)      winner = SRC_TAP;
      else if (rem_req_valid) winner = SRC_REM;
      else if (l1_req_valid)  winner = SRC_L1;
      else                    winner = SRC_NONE;
    end else begin
      if (l1_req_valid)       winner = SRC_L1;
      else if (rem_req_valid) winner = SRC_REM;
      else if (tap_req_valid) winner = SRC_TAP;
      else                    winner = SRC_NONE;
    end
  end

  // ─── Mux request to bank ──────────────────────────────────────────────────
  logic                      bank_req_valid;
  logic [ADDR_W-1:0]         bank_req_addr;
  logic                      bank_req_we;
  logic                      bank_req_dirty;
  logic [LINE_BITS-1:0]      bank_req_wdata;
  logic                      bank_req_ready;
  logic                      bank_resp_hit;
  logic [LINE_BITS-1:0]      bank_resp_data;
  logic                      bank_resp_dirty;
  logic [L2_ADDR_TAG_W-1:0]  bank_resp_tag;

  always_comb begin
    case (winner)
      SRC_TAP: begin
        bank_req_valid = tap_req_valid;
        bank_req_addr  = tap_req_addr;
        bank_req_we    = tap_req_we;
        bank_req_dirty = tap_req_dirty;
        bank_req_wdata = tap_req_wdata;
      end
      SRC_REM: begin
        bank_req_valid = rem_req_valid;
        bank_req_addr  = rem_req_addr;
        bank_req_we    = rem_req_we;
        bank_req_dirty = rem_req_dirty;
        bank_req_wdata = rem_req_wdata;
      end
      default: begin // SRC_L1 / SRC_NONE
        bank_req_valid = l1_req_valid;
        bank_req_addr  = l1_req_addr;
        bank_req_we    = l1_req_we;
        bank_req_dirty = l1_req_dirty;
        bank_req_wdata = l1_req_wdata;
      end
    endcase
  end

  // ─── Ready signals: only the winning source gets ready ───────────────────
  assign l1_req_ready  = bank_req_ready && (winner == SRC_L1);
  assign rem_req_ready = bank_req_ready && (winner == SRC_REM);
  assign tap_req_ready = bank_req_ready && (winner == SRC_TAP);

  // ─── Bank instance ────────────────────────────────────────────────────────
  l2_bank u_bank (
    .clk          (clk),
    .rst_n        (rst_n),
    .req_valid    (bank_req_valid),
    .req_ready    (bank_req_ready),
    .req_addr     (bank_req_addr),
    .req_we       (bank_req_we),
    .req_dirty    (bank_req_dirty),
    .req_wdata    (bank_req_wdata),
    .resp_hit     (bank_resp_hit),
    .resp_rdata   (bank_resp_data),
    .resp_dirty   (bank_resp_dirty),
    .resp_tag     (bank_resp_tag),
    .victim_data  (victim_data),
    .victim_dirty (victim_dirty),
    .victim_tag   (victim_tag),
    .victim_valid (victim_valid)
  );

  // ─── Route bank hit response to the right source ──────────────────────────
  assign l1_resp_hit   = bank_resp_hit && (winner == SRC_L1);
  assign l1_resp_data  = bank_resp_data;
  assign rem_resp_hit  = bank_resp_hit && (winner == SRC_REM);
  assign rem_resp_data = bank_resp_data;
  assign rem_resp_dirty = bank_resp_dirty;

  // ─── DTR — one outstanding transaction per bank (§3.7) ───────────────────
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dtr_busy        <= 1'b0;
      dtr_pending_op  <= POP_NONE;
      dtr_addr        <= '0;
    end else begin
      if (dtr_clear) begin
        dtr_busy       <= 1'b0;
        dtr_pending_op <= POP_NONE;
        dtr_addr       <= '0;
      end else if (dtr_set_valid && !dtr_busy) begin
        dtr_busy       <= 1'b1;
        dtr_pending_op <= dtr_set_op;
        dtr_addr       <= dtr_set_addr;
      end
    end
  end

endmodule

