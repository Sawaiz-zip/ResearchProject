"""
LangGraph graph definition.
All pipeline steps are explicit nodes; all routing decisions are explicit conditional edges.
Constitution Principle I: no hidden control flow.
"""

from langgraph.graph import StateGraph, END

from pipeline.state import GraphState
from pipeline.config import AblationMode, PipelineConfig
from pipeline.nodes import (
    classify_node,
    extract_spec_node,
    gen_scenarios_node,
    gen_driver_node,
    gen_checker_node,
    standardise_node,
    pyverilog_analysis_node,
    error_reasoner_node,
    repair_node,
    evaluate_node,
)
from pipeline.nodes.repair import should_repair


def build_graph(config: PipelineConfig) -> StateGraph:
    """
    Build and return the compiled LangGraph graph for the given ablation mode.
    The graph structure is the same for all modes; conditional edges use `config.mode`
    to decide whether to enter the repair loop.
    """
    g = StateGraph(GraphState)

    # ── Register nodes ────────────────────────────────────────────────────────
    g.add_node("classify",           classify_node)
    g.add_node("extract_spec",       extract_spec_node)
    g.add_node("gen_scenarios",      gen_scenarios_node)
    g.add_node("gen_driver",         gen_driver_node)
    g.add_node("gen_checker",        gen_checker_node)
    g.add_node("standardise",        standardise_node)       # SEQ only
    g.add_node("pyverilog_analysis", pyverilog_analysis_node)
    g.add_node("error_reasoner",     error_reasoner_node)
    g.add_node("repair",             repair_node)
    g.add_node("evaluate",           evaluate_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    g.set_entry_point("classify")

    # ── Sequential backbone ───────────────────────────────────────────────────
    g.add_edge("classify",      "extract_spec")
    g.add_edge("extract_spec",  "gen_scenarios")

    # ── Parallel driver + checker branches ───────────────────────────────────
    # After gen_scenarios, both gen_driver and gen_checker are launched in parallel.
    # LangGraph fans out automatically when a node has multiple outgoing edges.
    g.add_edge("gen_scenarios", "gen_driver")
    g.add_edge("gen_scenarios", "gen_checker")

    # ── SEQ conditional: standardise before analysis ──────────────────────────
    def route_after_parallel_join(state: GraphState) -> str:
        """After driver+checker both complete, route SEQ through standardise."""
        # TODO (Phase 3): LangGraph fan-in — both gen_driver and gen_checker must
        # complete before this edge fires. Implement fan-in barrier here.
        if state.get("circuit_type") == "SEQ":
            return "standardise"
        return "pyverilog_analysis"

    # Placeholder: direct edge until fan-in is implemented in Phase 1/3
    g.add_edge("gen_driver",  "pyverilog_analysis")
    g.add_edge("gen_checker", "pyverilog_analysis")

    g.add_edge("standardise",        "pyverilog_analysis")
    g.add_edge("pyverilog_analysis", "error_reasoner")

    # ── Repair conditional edge ───────────────────────────────────────────────
    g.add_conditional_edges(
        "error_reasoner",
        lambda state: should_repair(state, config.mode),
        {"repair": "repair", "evaluate": "evaluate"},
    )

    g.add_edge("repair",   "gen_driver")   # re-enter generation with error context
    g.add_edge("evaluate", END)

    return g.compile()
