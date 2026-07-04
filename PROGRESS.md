# Progress Tracker — S6.ReKI.1

> **For future Claude sessions:** Update this file as work progresses. Read `CLAUDE.md` first for full project context.

**Last updated:** 2026-07-04

---

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Setup (Wks 1–2) | ✅ Done | All lit review done; env set up; dataset downloaded; Pyverilog smoke test passed |
| Phase 1 — Generation (Wks 3–6) | ✅ Done | CMB pipeline end-to-end; smoke test PASSED (Eval0 5/5, Eval1 4/5, Eval2 4/4) |
| Phase 2 — Pyverilog (Wks 5–9) | ✅ Done | pyverilog_runner + verible fallback + error_reasoner; 17/17 unit tests pass |
| Feature 003 — DUT-gen + temp + results | ✅ Done | gen_dut node (description→DUT); configurable temperature (Constitution v1.1.0); human-readable run summary; offline test suite 36 pass / 1 live-skip |
| Phase 3 — Repair loop (Wks 10–13) | ✅ Done | repair_node + 3-source feedback (static/compile/sim); 4 ablation modes distinct; oscillation + exhaustion termination. |
| Phase 3b — SEQ support | ✅ Done | Deterministic $monitor/clock standardiser (Python-only, idempotent); merge_generation fan-in barrier; SEQ→standardise routing (CMB skips); dff/counter/shift_register fixtures; 60 tests pass. |
| Phase 4 — Evaluation (Wks 14–16) | ⚪ Not started | |
| Phase 5 — Writing (Wks 17–20) | ⚪ Not started | Exposé already done |

Legend: ✅ done · 🟢 on track · 🟡 partial · 🔴 blocked · ⚪ not started

---

## ✅ Done

### Research & Design
- AutoBench paper (arXiv:2407.03891) read in full and distilled into `CLAUDE.md` § 4
- VerilogEval paper (arXiv:2309.07544) read — benchmark structure understood
- Pyverilog paper read — AST/dataflow/CFG API understood
- Project plan finalized: 5 phases, 20 weeks, ending Sept 1 2026
- Architecture decided: LangGraph + Claude API + Pyverilog + Icarus Verilog
- Pipeline design: 10 nodes wired in LangGraph graph
- 4 research questions formulated; 5 contributions identified
- Exposé (`expose.tex`) written and verified — fits professor's `scrreprt` template
- All 9 references verified correct

### Phase 0 — Setup
- Auto-memory configured: `MEMORY.md`, `user_profile.md`, `project_details.md`
- Full project skeleton (all nodes + prompts) pushed to GitHub
- **Dependencies installed:** langgraph, anthropic, pyverilog 1.3.0, jinja2, pytest, python-dotenv
- **Icarus Verilog 13.0** installed via Homebrew
- **VerilogEval dataset** downloaded → `data/verilog_eval/problems/` (156 problems)
- **Pyverilog smoke test PASSED** on 3 CMB + 1 SEQ module
  - `vast.Ioport` wrapper discovered — handled in `_extract_ports()`
  - Dataflow fails on async reset (`posedge clk or posedge ar`) → catch `FormatError`, AST-only fallback

### Phase 1 — CMB Generation (branch: `phase-1-generation`, merged → `main`)
- classify, extract_spec, gen_scenarios, gen_driver, gen_checker nodes — fully implemented
- icarus.py: `compile_tb` / `simulate_tb` / `eval2` — fully implemented
- mutant_gen.py, evaluate_node, CLI `__main__.py` — fully implemented
- Multi-provider LLM abstraction (Anthropic > Groq/compat > OpenAI)
- 5 CMB fixtures created and verified: alu_1bit, mux2to1, half_adder, comparator_2bit, priority_encoder
- **Smoke test gate PASSED:** Eval0 5/5=100%, Eval1 4/5=80%, Eval2 4/4=100%

