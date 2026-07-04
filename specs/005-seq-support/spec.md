# Feature Specification: Sequential (SEQ) Circuit Support

**Feature Branch**: `005-seq-support`

**Created**: 2026-07-04

**Status**: Draft

**Input**: User description: "Enable sequential circuits end-to-end. Deterministic Python-only standardiser that makes every DUT output observable and ensures a clock; route SEQ through the standardise node before static analysis (CMB skips it); SEQ testbench generation handles clocking; add SEQ fixtures; exercise the existing Pyverilog SEQ checks. Tests cover the standardiser, the routing, and a SEQ smoke run — offline, with one optional live test."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate and evaluate a testbench for a clocked circuit (Priority: P1)

A user describes a sequential circuit — a flip-flop, a register, a counter — and runs the pipeline. The circuit is recognised as clocked, a suitable clocked DUT is produced, and a testbench that drives a clock, sequences reset, applies inputs on the clock, and observes outputs is generated and evaluated. The run completes end-to-end with an evaluation result, just as it does for combinational circuits today.

**Why this priority**: This is the headline capability — the pipeline currently only handles combinational circuits. Sequential support is the next major slice of coverage and the area prior work struggled with most.

**Independent Test**: Run the pipeline on a simple clocked fixture (e.g. a D flip-flop); confirm it is classified sequential, a clocked testbench is produced, and evaluation runs to a result.

**Acceptance Scenarios**:

1. **Given** a description of a clocked circuit, **When** the pipeline runs, **Then** the circuit is classified as sequential and a clocked testbench is generated and evaluated.
2. **Given** a sequential run, **When** the testbench is produced, **Then** it generates a clock, sequences any reset, and samples outputs in step with the clock.
3. **Given** a sequential testbench, **When** static analysis runs, **Then** the existing sequential checks (clock-edge sensitivity present, every output observed) are applied.

---

### User Story 2 - Every output is observable, guaranteed (Priority: P1)

For a sequential testbench, every output of the circuit must be observed (printed/monitored) so the checker and evaluation can see it. A deterministic step guarantees this: it inspects the generated testbench and, for any output that is not already displayed or monitored, adds observation for it — without ever changing the circuit itself, and without help from the language model. Running the step twice makes no further change.

**Why this priority**: Reliable output observation is the foundation of sequential evaluation and the deterministic replacement for prior work's fragile model-based approach — a stated project contribution.

**Independent Test**: Feed the step a sequential testbench missing observation for one output; confirm observation is added for exactly that output; run it again and confirm nothing changes; confirm the circuit definition is untouched.

**Acceptance Scenarios**:

1. **Given** a testbench where one output has no display/monitor, **When** the standardiser runs, **Then** that output becomes observed and already-observed outputs are unchanged.
2. **Given** a testbench where all outputs are already observed, **When** the standardiser runs, **Then** the testbench is unchanged (no-op).
3. **Given** any testbench, **When** the standardiser runs, **Then** it makes no language-model call and never edits the circuit definition.
4. **Given** the standardiser has run once, **When** it runs again on its own output, **Then** the result is identical (idempotent).

---

### User Story 3 - Combinational circuits are unaffected (Priority: P1)

Adding sequential support must not change combinational behaviour. Combinational runs skip the sequential-only standardiser and follow exactly the path they do today; their results are unchanged.

**Why this priority**: Protects the completed, validated combinational pipeline — a regression here would undermine the whole project.

**Independent Test**: Run the combinational smoke set; confirm it does not pass through the standardiser and its results match the pre-feature baseline.

**Acceptance Scenarios**:

1. **Given** a combinational circuit, **When** the pipeline runs, **Then** it does not pass through the sequential standardiser.
2. **Given** the combinational smoke set, **When** it runs after this feature, **Then** pass/fail outcomes match the pre-feature baseline.

---

### User Story 4 - A sequential smoke set to iterate on (Priority: P2)

A small library of sequential example circuits exists so the sequential path can be exercised and regression-tested quickly, mirroring the combinational smoke set.

**Why this priority**: Enables fast iteration and regression coverage for sequential support, but the pipeline functions without a large set.

**Independent Test**: Run each sequential fixture through the pipeline offline; confirm each is classified sequential and reaches evaluation.

**Acceptance Scenarios**:

1. **Given** the sequential fixtures, **When** each is run, **Then** each is classified sequential and produces a result.
2. **Given** the sequential fixtures, **When** static analysis runs, **Then** the sequential checks are exercised on real sequential circuits.

---

### Edge Cases

