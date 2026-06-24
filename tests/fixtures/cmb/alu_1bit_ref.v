module alu_1bit (
  input        a,
  input        b,
  input  [1:0] op,
  output reg   result
);
  always @(*) begin
    case (op)
      2'b00: result = a & b;
      2'b01: result = a | b;
      2'b10: result = a ^ b;
      2'b11: result = ~a;
      default: result = 1'b0;
    endcase
  end
endmodule
