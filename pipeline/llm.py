"""
Shared LLM wrapper. All nodes call llm_call() — never the Anthropic client directly.
Guarantees: temperature=0, structured logging, exponential backoff on rate limits.
"""

import time
import os
import anthropic
from jinja2 import Environment, FileSystemLoader


_client: anthropic.Anthropic | None = None
_jinja_env: Environment | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _get_jinja(prompts_dir: str) -> Environment:
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(loader=FileSystemLoader(prompts_dir), trim_blocks=True)
    return _jinja_env


def render_prompt(template_name: str, prompts_dir: str = "prompts", **kwargs) -> str:
    env = _get_jinja(prompts_dir)
    tmpl = env.get_template(template_name)
    return tmpl.render(**kwargs)


def llm_call(
    *,
    node: str,
    model: str,
    prompt: str,
    run_id: str,
    max_tokens: int = 4096,
    max_retries: int = 3,
) -> tuple[str, dict]:
    """
    Call the Anthropic API and return (response_text, log_entry).
    log_entry matches the llm_calls schema in GraphState.
    Retries with exponential backoff on rate-limit errors (429).
    """
    client = _get_client()
    log: dict = {
        "node": node,
        "model": model,
        "run_id": run_id,
        "tokens_in": 0,
        "tokens_out": 0,
        "latency_ms": 0,
        "rate_limit_retries": 0,
    }

    for attempt in range(max_retries):
        t0 = time.monotonic()
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            log["tokens_in"] = response.usage.input_tokens
            log["tokens_out"] = response.usage.output_tokens
            log["latency_ms"] = elapsed
            return response.content[0].text, log

        except anthropic.RateLimitError:
            log["rate_limit_retries"] += 1
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)   # 1s, 2s, 4s

    raise RuntimeError("llm_call: unreachable")
