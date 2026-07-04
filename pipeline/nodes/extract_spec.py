"""
Node 1b — Extract structured JSON spec from NL description + golden DUT.
Model: Sonnet (needs to understand Verilog port declarations precisely).
"""

import json

from pipeline.config import PipelineConfig
from pipeline.llm import extract_json, llm_call, render_prompt
from pipeline.state import GraphState


def extract_spec_node(state: GraphState) -> dict:
    cfg = PipelineConfig()
    # Consume the generated DUT (fallback to a supplied golden DUT for legacy
    # fixtures / benchmark inputs that pre-seed golden_dut).
    dut = state.get("dut_rtl") or state.get("golden_dut", "")
    prompt = render_prompt(
        "extract_spec.j2",
        nl_description=state["nl_description"],
        dut=dut,
        module_name=state["module_name"],
    )
    text, log = llm_call(
        node="extract_spec",
        model=cfg.model_strong,
        prompt=prompt,
        run_id=state["run_id"],
    )
    try:
        spec = extract_json(text)
        if not isinstance(spec, dict):
            spec = {}
    except (json.JSONDecodeError, AttributeError, ValueError):
        spec = {}

    return {
        "spec": spec,
        "llm_calls": [log],
    }
