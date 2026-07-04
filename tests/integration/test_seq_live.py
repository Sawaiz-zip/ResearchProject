"""
T014 — minimal live SEQ smoke test. Marked `live`; skipped without an API key.
Runs the dff fixture end-to-end; asserts it is classified SEQ and reaches a result.
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


def test_live_dff_end_to_end():
    from dotenv import load_dotenv
    load_dotenv()

    from pipeline.config import AblationMode, PipelineConfig
    from pipeline.graph import build_graph

    state = {
        "nl_description": (
            "A positive-edge-triggered D flip-flop: on each rising edge of clk, "
            "output q takes the value of input d."
        ),
        "module_name": "dff", "golden_dut": "", "mutant_duts": [],
        "circuit_type": "CMB", "dut_rtl": "", "spec": {}, "scenarios": [],
        "driver_rtl": "", "checker_py": "", "pyverilog_report": {},
        "error_report": [], "last_error_report": [], "scenario_results": [],
        "eval_dut_source": "generated", "repair_iter": 0, "max_repair_iter": 3,
        "oscillation_detected": False, "last_repair_signature": "", "feedback_source": "",
        "repair_history": [], "eval0_pass": False, "eval1_pass": False,
        "eval2_pass_rate": 0.0, "failure_stage": None, "final_status": "failed_compile",
        "run_id": "live_dff", "llm_calls": [],
    }
    final = build_graph(PipelineConfig(mode=AblationMode.HYBRID)).invoke(state)

    assert final.get("circuit_type") == "SEQ"
    assert final.get("dut_rtl", "").strip()
    assert final.get("final_status")
