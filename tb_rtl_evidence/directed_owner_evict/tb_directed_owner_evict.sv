`timescale 1ns/1ps
// Plain directed testbench for the owner-evict-during-forward race.
//
// Wiring mirrors tb_rtl_evidence/sby_k64/fml_l1_dir.sv (2x l1_mesi_ctrl +
// merge FIFO + dir_ctrl + demux + L2 bank) with every formal construct
// removed: no assume/assert, no SVA instance, no $error. The a2_2 check is
// done in Python (directed_owner_evict.py).
//
// clk and rst_n are driven by cocotb, not generated here, so there is a
// single driver for each.
module tb_directed_owner_evict import tile_pkg::*; (
    input  logic clk,
    input  logic rst_n,
    input  logic c0v, c0w, c0e,
    input  logic c1v, c1w, c1e,
    input  logic [LINE_BITS-1:0] c0d, c1d
);

  localparam logic [ADDR_W-1:0] LINE = 32'h40;

  logic c0rv, c1rv;
  logic [LINE_BITS-1:0] c0rd, c1rd;

  // ---- L1 #0 / #1 -------------------------------------------------------
  logic l1_0_req_valid, l1_1_req_valid;
  logic [FLIT_W-1:0] l1_0_req_flit, l1_1_req_flit;
  logic l1_0_rsp_valid, l1_1_rsp_valid;
  logic [FLIT_W-1:0] l1_0_rsp_flit, l1_1_rsp_flit;
  l1_state_t l1_0_state, l1_1_state;
  logic l1_0_dispatch, l1_1_dispatch;
  msg_type_t l1_0_rx_msg, l1_1_rx_msg;

  l1_mesi_ctrl l1_0 (
    .clk(clk), .rst_n(rst_n), .tile_id(2'd0),
    .core_req_valid(c0v), .core_req_is_write(c0w), .core_req_addr(LINE),
    .core_req_wdata(c0d), .core_evict_valid(c0e),
    .core_rsp_valid(c0rv), .core_rsp_rdata(c0rd),
    .bank_req_valid(), .bank_req_is_write(), .bank_req_addr(),
    .bank_req_wdata(), .bank_req_wstrb(), .bank_req_source(),
    .bank_rsp_valid(1'b0), .bank_rsp_rdata('0), .bank_rsp_rstrb('0), .bank_rsp_rlast(1'b0),
    .noc_req_valid(l1_0_req_valid), .noc_req_flit(l1_0_req_flit),
    .noc_rsp_valid(l1_0_rsp_valid), .noc_rsp_flit(l1_0_rsp_flit),
    .mesi_state(l1_0_state), .line_addr(), .line_data(),
    .vic_valid_o(), .vic_state_o(), .vic_addr_o(),
    .rx_oflow_o(), .tx_oflow_o(),
    .dispatch_o(l1_0_dispatch), .rx_msg_o(l1_0_rx_msg)
  );

  l1_mesi_ctrl l1_1 (
    .clk(clk), .rst_n(rst_n), .tile_id(2'd1),
    .core_req_valid(c1v), .core_req_is_write(c1w), .core_req_addr(LINE),
    .core_req_wdata(c1d), .core_evict_valid(c1e),
    .core_rsp_valid(c1rv), .core_rsp_rdata(c1rd),
    .bank_req_valid(), .bank_req_is_write(), .bank_req_addr(),
    .bank_req_wdata(), .bank_req_wstrb(), .bank_req_source(),
    .bank_rsp_valid(1'b0), .bank_rsp_rdata('0), .bank_rsp_rstrb('0), .bank_rsp_rlast(1'b0),
    .noc_req_valid(l1_1_req_valid), .noc_req_flit(l1_1_req_flit),
    .noc_rsp_valid(l1_1_rsp_valid), .noc_rsp_flit(l1_1_rsp_flit),
    .mesi_state(l1_1_state), .line_addr(), .line_data(),
    .vic_valid_o(), .vic_state_o(), .vic_addr_o(),
    .rx_oflow_o(), .tx_oflow_o(),
    .dispatch_o(l1_1_dispatch), .rx_msg_o(l1_1_rx_msg)
  );

  // ---- L1 -> directory packet-atomic merge (64 flits per source) --------
  localparam int MF_DEPTH = 64;
  logic [FLIT_W-1:0] mf0 [MF_DEPTH];
  logic [FLIT_W-1:0] mf1 [MF_DEPTH];
  logic [6:0] mf0_wr, mf0_rd, mf0_cnt;
  logic [6:0] mf1_wr, mf1_rd, mf1_cnt;
  logic mf_rr, mf_lock, mf_sel;
  logic dir_req_valid;
  logic [FLIT_W-1:0] dir_req_flit;
  logic drain0, drain1, ovf;
  always_comb begin
    drain0 = 1'b0;
    drain1 = 1'b0;
    if (mf_lock) begin
      if (mf_sel == 1'b0 && mf0_cnt != 0)      drain0 = 1'b1;
      else if (mf_sel == 1'b1 && mf1_cnt != 0) drain1 = 1'b1;
    end else if (mf0_cnt != 0 && (mf_rr == 1'b0 || mf1_cnt == 0)) begin
      drain0 = 1'b1;
    end else if (mf1_cnt != 0) begin
      drain1 = 1'b1;
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      mf0_wr <= '0; mf0_rd <= '0; mf0_cnt <= '0;
      mf1_wr <= '0; mf1_rd <= '0; mf1_cnt <= '0;
      mf_rr <= 1'b0; mf_lock <= 1'b0; mf_sel <= 1'b0;
      dir_req_valid <= 1'b0; dir_req_flit <= '0; ovf <= 1'b0;
    end else begin
      if (l1_0_req_valid) begin
        mf0[mf0_wr] <= l1_0_req_flit;
        mf0_wr <= mf0_wr + 1'b1;
        if (mf0_cnt >= MF_DEPTH - 1) ovf <= 1'b1;
      end
      if (l1_1_req_valid) begin
        mf1[mf1_wr] <= l1_1_req_flit;
        mf1_wr <= mf1_wr + 1'b1;
        if (mf1_cnt >= MF_DEPTH - 1) ovf <= 1'b1;
      end

      if (drain0) begin
        dir_req_valid <= 1'b1;
        dir_req_flit  <= mf0[mf0_rd];
        mf0_rd <= mf0_rd + 1'b1;
        mf_rr  <= 1'b1; mf_sel <= 1'b0; mf_lock <= (mf0_cnt > 1);
      end else if (drain1) begin
        dir_req_valid <= 1'b1;
        dir_req_flit  <= mf1[mf1_rd];
        mf1_rd <= mf1_rd + 1'b1;
        mf_rr  <= 1'b0; mf_sel <= 1'b1; mf_lock <= (mf1_cnt > 1);
      end else begin
        dir_req_valid <= 1'b0;
        dir_req_flit  <= '0;
        mf_lock <= 1'b0;
      end

      mf0_cnt <= mf0_cnt + (l1_0_req_valid ? 7'd1 : 7'd0)
                          - (drain0 ? 7'd1 : 7'd0);
      mf1_cnt <= mf1_cnt + (l1_1_req_valid ? 7'd1 : 7'd0)
                          - (drain1 ? 7'd1 : 7'd0);
    end
  end

  // ---- Directory -------------------------------------------------------
  logic dir_rsp_valid;
  logic [FLIT_W-1:0] dir_rsp_flit;
  dir_state_t dir_state;
  logic [TILE_ID_W-1:0] dir_owner, dir_req_tile, dir_rx_src;
  logic [TILE_COUNT-1:0] dir_sharers;
  logic [ADDR_W-1:0] dir_dline;
  pending_op_t dir_pending_op;
  logic dir_rxq_empty;
  msg_type_t dir_rx_msg;
  logic dir_dtr_busy;
  logic dir_oflow;

  logic bank_req_valid, bank_req_is_write;
  logic [ADDR_W-1:0] bank_req_addr;
  logic [LINE_BITS-1:0] bank_req_wdata;
  logic [LINE_BITS/8-1:0] bank_req_wstrb;
  bank_src_e bank_req_source;
  logic bank_rsp_valid;
  logic [LINE_BITS-1:0] bank_rsp_rdata;
  logic dtr_busy;

  dir_ctrl u_dir (
    .clk(clk), .rst_n(rst_n), .tile_id(2'd0),
    .bank_req_valid(bank_req_valid), .bank_req_is_write(bank_req_is_write),
    .bank_req_addr(bank_req_addr), .bank_req_wdata(bank_req_wdata),
    .bank_req_wstrb(bank_req_wstrb), .bank_req_source(bank_req_source),
    .bank_rsp_valid(bank_rsp_valid), .bank_rsp_rdata(bank_rsp_rdata),
    .bank_rsp_rstrb('0), .bank_rsp_rlast(bank_rsp_valid),
    .noc_req_valid(dir_req_valid), .noc_req_flit(dir_req_flit),
    .noc_rsp_valid(dir_rsp_valid), .noc_rsp_flit(dir_rsp_flit),
    .dir_state_o(dir_state), .owner_o(dir_owner),
    .sharers_o(dir_sharers), .dline_o(dir_dline),
    .pending_op_o(dir_pending_op), .req_tile_o(dir_req_tile),
    .rxq_empty_o(dir_rxq_empty), .rx_msg_o(dir_rx_msg), .rx_src_o(dir_rx_src),
    .rx_oflow_o(dir_oflow), .tx_oflow_o(), .dtr_busy(dtr_busy)
  );

  // ---- Directory -> L1 demux (dest is valid only on the head flit) ------
  logic dmux_active;
  logic [3:0] dmux_flt;
  logic [TILE_ID_W-1:0] dmux_dst;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dmux_active <= 1'b0; dmux_flt <= 4'd0; dmux_dst <= '0;
    end else if (dir_rsp_valid) begin
      if (!dmux_active) begin
        if (dir_rsp_flit[HDR_HEAD]) begin
          dmux_dst <= dir_rsp_flit[HDR_DEST_LO +: TILE_ID_W];
          dmux_flt <= 4'd0;
          dmux_active <= (dir_rsp_flit[HDR_LEN_HI:HDR_LEN_LO] != 6'd1);
        end
      end else if (dmux_flt == 4'd7) begin
        dmux_active <= 1'b0; dmux_flt <= 4'd0;
      end else begin
        dmux_flt <= dmux_flt + 4'd1;
      end
    end
  end

  wire [TILE_ID_W-1:0] dmux_dst_cur =
      dmux_active ? dmux_dst : dir_rsp_flit[HDR_DEST_LO +: TILE_ID_W];

  assign l1_0_rsp_valid = dir_rsp_valid && (dmux_dst_cur == 2'd0);
  assign l1_0_rsp_flit  = dir_rsp_flit;
  assign l1_1_rsp_valid = dir_rsp_valid && (dmux_dst_cur == 2'd1);
  assign l1_1_rsp_flit  = dir_rsp_flit;

  // ---- L2 bank model: one line, 1-cycle read, writes update the line ---
  logic [LINE_BITS-1:0] bank_data, bank_rsp_rdata_q;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      bank_data <= '0;
      bank_rsp_valid <= 1'b0;
      bank_rsp_rdata_q <= '0;
    end else begin
      bank_rsp_valid <= bank_req_valid && !bank_req_is_write;
      if (bank_req_valid && !bank_req_is_write)
        bank_rsp_rdata_q <= bank_data;
      if (bank_req_valid && bank_req_is_write)
        bank_data <= bank_req_wdata;
    end
  end
  assign bank_rsp_rdata = bank_rsp_rdata_q;

endmodule