- A sequential testbench already observes all outputs — the standardiser must be a no-op (no duplicate observation).
- A testbench has no clock generation for a clocked circuit — the standardiser ensures a toggling clock exists.
- An output is observed indirectly (e.g. inside a scenario's pass/fail check) versus via a display/monitor — the standardiser must recognise existing observation to avoid redundant insertion.
- A circuit with an asynchronous reset (a sensitivity list the analyser historically choked on) — the run must still complete (degrade gracefully) rather than crash.
- The standardiser is given a malformed or unparseable testbench — it must fail safe (leave the testbench unchanged) rather than corrupt it.
- A combinational circuit is mistakenly classified sequential — routing must still produce a valid run (the standardiser is safe on any testbench).

## Requirements *(mandatory)*

### Functional Requirements

#### Deterministic standardiser

- **FR-001**: The system MUST provide a deterministic step that ensures every circuit output is observable in a sequential testbench, inserting observation only for outputs that lack it.
- **FR-002**: The standardiser MUST be idempotent — running it on its own output produces no further change.
- **FR-003**: The standardiser MUST NOT modify the circuit definition and MUST NOT make any language-model call.
- **FR-004**: The standardiser MUST ensure a clock is generated/toggled for a clocked testbench.
- **FR-005**: The standardiser MUST fail safe on malformed input — leaving the testbench unchanged rather than corrupting it.

#### Routing

- **FR-006**: Sequential circuits MUST pass through the standardiser after testbench generation and before static analysis.
- **FR-007**: Combinational circuits MUST NOT pass through the standardiser and MUST follow their existing path unchanged.
- **FR-008**: Routing MUST be driven by the circuit's classification (sequential vs combinational) as an explicit branch.

#### Sequential generation

- **FR-009**: Sequential testbench generation MUST produce a clock, sequence any reset, apply inputs relative to the clock edge, and sample outputs at the appropriate time.
- **FR-010**: The classification and DUT generation MUST produce a clocked circuit definition when the description implies sequential behaviour.

#### Analysis

- **FR-011**: The existing sequential static checks (clock-edge sensitivity present in the testbench; every output observed) MUST be exercised on sequential runs.

#### Fixtures & smoke

- **FR-012**: The system MUST include a small set of sequential example circuits usable for smoke-testing the sequential path.
- **FR-013**: Each sequential fixture MUST be classified sequential and reach evaluation when run.

#### Testing

- **FR-014**: The default test suite MUST cover the standardiser (insertion, idempotency, correct output targeting, no-op when already covered, no circuit modification) fully offline.
- **FR-015**: The default test suite MUST verify routing (sequential passes through the standardiser; combinational does not) fully offline.
- **FR-016**: A single optional live sequential test MAY make a real language-model call and MUST skip automatically when no key is present.

### Key Entities *(include if feature involves data)*

- **Sequential Testbench**: A testbench for a clocked circuit — drives a clock, sequences reset, applies inputs on the clock, observes outputs.
- **Standardiser Result**: The (possibly) modified testbench plus the record that observation was ensured for all outputs; the circuit definition is never part of what it changes.
- **Sequential Fixture**: A named example clocked circuit (description + reference definition) used for smoke-testing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A described clocked circuit runs end-to-end and produces an evaluation result, for at least the simple cases (flip-flop, counter, shift register).
- **SC-002**: After the standardiser runs, 100% of circuit outputs are observable in the sequential testbench.
- **SC-003**: Running the standardiser twice yields an identical testbench (idempotent) in all tested cases.
- **SC-004**: The combinational smoke set's pass/fail outcomes are unchanged from the pre-feature baseline, and combinational runs never enter the standardiser.
- **SC-005**: Every sequential fixture is classified sequential and reaches evaluation.
- **SC-006**: The standardiser and routing behaviour are demonstrated by an automated suite that runs offline (no model calls), with at most one optional live sequential test that skips without a key.

## Assumptions

- "Observable" means the output appears in a display/monitor call or in a scenario's pass/fail check that references it; the standardiser recognises either form before deciding to insert.
- The deterministic standardiser is a text/structural pass over the testbench (no model involvement); a fully formal AST round-trip is not required as long as insertion is correct and idempotent — consistent with the project's "Python-only standardiser" contribution and the constitution's rejection of model-based standardisation.
- Scope targets simple-to-moderate sequential circuits (flip-flops, registers, counters, shift registers, simple state machines). Chasing peak accuracy on complex finite state machines is out of scope; the aim is a working sequential path, per the project's "pipeline over accuracy" priority.
- The combinational path, evaluation gates, repair loop, DUT generation, and results reporting are unchanged except for the added sequential branch.
- The constitution's precondition (combinational passes on ≥5 modules before sequential work) is already satisfied.

## Governance / Constitution Impact

- **No amendments required.** This feature is consistent with the constitution: the standardiser is deterministic and Python-only (Principle VI — model-based standardisation explicitly rejected); routing is an explicit conditional branch (Principle I); sequential work follows the combinational milestone (Principle V); static analysis precedes simulation (Principle VII). The standardiser and sequential path map to RQ1 (error taxonomy — the missing-`$fdisplay` class) and RQ2 (pre-simulation localisation), satisfying Principle X.
