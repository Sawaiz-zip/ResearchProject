# Progress Tracker — S6.ReKI.1

> **For future Claude sessions:** Update this file as work progresses. Read `CLAUDE.md` first for full project context.

**Last updated:** 2026-06-24

---

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Setup (Wks 1–2) | ✅ Done | All lit review done; env set up; dataset downloaded; Pyverilog smoke test passed |
| Phase 1 — Generation (Wks 3–6) | ✅ Done | CMB pipeline end-to-end; smoke test PASSED (Eval0 5/5, Eval1 4/5, Eval2 4/4) |
| Phase 2 — Pyverilog (Wks 5–9) | ⚪ Not started | |
| Phase 3 — Repair + SEQ (Wks 10–13) | ⚪ Not started | |
| Phase 4 — Evaluation (Wks 14–16) | ⚪ Not started | |
| Phase 5 — Writing (Wks 17–20) | ⚪ Not started | Exposé already done |

Legend: ✅ done · 🟢 on track · 🟡 partial · 🔴 blocked · ⚪ not started

---

## ✅ Done

- AutoBench paper (arXiv:2407.03891) read in full and distilled into `CLAUDE.md` § 4
- VerilogEval paper (arXiv:2309.07544) read — benchmark structure understood
- Pyverilog paper read — AST/dataflow/CFG API understood
- Project plan finalized: 5 phases, 20 weeks, ending Sept 1 2026
- Architecture decided: LangGraph + Claude API + Pyverilog + Icarus Verilog
- Pipeline design: 10 nodes wired in LangGraph graph
- 4 research questions formulated; 5 contributions identified
- Exposé (`expose.tex`) written and verified — fits professor's `scrreprt` template
- All 9 references verified correct
- Auto-memory configured: `MEMORY.md`, `user_profile.md`, `project_details.md`
- Full project skeleton (81 files, all nodes + prompts) pushed to GitHub
- **Dependencies installed:** langgraph 1.2.4, anthropic 0.111, langchain-anthropic 1.4.7, pyverilog 1.3.0, jinja2 3.1.3, pytest 9.1.1, python-dotenv 1.2.2
- **Icarus Verilog 13.0** installed via Homebrew
- **VerilogEval dataset** downloaded → `data/verilog_eval/problems/` (156 problems, each with `_prompt.txt`, `_ref.sv`, `_test.sv`)
- **Pyverilog smoke test PASSED** on 3 CMB modules (notgate, vector2, m2014_q4i) + 1 SEQ module
  - Key finding: Verilog-2001 port style uses `vast.Ioport` wrapper — handled in `pyverilog_runner.py` notes
  - Key finding: dataflow fails on `always @(posedge clk or posedge ar)` (async reset) → catch `FormatError`, degrade to AST-only
  - Key finding: dataflow works on `always @(posedge clk)` with synchronous reset
  - Verible fallback still planned for Phase 2 when even AST fails

---

## 🔄 In Progress

- **Supervisor email drafted** (`supervisor_email.md`) — pending send + reply on scope confirmation, dataset, golden RTL, meeting cadence
- **Exposé revised** for the new testbench-generation scope (title, motivation, RQs, methods, metrics, timeline)
- **CLAUDE.md updated** — new §6 pipeline (6 stages), §7 GraphState with TB fields, §8 RQs, §9 contributions, §10 metrics, §16 open questions
- Plan file at `~/.claude/plans/i-want-you-to-rosy-frost.md` captures the full improvement roadmap

---

## ⏭️ Next Session — Start Here

**Phase 1 is complete and smoke-tested. Begin Phase 2.**

**LLM provider:** Groq free tier via OpenAI-compat API — `.env` has `LLM_API_KEY` + `LLM_BASE_URL` set.  
Run any module with: `python -m pipeline run --module <name> --mode hybrid`

**Phase 2 — Pyverilog static analysis layer (next):**
1. Implement `pipeline/analysis/pyverilog_runner.py` — see detailed 8-step TODO + smoke-test findings already in that file
2. Implement `pipeline/nodes/pyverilog_analysis.py` — call pyverilog_runner.run(), set pyverilog_report in state
3. Implement `pipeline/nodes/error_reasoner.py` — render error_reasoner.j2, call Sonnet, parse error list into error_report
4. Hand-label 20 circuits to measure Pyverilog error precision/recall
5. Gate: `pytest tests/unit/test_pyverilog_runner.py` passes with buggy hand-crafted TB producing non-empty error_report

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
