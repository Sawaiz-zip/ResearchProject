"""
T013 — SEQ routing through the full graph, offline.
SEQ circuits pass through the standardiser (outputs made observable); CMB circuits
do not; both complete without a fan-in deadlock.
"""

from pipeline.config import AblationMode, PipelineConfig
from pipeline.graph import build_graph
from pipeline.standardiser.fdisplay_inserter import _MARKER, _is_observed


def _state(run_id, **over):
    s = {
        "nl_description": "a d flip flop", "module_name": "dff", "golden_dut": "",
        "mutant_duts": ["m1"], "circuit_type": "CMB", "dut_rtl": "", "spec": {},
        "scenarios": [], "driver_rtl": "", "checker_py": "", "pyverilog_report": {},
        "error_report": [], "last_error_report": [], "scenario_results": [],
        "eval_dut_source": "generated", "repair_iter": 0, "max_repair_iter": 3,
        "oscillation_detected": False, "last_repair_signature": "", "feedback_source": "",
        "repair_history": [], "eval0_pass": False, "eval1_pass": False,
        "eval2_pass_rate": 0.0, "failure_stage": None, "final_status": "failed_compile",
        "run_id": run_id, "llm_calls": [],
    }
    s.update(over)
    return s


def test_seq_run_passes_through_standardise(fake_llm_seq, mock_icarus):
    # BASELINE avoids the repair loop so the test isolates the SEQ routing.
    final = build_graph(PipelineConfig(mode=AblationMode.BASELINE)).invoke(_state("seq_route"))
    assert final["circuit_type"] == "SEQ"
    # The standardiser ran: its marker is present and the output is now observed.
    assert _MARKER in final["driver_rtl"]
    assert _is_observed(final["driver_rtl"], "q")
    # And the run completed (no fan-in deadlock).
    assert final["final_status"]


def test_cmb_run_skips_standardise(fake_llm, mock_icarus):
    final = build_graph(PipelineConfig(mode=AblationMode.BASELINE)).invoke(_state("cmb_route"))
    assert final["circuit_type"] == "CMB"
    # CMB never enters the standardiser → no marker.
    assert _MARKER not in final["driver_rtl"]
    assert final["final_status"]
