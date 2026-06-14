"""
Icarus Verilog wrapper.
Eval0: does the testbench compile?
Eval1: does it pass against the golden DUT?
Eval2: does it catch bugs in mutant DUTs?
"""

import subprocess
import tempfile
import os


def compile_tb(driver_rtl: str, dut_verilog: str, timeout_s: int = 30) -> tuple[bool, str]:
    """
    Compile TB + DUT with iverilog.
    Returns (success, compiler_output).
    """
    # TODO (Phase 1):
    # 1. Write driver_rtl and dut_verilog to temp .v files
    # 2. Subprocess: iverilog -o <out> <tb.v> <dut.v>
    # 3. Return (returncode == 0, stdout+stderr)
    raise NotImplementedError("compile_tb not implemented yet")


def simulate_tb(compiled_path: str, timeout_s: int = 30) -> tuple[bool, str]:
    """
    Run compiled simulation with vvp.
    Returns (passed, simulation_output).
    passed=True if no $error / assertion failures in output.
    """
    # TODO (Phase 1):
    # 1. Subprocess: vvp <compiled_path> with timeout
    # 2. Parse output for failure indicators
    # 3. Return (passed, output)
    raise NotImplementedError("simulate_tb not implemented yet")


def eval2(driver_rtl: str, mutant_duts: list[str], timeout_s: int = 30) -> float:
    """
    Run TB against each mutant DUT.
    Returns fraction of mutants where TB correctly FAILS (catches the bug).
    """
    # TODO (Phase 1):
    # 1. For each mutant: compile_tb + simulate_tb
    # 2. Count mutants where simulation FAILS (TB caught the bug)
    # 3. Return caught / total
    raise NotImplementedError("eval2 not implemented yet")
