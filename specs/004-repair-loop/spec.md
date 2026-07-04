# Feature Specification: Repair Loop (Static + Compiler + Simulation Feedback)

**Feature Branch**: `004-repair-loop`

**Created**: 2026-07-04

**Status**: Draft

**Input**: User description: "Phase 3 repair loop — feed structured error context back to the LLM and regenerate the testbench until fixed or budget exhausted. Three feedback sources: Pyverilog static errors, compilation failures, and simulation failures. Four ablation modes must become genuinely distinct. Bounded iterations + oscillation detection. Precise final status. Generated-DUT Eval1 failures repair the testbench against the DUT as reference. Log every iteration. Tests cover all modes offline."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatically repair a broken testbench (Priority: P1)

A generated testbench has a detectable error (a wrong port binding, a compile error, or a scenario whose expected value disagrees with the DUT). Instead of the run simply failing, the pipeline feeds the specific error back to the model, regenerates the testbench, and re-checks it — repeating until the testbench is correct or an iteration budget is reached.

**Why this priority**: This is the headline capability of Phase 3 and the mechanism that turns detected errors into fixes. Without it, the static-analysis and evaluation layers can only report problems, not resolve them.

**Independent Test**: Start from a testbench with a known injected error; confirm the pipeline regenerates a corrected testbench within the iteration budget and the final status is success.

**Acceptance Scenarios**:

1. **Given** a testbench with a static-analysis error and remaining budget, **When** the pipeline runs, **Then** the error is fed back, the testbench is regenerated, and the run ends in success once the error is gone.
2. **Given** a testbench that fails to compile, **When** the pipeline runs in a mode that repairs compile failures, **Then** the compiler feedback is fed back and the testbench is regenerated.
3. **Given** a testbench that compiles but fails simulation against the evaluation DUT, **When** the pipeline runs in a mode that repairs simulation failures, **Then** the failing-scenario feedback is fed back and the testbench is regenerated.
4. **Given** a repair succeeds, **When** the run completes, **Then** the number of repair iterations taken is recorded and reported.

---

### User Story 2 - Distinct behaviour per ablation mode (Priority: P1)

A researcher runs the same module under each of the four feedback strategies and gets genuinely different behaviour, so the strategies can be compared. BASELINE never repairs. COMPILER_ONLY repairs only on compile failures. PYVERILOG_ONLY repairs only on static-analysis errors. HYBRID repairs on all sources.

**Why this priority**: The comparison of feedback strategies is a core research contribution; the modes must be real, not cosmetic, or the evaluation is meaningless.

**Independent Test**: Run a module that has both a static error and a simulation error under each mode; confirm each mode repairs (or refrains from repairing) according to its definition.

**Acceptance Scenarios**:

1. **Given** BASELINE mode, **When** any error is present, **Then** no repair is attempted and the run ends at first evaluation.
2. **Given** COMPILER_ONLY mode, **When** a static-analysis error is present but the testbench compiles, **Then** no repair is attempted; **When** a compile failure occurs, **Then** repair is attempted.
3. **Given** PYVERILOG_ONLY mode, **When** the testbench compiles but fails simulation, **Then** no repair is attempted; **When** a static-analysis error is present, **Then** repair is attempted.
4. **Given** HYBRID mode, **When** any of the three error sources is present, **Then** repair is attempted.

---

### User Story 3 - The loop always terminates cleanly (Priority: P1)

Whatever happens, the repair loop stops: it never runs forever. It stops on success, when the iteration budget is used up, or when it detects it is going in circles (the same errors keep coming back, or the regenerated testbench stops changing). The final status names exactly how it ended.

**Why this priority**: An unbounded or looping repair process would make the pipeline unusable and would burn API budget. Termination guarantees are non-negotiable.

**Independent Test**: Configure the model to keep returning an unchanged (still-broken) testbench; confirm the loop stops via oscillation detection and the final status is "oscillated". Separately, force persistent distinct errors and confirm it stops at the budget with status "exhausted_iters".

**Acceptance Scenarios**:

1. **Given** the regenerated testbench repeats the same errors as the previous iteration, **When** the loop runs, **Then** it stops and the final status is "oscillated".
2. **Given** errors persist and change each iteration, **When** the iteration budget is reached, **Then** the loop stops and the final status is "exhausted_iters".
3. **Given** a repair succeeds before the budget, **When** the run completes, **Then** the final status is "success" and no further iterations occur.
4. **Given** any termination, **When** the run completes, **Then** the total repair iterations used are within the configured maximum.

---

### User Story 4 - Auditable repair history (Priority: P2)

Each repair attempt is recorded: which feedback source triggered it, which iteration it was, and its token cost. A researcher can later attribute failures to a stage and total the cost of repair.

**Why this priority**: Supports the per-node failure attribution and cost analysis contributions, but the loop functions without it.

**Independent Test**: Run a module that takes two repair iterations; confirm the persisted result lists each iteration with its trigger source and token cost.

**Acceptance Scenarios**:

