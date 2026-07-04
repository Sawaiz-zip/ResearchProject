# Phase 1 Data Model: State & Result Schema Changes

## GraphState (`pipeline/state.py`)

### New / changed fields

| Field | Type | Change | Meaning |
|---|---|---|---|
| `nl_description` | `str` | unchanged (input) | User's plain-English circuit description |
| `golden_dut` | `str` | **now optional** | Reference DUT; empty string `""` when the user supplied none. Used **only** at evaluation. |
| `dut_rtl` | `str` | **NEW** | LLM-generated DUT produced by `gen_dut`. Consumed by generation + static analysis. |
| `eval_dut_source` | `Literal["golden", "generated"]` | **NEW** | Which DUT `evaluate_node` actually compiled/simulated against. |
| `scenario_results` | `list[dict]` | **NEW** | `[{"name": str, "passed": bool}]` parsed from `sim_output`. |

`golden_dut` remains a key in the TypedDict but callers must tolerate `""`. Generation nodes never read `golden_dut` directly — they read `dut_rtl` (with a `golden_dut` fallback only if `dut_rtl` is empty, to keep old fixtures working).

### llm_calls entry (per-call log)

| Field | Type | Change |
|---|---|---|
| `temperature` | `float` | **NEW** — the temperature actually used for the call |

Existing fields (`node, model, provider, run_id, tokens_in, tokens_out, latency_ms, rate_limit_retries`) unchanged.

## Result JSON (`results/<run_id>.json`)

### New fields

| Field | Type | Source |
|---|---|---|
| `nl_description` | `str` | `state["nl_description"]` (FR-012) |
| `dut_rtl` | `str` | generated DUT (FR-005) |
| `eval_dut_source` | `str` | `"golden"` or `"generated"` (FR-008) |
| `scenario_results` | `list[{name, passed}]` | `parse_scenarios(sim_output)` (FR-013) |
| `scenarios_passed` | `int` | count of `passed == True` |
| `scenarios_total` | `int` | `len(scenario_results)` |
| `tokens_in_total` | `int` | sum over `llm_calls` |
| `tokens_out_total` | `int` | sum over `llm_calls` |

Existing fields retained. `golden_dut` is **not** added to the result to avoid bloat (it's benchmark input, not generated output).

## PipelineConfig (`pipeline/config.py`)

| Field | Type | Change |
|---|---|---|
| `default_temperature` | `float` | **NEW** — `float(os.environ.get("LLM_TEMPERATURE", "0.7"))` |

## State transitions (graph order)

```
classify            (reads nl_description → circuit_type)
   ↓
gen_dut             (reads nl_description + circuit_type → dut_rtl)      ← NEW
   ↓
extract_spec        (reads nl_description + dut_rtl → spec)
   ↓
gen_scenarios
   ↓ (fan-out)
gen_driver ‖ gen_checker
   ↓ (fan-in)
[standardise if SEQ]
   ↓
pyverilog_analysis  (reads driver_rtl + dut_rtl → pyverilog_report)
   ↓
error_reasoner
   ↓ (should_repair?)
repair ⟲ gen_driver   |   evaluate
   ↓
evaluate            (eval DUT = golden_dut if present else dut_rtl;
                     writes eval fields + scenario_results + eval_dut_source)
   ↓
END
```

## Validation rules

- `dut_rtl` must be non-empty after `gen_dut`; if empty, `evaluate_node` sets `failure_stage="gen_dut"`, `final_status="failed_compile"`.
- `eval_dut_source` is `"golden"` iff `golden_dut.strip()` is non-empty at evaluation time, else `"generated"`.
- `scenario_results` may be empty (e.g. run failed before simulation) — summary must render `0 of 0`.
- `temperature` in each log entry must equal the resolved temperature (arg → env → 0.7).