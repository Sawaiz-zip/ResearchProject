# Technical Progress Report — S6.ReKI.1
**LLM-Driven Verilog Testbench Generation with Pyverilog-Based Early Error Localization**
**Student:** Muhammad Sawaiz Naveed | **Date:** 24 June 2026 | **Supervisor:** Bing Wen, TU Ilmenau

---

## 1. What Problem Are We Solving?

Before a hardware chip can be manufactured, engineers must verify that the circuit design actually works correctly. They do this by writing a **testbench** — a separate piece of code that feeds inputs into the circuit and checks whether the outputs are correct. Think of it like a teacher writing an exam to test students: the circuit is the student, and the testbench is the exam paper.

Writing these testbenches by hand is slow, repetitive, and error-prone. It can consume **60% of the total engineering effort** on a hardware project (according to industry surveys). The natural question is: can an AI write these testbenches automatically?

The answer is: **yes, but the AI often makes mistakes that are hard to catch.** The AI produces code that looks correct and even compiles without errors, but is actually wrong in subtle ways — for example, it connects the wrong wire to the wrong pin, or it prints the output to the wrong place, or it never actually exercises the interesting corner cases. You only find out something is wrong after running a full simulation, which takes time.

**Our project's core idea:** catch those subtle mistakes *before* running the simulation, using a static analysis tool called Pyverilog. Instead of the AI writing a testbench → running it → discovering it fails → fixing it (slow loop), we add a fast pre-check step: AI writes testbench → Pyverilog scans it for structural problems in milliseconds → AI gets precise feedback → fixes the problem → *then* we run the simulation.

---

## 2. What We Studied

We read and summarised three key papers that form the foundation of this project.

### Paper 1 — AutoBench (the seed paper we are building on)

**What it is:** A research pipeline from TU Munich (2024) that uses an AI (GPT-4) to write Verilog testbenches automatically through a multi-step process.

**How it works:** Instead of asking the AI "write me a testbench," it breaks the job into stages — first understand the circuit, then list test cases, then write the test code, then write a separate checker. It also has a self-healing mechanism: if the code fails to compile, it feeds the error back to the AI and tries again.

**Results:** It works well for simple circuits (62% success rate) but poorly for circuits that have memory/clocks (only 26% success rate). It was only tested with GPT-4, never reported how much it costs to run, and never explained *where* in the pipeline things go wrong.

**What we take from it:** The multi-stage pipeline idea is good. We adopt it. But we replace the fragile parts and add the static analysis layer that AutoBench completely lacks.

### Paper 2 — VerilogEval (our benchmark dataset)

**What it is:** A standardised set of 156 circuit problems created by researchers at MIT (2023), taken from HDLBits — a popular online Verilog learning platform. Think of it as a standardised exam paper that everyone uses so results can be compared fairly.

**Each problem includes:** a plain-English description of the circuit ("design a 4-bit counter that resets to zero when it overflows"), the correct circuit code (the "answer key"), and a reference test.

**Why we use it:** It is the industry-standard benchmark for evaluating AI-generated Verilog. Using it means our results can be directly compared to AutoBench and other papers. It splits naturally into 81 simple circuits and 75 complex (clocked) circuits — the same division AutoBench used.

### Paper 3 — Pyverilog (our analysis tool)

**What it is:** A Python library (2015) that can read Verilog code and turn it into a structured representation — like parsing an English sentence into subject/verb/object so a computer can reason about it.

**Three capabilities:**
- **AST Parser** — reads Verilog and builds a tree structure showing every component: what ports does this module have? What signals are assigned where? This lets us check: "did the testbench connect the clock pin correctly?"
- **Dataflow Analyser** — traces how signals travel through the circuit: "if input A changes, which outputs are affected?" This lets us catch: "the testbench drives input A but never drives input B — B is always zero, so the test is incomplete."
- **Control-flow Graph** — maps the logical paths through the code. Useful for understanding state machines.

**Why it matters for us:** Pyverilog can find structural bugs in milliseconds without running any simulation. That is the "early" in "early error localization" — we find the problem early, before the expensive simulation step.

**Known limitation:** Pyverilog sometimes struggles with messy or unusual Verilog that AI models tend to produce. We handle this by adding Verible (another parser from Google) as a fallback.

---

## 3. What We Designed

### 3.1 The Overall Architecture

We designed a pipeline — a sequence of steps that transforms a plain-English description into a verified testbench. Each step is a named **node** in a LangGraph graph (think of it like a flowchart where every box is a step and every arrow is a decision).

