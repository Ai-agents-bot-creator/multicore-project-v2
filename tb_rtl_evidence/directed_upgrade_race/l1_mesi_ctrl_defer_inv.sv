// l1_mesi_ctrl.sv — L1 MESI controller (WP Appendix A; §3.3 rules 2,5,6,8,9,10; rulings B2, B6)
// Scaffold scope: ONE line slot per tile + victim registers for the conflict-eviction
// sub-step (B2). The 4x4 array + tree-PLRU land with §16.3; 9-flit packetisation is
// folded in here until nic.sv lands (WP §3.1 block 5).
// B6 NEGATIVE CONTROL — DEFER-INV mutant. Same-name replacement of
// rtl/l1/l1_mesi_ctrl.sv (pattern: dir_ctrl_mut.sv): the comb dispatch guard
// below holds a same-line INV while a miss is open instead of aborting it.
// B6.2 must FAIL against this file with the fault present.
`ifndef L1_MESI_CTRL_DEFER_INV_SV
`define L1_MESI_CTRL_DEFER_INV_SV

module l1_mesi_ctrl import tile_pkg::*; (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [TILE_ID_W-1:0] tile_id,      // flit source id
    // Core interface (line-granular: no byte strobes — sub-line stores land with the core model)
    input  logic        core_req_valid,
    input  logic        core_req_is_write,
    input  logic [ADDR_W-1:0] core_req_addr,
    input  logic [LINE_BITS-1:0] core_req_wdata,
    input  logic        core_evict_valid,      // proactive release (Appendix A EI_A/MI_A rows)
    output logic        core_rsp_valid,
    output logic [LINE_BITS-1:0] core_rsp_rdata,
    // L2 bank interface (R3 frozen). Unused on the F1-F8 paths: all L1 data arrives
    // via DATA from the directory (§3.3 message set). Kept for R3 compatibility.
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
    // NoC interface (flit level, 64 b; L1 <-> directory)
    output logic        noc_req_valid,
    output logic [FLIT_W-1:0] noc_req_flit,
    input  logic        noc_rsp_valid,
    input  logic [FLIT_W-1:0] noc_rsp_flit,
    // Observability for tb / reference-model shadow / SVA
    output l1_state_t   mesi_state,
    output logic [ADDR_W-1:0] line_addr,
    output logic [LINE_BITS-1:0] line_data,
    output logic        vic_valid_o,           // B2 conflict victim in flight (A1.x)
    output l1_state_t   vic_state_o,
    output logic [ADDR_W-1:0] vic_addr_o,
    output logic        rx_oflow_o,            // message dropped: single-buffered RX (A3.x)
    output logic        tx_oflow_o,            // TX queue overflow (A3.x)
    // SVA observability (does not change behaviour)
    output logic        dispatch_o,            // a complete message dispatches this cycle
    output msg_type_t   rx_msg_o,
    output logic        abort_o                // B6: same-line INV aborted the miss this cycle
);

  // ── protocol state ────────────────────────────────────────────────────────
  l1_state_t state, vic_state;
  logic [ADDR_W-1:0] addr_q, vic_addr;
  logic [LINE_BITS-1:0] data_q, wdata_q;
  logic vic_valid;        // conflict victim captured, release in flight (B2 sub-step)
  logic evict_pend;       // victim release awaits PUTACK (M/E victim; S needs no ack)

  // ── TX engine: message queue + 9-flit serializer ──────────────────────────
  // ponytail: parallel arrays, not an array of structs — iverilog 13 mis-elaborates
  // struct arrays; rebuild the struct when a simulator that handles it is the floor.
  localparam int TX_DEPTH = 4;
  logic [3:0]           txq_msg  [TX_DEPTH];
  logic [ADDR_W-1:0]    txq_addr [TX_DEPTH];
  logic [LINE_BITS-1:0] txq_data [TX_DEPTH];
  logic                 txq_we   [TX_DEPTH];   // HDR_WE: DATAFWD dirty / PUTM data
  logic                 txq_excl [TX_DEPTH];   // HDR_EXCL (L1 sends 0)

  logic [$clog2(TX_DEPTH)-1:0] tx_wr, tx_rd;
  logic [2:0] tx_cnt;
  logic tx_busy;
  logic [3:0] tx_flt;                 // flit index within packet
  logic [5:0] tx_len;                 // 1 or 9 flits

  logic [3:0]           tx_cur_msg;
  logic [ADDR_W-1:0]    tx_cur_addr;
  logic [LINE_BITS-1:0] tx_cur_data;
  logic                 tx_cur_we, tx_cur_excl;

  // issue stage (built in always_comb, consumed by always_ff) — up to 2 msg/cycle
  logic [3:0]           iss0_msg,  iss1_msg;
  logic [ADDR_W-1:0]    iss0_addr, iss1_addr;
  logic [LINE_BITS-1:0] iss0_data, iss1_data;
  logic                 iss0_we, iss1_we, iss0_excl, iss1_excl;
  logic [1:0] iss_n;

  // ── RX engine: 9-flit reassembly, single-buffered ─────────────────────────
  logic rx_active;
  logic [3:0] rx_flt;
  msg_type_t rx_hdr_msg;
  logic [ADDR_W-1:0] rx_hdr_addr;
  logic rx_hdr_we, rx_hdr_excl;
  logic [LINE_BITS-1:0] rx_data;
  logic rx_pending;                   // complete message awaiting dispatch
  msg_type_t rx_msg;
  logic [ADDR_W-1:0] rx_addr;
  logic rx_we, rx_excl;
  logic [LINE_BITS-1:0] rx_line;
  logic rx_publish;                   // a message completes this cycle

  // ── helpers ───────────────────────────────────────────────────────────────
  function automatic logic [ADDR_W-1:0] line_of(input logic [ADDR_W-1:0] a);
    line_of = a & ~((1 << OFFSET_W) - 1);
  endfunction

  function automatic logic is_stable(input l1_state_t s);
    case (s)
      L1_I, L1_S, L1_E, L1_M: return 1'b1;
      default:                return 1'b0;
    endcase
  endfunction

  function automatic logic is_miss(input l1_state_t s);
    case (s)
      L1_IS_D, L1_IM_D, L1_SM_D: return 1'b1;
      default:                   return 1'b0;
    endcase
  endfunction

  function automatic logic is_held(input l1_state_t s);
    case (s)
      L1_S, L1_E, L1_M: return 1'b1;
      default:          return 1'b0;
    endcase
  endfunction

  function automatic logic [FLIT_W-1:0] mk_hdr(
      input msg_type_t m, input logic [ADDR_W-1:0] a,
      input logic we, input logic excl);
    mk_hdr = '0;
    mk_hdr[HDR_DEST_HI:HDR_DEST_LO] = {{(8-TILE_ID_W){1'b0}}, a[HOME_HI:HOME_LO]};
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

  // issue one message (comb-only; two slots because INV-in-M and the conflict
  // path emit two messages in one cycle)
  task automatic send(input msg_type_t m, input logic [ADDR_W-1:0] a,
                      input logic [LINE_BITS-1:0] d,
                      input logic we, input logic excl);
    if (iss_n == 2'd0) begin
      iss0_msg = m; iss0_addr = a; iss0_data = d; iss0_we = we; iss0_excl = excl;
      iss_n = 2'd1;
    end else begin
      iss1_msg = m; iss1_addr = a; iss1_data = d; iss1_we = we; iss1_excl = excl;
      iss_n = 2'd2;
    end
  endtask

  // ── combinational decision tree ───────────────────────────────────────────
  // Priority: core_evict > RX dispatch > core request.
  // evict-first makes the F6/F7 evict-during-forward race deterministic: a FWD
  // arriving the same cycle as core_evict is dispatched one cycle later, from
  // I/EI_A/MI_A, producing the defensive INVACK (Appendix A, N5/N12).
  logic dispatch;                     // rx_pending consumed this cycle
  logic core_accept;                  // core request accepted this cycle
  logic data_install;                 // DATA completing a miss this cycle
  logic [ADDR_W-1:0] ca;              // core address, line-aligned
  logic hit, conflict;

  always_comb begin
    ca         = line_of(core_req_addr);
    hit        = 1'b0;
    conflict   = 1'b0;
    iss0_msg   = MSG_RSVD0;
    iss0_addr  = '0;
    iss0_data  = '0;
    iss0_we    = 1'b0;
    iss0_excl  = 1'b0;
    iss1_msg   = MSG_RSVD0;
    iss1_addr  = '0;
    iss1_data  = '0;
    iss1_we    = 1'b0;
    iss1_excl  = 1'b0;
    iss_n      = 2'd0;
    dispatch   = 1'b0;
    core_accept= 1'b0;
    data_install = 1'b0;

    if (is_stable(state)) begin
      hit      = (addr_q == ca);
      conflict = (addr_q != ca);
    end

    // ---- 1. proactive eviction (highest priority; F6/F7 race) ----
    if (core_evict_valid && is_stable(state) && !vic_valid) begin
      case (state)
        L1_M:    send(MSG_PUTM, addr_q, data_q, 1'b1, 1'b0);
        default: send(MSG_PUTS, addr_q, '0, 1'b0, 1'b0);   // E waits PUTACK, S does not
      endcase
    end
    // ---- 2. RX message dispatch (Premise R: state-independent) ----
    // DEFER-INV guard (B6-forbidden): while a same-line INV is pending and
    // the miss (IS_D/IM_D/SM_D) is open, suppress dispatch entirely -
    // rx_pending holds, no INVACK is sent, the directory's INV sweep never
    // completes (deadlock). B6.2 fails with DEFER-INV FAULT PRESENT.
    else if (rx_pending &&
             !(rx_msg == MSG_INV && rx_addr == addr_q && is_miss(state))) begin
      dispatch = 1'b1;
      case (rx_msg)
        MSG_DATA: begin
          // Appendix A: IS_D/IM_D/SM_D are the only DATA exit rows
          if (is_miss(state) && rx_addr == addr_q) begin
            data_install = 1'b1;
            send(MSG_UNBLOCK, addr_q, '0, 1'b0, 1'b0);
          end
        end

        MSG_FWD_GETS: begin
          // Appendix A rows 1017/1018 + defensive rows
          if (state == L1_E && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b0, 1'b0);  // clean
          else if (state == L1_M && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b1, 1'b0);  // dirty
          else if (state == L1_S && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b0, 1'b0);  // defensive: see R5
          else
            send(MSG_INVACK, rx_addr, '0, 1'b0, 1'b0);      // I / EI_A / MI_A / transient
        end

        MSG_FWD_GETM: begin
          if (state == L1_E && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b0, 1'b0);
          else if (state == L1_M && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b1, 1'b0);
          else if (state == L1_S && rx_addr == addr_q)
            send(MSG_DATAFWD, addr_q, data_q, 1'b0, 1'b0);  // defensive: see R5
          else
            send(MSG_INVACK, rx_addr, '0, 1'b0, 1'b0);
        end

        MSG_INV: begin
          // M: PUTM then INVACK (two flit streams, order preserved in the queue)
          if (state == L1_M && rx_addr == addr_q)
            send(MSG_PUTM, addr_q, data_q, 1'b1, 1'b0);
          send(MSG_INVACK, rx_addr, '0, 1'b0, 1'b0);
        end

        MSG_PUTACK: begin
          // B2: victim released — the deferred miss request follows the release on VC0
          if (evict_pend && rx_addr == vic_addr &&
              (state == L1_IS_D || state == L1_IM_D)) begin
            if (state == L1_IM_D) send(MSG_GETM, addr_q, '0, 1'b0, 1'b0);
            else                  send(MSG_GETS, addr_q, '0, 1'b0, 1'b0);
          end
        end

        default: ;   // UNBLOCK etc. are directory-side events; ignore at the L1
      endcase
    end
    // ---- 3. core request (stable states only; one outstanding line per tile) ----
    else if (core_req_valid && is_stable(state)) begin
      core_accept = 1'b1;
      if (state == L1_I) begin
        if (core_req_is_write) send(MSG_GETM, ca, '0, 1'b0, 1'b0);
        else                   send(MSG_GETS, ca, '0, 1'b0, 1'b0);
      end else if (hit) begin
        if (core_req_is_write && state == L1_S)
          send(MSG_GETM, addr_q, '0, 1'b0, 1'b0);           // S store hit -> SM_D
        // read hit / E or M write hit: no message
      end else begin
        // B2 conflict eviction: release the victim before the miss request
        case (state)
          L1_M:    send(MSG_PUTM, addr_q, data_q, 1'b1, 1'b0);
          default: send(MSG_PUTS, addr_q, '0, 1'b0, 1'b0);   // E or S victim
        endcase
        if (state == L1_S) begin                            // S victim needs no PUTACK
          if (core_req_is_write) send(MSG_GETM, ca, '0, 1'b0, 1'b0);
          else                   send(MSG_GETS, ca, '0, 1'b0, 1'b0);
        end
      end
    end
  end

  // ── TX capacity + flit retire ─────────────────────────────────────────────
  logic [2:0] tx_free;
  logic       tx_push_ok;
  logic       tx_pop;

  assign tx_pop     = tx_busy && ({2'b00, tx_flt} == (tx_len - 6'd1));
  assign tx_free    = 3'd4 - tx_cnt + (tx_pop ? 3'd1 : 3'd0);
  assign tx_push_ok = (iss_n != 2'd0) && ({1'b0, iss_n} <= tx_free);

  // ── sequential state update ───────────────────────────────────────────────
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state       <= L1_I;
      addr_q      <= '0;
      data_q      <= '0;
      wdata_q     <= '0;
      vic_valid   <= 1'b0;
      vic_state   <= L1_I;
      vic_addr    <= '0;
      evict_pend  <= 1'b0;
      core_rsp_valid <= 1'b0;
      core_rsp_rdata <= '0;
      abort_o     <= 1'b0;
      tx_wr <= '0; tx_rd <= '0; tx_cnt <= '0;
      tx_busy <= 1'b0; tx_flt <= '0; tx_len <= '0;
      tx_cur_msg <= MSG_RSVD0;
      tx_cur_addr <= '0;
      tx_cur_data <= '0;
      tx_cur_we <= 1'b0;
      tx_cur_excl <= 1'b0;
      rx_active <= 1'b0; rx_flt <= '0;
      rx_pending <= 1'b0;
      rx_hdr_msg <= MSG_RSVD0; rx_hdr_addr <= '0;
      rx_hdr_we <= 1'b0; rx_hdr_excl <= 1'b0;
      rx_data <= '0;
      rx_msg <= MSG_RSVD0; rx_addr <= '0;
      rx_we <= 1'b0; rx_excl <= 1'b0; rx_line <= '0;
      rx_oflow_o <= 1'b0;
      tx_oflow_o <= 1'b0;
    end else begin
      core_rsp_valid <= 1'b0;
      abort_o        <= 1'b0;

      // ---- TX queue write + retire ----
      if (tx_push_ok) begin
        txq_msg[tx_wr]  <= iss0_msg;   txq_addr[tx_wr] <= iss0_addr;
        txq_data[tx_wr] <= iss0_data;  txq_we[tx_wr]   <= iss0_we;
        txq_excl[tx_wr] <= iss0_excl;
        if (iss_n == 2'd2) begin
          txq_msg[tx_wr + 1'b1]  <= iss1_msg;   txq_addr[tx_wr + 1'b1] <= iss1_addr;
          txq_data[tx_wr + 1'b1] <= iss1_data;  txq_we[tx_wr + 1'b1]   <= iss1_we;
          txq_excl[tx_wr + 1'b1] <= iss1_excl;
        end
        tx_wr <= tx_wr + iss_n;
      end
      if (tx_pop) tx_rd <= tx_rd + 1'b1;
      tx_cnt <= tx_cnt + (tx_push_ok ? {1'b0, iss_n} : 3'd0)
                       - (tx_pop ? 3'd1 : 3'd0);
      if (iss_n != 2'd0 && !tx_push_ok) tx_oflow_o <= 1'b1;  // sticky: A3.x

      // ---- TX serializer ----
      if (!tx_busy) begin
        if (tx_cnt > 3'd0) begin
          tx_busy <= 1'b1;
          tx_flt  <= 4'd0;
          tx_cur_msg  <= txq_msg[tx_rd];
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

      // ---- RX reassembly ----
      if (noc_rsp_valid) begin
        if (!rx_active) begin
          if (noc_rsp_flit[HDR_HEAD]) begin
            rx_hdr_msg  <= msg_type_t'(noc_rsp_flit[HDR_MSG_HI:HDR_MSG_LO]);
            rx_hdr_addr <= noc_rsp_flit[HDR_ADDR_HI:HDR_ADDR_LO];
            rx_hdr_we   <= noc_rsp_flit[HDR_WE];
            rx_hdr_excl <= noc_rsp_flit[HDR_EXCL];
            if (noc_rsp_flit[HDR_LEN_HI:HDR_LEN_LO] == 6'd1) begin
              rx_msg  <= msg_type_t'(noc_rsp_flit[HDR_MSG_HI:HDR_MSG_LO]);
              rx_addr <= noc_rsp_flit[HDR_ADDR_HI:HDR_ADDR_LO];
              rx_we   <= noc_rsp_flit[HDR_WE];
              rx_excl <= noc_rsp_flit[HDR_EXCL];
              rx_line <= '0;
            end else begin
              rx_active <= 1'b1;
              rx_flt    <= 4'd1;
            end
          end
        end else begin
          if (rx_flt == 4'd8) begin
            rx_active <= 1'b0;
            rx_msg  <= rx_hdr_msg;
            rx_addr <= rx_hdr_addr;
            rx_we   <= rx_hdr_we;
            rx_excl <= rx_hdr_excl;
            rx_line <= {noc_rsp_flit[63:0], rx_data[447:0]};
          end else begin
            case (rx_flt)
              4'd1: rx_data[ 63:  0] <= noc_rsp_flit[63:0];
              4'd2: rx_data[127: 64] <= noc_rsp_flit[63:0];
              4'd3: rx_data[191:128] <= noc_rsp_flit[63:0];
              4'd4: rx_data[255:192] <= noc_rsp_flit[63:0];
              4'd5: rx_data[319:256] <= noc_rsp_flit[63:0];
              4'd6: rx_data[383:320] <= noc_rsp_flit[63:0];
              4'd7: rx_data[447:384] <= noc_rsp_flit[63:0];
              default: ;
            endcase
            rx_flt <= rx_flt + 4'd1;
          end
        end
      end
      if (rx_publish) begin
        rx_pending <= 1'b1;
        if (rx_pending && !dispatch) rx_oflow_o <= 1'b1;   // sticky: A3.x
      end else if (dispatch) begin
        rx_pending <= 1'b0;
      end

      // ---- dispatch side effects ----
      if (dispatch) begin
        case (rx_msg)
          MSG_DATA: begin
            if (data_install) begin
              if (state == L1_IS_D) begin
                data_q  <= rx_line;
                if (rx_excl) state <= L1_E; else state <= L1_S;
                core_rsp_rdata <= rx_line;
                core_rsp_valid <= 1'b1;
              end else if (state == L1_IM_D) begin
                data_q  <= rx_excl ? wdata_q : rx_line;
                if (rx_excl) state <= L1_M; else state <= L1_S;
                core_rsp_rdata <= rx_excl ? wdata_q : rx_line;
                core_rsp_valid <= 1'b1;
              end else begin                                   // L1_SM_D
                if (rx_excl) begin
                  data_q  <= wdata_q;
                  state   <= L1_M;
                  core_rsp_rdata <= wdata_q;
                end else begin
                  data_q  <= rx_line;                          // defensive: not granted
                  state   <= L1_S;
                  core_rsp_rdata <= rx_line;
                end
                core_rsp_valid <= 1'b1;
              end
              vic_valid  <= 1'b0;
              evict_pend <= 1'b0;
            end
          end

          MSG_FWD_GETS: begin
            if ((state == L1_E || state == L1_M) && rx_addr == addr_q)
              state <= L1_S;
          end

          MSG_FWD_GETM: begin
            if ((state == L1_E || state == L1_M) && rx_addr == addr_q) begin
              state     <= L1_I;          // ownership transfer
              vic_valid <= 1'b0;
            end
          end

          MSG_INV: begin
            if (rx_addr == addr_q && is_held(state))
              state <= L1_I;
            else if (rx_addr == addr_q && is_miss(state)) begin
              // ruling B6 (Appendix A abort row: IS_D/IM_D/SM_D --INV--> same
              // state): the same-line INV aborts the outstanding miss. The
              // copy is invalidated now (SM_D still held S), the miss request
              // already at the directory stands, and the parked access
              // (addr_q/wdata_q) is re-driven when DATA re-acquires the line.
              // INVACK (VC2) is issued combinationally above — never deferred.
              data_q  <= '0;
              abort_o <= 1'b1;
            end
          end

          MSG_PUTACK: begin
            if ((state == L1_EI_A || state == L1_MI_A) && rx_addr == addr_q) begin
              state     <= L1_I;          // release the way
              vic_valid <= 1'b0;
            end else if (evict_pend && rx_addr == vic_addr) begin
              evict_pend <= 1'b0;         // B2 release done; GET issued in comb
            end
          end

          default: ;
        endcase
      end

      // ---- core request side effects ----
      if (core_accept) begin
        if (state == L1_I) begin
          addr_q    <= ca;
          wdata_q   <= core_req_wdata;
          if (core_req_is_write) state <= L1_IM_D; else state <= L1_IS_D;
          vic_valid <= 1'b0;
        end else if (hit) begin
          if (core_req_is_write) begin
            if (state == L1_S) begin
              wdata_q <= core_req_wdata;
              state   <= L1_SM_D;       // GETM issued in comb
            end else begin
              wdata_q <= core_req_wdata;
              data_q  <= core_req_wdata;
              state   <= L1_M;          // E -> M silent upgrade; M write in place
              core_rsp_rdata <= core_req_wdata;
              core_rsp_valid <= 1'b1;
            end
          end else begin
            core_rsp_rdata <= data_q;
            core_rsp_valid <= 1'b1;
          end
        end else begin                  // conflict (B2)
          vic_valid  <= 1'b1;
          vic_state  <= state;
          vic_addr   <= addr_q;
          addr_q     <= ca;
          wdata_q    <= core_req_wdata;
          if (core_req_is_write) state <= L1_IM_D; else state <= L1_IS_D;
          evict_pend <= (state != L1_S);   // S victim: no PUTACK wait (rule 9)
        end
      end

      // ---- proactive eviction side effects ----
      if (core_evict_valid && is_held(state) && !vic_valid) begin
        if (state == L1_S)      state <= L1_I;      // no ack
        else if (state == L1_E) state <= L1_EI_A;
        else                    state <= L1_MI_A;
      end
    end
  end

  // ── RX publish detector (pure comb of flit stream + FSM) ──────────────────
  always_comb begin
    rx_publish = 1'b0;
    if (noc_rsp_valid) begin
      if (!rx_active)
        rx_publish = noc_rsp_flit[HDR_HEAD] &&
                     (noc_rsp_flit[HDR_LEN_HI:HDR_LEN_LO] == 6'd1);
      else
        rx_publish = (rx_flt == 4'd8);
    end
  end

  assign dispatch_o = dispatch;
  assign rx_msg_o   = rx_msg;

  // ── TX flit output ────────────────────────────────────────────────────────
  always_comb begin
    noc_req_valid = tx_busy;
    noc_req_flit  = '0;
    if (tx_busy) begin
      if (tx_flt == 4'd0) begin
        noc_req_flit = mk_hdr(msg_type_t'(tx_cur_msg), tx_cur_addr,
                              tx_cur_we, tx_cur_excl);
      end else begin
        case (tx_flt)
          4'd1: noc_req_flit = tx_cur_data[ 63:  0];
          4'd2: noc_req_flit = tx_cur_data[127: 64];
          4'd3: noc_req_flit = tx_cur_data[191:128];
          4'd4: noc_req_flit = tx_cur_data[255:192];
          4'd5: noc_req_flit = tx_cur_data[319:256];
          4'd6: noc_req_flit = tx_cur_data[383:320];
          4'd7: noc_req_flit = tx_cur_data[447:384];
          4'd8: noc_req_flit = tx_cur_data[511:448];
          default: ;
        endcase
      end
    end
  end

  // ── R3 bank port: unused (all L1 data arrives via directory DATA) ─────────
  assign bank_req_valid    = 1'b0;
  assign bank_req_is_write = 1'b0;
  assign bank_req_addr     = '0;
  assign bank_req_wdata    = '0;
  assign bank_req_wstrb    = '0;
  assign bank_req_source   = SRC_L1;
  wire _unused_ok = &{1'b0, bank_rsp_valid, bank_rsp_rdata, bank_rsp_rstrb,
                      bank_rsp_rlast, 1'b0};

  // ── observability ─────────────────────────────────────────────────────────
  assign mesi_state  = state;
  assign line_addr   = addr_q;
  assign line_data   = data_q;
  assign vic_valid_o = vic_valid;
  assign vic_state_o = vic_state;
  assign vic_addr_o  = vic_addr;

endmodule
`endif
