# Feature Specification: Evaluation Harness (Ablation Study)

**Feature Branch**: `006-eval-harness`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "Phase 4 ablation study. Batch runner over modules × 4 modes; aggregator producing per-mode Eval0/1/2 rates, mean repair iterations, token/time cost, final-status distribution, per-node failure attribution. Token-budget-aware (default small subset; opt-in for large sweeps; run-count estimate). Record mode+module per result. Aggregation testable offline; runner exercisable mocked. Precision/recall optional. Deliver runner, aggregator (machine + human-readable), the mode/module fields, and tests."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare the four feedback strategies (Priority: P1)

A researcher runs the pipeline over a set of circuits under each of the four ablation modes and gets a single summary that puts the modes side by side: how often each mode's testbench compiles, passes against the reference, and catches injected bugs, plus how much repair, time, and token cost each mode incurs. This is the evidence for the project's central comparison of feedback strategies.

**Why this priority**: The mode comparison is the core research contribution of the evaluation phase; without it there are no results to report.

**Independent Test**: Run the harness over a small module set across all four modes; confirm a summary is produced with one row per mode and the three evaluation rates plus cost figures.

**Acceptance Scenarios**:

1. **Given** a set of modules and the four modes, **When** the batch runner executes, **Then** one result record is saved per (module, mode) pair, each tagged with its mode and module.
2. **Given** the saved result records, **When** the aggregator runs, **Then** it produces, per mode, the Eval0/Eval1/Eval2 rates, mean repair iterations, mean token cost, and mean wall-clock time.
3. **Given** the aggregated summary, **When** a person reads it, **Then** they can compare the four modes without opening individual result records.

---

### User Story 2 - Understand where failures come from (Priority: P1)

Beyond pass rates, the researcher wants to know *where* runs fail — which pipeline stage each failure originated in, and how final outcomes distribute (success, oscillated, exhausted iterations, specific failures). This per-stage attribution is a stated contribution that prior work lacks.

**Why this priority**: Failure attribution is a distinct, novel contribution; it turns raw pass rates into actionable insight about the pipeline.

**Independent Test**: Aggregate a set of result records containing a mix of outcomes; confirm the summary reports the count/fraction of failures per originating stage and the distribution of final statuses.

**Acceptance Scenarios**:

1. **Given** result records with varied failure stages, **When** the aggregator runs, **Then** the summary includes a per-stage failure count/fraction.
2. **Given** result records with varied final statuses, **When** the aggregator runs, **Then** the summary includes the distribution of final statuses per mode.

---

### User Story 3 - Stay within the API budget (Priority: P1)

Because the project runs on a free tier, the researcher must not accidentally launch hundreds of paid runs. The runner defaults to a small subset, tells the user how many runs a given selection implies, and refuses to launch a large sweep unless the user explicitly opts in (and/or sets a limit).

**Why this priority**: A single careless invocation of the full benchmark could exhaust the entire budget; the guardrail is essential to the project being runnable at all.

**Independent Test**: Invoke the runner with no arguments; confirm it targets only the small default subset and prints the implied run count. Invoke it for a large selection without opt-in; confirm it refuses and explains how to opt in.

**Acceptance Scenarios**:

1. **Given** no explicit selection, **When** the runner starts, **Then** it targets only the small default subset and reports the number of runs it will perform.
2. **Given** a selection larger than a safe threshold and no opt-in, **When** the runner starts, **Then** it does not execute and explains how to opt in or set a limit.
3. **Given** an explicit opt-in or a module limit, **When** the runner starts, **Then** it proceeds with the bounded selection.

---

### User Story 4 - Trustworthy, offline-verifiable aggregation (Priority: P2)

The aggregation and reporting logic can be validated without spending any API budget, by running it over synthetic result records with known contents and checking the computed summary.

**Why this priority**: Guarantees the headline numbers are correct before any expensive real sweep; protects the credibility of the results.

**Independent Test**: Feed the aggregator a hand-made set of result records with known values; confirm every computed figure matches the expected value.

**Acceptance Scenarios**:

1. **Given** synthetic result records with known outcomes, **When** the aggregator runs, **Then** each rate, mean, and distribution equals its hand-computed expected value.
2. **Given** an empty or malformed record set, **When** the aggregator runs, **Then** it degrades gracefully (reports nothing to aggregate) rather than crashing.

---

### Edge Cases

- A result set contains runs from only some of the four modes — the summary reports the modes present without inventing the others.
- A run has zero repair iterations / zero tokens — means and rates still compute correctly.
- Result records from different runs of the same (module, mode) exist — the aggregator must not silently double-count; the newest wins or all are counted per a documented rule.
- A malformed or partial result record is present — aggregation skips it safely rather than crashing.
- The runner is asked for the full benchmark without opt-in — it refuses and reports the run count instead of executing.
- A single run errors mid-sweep — the sweep records the failure and continues rather than aborting the whole batch.

