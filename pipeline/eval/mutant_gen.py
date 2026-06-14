"""
LLM-based mutant DUT generator for Eval2.
Injects a single-line fault into the golden DUT to create a buggy variant.
Model: Haiku (cheap, structural task).
"""

from pipeline.state import GraphState


def generate_mutants(state: GraphState, n: int = 5) -> list[str]:
    """
    Generate n mutant versions of state["golden_dut"] by asking Haiku
    to introduce a single-line fault (e.g. flip an operator, invert a signal).
    Returns list of Verilog strings.
    """
    # TODO (Phase 1): render gen_mutant.j2 n times, call llm_call() each time
    raise NotImplementedError("generate_mutants not implemented yet")
