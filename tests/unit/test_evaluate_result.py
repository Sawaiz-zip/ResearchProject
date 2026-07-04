"""T025 — evaluate_node result JSON: new fields + eval DUT selection."""

import json

from pipeline.nodes.evaluate import evaluate_node


def _state(**over):
    s = {
        "run_id": "evaltest",
        "module_name": "top_module",
        "circuit_type": "CMB",
        "nl_description": "a half adder circuit",
        "dut_rtl": "module top_module(); endmodule",
        "golden_dut": "",
        "driver_rtl": "module testbench; endmodule",
        "mutant_duts": ["m1"],   # skip mutant generation (no LLM)
        "repair_iter": 0,
        "llm_calls": [
            {"node": "gen_dut", "tokens_in": 20, "tokens_out": 8, "temperature": 0.7},
        ],
    }
    s.update(over)
    return s


def _read_result(run_id):
    import pathlib
    root = pathlib.Path(__file__).parent.parent.parent
    return json.loads((root / "results" / f"{run_id}.json").read_text())


def test_result_has_new_fields_generated_dut(mock_icarus):
    evaluate_node(_state(run_id="evt_gen"))
    r = _read_result("evt_gen")
    assert r["nl_description"] == "a half adder circuit"
    assert r["eval_dut_source"] == "generated"
    assert r["scenario_results"] == [
        {"name": "zero", "passed": True},
        {"name": "both", "passed": True},
    ]
    assert r["scenarios_passed"] == 2
    assert r["scenarios_total"] == 2
    assert r["tokens_in_total"] == 20
    assert r["tokens_out_total"] == 8
    assert r["dut_rtl"] == "module top_module(); endmodule"


def test_eval_dut_source_golden_when_present(mock_icarus):
    evaluate_node(_state(run_id="evt_gold", golden_dut="module golden(); endmodule"))
    r = _read_result("evt_gold")
    assert r["eval_dut_source"] == "golden"
