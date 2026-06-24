"""
Node 1e — Generate Python checker script.
Runs in parallel with gen_driver (separate LangGraph branch).
Model: Sonnet (code generation).
"""

from pipeline.config import PipelineConfig
from pipeline.llm import extract_code_block, llm_call, render_prompt
from pipeline.state import GraphState


def gen_checker_node(state: GraphState) -> dict:
    cfg = PipelineConfig()
    prompt = render_prompt(
        "gen_checker.j2",
        spec=state["spec"],
        scenarios=state["scenarios"],
        module_name=state["module_name"],
    )
    text, log = llm_call(
        node="gen_checker",
        model=cfg.model_strong,
        prompt=prompt,
        run_id=state["run_id"],
        max_tokens=4096,
    )
    checker_py = extract_code_block(text, lang="python")
    if not checker_py:
        checker_py = text.strip()

    return {
        "checker_py": checker_py,
        "llm_calls": [log],
    }
