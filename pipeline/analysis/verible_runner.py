"""
Verible fallback parser — used when Pyverilog cannot parse the TB.
Runs verible-verilog-syntax as a subprocess and extracts partial structural information.
"""

from pipeline.analysis.error_taxonomy import PyverilogReport


def run(tb_verilog: str, dut_verilog: str) -> PyverilogReport:
    """
    Parse TB with Verible and return a partial PyverilogReport.
    parse_ok=True if Verible succeeds; parser_used="verible".
    """
    # TODO (Phase 2):
    # 1. Write tb_verilog to a temp file
    # 2. Subprocess: verible-verilog-syntax --export_json <file>
    # 3. Parse JSON output to extract port list and basic structure
    # 4. Perform limited checks possible without full dataflow analysis
    # 5. Return PyverilogReport(parse_ok=True, parser_used="verible", ...)
    raise NotImplementedError("verible_runner.run not implemented yet")
