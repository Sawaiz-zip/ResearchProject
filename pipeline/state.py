import operator
from typing import Annotated, Literal, TypedDict


class GraphState(TypedDict):
    # ── Inputs ──────────────────────────────────────────────────────────────
    nl_description: str
    module_name: str
    golden_dut: str          # Verilog source of the DUT
    mutant_duts: list[str]   # for Eval2

    # ── Stage outputs ────────────────────────────────────────────────────────
    circuit_type: Literal["CMB", "SEQ"]
    spec: dict                    # JSON spec: {ports, behaviour, timing}
    scenarios: list[dict]         # [{name, inputs, expected}]
    driver_rtl: str               # generated Verilog testbench
    checker_py: str               # generated Python checker
    pyverilog_report: dict        # AST + dataflow + port-binding summary
    error_report: list[dict]      # [{type, signal, line, suggested_fix, severity}]
    last_error_report: list[dict] # for oscillation detection

    # ── Loop control ─────────────────────────────────────────────────────────
    repair_iter: int
    max_repair_iter: int
    oscillation_detected: bool

    # ── Evaluation ───────────────────────────────────────────────────────────
    eval0_pass: bool
    eval1_pass: bool
    eval2_pass_rate: float
    failure_stage: str | None
    final_status: Literal[
        "success",
        "failed_compile",
        "failed_eval1",
        "failed_eval2",
        "oscillated",
        "exhausted_iters",
        "invalid_dut",
    ]

    # ── Telemetry ────────────────────────────────────────────────────────────
    run_id: str
    # Annotated with operator.add so parallel branches (gen_driver, gen_checker)
    # each append their log entry without overwriting each other's.
    llm_calls: Annotated[list[dict], operator.add]
