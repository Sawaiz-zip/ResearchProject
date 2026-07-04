"""
T018 — minimal live repair smoke test. Marked `live`; skipped without an API key.
Does not assert success (model-dependent) — only that the loop ran and reported.
Run with:  pytest -m live
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


def test_live_repair_reports_history():
    from dotenv import load_dotenv
    load_dotenv()

    from pipeline.config import AblationMode, PipelineConfig
    from pipeline.graph import build_graph

    state = {
        "nl_description": (
            "A 1-bit full adder: inputs a, b, cin; outputs sum = a^b^cin and "
            "cout = majority(a,b,cin)."
        ),
        "module_name": "full_adder", "golden_dut": "", "mutant_duts": [],
        "circuit_type": "CMB", "dut_rtl": "", "spec": {}, "scenarios": [],
        "driver_rtl": "", "checker_py": "", "pyverilog_report": {},
        "error_report": [], "last_error_report": [], "scenario_results": [],
        "eval_dut_source": "generated", "repair_iter": 0, "max_repair_iter": 3,
        "oscillation_detected": False, "last_repair_signature": "", "feedback_source": "",
        "repair_history": [], "eval0_pass": False, "eval1_pass": False,
        "eval2_pass_rate": 0.0, "failure_stage": None, "final_status": "failed_compile",
        "run_id": "live_repair", "llm_calls": [],
    }
    final = build_graph(PipelineConfig(mode=AblationMode.HYBRID)).invoke(state)

    assert final.get("final_status") in {
        "success", "failed_eval1", "failed_eval2", "oscillated", "exhausted_iters",
        "failed_compile",
    }
    assert final.get("repair_iter", 0) <= final["max_repair_iter"]