1. **Given** a run that repairs twice, **When** it completes, **Then** the result records two repair iterations, each tagged with its feedback source and token usage.
2. **Given** a run that never repairs, **When** it completes, **Then** the repair history is empty and repair cost is zero.

---

### Edge Cases

- The generated DUT (no golden reference) and the testbench disagree in simulation — the loop treats the DUT as the reference and repairs the testbench; it never edits the DUT.
- A repair makes things worse (introduces a new error) — the loop continues within budget; oscillation detection only fires on repetition, not on change.
- The very first evaluation already passes — no repair is attempted; iterations = 0.
- The model returns an identical testbench because it cannot improve it — detected as oscillation and stopped.
- Repairing on simulation failure must not repeatedly regenerate mutants or otherwise multiply cost beyond the necessary regeneration.
- A repair fixes the compile error but reveals a simulation error (or vice versa) — each is fed back in turn until success or budget.

## Requirements *(mandatory)*

### Functional Requirements

#### Feedback & Regeneration

- **FR-001**: The system MUST feed a structured description of detected errors back to the model and regenerate the testbench when repair is warranted.
- **FR-002**: The system MUST support three feedback sources as repair triggers: static-analysis errors, compilation failures, and simulation failures against the evaluation DUT.
- **FR-003**: When repairing a simulation failure where the DUT was generated from the description (no golden reference), the system MUST treat the DUT as the reference of record and repair the testbench to match it; it MUST NOT modify the DUT.
- **FR-004**: Each regeneration MUST include the specific failing information (e.g. which port, which compile message, which scenarios and their expected-vs-actual) so the model can act on it.

#### Ablation Modes

- **FR-005**: In BASELINE mode the system MUST never attempt repair.
- **FR-006**: In COMPILER_ONLY mode the system MUST attempt repair only in response to a compilation failure.
- **FR-007**: In PYVERILOG_ONLY mode the system MUST attempt repair only in response to a static-analysis error.
- **FR-008**: In HYBRID mode the system MUST attempt repair in response to any of the three feedback sources.

#### Termination

- **FR-009**: The repair loop MUST be bounded by a configurable maximum iteration count (default 3) and MUST stop when it is reached.
- **FR-010**: The system MUST detect oscillation — the same errors recurring across iterations, or the regenerated testbench being unchanged — and stop.
- **FR-011**: The system MUST set the final status to exactly one of: success, oscillated, exhausted_iters, or a specific failure status, correctly reflecting how the run ended.
- **FR-012**: The repair loop MUST always terminate; under no input may it iterate beyond the configured maximum.

#### Logging & Reporting

- **FR-013**: The system MUST record each repair iteration with its triggering feedback source, iteration number, and token cost.
- **FR-014**: The persisted run result MUST include the number of repair iterations taken and the repair history.

### Key Entities *(include if feature involves data)*

- **Repair Iteration**: One pass of feedback → regenerate → re-check. Attributes: iteration number, triggering feedback source (static / compile / simulation), token cost, resulting status.
- **Error Feedback**: The structured information handed to the model for a repair — the error source, the affected signal or scenario, and the specific detail (message / expected-vs-actual).
- **Loop State**: The control information that bounds the loop — current iteration count, maximum, oscillation flag, and the previous iteration's error signature used to detect repetition.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A testbench with a single injected, detectable error is repaired to success within the iteration budget in at least the common case.
- **SC-002**: Across the four modes run on the same faulty module, each mode's repair behaviour matches its definition (0 repairs for BASELINE; source-restricted repairs for COMPILER_ONLY and PYVERILOG_ONLY; all-source repairs for HYBRID).
- **SC-003**: For every possible run, the number of repair iterations never exceeds the configured maximum.
- **SC-004**: A run in which the model returns an unchanging broken testbench terminates with status "oscillated" rather than exhausting the full budget.
- **SC-005**: A completed run's result reports the repair-iteration count and a per-iteration history including feedback source and token cost.
- **SC-006**: The full behaviour above is demonstrated by an automated test suite that runs offline (no API calls), with at most one optional live test that skips without a key.

## Assumptions

- The evaluation DUT is the reference of record for simulation-based repair. When a golden DUT is supplied it is the reference; otherwise the generated DUT is. The loop only ever regenerates the testbench, never the DUT.
- "The same errors recurring" is judged by a stable signature of the error set (and/or the regenerated testbench being byte-identical to the prior one); an informed default is acceptable and refined in planning.
- Regeneration targets the testbench driver; the checker track is not required to regenerate on every repair unless a future need arises.
- The existing max-iteration default of 3 is retained.
- Simulation-based repair reuses already-generated evaluation artifacts (e.g. mutants) rather than regenerating them each iteration, to bound cost.

## Governance / Constitution Impact

- **No amendments required.** This feature is consistent with the constitution: repair routing is expressed as explicit conditional edges (Principle I), the repair prompt is an externalised template (Principle II), every repair LLM call is logged including token cost (Principle III), and the ablation modes are selectable by a single config flag (Workflow rule 5). The repair node maps to RQ3 (repair effectiveness) and RQ4 (cost–quality tradeoff), satisfying Principle X.
