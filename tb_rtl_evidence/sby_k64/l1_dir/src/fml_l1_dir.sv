// fml_l1_dir.sv — formal harness for the F1-F8 forward slice (2 L1s + dir + bank).
//
// Slice model: ONE line (all traffic on LINE), matching the co-landed one-entry
// directory. The merge FIFO / demux stand in for the router+NIC until §16.4:
// they are environment, not RTL under proof. Depth 64 cannot overflow because a
// source can queue at most 4 messages x 9 flits while the other source holds the
// packet-atomic drain.
`ifndef FML_L1_DIR_SV
`define FML_L1_DIR_SV

module fml_l1_dir import tile_pkg::*; (
    input logic clk,
    // Free core stimulus. Top-level inputs are free in BMC; keeping them as
    // module inputs (not undriven nets) makes every reader see the same value.
    input logic c0v, c0w, c0e, c1v, c1w, c1e,
    input logic [LINE_BITS-1:0] c0d, c1d
);

  localparam logic [ADDR_W-1:0] LINE = 32'h40;

  // Two-cycle reset, then free-running.
  logic [1:0] rst_cnt = 2'd0;
  always_ff @(posedge clk) if (rst_cnt != 2'd2) rst_cnt <= rst_cnt + 2'd1;
  wire rst_n = (rst_cnt == 2'd2);

  logic c0rv, c1rv;
  logic [LINE_BITS-1:0] c0rd, c1rd;

  // ── L1 #0 ─────────────────────────────────────────────────────────────────
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

  // ── L1 #1 ─────────────────────────────────────────────────────────────────
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

  // ── L1 -> directory packet-atomic merge (64 flits per source) ─────────────
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

  // ── Directory ─────────────────────────────────────────────────────────────
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
  logic dir_oflow;      // sticky: directory mailbox overrun

  logic bank_req_valid, bank_req_is_write;
  logic [ADDR_W-1:0] bank_req_addr;
  logic [LINE_BITS-1:0] bank_req_wdata;
  logic [LINE_BITS/8-1:0] bank_req_wstrb;
  bank_src_e bank_req_source;
  logic bank_rsp_valid;
  logic [LINE_BITS-1:0] bank_rsp_rdata;
  logic dtr_busy;

  dir_ctrl dir_0 (
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

  // ── Directory -> L1 demux (dest is valid only on the head flit) ──────────
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

  // ── L2 bank model: one line, 1-cycle read, writes update the line ───────
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

  // ── Assertions (direct instantiation: Yosys has no bind) ─────────────────
  sva_l1_dir u_sva (
    .clk(clk), .rst_n(rst_n),
    .l1_0_state(l1_0_state), .l1_1_state(l1_1_state),
    .dir_state(dir_state), .dir_sharers(dir_sharers), .dir_owner(dir_owner),
    .dir_pending_op(dir_pending_op), .dir_req_tile(dir_req_tile),
    .dir_rsp_valid(dir_rsp_valid), .dir_rsp_flit(dir_rsp_flit),
    .dir_rxq_empty(dir_rxq_empty), .dir_rx_msg(dir_rx_msg), .dir_rx_src(dir_rx_src),
    .l1_0_dispatch(l1_0_dispatch), .l1_0_rx_msg(l1_0_rx_msg),
    .l1_1_dispatch(l1_1_dispatch), .l1_1_rx_msg(l1_1_rx_msg)
  );

  // Environment sanity: the stand-in interconnect must not drop flits.
  always_ff @(posedge clk) if (rst_n) begin
    env_no_ovf: assert (!ovf);
    // The real NIC credit-gates the directory's mailbox. The slice has no NIC,
    // so constrain the environment to the contract that would make the mailbox
    // never overrun; otherwise the harness can corrupt the FIFO and manufacture
    // a false counterexample.
    env_dir_credit: assume (!dir_oflow);
    // Directory RX only receives valid L1-to-directory message types.
    // Valid: GETS(0), GETM(1), PUTS(2), PUTM(3), INVACK(6), UNBLOCK(4), DATAFWD(10)
    // FWD_GETS(8), FWD_GETM(9), INV(5), DATA(7), PUTACK(11) are directory-to-L1, never to directory.
    if (dir_req_valid && dir_req_flit[HDR_HEAD]) begin
      env_dir_rx_msg: assume (dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == 4'd0 ||  // GETS
                              dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == 4'd1 ||  // GETM
                              dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == 4'd2 ||  // PUTS
                              dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == 4'd3 ||  // PUTM
                              dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == 4'd6 ||  // INVACK
                              dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == 4'd4 ||  // UNBLOCK
                              dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == 4'd10);  // DATAFWD
    end
    // Directory destination must be a valid tile (0 or 1 for 2-tile slice)
    if (dir_rsp_valid && dir_rsp_flit[HDR_HEAD]) begin
      env_dir_dst: assume (dir_rsp_flit[HDR_DEST_LO +: TILE_ID_W] < 2);
    end
    // WP §3.3 rule 6 / Appendix A L1-FSM table: the requester emits MSG_UNBLOCK
    // only on the DATA-install exit of IS_D/IM_D/SM_D, i.e. after it has
    // received DATA and installed the line — so when the directory takes a
    // UNBLOCK from its pending req_tile, that tile's L1 holds the line in
    // S, E or M. ASSUMPTION: restricts the BMC state space; it is not a proof.
    if (dir_req_valid && dir_req_flit[HDR_HEAD] &&
        dir_req_flit[HDR_MSG_HI:HDR_MSG_LO] == MSG_UNBLOCK &&
        dir_req_flit[HDR_SRC_HI:HDR_SRC_LO] == dir_req_tile) begin
      env_unblk_installed: assume (dir_req_tile == 2'd0 ?
          (l1_0_state == L1_S || l1_0_state == L1_E || l1_0_state == L1_M) :
          (l1_1_state == L1_S || l1_1_state == L1_E || l1_1_state == L1_M));
    end
  end
endmodule
`endif
