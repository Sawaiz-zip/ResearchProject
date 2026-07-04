"""
Fan-in barrier after the parallel driver + checker branches.
No-op node: its only purpose is to give the graph a single point that runs *after
both* gen_driver and gen_checker complete, so the SEQ-vs-CMB routing decision (and
the standardise step) happens on the fully-generated testbench. No LLM calls.
"""

from pipeline.state import GraphState


def merge_generation_node(state: GraphState) -> dict:
    return {}
