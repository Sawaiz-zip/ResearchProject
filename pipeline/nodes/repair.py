"""
Node 5 — Repair loop router.
Checks oscillation, increments repair_iter, regenerates driver with error context.
RQ: RQ3 (repair effectiveness), RQ4 (cost of repair).
Model: Sonnet.
"""

from pipeline.state import GraphState
from pipeline.config import AblationMode


def repair_node(state: GraphState) -> dict:
    # TODO (Phase 3): render repair_driver.j2, call llm_call(), update driver_rtl
    raise NotImplementedError("repair_node not implemented yet")


def should_repair(state: GraphState, mode: AblationMode) -> str:
    """
    Conditional edge function.
    Returns "repair" or "evaluate" based on ablation mode and error state.
    """
    # TODO (Phase 3): implement routing logic per AblationMode
    raise NotImplementedError("should_repair not implemented yet")