### Phase 2 — Pyverilog Static Analysis (branch: `phase-2-pyverilog`)
- `pyverilog_runner.run()` — port-binding mismatch (AST), undriven inputs, unobserved outputs, sensitivity list check, `$fdisplay` presence check
- `verible_runner.run()` — fallback for unparseable LLM-generated Verilog
- `pyverilog_analysis_node` — calls runner + Verible fallback; deterministic, zero LLM calls
- `error_reasoner_node` — calls Sonnet only when report is non-clean; skips LLM (saves tokens) on clean TBs
- **17/17 unit tests pass** (8 pyverilog_runner including 3 SEQ tests, 6 error_taxonomy, 3 config)
- **T107 gate PASSED:** half_adder pipeline → success with Phase 2 active; error_reasoner correctly makes 0 LLM calls on clean TB
- **T108 gate PASSED:** buggy TB with wrong port → 2 PORT_BINDING_MISMATCH errors flagged

---

## 🔄 In Progress

Nothing actively in progress — Features 003, 004 (repair), 005 (SEQ) complete. Remaining: full ablation evaluation (Phase 4).

### Feature 005 — SEQ Support (spec `005-seq-support`)
- **Deterministic standardiser** (`pipeline/standardiser/fdisplay_inserter.py`): Python-only, no LLM. Inserts a `$monitor` covering any unobserved DUT outputs and a clock toggle when a declared clock isn't driven; idempotent via a `// [standardised]` marker; fail-safe (returns input unchanged on any error). Satisfies Constitution Principle VI. `standardise_node` now calls it.
- **Graph**: new `merge_generation` no-op fan-in barrier — `gen_driver`+`gen_checker` → `merge_generation` → conditional `route_after_generation` → `standardise` (SEQ) or `pyverilog_analysis` (CMB). `after_repair` re-routes repaired SEQ testbenches through `standardise`. No LangGraph deadlock (verified by test).
- **Fixtures**: `tests/fixtures/seq/{dff,counter_4bit,shift_register}` (_prompt.txt + _ref.v), all compile under iverilog v13.
- **Tests**: `test_fdisplay_inserter.py` (insertion, idempotency, targeting, no-op, fail-safe, no DUT emit) + `test_seq_routing.py` (SEQ→standardise, CMB skips, no deadlock) — offline. One live SEQ test marked `live`. **60 passed, 3 skipped.** CMB + repair paths unaffected (regression green).

### Feature 004 — Repair Loop (spec `004-repair-loop`)
- **repair_node implemented**: regenerates the testbench from structured error feedback via `repair_driver.j2` (Sonnet), logged as node `repair`. Oscillation detection = same error signature recurring OR regenerated testbench identical to previous. Increments `repair_iter`, appends a `repair_history` entry (iteration, feedback_source, tokens).
- **Three feedback sources**: Pyverilog static errors (via `error_reasoner`), compile failures (Eval0), simulation failures (Eval1). `evaluate_node` now writes `error_report` + `feedback_source` on Eval0/Eval1 failure so repair has context; DUT is treated as reference for Eval1 repairs.
- **Four ablation modes now distinct**: BASELINE never repairs; COMPILER_ONLY on compile fails; PYVERILOG_ONLY on static errors; HYBRID on all. Enforced by `should_repair` (post static) + `should_repair_after_eval` (post eval) + `after_repair` (re-analyse vs stop).
- **Graph rewiring**: `repair → after_repair → {pyverilog_analysis, evaluate}`; `evaluate → should_repair_after_eval → {repair, END}`. Confirmed no LangGraph fan-in deadlock on loop re-entry.
- **Termination**: bounded by `max_repair_iter` (3); `final_status` resolves to `oscillated` / `exhausted_iters` / `success` / specific failure.
- **State**: added `repair_history`, `last_repair_signature`, `feedback_source`. Result JSON + `print_run_summary` show the per-iteration repair breakdown.
- **Tests**: `test_repair_node.py` (signature, oscillation, full mode matrix) + `test_repair_loop.py` (success-within-budget, BASELINE no-repair, oscillation→oscillated, exhaustion→exhausted_iters, COMPILER_ONLY compile-repair, no deadlock) — all offline. One live test marked `live`. **49 passed, 2 skipped.**

