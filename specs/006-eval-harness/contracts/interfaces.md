# Phase 1 Contracts: Evaluation Harness Interfaces

## 1. Runner (`pipeline/eval/harness.py`)

```python
SAFE_THRESHOLD = 24
DEFAULT_MODULES = ["alu_1bit", "mux2to1", "half_adder", "comparator_2bit", "priority_encoder"]

def estimate_runs(modules: list[str], modes: list, limit: int | None = None) -> int
    # len(modules[:limit]) * len(modes)

def resolve_modules(selector: str | list[str]) -> list[str]
    # keywords: "cmb-fixtures"/"smoke" -> DEFAULT_MODULES; "seq-fixtures" -> SEQ fixtures;
    # "verilogeval[:N]" -> first N VerilogEval problem keys; else treat as explicit names.

def run_sweep(modules, modes, *, limit=None, opt_in=False, results_dir="results",
              graph_invoke=None) -> dict
    # prints the run-count estimate; if effective n > SAFE_THRESHOLD and not opt_in -> refuse
    #   (return {"ran": 0, "refused": True, "n": n}); else run each (module, mode):
    #   build state (with mode tag), invoke the graph, write results/<run_id>.json,
    #   catch per-run exceptions (record final_status="harness_error", continue).
    # `graph_invoke` is injectable for tests (defaults to the real build_graph+invoke).
    # returns {"ran": int, "refused": bool, "n": int, "results": [run summaries]}.
```

## 2. Aggregator (`pipeline/eval/aggregate.py`)

```python
def aggregate(results_dir: str = "results") -> dict
    # read results/*.json (skip summary.json + malformed), de-dup newest per (module,mode),
    # group by mode, compute the summary schema (see data-model.md), write summary.json, return it.

def print_summary_table(summary: dict) -> None
    # human-readable per-mode table to stdout.
```

## 3. Result tagging (`pipeline/nodes/evaluate.py`, `pipeline/state.py`, `pipeline/__main__.py`)

- `GraphState` gains `mode: str`.
- `evaluate_node._write_result` adds `"mode": state.get("mode", "")` to the result dict.
- `__main__` and `run_sweep` set `state["mode"] = mode.value`.

## 4. CLI (`scripts/run_eval.py`)

```
python scripts/run_eval.py [--modules cmb-fixtures|seq-fixtures|verilogeval[:N]|<names...>]
                           [--modes baseline compiler_only pyverilog_only hybrid]
                           [--limit N] [--yes] [--results-dir results] [--no-aggregate]
```
- Prints the estimate; enforces the guard; runs the sweep; then calls `aggregate` +
  `print_summary_table` (unless `--no-aggregate`).

`scripts/aggregate_results.py` → thin wrapper calling `pipeline.eval.aggregate.aggregate()`.

## 5. Tests

- `tests/unit/test_aggregate.py`: write synthetic result dicts to a tmp dir; assert every
  computed figure; empty dir → graceful; malformed record skipped; newest-wins de-dup; failure
  fractions per mode sum to 1.
- `tests/unit/test_harness_guard.py`: `estimate_runs` correct; `run_sweep` with a large selection
  and `opt_in=False` refuses (0 runs) via an injected `graph_invoke` that must NOT be called;
  proceeds with `--limit`/`opt_in`. No API calls.
- `tests/integration/test_harness_smoke_mocked.py`: `run_sweep` over 1 fixture × 2 modes with
  `fake_llm` + `mock_icarus`; assert 2 result files each tagged with its mode; `aggregate` yields
  2 mode entries.
