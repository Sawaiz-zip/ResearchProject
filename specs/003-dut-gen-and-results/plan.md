# Implementation Plan: DUT Generation, Configurable Temperature & Human-Readable Results

**Branch**: `phase-2-pyverilog` (working branch; no dedicated feature branch) | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-dut-gen-and-results/spec.md`

## Summary

Four coordinated changes to the existing LangGraph testbench pipeline:

1. **DUT generation** — the pipeline no longer requires a golden DUT as input. A new `gen_dut` node (Sonnet) sits between `classify` and `extract_spec` and produces the DUT from the description + circuit type. Everything downstream consumes the generated DUT.
2. **Classify from description only** — drop `golden_dut` from `classify_circuit.j2` and the classify node call.
3. **Configurable temperature** — `llm_call()` gains a `temperature` parameter defaulting to `LLM_TEMPERATURE` env (0.7); the hardcoded `temperature=0` is removed. Robustness comes from tolerant JSON parsing + retry, not deterministic decoding. **This amends Constitution Principle IV.**
4. **Human-readable results** — persist `nl_description`, generated DUT, eval-DUT source, and structured per-scenario outcomes; print a console summary each run.

Plus a test strategy: mock `llm_call` for offline coverage of every node/branch; a few marked live-API integration tests that skip without a key.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: LangGraph, Anthropic / OpenAI-compat SDKs (Groq free tier in use), Pyverilog, Jinja2, pytest, python-dotenv
**Storage**: JSON result files under `results/<run_id>.json`
**Testing**: pytest (`tests/unit`, `tests/integration`); mocking via `unittest.mock` / `monkeypatch`
**Target Platform**: Local CLI (macOS/Linux); `python -m pipeline run ...`
**Project Type**: Single-project research pipeline (graph-based state machine)
**Performance Goals**: Not latency-critical; primary constraint is minimising LLM tokens (free tier)
**Constraints**: Free-tier API budget — tests must not spend tokens by default; iverilog stays at v13
**Scale/Scope**: 156 VerilogEval modules + local fixtures; single-module runs

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.0.0.*

| Principle | Status | Note |
|---|---|---|
| I. Graph-First Architecture | ✅ Pass | `gen_dut` is a named node with an explicit edge `classify → gen_dut → extract_spec`. No hidden control flow. |
| II. Prompt Externalisation | ✅ Pass | New `prompts/gen_dut.j2`; `classify_circuit.j2` edited. No inline prompts. |
| III. Full LLM Call Logging | ✅ Pass | `gen_dut` logs via shared `llm_call`; log entry now also carries `temperature`. |
| **IV. Determinism at Temperature 0** | ⚠️ **Amended** | This feature **deliberately relaxes** Principle IV to a configurable temperature (default 0.7). See Complexity Tracking + constitution amendment task. |
| V. CMB Before SEQ | ✅ Pass | No SEQ-specific work here; CMB path remains primary. `gen_dut` works for both types. |
| VI. Deterministic Standardisation | ✅ Pass | Untouched. |
| VII. Static Analysis Before Simulation | ✅ Pass | Order unchanged; static analysis now targets the generated DUT. |
| VIII. Model Routing Per Node | ✅ Pass | `gen_dut` = Sonnet (code generation), consistent with driver/checker. |
| IX. Reproducibility & Test Isolation | ⚠️ Watch | Non-zero default temperature reduces run-to-run determinism. Mitigation: tests mock the LLM (deterministic); `run_id` still unique; temperature recorded per call for auditability. |
| X. Research-Question Traceability | ✅ Pass | `gen_dut` docstring maps to RQ1/RQ3. |

**Gate result**: PASS with one explicit, documented amendment (Principle IV). The amendment is a first-class task, not a silent deviation — satisfying the governance clause.

## Project Structure

### Documentation (this feature)

```text
specs/003-dut-gen-and-results/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 — decisions & rationale
├── data-model.md        # Phase 1 — state/result schema changes
├── quickstart.md        # Phase 1 — how to run & validate
├── contracts/
│   └── interfaces.md     # llm_call signature, result JSON schema, gen_dut node contract
├── checklists/
│   └── requirements.md   # Spec quality checklist (done)
└── tasks.md             # Phase 2 — created by /speckit-tasks (NOT here)
```

### Source Code (repository root)

```text
pipeline/
├── llm.py                       # EDIT: temperature param + LLM_TEMPERATURE env; log temperature
├── config.py                    # EDIT: add default_temperature field (reads env)
├── state.py                     # EDIT: add dut_rtl, eval_dut_source, scenario_results; golden_dut optional
├── graph.py                     # EDIT: insert gen_dut node + edges classify→gen_dut→extract_spec
├── __main__.py                  # EDIT: golden_dut optional; call print_run_summary(); init new state keys
├── nodes/
│   ├── classify.py              # EDIT: drop golden_dut from prompt render
│   ├── gen_dut.py               # NEW: Sonnet node, generates dut_rtl from description + circuit_type
│   ├── extract_spec.py          # EDIT: consume dut_rtl (fallback to golden_dut) instead of golden_dut
│   └── evaluate.py              # EDIT: eval DUT selection, scenario parsing, nl_description + totals in result
├── analysis/
│   └── pyverilog_runner.py      # EDIT (caller): analysis node passes dut_rtl; runner unchanged if signature ok
├── nodes/pyverilog_analysis.py  # EDIT: pass dut_rtl (fallback golden_dut) to runner
└── reporting.py                 # NEW: print_run_summary() + parse_scenarios() helpers

prompts/
├── gen_dut.j2                   # NEW: description + circuit_type → Verilog DUT
└── classify_circuit.j2          # EDIT: remove golden_dut variable

tests/
├── conftest.py                  # NEW: shared fake_llm fixture + monkeypatch of llm_call
├── unit/
│   ├── test_gen_dut.py          # NEW: node writes dut_rtl (mocked llm)
│   ├── test_llm_temperature.py  # NEW: temperature param + env default + logged
│   ├── test_reporting.py        # NEW: parse_scenarios + summary rendering (no llm)
│   └── test_evaluate_result.py  # NEW: result JSON has nl_description, scenario_results, totals, eval_dut_source
├── integration/
│   ├── test_pipeline_flow_mocked.py  # NEW: full graph, mocked llm — CMB & SEQ, repair/evaluate, golden-vs-generated
│   └── test_live_api.py         # NEW: @pytest.mark.live — 1–2 real runs, skip if no key
└── fixtures/…                   # existing CMB fixtures reused

.specify/memory/constitution.md  # EDIT: amend Principle IV, bump version → 1.1.0
```

**Structure Decision**: Single-project layout (already established). Changes are surgical edits to existing modules plus two new files (`nodes/gen_dut.py`, `reporting.py`) and one new prompt. A shared `conftest.py` centralises LLM mocking so the entire default suite stays offline.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Amends Constitution Principle IV (temperature=0 → configurable, default 0.7) | Research goal: the pipeline must be model-agnostic and robust at temperature>0, not dependent on deterministic decoding. Supervisor priority is a robust pipeline. | Keeping temperature=0 rejected because it makes robustness untestable and ties the pipeline to a single decoding regime; the whole point is to prove the repair/parsing loop survives stochastic output. Mitigations: tests mock the LLM (deterministic), temperature is recorded per call, and default is overridable via env. |