### Feature 003 — DUT Generation, Configurable Temperature & Human-Readable Results (spec `003-dut-gen-and-results`)
- **DUT generation**: pipeline now runs from a description alone. New `gen_dut` node (Sonnet) between classify and extract_spec synthesises the DUT; classify uses the description only. Graph: `classify → gen_dut → extract_spec → …`. All downstream nodes (extract_spec, gen_driver, pyverilog_analysis, evaluate, mutant_gen) consume `dut_rtl`.
- **Golden DUT eval-only**: `golden_dut` optional; `evaluate_node` uses it only for Eval0/1/2 when present, else the generated DUT; `eval_dut_source` records which.
- **Configurable temperature**: `llm_call(..., temperature=None)` → `LLM_TEMPERATURE` env → 0.7. Hardcoded `temperature=0` removed. Every call logs its temperature. **Constitution Principle IV amended → v1.1.0.** error_reasoner JSON parse hardened with fallback.
- **Human-readable results**: result JSON now has `nl_description`, `dut_rtl`, `eval_dut_source`, `scenario_results`, `scenarios_passed/total`, `tokens_in/out_total`. New `pipeline/reporting.py` (`parse_scenarios`, `print_run_summary`) prints a summary each run.
- **Tests**: `tests/conftest.py` `fake_llm`/`fake_llm_factory`/`mock_icarus` fixtures → whole suite offline (zero tokens). Full-flow mocked integration test covers CMB/SEQ, golden-vs-generated eval DUT, malformed-output robustness, should_repair routing. Live test marked `live`, auto-skips without a key. **36 passed, 1 skipped.**

---

## ⏭️ Next Session — Start Here

**Phases 0, 1, 2 complete. Active branch: `phase-2-pyverilog`. Begin Phase 3.**

**LLM provider:** Groq free tier — `.env` has `LLM_API_KEY` + `LLM_BASE_URL` set.  
Run any module: `python -m pipeline run --module <name> --mode hybrid`

**Phase 3 — Repair loop (next):**
1. Implement `pipeline/nodes/repair.py` — oscillation check, increment repair_iter, route back to gen_driver with error_report in state
2. Implement `prompts/repair_driver.j2` — already exists as skeleton; review and refine
3. Wire conditional edge in graph: `should_repair()` for all 4 ablation modes
4. Add SEQ fixtures to `tests/fixtures/seq/` (dff, counter_4bit, shift_register)
5. Gate: `tests/integration/test_repair_loop.py` — inject known port error, assert pipeline repairs within 2 iterations

---

## 🚧 Blocked / Waiting

- Nothing — all blockers resolved by supervisor email (2026-05-26)

---

## Notes / Decisions Log

*Append here as decisions are made in future sessions. Format: `YYYY-MM-DD — decision — rationale`.*

