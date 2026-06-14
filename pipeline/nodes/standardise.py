"""
Node 4 — Deterministic $fdisplay standardiser (SEQ circuits only).
RQ: RQ1, RQ2 (ensures outputs are observable before static analysis).
NO LLM CALLS in this node — Python AST pass only.
"""

from pipeline.state import GraphState


def standardise_node(state: GraphState) -> dict:
    # TODO (Phase 3): call fdisplay_inserter.insert_fdisplay(state["driver_rtl"], state["spec"])
    raise NotImplementedError("standardise_node not implemented yet")
