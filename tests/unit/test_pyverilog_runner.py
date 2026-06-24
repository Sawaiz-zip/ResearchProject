"""
Unit tests for pyverilog_runner.run().
Uses hand-crafted minimal Verilog to isolate each check category.
"""
import json
import pytest
from pipeline.analysis.pyverilog_runner import run
from pipeline.analysis.error_taxonomy import ErrorType

# ── Fixtures ─────────────────────────────────────────────────────────────────

HALF_ADDER_DUT = """\
module half_adder(input a, input b, output sum, output cout);
    assign sum = a ^ b;
    assign cout = a & b;
endmodule
"""

# All four ports connected correctly
CORRECT_TB = """\
module tb_half_adder;
    reg a, b;
    wire sum, cout;
    half_adder dut(.a(a), .b(b), .sum(sum), .cout(cout));
    initial begin
        a = 0; b = 0; #10;
        if (sum !== 1'b0 || cout !== 1'b0)
            $display("FAIL: zero_plus_zero");
        else
            $display("PASS: zero_plus_zero");
        $finish;
    end
endmodule
"""

# cout port omitted from instantiation
MISSING_PORT_TB = """\
module tb_half_adder;
    reg a, b;
    wire sum;
    half_adder dut(.a(a), .b(b), .sum(sum));
    initial begin
        a = 0; b = 0; #10;
        if (sum !== 1'b0) $display("FAIL: test");
        else $display("PASS: test");
        $finish;
    end
endmodule
"""

# Port name "wrong_port" does not exist in the DUT
WRONG_PORT_NAME_TB = """\
module tb_half_adder;
    reg a, b;
    wire s, c;
    half_adder dut(.a(a), .b(b), .wrong_port(s), .cout(c));
    initial begin
        a = 0; b = 0; #10;
        $display("PASS: test");
        $finish;
    end
endmodule
"""

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_clean_tb_no_errors():
    report = run(CORRECT_TB, HALF_ADDER_DUT, module_name="half_adder")
    assert report.parse_ok
    assert report.is_clean(), f"Expected clean but got port_errors={report.port_errors}"


def test_missing_port_flagged():
    report = run(MISSING_PORT_TB, HALF_ADDER_DUT, module_name="half_adder")
    assert report.parse_ok
    error_types = [e.error_type for e in report.port_errors]
    assert ErrorType.PORT_BINDING_MISMATCH in error_types, (
        f"Expected PORT_BINDING_MISMATCH in port_errors, got: {error_types}"
    )


def test_wrong_portname_flagged():
    report = run(WRONG_PORT_NAME_TB, HALF_ADDER_DUT, module_name="half_adder")
    assert report.parse_ok
    error_types = [e.error_type for e in report.port_errors]
    assert ErrorType.PORT_BINDING_MISMATCH in error_types, (
        f"Expected PORT_BINDING_MISMATCH for unknown port name, got: {error_types}"
    )


def test_parse_ok_on_valid_verilog():
    report = run(CORRECT_TB, HALF_ADDER_DUT, module_name="half_adder")
    assert report.parse_ok is True
    assert report.parser_used == "pyverilog"


def test_report_is_json_serialisable():
    report = run(CORRECT_TB, HALF_ADDER_DUT, module_name="half_adder")
    # Must not raise
    serialised = json.dumps(report.to_dict())
    parsed = json.loads(serialised)
    assert "parse_ok" in parsed
    assert "port_errors" in parsed
