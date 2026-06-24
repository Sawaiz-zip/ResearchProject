"""
Node 1c — Generate named test scenarios from spec.
Model: Haiku (structured list output — cheap).
"""

import json

from pipeline.config import PipelineConfig
from pipeline.llm import extract_json, llm_call, render_prompt
from pipeline.state import GraphState


def gen_scenarios_node(state: GraphState) -> dict:
    cfg = PipelineConfig()
    prompt = render_prompt(
        "gen_scenarios.j2",
        spec=state["spec"],
        module_name=state["module_name"],
    )
    text, log = llm_call(
        node="gen_scenarios",
        model=cfg.model_cheap,
        prompt=prompt,
        run_id=state["run_id"],
    )
    try:
        scenarios = extract_json(text)
        if not isinstance(scenarios, list):
            scenarios = []
    except (json.JSONDecodeError, AttributeError, ValueError):
        scenarios = []

    return {
        "scenarios": scenarios,
        "llm_calls": [log],
    }
