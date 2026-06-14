"""
Deterministic $fdisplay inserter — Python AST pass, NO LLM.
Reads DUT output port list from spec, checks each output has a $fdisplay/$monitor,
inserts missing ones at the end of the always block.
RQ1 + RQ2 (ensures SEQ outputs are observable before static analysis).
"""


def insert_fdisplay(driver_rtl: str, spec: dict) -> str:
    """
    Return modified driver_rtl with $fdisplay statements inserted for any
    output signal in spec["ports"]["outputs"] that lacks one.
    Idempotent: if $fdisplay already exists for a signal, it is not duplicated.
    """
    # TODO (Phase 3):
    # 1. Parse driver_rtl with pyverilog (or regex fallback) to find always blocks
    # 2. Extract output signal names from spec["ports"]["outputs"]
    # 3. For each output missing $fdisplay/$monitor, inject at end of always block
    # 4. Return modified Verilog string
    raise NotImplementedError("insert_fdisplay not implemented yet")
