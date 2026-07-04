# Phase 1 Contracts: Interfaces

## 1. `llm_call` signature (`pipeline/llm.py`)

```python
def llm_call(
    *,
    node: str,
    model: str,
    prompt: str,
    run_id: str,
    max_tokens: int = 4096,
    max_retries: int = 3,
    temperature: float | None = None,   # NEW
) -> tuple[str, dict]:
    ...
```

- Resolved temperature = `temperature` arg if not None, else `float(os.environ["LLM_TEMPERATURE"])` if set, else `0.7`.
- The resolved value is passed to the provider call (replacing the hardcoded `temperature=0`) and written into the returned `log["temperature"]`.
- Contract: a malformed/non-parseable model response must not raise out of `llm_call` beyond the existing retry policy; parsing is the caller's responsibility and callers must fall back rather than crash.

## 2. `gen_dut` node contract (`pipeline/nodes/gen_dut.py`)

```python
def gen_dut_node(state: GraphState) -> dict:
    # reads: state["nl_description"], state["circuit_type"], state["run_id"]
    # returns: {"dut_rtl": <verilog str>, "llm_calls": [log]}
```

- Model: Sonnet (`cfg.model_strong`).
- Prompt: `prompts/gen_dut.j2` with variables `nl_description`, `circuit_type`, `module_name`.
- Output extracted via `extract_code_block(text, "verilog")` (tolerant).
- Fallback: if extraction yields empty string, return the raw stripped text as `dut_rtl` (never crash).

## 3. `gen_dut.j2` prompt variables

| Variable | Meaning |
|---|---|
| `nl_description` | user's circuit description |
| `circuit_type` | `"CMB"` or `"SEQ"` — steer clocked vs combinational output |
| `module_name` | desired module name (so ports line up with generated testbench) |

Output: a single synthesizable Verilog module, no markdown fences, no testbench.

## 4. `classify_circuit.j2` change

- **Remove** the `golden_dut` variable and any reference to DUT source.
- Input is `nl_description` only; output JSON `{"circuit_type": "CMB"|"SEQ"}` unchanged.
- `classify_node` render call drops the `golden_dut=` kwarg.

## 5. Reporting (`pipeline/reporting.py`)

```python
def parse_scenarios(sim_output: str) -> list[dict]:
    # returns [{"name": str, "passed": bool}] from PASS:/FAIL: lines

def print_run_summary(result: dict) -> None:
    # prints the human-readable block to stdout
```

`print_run_summary` reads the same dict persisted to `results/<run_id>.json`. It must render when `llm_calls` is empty and when `scenario_results` is empty.

### Summary output contract (fields that MUST appear)

- module name, run_id, circuit_type
- the natural-language description (possibly truncated)
- `N of M scenarios passed` with failing scenario names listed
- Eval0 (compiles), Eval1 (passes), Eval2 (mutants caught) results
- repair iterations
- total tokens (in / out)
- wall time
- final status
- which DUT evaluation used (`eval_dut_source`)

## 6. Result JSON schema additions

See [data-model.md](../data-model.md#result-json-resultsrun_idjson). New keys: `nl_description`, `dut_rtl`, `eval_dut_source`, `scenario_results`, `scenarios_passed`, `scenarios_total`, `tokens_in_total`, `tokens_out_total`.

## 7. Test fixture contract (`tests/conftest.py`)

```python
@pytest.fixture
def fake_llm(monkeypatch):
    # monkeypatches pipeline.llm.llm_call (and re-exports in nodes) to return
    # canned (text, log) keyed by `node`. Zero network calls.
```

- Canned responses keyed by node name: `classify`, `gen_dut`, `extract_spec`, `gen_scenarios`, `gen_driver`, `gen_checker`, `gen_mutant`, `error_reasoner`, `repair`.
- Each canned `log` dict includes `temperature` so downstream token/temperature assertions work.
- Live tests use marker `live`, registered in `pyproject.toml`, `skipif` when no API key env is present.