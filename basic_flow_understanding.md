# Technical Progress Report — S6.ReKI.1
**LLM-Driven Verilog Testbench Generation with Pyverilog-Based Early Error Localization**
**Student:** Muhammad Sawaiz Naveed | **Date:** 14 June 2026 | **Supervisor:** Bing Wen, TU Ilmenau

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

## 4. What We Built (The Skeleton)

This session we built the complete **project skeleton** — all the files, directories, and code structure are in place, but the actual logic inside each function is marked as "TODO: implement in Phase X." Think of it like building the frame of a house: every room exists, every door is in the right place, but the furniture hasn't been moved in yet.

### What was created (81 files, pushed to GitHub):

**`pipeline/state.py`** — The shared data container. Every step reads from and writes to this single structure (called `GraphState`). It holds everything: the input description, the generated testbench code, the error report, the repair iteration count, the evaluation results, and the log of every AI call made.

**`pipeline/config.py`** — Settings. Defines the four ablation modes and configuration options like "how many repair attempts before giving up."

**`pipeline/llm.py`** — The shared AI call function. Every node calls this one function to talk to Claude. It handles: logging, rate limit retries (with automatic waiting if the API is busy), and enforcing temperature=0. No node can bypass this.

**`pipeline/graph.py`** — The LangGraph graph definition. All 10 nodes are registered. All the edges (arrows between steps) are defined. The conditional edge (should we repair or go to evaluation?) is wired up.

**`pipeline/nodes/` (10 files)** — One file per pipeline step. Each file currently raises `NotImplementedError` with a comment explaining exactly what to write there and in which phase. For example, `classify.py` says:
```python
# TODO (Phase 1): render classify_circuit.j2, call llm_call(), parse JSON output
```

**`prompts/` (8 files)** — All AI prompt templates are written and ready. These are Jinja2 templates (like a form letter with blanks to fill in). When a node runs, it fills in the blanks with the actual circuit data and sends the completed prompt to Claude. For example, `gen_driver.j2` says: "You are a hardware verification expert. Write a Verilog testbench driver for [module name]. Here is the spec: [spec]. Here are the test scenarios: [scenarios]..."

**`pipeline/analysis/error_taxonomy.py`** — The data structures for describing errors. Fully implemented. Defines all error types (`PORT_BINDING_MISMATCH`, `UNDRIVEN_INPUT`, `MISSING_FDISPLAY`, etc.), severity levels (`ERROR`, `WARNING`, `INFO`), and the `PyverilogReport` object that holds an analysis result. This is the "vocabulary" the whole system uses to talk about bugs.

**`pipeline/eval/icarus.py`** — Stub for the Icarus Verilog wrapper. Will run `iverilog` and `vvp` as subprocesses and parse the output.

**`pipeline/standardiser/fdisplay_inserter.py`** — Stub for the Python AST pass that inserts missing `$fdisplay` statements. No AI involved — pure Python.

**`scripts/`** — Three scripts:
- `run_smoke.sh` — runs the pipeline on 5 simple test circuits for fast validation
- `run_eval.sh` — runs the full 156-circuit evaluation
- `aggregate_results.py` — reads all result files and produces a summary table

**`tests/`** — pytest test suite. Two tests already pass right now (for `error_taxonomy.py` and `config.py`). The rest are stubs waiting for their corresponding nodes to be implemented.

**`specs/`** — Spec-kit planning documents:
- `constitution.md` — the 10 engineering rules
- `spec.md` — 5 user stories with acceptance criteria
- `plan.md` — full file tree and 6-phase breakdown
- `tasks.md` — 59 numbered tasks with parallel markers

**`README.md`** — Public documentation on GitHub explaining what the project does, how to run it, and how the pipeline works.

---

## 5. What's Next

### Phase 1 — Make It Actually Generate Testbenches (Next 3 Weeks)

This is the immediate next step. We need to fill in the actual logic in the node stubs so the pipeline can produce a real testbench end-to-end.

**Specifically:**

1. **`classify_node`** — Send the circuit description to Haiku, parse the JSON response (`{"circuit_type": "CMB"}`), write the result to GraphState.

2. **`extract_spec_node`** — Send description + circuit code to Sonnet, parse the JSON spec (ports, behaviour, timing), write to GraphState.

3. **`gen_scenarios_node`** — Send the spec to Haiku, parse the list of test scenarios, write to GraphState.

4. **`gen_driver_node` + `gen_checker_node`** — Send spec + scenarios to Sonnet, extract the generated Verilog/Python code from the response, write to GraphState. These two run in parallel.

5. **`icarus.compile_tb()`** — Write the generated Verilog to a temp file, run `iverilog -o output tb.v dut.v` as a subprocess, return whether it succeeded.

6. **`icarus.simulate_tb()`** — Run `vvp output` with a 30-second timeout, scan the output for failure messages, return pass/fail.

7. **`evaluate_node`** — Orchestrate Eval0 → Eval1 → Eval2, write the full result JSON to `results/<run_id>.json`.

**Gate before Phase 2 can begin:** Run `scripts/run_smoke.sh` on 5 simple circuits. Eval0 (compilation) must pass on at least 4/5. Eval1 (correctness) must pass on at least 3/5. If those numbers aren't hit, we fix the prompts and retry before moving forward.

### Phase 2 — Add the Pyverilog Layer (Weeks 5–9)

Once the pipeline generates testbenches reliably, we add the pre-simulation checker:

- Implement `pyverilog_runner.py` — parse TB + circuit together, walk the AST, check port connections and sensitivity lists, run dataflow analysis
- Implement `verible_runner.py` — fallback parser for messy AI-generated Verilog
- Implement `error_reasoner_node` — translate Pyverilog's technical output into actionable AI prompts
- Hand-label 20 circuits to measure how accurate Pyverilog's error detection actually is (precision and recall)

### Phase 3 — Repair Loop + Sequential Circuits (Weeks 10–13)

- Wire the conditional edge: if Pyverilog finds errors and we haven't used up our 3 attempts, loop back to the driver generation step with the error report attached to the prompt
- Implement oscillation detection
- Implement the `$fdisplay` standardiser (Python AST pass)
- Add support for sequential (clocked) circuits through the full pipeline

### Phase 4 — Full Evaluation (Weeks 14–16)

- Run all 4 ablation modes across all 156 VerilogEval circuits (624 total pipeline runs)
- Collect and compare: Eval0/1/2 pass rates, token costs, repair iterations needed, failure stage attribution
- This produces the empirical results that answer the four research questions

### Phase 5 — Write the Report (Weeks 17–20, deadline Sept 1)

- Write the final research report in LaTeX
- Key sections: introduction, related work, methodology (pipeline design), evaluation setup, results and analysis, discussion, conclusion

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
| Full project skeleton (81 files) on GitHub | ✅ Done |
| All 8 AI prompt templates written | ✅ Done |
| Error taxonomy data structures | ✅ Done |
| LangGraph graph skeleton (all nodes wired) | ✅ Done |
| Shared LLM wrapper with logging | ✅ Done |
| LangGraph course | 🟡 In Progress |
| Install dependencies + Pyverilog smoke test | ⚪ Next |
| Download VerilogEval dataset | ⚪ Next |
| Phase 1 node implementations | ⚪ Next |

**Bottom line:** The entire project structure is designed, planned, and scaffolded. The next step is to install the dependencies and start filling in the actual AI logic in the nodes, one by one, until a full testbench comes out the other end.
