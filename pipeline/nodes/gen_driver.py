"""
Node 1d — Generate Verilog testbench driver.
Runs in parallel with gen_checker (separate LangGraph branch).
In repair iterations, state["error_report"] is non-empty and the prompt includes it.
Model: Sonnet (code generation).
"""

from pipeline.config import PipelineConfig
from pipeline.llm import extract_code_block, llm_call, render_prompt
from pipeline.state import GraphState


def gen_driver_node(state: GraphState) -> dict:
    cfg = PipelineConfig()
    prompt = render_prompt(
        "gen_driver.j2",
        spec=state["spec"],
        scenarios=state["scenarios"],
        module_name=state["module_name"],
        golden_dut=state["golden_dut"],
        error_report=state.get("error_report") or [],
    )
    text, log = llm_call(
        node="gen_driver",
        model=cfg.model_strong,
        prompt=prompt,
        run_id=state["run_id"],
        max_tokens=8192,
    )
    driver_rtl = extract_code_block(text, lang="verilog")
    if not driver_rtl:
        driver_rtl = text.strip()

    return {
        "driver_rtl": driver_rtl,
        "llm_calls": [log],
    }