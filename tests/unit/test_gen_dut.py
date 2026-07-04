"""T023 — gen_dut node (offline via fake_llm)."""

from pipeline.nodes.gen_dut import gen_dut_node


def _state(**over):
    s = {
        "nl_description": "a half adder",
        "circuit_type": "CMB",
        "module_name": "top_module",
        "run_id": "test",
    }
    s.update(over)
    return s


def test_gen_dut_writes_dut_rtl(fake_llm):
    out = gen_dut_node(_state())
    assert "module" in out["dut_rtl"]
    assert len(out["llm_calls"]) == 1
    assert out["llm_calls"][0]["node"] == "gen_dut"
    assert "temperature" in out["llm_calls"][0]


def test_gen_dut_fallback_on_empty_extraction(fake_llm_factory):
    # Model returns bare text with no code fence → node keeps raw text.
    fake_llm_factory({"gen_dut": "module bare(); endmodule"})
    out = gen_dut_node(_state())
    assert out["dut_rtl"].strip() == "module bare(); endmodule"
