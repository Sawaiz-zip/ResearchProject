"""
Verible-based fallback static analysis.
Used when Pyverilog cannot parse the TB (e.g., LLM produced invalid Verilog).
Only checks syntax — no semantic port-binding analysis.
"""

import subprocess

from pipeline.analysis.error_taxonomy import PyverilogReport


def run(tb_verilog: str, dut_verilog: str = "") -> PyverilogReport:
    """
    Run verible-verilog-syntax on tb_verilog.
    Returns PyverilogReport(parse_ok=True, parser_used="verible") on success.
    Returns PyverilogReport(parse_ok=False, parser_used="none") if verible is
    not installed or also fails to parse.
    """
    try:
        result = subprocess.run(
            ["verible-verilog-syntax", "--export_json", "-"],
            input=tb_verilog,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return PyverilogReport(
                parse_ok=False,
                parser_used="verible",
                raw_warnings=[
                    f"Verible parse error (rc={result.returncode}): {result.stderr[:500]}"
                ],
            )
        return PyverilogReport(
            parse_ok=True,
            parser_used="verible",
            raw_warnings=[
                "Pyverilog parse failed — used Verible (syntax-only, no semantic checks)"
            ],
        )
    except FileNotFoundError:
        return PyverilogReport(
            parse_ok=False,
            parser_used="none",
            raw_warnings=["verible-verilog-syntax not on PATH — install Verible for fallback"],
        )
    except subprocess.TimeoutExpired:
        return PyverilogReport(
            parse_ok=False,
            parser_used="none",
            raw_warnings=["Verible timed out"],
        )
    except Exception as exc:
        return PyverilogReport(
            parse_ok=False,
            parser_used="none",
            raw_warnings=[f"Verible runner error: {exc}"],
        )
