"""
CLI entry point.
Usage:
  python -m pipeline run --module Prob005_notgate
  python -m pipeline run --module half_adder --mode baseline
  python -m pipeline run --module my_mod --nl desc.txt --dut dut.v
"""

import argparse
import pathlib
import sys
import uuid

from dotenv import load_dotenv
load_dotenv()  # must be before any module that reads ANTHROPIC_API_KEY

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent
_VERILOG_EVAL_DIR = _PROJECT_ROOT / "data" / "verilog_eval" / "problems"
_FIXTURES_CMB = _PROJECT_ROOT / "tests" / "fixtures" / "cmb"
_FIXTURES_SEQ = _PROJECT_ROOT / "tests" / "fixtures" / "seq"


def load_module(
    module_name: str,
    nl_override: str | None,
    dut_override: str | None,
) -> dict:
    """
    Return {"module_name", "nl_description", "golden_dut"}.

    Search order:
      1. --nl / --dut overrides (both required together)
      2. data/verilog_eval/problems/<module_name>_prompt.txt + _ref.sv
         (also matches partial names like "notgate" → Prob005_notgate)
      3. tests/fixtures/cmb/<module_name>_prompt.txt + _ref.v
      4. tests/fixtures/seq/<module_name>_prompt.txt + _ref.v
    """
    if nl_override and dut_override:
        return {
            "module_name": module_name,
            "nl_description": pathlib.Path(nl_override).read_text(),
            "golden_dut": pathlib.Path(dut_override).read_text(),
        }

    # Exact VerilogEval match (e.g. "Prob005_notgate")
    prompt_path = _VERILOG_EVAL_DIR / f"{module_name}_prompt.txt"
    ref_path = _VERILOG_EVAL_DIR / f"{module_name}_ref.sv"
    if prompt_path.exists() and ref_path.exists():
        return {
            "module_name": "RefModule",
            "nl_description": prompt_path.read_text(),
            "golden_dut": ref_path.read_text(),
        }

    # Partial VerilogEval match (e.g. "notgate" → Prob005_notgate_prompt.txt)
    for candidate in sorted(_VERILOG_EVAL_DIR.glob(f"*{module_name}*_prompt.txt")):
        stem = candidate.stem.replace("_prompt", "")
        ref = candidate.parent / f"{stem}_ref.sv"
        if ref.exists():
            return {
                "module_name": "RefModule",
                "nl_description": candidate.read_text(),
                "golden_dut": ref.read_text(),
            }

    # CMB / SEQ fixtures
    for fixture_dir in [_FIXTURES_CMB, _FIXTURES_SEQ]:
        p = fixture_dir / f"{module_name}_prompt.txt"
        r = fixture_dir / f"{module_name}_ref.v"
        if p.exists() and r.exists():
            return {
                "module_name": module_name,
                "nl_description": p.read_text(),
                "golden_dut": r.read_text(),
            }

    raise FileNotFoundError(
        f"Module '{module_name}' not found.\n"
        f"  Searched VerilogEval: {_VERILOG_EVAL_DIR}\n"
        f"  Searched fixtures:    {_FIXTURES_CMB}, {_FIXTURES_SEQ}\n"
        f"  Use --nl and --dut to provide files directly."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="LangGraph Verilog testbench generation pipeline",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run", help="Run pipeline on a single module")
    run_p.add_argument(
        "--module", required=True,
        help="VerilogEval key (e.g. Prob005_notgate) or fixture name (e.g. half_adder)",
    )
    run_p.add_argument(
        "--mode",
        choices=["baseline", "compiler_only", "pyverilog_only", "hybrid"],
        default="hybrid",
        help="Ablation mode (default: hybrid)",
    )
    run_p.add_argument("--nl", help="Path to .txt NL description (overrides dataset)")
    run_p.add_argument("--dut", help="Path to golden DUT .v/.sv file (overrides dataset)")
    run_p.add_argument("--run-id", dest="run_id", help="Run ID (8-char UUID generated if omitted)")

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return

    # Lazy imports so --help works even without ANTHROPIC_API_KEY
    from pipeline.config import AblationMode, PipelineConfig
    from pipeline.graph import build_graph

    try:
        module_data = load_module(args.module, args.nl, args.dut)
    except FileNotFoundError as e:
        print(f"[pipeline] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    run_id = args.run_id or str(uuid.uuid4())[:8]
    mode = AblationMode(args.mode)
    config = PipelineConfig(mode=mode)

    initial_state: dict = {
        **module_data,
        "mutant_duts": [],
        "circuit_type": "CMB",
        "spec": {},
        "scenarios": [],
        "driver_rtl": "",
        "checker_py": "",
        "pyverilog_report": {},
        "error_report": [],
        "last_error_report": [],
        "repair_iter": 0,
        "max_repair_iter": config.max_repair_iter,
        "oscillation_detected": False,
        "eval0_pass": False,
        "eval1_pass": False,
        "eval2_pass_rate": 0.0,
        "failure_stage": None,
        "final_status": "failed_compile",
        "run_id": run_id,
        "llm_calls": [],
    }

    print(f"[pipeline] run_id={run_id}  module={args.module}  mode={args.mode}")
    graph = build_graph(config)
    final_state = graph.invoke(initial_state)

    status = final_state.get("final_status", "?")
    e0 = final_state.get("eval0_pass", False)
    e1 = final_state.get("eval1_pass", False)
    e2 = final_state.get("eval2_pass_rate", 0.0)
    n_calls = len(final_state.get("llm_calls") or [])
    print(f"[pipeline] status={status}  eval0={e0}  eval1={e1}  eval2={e2:.2f}")
    print(f"[pipeline] llm_calls={n_calls}  result=results/{run_id}.json")


if __name__ == "__main__":
    main()
