"""T015 — repair_node + routing functions (offline)."""

from pipeline.config import AblationMode
from pipeline.nodes.repair import (
    _error_signature,
    _feedback_source,
    repair_node,
    should_repair,
    should_repair_after_eval,
    after_repair,
)


# ── signature & source helpers ────────────────────────────────────────────────

def test_error_signature_stable_under_reorder():
    a = [{"error_type": "x", "signal": "p"}, {"error_type": "y", "signal": "q"}]
    b = list(reversed(a))
    assert _error_signature(a) == _error_signature(b)


def test_feedback_source_classification():
    assert _feedback_source([{"error_type": "compile_error"}]) == "compile"
    assert _feedback_source([{"error_type": "eval1_mismatch"}]) == "simulation"
    assert _feedback_source([{"error_type": "port_binding_mismatch"}]) == "static"


# ── repair_node ───────────────────────────────────────────────────────────────

def _repair_state(**over):
    s = {
        "run_id": "r",
        "module_name": "top_module",
        "driver_rtl": "module testbench; endmodule",
        "spec": {}, "scenarios": [],
        "error_report": [{"error_type": "compile_error", "detail": "boom"}],
        "repair_iter": 0,
        "max_repair_iter": 3,
        "last_repair_signature": "",
    }
    s.update(over)
    return s


def test_repair_regenerates_and_logs_history(fake_llm):
    out = repair_node(_repair_state())
    assert out["driver_rtl"].strip()                       # regenerated
    assert out["repair_iter"] == 1
    assert len(out["repair_history"]) == 1
    assert out["repair_history"][0]["feedback_source"] == "compile"
    assert out["repair_history"][0]["iteration"] == 1
    assert out["feedback_source"] == "compile"
    assert not out.get("oscillation_detected")


def test_repair_detects_oscillation_same_signature(fake_llm):
    # previous signature equals current → oscillation, no increment.
    sig = _error_signature([{"error_type": "compile_error", "detail": "boom"}])
    out = repair_node(_repair_state(last_repair_signature=sig))
    assert out["oscillation_detected"] is True
    assert "repair_iter" not in out or out.get("repair_iter") == 0


def test_repair_detects_oscillation_identical_driver(fake_llm_factory):
    # repair returns the exact same testbench it was given → oscillation.
    same = "module testbench; endmodule"
    fake_llm_factory({"repair": same})
    out = repair_node(_repair_state(driver_rtl=same))
    assert out["oscillation_detected"] is True


# ── should_repair (post static analysis) ──────────────────────────────────────

def _st(**over):
    s = {"error_report": [], "repair_iter": 0, "max_repair_iter": 3,
         "oscillation_detected": False, "eval0_pass": False, "eval1_pass": False}
    s.update(over)
    return s


def test_should_repair_static_matrix():
    errs = _st(error_report=[{"error_type": "port_binding_mismatch"}])
    assert should_repair(errs, AblationMode.BASELINE) == "evaluate"
    assert should_repair(errs, AblationMode.COMPILER_ONLY) == "evaluate"
    assert should_repair(errs, AblationMode.PYVERILOG_ONLY) == "repair"
    assert should_repair(errs, AblationMode.HYBRID) == "repair"
    # no errors → evaluate even in repairing modes
    assert should_repair(_st(), AblationMode.HYBRID) == "evaluate"
    # budget exhausted / oscillation → evaluate
    assert should_repair(_st(error_report=[{"error_type": "x"}], repair_iter=3),
                        AblationMode.HYBRID) == "evaluate"
    assert should_repair(_st(error_report=[{"error_type": "x"}], oscillation_detected=True),
                        AblationMode.HYBRID) == "evaluate"


# ── should_repair_after_eval (post evaluation) — the ablation matrix ──────────

def test_should_repair_after_eval_matrix():
    compile_fail = _st(eval0_pass=False, eval1_pass=False)
    sim_fail = _st(eval0_pass=True, eval1_pass=False)
    ok = _st(eval0_pass=True, eval1_pass=True)

    # BASELINE: never
    assert should_repair_after_eval(compile_fail, AblationMode.BASELINE) == "END"
    # PYVERILOG_ONLY: never from eval
    assert should_repair_after_eval(compile_fail, AblationMode.PYVERILOG_ONLY) == "END"
    assert should_repair_after_eval(sim_fail, AblationMode.PYVERILOG_ONLY) == "END"
    # COMPILER_ONLY: only on compile fail
    assert should_repair_after_eval(compile_fail, AblationMode.COMPILER_ONLY) == "repair"
    assert should_repair_after_eval(sim_fail, AblationMode.COMPILER_ONLY) == "END"
    # HYBRID: compile OR sim fail
    assert should_repair_after_eval(compile_fail, AblationMode.HYBRID) == "repair"
    assert should_repair_after_eval(sim_fail, AblationMode.HYBRID) == "repair"
    # success → END for all
    for m in AblationMode:
        assert should_repair_after_eval(ok, m) == "END"
    # exhausted / oscillation → END even when failing
    assert should_repair_after_eval(_st(eval0_pass=False, repair_iter=3),
                                   AblationMode.HYBRID) == "END"
    assert should_repair_after_eval(_st(eval0_pass=False, oscillation_detected=True),
                                   AblationMode.HYBRID) == "END"


def test_after_repair_routing():
    assert after_repair(_st()) == "pyverilog_analysis"
    assert after_repair(_st(oscillation_detected=True)) == "evaluate"
    assert after_repair(_st(repair_iter=4, max_repair_iter=3)) == "evaluate"
