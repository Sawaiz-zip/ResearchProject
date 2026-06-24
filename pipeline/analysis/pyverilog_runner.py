"""
Pyverilog-based static analysis of generated testbench vs golden DUT.
Checks: port bindings, sensitivity lists, dataflow (undriven/unobserved), $fdisplay presence.
RQ1 + RQ2.

Smoke-test findings (Phase 0, 2026-06-23):
  - AST parse (pyverilog.vparser.parser.parse) works on all tested modules.
  - VerilogEval .sv files use Verilog-2001 port style: ports are wrapped in `vast.Ioport`
    nodes whose `.first` child is the actual Input/Output declaration. Always check
    `isinstance(item, vast.Ioport)` before accessing `.name`.
  - Dataflow (VerilogDataflowAnalyzer) works for CMB and SEQ with synchronous reset.
  - Dataflow raises `pyverilog.utils.verror.FormatError: Illegal sensitivity list`
    on modules with async reset (`always @(posedge clk or posedge ar)`).
    Mitigation: catch FormatError and fall back to AST-only analysis for those modules.
  - The LALR-table "183 shift/reduce conflicts" warning is normal; it fires every process
    but does not affect correctness.
"""

import tempfile
import os
import pyverilog.vparser.parser as vparser
import pyverilog.vparser.ast as vast
import pyverilog.dataflow.dataflow_analyzer as dfanalyzer
import pyverilog.utils.verror as verror

from pipeline.analysis.error_taxonomy import PyverilogReport


def _extract_ports(module_def) -> list[tuple[str, str]]:
    """Return [(direction, name), ...] handling both old Port and new Ioport styles."""
    ports = []
    for item in module_def.portlist.ports:
        if isinstance(item, vast.Ioport):
            decl = item.first
            ports.append((decl.__class__.__name__, decl.name))
        else:
            ports.append(("unknown", item.name))
    return ports


def run(tb_verilog: str, dut_verilog: str) -> PyverilogReport:
    """
    Parse TB + DUT together with Pyverilog and return a structured report.
    Raises ParseError if Pyverilog AST cannot handle the input (caller falls back to Verible).
    Dataflow errors (e.g. async reset) are caught and noted; analysis degrades to AST-only.
    """
    # TODO (Phase 2):
    # 1. Write tb_verilog and dut_verilog to temp files (use tempfile.NamedTemporaryFile)
    # 2. AST parse both files together: ast, _ = vparser.parse([tb_path, dut_path])
    #    Walk definitions to find TB module and DUT module separately.
    # 3. Extract DUT ports via _extract_ports(); build expected port map.
    # 4. Walk TB module's instantiation(s) (vast.Instance) to check:
    #    - all DUT ports are connected (no missing PortArg)
    #    - port names match DUT port names (catch swaps like clk→reset)
    # 5. Walk TB always-blocks (vast.Always) to check sensitivity lists
    #    for SEQ circuits: clk must appear; check for posedge.
    # 6. Try dataflow on DUT: VerilogDataflowAnalyzer([dut_path], dut_module_name)
    #    Catch verror.FormatError (async reset) → set dataflow_available=False.
    #    If available: check getTerms() for undriven inputs / unobserved outputs.
    # 7. Walk TB for $fdisplay/$monitor/$display presence per DUT output (SEQ check).
    # 8. Populate and return PyverilogReport with error_list.
    raise NotImplementedError("pyverilog_runner.run not implemented yet — Phase 2")
