# Progress Tracker — S6.ReKI.1

> **For future Claude sessions:** Update this file as work progresses. Read `CLAUDE.md` first for full project context.

**Last updated:** 2026-05-20

---

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Setup (Wks 1–2) | 🟡 Partial | Lit review started (AutoBench done); env not yet set up; dataset pending |
| Phase 1 — Generation (Wks 3–6) | ⚪ Not started | |
| Phase 2 — Pyverilog (Wks 5–9) | ⚪ Not started | |
| Phase 3 — Repair + SEQ (Wks 10–13) | ⚪ Not started | |
| Phase 4 — Evaluation (Wks 14–16) | ⚪ Not started | |
| Phase 5 — Writing (Wks 17–20) | ⚪ Not started | Exposé already done |

Legend: ✅ done · 🟢 on track · 🟡 partial · 🔴 blocked · ⚪ not started

---

## ✅ Done

- AutoBench paper (arXiv:2407.03891) read in full and distilled into `CLAUDE.md` § 4
- Project plan finalized: 5 phases, 20 weeks, ending Sept 1 2026
- Architecture decided: LangGraph + Claude API + Pyverilog + Icarus Verilog
- Pipeline design: 5 nodes (LLM gen → Pyverilog → LLM reason → repair → Icarus eval)
- 4 research questions formulated
- 5 contributions identified
- Exposé (`expose.tex`) written and verified — fits professor's `scrreprt` template
- All 9 references verified correct
- Auto-memory configured: `MEMORY.md`, `user_profile.md`, `project_details.md`
- Terminal/statusline configured (Starship + zsh plugins)

---

## 🔄 In Progress

- **Supervisor email drafted** (`supervisor_email.md`) — pending send + reply on scope confirmation, dataset, golden RTL, meeting cadence
- **Exposé revised** for the new testbench-generation scope (title, motivation, RQs, methods, metrics, timeline)
- **CLAUDE.md updated** — new §6 pipeline (6 stages), §7 GraphState with TB fields, §8 RQs, §9 contributions, §10 metrics, §16 open questions
- Plan file at `~/.claude/plans/i-want-you-to-rosy-frost.md` captures the full improvement roadmap

---

## ⏭️ Next Session — Start Here

Tackle in order:

1. **Send supervisor email** (`supervisor_email.md`) and await scope confirmation before committing to Phase 1 work
   - Scope, dataset, golden RTL/testbench source, meeting cadence
   - Budget/models/compute/submission/page-count intentionally omitted (supervisor already said pipeline > accuracy, free tier)

2. **Initialize Python project structure**
   ```
   ResearchProject/
   ├── pyproject.toml
   ├── src/
   │   ├── graph/        # LangGraph nodes + state
   │   ├── tools/        # iverilog wrapper, pyverilog wrapper
   │   └── prompts/      # Jinja templates per node
   ├── tests/
   ├── data/             # dataset goes here
   └── notebooks/        # exploratory analysis
   ```

3. **Install dependencies** (only after structure exists)
   ```bash
   pip install langgraph anthropic pyverilog jinja2 pytest
   brew install icarus-verilog  # if not already installed
   ```

4. **Smoke-test Pyverilog on 2–3 example modules** to confirm it parses LLM-style output cleanly — this is the highest-risk dependency

5. **Read 2 more papers** before coding:
   - Liu 2023 VerilogEval (arXiv:2309.07544) — for benchmark structure
   - Takamaeda 2015 Pyverilog — for API surface

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
- **2026-05-26** — Supervisor email reply received from Shengchao (cc: Jiajun Wu, Wen Bing). All open questions resolved:
  - ✅ Pyverilog static analysis approach confirmed as correct
  - ✅ VerilogEval confirmed as sufficient dataset
  - ✅ Golden models from VerilogEval confirmed for evaluation
  - ✅ Follow AutoBench metrics (Eval0/1/2)
  - ✅ Meeting cadence: monthly; no May meeting; June slot via poll
  - ✅ Progress sharing: Google Doc + GitHub repo (supervisors will leave comments)
  - ✅ Office hours: Wednesday 17:00–18:00 for ad-hoc questions
  - ✅ Phase 1 implementation can begin immediately — no blockers remain
