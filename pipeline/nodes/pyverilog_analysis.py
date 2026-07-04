"""
Node 2 — Pyverilog static analysis with Verible fallback.
RQ1 (error taxonomy), RQ2 (pre-simulation localization).
NO LLM CALLS — deterministic analysis only.
"""

from pipeline.analysis import pyverilog_runner, verible_runner
from pipeline.state import GraphState


def pyverilog_analysis_node(state: GraphState) -> dict:
    driver_rtl = state.get("driver_rtl", "")
    # Static analysis targets the generated DUT (fallback to golden for legacy).
    dut = state.get("dut_rtl") or state.get("golden_dut", "")
    module_name = state.get("module_name", "")

    if not driver_rtl.strip() or not dut.strip():
        return {
            "pyverilog_report": {
                "parse_ok": False,
                "parser_used": "none",
                "port_errors": [],
                "sensitivity_errors": [],
                "dataflow_errors": [],
                "fdisplay_missing": [],
                "raw_warnings": ["driver_rtl or dut is empty — skipping analysis"],
            }
        }

    report = pyverilog_runner.run(driver_rtl, dut, module_name=module_name)

    if not report.parse_ok:
        # Pyverilog failed — try Verible for a basic syntax check
        report = verible_runner.run(driver_rtl, dut)

    return {"pyverilog_report": report.to_dict()}