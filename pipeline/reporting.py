"""
Human-readable run reporting.
parse_scenarios(): turn raw simulator output into structured per-scenario results.
print_run_summary(): print an at-a-glance summary of a completed run.
No LLM calls, no side effects beyond stdout.
"""

import re

# Testbenches print exactly "PASS: <name>" / "FAIL: <name>" per scenario
# (enforced by gen_driver.j2). Anchor to the start of a line so debug prints
# that merely contain the word "failed" are never miscounted.
_PASS_RE = re.compile(r"^\s*PASS\s*:\s*(?P<name>.+?)\s*$", re.MULTILINE)
_FAIL_RE = re.compile(r"^\s*FAIL\s*:\s*(?P<name>.+?)\s*$", re.MULTILINE)


def parse_scenarios(sim_output: str) -> list[dict]:
    """
    Parse `sim_output` into an ordered list of {"name": str, "passed": bool}.
    Preserves the order scenarios appear in the log. Lines that are not explicit
    PASS:/FAIL: markers are ignored.
    """
    if not sim_output:
        return []

    results: list[dict] = []
    for m in re.finditer(r"^\s*(PASS|FAIL)\s*:\s*(?P<name>.+?)\s*$",
                         sim_output, re.MULTILINE):
        results.append({
            "name": m.group("name"),
            "passed": m.group(1) == "PASS",
        })
    return results


def _fmt_bool(b: bool) -> str:
    return "PASS" if b else "FAIL"


def print_run_summary(result: dict) -> None:
    """Print a readable summary of a run result dict (same shape as results/*.json)."""
    llm_calls = result.get("llm_calls") or []
    tokens_in = result.get("tokens_in_total")
    tokens_out = result.get("tokens_out_total")
    if tokens_in is None:
        tokens_in = sum(c.get("tokens_in", 0) for c in llm_calls)
    if tokens_out is None:
        tokens_out = sum(c.get("tokens_out", 0) for c in llm_calls)

    scenarios = result.get("scenario_results") or []
    n_pass = result.get("scenarios_passed")
    n_total = result.get("scenarios_total")
    if n_total is None:
        n_total = len(scenarios)
    if n_pass is None:
        n_pass = sum(1 for s in scenarios if s.get("passed"))
    failing = [s.get("name", "?") for s in scenarios if not s.get("passed")]

    desc = (result.get("nl_description") or "").strip().replace("\n", " ")
    if len(desc) > 200:
        desc = desc[:197] + "..."

    wall_ms = result.get("wall_clock_ms", 0)
    e2 = result.get("eval2_pass_rate", 0.0)

    line = "═" * 60
    print(line)
    print(f" Run: {result.get('run_id','?')}  |  {result.get('module_name','?')}"
          f"  |  {result.get('circuit_type','?')}")
    print(line)
    print(f" Description : {desc or '(none)'}")
    print()
    print(f" Test Results : {n_pass} / {n_total} scenarios passed")
    if failing:
        print(f"   Failing : {', '.join(failing)}")
    print()
    print(f" Eval0 (compiles)       : {_fmt_bool(result.get('eval0_pass', False))}")
    print(f" Eval1 (correct output) : {_fmt_bool(result.get('eval1_pass', False))}")
    print(f" Eval2 (catches bugs)   : {e2:.0%} mutants caught")
    print()
    print(f" Eval DUT          : {result.get('eval_dut_source', 'generated')}")
    print(f" Repair iterations : {result.get('repair_iter', 0)}")
    repair_history = result.get("repair_history") or []
    for h in repair_history:
        print(f"   iter {h.get('iteration','?')}: {h.get('feedback_source','?')} "
              f"feedback ({h.get('tokens_in',0)}+{h.get('tokens_out',0)} tok)")
    print(f" Tokens            : {tokens_in + tokens_out:,} "
          f"(in {tokens_in:,} / out {tokens_out:,})")
    print(f" Wall time         : {wall_ms / 1000:.1f} s")
    print(f" Status            : {result.get('final_status', '?').upper()}")
    print(line)