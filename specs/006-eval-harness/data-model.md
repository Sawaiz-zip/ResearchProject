# Phase 1 Data Model: Evaluation Harness

## GraphState addition (`pipeline/state.py`)

| Field | Type | Meaning |
|---|---|---|
| `mode` | `str` | the ablation mode for this run (`baseline`/`compiler_only`/`pyverilog_only`/`hybrid`) |

## Result JSON addition (`results/<run_id>.json`)

| Field | Type | Source |
|---|---|---|
| `mode` | `str` | `state["mode"]` (FR-001) |
| `module_name` | `str` | already present (FR-002) |

All other fields already exist: `eval0_pass`, `eval1_pass`, `eval2_pass_rate`, `repair_iter`,
`repair_history`, `wall_clock_ms`, `tokens_in_total`, `tokens_out_total`, `final_status`,
`failure_stage`, `scenarios_passed`, `scenarios_total`, `nl_description`, `circuit_type`.

## Summary JSON (`results/summary.json`)

```
{
  "<mode>": {
    "n": int,
    "eval0_pass_rate": float, "eval1_pass_rate": float, "eval2_pass_rate": float,
    "mean_repair_iter": float,
    "mean_tokens_in": float, "mean_tokens_out": float,
    "mean_wall_clock_ms": float,
    "mean_scenarios_passed": float, "mean_scenarios_total": float,
    "final_statuses": {"<status>": count, ...},
    "failure_stages": {"<stage or 'none'>": {"count": int, "fraction": float}, ...}
  },
  ...
}
```

## Sweep Selection (in-memory, `pipeline/eval/harness.py`)

| Field | Meaning |
|---|---|
| `modules` | resolved list of module identifiers |
| `modes` | list of `AblationMode` |
| `limit` | optional cap on module count |
| `opt_in` | bool authorising a large sweep |
| `n` | `len(modules) * len(modes)` after limit — the implied run count |

## Validation rules

- Every result record used by the aggregator has a non-empty `mode`; records lacking it are
  grouped under `"unknown"` (and flagged), not dropped silently.
- De-dup: exactly one record per `(module_name, mode)` survives (newest by mtime).
- Rates are in `[0, 1]`; means over an empty group are reported as `0` (not division error).
- Failure-stage fractions per mode sum to `1.0` (within float tolerance) across all stages incl.
  `"none"` (successes).
- `run_sweep` with `n > SAFE_THRESHOLD` and `opt_in=False` performs **zero** runs.
