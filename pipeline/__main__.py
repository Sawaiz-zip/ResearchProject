"""
CLI entry point.
Usage: python -m pipeline run --module <name> --mode hybrid
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="LangGraph Verilog testbench generation pipeline",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run", help="Run pipeline on a single module")
    run_p.add_argument("--module", required=True, help="Module name from VerilogEval dataset")
    run_p.add_argument(
        "--mode",
        choices=["baseline", "compiler_only", "pyverilog_only", "hybrid"],
        default="hybrid",
        help="Ablation mode (default: hybrid)",
    )
    run_p.add_argument("--nl", help="Path to .txt file with NL description (overrides dataset)")
    run_p.add_argument("--dut", help="Path to golden DUT .v file (overrides dataset)")

    args = parser.parse_args()

    if args.command == "run":
        # TODO (Phase 1): load module from dataset or --nl/--dut flags, build graph, run
        print(f"[pipeline] would run module={args.module} mode={args.mode}")
        print("[pipeline] Not implemented yet — coming in Phase 1")
        sys.exit(0)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