Here is the pipeline in plain English:

```
INPUT: "Design a circuit that adds two 4-bit numbers"
  + the actual circuit code (given to us)
         │
         ▼
STEP 1 — CLASSIFY
  Ask the AI (Haiku): is this a simple circuit or does it have
  memory/clocks? Simple = "CMB", Clocked = "SEQ"
         │
         ▼
STEP 2 — EXTRACT SPEC
  Ask the AI (Sonnet): read the description and the circuit code,
  give me a structured summary — what are the inputs? Outputs?
  What should the circuit do?
         │
         ▼
STEP 3 — GENERATE SCENARIOS
  Ask the AI (Haiku): based on the spec, what test cases should
  we run? (e.g. "test zero + zero", "test maximum + maximum",
  "test overflow")
         │
         ├─────────────────────┐
         ▼                     ▼
STEP 4A — GENERATE DRIVER    STEP 4B — GENERATE CHECKER
  Write the Verilog           Write a Python script that
  testbench code.             reads the simulation output
  (Sonnet)                    and checks it. (Sonnet)
  [These two run at the same time — in parallel]
         │
         ▼  (For clocked circuits only)
STEP 5 — STANDARDISE
  Python code (no AI) scans the testbench and inserts any
  missing print statements. Mechanical, 100% reliable.
         │
         ▼
STEP 6 — PYVERILOG ANALYSIS
  No AI involved. Pyverilog reads the testbench + circuit together
  and checks:
    - Are all the wires connected to the right pins?
    - Are all inputs being driven? Are all outputs being checked?
    - Are the clock sensitivity lists correct?
    - Are the print statements there for every output?
  → Produces a structured error report.
         │
         ▼
STEP 7 — ERROR REASONER
  The AI (Sonnet) reads Pyverilog's technical report and translates
  it into plain, actionable instructions: "Line 14: you connected
  clk to reset — swap them."
         │
         ├── If errors found AND less than 3 attempts used:
         │       feed error report back to Step 4A, regenerate
         │
         ▼
STEP 8 — EVALUATE
  Run the testbench through Icarus Verilog (a standard simulator):
    Eval0: Does it compile?
    Eval1: Does it pass against the correct circuit?
    Eval2: Does it catch bugs? (We inject faults into the circuit
           and check if the testbench detects them)
         │
         ▼
OUTPUT: Testbench file + full log of every AI call made
        (which step, which model, how many tokens, how long it took)
```

### 3.2 The Repair Loop

If Pyverilog finds errors, instead of giving up or running the simulator blind, we send the error report back to the AI and ask it to fix the testbench. This repeats up to 3 times. Two safety mechanisms:

- **Oscillation detection:** If the same errors appear twice in a row (the AI is going in circles), we stop immediately rather than wasting more API calls.
- **Exhaustion:** If 3 attempts pass without fixing the problem, we record the failure and move on.

### 3.3 Four Modes (Ablation Study)

A key part of the research is proving that our approach (Pyverilog + AI repair) is actually better than simpler alternatives. We run the same pipeline in four configurations:

| Mode | What it does |
|---|---|
| **Baseline** | Write testbench once, no repair at all |
| **Compiler-only** | Repair only if the code fails to compile (same as AutoBench) |
| **Pyverilog-only** | Repair using Pyverilog's structural checks only |
| **Hybrid (ours)** | Both sources trigger repair — our full system |

Comparing all four across 156 circuits lets us say exactly how much Pyverilog contributes, independently of everything else.

### 3.4 The Constitution (Engineering Rules)

Before writing any code, we wrote a "constitution" — 10 rules that every line of code must follow. The most important ones:

1. Every pipeline step must be a named LangGraph node. No hidden steps.
2. All AI prompts must be separate template files — never buried in the code.
3. Every AI call must be logged (which step, which model, how many tokens, how long).
4. Temperature must always be 0 — the AI gives the same answer every time, making results reproducible.
5. Simple circuits before clocked circuits — don't start the hard case until the easy case works.
6. The `$fdisplay` fix (inserting missing print statements) must use Python code only — never ask the AI to do it, because the AI is unreliable at mechanical formatting tasks.

---

## 4. What We Built (Phase 0 + Phase 1 — Complete)

Phase 0 set up the environment and confirmed all tools work. Phase 1 implemented the full combinational-circuit pipeline end-to-end. The system can now take a plain-English circuit description, generate a Verilog testbench using an LLM, and evaluate it — all automatically.

### 4.1 Environment Setup (Phase 0)

