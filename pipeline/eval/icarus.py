"""
Icarus Verilog wrapper.
Eval0: does the testbench compile?
Eval1: does it pass against the golden DUT?
Eval2: does it catch bugs in mutant DUTs?
"""

import os
import subprocess
import tempfile


def compile_tb(
    driver_rtl: str, dut_verilog: str, timeout_s: int = 30
) -> tuple[bool, str, str]:
    """
    Eval0: compile TB + DUT with iverilog.
    Returns (success, compiler_output, compiled_binary_path).
    compiled_binary_path is "" on failure.
    Caller is responsible for deleting compiled_binary_path when done.
    """
    tb_fd, tb_path = tempfile.mkstemp(suffix=".v", prefix="tb_")
    dut_fd, dut_path = tempfile.mkstemp(suffix=".v", prefix="dut_")
    out_fd, out_path = tempfile.mkstemp(suffix=".out", prefix="sim_")
    os.close(tb_fd)
    os.close(dut_fd)
    os.close(out_fd)

    try:
        with open(tb_path, "w") as f:
            f.write(driver_rtl)
        with open(dut_path, "w") as f:
            f.write(dut_verilog)

        result = subprocess.run(
            ["iverilog", "-g2012", "-o", out_path, tb_path, dut_path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        output = (result.stdout + result.stderr).strip()
        success = result.returncode == 0
        if not success and os.path.exists(out_path):
            os.unlink(out_path)
            out_path = ""
        return success, output, out_path if success else ""

    except subprocess.TimeoutExpired:
        return False, "iverilog timed out", ""
    finally:
        for p in [tb_path, dut_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


def simulate_tb(compiled_path: str, timeout_s: int = 30) -> tuple[bool, str]:
    """
    Eval1: run compiled simulation with vvp.
    Returns (passed, simulation_output).
    passed=True if the output contains no FAIL markers and vvp exits normally.
    """
    if not compiled_path or not os.path.exists(compiled_path):
        return False, "compiled binary not found"

    try:
        result = subprocess.run(
            ["vvp", compiled_path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        output = (result.stdout + result.stderr).strip()
        # Our prompt instructs the TB to print exactly "FAIL: <name>" on failure.
        # Match that precisely to avoid catching words like "failed" in debug prints.
        import re as _re
        has_fail_marker = bool(_re.search(r'\bFAIL\s*:', output))
        # Also catch VerilogEval reference TB style ("mismatch") and $error crashes
        has_mismatch    = "mismatch" in output.lower()
        has_error_crash = result.returncode not in (0, 1)
        failed = has_fail_marker or has_mismatch or has_error_crash
        return not failed, output

    except subprocess.TimeoutExpired:
        return False, f"vvp timed out after {timeout_s}s"


def eval2(driver_rtl: str, mutant_duts: list[str], timeout_s: int = 30) -> float:
    """
    Eval2: run TB against each mutant DUT.
    Returns the fraction of mutants where the TB correctly detects the bug
    (i.e. simulation FAILS on the mutant).
    """
    if not mutant_duts:
        return 0.0

    caught = 0
    for mutant_verilog in mutant_duts:
        success, _compiler_out, compiled_path = compile_tb(
            driver_rtl, mutant_verilog, timeout_s=timeout_s
        )
        if not success:
            # If the mutant doesn't even compile, skip it — it's an invalid mutant,
            # not a caught bug (the TB didn't discriminate; the mutation was bad).
            continue
        try:
            passed, _sim_out = simulate_tb(compiled_path, timeout_s=timeout_s)
            if not passed:
                # TB detected the bug in this mutant
                caught += 1
        finally:
            if compiled_path and os.path.exists(compiled_path):
                try:
                    os.unlink(compiled_path)
                except OSError:
                    pass

    return caught / len(mutant_duts)
