<!--
Sync Impact Report (generated 2026-06-14):
- constitution.md: filled from project context in CLAUDE.md (sections 5, 14, 15)
- spec-template.md: no structural changes; mandatory sections align with research project
- Dependent artifacts: all specs/plan/tasks files must comply with the principles below
-->

# S6.ReKI.1 — LangGraph Verilog Testbench Pipeline Constitution

## Core Principles

### I. Graph-First Architecture (NON-NEGOTIABLE)
Every pipeline step is a named LangGraph node. No hidden control flow — routing logic lives exclusively in conditional edges. Sub-graphs are permitted but must be named and documented. Imperative scripts that embed implicit state transitions are prohibited.

### II. Prompt Externalisation
All LLM prompts are Jinja2 templates stored in `prompts/`. Inline f-string prompts are forbidden in source code. Template filenames mirror the node they serve (`classify_circuit.j2`, `generate_driver.j2`, etc.). Variables injected into templates are documented at the top of each template file.

### III. Full LLM Call Logging (NON-NEGOTIABLE)
Every LLM call logs: `{node, model, tokens_in, tokens_out, latency_ms, run_id}`. Logging happens inside a shared wrapper — nodes never call the API directly. This enables per-node failure attribution and cost analysis (RQ4).

### IV. Determinism at Temperature 0
All code-generation and reasoning nodes run at `temperature=0`. Classification nodes also use `temperature=0`. No node may deviate without an explicit, documented justification in the node's docstring.

### V. CMB Before SEQ
Combinational (CMB) circuit support is implemented and validated before any sequential (SEQ) circuit work begins. SEQ work may not be started until the CMB pipeline passes Eval0 + Eval1 on a smoke set of ≥5 modules.

### VI. Deterministic Standardisation Over LLM Standardisation
The `$fdisplay` insertion and clock normalisation steps use Python AST passes only. LLM-based standardisation (as in AutoBench) is explicitly rejected. The standardiser must be independently testable with unit tests.

### VII. Static Analysis Before Simulation
The Pyverilog analysis node runs before Icarus Verilog. Simulation is ground-truth evaluation only, not the primary feedback signal. Verible is a fallback parser — it must never be the primary path.

### VIII. Model Routing Per Node
- **Haiku** (`claude-haiku-4-5`): circuit classification, scenario listing, cheap structural tasks
- **Sonnet** (`claude-sonnet-4-6`): spec extraction, driver generation, checker generation, error reasoning, repair

No node may use a model heavier than Sonnet. Model assignment is declared in the LangGraph node definition, not buried in helpers.

### IX. Reproducibility & Test Isolation
- All randomness is seeded or eliminated
- Each pipeline run gets a unique `run_id` (UUID4)
- Evaluation uses an 80% held-out test split; prompts are frozen before final eval
- `pytest` is the test runner; unit + integration tests live in `tests/`

### X. Research-Question Traceability
Every pipeline node maps to at least one of RQ1–RQ4. New nodes added during development must declare their RQ mapping in a docstring comment. Features that do not serve a research question are deferred.

## Technology Constraints

**Language**: Python 3.11+
**Pipeline orchestration**: LangGraph (explicit nodes + conditional edges)
**LLM API**: Anthropic Claude — `claude-haiku-4-5` for cheap nodes, `claude-sonnet-4-6` for code/reasoning
**Static analysis**: Pyverilog (primary), Verible (fallback)
**Simulator**: Icarus Verilog (`iverilog` / `vvp`) — IEEE 1800-2012
**Dataset**: VerilogEval (156 problems from HDLBits); supervisor dataset if provided later
**Testing**: pytest
**Dependency management**: uv / pyproject.toml

## Development Workflow

1. **Spec first** — write or update `specs/<id>/spec.md` before touching source code
2. **Plan second** — populate `specs/<id>/plan.md` with file layout and phase breakdown
3. **Tasks third** — generate `specs/<id>/tasks.md`; tick items off as work proceeds
4. **CMB smoke gate** — validate on ≥5 combinational modules before scaling to full dataset
5. **Ablation discipline** — each ablation variant (baseline / compiler-only / Pyverilog-only / hybrid) must be runnable with a single config flag, not separate codebases
6. **No speculative features** — implement only what is required by the current spec and research questions

## Governance

This constitution supersedes all other informal decisions. Amendments require: (a) updating this file, (b) bumping the version below, (c) updating any affected specs. All implementation tasks must pass a mental "constitution check" before coding begins. CLAUDE.md sections 5–10 are the authoritative source for research decisions; this constitution governs engineering practice only.

**Version**: 1.0.0 | **Ratified**: 2026-06-14 | **Last Amended**: 2026-06-14
