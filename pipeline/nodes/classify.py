"""
Node 1a — Classify CMB/SEQ.
RQ: RQ1 (what error categories exist — classification is the first gating decision).
Model: Haiku (cheap, binary output).
"""

from pipeline.state import GraphState


def classify_node(state: GraphState) -> dict:
    # TODO (Phase 1): render classify_circuit.j2, call llm_call(), parse JSON output
    raise NotImplementedError("classify_node not implemented yet")
