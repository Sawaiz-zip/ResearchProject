"""
Node 1a — Classify CMB/SEQ.
RQ1: circuit type is the first gating decision for the error taxonomy.
Model: Haiku (binary output — cheap).
"""

import json

from pipeline.config import PipelineConfig
from pipeline.llm import extract_json, llm_call, render_prompt
from pipeline.state import GraphState


def classify_node(state: GraphState) -> dict:
    cfg = PipelineConfig()
    prompt = render_prompt(
        "classify_circuit.j2",
        nl_description=state["nl_description"],
    )
    text, log = llm_call(
        node="classify",
        model=cfg.model_cheap,
        prompt=prompt,
        run_id=state["run_id"],
    )
    try:
        data = extract_json(text)
        circuit_type = data.get("circuit_type", "CMB")
    except (json.JSONDecodeError, AttributeError, ValueError):
        # Fall back to keyword scan if the model doesn't return valid JSON
        circuit_type = "SEQ" if "seq" in text.lower() else "CMB"

    if circuit_type not in ("CMB", "SEQ"):
        circuit_type = "CMB"

    return {
        "circuit_type": circuit_type,
        "llm_calls": [log],
    }