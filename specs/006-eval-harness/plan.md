# Implementation Plan: Evaluation Harness (Ablation Study)

**Branch**: `phase-2-pyverilog` (working branch) | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-eval-harness/spec.md`

## Summary

Add the Phase-4 ablation harness: tag each result record with its mode + module, a
token-budget-aware batch runner over modules × the four ablation modes, and an enhanced
aggregator producing a machine-readable `summary.json` plus a human-readable table with
per-mode Eval0/1/2 rates, mean repair/token/time cost, final-status distribution, and
per-node failure attribution. Aggregation is unit-tested offline on synthetic records;
the runner is exercised on a tiny mocked sweep. No real-API sweep runs in tests.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing pipeline (LangGraph graph), pytest; stdlib only for aggregation
**Storage**: `results/<run_id>.json` per run; `results/summary.json` aggregate
**Testing**: pytest; offline via synthetic records + `fake_llm`/`mock_icarus`
**Target Platform**: Local CLI
**Project Type**: Single-project research pipeline (tooling layer)
**Performance Goals**: N/A (batch tool); the binding constraint is API token budget
**Constraints**: Free-tier budget — default small subset, opt-in gate for large sweeps; iverilog v13
**Scale/Scope**: Default 5 CMB fixtures × 4 modes = 20 runs; full VerilogEval (156×4=624) only on explicit opt-in

## Constitution Check

*Against `.specify/memory/constitution.md` v1.1.0.*

| Principle | Status | Note |
|---|---|---|
| I. Graph-First Architecture | ✅ | Harness orchestrates whole-graph runs; adds no hidden control flow inside the graph. |
| II. Prompt Externalisation | ✅ | No prompts. |
| III. Full LLM Call Logging | ✅ | Consumes existing per-run logs; adds mode/module tags. |
| IV. Configurable Temperature | ✅ | Unaffected. |
| V. CMB Before SEQ | ✅ | Default subset is CMB fixtures; SEQ optional. |
| VI. Deterministic Standardisation | ✅ | Unaffected. |
| VII. Static Analysis Before Simulation | ✅ | Unaffected. |
| VIII. Model Routing Per Node | ✅ | No new LLM nodes. |
| IX. Reproducibility & Test Isolation | ✅ | Aggregation deterministic; tests offline. Ablation runnable via a single mode flag (Workflow rule 5). |
| X. Research-Question Traceability | ✅ | Harness ↔ RQ3 (repair effectiveness), RQ4 (cost), + per-node failure attribution contribution. |

**Gate result**: PASS, no amendments.

## Project Structure

### Documentation (this feature)

```text
specs/006-eval-harness/
├── plan.md · spec.md · research.md · data-model.md · quickstart.md
├── contracts/interfaces.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
pipeline/
├── state.py                  # EDIT: add `mode: str`
├── nodes/evaluate.py         # EDIT: write `mode` into the result JSON
├── __main__.py               # EDIT: set state["mode"]=mode.value in initial_state
└── eval/
    ├── harness.py            # NEW: run_sweep(), estimate/guard, module resolver
    └── aggregate.py          # NEW: aggregate(results_dir) + print_summary_table()

scripts/
├── run_eval.py               # NEW: CLI for the batch sweep (estimate → guard → run → aggregate)
└── aggregate_results.py      # REWRITE as thin wrapper → pipeline.eval.aggregate

tests/
├── unit/test_aggregate.py    # NEW: synthetic records → assert figures; empty/malformed; de-dup; attribution
├── unit/test_harness_guard.py# NEW: estimate; refuse-over-threshold; proceed with limit/opt-in (mocked invoke)
└── integration/test_harness_smoke_mocked.py  # NEW: run_sweep 1 fixture × 2 modes (fake_llm+mock_icarus)
```

**Structure Decision**: Put the reusable logic in `pipeline/eval/` (importable + unit-testable);
keep `scripts/run_eval.py` a thin CLI. `scripts/aggregate_results.py` becomes a back-compat
shim delegating to `pipeline.eval.aggregate`. The module resolver reuses `__main__.load_module`.

## Key Design Points

- **Budget guard**: `run_sweep` computes `n = len(modules) * len(modes)`; if `n > SAFE_THRESHOLD`
  (default 24) and neither `opt_in` nor an effective `limit` bounds it below the threshold, it
  refuses and prints how to proceed. It always prints the estimate first.
- **De-dup**: aggregator keeps the newest record per `(module, mode)` by file mtime (documented
  rule) to avoid double-counting re-runs.
- **Failure attribution**: distribution over `failure_stage` (per mode and overall) as counts +
  fractions; final-status distribution similarly.
- **Token means**: prefer the `tokens_in_total` / `tokens_out_total` fields; fall back to summing
  `llm_calls` for older records.
- **Graceful degradation**: malformed/partial records are skipped; empty set → "nothing to
  aggregate" rather than a crash.

## Complexity Tracking

*No constitution violations.* The only risk is accidental cost; mitigated by the default-small-subset
+ opt-in guard, verified by `test_harness_guard.py`.
