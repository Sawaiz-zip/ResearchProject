"""
Node 1b — Generate the DUT from the natural-language description.
The pipeline no longer requires a user-supplied golden DUT; it synthesises one
from the description (steered by the classified circuit type). The generated DUT
is the artifact whose testbench is generated, whose errors are localised
(RQ1/RQ2) and repaired (RQ3).
Model: Sonnet (code generation).
"""

from pipeline.config import PipelineConfig
from pipeline.llm import extract_code_block, llm_call, render_prompt
from pipeline.state import GraphState


def gen_dut_node(state: GraphState) -> dict:
    cfg = PipelineConfig()
    prompt = render_prompt(
        "gen_dut.j2",
        nl_description=state["nl_description"],
        circuit_type=state.get("circuit_type", "CMB"),
        module_name=state.get("module_name", "top_module"),
    )
    text, log = llm_call(
        node="gen_dut",
        model=cfg.model_strong,
        prompt=prompt,
        run_id=state["run_id"],
        max_tokens=4096,
    )
    # Tolerant extraction — robust to temperature>0 (Constitution IV).
    dut_rtl = extract_code_block(text, lang="verilog")
    if not dut_rtl.strip():
        dut_rtl = text.strip()

    return {
        "dut_rtl": dut_rtl,
        "llm_calls": [log],
    }