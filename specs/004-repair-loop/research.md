# Phase 0 Research: Repair Loop

## D1 — Two repair entry points vs one

- **Decision**: Two conditional edges into `repair`: `should_repair` after `error_reasoner`
  (static errors) and `should_repair_after_eval` after `evaluate` (compile/sim failures).
- **Rationale**: Static errors are known before simulation; compile/sim failures are only
  known after `evaluate`. Distinct triggers give the ablation modes clean semantics.
- **Alternatives**: Route all feedback through a single post-evaluate check — rejected
  because it would run simulation even when a static error already justifies repair,
  wasting the cheap static signal (violates Principle VII spirit).

## D2 — Mode → trigger matrix

| Mode | Static (post-analysis) | Compile fail (post-eval) | Sim fail (post-eval) |
|---|---|---|---|
| BASELINE | no | no | no |
| COMPILER_ONLY | no | **yes** | no |
| PYVERILOG_ONLY | **yes** | no | no |
| HYBRID | **yes** | **yes** | **yes** |

- **Rationale**: Each mode isolates exactly one feedback family (except HYBRID = all),
  which is what the ablation study compares. COMPILER_ONLY deliberately ignores static
  and semantic signals; PYVERILOG_ONLY deliberately ignores runtime signals.
- **Alternatives**: Letting PYVERILOG_ONLY also repair compile errors — rejected, blurs
  the ablation boundary.

## D3 — Feeding compile/sim failures into `error_report`

- **Decision**: On Eval0 failure `evaluate_node` writes
  `error_report=[{"error_type":"compile_error","detail":<compiler_output>, ...}]` and
  `feedback_source="compile"`. On Eval1 failure it writes
  `error_report=[{"error_type":"eval1_mismatch","failing_scenarios":[...],"detail":<sim_output>}]`
  and `feedback_source="simulation"`. `repair_node` (reached right after `evaluate`, before
  `error_reasoner` re-runs) reads this to build the repair prompt.
- **Rationale**: One uniform `error_report` shape drives both the repair prompt and
  oscillation signature regardless of source. `should_repair_after_eval` can also reuse the
  existing `compile_error` check already present in `should_repair`.
- **Alternatives**: A separate compile-feedback channel — rejected as duplicate machinery.

## D4 — Oscillation detection

- **Decision**: `repair_node` computes a stable `_error_signature(error_report)` (sorted
  tuple of `(error_type, signal/detail-key)`), and also compares the newly regenerated
  driver to the previous driver. Oscillation = signature equals `last_repair_signature`
  **or** regenerated driver is byte-identical to the prior driver. On oscillation it sets
  `oscillation_detected=True` and does **not** count a productive iteration.
- **Rationale**: Catches both "same errors recurring" and "model returns identical TB".
  Signature over raw text is robust to trivial reordering; driver-identity catches the
  stuck-model case even if error text drifts.
- **Alternatives**: Hashing only the driver — misses cases where the model reshuffles but
  keeps the same bug; using only error equality — misses identical-output stalls.

## D5 — Loop termination & final status

- **Decision**: `repair_iter` increments once per productive repair, bounded by
  `max_repair_iter` (3). `after_repair` routes to `evaluate` (not `gen_driver`) when
  `oscillation_detected` or `repair_iter > max`. `evaluate_node`/finalisation sets:
  `success` (evals pass), `oscillated` (oscillation flag set), `exhausted_iters`
  (budget hit without success), else the specific `failed_compile`/`failed_eval1`/
  `failed_eval2`.
- **Rationale**: Guarantees termination (FR-012) and precise status (FR-011).
- **Alternatives**: Terminating inside `repair_node` by jumping to END — rejected;
  `evaluate` is the single place that writes the result, so routing back through it keeps
  one source of truth.

## D6 — LangGraph fan-in risk

- **Decision**: Re-enter the loop at `gen_driver` only. Validate with a mocked
  integration test that a full repair cycle (`repair → gen_driver → pyverilog_analysis →
  error_reasoner → evaluate`) completes without deadlock. If LangGraph blocks waiting on
  `gen_checker` at the `pyverilog_analysis` fan-in, fall back to also re-triggering
  `gen_checker` on the repair path (checker output is cheap and idempotent) or collapse the
  two edges.
- **Rationale**: The checker track does not need regeneration on every repair (D of spec
  Assumptions); avoid unnecessary LLM calls. Empirical test decides if the fallback is
  needed.
- **Alternatives**: Always regenerate both tracks — simplest but spends an extra Sonnet
  call per iteration; deferred unless the deadlock test forces it.

## D7 — Cost control on the sim-repair path

- **Decision**: `evaluate_node` runs Eval2 (mutant generation) only after Eval0+Eval1 pass;
  on failure it returns before Eval2. Mutants, once generated, are cached in state and not
  regenerated across iterations. So repair iterations spend only the single `repair`
  regeneration call each (plus re-simulation, which is free).
- **Rationale**: Bounds per-iteration token cost to one Sonnet call (FR + spec cost
  assumption).
- **Alternatives**: Regenerating mutants each loop — rejected, wasteful.

## D8 — Prompt reuse

- **Decision**: Reuse `prompts/repair_driver.j2` (already exists). Confirm it surfaces the
  error detail (compile message / failing scenarios). Minor edit only if a field is missing.
- **Rationale**: Avoid prompt sprawl; the template already takes `error_report`, `spec`,
  `scenarios`, `driver_rtl`, `module_name`.
