# Phase 0 Research: Evaluation Harness

## D1 — Where the logic lives

- **Decision**: `pipeline/eval/harness.py` (runner) and `pipeline/eval/aggregate.py`
  (aggregation) as importable modules; `scripts/run_eval.py` a thin CLI; existing
  `scripts/aggregate_results.py` becomes a back-compat wrapper delegating to the new module.
- **Rationale**: Importable modules are unit-testable offline; CLIs are not. Keeps the
  aggregation figures verifiable without a shell.
- **Alternatives**: Bash `run_eval.sh` — rejected; hard to unit-test and to enforce the budget
  guard programmatically.

## D2 — Recording the mode

- **Decision**: Add `mode: str` to `GraphState`; `__main__` and the harness set it from the
  chosen `AblationMode`; `evaluate_node._write_result` writes `mode` into the result JSON.
- **Rationale**: The aggregator groups by mode; today the field is absent so grouping collapses
  to "unknown". This is the minimal fix (FR-001).
- **Alternatives**: Infer mode from the filename — rejected, brittle.

## D3 — Token-budget guard

- **Decision**: `run_sweep(modules, modes, limit=None, opt_in=False)`. `n = len(modules)*len(modes)`
  (after applying `limit`). `SAFE_THRESHOLD = 24`. If effective `n > SAFE_THRESHOLD` and not
  `opt_in`, refuse and print the estimate + how to proceed (`--yes` or `--limit`). Always print
  the estimate before running.
- **Rationale**: The free tier cannot absorb 624 runs; a default subset + explicit opt-in makes a
  large sweep a deliberate choice (FR-004/005/006, US3). 24 ≈ 5–6 modules × 4 modes — comfortably
  covers the default CMB fixture sweep (20) without opt-in.
- **Alternatives**: Token-cost estimate in dollars — rejected; run-count is the honest, provider-
  agnostic proxy on a free tier.

## D4 — Module selection vocabulary

- **Decision**: `--modules` accepts explicit names or the keywords `cmb-fixtures` (default),
  `seq-fixtures`, `smoke` (= CMB fixtures), or `verilogeval[:N]`. The resolver reuses
  `__main__.load_module`.
- **Rationale**: Named presets keep common sweeps one flag away; `verilogeval:N` bounds the
  expensive set explicitly.
- **Alternatives**: Only explicit names — rejected, tedious and error-prone.

## D5 — De-duplication of re-runs

- **Decision**: The aggregator keeps the **newest** record per `(module, mode)` by file mtime.
  Documented in the aggregator.
- **Rationale**: Re-running a module (e.g. after a fix) would otherwise double-count; newest-wins
  matches intent (FR — edge case).
- **Alternatives**: Count all — rejected (skews rates); error on duplicates — rejected (too rigid
  for iterative work).

## D6 — Failure attribution & status distribution

- **Decision**: Per mode (and overall), tally `failure_stage` and `final_status` into counts and
  fractions. `failure_stage` is already written by `evaluate_node` (values like `gen_driver`,
  `gen_dut`, `evaluate`, or null on success).
- **Rationale**: Directly produces the per-node attribution contribution (FR-011, US2, SC-002)
  from data already recorded.

## D7 — Per-run failure isolation

- **Decision**: `run_sweep` wraps each `graph.invoke` in try/except; on error it records a minimal
  failed result (`final_status="harness_error"`, the exception text, mode/module) and continues.
- **Rationale**: One bad module must not abort a multi-hour sweep (FR-007).

## D8 — Precision/recall (FR-017)

- **Decision**: Out of scope for this feature; noted as a follow-up. Needs a hand-labelled set,
  which is manual data work best done separately.
- **Rationale**: Keeps this feature shippable and offline-testable; avoids blocking on labelling.
