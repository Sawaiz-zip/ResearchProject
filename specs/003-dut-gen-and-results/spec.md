# Feature Specification: DUT Generation, Configurable Temperature & Human-Readable Results

**Feature Branch**: `003-dut-gen-and-results`

**Created**: 2026-07-04

**Status**: Draft

**Input**: User description: "Phase 3 pipeline refinements — (1) generate the DUT from the natural-language description instead of requiring a golden DUT as input; (2) classify from the description only; (3) make LLM temperature configurable (not forced to 0); (4) produce clear human-readable per-run results. Plus tests that fully exercise the flow while minimising Groq free-tier token usage."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a testbench from a description alone (Priority: P1)

A user has only a plain-English description of a circuit — no reference (golden) Verilog. They run the pipeline with just that description. The pipeline first decides whether the circuit is combinational or sequential, then generates a Design-Under-Test (DUT) from the description, and proceeds through the rest of the flow (spec extraction, scenario generation, driver/checker generation, static analysis, evaluation) using that generated DUT.

**Why this priority**: This is the core capability change. Today the pipeline cannot run without a hand-supplied golden DUT, which does not match how a real user works. Without this, the tool is only usable on benchmark data that already ships reference RTL.

**Independent Test**: Run the pipeline with a description and no DUT input; confirm a DUT is generated, all downstream nodes consume it, and a result is produced end-to-end.

**Acceptance Scenarios**:

1. **Given** a description of a combinational circuit and no golden DUT, **When** the pipeline runs, **Then** a DUT is generated from the description and the run completes with an evaluation result.
2. **Given** a description of a sequential circuit and no golden DUT, **When** the pipeline runs, **Then** classification identifies it as SEQ before any DUT exists, and a DUT is generated for the remaining stages.
3. **Given** a generated DUT, **When** static analysis runs, **Then** port-binding and observability checks operate against the generated DUT exactly as they previously did against the golden DUT.

---

### User Story 2 - Benchmark against a golden DUT without changing the user flow (Priority: P2)

A researcher wants numbers comparable to prior work (AutoBench). They supply a golden DUT from the benchmark dataset, but only for the evaluation step — the generation flow still produces its own DUT and testbench from the description. Evaluation (does the testbench compile, pass, and catch bugs) is measured against the supplied golden DUT.

**Why this priority**: Needed to keep the research results credible and comparable, but it is a specialised path layered on top of the P1 user flow.

**Independent Test**: Run a benchmark module with a golden DUT provided as an evaluation-only reference; confirm generation still creates its own DUT, and Eval1/Eval2 are computed against the golden DUT.

**Acceptance Scenarios**:

1. **Given** a description and an evaluation-only golden DUT, **When** the pipeline runs, **Then** generation uses the LLM-generated DUT while evaluation compiles and simulates the testbench against the golden DUT.
2. **Given** no golden DUT is supplied, **When** evaluation runs, **Then** evaluation falls back to the generated DUT and the result clearly records which DUT was used for evaluation.

---

### User Story 3 - Clear, readable results for every run (Priority: P2)

After any run, the user sees an at-a-glance summary: what they asked for, how many test scenarios passed, whether the three evaluation gates passed, how many repair iterations occurred, how many tokens were used, and how long it took. The same information is persisted so runs can be reviewed later.

**Why this priority**: The current output is a raw JSON blob with pass/fail buried inside an unparsed simulator log; a user cannot tell at a glance what happened. High user-facing value, but the pipeline still functions without it.

**Independent Test**: Run any module; confirm a console summary is printed containing the description, per-scenario pass/fail counts, the three evaluation outcomes, repair count, token total, wall time, and final status; confirm the persisted result contains the description and structured per-scenario outcomes.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** results are produced, **Then** the persisted result includes the original description and a structured list of per-scenario pass/fail outcomes (not just a raw log).
2. **Given** a completed run, **When** the summary is printed, **Then** it shows "N of M scenarios passed", the three evaluation results, repair iterations, total tokens (in/out), wall time, and final status.
3. **Given** a run where the testbench fails some scenarios, **When** the summary is printed, **Then** the failing scenarios are individually identifiable.

