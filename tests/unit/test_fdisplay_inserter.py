"""T012 — deterministic $fdisplay/$monitor standardiser (no LLM)."""

from pipeline.standardiser.fdisplay_inserter import (
    insert_fdisplay,
    _find_outputs,
    _is_observed,
    _has_clock_gen,
)

_SPEC = {"ports": {"inputs": [{"name": "clk"}, {"name": "d"}],
                   "outputs": [{"name": "q"}], "clock": "clk"}}

_TB_UNOBSERVED = (
    "module testbench;\n"
    "  reg clk, d; wire q;\n"
    "  dff uut(.clk(clk), .d(d), .q(q));\n"
    "  initial begin clk=0; d=1; #10; $finish; end\n"
    "endmodule\n"
)

_TB_OBSERVED = (
    "module testbench;\n"
    "  reg clk, d; wire q;\n"
    "  dff uut(.clk(clk), .d(d), .q(q));\n"
    "  always #5 clk = ~clk;\n"
    "  initial begin d=1; #10;\n"
    '    if (q===1) $display("PASS: load"); else $display("FAIL: load");\n'
    "    $finish; end\n"
    "endmodule\n"
)


def test_find_outputs():
    assert _find_outputs(_SPEC) == ["q"]


def test_inserts_monitor_for_unobserved_output():
    out = insert_fdisplay(_TB_UNOBSERVED, _SPEC)
    assert "$monitor" in out
    assert _is_observed(out, "q")


def test_inserts_clock_when_absent():
    out = insert_fdisplay(_TB_UNOBSERVED, _SPEC)
    assert "clk = ~clk" in out
    assert _has_clock_gen(out, "clk")


def test_noop_when_all_observed_and_clocked():
    # q is checked and clk toggles → nothing to add.
    out = insert_fdisplay(_TB_OBSERVED, _SPEC)
    assert out == _TB_OBSERVED


def test_idempotent():
    once = insert_fdisplay(_TB_UNOBSERVED, _SPEC)
    twice = insert_fdisplay(once, _SPEC)
    assert once == twice


def test_fail_safe_on_garbage():
    garbage = "this is not verilog at all"
    assert insert_fdisplay(garbage, _SPEC) == garbage    # no endmodule → unchanged


def test_does_not_emit_a_dut_module():
    out = insert_fdisplay(_TB_UNOBSERVED, _SPEC)
    # only the testbench module remains; the standardiser never adds a DUT
    assert out.count("module ") == _TB_UNOBSERVED.count("module ")


def test_empty_input_unchanged():
    assert insert_fdisplay("", _SPEC) == ""


def test_no_clock_added_when_clk_not_in_tb():
    # spec says clock 'clk' but the TB never references it → do not fabricate one.
    spec = {"ports": {"outputs": [{"name": "q"}], "clock": "clk"}}
    tb = "module testbench;\n wire q;\n dummy u(.q(q));\n initial $finish;\nendmodule\n"
    out = insert_fdisplay(tb, spec)
    assert "clk = ~clk" not in out       # no fabricated clock
    assert "$monitor" in out             # but q still made observable
