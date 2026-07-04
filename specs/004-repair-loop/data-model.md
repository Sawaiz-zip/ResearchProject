# Phase 1 Data Model: Repair Loop

## GraphState additions (`pipeline/state.py`)

| Field | Type | Meaning |
|---|---|---|
| `repair_history` | `list[dict]` | one entry per repair iteration (see below); reducer-appended |
| `last_repair_signature` | `str` | error signature of the previous repair attempt (oscillation) |
| `feedback_source` | `Literal["static", "compile", "simulation", ""]` | source that triggered the most recent repair |

Existing loop-control fields reused: `repair_iter`, `max_repair_iter`,
`oscillation_detected`, `error_report`, `last_error_report`.

### Repair history entry

```
{
  "iteration": int,           # 1-based
  "feedback_source": str,     # "static" | "compile" | "simulation"
  "tokens_in": int,
  "tokens_out": int,
  "error_signature": str,
}
```

### error_report entries written by evaluate (new shapes)

```
# Eval0 (compile) failure:
{"error_type": "compile_error", "signal": "", "detail": <compiler_output>,
 "suggested_fix": "Fix the Verilog so it compiles under iverilog -g2012."}

# Eval1 (simulation) failure:
{"error_type": "eval1_mismatch", "signal": "",
 "failing_scenarios": ["name1", "name2", ...],
 "detail": <sim_output>,
 "suggested_fix": "Correct the expected values for the failing scenarios to match the DUT."}
```

## Result JSON additions (`results/<run_id>.json`)

| Field | Type | Source |
|---|---|---|
| `repair_iter` | `int` | already present; now non-zero when repairs occur |
| `repair_history` | `list[dict]` | new — the per-iteration log |
| `feedback_source` | `str` | new — last trigger source |

## Final status values (`final_status`)

Unchanged enum, now fully exercised:
`success` · `failed_compile` · `failed_eval1` · `failed_eval2` · `oscillated` · `exhausted_iters` · `invalid_dut`

Resolution order at finalisation:
1. `oscillation_detected` → `oscillated`
2. Eval passed → `success`
3. `repair_iter >= max_repair_iter` and not passed → `exhausted_iters`
4. else specific failure (`failed_compile` / `failed_eval1` / `failed_eval2`)

## Loop invariants (validation rules)

- `repair_iter` never exceeds `max_repair_iter` (FR-009, FR-012).
- Each productive iteration appends exactly one `repair_history` entry.
- `oscillation_detected == True` ⟹ loop routes to finalisation, never back to `gen_driver`.
- On success, `error_report` is cleared.
- The DUT (`dut_rtl` / `golden_dut`) is never modified by repair — only `driver_rtl` changes.

## Control-flow transitions

```
error_reasoner ── should_repair ──► repair ── after_repair ──► gen_driver | evaluate
evaluate ── should_repair_after_eval ──► repair | END
repair: repair_iter += 1 (unless oscillating); append repair_history; set feedback_source,
        last_repair_signature, last_error_report; regenerate driver_rtl.
```
