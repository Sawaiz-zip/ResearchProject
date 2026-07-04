"""
Node 4 — Deterministic $fdisplay/$monitor standardiser (SEQ circuits only).
RQ1, RQ2 — ensures outputs are observable before static analysis.
NO LLM CALLS — Python pass only (Constitution Principle VI).
"""

from pipeline.standardiser.fdisplay_inserter import insert_fdisplay
from pipeline.state import GraphState


def standardise_node(state: GraphState) -> dict:
    driver_rtl = state.get("driver_rtl", "")
    spec = state.get("spec") or {}
    updated = insert_fdisplay(driver_rtl, spec)
    return {"driver_rtl": updated}
