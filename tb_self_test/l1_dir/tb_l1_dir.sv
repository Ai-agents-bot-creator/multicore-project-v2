// tb_l1_dir.sv — Testbench top: two real L1 controllers + real directory + bank model
// NoC scaffold: per-L1 flit FIFOs merged into the directory's single input; the
// directory output is demuxed by the flit destination field. Routers/credits land
// with their own work order — here a FIFO absorbs the flit rate.
`ifndef TB_L1_DIR_SV
`define TB_L1_DIR_SV

module tb_l1_dir import tile_pkg::*; (
    input  logic        clk,
    input  logic        rst_n,
    // Core 0 interface (requester)
    input  logic        core0_req_valid,
    input  logic        core0_req_is_write,
    input  logic [ADDR_W-1:0] core0_req_addr,
    input  logic [LINE_BITS-1:0] core0_req_wdata,
    input  logic        core0_evict_valid,
    output logic        core0_rsp_valid,
    output logic [LINE_BITS-1:0] core0_rsp_rdata,
    // Core 1 interface (owner)
    input  logic        core1_req_valid,
    input  logic        core1_req_is_write,
    input  logic [ADDR_W-1:0] core1_req_addr,
    input  logic [LINE_BITS-1:0] core1_req_wdata,
    input  logic        core1_evict_valid,
    output logic        core1_rsp_valid,
    output logic [LINE_BITS-1:0] core1_rsp_rdata,
    // L2 bank tap (observability; the bank model is inside)
    output logic        bank_req_valid,
    output logic        bank_req_is_write,
    output logic [ADDR_W-1:0]  bank_req_addr,
    output logic [LINE_BITS-1:0] bank_req_wdata,
    output logic [LINE_BITS/8-1:0] bank_req_wstrb,
    output bank_src_e         bank_req_source,
    output logic        bank_rsp_valid,
    output logic [LINE_BITS-1:0] bank_rsp_rdata,
    output logic [LINE_BITS/8-1:0] bank_rsp_rstrb,
    output logic        bank_rsp_rlast,
    // NoC taps
    output logic        noc_l1_dir_valid,
    output logic [FLIT_W-1:0] noc_l1_dir_flit,
    output logic        noc_dir_l1_valid,
    output logic [FLIT_W-1:0] noc_dir_l1_flit,
    // Status
    output logic        dtr_busy,
    output logic        noc_ovf_o
);

  // ── L1 #0 ─────────────────────────────────────────────────────────────────
  logic l1_0_noc_req_valid;
  logic [FLIT_W-1:0] l1_0_noc_req_flit;
  logic l1_0_noc_rsp_valid;
  logic [FLIT_W-1:0] l1_0_noc_rsp_flit;
  l1_state_t l1_0_state;

  l1_mesi_ctrl l1_0 (
    .clk(clk), .rst_n(rst_n), .tile_id(2'd0),
    .core_req_valid(core0_req_valid), .core_req_is_write(core0_req_is_write),
    .core_req_addr(core0_req_addr), .core_req_wdata(core0_req_wdata),
    .core_evict_valid(core0_evict_valid),
    .core_rsp_valid(core0_rsp_valid), .core_rsp_rdata(core0_rsp_rdata),
    .bank_req_valid(), .bank_req_is_write(), .bank_req_addr(),
    .bank_req_wdata(), .bank_req_wstrb(), .bank_req_source(),
    .bank_rsp_valid(1'b0), .bank_rsp_rdata('0), .bank_rsp_rstrb('0), .bank_rsp_rlast(1'b0),
    .noc_req_valid(l1_0_noc_req_valid), .noc_req_flit(l1_0_noc_req_flit),
    .noc_rsp_valid(l1_0_noc_rsp_valid), .noc_rsp_flit(l1_0_noc_rsp_flit),
    .mesi_state(l1_0_state), .line_addr(), .line_data(),
    .vic_valid_o(), .vic_state_o(), .vic_addr_o(),
    .rx_oflow_o(), .tx_oflow_o()
  );

  // ── L1 #1 ─────────────────────────────────────────────────────────────────
  logic l1_1_noc_req_valid;
  logic [FLIT_W-1:0] l1_1_noc_req_flit;
  logic l1_1_noc_rsp_valid;
  logic [FLIT_W-1:0] l1_1_noc_rsp_flit;
  l1_state_t l1_1_state;

  l1_mesi_ctrl l1_1 (
    .clk(clk), .rst_n(rst_n), .tile_id(2'd1),
    .core_req_valid(core1_req_valid), .core_req_is_write(core1_req_is_write),
    .core_req_addr(core1_req_addr), .core_req_wdata(core1_req_wdata),
    .core_evict_valid(core1_evict_valid),
    .core_rsp_valid(core1_rsp_valid), .core_rsp_rdata(core1_rsp_rdata),
    .bank_req_valid(), .bank_req_is_write(), .bank_req_addr(),
    .bank_req_wdata(), .bank_req_wstrb(), .bank_req_source(),
    .bank_rsp_valid(1'b0), .bank_rsp_rdata('0), .bank_rsp_rstrb('0), .bank_rsp_rlast(1'b0),
    .noc_req_valid(l1_1_noc_req_valid), .noc_req_flit(l1_1_noc_req_flit),
    .noc_rsp_valid(l1_1_noc_rsp_valid), .noc_rsp_flit(l1_1_noc_rsp_flit),
    .mesi_state(l1_1_state), .line_addr(), .line_data(),
    .vic_valid_o(), .vic_state_o(), .vic_addr_o(),
    .rx_oflow_o(), .tx_oflow_o()
  );

  // ── L1 -> directory flit merge (depth-16 FIFO per L1) ─────────────────────
  // ponytail: FIFO + round-robin instead of router credits; overflow is flagged,
  // replace with the real nic/router in the interconnect work order.
  localparam int MF_DEPTH = 16;
  logic [FLIT_W-1:0] mf0 [MF_DEPTH];
  logic [FLIT_W-1:0] mf1 [MF_DEPTH];
  logic [3:0] mf0_wr, mf0_rd, mf0_cnt;
  logic [3:0] mf1_wr, mf1_rd, mf1_cnt;
  logic mf_rr;
  logic mf_lock;   // draining one source's packet run
  logic mf_sel;
  logic dir_noc_req_valid;
  logic [FLIT_W-1:0] dir_noc_req_flit;

  logic drain0, drain1;
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
      mf_rr <= 1'b0;
      mf_lock <= 1'b0;
      mf_sel <= 1'b0;
      dir_noc_req_valid <= 1'b0;
      dir_noc_req_flit  <= '0;
      noc_ovf_o <= 1'b0;
    end else begin
      if (l1_0_noc_req_valid) begin
        mf0[mf0_wr] <= l1_0_noc_req_flit;
        mf0_wr <= mf0_wr + 1'b1;
        if (mf0_cnt >= 4'd15) noc_ovf_o <= 1'b1;
      end
      if (l1_1_noc_req_valid) begin
        mf1[mf1_wr] <= l1_1_noc_req_flit;
        mf1_wr <= mf1_wr + 1'b1;
        if (mf1_cnt >= 4'd15) noc_ovf_o <= 1'b1;
      end

      // packet-atomic drain: keep one source selected while it stays non-empty
      if (drain0) begin
        dir_noc_req_valid <= 1'b1;
        dir_noc_req_flit  <= mf0[mf0_rd];
        mf0_rd <= mf0_rd + 1'b1;
        mf_rr  <= 1'b1;
        mf_sel <= 1'b0;
        mf_lock <= (mf0_cnt > 4'd1);
      end else if (drain1) begin
        dir_noc_req_valid <= 1'b1;
        dir_noc_req_flit  <= mf1[mf1_rd];
        mf1_rd <= mf1_rd + 1'b1;
        mf_rr  <= 1'b0;
        mf_sel <= 1'b1;
        mf_lock <= (mf1_cnt > 4'd1);
      end else begin
        dir_noc_req_valid <= 1'b0;
        dir_noc_req_flit  <= '0;
        mf_lock <= 1'b0;
      end

      // one combined count update: simultaneous push+pop must not cancel out
      mf0_cnt <= mf0_cnt + (l1_0_noc_req_valid ? 4'd1 : 4'd0)
                          - (drain0 ? 4'd1 : 4'd0);
      mf1_cnt <= mf1_cnt + (l1_1_noc_req_valid ? 4'd1 : 4'd0)
                          - (drain1 ? 4'd1 : 4'd0);
    end
  end

  // ── Directory ─────────────────────────────────────────────────────────────
  logic dir_noc_rsp_valid;
  logic [FLIT_W-1:0] dir_noc_rsp_flit;
  dir_state_t dir_state;
  logic [TILE_ID_W-1:0] dir_owner;

  dir_ctrl dir_0 (
    .clk(clk), .rst_n(rst_n), .tile_id(2'd0),
    .bank_req_valid(bank_req_valid), .bank_req_is_write(bank_req_is_write),
    .bank_req_addr(bank_req_addr), .bank_req_wdata(bank_req_wdata),
    .bank_req_wstrb(bank_req_wstrb), .bank_req_source(bank_req_source),
    .bank_rsp_valid(bank_rsp_valid), .bank_rsp_rdata(bank_rsp_rdata),
    .bank_rsp_rstrb(bank_rsp_rstrb), .bank_rsp_rlast(bank_rsp_rlast),
    .noc_req_valid(dir_noc_req_valid), .noc_req_flit(dir_noc_req_flit),
    .noc_rsp_valid(dir_noc_rsp_valid), .noc_rsp_flit(dir_noc_rsp_flit),
    .dir_state_o(dir_state), .owner_o(dir_owner),
    .sharers_o(), .dline_o(), .rx_oflow_o(), .tx_oflow_o(),
    .dtr_busy(dtr_busy)
  );

  // ── Directory -> L1 demux ─────────────────────────────────────────────────
  // The destination field is only valid on the head flit; body flits carry data.
  // Latch the destination at the head and keep it for the whole packet.
  logic       dmux_active;
  logic [3:0] dmux_flt;
  logic [TILE_ID_W-1:0] dmux_dst;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dmux_active <= 1'b0;
      dmux_flt    <= 4'd0;
      dmux_dst    <= '0;
    end else if (dir_noc_rsp_valid) begin
      if (!dmux_active) begin
        if (dir_noc_rsp_flit[HDR_HEAD]) begin
          dmux_dst <= dir_noc_rsp_flit[HDR_DEST_LO +: TILE_ID_W];
          dmux_flt <= 4'd0;
          dmux_active <= (dir_noc_rsp_flit[HDR_LEN_HI:HDR_LEN_LO] != 6'd1);
        end
      end else if (dmux_flt == 4'd7) begin
        dmux_active <= 1'b0;               // eight body flits consumed
        dmux_flt    <= 4'd0;
      end else begin
        dmux_flt <= dmux_flt + 4'd1;
      end
    end
  end

  wire [TILE_ID_W-1:0] dmux_dst_cur =
      dmux_active ? dmux_dst : dir_noc_rsp_flit[HDR_DEST_LO +: TILE_ID_W];

  assign l1_0_noc_rsp_valid = dir_noc_rsp_valid && (dmux_dst_cur == 2'd0);
  assign l1_0_noc_rsp_flit  = dir_noc_rsp_flit;
  assign l1_1_noc_rsp_valid = dir_noc_rsp_valid && (dmux_dst_cur == 2'd1);
  assign l1_1_noc_rsp_flit  = dir_noc_rsp_flit;

  // ── NoC taps ──────────────────────────────────────────────────────────────
  assign noc_l1_dir_valid = dir_noc_req_valid;
  assign noc_l1_dir_flit  = dir_noc_req_flit;
  assign noc_dir_l1_valid = dir_noc_rsp_valid;
  assign noc_dir_l1_flit  = dir_noc_rsp_flit;

  // ── L2 bank model: unbounded lines, 1-cycle read latency ──────────────────
  // ponytail: 8-entry CAM, no replacement -> DIR_EVICT unreachable this round (OI-7).
  localparam int BM_ENTRIES = 8;
  logic [ADDR_W-1:0]    bm_tag   [BM_ENTRIES];
  logic [LINE_BITS-1:0] bm_data  [BM_ENTRIES];
  logic                 bm_valid [BM_ENTRIES];
  logic                 bm_dirty [BM_ENTRIES];

  logic [LINE_BITS-1:0] bank_rsp_rdata_r;
  logic                 bank_rsp_valid_r;

  assign bank_rsp_valid   = bank_rsp_valid_r;
  assign bank_rsp_rdata   = bank_rsp_rdata_r;
  assign bank_rsp_rstrb   = '0;
  assign bank_rsp_rlast   = bank_rsp_valid_r;

  integer bi;
  integer bj;
  integer bslot;
  logic   bfound;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      bank_rsp_valid_r <= 1'b0;
      bank_rsp_rdata_r <= '0;
      for (bi = 0; bi < BM_ENTRIES; bi = bi + 1) begin
        bm_valid[bi] <= 1'b0;
        bm_tag[bi]   <= '0;
        bm_data[bi]  <= '0;
        bm_dirty[bi] <= 1'b0;
      end
    end else begin
      bank_rsp_valid_r <= 1'b0;
      if (bank_req_valid) begin
        if (bank_req_is_write) begin
          bfound = 1'b0;
          bslot  = 0;
          for (bj = 0; bj < BM_ENTRIES; bj = bj + 1) begin
            if (bm_valid[bj] && bm_tag[bj] == bank_req_addr) begin
              bfound = 1'b1;
              bslot  = bj;
            end else if (!bm_valid[bj] && !bfound) begin
              bslot = bj;
            end
          end
          bm_valid[bslot] <= 1'b1;
          bm_tag[bslot]   <= bank_req_addr;
          bm_data[bslot]  <= bank_req_wdata;
          bm_dirty[bslot] <= 1'b1;
        end else begin
          bank_rsp_rdata_r <= '0;
          for (bi = 0; bi < BM_ENTRIES; bi = bi + 1) begin
            if (bm_valid[bi] && bm_tag[bi] == bank_req_addr)
              bank_rsp_rdata_r <= bm_data[bi];
          end
          bank_rsp_valid_r <= 1'b1;
        end
      end
    end
  end

endmodule
`endif
