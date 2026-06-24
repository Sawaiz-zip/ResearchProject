"""
Node 3 — LLM-based error reasoner.
Converts raw Pyverilog report into structured, actionable error list.
RQ2 (localization quality), RQ3 (LLM reasoning quality).
Model: Sonnet.

Phase 1 stub: passes through with empty error_report so should_repair() routes
straight to evaluate. Full implementation in Phase 2.
"""

from pipeline.state import GraphState


def error_reasoner_node(state: GraphState) -> dict:
    # Save current error_report as last before overwriting (oscillation detection).
    # Phase 2 will render error_reasoner.j2, call Sonnet, parse the error list.
    return {
        "last_error_report": state.get("error_report") or [],
        "error_report": [],
    }