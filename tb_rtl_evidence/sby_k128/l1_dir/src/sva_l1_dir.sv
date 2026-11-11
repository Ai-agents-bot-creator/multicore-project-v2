// sva_l1_dir.sv — A1/A2/A3/A7 slice assertions for the co-landed L1 MESI + dir_ctrl.
//
// Slice model: ONE line (all traffic is on the single directory entry). The
// §16.3 per-line arrays and the 4x4 set are out of scope.
//
// Yosys 0.70 has no `bind`, so the .sby harness instantiates this checker and
// wires the observability ports. A bind-capable simulator (xsim) can attach the
// same checker non-invasively with:
//     bind fml_l1_dir sva_l1_dir u_sva (.*);
//
// A2.5 ("Owner is only consulted in DIR_E/DIR_M") is a coding-style property,
// not an SVA-expressible one; it is recorded as R5 in 01_DECISION_LOG.md.
`ifndef SVA_L1_DIR_SV
`define SVA_L1_DIR_SV

module sva_l1_dir import tile_pkg::*; (
    input logic                  clk,
    input logic                  rst_n,
    input l1_state_t             l1_0_state,
    input l1_state_t             l1_1_state,
    input dir_state_t            dir_state,
    input logic [TILE_COUNT-1:0] dir_sharers,
    input logic [TILE_ID_W-1:0]  dir_owner,
    input pending_op_t           dir_pending_op,
    input logic [TILE_ID_W-1:0]  dir_req_tile,
    input logic                  dir_rsp_valid,
    input logic [FLIT_W-1:0]     dir_rsp_flit,
    input logic                  dir_rxq_empty,
    input msg_type_t             dir_rx_msg,
    input logic [TILE_ID_W-1:0]  dir_rx_src,
    input logic                  l1_0_dispatch,
    input msg_type_t             l1_0_rx_msg,
    input logic                  l1_1_dispatch,
    input msg_type_t             l1_1_rx_msg
);

  localparam int NT = 2;   // L1 controllers instantiated in the formal harness

  function automatic logic is_held(input l1_state_t s);
    return (s == L1_S) || (s == L1_E) || (s == L1_M);
  endfunction
  function automatic logic is_excl(input l1_state_t s);
    return (s == L1_E) || (s == L1_M);
  endfunction
  function automatic logic is_wait(input dir_state_t s);
    return (s == DIR_MEM_WAIT) || (s == DIR_FWD_WAIT) || (s == DIR_INV_WAIT);
  endfunction

  logic holder0, holder1, s0, s1, own0, own1;
  assign holder0 = is_excl(l1_0_state);
  assign holder1 = is_excl(l1_1_state);
  assign s0      = (l1_0_state == L1_S);
  assign s1      = (l1_1_state == L1_S);
  // The owner may already be in its release transient while PUTS/PUTM is in flight.
  assign own0    = (l1_0_state == L1_E) || (l1_0_state == L1_M) ||
                   (l1_0_state == L1_EI_A) || (l1_0_state == L1_MI_A);
  assign own1    = (l1_1_state == L1_E) || (l1_1_state == L1_M) ||
                   (l1_1_state == L1_EI_A) || (l1_1_state == L1_MI_A);

  always_ff @(posedge clk) if (rst_n) begin

    // ── A1 — MESI invariants ────────────────────────────────────────────────
    a1_1: assert (!(l1_0_state == L1_M && l1_1_state == L1_M));
    a1_2: assert (!(l1_0_state == L1_E && l1_1_state == L1_E));
    a1_3: assert (!((s0 && (holder1)) || (s1 && (holder0))));
    a1_4a: assert (!(l1_0_state == L1_M && is_held(l1_1_state)));
    a1_4b: assert (!(l1_1_state == L1_M && is_held(l1_0_state)));

    // ── A2 — directory invariants ───────────────────────────────────────────
    // A2.1 DIR_I iff no stable L1 holds the line.
    a2_1: assert (!(dir_state == DIR_I &&
                    (is_held(l1_0_state) || is_held(l1_1_state))));
    // A2.2 DIR_S => sharers are exactly the S copies.
    a2_2: assert (dir_state != DIR_S ||
                  dir_sharers == ((s0 ? 1 : 0) | (s1 ? 2 : 0)));
    // A2.3 DIR_E/M => the only holder is Owner (a release transient still counts).
    a2_3: assert (!((dir_state == DIR_E || dir_state == DIR_M) &&
                    !((dir_owner == 0 && own0 && !is_held(l1_1_state)) ||
                      (dir_owner == 1 && own1 && !is_held(l1_0_state)))));
    // A2.4 DIR_I => Owner and sharers cleared (valid is encoded by state != DIR_I).
    a2_4: assert (dir_state != DIR_I || (dir_sharers == '0 && dir_owner == '0));
    // A2.6 DIR_E/M => Owner < NT and sharers == {Owner}.
    a2_6: assert (!((dir_state == DIR_E || dir_state == DIR_M) &&
                    ((dir_owner >= NT) || (dir_sharers != (1 << dir_owner)))));
    // No sharer bit may name a tile that is not in this instance.
    a2_6b: assert ((dir_sharers >> NT) == '0);
    // A2.7 every transient has a pending operation (valid is implied by state).
    a2_7: assert (!is_wait(dir_state) || dir_pending_op != POP_NONE);

    // ── A3 — message protocol (safety half) ─────────────────────────────────
    // No DATA without a pending request, and always to the requesting tile.
    if (dir_rsp_valid && dir_rsp_flit[HDR_HEAD]) begin
      if (msg_type_t'(dir_rsp_flit[HDR_MSG_HI:HDR_MSG_LO]) == MSG_DATA) begin
        a3_1_data: assert (dir_pending_op != POP_NONE);
        a3_1_dst:  assert (dir_rsp_flit[HDR_DEST_LO +: TILE_ID_W] == dir_req_tile);
      end
      // A forward exists only while an owner exists and goes to that owner.
      if (msg_type_t'(dir_rsp_flit[HDR_MSG_HI:HDR_MSG_LO]) == MSG_FWD_GETS ||
          msg_type_t'(dir_rsp_flit[HDR_MSG_HI:HDR_MSG_LO]) == MSG_FWD_GETM) begin
        a3_1_fwd_state: assert (dir_state == DIR_E || dir_state == DIR_M ||
                                dir_state == DIR_FWD_WAIT);
        a3_1_fwd_dst:   assert (dir_rsp_flit[HDR_DEST_LO +: TILE_ID_W] == dir_owner);
      end
    end

    // ── A7 — directory FSM legality ─────────────────────────────────────────
    // Each *_WAIT exits only on UNBLOCK from the pending requester.
    if ($past(rst_n) && is_wait($past(dir_state)) &&
        dir_state != $past(dir_state)) begin
      a7_dir_exit: assert (!$past(dir_rxq_empty) &&
                           $past(dir_rx_msg) == MSG_UNBLOCK &&
                           $past(dir_rx_src) == $past(dir_req_tile));
    end

    // ── A7 — L1 FSM legality (both tiles) ───────────────────────────────────
    if ($past(rst_n)) begin
      case ($past(l1_0_state))
        L1_IS_D: a7_0_isd: assert (l1_0_state == L1_IS_D ||
                                   l1_0_state == L1_S || l1_0_state == L1_E);
        L1_IM_D: a7_0_imd: assert (l1_0_state == L1_IM_D ||
                                   l1_0_state == L1_M || l1_0_state == L1_S);
        L1_SM_D: a7_0_smd: assert (l1_0_state == L1_SM_D ||
                                   l1_0_state == L1_M || l1_0_state == L1_S);
        L1_EI_A: a7_0_eia: assert (l1_0_state == L1_EI_A || l1_0_state == L1_I);
        L1_MI_A: a7_0_mia: assert (l1_0_state == L1_MI_A || l1_0_state == L1_I);
        default: ;
      endcase
      case ($past(l1_1_state))
        L1_IS_D: a7_1_isd: assert (l1_1_state == L1_IS_D ||
                                   l1_1_state == L1_S || l1_1_state == L1_E);
        L1_IM_D: a7_1_imd: assert (l1_1_state == L1_IM_D ||
                                   l1_1_state == L1_M || l1_1_state == L1_S);
        L1_SM_D: a7_1_smd: assert (l1_1_state == L1_SM_D ||
                                   l1_1_state == L1_M || l1_1_state == L1_S);
        L1_EI_A: a7_1_eia: assert (l1_1_state == L1_EI_A || l1_1_state == L1_I);
        L1_MI_A: a7_1_mia: assert (l1_1_state == L1_MI_A || l1_1_state == L1_I);
        default: ;
      endcase

      // A transient leaves only via its defined event.
      if ($past(l1_0_state) == L1_IS_D || $past(l1_0_state) == L1_IM_D ||
          $past(l1_0_state) == L1_SM_D)
        a7_0_data: assert (l1_0_state == $past(l1_0_state) ||
                           ($past(l1_0_dispatch) && $past(l1_0_rx_msg) == MSG_DATA));
      if ($past(l1_1_state) == L1_IS_D || $past(l1_1_state) == L1_IM_D ||
          $past(l1_1_state) == L1_SM_D)
        a7_1_data: assert (l1_1_state == $past(l1_1_state) ||
                           ($past(l1_1_dispatch) && $past(l1_1_rx_msg) == MSG_DATA));
      if ($past(l1_0_state) == L1_EI_A || $past(l1_0_state) == L1_MI_A)
        a7_0_ack: assert (l1_0_state == $past(l1_0_state) ||
                          ($past(l1_0_dispatch) && $past(l1_0_rx_msg) == MSG_PUTACK));
      if ($past(l1_1_state) == L1_EI_A || $past(l1_1_state) == L1_MI_A)
        a7_1_ack: assert (l1_1_state == $past(l1_1_state) ||
                          ($past(l1_1_dispatch) && $past(l1_1_rx_msg) == MSG_PUTACK));
    end
  end
endmodule
`endif
