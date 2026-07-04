# Quickstart: DUT Generation, Temperature & Results

## Prerequisites

- Python env with project deps installed (`langgraph`, `pyverilog`, `jinja2`, `pytest`, `python-dotenv`, provider SDK).
- iverilog **v13** on PATH (`iverilog -V`).
- `.env` with a provider key for live runs (Groq free tier: `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_CHEAP_MODEL` + `LLM_STRONG_MODEL`). Optional: `LLM_TEMPERATURE=0.7`.

## Validate offline (no tokens spent)

```bash
# Full suite, fully mocked — must pass with NO API key set
pytest tests/unit tests/integration/test_pipeline_flow_mocked.py -q
```

Expected: every node and routing branch exercised (CMB & SEQ, repair vs evaluate, golden vs generated eval DUT); zero network calls.

## Validate the new user flow (description only, live)

```bash
# No golden DUT — DUT is generated from the description
python -m pipeline run --module half_adder --mode hybrid
```

Expected console summary includes:
- the description
- `N of M scenarios passed`
- Eval0/Eval1/Eval2 results
- repair iterations, total tokens, wall time, final status
- `eval DUT: generated`

## Validate benchmark mode (golden DUT at eval only)

```bash
# VerilogEval module ships a golden DUT → used for evaluation only
python -m pipeline run --module Prob005_notgate --mode hybrid
```

Expected: generation still produces its own DUT; summary shows `eval DUT: golden`.

## Validate configurable temperature

```bash
LLM_TEMPERATURE=0.9 python -m pipeline run --module half_adder --mode hybrid
```

Expected: run completes; each entry in `results/<run_id>.json` → `llm_calls[*].temperature == 0.9`.

## Run the (few) live integration tests

```bash
pytest -m live -q          # skipped automatically if no API key present
```

## What "done" looks like

- `pytest -q` green offline.
- A run with no DUT input produces a DUT and a readable summary.
- A benchmark run reports `eval_dut_source: golden`.
- `LLM_TEMPERATURE` visibly changes `llm_calls[*].temperature`.
- Constitution Principle IV updated to v1.1.0.