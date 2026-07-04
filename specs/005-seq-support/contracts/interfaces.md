# Phase 1 Contracts: SEQ Support Interfaces

## 1. Standardiser (`pipeline/standardiser/fdisplay_inserter.py`)

```python
def insert_fdisplay(driver_rtl: str, spec: dict) -> str
```
- Inputs: the generated testbench text; the spec (for output names, clock name, timing).
- Output: testbench text with (a) a `$monitor` covering any unobserved outputs, (b) a clock
  generator if a clock is needed and absent, (c) a `// [standardised]` marker.
- Guarantees: idempotent; no DUT modification; no LLM; fail-safe (returns input on error).

## 2. Nodes

```python
def standardise_node(state: GraphState) -> dict      # {"driver_rtl": updated}; 0 LLM calls
def merge_generation_node(state: GraphState) -> dict  # {} — fan-in barrier
```

`pipeline/nodes/__init__.py` exports `merge_generation_node` (and keeps `standardise_node`).

## 3. Routing (`pipeline/graph.py` + `pipeline/nodes/repair.py`)

```python
def route_after_generation(state) -> str   # "standardise" if SEQ else "pyverilog_analysis"
def after_repair(state) -> str             # "evaluate" | "standardise"(SEQ) | "pyverilog_analysis"(CMB)
```

Graph edges changed:
```python
# remove: gen_driver -> pyverilog_analysis ; gen_checker -> pyverilog_analysis
g.add_edge("gen_driver",  "merge_generation")
g.add_edge("gen_checker", "merge_generation")
g.add_conditional_edges("merge_generation", route_after_generation,
    {"standardise": "standardise", "pyverilog_analysis": "pyverilog_analysis"})
g.add_edge("standardise", "pyverilog_analysis")   # existing
# repair conditional-edge map gains a "standardise" target:
g.add_conditional_edges("repair", after_repair,
    {"pyverilog_analysis": "pyverilog_analysis", "standardise": "standardise",
     "evaluate": "evaluate"})
```

## 4. Fixtures (`tests/fixtures/seq/`)

`dff`, `counter_4bit`, `shift_register` — each `<name>_prompt.txt` + `<name>_ref.v`, all
compiling under `iverilog -g2012`, all using `always @(posedge clk ...)`.

## 5. Tests

- `tests/unit/test_fdisplay_inserter.py`: insertion for a missing output; no-op when all
  observed; idempotency; correct output targeting; clock insertion when absent; fail-safe on
  malformed input; DUT text never emitted.
- `tests/integration/test_seq_routing.py` (mocked LLM): a SEQ run passes through `standardise`
  and its `driver_rtl` ends observed; a CMB run never enters `standardise`; both complete (no
  deadlock). Assert via a spy/monkeypatch on `standardise_node` or by observing `driver_rtl`
  changes / the `// [standardised]` marker.
- `tests/integration/test_seq_live.py`: `@pytest.mark.live`, skips without key; one real SEQ
  run (e.g. `dff`) reaching a result.

## 6. Conftest additions

Extend `tests/conftest.py` `_CANNED_BY_NODE` so a SEQ run has coherent canned responses:
a clocked DUT for `gen_dut`, a spec with a clock and one output, and a driver that is (for the
routing test) missing the `$monitor` so the standardiser visibly acts.
