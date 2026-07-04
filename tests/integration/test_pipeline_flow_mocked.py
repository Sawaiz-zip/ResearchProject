"""
T026 — full pipeline flow, fully offline (fake_llm + mocked Icarus).
Covers: CMB generated-DUT path, SEQ classification, golden-vs-generated eval DUT,
repair-vs-evaluate routing (should_repair), and robustness to malformed output.
Zero API tokens.
"""

from pipeline.config import AblationMode, PipelineConfig
from pipeline.graph import build_graph
from pipeline.nodes.repair import should_repair


def _initial_state(run_id, **over):
    s = {
        "nl_description": "a half adder with sum and carry out",
        "module_name": "top_module",
        "golden_dut": "",
        "mutant_duts": ["m1", "m2"],   # pre-seeded → no mutant LLM calls
        "circuit_type": "CMB",
        "dut_rtl": "",
        "spec": {},
        "scenarios": [],
        "driver_rtl": "",
        "checker_py": "",
        "pyverilog_report": {},
        "error_report": [],
        "last_error_report": [],
        "scenario_results": [],
        "eval_dut_source": "generated",
        "repair_iter": 0,
        "max_repair_iter": 3,
        "oscillation_detected": False,
        "eval0_pass": False,
        "eval1_pass": False,
        "eval2_pass_rate": 0.0,
        "failure_stage": None,
        "final_status": "failed_compile",
        "run_id": run_id,
        "llm_calls": [],
    }
    s.update(over)
    return s


def test_cmb_flow_generates_dut_and_completes(fake_llm, mock_icarus):
    graph = build_graph(PipelineConfig(mode=AblationMode.HYBRID))
    final = graph.invoke(_initial_state("flow_cmb"))

    assert final["circuit_type"] == "CMB"
    assert "module" in final["dut_rtl"]          # gen_dut produced a DUT
    assert final["spec"]                          # extract_spec consumed it
    assert final["scenarios"]                     # gen_scenarios ran
    assert final["driver_rtl"]                    # gen_driver ran
    assert final["checker_py"]                    # gen_checker ran
    assert final["final_status"] == "success"
    # every LLM node logged a temperature
    assert all("temperature" in c for c in final["llm_calls"])


def test_seq_classification_propagates(fake_llm_factory, mock_icarus):
    fake_llm_factory({"classify": '{"circuit_type": "SEQ"}'})
    graph = build_graph(PipelineConfig(mode=AblationMode.HYBRID))
    final = graph.invoke(_initial_state("flow_seq"))
    assert final["circuit_type"] == "SEQ"
    assert final["dut_rtl"]


def test_golden_dut_used_for_eval_only(fake_llm, mock_icarus):
    graph = build_graph(PipelineConfig(mode=AblationMode.HYBRID))
    final = graph.invoke(_initial_state(
        "flow_gold", golden_dut="module top_module(); endmodule"
    ))
    # Generation still produced its own DUT...
    assert "module" in final["dut_rtl"]
    # ...but evaluation used the golden one.
    assert final["eval_dut_source"] == "golden"


def test_malformed_output_does_not_abort(fake_llm_factory, mock_icarus):
    # classify + extract_spec + scenarios return junk; nodes must fall back.
    fake_llm_factory({
        "classify": "I think this is combinational, definitely",
        "extract_spec": "not json at all {{{",
        "gen_scenarios": "oops not a list",
    })
    graph = build_graph(PipelineConfig(mode=AblationMode.HYBRID))
    final = graph.invoke(_initial_state("flow_junk"))
    assert final["final_status"] in {
        "success", "failed_compile", "failed_eval1", "failed_eval2",
    }
    assert final["circuit_type"] in {"CMB", "SEQ"}


def test_should_repair_routing():
    # BASELINE never repairs
    assert should_repair(_initial_state("r"), AblationMode.BASELINE) == "evaluate"
    # HYBRID with no errors → evaluate
    assert should_repair(_initial_state("r"), AblationMode.HYBRID) == "evaluate"
    # HYBRID with errors under the cap → repair
    st = _initial_state("r", error_report=[{"error_type": "x"}])
    assert should_repair(st, AblationMode.HYBRID) == "repair"
    # oscillation → evaluate
    st_osc = _initial_state("r", error_report=[{"error_type": "x"}],
                           oscillation_detected=True)
    assert should_repair(st_osc, AblationMode.HYBRID) == "evaluate"
    # exhausted iters → evaluate
    st_max = _initial_state("r", error_report=[{"error_type": "x"}],
                           repair_iter=3, max_repair_iter=3)
    assert should_repair(st_max, AblationMode.HYBRID) == "evaluate"
