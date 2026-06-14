"""
Node 6 — Icarus Verilog evaluation (Eval0 / Eval1 / Eval2).
RQ: RQ3 (repair effectiveness), RQ4 (cost–quality tradeoff).
NO LLM CALLS — deterministic simulation only.
"""

from pipeline.state import GraphState


def evaluate_node(state: GraphState) -> dict:
    # TODO (Phase 1): call icarus.compile_tb(), icarus.simulate_tb(), icarus.eval2()
    # Write RunResult JSON to results/<run_id>.json
    raise NotImplementedError("evaluate_node not implemented yet")
