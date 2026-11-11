module tb_smoke (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [3:0]  a,
    input  logic [3:0]  b,
    input  logic [1:0]  op,
    output logic [3:0]  y
);
    always_comb begin
        case (op)
            2'b00: y = a + b;      // add
            2'b01: y = a - b;      // sub
            default: y = a;        // pass
        endcase
    end
endmodule