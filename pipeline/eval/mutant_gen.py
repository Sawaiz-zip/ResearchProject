"""
LLM-based mutant DUT generator for Eval2.
Injects a single-line fault into the golden DUT to create a buggy variant.
Model: Haiku (cheap, structural task).
"""

from pipeline.config import PipelineConfig
from pipeline.llm import extract_code_block, llm_call, render_prompt
from pipeline.state import GraphState


def generate_mutants(
    state: GraphState, n: int = 5
) -> tuple[list[str], list[dict]]:
    """
    Generate n mutant versions of state["golden_dut"] by asking Haiku to
    introduce a single-line fault (flip operator, invert signal, swap constants).
    Returns (mutant_verilog_list, llm_call_logs).
    """
    cfg = PipelineConfig()
    mutants: list[str] = []
    logs: list[dict] = []

    for _ in range(n):
        prompt = render_prompt(
            "gen_mutant.j2",
            golden_dut=state["golden_dut"],
            module_name=state["module_name"],
        )
        text, log = llm_call(
            node="gen_mutant",
            model=cfg.model_cheap,
            prompt=prompt,
            run_id=state["run_id"],
        )
        mutant = extract_code_block(text, lang="verilog")
        if not mutant:
            mutant = text.strip()
        mutants.append(mutant)
        logs.append(log)

    return mutants, logs
