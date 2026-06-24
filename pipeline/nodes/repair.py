"""
Node 5 — Repair loop router.
Checks oscillation, increments repair_iter, regenerates driver with error context.
RQ3 (repair effectiveness), RQ4 (cost of repair).
Model: Sonnet.
"""

from pipeline.config import AblationMode
from pipeline.state import GraphState


def repair_node(state: GraphState) -> dict:
    """Increment repair counter. Phase 3 will add the LLM re-generation call here."""
    # TODO (Phase 3): render repair_driver.j2, call llm_call(), update driver_rtl.
    raise NotImplementedError("repair_node not implemented yet — Phase 3")


def should_repair(state: GraphState, mode: AblationMode) -> str:
    """
    Conditional edge: returns "repair" or "evaluate".

    Routes to "repair" when ALL of the following are true:
      - mode is not BASELINE
      - error_report is non-empty
      - repair_iter < max_repair_iter
      - oscillation not detected

    In Phase 1, error_report is always [] (pyverilog stub), so this always
    returns "evaluate" — no repair loop is entered.
    """
    if mode == AblationMode.BASELINE:
        return "evaluate"

    error_report = state.get("error_report") or []
    if not error_report:
        return "evaluate"

    if state.get("oscillation_detected", False):
        return "evaluate"

    repair_iter = state.get("repair_iter", 0)
    max_repair_iter = state.get("max_repair_iter", 3)
    if repair_iter >= max_repair_iter:
        return "evaluate"

    # COMPILER_ONLY: only repair when the error source is a compile failure.
    # Wired properly in Phase 3 when compile errors are captured in error_report.
    if mode == AblationMode.COMPILER_ONLY:
        has_compile_error = any(
            e.get("error_type") == "compile_error" for e in error_report
        )
        return "repair" if has_compile_error else "evaluate"

    # PYVERILOG_ONLY and HYBRID: any non-empty error_report triggers repair.
    return "repair"
