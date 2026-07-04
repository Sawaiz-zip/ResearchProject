# Implementation Plan: Repair Loop (Static + Compiler + Simulation Feedback)

**Branch**: `phase-2-pyverilog` (working branch) | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-repair-loop/spec.md`

## Summary

Implement the Phase 3 repair loop. Detected errors from three sources — Pyverilog
static analysis, compilation (Eval0), and simulation (Eval1) — are fed back to the
model, which regenerates the testbench; the loop re-checks and iterates until the
testbench passes, the iteration budget (default 3) is spent, or oscillation is
detected. Two conditional entry points into `repair`: one after `error_reasoner`
(static errors) and a new one after `evaluate` (compile/sim failures). The four
ablation modes become genuinely distinct by restricting which source triggers
repair. Every iteration is logged with its trigger source and token cost.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: LangGraph, Anthropic/OpenAI-compat SDK (Groq free tier), Pyverilog, Jinja2, pytest
**Storage**: `results/<run_id>.json`
**Testing**: pytest; offline via `tests/conftest.py` `fake_llm` (extended to script per-iteration responses)
**Target Platform**: Local CLI
**Project Type**: Single-project research pipeline
**Performance Goals**: Bounded token cost — repair must reuse eval artifacts (mutants) and never exceed max iterations
**Constraints**: Free-tier API budget; loop MUST terminate; iverilog v13
**Scale/Scope**: Single-module runs; loop bounded at 3 iterations

## Constitution Check

*Against `.specify/memory/constitution.md` v1.1.0.*

| Principle | Status | Note |
|---|---|---|
| I. Graph-First Architecture | ✅ | Repair routing is explicit conditional edges (`should_repair`, `should_repair_after_eval`, `after_repair`). No hidden control flow. |
| II. Prompt Externalisation | ✅ | Reuses `prompts/repair_driver.j2`. |
| III. Full LLM Call Logging | ✅ | Repair calls logged via `llm_call` (incl. temperature, tokens); plus a `repair_history` entry per iteration. |
| IV. Configurable Temperature | ✅ | Repair uses the shared temperature config. |
| V. CMB Before SEQ | ✅ | Loop is circuit-type agnostic; CMB remains primary. |
| VI. Deterministic Standardisation | ✅ | Untouched. |
| VII. Static Analysis Before Simulation | ✅ | Static feedback still precedes simulation; sim feedback is an additional, later trigger. |
| VIII. Model Routing Per Node | ✅ | Repair = Sonnet. |
| IX. Reproducibility & Test Isolation | ✅ | Tests mock the LLM and script per-iteration responses deterministically. |
| X. Research-Question Traceability | ✅ | Repair node maps to RQ3 (repair effectiveness) and RQ4 (cost). |

**Gate result**: PASS, no amendments.

## Project Structure

### Documentation (this feature)

```text
specs/004-repair-loop/
├── plan.md · spec.md · research.md · data-model.md · quickstart.md
├── contracts/interfaces.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
pipeline/
├── nodes/repair.py          # IMPLEMENT repair_node; add after_repair; refine should_repair;
│                            #   add should_repair_after_eval; add _error_signature()
├── nodes/evaluate.py        # EDIT: on Eval0/Eval1 fail write error_report + feedback_source;
│                            #   respect oscillation/exhaustion when setting final_status;
│                            #   persist repair_iter + repair_history
├── graph.py                 # EDIT: repair -> conditional after_repair {gen_driver, evaluate};
│                            #   evaluate -> conditional should_repair_after_eval {repair, END}
├── state.py                 # EDIT: add repair_history, last_repair_signature, feedback_source
└── config.py                # (max_repair_iter already = 3; no change expected)

prompts/repair_driver.j2     # REVIEW: ensure it renders error_report detail (compile msg,
                             #   failing scenarios) — minor edit if needed

tests/
├── conftest.py              # EDIT: fake_llm gains a 'repair' response + scripted/stateful mode
├── unit/test_repair_node.py # NEW: repair_node increments, logs history, oscillation signature
└── integration/test_repair_loop.py  # NEW: all 4 modes, oscillated, exhausted_iters,
                             #   success-within-budget, no-deadlock fan-in check
```

**Structure Decision**: Surgical edits to `repair.py`, `evaluate.py`, `graph.py`, `state.py`
plus two new test files and a `conftest` extension. The graph gains two conditional edges
and converts one fixed edge (`repair→gen_driver`) into a conditional.

## Graph After This Feature

```
classify → gen_dut → extract_spec → gen_scenarios → (gen_driver ‖ gen_checker)
  → [standardise if SEQ] → pyverilog_analysis → error_reasoner
      │
      └─ should_repair(mode) ──► repair ──► after_repair ──► gen_driver   (continue loop)
                              └► evaluate         └────────► evaluate      (oscillation/exhausted)
                                     │
                                     └─ should_repair_after_eval(mode) ──► repair (compile/sim feedback)
                                                                       └─► END
```

- **should_repair** (post static analysis): repair only for PYVERILOG_ONLY / HYBRID when
  `error_report` non-empty, under budget, not oscillating.
- **should_repair_after_eval** (post evaluation): repair for COMPILER_ONLY on Eval0 fail;
  for HYBRID on Eval0 or Eval1 fail; never for BASELINE / PYVERILOG_ONLY; END on success,
  exhaustion, or oscillation.
- **after_repair**: `evaluate` if `oscillation_detected` or `repair_iter > max`; else `gen_driver`.

## Complexity Tracking

*No constitution violations — table omitted.*

Key risk tracked in research.md: LangGraph fan-in into `pyverilog_analysis` when the loop
re-enters at `gen_driver` only. Mitigation validated by a no-deadlock integration test; if
LangGraph blocks, fall back to re-triggering `gen_checker` on the repair path or collapsing
the fan-in.
