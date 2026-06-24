"""
Node 6 — Icarus Verilog evaluation (Eval0 / Eval1 / Eval2).
RQ3 (repair effectiveness), RQ4 (cost–quality tradeoff).
NO LLM CALLS in this node — deterministic simulation only.
"""

import json
import os
import pathlib
import time

from pipeline.config import PipelineConfig
from pipeline.eval import icarus, mutant_gen
from pipeline.state import GraphState

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


def evaluate_node(state: GraphState) -> dict:
    cfg = PipelineConfig()
    t_start = time.monotonic()

    updates: dict = {
        "eval0_pass": False,
        "eval1_pass": False,
        "eval2_pass_rate": 0.0,
        "failure_stage": None,
        "final_status": "failed_compile",
        "llm_calls": [],
    }

    driver_rtl = state.get("driver_rtl", "")
    if not driver_rtl.strip():
        updates["failure_stage"] = "gen_driver"
        updates["final_status"] = "failed_compile"
        _write_result(state, updates, t_start)
        return updates

    # ── Eval0: compile ──────────────────────────────────────────────────────
    success, compiler_out, compiled_path = icarus.compile_tb(
        driver_rtl, state["golden_dut"], timeout_s=cfg.simulation_timeout_s
    )
    updates["eval0_pass"] = success

    if not success:
        updates["failure_stage"] = "evaluate"
        updates["final_status"] = "failed_compile"
        _write_result(state, updates, t_start)
        return updates

    # ── Eval1: simulate against golden DUT ──────────────────────────────────
    sim_out = ""
    try:
        passed, sim_out = icarus.simulate_tb(
            compiled_path, timeout_s=cfg.simulation_timeout_s
        )
        updates["eval1_pass"] = passed
        updates["sim_output"] = sim_out
        if not passed:
            updates["failure_stage"] = "evaluate"
            updates["final_status"] = "failed_eval1"
    finally:
        if compiled_path and os.path.exists(compiled_path):
            try:
                os.unlink(compiled_path)
            except OSError:
                pass

    if not updates["eval1_pass"]:
        updates["driver_rtl"] = state.get("driver_rtl", "")
        updates["compiler_output"] = compiler_out
        _write_result(state, updates, t_start)
        return updates

    # ── Eval2: simulate against mutant DUTs ─────────────────────────────────
    mutant_duts = state.get("mutant_duts") or []
    if not mutant_duts:
        mutant_duts, mutant_logs = mutant_gen.generate_mutants(state, n=cfg.num_mutants)
        updates["mutant_duts"] = mutant_duts
        updates["llm_calls"] = mutant_logs

    if mutant_duts:
        pass_rate = icarus.eval2(
            driver_rtl, mutant_duts, timeout_s=cfg.simulation_timeout_s
        )
        updates["eval2_pass_rate"] = pass_rate
        if pass_rate == 0.0:
            updates["final_status"] = "failed_eval2"
            updates["failure_stage"] = "evaluate"
        else:
            updates["final_status"] = "success"
    else:
        updates["final_status"] = "success"

    _write_result(state, updates, t_start)
    return updates


def _write_result(state: GraphState, updates: dict, t_start: float) -> None:
    results_dir = _PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)

    run_id = state.get("run_id", "unknown")
    # Combine llm_calls already in state with any from this node (mutant gen)
    all_llm_calls = list(state.get("llm_calls") or []) + list(
        updates.get("llm_calls") or []
    )

    result = {
        "run_id": run_id,
        "module_name": state.get("module_name", ""),
        "circuit_type": state.get("circuit_type", ""),
        "repair_iter": state.get("repair_iter", 0),
        "final_status": updates.get("final_status", ""),
        "failure_stage": updates.get("failure_stage"),
        "eval0_pass": updates.get("eval0_pass", False),
        "eval1_pass": updates.get("eval1_pass", False),
        "eval2_pass_rate": updates.get("eval2_pass_rate", 0.0),
        "llm_calls": all_llm_calls,
        "wall_clock_ms": int((time.monotonic() - t_start) * 1000),
        # Debug fields — present when Eval0/Eval1 fails
        "driver_rtl": updates.get("driver_rtl") or state.get("driver_rtl", ""),
        "compiler_output": updates.get("compiler_output", ""),
        "sim_output": updates.get("sim_output", ""),
    }

    out_path = results_dir / f"{run_id}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
