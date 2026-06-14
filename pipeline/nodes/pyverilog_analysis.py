"""
Node 2 — Pyverilog static analysis with Verible fallback.
RQ: RQ1 (error taxonomy), RQ2 (pre-simulation localization).
NO LLM CALLS — deterministic analysis only.
"""

from pipeline.state import GraphState


def pyverilog_analysis_node(state: GraphState) -> dict:
    # TODO (Phase 2): call pyverilog_runner.run(), fall back to verible_runner if parse fails
    raise NotImplementedError("pyverilog_analysis_node not implemented yet")
