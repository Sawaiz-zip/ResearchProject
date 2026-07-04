module counter_4bit(
  input        clk,
  input        rst,
  output reg [3:0] out
);
  always @(posedge clk) begin
    if (rst)
      out <= 4'b0000;
    else
      out <= out + 4'b0001;
  end
endmodule
