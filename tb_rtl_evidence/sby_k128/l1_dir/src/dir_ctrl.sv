// dir_ctrl.sv — Directory controller (WP Appendix B; §3.3 rules 1,3,4,7,9; §3.7 DTR)
// Scaffold scope: ONE directory entry (one line) + messages serialised through a
// depth-4 mailbox. Per-line entries land with §16.3. Bank eviction (DIR_EVICT) is
// unreachable until the R3 bank port reports a miss (OI-7).
`ifndef DIR_CTRL_SV
`define DIR_CTRL_SV

module dir_ctrl import tile_pkg::*; (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [TILE_ID_W-1:0] tile_id,
    // L2 bank interface (R3 frozen)
    output logic        bank_req_valid,
    output logic        bank_req_is_write,
    output logic [ADDR_W-1:0]  bank_req_addr,
    output logic [LINE_BITS-1:0] bank_req_wdata,
    output logic [LINE_BITS/8-1:0] bank_req_wstrb,
    output bank_src_e         bank_req_source,
    input  logic        bank_rsp_valid,
    input  logic [LINE_BITS-1:0] bank_rsp_rdata,
    input  logic [LINE_BITS/8-1:0] bank_rsp_rstrb,
    input  logic        bank_rsp_rlast,
    // NoC interface (flit level, 64 b)
    input  logic        noc_req_valid,
    input  logic [FLIT_W-1:0] noc_req_flit,
    output logic        noc_rsp_valid,
    output logic [FLIT_W-1:0] noc_rsp_flit,
    // Observability (tb / shadow / SVA)
    output dir_state_t  dir_state_o,
    output logic [TILE_ID_W-1:0] owner_o,
    output logic [TILE_COUNT-1:0] sharers_o,
    output logic [ADDR_W-1:0] dline_o,
    // SVA observability (does not change behaviour)
    output pending_op_t pending_op_o,
    output logic [TILE_ID_W-1:0] req_tile_o,
    output logic rxq_empty_o,
    output msg_type_t rx_msg_o,
    output logic [TILE_ID_W-1:0] rx_src_o,
    output logic        rx_oflow_o,
    output logic        tx_oflow_o,
    output logic        dtr_busy
);

  // ── directory entry (§3.2: one entry for the scaffold) ────────────────────
  dir_state_t state;
  logic [ADDR_W-1:0] dline;
  logic [TILE_ID_W-1:0] owner;
  logic [TILE_COUNT-1:0] sharers;
  pending_op_t pending_op;
  logic [TILE_ID_W-1:0] req_tile;
  logic [1:0] phase;          // bank sub-step: 0 idle, 1 awaiting rsp
  logic [TILE_COUNT-1:0] inv_mask;  // INVs not yet transmitted (INV_WAIT)
  logic data_sent;            // DATA to requester already pushed
  logic serving;              // stable-state bank read serve in progress

  // ── TX engine ─────────────────────────────────────────────────────────────
  // ponytail: parallel arrays, not an array of structs — iverilog 13 mis-elaborates
  // struct arrays; rebuild the struct when a newer simulator is the floor.
  localparam int TX_DEPTH = 4;
  logic [3:0]           txq_msg  [TX_DEPTH];
  logic [TILE_ID_W-1:0] txq_dst  [TX_DEPTH];
  logic [ADDR_W-1:0]    txq_addr [TX_DEPTH];
  logic [LINE_BITS-1:0] txq_data [TX_DEPTH];
  logic                 txq_we   [TX_DEPTH];
  logic                 txq_excl [TX_DEPTH];

  logic [$clog2(TX_DEPTH)-1:0] tx_wr, tx_rd;
  logic [2:0] tx_cnt;
  logic tx_busy;
  logic [3:0] tx_flt;
  logic [5:0] tx_len;
  logic [3:0]           tx_cur_msg;
  logic [TILE_ID_W-1:0] tx_cur_dst;
  logic [ADDR_W-1:0]    tx_cur_addr;
  logic [LINE_BITS-1:0] tx_cur_data;
  logic                 tx_cur_we, tx_cur_excl;

  logic [3:0]           iss0_msg,  iss1_msg;
  logic [TILE_ID_W-1:0] iss0_dst,  iss1_dst;
  logic [ADDR_W-1:0]    iss0_addr, iss1_addr;
  logic [LINE_BITS-1:0] iss0_data, iss1_data;
  logic                 iss0_we, iss1_we, iss0_excl, iss1_excl;
  logic [1:0] iss_n;

  // ── RX engine + mailbox (messages arrive here while the DTR is busy) ──────
  localparam int RXQ_DEPTH = 4;
  logic [3:0]           rxq_msg  [RXQ_DEPTH];
  logic [TILE_ID_W-1:0] rxq_src  [RXQ_DEPTH];
  logic [ADDR_W-1:0]    rxq_addr [RXQ_DEPTH];
  logic [LINE_BITS-1:0] rxq_data [RXQ_DEPTH];
  logic                 rxq_we   [RXQ_DEPTH];
  logic                 rxq_excl [RXQ_DEPTH];
  logic [$clog2(RXQ_DEPTH)-1:0] rxq_wr, rxq_rd;
  logic [2:0] rxq_cnt;
  logic rxq_empty;
  logic [3:0]           h_msg;
  logic [TILE_ID_W-1:0] h_src;
  logic [ADDR_W-1:0]    h_addr;
  logic [LINE_BITS-1:0] h_data;
  logic                 h_we, h_excl;

  logic rx_active;
  logic [3:0] rx_flt;
  msg_type_t rx_hdr_msg;
  logic [TILE_ID_W-1:0] rx_hdr_src;
  logic [ADDR_W-1:0] rx_hdr_addr;
  logic rx_hdr_we, rx_hdr_excl;
  logic [LINE_BITS-1:0] rx_data;
  logic rx_publish;

  // ── helpers ───────────────────────────────────────────────────────────────
  function automatic logic [FLIT_W-1:0] mk_hdr(
      input msg_type_t m, input logic [TILE_ID_W-1:0] dst,
      input logic [ADDR_W-1:0] a, input logic we, input logic excl);
    mk_hdr = '0;
    mk_hdr[HDR_DEST_HI:HDR_DEST_LO] = {{(8-TILE_ID_W){1'b0}}, dst};
    mk_hdr[HDR_SRC_HI:HDR_SRC_LO]   = {{(8-TILE_ID_W){1'b0}}, tile_id};
    mk_hdr[HDR_MSG_HI:HDR_MSG_LO]   = m;
    mk_hdr[HDR_VC_HI:HDR_VC_LO]     = msg_to_vc(m);
    mk_hdr[HDR_HEAD]                = 1'b1;
    mk_hdr[HDR_TAIL]                = (msg_to_len(m) == 6'd1);
    mk_hdr[HDR_WE]                  = we;
    mk_hdr[HDR_EXCL]                = excl;
    mk_hdr[HDR_LEN_HI:HDR_LEN_LO]   = msg_to_len(m);
    mk_hdr[HDR_ADDR_HI:HDR_ADDR_LO] = a;
  endfunction

  task automatic send(input msg_type_t m, input logic [TILE_ID_W-1:0] dst,
                      input logic [ADDR_W-1:0] a, input logic [LINE_BITS-1:0] d,
                      input logic we, input logic excl);
    if (iss_n == 2'd0) begin
      iss0_msg = m; iss0_dst = dst; iss0_addr = a;
      iss0_data = d; iss0_we = we; iss0_excl = excl;
      iss_n = 2'd1;
    end else begin
      iss1_msg = m; iss1_dst = dst; iss1_addr = a;
      iss1_data = d; iss1_we = we; iss1_excl = excl;
      iss_n = 2'd2;
    end
  endtask

  function automatic logic [TILE_ID_W-1:0] low_tile(input logic [TILE_COUNT-1:0] m);
    for (int i = 0; i < TILE_COUNT; i++)
      if (m[i]) return TILE_ID_W'(i);
    return '0;
  endfunction

  // ── FSM + issue + bank control (comb) ─────────────────────────────────────
  dir_state_t state_d;
  logic [ADDR_W-1:0] dline_d;
  logic [TILE_ID_W-1:0] owner_d, req_tile_d;
  logic [TILE_COUNT-1:0] sharers_d, inv_mask_d;
  pending_op_t pending_op_d;
  logic [1:0] phase_d;
  logic data_sent_d, serving_d;
  logic pop;

  always_comb begin
    state_d      = state;
    dline_d      = dline;
    owner_d      = owner;
    sharers_d    = sharers;
    pending_op_d = pending_op;
    req_tile_d   = req_tile;
    phase_d      = phase;
    inv_mask_d   = inv_mask;
    data_sent_d  = data_sent;
    serving_d    = serving;
    pop          = 1'b0;

    iss0_msg = MSG_RSVD0; iss0_dst = '0; iss0_addr = '0;
    iss0_data = '0; iss0_we = 1'b0; iss0_excl = 1'b0;
    iss1_msg = MSG_RSVD0; iss1_dst = '0; iss1_addr = '0;
    iss1_data = '0; iss1_we = 1'b0; iss1_excl = 1'b0;
    iss_n = 2'd0;

    bank_req_valid    = 1'b0;
    bank_req_is_write = 1'b0;
    bank_req_addr     = '0;
    bank_req_wdata    = '0;
    bank_req_wstrb    = '0;
    bank_req_source   = SRC_REMOTE;

    // ---- stable-state bank read serve (DIR_S / DIR_E / DIR_M owner GETS) ----
    if (serving) begin
      if (phase == 2'd0) begin
        bank_req_valid  = 1'b1;
        bank_req_addr   = dline;
        bank_req_source = SRC_REMOTE;
        phase_d = 2'd1;
      end else if (bank_rsp_valid) begin
        send(MSG_DATA, req_tile, dline, bank_rsp_rdata, 1'b0,
             (state != DIR_S));   // E/M owner reply keeps exclusivity
        if (state == DIR_S) sharers_d = sharers | (1 << req_tile);
        phase_d   = 2'd0;
        serving_d = 1'b0;
      end
    end
    // ---- DIR_MEM_WAIT: fill from bank, DATA, then UNBLOCK exit ----
    else if (state == DIR_MEM_WAIT) begin
      if (phase == 2'd0) begin
        bank_req_valid  = 1'b1;
        bank_req_addr   = dline;
        bank_req_source = SRC_REMOTE;
        phase_d = 2'd1;
      end else if (phase == 2'd1 && bank_rsp_valid) begin
        send(MSG_DATA, req_tile, dline, bank_rsp_rdata, 1'b0, 1'b1);
        phase_d      = 2'd2;
        data_sent_d  = 1'b1;
      end else if (phase == 2'd2 && !rxq_empty &&
                   h_msg == MSG_UNBLOCK && h_src == req_tile && h_addr == dline) begin
        pop = 1'b1;
        owner_d      = req_tile;
        sharers_d    = (1 << req_tile);
        pending_op_d = POP_NONE;
        if (pending_op == POP_GETM) state_d = DIR_M;
        else                        state_d = DIR_E;
        phase_d      = 2'd0;
        data_sent_d  = 1'b0;
      end
    end
    // ---- DIR_INV_WAIT: INV sweep, INVACK collection, exclusive DATA ----
    else if (state == DIR_INV_WAIT) begin
      if (inv_mask != 0) begin
        send(MSG_INV, low_tile(inv_mask), dline, '0, 1'b0, 1'b0);
        inv_mask_d = inv_mask & (inv_mask - 1);
      end
      if (!rxq_empty) begin
        if (h_msg == MSG_INVACK || h_msg == MSG_PUTS) begin
          pop = 1'b1;
          sharers_d = sharers & ~(1 << h_src);
        end else if (h_msg == MSG_PUTM) begin
          pop = 1'b1;                       // a sharer cannot carry data; ignore
        end else if (h_msg == MSG_UNBLOCK && h_src == req_tile && data_sent) begin
          pop = 1'b1;
          owner_d      = req_tile;
          sharers_d    = (1 << req_tile);
          pending_op_d = POP_NONE;
          state_d      = DIR_M;
          data_sent_d  = 1'b0;
        end
      end
      if (sharers == 0 && inv_mask == 0 && !data_sent) begin
        if (phase == 2'd0) begin
          bank_req_valid  = 1'b1;
          bank_req_addr   = dline;
          bank_req_source = SRC_REMOTE;
          phase_d = 2'd1;
        end else if (bank_rsp_valid) begin
          send(MSG_DATA, req_tile, dline, bank_rsp_rdata, 1'b0, 1'b1);
          data_sent_d = 1'b1;
          phase_d     = 2'd0;
        end
      end
    end
    // ---- DIR_FWD_WAIT: absorb DATAFWD/PUTM/PUTS, await UNBLOCK ----
    else if (state == DIR_FWD_WAIT) begin
      // bank-read fallback after the owner released cleanly (PUTS row 1049)
      if (phase == 2'd1 && bank_rsp_valid && !data_sent) begin
        send(MSG_DATA, req_tile, dline, bank_rsp_rdata, 1'b0,
             (pending_op == POP_GETM));
        data_sent_d = 1'b1;
        phase_d     = 2'd0;
      end
      if (!rxq_empty) begin
        if (h_msg == MSG_DATAFWD) begin
          pop = 1'b1;
          bank_req_valid    = 1'b1;
          bank_req_is_write = 1'b1;
          bank_req_addr     = dline;
          bank_req_wdata    = h_data;
          bank_req_wstrb    = {LINE_BITS/8{1'b1}};
          bank_req_source   = SRC_REMOTE;
          if (!data_sent) begin
            send(MSG_DATA, req_tile, dline, h_data, 1'b0,
                 (pending_op == POP_GETM));
            data_sent_d = 1'b1;
          end
        end else if (h_msg == MSG_PUTM) begin
          pop = 1'b1;
          bank_req_valid    = 1'b1;
          bank_req_is_write = 1'b1;
          bank_req_addr     = h_addr;
          bank_req_wdata    = h_data;
          bank_req_wstrb    = {LINE_BITS/8{1'b1}};
          bank_req_source   = SRC_REMOTE;
          sharers_d = sharers & ~(1 << h_src);
          send(MSG_PUTACK, h_src, h_addr, '0, 1'b0, 1'b0);
          if (!data_sent) begin
            send(MSG_DATA, req_tile, dline, h_data, 1'b0,
                 (pending_op == POP_GETM));
            data_sent_d = 1'b1;
          end
        end else if (h_msg == MSG_PUTS) begin
          pop = 1'b1;
          sharers_d = sharers & ~(1 << h_src);
          send(MSG_PUTACK, h_src, h_addr, '0, 1'b0, 1'b0);
          if (!data_sent && phase == 2'd0) begin
            bank_req_valid  = 1'b1;
            bank_req_addr   = dline;
            bank_req_source = SRC_REMOTE;
            phase_d = 2'd1;
          end
        end else if (h_msg == MSG_INVACK) begin
          pop = 1'b1;                       // duplicate release: ignore (row 1050)
        end else if (h_msg == MSG_UNBLOCK && h_src == req_tile && data_sent) begin
          pop = 1'b1;
          if (pending_op == POP_GETM) begin
            owner_d   = req_tile;
            sharers_d = (1 << req_tile);
            state_d   = DIR_M;
          end else begin
            owner_d   = '0;
            sharers_d = sharers;
            state_d   = DIR_S;
          end
          pending_op_d = POP_NONE;
          data_sent_d  = 1'b0;
        end
      end
    end
    // ---- stable states ----
    else if (!rxq_empty) begin
      case (state)
        DIR_I: begin
          pop = 1'b1;
          if (h_msg == MSG_GETS || h_msg == MSG_GETM) begin
            dline_d      = h_addr;
            req_tile_d   = h_src;
            if (h_msg == MSG_GETM) pending_op_d = POP_GETM;
            else                   pending_op_d = POP_GETS;
            state_d      = DIR_MEM_WAIT;
            phase_d      = 2'd0;
            data_sent_d  = 1'b0;
          end else if (h_msg == MSG_PUTM) begin
            // not specified: a put for an untracked line still updates the bank
            bank_req_valid    = 1'b1;
            bank_req_is_write = 1'b1;
            bank_req_addr     = h_addr;
            bank_req_wdata    = h_data;
            bank_req_wstrb    = {LINE_BITS/8{1'b1}};
            bank_req_source   = SRC_REMOTE;
          end
          // PUTS / INVACK / UNBLOCK: stale, no state change
        end

        DIR_S: begin
          pop = 1'b1;
          if (h_msg == MSG_GETS) begin
            req_tile_d   = h_src;
            pending_op_d = POP_GETS;
            serving_d    = 1'b1;
            phase_d      = 2'd0;
          end else if (h_msg == MSG_GETM) begin
            pending_op_d = POP_GETM;
            req_tile_d   = h_src;
            owner_d      = '0;
            sharers_d    = sharers & ~(1 << h_src);
            inv_mask_d   = sharers & ~(1 << h_src);
            state_d      = DIR_INV_WAIT;
            phase_d      = 2'd0;
            data_sent_d  = 1'b0;
          end else if (h_msg == MSG_PUTS) begin
            sharers_d = sharers & ~(1 << h_src);
            if ((sharers & ~(1 << h_src)) == 0) state_d = DIR_I;
          end
          // INVACK / UNBLOCK: stale, no-op
        end

        DIR_E: begin
          if (h_msg == MSG_GETS || h_msg == MSG_GETM) begin
            pop = 1'b1;
            if (h_src == owner) begin
              req_tile_d   = h_src;
              if (h_msg == MSG_GETM) pending_op_d = POP_GETM;
            else                   pending_op_d = POP_GETS;
              serving_d    = 1'b1;
              phase_d      = 2'd0;
            end else begin
              if (h_msg == MSG_GETM) pending_op_d = POP_GETM;
            else                   pending_op_d = POP_GETS;
              req_tile_d   = h_src;
              sharers_d    = (1 << owner) | (1 << h_src);
              state_d      = DIR_FWD_WAIT;
              phase_d      = 2'd0;
              data_sent_d  = 1'b0;
              if (h_msg == MSG_GETM)
                send(MSG_FWD_GETM, owner, dline, '0, 1'b0, 1'b0);
              else
                send(MSG_FWD_GETS, owner, dline, '0, 1'b0, 1'b0);
            end
          end else if (h_msg == MSG_PUTS) begin
            pop = 1'b1;
            if (h_src == owner) begin
              owner_d   = '0;
              sharers_d = '0;
              send(MSG_PUTACK, h_src, h_addr, '0, 1'b0, 1'b0);
              state_d   = DIR_I;
            end else begin
              sharers_d = sharers & ~(1 << h_src);
            end
          end else if (h_msg == MSG_PUTM) begin
            pop = 1'b1;
            if (h_src == owner) begin
              bank_req_valid    = 1'b1;
              bank_req_is_write = 1'b1;
              bank_req_addr     = h_addr;
              bank_req_wdata    = h_data;
              bank_req_wstrb    = {LINE_BITS/8{1'b1}};
              bank_req_source   = SRC_REMOTE;
              owner_d   = '0;
              sharers_d = '0;
              send(MSG_PUTACK, h_src, h_addr, '0, 1'b0, 1'b0);
              state_d   = DIR_I;
            end
          end
          // INVACK / UNBLOCK: stale, no-op
        end

        DIR_M: begin
          if (h_msg == MSG_GETS || h_msg == MSG_GETM) begin
            pop = 1'b1;
            if (h_src == owner) begin
              // not specified where the data comes from; bank is stale in DIR_M.
              // Unreachable in practice (an owner never GETS its own line).
              req_tile_d   = h_src;
              if (h_msg == MSG_GETM) pending_op_d = POP_GETM;
            else                   pending_op_d = POP_GETS;
              serving_d    = 1'b1;
              phase_d      = 2'd0;
            end else begin
              if (h_msg == MSG_GETM) pending_op_d = POP_GETM;
            else                   pending_op_d = POP_GETS;
              req_tile_d   = h_src;
              sharers_d    = (1 << owner) | (1 << h_src);
              state_d      = DIR_FWD_WAIT;
              phase_d      = 2'd0;
              data_sent_d  = 1'b0;
              if (h_msg == MSG_GETM)
                send(MSG_FWD_GETM, owner, dline, '0, 1'b0, 1'b0);
              else
                send(MSG_FWD_GETS, owner, dline, '0, 1'b0, 1'b0);
            end
          end else if (h_msg == MSG_PUTM) begin
            pop = 1'b1;
            if (h_src == owner) begin
              bank_req_valid    = 1'b1;
              bank_req_is_write = 1'b1;
              bank_req_addr     = h_addr;
              bank_req_wdata    = h_data;
              bank_req_wstrb    = {LINE_BITS/8{1'b1}};
              bank_req_source   = SRC_REMOTE;
              owner_d   = '0;
              sharers_d = '0;
              send(MSG_PUTACK, h_src, h_addr, '0, 1'b0, 1'b0);
              state_d   = DIR_I;
            end
          end else if (h_msg == MSG_PUTS) begin
            pop = 1'b1;                       // stale sharer release
          end
          // INVACK / UNBLOCK: stale, no-op
        end

        default: pop = 1'b1;                  // DIR_EVICT unreachable this round (OI-7)
      endcase
    end
  end

  // ── TX capacity + retire ──────────────────────────────────────────────────
  logic [2:0] tx_free;
  logic       tx_push_ok;
  logic       tx_pop;

  assign tx_pop     = tx_busy && ({2'b00, tx_flt} == (tx_len - 6'd1));
  assign tx_free    = 3'd4 - tx_cnt + (tx_pop ? 3'd1 : 3'd0);
  assign tx_push_ok = (iss_n != 2'd0) && ({1'b0, iss_n} <= tx_free);

  // ── registered state ──────────────────────────────────────────────────────
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state      <= DIR_I;
      dline      <= '0;
      owner      <= '0;
      sharers    <= '0;
      pending_op <= POP_NONE;
      req_tile   <= '0;
      phase      <= 2'd0;
      inv_mask   <= '0;
      data_sent  <= 1'b0;
      serving    <= 1'b0;
      tx_wr <= '0; tx_rd <= '0; tx_cnt <= '0;
      tx_busy <= 1'b0; tx_flt <= '0; tx_len <= '0;
      tx_cur_msg <= MSG_RSVD0; tx_cur_dst <= '0; tx_cur_addr <= '0;
      tx_cur_data <= '0; tx_cur_we <= 1'b0; tx_cur_excl <= 1'b0;
      rxq_wr <= '0; rxq_rd <= '0; rxq_cnt <= '0;
      rx_active <= 1'b0; rx_flt <= '0;
      rx_hdr_msg <= MSG_RSVD0; rx_hdr_src <= '0; rx_hdr_addr <= '0;
      rx_hdr_we <= 1'b0; rx_hdr_excl <= 1'b0;
      rx_data <= '0;
      rx_oflow_o <= 1'b0;
      tx_oflow_o <= 1'b0;
    end else begin
      // ---- FSM ----
      state      <= state_d;
      dline      <= dline_d;
      owner      <= owner_d;
      sharers    <= sharers_d;
      pending_op <= pending_op_d;
      req_tile   <= req_tile_d;
      phase      <= phase_d;
      inv_mask   <= inv_mask_d;
      data_sent  <= data_sent_d;
      serving    <= serving_d;

      // ---- TX queue + serializer ----
      if (tx_push_ok) begin
        txq_msg[tx_wr]  <= iss0_msg;   txq_dst[tx_wr]  <= iss0_dst;
        txq_addr[tx_wr] <= iss0_addr;  txq_data[tx_wr] <= iss0_data;
        txq_we[tx_wr]   <= iss0_we;    txq_excl[tx_wr] <= iss0_excl;
        if (iss_n == 2'd2) begin
          txq_msg[tx_wr + 1'b1]  <= iss1_msg;   txq_dst[tx_wr + 1'b1]  <= iss1_dst;
          txq_addr[tx_wr + 1'b1] <= iss1_addr;  txq_data[tx_wr + 1'b1] <= iss1_data;
          txq_we[tx_wr + 1'b1]   <= iss1_we;    txq_excl[tx_wr + 1'b1] <= iss1_excl;
        end
        tx_wr <= tx_wr + iss_n;
      end
      if (tx_pop) tx_rd <= tx_rd + 1'b1;
      tx_cnt <= tx_cnt + (tx_push_ok ? {1'b0, iss_n} : 3'd0)
                       - (tx_pop ? 3'd1 : 3'd0);
      if (iss_n != 2'd0 && !tx_push_ok) tx_oflow_o <= 1'b1;

      if (!tx_busy) begin
        if (tx_cnt > 3'd0) begin
          tx_busy <= 1'b1;
          tx_flt  <= 4'd0;
          tx_cur_msg  <= txq_msg[tx_rd];
          tx_cur_dst  <= txq_dst[tx_rd];
          tx_cur_addr <= txq_addr[tx_rd];
          tx_cur_data <= txq_data[tx_rd];
          tx_cur_we   <= txq_we[tx_rd];
          tx_cur_excl <= txq_excl[tx_rd];
          tx_len      <= msg_to_len(msg_type_t'(txq_msg[tx_rd]));
        end
      end else if (tx_pop) begin
        tx_busy <= 1'b0;
        tx_flt  <= 4'd0;
      end else begin
        tx_flt <= tx_flt + 4'd1;
      end

      // ---- RX reassembly into the mailbox ----
      if (noc_req_valid) begin
        if (!rx_active) begin
          if (noc_req_flit[HDR_HEAD]) begin
            rx_hdr_msg  <= msg_type_t'(noc_req_flit[HDR_MSG_HI:HDR_MSG_LO]);
            rx_hdr_src  <= noc_req_flit[HDR_SRC_LO +: TILE_ID_W];
            rx_hdr_addr <= noc_req_flit[HDR_ADDR_HI:HDR_ADDR_LO];
            rx_hdr_we   <= noc_req_flit[HDR_WE];
            rx_hdr_excl <= noc_req_flit[HDR_EXCL];
            if (noc_req_flit[HDR_LEN_HI:HDR_LEN_LO] == 6'd1) begin
              rxq_msg[rxq_wr]  <= noc_req_flit[HDR_MSG_HI:HDR_MSG_LO];
              rxq_src[rxq_wr]  <= noc_req_flit[HDR_SRC_LO +: TILE_ID_W];
              rxq_addr[rxq_wr] <= noc_req_flit[HDR_ADDR_HI:HDR_ADDR_LO];
              rxq_we[rxq_wr]   <= noc_req_flit[HDR_WE];
              rxq_excl[rxq_wr] <= noc_req_flit[HDR_EXCL];
              rxq_data[rxq_wr] <= '0;
              rxq_wr <= rxq_wr + 1'b1;
              if (rxq_cnt >= 3'd4) rx_oflow_o <= 1'b1;
            end else begin
              rx_active <= 1'b1;
              rx_flt    <= 4'd1;
            end
          end
        end else begin
          if (rx_flt == 4'd8) begin
            rx_active <= 1'b0;
            rxq_msg[rxq_wr]  <= rx_hdr_msg;
            rxq_src[rxq_wr]  <= rx_hdr_src;
            rxq_addr[rxq_wr] <= rx_hdr_addr;
            rxq_we[rxq_wr]   <= rx_hdr_we;
            rxq_excl[rxq_wr] <= rx_hdr_excl;
            rxq_data[rxq_wr] <= {noc_req_flit[63:0], rx_data[447:0]};
            rxq_wr <= rxq_wr + 1'b1;
            if (rxq_cnt >= 3'd4) rx_oflow_o <= 1'b1;
          end else begin
            case (rx_flt)
              4'd1: rx_data[ 63:  0] <= noc_req_flit[63:0];
              4'd2: rx_data[127: 64] <= noc_req_flit[63:0];
              4'd3: rx_data[191:128] <= noc_req_flit[63:0];
              4'd4: rx_data[255:192] <= noc_req_flit[63:0];
              4'd5: rx_data[319:256] <= noc_req_flit[63:0];
              4'd6: rx_data[383:320] <= noc_req_flit[63:0];
              4'd7: rx_data[447:384] <= noc_req_flit[63:0];
              default: ;
            endcase
            rx_flt <= rx_flt + 4'd1;
          end
        end
      end

      // mailbox pointers: push above, pop below
      if (pop)      rxq_rd  <= rxq_rd + 1'b1;
      rxq_cnt <= rxq_cnt + (rx_publish ? 3'd1 : 3'd0) - (pop ? 3'd1 : 3'd0);
      if (rx_publish && rxq_cnt >= 3'd4 && !pop) rx_oflow_o <= 1'b1;
    end
  end

  // ── RX publish detector ───────────────────────────────────────────────────
  always_comb begin
    rx_publish = 1'b0;
    if (noc_req_valid) begin
      if (!rx_active)
        rx_publish = noc_req_flit[HDR_HEAD] &&
                     (noc_req_flit[HDR_LEN_HI:HDR_LEN_LO] == 6'd1);
      else
        rx_publish = (rx_flt == 4'd8);
    end
  end

  // ── TX flit output ────────────────────────────────────────────────────────
  always_comb begin
    noc_rsp_valid = tx_busy;
    noc_rsp_flit  = '0;
    if (tx_busy) begin
      if (tx_flt == 4'd0) begin
        noc_rsp_flit = mk_hdr(msg_type_t'(tx_cur_msg), tx_cur_dst, tx_cur_addr,
                              tx_cur_we, tx_cur_excl);
      end else begin
        case (tx_flt)
          4'd1: noc_rsp_flit = tx_cur_data[ 63:  0];
          4'd2: noc_rsp_flit = tx_cur_data[127: 64];
          4'd3: noc_rsp_flit = tx_cur_data[191:128];
          4'd4: noc_rsp_flit = tx_cur_data[255:192];
          4'd5: noc_rsp_flit = tx_cur_data[319:256];
          4'd6: noc_rsp_flit = tx_cur_data[383:320];
          4'd7: noc_rsp_flit = tx_cur_data[447:384];
          4'd8: noc_rsp_flit = tx_cur_data[511:448];
          default: ;
        endcase
      end
    end
  end

  // ── mailbox head + status ─────────────────────────────────────────────────
  assign rxq_empty = (rxq_cnt == 3'd0);
  assign h_msg  = rxq_msg[rxq_rd];
  assign h_src  = rxq_src[rxq_rd];
  assign h_addr = rxq_addr[rxq_rd];
  assign h_data = rxq_data[rxq_rd];
  assign h_we   = rxq_we[rxq_rd];
  assign h_excl = rxq_excl[rxq_rd];

  assign dir_state_o  = state;
  assign owner_o      = owner;
  assign sharers_o    = sharers;
  assign dline_o      = dline;
  assign pending_op_o = pending_op;
  assign req_tile_o   = req_tile;
  assign rxq_empty_o  = rxq_empty;
  assign rx_msg_o     = msg_type_t'(h_msg);
  assign rx_src_o     = h_src;
  assign dtr_busy    = (state != DIR_I);

  wire _unused_ok = &{1'b0, bank_rsp_rstrb, bank_rsp_rlast, h_we, h_excl, 1'b0};

endmodule
`endif
