# Phase 0 Research: SEQ Support

## D1 — Standardiser: text pass vs full AST round-trip

- **Decision**: Deterministic **text/regex pass** over the testbench string, guided by the
  output names from `spec["ports"]["outputs"]`. Detect observation per output; insert a single
  `$monitor` covering all outputs into the `initial` block when any is unobserved; ensure a
  clock generator exists. No LLM. Idempotent via re-detection (+ a marker comment).
- **Rationale**: Pyverilog parses but does not cleanly *emit* modified Verilog (its code
  generator round-trips lossily). A targeted text insertion is robust, reviewable, and
  satisfies Principle VI ("Python AST pass" is satisfied in spirit — a deterministic Python
  pass; the constitution's key demand is *no LLM* and *independently testable*).
- **Alternatives considered**: Pyverilog AST → regenerate — rejected (lossy, fragile). Per-output
  `$display` at each scenario — rejected as more invasive than one `$monitor`.

## D2 — What counts as "observed"

- **Decision**: An output is observed if its name appears in any `$display`/`$fdisplay`/
  `$monitor`/`$write` argument **or** in a comparison inside a pass/fail check (e.g.
  `if (out === ...)`). Reuse the existing `_is_observed` heuristic already in
  `pyverilog_runner` (display/compare/if detection) for consistency.
- **Rationale**: Avoids redundant insertion when the generated TB already checks the output
  (the common case), keeping the standardiser a true no-op when coverage is complete (FR-002).
- **Alternatives**: Only counting `$display`/`$monitor` — rejected, would wrongly re-insert on
  TBs that check outputs via `if` comparisons.

## D3 — Clock generation

- **Decision**: If the spec indicates a clock (timing synchronous or a clock port present) and
  the TB has no clock generator (`always #<n> clk = ~clk;` or equivalent toggle), insert a
  standard `always #5 <clk> = ~<clk>;` plus an initial `<clk> = 0;`. Detect existing generators
  to stay idempotent.
- **Rationale**: A missing clock is the other classic SEQ testbench defect; ensuring it makes
  the SEQ path robust without an LLM.
- **Alternatives**: Leave clocking entirely to the LLM — rejected; the deterministic guarantee
  is the point.

## D4 — Graph routing & the fan-in barrier

- **Decision**: Introduce a no-op `merge_generation` join node. Both `gen_driver` and
  `gen_checker` edge into it (replacing their two direct edges into `pyverilog_analysis`). A
  conditional edge from `merge_generation` routes `SEQ → standardise → pyverilog_analysis` and
  `CMB → pyverilog_analysis`.
- **Rationale**: The branch decision must happen **after both** generation branches complete,
  or `pyverilog_analysis` could fire on the un-standardised driver (a race). A dedicated join
  node makes the barrier explicit and deterministic (Principle I), rather than relying on
  ambiguous multi-predecessor timing.
- **Alternatives**: Conditional straight off `gen_driver` while `gen_checker` still edges to
  `pyverilog_analysis` — rejected (race between `standardise` and the checker's edge).

## D5 — Repair re-entry for SEQ

- **Decision**: Extend `after_repair` so a repaired **SEQ** testbench routes back through
  `standardise` before `pyverilog_analysis`; CMB routes straight to `pyverilog_analysis`;
  oscillation/exhaustion still routes to `evaluate`. The repair conditional-edge map gains a
  `"standardise"` target.
- **Rationale**: Repair regenerates the driver and may drop the `$monitor`; re-standardising
  keeps outputs observable across iterations.
- **Alternatives**: Skip re-standardisation on repair — rejected; could reintroduce the
  missing-observation defect mid-loop.

## D6 — Fixtures

- **Decision**: Three correct, `iverilog -g2012`-compilable SEQ reference modules with prompts:
  `dff` (D flip-flop), `counter_4bit` (synchronous up counter with reset), `shift_register`
  (serial-in shift register). Each `_ref.v` uses `always @(posedge clk ...)` so classification
  and `is_seq` detection fire.
- **Rationale**: Minimal but representative smoke set mirroring the CMB fixtures; enough to
  exercise routing, standardiser, and the SEQ static checks. Keeps token/iteration cost low.
- **Alternatives**: Include an FSM fixture now — deferred; simple sequential first (scope).

## D7 — Prompts

- **Decision**: Keep existing `gen_dut.j2` (already branches on `circuit_type == "SEQ"` for
  clocked logic) and `gen_driver.j2` (already has a sequential-clocking requirement line).
  Minor wording tightening only if smoke reveals gaps.
- **Rationale**: Avoid prompt churn; the deterministic standardiser is the guarantee, not the
  prompt.

## D8 — Async-reset degradation

- **Decision**: Rely on the existing `pyverilog_runner` behaviour that catches `FormatError`
  on async-reset sensitivity lists and falls back to AST-only. The standardiser itself is text
  based and unaffected. The run must complete rather than crash (edge case in spec).
- **Rationale**: Already handled in Phase 0; no new work, just confirmed by a fixture/test if
  time permits.
