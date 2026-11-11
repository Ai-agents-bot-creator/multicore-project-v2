// l2_bank.sv — L2 bank stub (R3 port freeze)
// Header: "Stub for R3 port freeze. Implementation lands in the next work order."
// Implements the frozen port from tile_pkg.sv:
//   req:  valid, is_write, addr[ADDR_W-1:0], wdata[511:0], wstrb[63:0], source : bank_src_e
//   rsp:  valid, rdata[511:0], rstrb[63:0], rlast
//   status: dtr_busy
`ifndef L2_BANK_SV
`define L2_BANK_SV

module l2_bank import tile_pkg::*; (
    input  logic                      clk,
    input  logic                      rst_n,
    // Request port
    input  logic                      req_valid,
    input  logic                      req_is_write,
    input  logic [ADDR_W-1:0]         req_addr,
    input  logic [LINE_BITS-1:0]      req_wdata,
    input  logic [LINE_BITS/8-1:0]    req_wstrb,
    input  bank_src_e                 req_source,
    // Response port
    output logic                      rsp_valid,
    output logic [LINE_BITS-1:0]      rsp_rdata,
    output logic [LINE_BITS/8-1:0]    rsp_rstrb,
    output logic                      rsp_rlast,
    // Status
    output logic                      dtr_busy
);
    // Stub: no PLRU, no state machine, no write logic
    // Implementation lands in the next work order.
    always_comb begin
        rsp_valid = 1'b0;
        rsp_rdata = '0;
        rsp_rstrb = '0;
        rsp_rlast = 1'b0;
        dtr_busy  = 1'b0;
    end

endmodule
`endif