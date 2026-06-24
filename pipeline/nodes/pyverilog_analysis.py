"""
Node 2 — Pyverilog static analysis with Verible fallback.
RQ1 (error taxonomy), RQ2 (pre-simulation localization).
NO LLM CALLS — deterministic analysis only.

Phase 1 stub: returns an empty report so the rest of the graph runs unblocked.
Full implementation in Phase 2 (pyverilog_runner.py).
"""

from pipeline.state import GraphState


def pyverilog_analysis_node(state: GraphState) -> dict:
    # Phase 2 will call pyverilog_runner.run(tb, dut) here.
    empty_report = {
        "parse_ok": True,
        "parser_used": "none",
        "port_errors": [],
        "sensitivity_errors": [],
        "dataflow_errors": [],
        "fdisplay_missing": [],
        "raw_warnings": ["[Phase 1 stub] static analysis not yet implemented"],
    }
    return {"pyverilog_report": empty_report}