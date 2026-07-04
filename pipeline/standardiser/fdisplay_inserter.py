"""
Deterministic $fdisplay/$monitor standardiser — Python only, NO LLM.
Ensures every DUT output is observable in a sequential testbench and that a clock
is toggled. Idempotent and fail-safe. Replaces AutoBench's fragile LLM-based
standardisation (Constitution Principle VI). RQ1 (missing-$fdisplay error class) + RQ2.
"""

import re

_MARKER = "// [standardised]"


def _find_outputs(spec: dict) -> list[str]:
    outs = (spec or {}).get("ports", {}).get("outputs", []) or []
    names = []
    for o in outs:
        if isinstance(o, dict) and o.get("name"):
            names.append(str(o["name"]))
        elif isinstance(o, str):
            names.append(o)
    return names


def _clock_name(spec: dict) -> str | None:
    clk = (spec or {}).get("ports", {}).get("clock")
    if not clk or clk in ("null", "None"):
        return None
    return str(clk)


def _is_observed(driver_rtl: str, name: str) -> bool:
    """An output is observed if its name appears in a display/monitor/write call
    OR in a comparison / if-check (the scenario pass/fail pattern)."""
    word = re.compile(rf"\b{re.escape(name)}\b")
    for line in driver_rtl.splitlines():
        if not word.search(line):
            continue
        if any(k in line for k in ("$display", "$monitor", "$fdisplay", "$write")):
            return True
        if "===" in line or "==" in line or re.search(r"\bif\b", line):
            return True
    return False


def _has_clock_gen(driver_rtl: str, clk: str) -> bool:
    """A toggling clock generator exists (e.g. `always #5 clk = ~clk;`)."""
    return bool(re.search(rf"\b{re.escape(clk)}\s*=\s*~", driver_rtl)) or bool(
        re.search(rf"~\s*{re.escape(clk)}\b", driver_rtl)
    )


def insert_fdisplay(driver_rtl: str, spec: dict) -> str:
    """
    Return driver_rtl with observation ensured for every DUT output and a clock
    toggle ensured for a clocked testbench. Idempotent (a `// [standardised]`
    marker short-circuits a second pass). Never edits the DUT. Fail-safe: any
    internal error returns the original driver_rtl unchanged.
    """
    try:
        if not driver_rtl or not driver_rtl.strip():
            return driver_rtl
        if _MARKER in driver_rtl:
            return driver_rtl  # already standardised → idempotent no-op

        outputs = _find_outputs(spec)
        clk = _clock_name(spec)

        unobserved = [o for o in outputs if not _is_observed(driver_rtl, o)]
        # Only add a clock toggle when the clock signal is already declared/used in
        # the testbench but never toggled (the common "forgot to toggle" defect).
        need_clock = bool(
            clk
            and re.search(rf"\b{re.escape(clk)}\b", driver_rtl)
            and not _has_clock_gen(driver_rtl, clk)
        )

        if not unobserved and not need_clock:
            return driver_rtl  # nothing to do (all outputs observed, clock ok)

        block = [f"  {_MARKER}"]
        if need_clock:
            block.append(f"  initial {clk} = 0;")
            block.append(f"  always #5 {clk} = ~{clk};")
        if unobserved and outputs:
            fmt = " ".join(f"{o}=%b" for o in outputs)
            sigs = ", ".join(outputs)
            block.append(f'  initial $monitor("[mon] t=%0t {fmt}", $time, {sigs});')
        insertion = "\n".join(block) + "\n"

        # Insert just before the final `endmodule` (never touches the DUT, which is
        # a separate file in evaluation and not present in the testbench string).
        idx = driver_rtl.rfind("endmodule")
        if idx == -1:
            return driver_rtl  # not a well-formed module → fail safe
        return driver_rtl[:idx] + insertion + driver_rtl[idx:]

    except Exception:
        return driver_rtl  # fail-safe: never corrupt the testbench
