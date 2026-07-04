# Phase 1 Data Model: SEQ Support

## No GraphState schema changes

SEQ support reuses existing fields: `circuit_type` ("SEQ"|"CMB"), `driver_rtl`, `spec`.
The standardiser rewrites `driver_rtl` in place; no new state fields are required.

## Standardiser contract (`pipeline/standardiser/fdisplay_inserter.py`)

```python
def insert_fdisplay(driver_rtl: str, spec: dict) -> str:
    """Return driver_rtl with observation ensured for every DUT output and a clock
    generator ensured for clocked testbenches. Idempotent; never edits the DUT;
    no LLM. Fail-safe: returns driver_rtl unchanged on any internal error."""
```

Helpers:
- `_find_outputs(spec) -> list[str]` — output port names from `spec["ports"]["outputs"]`.
- `_is_observed(driver_rtl, name) -> bool` — name appears in a display/monitor/write call OR
  in a comparison/if check.
- `_has_clock_gen(driver_rtl, clk) -> bool` — a toggling clock generator exists.
- `_clock_name(spec) -> str | None` — clock port from `spec["ports"]["clock"]`.

Behaviour:
1. If all outputs observed and clock present (when needed) → return unchanged (no-op).
2. Insert one `$monitor("...", outs...)` into the `initial` block for missing observation.
3. Insert `always #5 <clk> = ~<clk>;` (+ initial `<clk>=0;`) when a clock is needed and absent.
4. Guard with a marker comment (`// [standardised]`) so a second pass is a no-op.
5. Any exception → return the original `driver_rtl` (fail-safe).

## Node contracts

- `standardise_node(state) -> {"driver_rtl": <updated>}` — calls `insert_fdisplay`; zero LLM
  calls; safe on any `driver_rtl`.
- `merge_generation_node(state) -> {}` — no-op join/barrier.

## Routing

- `route_after_generation(state) -> "standardise" | "pyverilog_analysis"` — by `circuit_type`.
- `after_repair(state)` (extended) → `"evaluate"` (stop) | `"standardise"` (SEQ) |
  `"pyverilog_analysis"` (CMB).

## Fixtures (`tests/fixtures/seq/`)

| Name | `_ref.v` summary | Ports |
|---|---|---|
| `dff` | `always @(posedge clk) q <= d;` | clk, d → q |
| `counter_4bit` | up counter with sync reset | clk, rst → out[3:0] |
| `shift_register` | serial-in shift register | clk, rst, in → out[3:0] |

Each ships `<name>_prompt.txt` + `<name>_ref.v`; both compile under `iverilog -g2012`.

## Validation rules

- After `standardise_node`, every output in `spec` is observed in `driver_rtl` (SC-002).
- `insert_fdisplay(insert_fdisplay(x)) == insert_fdisplay(x)` (idempotent, SC-003).
- `insert_fdisplay` never alters text outside the testbench's `initial`/clock scaffolding and
  never emits a module definition (no DUT modification).
- CMB runs never invoke `standardise_node` (SC-004).
