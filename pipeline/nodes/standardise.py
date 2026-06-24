"""
Node 4 — Deterministic $fdisplay standardiser (SEQ circuits only).
RQ1, RQ2 — ensures outputs are observable before static analysis.
NO LLM CALLS — Python AST pass only.

Phase 1 stub: pass-through (SEQ support added in Phase 4).
"""

from pipeline.state import GraphState


def standardise_node(state: GraphState) -> dict:
    # Phase 4 will call fdisplay_inserter.insert(state["driver_rtl"], state["spec"])
    # and write the modified Verilog back to driver_rtl.
    return {}
