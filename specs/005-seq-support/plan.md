# Implementation Plan: Sequential (SEQ) Circuit Support

**Branch**: `phase-2-pyverilog` (working branch) | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-seq-support/spec.md`

## Summary

Enable the sequential path end-to-end. Implement the deterministic `$fdisplay`/`$monitor`
standardiser (Python-only, no LLM), wire the currently-dead `standardise` node into the
graph behind a circuit-type branch (SEQ passes through it, CMB skips it), ensure SEQ
testbench generation clocks correctly, add a small SEQ fixture set, and exercise the
existing Pyverilog SEQ checks on real sequential runs. The combinational path is untouched.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: LangGraph, Pyverilog, Jinja2, Icarus Verilog v13, pytest
**Storage**: `results/<run_id>.json`
**Testing**: pytest; offline via `tests/conftest.py` `fake_llm`
**Target Platform**: Local CLI
**Project Type**: Single-project research pipeline
**Performance Goals**: Standardiser adds zero LLM cost (deterministic); SEQ path bounded like CMB
**Constraints**: Free-tier API budget; iverilog v13; Constitution VI (no LLM standardisation)
**Scale/Scope**: Simple/moderate sequential circuits (DFF, counter, shift register, simple FSM)

## Constitution Check

*Against `.specify/memory/constitution.md` v1.1.0.*

| Principle | Status | Note |
|---|---|---|
| I. Graph-First Architecture | ✅ | SEQ routing is an explicit conditional edge on `circuit_type`; a `merge_generation` join node gives a deterministic fan-in barrier. |
| II. Prompt Externalisation | ✅ | Only reviews/edits existing `gen_dut.j2` / `gen_driver.j2`. |
| III. Full LLM Call Logging | ✅ | Standardiser makes zero LLM calls; `standardise_node` logs none. |
| IV. Configurable Temperature | ✅ | Unaffected. |
| V. CMB Before SEQ | ✅ | Precondition satisfied (CMB smoke 5/5). This is the sanctioned start of SEQ work. |
| **VI. Deterministic Standardisation** | ✅ **Core** | The standardiser is Python-only, idempotent, independently unit-tested — exactly what Principle VI mandates. |
| VII. Static Analysis Before Simulation | ✅ | `standardise` runs before `pyverilog_analysis`, which runs before Icarus. |
| VIII. Model Routing Per Node | ✅ | No new LLM nodes. |
| IX. Reproducibility & Test Isolation | ✅ | Standardiser is deterministic; tests mock the LLM. |
| X. Research-Question Traceability | ✅ | Standardiser ↔ RQ1 (missing-`$fdisplay` error class) + RQ2. |

**Gate result**: PASS, no amendments. Principle VI is directly served.

## Project Structure

### Documentation (this feature)

```text
specs/005-seq-support/
├── plan.md · spec.md · research.md · data-model.md · quickstart.md
├── contracts/interfaces.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
pipeline/
├── standardiser/fdisplay_inserter.py   # IMPLEMENT insert_fdisplay() + helpers
├── nodes/standardise.py                # IMPLEMENT: call insert_fdisplay, update driver_rtl
├── nodes/merge_generation.py           # NEW: pass-through fan-in barrier node
├── nodes/__init__.py                   # export merge_generation_node
├── nodes/repair.py                     # EDIT after_repair: SEQ → standardise on re-entry
└── graph.py                            # REWIRE: gen_driver/gen_checker → merge_generation
                                        #   → route_after_generation → {standardise|pyverilog_analysis}

prompts/
├── gen_dut.j2                          # REVIEW (SEQ clocking already present)
└── gen_driver.j2                       # REVIEW (SEQ clocking line already present)

tests/
├── fixtures/seq/                       # NEW: dff, counter_4bit, shift_register (_prompt.txt + _ref.v)
├── unit/test_fdisplay_inserter.py      # NEW
└── integration/
    ├── test_seq_routing.py             # NEW: SEQ→standardise, CMB skips; no deadlock
    └── test_seq_live.py                # NEW: @pytest.mark.live, skips without key
```

**Structure Decision**: Add a `merge_generation` join node so the SEQ branch is decided
*after both* driver and checker complete (a deterministic fan-in barrier), avoiding any race
where `pyverilog_analysis` could run before `standardise`. The standardiser is a self-contained
Python module unit-tested in isolation (Principle VI).

## Graph After This Feature

```
gen_scenarios ─┬─► gen_driver ─┐
               └─► gen_checker ─┴─► merge_generation
                                        │ route_after_generation(circuit_type)
                                        ├─ SEQ ─► standardise ─► pyverilog_analysis
                                        └─ CMB ───────────────► pyverilog_analysis
...
repair ─ after_repair ─► { standardise (SEQ) | pyverilog_analysis (CMB) | evaluate (stop) }
```

- `merge_generation`: no-op join; both gen edges point here (barrier), replacing the two
  direct edges into `pyverilog_analysis`.
- `route_after_generation(state)`: `"standardise"` if `circuit_type == "SEQ"` else
  `"pyverilog_analysis"`.
- `standardise → pyverilog_analysis` (existing edge kept).
- `after_repair` extended so a repaired SEQ testbench is re-standardised before re-analysis.

## Complexity Tracking

*No constitution violations.*

Risk: LangGraph fan-in / conditional interaction on the new `merge_generation` barrier and the
repair→standardise re-entry. Mitigation: a mocked routing test asserts SEQ traverses
`standardise` exactly once, CMB never does, and no deadlock occurs.
