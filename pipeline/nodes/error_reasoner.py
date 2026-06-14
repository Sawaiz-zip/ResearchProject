"""
Node 3 — LLM-based error reasoner.
Converts raw Pyverilog report into structured, actionable error list.
RQ: RQ2 (localization quality), RQ3 (LLM reasoning quality).
Model: Sonnet.
"""

from pipeline.state import GraphState


def error_reasoner_node(state: GraphState) -> dict:
    # TODO (Phase 2): render error_reasoner.j2, call llm_call(), parse error list
    # Also copy current error_report to last_error_report before overwriting
    raise NotImplementedError("error_reasoner_node not implemented yet")