---

### User Story 4 - Robust operation at non-zero temperature (Priority: P2)

An operator points the pipeline at a different model or raises the sampling temperature above zero. The pipeline still completes: structured outputs are parsed tolerantly, and transient malformed responses are retried rather than crashing the run.

**Why this priority**: The pipeline should be model-agnostic and not depend on deterministic decoding. Important for portability, but the default behaviour still works without it.

**Independent Test**: Configure a non-zero temperature; run a module; confirm the pipeline completes and the temperature actually used is recorded in the run's telemetry.

**Acceptance Scenarios**:

1. **Given** a configured temperature above zero, **When** any LLM node runs, **Then** that temperature is applied to the model call and recorded in the call log.
2. **Given** no temperature is configured, **When** the pipeline runs, **Then** a documented default is applied.
3. **Given** a malformed or non-parseable structured response, **When** a node processes it, **Then** the node retries or falls back rather than aborting the whole run.

---

### User Story 5 - Fully exercised flow without burning API quota (Priority: P1)

A developer runs the test suite to validate the whole pipeline. The suite covers every node and routing decision, but almost all tests substitute canned LLM responses so they consume no external API quota. Only a very small number of clearly-marked integration tests make real API calls, and those can be skipped when no key is present.

**Why this priority**: The project runs on a free tier with tight token limits; a test suite that spends real tokens on every run is unusable. Comprehensive coverage is required to trust the refactor.

**Independent Test**: Run the default test suite offline (no API key); confirm the full flow is exercised via substituted LLM responses and no external calls are made. Confirm the real-API integration tests are marked and skipped when no key is available.

**Acceptance Scenarios**:

1. **Given** no API key is configured, **When** the default test suite runs, **Then** all unit and flow tests pass without making external calls.
2. **Given** the test suite, **When** it exercises the pipeline, **Then** every node and every routing branch (CMB vs SEQ, repair vs evaluate, golden-vs-generated DUT at eval) is covered.
3. **Given** an API key is configured, **When** the marked integration tests run, **Then** a small fixed number of real end-to-end runs validate live behaviour.

---

### Edge Cases

- The description is ambiguous about combinational vs sequential — classification must still make a decision, and the generated DUT must be consistent with that decision.
- The LLM generates a DUT that does not compile — this is a generation failure the pipeline must record and surface, not a crash.
- The generated DUT and the testbench disagree because both came from the same description — evaluation against a generated DUT confirms mutual consistency, not ground-truth correctness; the result must make clear which DUT evaluation used.
- The simulator output contains lines that look like pass/fail markers but are debug prints — scenario parsing must not miscount them.
- A run makes zero LLM calls in some node (e.g. clean static analysis) — token totals and summary must still render correctly.
- Temperature is set high enough that a structured response is malformed — retry/fallback must keep the run alive.

## Requirements *(mandatory)*

### Functional Requirements

#### DUT Generation

- **FR-001**: The pipeline MUST accept a natural-language circuit description as its sole required input; a golden DUT MUST NOT be required to run the generation flow.
- **FR-002**: The pipeline MUST classify a circuit as combinational or sequential using only the description, before any DUT exists.
- **FR-003**: The pipeline MUST generate a DUT from the description and the classified circuit type via an LLM node, positioned after classification and before specification extraction.
- **FR-004**: All downstream stages that previously consumed the golden DUT (specification extraction, static analysis / port-binding & observability checks, evaluation) MUST consume the generated DUT when no golden DUT is supplied.
- **FR-005**: The pipeline MUST record the generated DUT in the persisted run result.

#### Golden DUT at Evaluation Only

- **FR-006**: The pipeline MUST allow an optional golden DUT to be supplied for evaluation purposes only, without altering the generation flow.
- **FR-007**: When a golden DUT is supplied, evaluation (compilation, pass-against-DUT, bug-catching) MUST be measured against the golden DUT; when it is absent, evaluation MUST fall back to the generated DUT.
- **FR-008**: The run result MUST record which DUT (generated or golden) was used for evaluation.

