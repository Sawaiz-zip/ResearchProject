# Spec 001 — LangGraph Verilog Testbench Generation Pipeline

**Branch:** `phase-1-generation` (merged → `main` on 2026-06-24)
**Status:** ✅ Complete — Phase 1 gate passed

---

## What this spec covers

The full CMB (combinational circuit) testbench generation pipeline:
classify → extract_spec → gen_scenarios → gen_driver ‖ gen_checker → pyverilog_analysis (stub) → error_reasoner (stub) → evaluate (Eval0/1/2).

Phase 2 (Pyverilog implementation) and Phase 3 (repair loop) are tracked in their own spec directories.

---

## Files

| File | Purpose |
|---|---|
| `spec.md` | 5 user stories with acceptance criteria |
| `plan.md` | File-by-file implementation plan |
| `tasks.md` | 59 numbered tasks — Phase 1 tasks T001–T027 all checked ✅ |
| `constitution.md` | 10 engineering rules every node must follow |

---

## Phase 1 Smoke Test Results (2026-06-24)

| Module | Eval0 | Eval1 | Eval2 |
|---|---|---|---|
| half_adder | ✅ | ✅ | 1.00 |
| mux2to1 | ✅ | ✅ | 1.00 |
| alu_1bit | ✅ | ✅ | 1.00 |
| comparator_2bit | ✅ | ✅ | 1.00 |
| priority_encoder | ✅ | ❌ | — |

**Eval0: 5/5 · Eval1: 4/5 · Eval2: 4/4** — Gate PASSED (required ≥ 80% / ≥ 50%)

The `priority_encoder` Eval1 failure is a known LLM hallucination on expected
output values — repair loop (Phase 3) will address this class of error.

---

## Key implementation decisions

- **Multi-provider LLM abstraction** (`pipeline/llm.py`): Anthropic > Groq/compat > OpenAI, selected automatically from `.env`
- **Annotated reducer** on `llm_calls` in `GraphState` so parallel gen_driver + gen_checker branches merge their logs without overwriting
- **Failure detection** in `simulate_tb` uses `r'\bFAIL\s*:'` (not a broad string match) to avoid false positives from LLM debug prints
- **Prompt constraints** added to `gen_scenarios.j2` and `gen_driver.j2` to prevent LLM from generating out-of-range inputs or expecting X/Z from CMB circuits
