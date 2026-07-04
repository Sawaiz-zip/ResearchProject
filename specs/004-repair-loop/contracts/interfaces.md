# Phase 1 Contracts: Repair Loop Interfaces

## 1. `repair_node` (`pipeline/nodes/repair.py`)

```python
def repair_node(state: GraphState) -> dict:
    # reads:  error_report, driver_rtl, spec, scenarios, module_name, run_id,
    #         repair_iter, last_repair_signature, feedback_source
    # returns (partial state update):
    #   {"driver_rtl": <regenerated>, "repair_iter": n+1,
    #    "last_error_report": <snapshot>, "last_repair_signature": <sig>,
    #    "oscillation_detected": bool, "repair_history": [entry],
    #    "llm_calls": [log]}
```

- Model: Sonnet (`cfg.model_strong`).
- Oscillation: if `_error_signature(error_report) == last_repair_signature` OR the newly
  regenerated driver equals the current `driver_rtl`, set `oscillation_detected=True` and
  do **not** increment `repair_iter` / append a productive history entry (append a history
  entry marked oscillated is optional).
- Never raises on malformed model output (tolerant `extract_code_block`, Constitution IV).

## 2. `_error_signature` helper

```python
def _error_signature(error_report: list[dict]) -> str:
    # stable string: sorted tuple of (error_type, signal or first detail key)
```

## 3. Routing functions (`pipeline/nodes/repair.py`)

```python
def should_repair(state, mode) -> str:            # "repair" | "evaluate"   (post error_reasoner)
def should_repair_after_eval(state, mode) -> str: # "repair" | "END"        (post evaluate)
def after_repair(state) -> str:                   # "gen_driver" | "evaluate"
```

### should_repair (post static analysis)
- BASELINE / COMPILER_ONLY → `"evaluate"` (they don't repair on static)
- empty `error_report` → `"evaluate"`
- `repair_iter >= max` or `oscillation_detected` → `"evaluate"`
- PYVERILOG_ONLY / HYBRID with non-empty static `error_report` → `"repair"`

### should_repair_after_eval (post evaluation)
- BASELINE / PYVERILOG_ONLY → `"END"`
- eval passed (`eval0_pass and eval1_pass`) → `"END"`
- `repair_iter >= max` or `oscillation_detected` → `"END"`
- COMPILER_ONLY → `"repair"` iff `not eval0_pass` else `"END"`
- HYBRID → `"repair"` iff `not eval0_pass or not eval1_pass` else `"END"`

### after_repair
- `oscillation_detected` or `repair_iter > max` → `"evaluate"`; else `"gen_driver"`

## 4. `evaluate_node` additions (`pipeline/nodes/evaluate.py`)

- On Eval0 fail: set `error_report=[compile_error{...}]`, `feedback_source="compile"`.
- On Eval1 fail: set `error_report=[eval1_mismatch{...}]` with `failing_scenarios` from
  `scenario_results`, `feedback_source="simulation"`.
- On success: clear `error_report`.
- Finalisation `final_status` per data-model resolution order (oscillated / success /
  exhausted_iters / specific failure).
- Persist `repair_iter`, `repair_history`, `feedback_source` in the result JSON.
- Eval2/mutants only after Eval0+Eval1 pass; reuse cached mutants across iterations.

## 5. Graph wiring (`pipeline/graph.py`)

```python
g.add_conditional_edges("error_reasoner",
    lambda s: should_repair(s, config.mode), {"repair": "repair", "evaluate": "evaluate"})
g.add_conditional_edges("repair",
    after_repair, {"gen_driver": "gen_driver", "evaluate": "evaluate"})
g.add_conditional_edges("evaluate",
    lambda s: should_repair_after_eval(s, config.mode), {"repair": "repair", "END": END})
```

(Removes the old fixed `repair→gen_driver` and `evaluate→END` edges.)

## 6. Test contract (`tests/conftest.py` + tests)

- `fake_llm` gains a `"repair"` canned response and a **scripted mode**: a per-node response
  queue (or counter) so a test can return a still-broken TB twice (→ oscillation) or a fixed
  TB on the 2nd call (→ success within budget).
- Integration test asserts, per mode, the number of `repair_history` entries and the
  `final_status`; asserts `repair_iter <= max_repair_iter` always; asserts a full repair
  cycle completes without LangGraph deadlock.
- One `@pytest.mark.live` test (skips without key).