#### Configurable Temperature

- **FR-009**: The system MUST allow the LLM sampling temperature to be configured, MUST NOT force it to zero, and MUST apply a documented default when unset.
- **FR-010**: The temperature actually used for each LLM call MUST be recorded in that call's log entry.
- **FR-011**: Structured-output nodes MUST parse responses tolerantly and MUST retry or fall back on malformed responses so that non-zero temperature does not abort a run.

#### Human-Readable Results

- **FR-012**: The persisted run result MUST include the original natural-language description.
- **FR-013**: The system MUST parse the simulator output into a structured list of per-scenario pass/fail outcomes, and MUST NOT miscount debug lines that resemble pass/fail markers.
- **FR-014**: After every run, the system MUST print a human-readable summary containing: the description, per-scenario "N of M passed" with failing scenarios identifiable, the three evaluation outcomes, the repair-iteration count, total tokens (input and output), wall-clock time, and the final status.
- **FR-015**: The summary and persisted result MUST render correctly even when a run makes zero LLM calls in one or more nodes.

#### Testing

- **FR-016**: The default test suite MUST exercise every node and every routing branch of the pipeline using substituted (canned) LLM responses, consuming no external API quota.
- **FR-017**: The default test suite MUST pass with no API key configured.
- **FR-018**: A small, explicitly-marked set of integration tests MAY make real API calls and MUST be skipped automatically when no API key is present.

### Key Entities *(include if feature involves data)*

- **Run Result**: The persisted record of one pipeline execution. Now additionally holds: the natural-language description, the generated DUT, which DUT evaluation used, structured per-scenario outcomes, and aggregate token/time totals.
- **Per-Scenario Outcome**: One test scenario's identity and pass/fail result, derived from the simulator output.
- **LLM Call Log Entry**: The existing per-call telemetry record, now additionally holding the temperature used.
- **Generated DUT**: The LLM-produced Design-Under-Test derived from the description; distinct from an optional golden DUT used only for evaluation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pipeline completes an end-to-end run given only a description and no golden DUT, for both a combinational and a sequential example.
- **SC-002**: For a benchmark run, evaluation results are computed against the supplied golden DUT while generation still produces its own DUT, and the result records which DUT was used.
- **SC-003**: A person reading only the printed summary can state, without opening any log, what was requested, how many scenarios passed, and whether the run succeeded.
- **SC-004**: The pipeline completes successfully with temperature configured above zero, and the used temperature appears in the telemetry.
- **SC-005**: The default test suite runs to completion with no API key present, exercises every node and routing branch, and makes zero external API calls.
- **SC-006**: Real-API integration tests are limited to a small fixed number of runs and are skipped automatically when no key is configured.

## Assumptions

- A single description is sufficient to both classify and generate a DUT; the description is assumed to be coherent enough for an LLM to produce compilable RTL in the common case, with generation-failure handling for the rest.
- Evaluation against a generated DUT is understood to verify mutual consistency of DUT and testbench, not ground-truth correctness; golden-DUT evaluation remains the path for comparable research numbers.
- The default temperature when unset is 0.7 (a conventional general-purpose value); this can be overridden per environment.
- "Substituted LLM responses" in tests means canned/mocked outputs standing in for real model calls; the exact mechanism is an implementation detail for the plan.
- Existing evaluation gates (compiles / passes-against-DUT / catches-bugs) and their meanings are unchanged; only the DUT they run against and how results are surfaced change.

## Governance / Constitution Impact

- **Amends Constitution Principle IV ("Determinism at Temperature 0").** That principle currently mandates `temperature=0` for all nodes. FR-009 through FR-011 deliberately relax this to a configurable temperature with a non-zero default, and shift the robustness guarantee from deterministic decoding to tolerant parsing plus retry. This requires a constitution amendment (update Principle IV, bump version) and is called out here so the change is explicit and auditable rather than a silent deviation.
- **New node maps to research questions.** The `gen_dut` node primarily serves RQ1/RQ3 (it produces the artifact whose errors are localised and repaired). This satisfies Principle X (research-question traceability).