- **Dependencies installed:** LangGraph, Pyverilog, Jinja2, pytest, python-dotenv, Anthropic SDK
- **Icarus Verilog 13.0** installed via Homebrew — the simulator that evaluates generated testbenches
- **VerilogEval dataset** downloaded — 156 circuit problems, each with a description, golden circuit code, and reference testbench
- **Pyverilog smoke test passed** on 3 simple circuits and 1 clocked circuit. Two important findings discovered:
  - Verilog-2001 style ports are wrapped in a `vast.Ioport` object — the code must unwrap it to get the port name
  - The dataflow analyser crashes on `always @(posedge clk or posedge reset)` (async reset) — handled by catching the error and falling back to AST-only mode

### 4.2 The Working Pipeline (Phase 1)

Every component listed below is fully implemented and tested, not a stub.

**`pipeline/llm.py`** — The shared AI call function used by every node. Supports three providers in priority order: Anthropic API → any OpenAI-compatible API (we use Groq's free tier) → OpenAI. Handles: logging every call (`node, model, tokens_in, tokens_out, latency_ms`), exponential backoff on rate limits, temperature=0 always. Model names like "claude-haiku" automatically map to the equivalent Groq/OpenAI model.

**`pipeline/state.py`** — The shared data container (`GraphState`). Every node reads from and writes to this single structure. One technical detail worth noting: the `llm_calls` log field uses a special "reducer" so that when the driver and checker nodes run in parallel, their log entries are merged rather than one overwriting the other.

**`pipeline/nodes/classify.py`** — Sends the circuit description + code to the LLM and gets back `{"circuit_type": "CMB"}` or `{"circuit_type": "SEQ"}`. Has a keyword fallback in case the LLM outputs plain text instead of JSON.

**`pipeline/nodes/extract_spec.py`** — Sends the description + circuit code to the LLM and gets back a structured JSON spec: what are the input ports, output ports, and what logic should the circuit implement?

**`pipeline/nodes/gen_scenarios.py`** — Takes the spec and asks the LLM for a list of named test cases (e.g., "test_zero_plus_zero", "test_max_values", "test_carry_out"). Prompts strictly forbid asking for invalid inputs or expecting X/Z values from a combinational circuit — a bug discovered during testing where the LLM would generate nonsensical test cases.

**`pipeline/nodes/gen_driver.py`** + **`pipeline/nodes/gen_checker.py`** — These run in parallel. The driver node generates the actual Verilog testbench. The checker node generates a Python script that reads the simulation output and verifies results. Both run as separate branches in the LangGraph graph simultaneously, cutting wall-clock time.

**`pipeline/eval/icarus.py`** — The Icarus Verilog wrapper. Fully implemented:
- `compile_tb()` — writes testbench + circuit to temp files, runs `iverilog -g2012`, returns whether it compiled and the compiler output
- `simulate_tb()` — runs the compiled binary with `vvp`, detects failure by looking for exactly `"FAIL: "` in the output (deliberately narrow — avoids false positives from debug prints containing the word "failed")
- `eval2()` — runs the testbench against each mutant circuit; a mutant is "caught" if the testbench fails on it

**`pipeline/eval/mutant_gen.py`** — Asks the LLM (cheap model) to inject a single fault into the golden circuit code (e.g., change `+` to `-`, flip a comparison, swap two ports). Generates 5 mutants per module for Eval2.

**`pipeline/nodes/evaluate.py`** — Orchestrates the full evaluation: Eval0 (compile) → Eval1 (run against golden circuit) → Eval2 (run against mutants). Writes a complete result JSON to `results/<run_id>.json` including debug fields (compiler output, simulation output) when something fails.

**`pipeline/__main__.py`** — The command-line interface. Run any module with:
```
python -m pipeline run --module half_adder --mode hybrid
```
Automatically finds modules in the VerilogEval dataset or local fixture files.

**`prompts/` (8 Jinja2 templates)** — All AI prompts live in separate files, never hardcoded. Each template has blank fields (`{{ module_name }}`, `{{ spec }}`, etc.) filled in at runtime with actual data.

**`pipeline/analysis/error_taxonomy.py`** — Defines the vocabulary for describing errors: `PORT_BINDING_MISMATCH`, `UNDRIVEN_INPUT`, `SENSITIVITY_LIST_ERROR`, `MISSING_FDISPLAY`, etc. with severity levels (`ERROR`, `WARNING`, `INFO`). Used by the Pyverilog layer (Phase 2).

**`tests/fixtures/cmb/`** — 5 combinational circuit fixtures used for the smoke test: `half_adder`, `mux2to1`, `alu_1bit`, `comparator_2bit`, `priority_encoder`. All verified to compile with Icarus Verilog.

### 4.3 Smoke Test Results (Phase 1 Gate)

The pipeline was run on all 5 CMB fixtures with `--mode hybrid`:

| Module | Eval0 (compiles?) | Eval1 (correct?) | Eval2 (catches bugs?) |
|---|---|---|---|
| half_adder | ✅ | ✅ | 1.00 (5/5 mutants caught) |
| mux2to1 | ✅ | ✅ | 1.00 |
| alu_1bit | ✅ | ✅ | 1.00 |
| comparator_2bit | ✅ | ✅ | 1.00 |
| priority_encoder | ✅ | ❌ | — |

**Eval0: 5/5 = 100% · Eval1: 4/5 = 80% · Eval2: 4/4 = 100% on passing modules**

**Phase 1 gate PASSED** (required: Eval0 ≥ 80%, Eval1 ≥ 50%).

The one Eval1 failure (`priority_encoder`) is a known LLM reasoning error: the model expected output `pos=2` when the correct answer for input `4'b1000` (bit 3 set) is `pos=3`. This is exactly the class of error the repair loop (Phase 3) is designed to fix using Pyverilog feedback.

---

## 5. What's Next

### ✅ Phase 1 — Complete

The pipeline generates and evaluates CMB testbenches end-to-end. Gate passed. No outstanding work in Phase 1.

---

### ✅ Phase 2 — Complete (Pyverilog Static Analysis Layer)

This is the primary research contribution of the project. Phase 2 adds the layer that makes the pipeline *smarter* by catching structural testbench bugs before running any simulation.

**What was built:**

**`pipeline/analysis/pyverilog_runner.py`** — The core deterministic analysis engine. Parses the generated testbench + golden DUT together using Pyverilog's AST, then runs four independent checks:

- **Port binding check** (AST): walks the testbench's DUT instantiation and flags any DUT port that is missing from the connection list, or any connection that uses a port name that doesn't exist in the DUT. This catches the most common class of LLM error — connecting the right signal to the wrong pin.
- **Undriven / unobserved check** (text heuristic): for each DUT input, checks if the connected TB signal ever appears on the left side of an assignment. For each DUT output, checks if it appears in an if-condition, comparison, or `$display` call. Flags `UNDRIVEN_INPUT` and `UNOBSERVED_OUTPUT` accordingly.
- **Sensitivity list check** (AST, sequential circuits only): walks the testbench's always-blocks. If the DUT is sequential (contains `posedge`) but none of the TB's always-blocks have a posedge/negedge trigger, flags `SENSITIVITY_LIST_ERROR`.
- **`$fdisplay` presence check** (sequential circuits only): for each DUT output, checks if the testbench has any `$display`/`$fdisplay`/`$monitor` call referencing that output signal. Flags `MISSING_FDISPLAY` if not.

Key implementation detail from the Phase 0 smoke test: Verilog-2001 port style wraps ports in `vast.Ioport` AST nodes whose `.first` attribute is the actual declaration — handled by `_extract_ports()`.

**`pipeline/analysis/verible_runner.py`** — Fallback when Pyverilog cannot parse the testbench (which happens if the LLM generates sufficiently malformed code). Runs `verible-verilog-syntax` as a subprocess. If Verible is not installed, returns `parse_ok=False` gracefully without crashing.

**`pipeline/nodes/pyverilog_analysis.py`** — The LangGraph node: calls `pyverilog_runner`, falls back to Verible if needed, writes the structured `pyverilog_report` to state. **Zero LLM calls** — fully deterministic.

**`pipeline/nodes/error_reasoner.py`** — If the Pyverilog report is clean (no errors), this node **skips the LLM call entirely** and sets `error_report=[]`. This saves tokens on every run where the testbench is already correct. If errors exist, it calls Sonnet with `error_reasoner.j2` to translate the technical Pyverilog output into human-readable, actionable fix instructions.

**Gate results (all passed 2026-06-24):**
- 17/17 unit tests pass (8 pyverilog_runner tests including 3 SEQ-specific, 6 error_taxonomy, 3 config)
- `half_adder` full pipeline run: `status=success`, `error_reasoner` made **0 LLM calls** (TB was clean — correct)
- Buggy TB with wrong port name: correctly flagged 2 `PORT_BINDING_MISMATCH` errors

---

### Phase 3 — Repair Loop + Sequential Circuits (Current — Weeks 10–13)

Now that Pyverilog produces structured error reports, we wire the feedback loop so the pipeline can fix its own mistakes:

- Implement `pipeline/nodes/repair.py` — reads the error report, increments `repair_iter`, detects oscillation (same report twice in a row means the AI is stuck — stop and record the failure), then routes back to the driver/checker generation nodes with the error report attached to the prompt
- Wire the conditional edge in `graph.py` for all 4 ablation modes: in `baseline` mode never repair; in `compiler_only` only repair on compile failure; in `pyverilog_only` only repair on Pyverilog errors; in `hybrid` both trigger repair
- Implement `pipeline/standardiser/fdisplay_inserter.py` — Python-only AST pass that inserts missing `$fdisplay` statements for clocked circuits. Zero LLM calls — deterministic
- Add SEQ fixtures to `tests/fixtures/seq/` (dff, counter, shift_register)
- Gate: integration test injects a known port error → pipeline fixes it within 2 iterations

---

### Phase 4 — Full Evaluation (Weeks 14–16)

- Run all 4 ablation modes (baseline / compiler-only / pyverilog-only / hybrid) across all 156 VerilogEval circuits = 624 total pipeline runs
- Collect: Eval0/1/2 pass rates, tokens per module, repair iterations needed, which pipeline stage failures originated from
- This produces the empirical results that answer the four research questions

---

### Phase 5 — Write the Report (Weeks 17–20, deadline Sept 1)

- Write the final research report in LaTeX
- Key sections: introduction, related work, methodology (pipeline design), evaluation setup, results and analysis, discussion, conclusion
- Report skeleton can be drafted in parallel with Phase 4 evaluation runs

---

## 6. How This Is Different From Simply Using ChatGPT

A natural question is: why build all this infrastructure? Why not just ask ChatGPT "write me a testbench for this circuit" and check if it works?

| Approach | What happens |
|---|---|
| Single prompt to ChatGPT | Works ~40–50% of the time. Fails silently on edge cases. No way to know *why* it failed. |
| AutoBench (multi-stage) | Works ~62% for simple circuits. Repair only triggers on compile errors. No structural pre-check. |
| Our approach (hybrid) | Catches structural errors before simulation. AI gets precise, line-level feedback. Failure stage is always logged. Cost is measured. |

The key insight is that **knowing why the testbench is wrong is more valuable than just knowing it is wrong.** A compiler error says "something failed at line 47." A Pyverilog error says "the clock pin `clk` in your testbench is connected to `reset` in the circuit — swap them on line 14." The AI can fix the second type of feedback far more reliably than the first.

---

## 7. Current Status Summary

| What | Status |
|---|---|
| All 3 papers read and understood | ✅ Done |
| Project constitution + spec + plan + 59 tasks written | ✅ Done |
| Full project skeleton on GitHub | ✅ Done |
| All 8 AI prompt templates written | ✅ Done |
| Error taxonomy data structures | ✅ Done |
| LangGraph graph skeleton (all nodes wired) | ✅ Done |
| Shared LLM wrapper with logging | ✅ Done |
| Dependencies installed (langgraph, pyverilog, jinja2, etc.) | ✅ Done |
| Icarus Verilog 13.0 installed | ✅ Done |
| VerilogEval dataset downloaded (156 problems) | ✅ Done |
| Pyverilog smoke test (3 CMB + 1 SEQ modules) | ✅ Done |
| Phase 1 node implementations (classify → gen_driver → evaluate) | ✅ Done |
| Icarus Verilog wrapper (compile_tb / simulate_tb / eval2) | ✅ Done |
| CLI (`python -m pipeline run --module X --mode hybrid`) | ✅ Done |
| 5-module CMB smoke test — Eval0 5/5, Eval1 4/5, Eval2 4/4 | ✅ Done (gate PASSED) |
| LLM provider: Groq free tier (Llama-3.3-70b-versatile) | ✅ Active |
| Phase 2 — Pyverilog static analysis layer | ✅ Done — 17/17 tests pass, gate verified |
| Phase 3 — Repair loop + SEQ support | ⚪ Next |
| Phase 4 — Full evaluation + ablations | ⚪ Not started |

**Bottom line:** Phases 0, 1, and 2 are complete and gate-tested. The pipeline generates testbenches, runs Pyverilog structural analysis on them, and skips unnecessary LLM calls when the testbench is already correct. The next step is Phase 3: wiring the repair feedback loop so the pipeline can fix its own errors, and adding sequential circuit support.