- **2026-05-10** — Adopted LangGraph over hand-rolled script — explicit graph + observability for the per-node failure analysis we want as a contribution
- **2026-05-10** — Chose Claude API over GPT-4 — better instruction following + cheaper Haiku tier for classification nodes
- **2026-05-10** — Decided to replace AutoBench's LLM-based `$fdisplay` standardizer with deterministic Python parser — fragile LLM behaviour on a mechanical task; key SEQ contribution
- **2026-05-10** — CMB before SEQ — paper achieved only 26% on SEQ; we de-risk by getting CMB solid first
- **2026-05-20** — **Scope pivot:** project realigned from "RTL error localisation" to "testbench generation + Pyverilog-based early error localisation" to match the official S6.ReKI.1 description from Prof. Wen. Pyverilog localisation stays as the differentiator vs AutoBench; testbench is the artefact being generated.
- **2026-05-20** — Supervisor priority confirmed: **pipeline architecture > raw benchmark accuracy**. Free-tier Claude API is sufficient. Cross-model study deprioritised; cost/budget items dropped from the supervisor email.
- **2026-05-20** — VerilogEval adopted as the default benchmark (public, ships golden RTL + testbenches) so we are not blocked on a supervisor-provided dataset.
- **2026-05-20** — Added Verible as a fallback static-analysis backend in case Pyverilog rejects LLM-generated code; smoke test moved to Phase 0.
- **2026-05-20** — Repair loop gets oscillation detection (break if same error report repeats) and Eval2 (mutant-pass) added to the metrics.
- **2026-05-20** — Writing schedule moved earlier: report skeleton in week 6, complete first draft by end of week 16, Phase 5 is revision only.
- **2026-06-24** — Phase 1 implementation complete and smoke-tested. classify, extract_spec, gen_scenarios, gen_driver, gen_checker nodes implemented; icarus.py (compile_tb/simulate_tb/eval2) working; mutant_gen.py, evaluate_node, CLI __main__.py all implemented; 5 CMB fixtures created (alu_1bit, mux2to1, half_adder, comparator_2bit, priority_encoder), all compile with iverilog; graph builds with all 10 nodes. Smoke set results: Eval0 5/5=100%, Eval1 4/5=80% (priority_encoder fails — LLM hallucinated expected pos==2 for in=8 but correct is pos==3; repair loop will address), Eval2 4/4=100% on passing modules. Phase 1 gate PASSED.
- **2026-06-24** — Switched from Anthropic API to Groq free tier (Llama-3.3-70b-versatile via OpenAI-compat endpoint). Added multi-provider LLM abstraction in llm.py: Anthropic > compat (LLM_API_KEY+LLM_BASE_URL) > OpenAI. Haiku/Sonnet names map to cheap/strong Groq models via env vars LLM_CHEAP_MODEL and LLM_STRONG_MODEL.
- **2026-06-24** — Phase 2 complete: pyverilog_runner.run() implements port-binding mismatch detection (AST), undriven-input + unobserved-output heuristics (comparison/if/display pattern matching), sensitivity-list check for SEQ circuits, $fdisplay presence check for SEQ. Verible fallback added. error_reasoner_node skips LLM when report is clean (saves tokens). 17/17 unit tests pass. T107 gate: half_adder pipeline still success with Phase 2 active; error_reasoner correctly makes zero LLM calls on clean TB.
- **2026-06-24** — Fixed two gen_driver/gen_scenarios prompt bugs discovered during smoke test: (1) LLM generating "invalid" inputs (a=2 on 1-bit signal) expecting 'bx outputs — added STRICT RULES to gen_scenarios.j2 and requirements to gen_driver.j2 prohibiting out-of-range values; (2) simulate_tb matched "FAIL" too broadly (caught "failed" in debug prints) — tightened regex to r'\bFAIL\s*:' to only catch deliberate PASS/FAIL markers.
- **2026-05-26** — Supervisor email reply received from Shengchao (cc: Jiajun Wu, Wen Bing). All open questions resolved:
  - ✅ Pyverilog static analysis approach confirmed as correct
  - ✅ VerilogEval confirmed as sufficient dataset
  - ✅ Golden models from VerilogEval confirmed for evaluation
  - ✅ Follow AutoBench metrics (Eval0/1/2)
  - ✅ Meeting cadence: monthly; no May meeting; June slot via poll
  - ✅ Progress sharing: Google Doc + GitHub repo (supervisors will leave comments)
  - ✅ Office hours: Wednesday 17:00–18:00 for ad-hoc questions
  - ✅ Phase 1 implementation can begin immediately — no blockers remain
