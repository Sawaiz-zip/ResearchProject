"""
T027 — minimal live-API smoke test. Marked `live`; skipped automatically when no
API key is configured so the default suite spends ZERO tokens.
Run explicitly with:  pytest -m live
"""

import os

import pytest

_HAS_KEY = bool(
    os.environ.get("ANTHROPIC_API_KEY")
    or (os.environ.get("LLM_API_KEY") and os.environ.get("LLM_BASE_URL"))
    or os.environ.get("OPENAI_API_KEY")
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not _HAS_KEY, reason="no LLM API key configured"),
]


def test_live_half_adder_end_to_end():
    from dotenv import load_dotenv
    load_dotenv()

    from pipeline.config import AblationMode, PipelineConfig
    from pipeline.graph import build_graph

    state = {
        "nl_description": (
            "A half adder: two 1-bit inputs a and b; outputs sum (a XOR b) "
            "and cout (a AND b)."
        ),
        "module_name": "top_module",
        "golden_dut": "",
        "mutant_duts": [],
        "circuit_type": "CMB",
        "dut_rtl": "",
        "spec": {}, "scenarios": [], "driver_rtl": "", "checker_py": "",
        "pyverilog_report": {}, "error_report": [], "last_error_report": [],
        "scenario_results": [], "eval_dut_source": "generated",
        "repair_iter": 0, "max_repair_iter": 3, "oscillation_detected": False,
        "eval0_pass": False, "eval1_pass": False, "eval2_pass_rate": 0.0,
        "failure_stage": None, "final_status": "failed_compile",
        "run_id": "live_test", "llm_calls": [],
    }

    graph = build_graph(PipelineConfig(mode=AblationMode.HYBRID))
    final = graph.invoke(state)

    assert final.get("final_status")
    assert final.get("dut_rtl", "").strip()          # a DUT was generated
    assert final.get("llm_calls")
    assert all("temperature" in c for c in final["llm_calls"])