## Requirements *(mandatory)*

### Functional Requirements

#### Result tagging

- **FR-001**: Every result record MUST record which ablation mode produced it.
- **FR-002**: Every result record MUST record which module (identity) produced it.

#### Batch runner

- **FR-003**: The runner MUST execute the pipeline over a configurable set of modules across a configurable subset of the four modes, saving one result record per (module, mode) pair.
- **FR-004**: The runner MUST default to a small subset (the smoke/fixture set) when no explicit selection is given.
- **FR-005**: The runner MUST report the number of runs a given selection implies before executing.
- **FR-006**: The runner MUST refuse to launch a selection larger than a safe threshold unless the user explicitly opts in and/or sets a module limit.
- **FR-007**: The runner MUST continue the sweep when an individual run fails, recording the failure rather than aborting the batch.

#### Aggregator

- **FR-008**: The aggregator MUST group result records by mode and compute, per mode, the Eval0, Eval1, and Eval2 pass rates.
- **FR-009**: The aggregator MUST compute, per mode, mean repair iterations, mean token cost (input and output), and mean wall-clock time per module.
- **FR-010**: The aggregator MUST compute, per mode, the distribution of final statuses.
- **FR-011**: The aggregator MUST compute a per-node (pipeline-stage) failure-attribution breakdown as counts and fractions.
- **FR-012**: The aggregator MUST produce a machine-readable summary and a human-readable table.
- **FR-013**: The aggregator MUST skip malformed/partial records and degrade gracefully on an empty set.

#### Testing

- **FR-014**: The aggregation logic MUST be fully testable offline on synthetic result records with no API calls.
- **FR-015**: The runner MUST be exercisable on a tiny mocked run (no real API calls) to validate its wiring and budget guardrail.
- **FR-016**: Any real-API sweep MUST be gated behind explicit opt-in; the default test path MUST make no API calls.

### Optional / Follow-up

- **FR-017 (Optional)**: A measurement of static-analysis error precision and recall against a small hand-labelled set MAY be added as a separate follow-up; it is not required for this feature to be complete.

### Key Entities *(include if feature involves data)*

- **Result Record**: The persisted record of one pipeline run — now additionally tagged with its mode and module — and already carrying evaluation outcomes, repair iterations, tokens, wall time, final status, and failure stage.
- **Mode Summary**: The per-mode aggregate — the three pass rates, mean repair/token/time figures, final-status distribution, and failure-stage breakdown.
- **Sweep Selection**: The chosen set of modules × modes to run, plus the implied run count and any opt-in/limit that authorises it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the harness across the four modes on a small module set yields a summary with one entry per mode, each showing the three evaluation rates and the cost figures.
- **SC-002**: The summary reports, per mode, a per-stage failure-attribution breakdown and a final-status distribution.
- **SC-003**: Invoking the runner with no arguments touches only the small default subset and reports its run count; a large selection without opt-in does not execute.
- **SC-004**: Every aggregate figure matches a hand-computed value on a synthetic record set (verified by an automated offline test).
- **SC-005**: The default test path spends zero API budget; the runner can be exercised end-to-end with mocked model calls.
- **SC-006**: Each result record is unambiguously attributable to a single (module, mode) pair.

## Assumptions

- The existing evaluation gates (Eval0/1/2), repair-iteration count, token logs, wall time, final status, and failure stage are already recorded per run; this feature adds the mode/module tags and the aggregation/runner layers around them.
- "A small default subset" means the existing smoke/fixture set (a handful of modules), sufficient to exercise all four modes cheaply.
- The "safe threshold" for requiring opt-in is a modest number of total runs (an informed default, e.g. on the order of a few dozen), tunable; the exact number is an implementation detail documented in the runner.
- Duplicate (module, mode) records are resolved by a documented rule (e.g. newest wins); the default is acceptable and stated in the aggregator.
- The full benchmark (all modules × four modes) is understood to be too expensive to run casually on the free tier; the harness makes running it a deliberate, bounded choice rather than a default.

## Governance / Constitution Impact

- **No amendments required.** The harness is analysis/tooling around the existing graph; it adds no LLM nodes and no hidden control flow. It directly serves the research questions: the mode comparison (RQ3, RQ4), per-node failure attribution (a stated contribution), and cost analysis (RQ4). The token-budget guardrail reflects the project's free-tier, pipeline-over-accuracy priority.
