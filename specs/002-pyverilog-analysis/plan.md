# Implementation Plan: Phase 2 — Pyverilog Static Analysis

**Branch**: `phase-2-pyverilog`
**Created**: 2026-06-24

---

## Files to Create / Modify

### New files

| File | What it does |
|---|---|
| `pipeline/analysis/verible_runner.py` | Fallback parser using `verible-verilog-syntax` subprocess |
| `tests/unit/test_pyverilog_runner.py` | Unit tests with hand-crafted buggy TBs |

### Modified files (stubs → full implementation)

| File | Change |
|---|---|
| `pipeline/analysis/pyverilog_runner.py` | Implement `run()` — 8-step AST + dataflow analysis |
| `pipeline/nodes/pyverilog_analysis.py` | Replace stub — call runner, handle fallback, write report |
| `pipeline/nodes/error_reasoner.py` | Replace stub — render `error_reasoner.j2`, call Sonnet |

### Unchanged (already correct)

| File | Why |
|---|---|
| `pipeline/analysis/error_taxonomy.py` | All types and dataclasses already defined |
| `prompts/error_reasoner.j2` | Already written in Phase 1 skeleton |
| `pipeline/graph.py` | Nodes already wired in graph (stubs were in the right positions) |

---

## Implementation Order

```
T101 — tests/unit/test_pyverilog_runner.py   (write tests FIRST — TDD)
T102 — pipeline/analysis/pyverilog_runner.py  (implement run())
T103 — pipeline/analysis/verible_runner.py    (fallback)
T104 — pipeline/nodes/pyverilog_analysis.py   (replace stub)
T105 — pipeline/nodes/error_reasoner.py       (replace stub)
T106 — Gate: pytest + smoke rerun
```

---

## Key Implementation Notes for `pyverilog_runner.run()`

### How to parse
```python
ast, _ = vparser.parse([tb_path, dut_path], preprocess_include=[], preprocess_define=[])
module_defs = {m.name: m for m in ast.description.definitions
               if isinstance(m, vast.ModuleDef)}
```
Parse both files together so cross-module references resolve.

### How to find DUT vs TB module
Pass `module_name` (the DUT module name) as a parameter. The TB is the other
module in the parsed AST.

### Port binding check algorithm
```
dut_ports = _extract_ports(module_defs[module_name])
# dut_ports → [(direction, name), ...]
# Find Instance of DUT inside TB
for item in tb_module.items:
    if isinstance(item, vast.InstanceList) and item.module == module_name:
        for inst in item.instances:
            connected = {pa.portname for pa in inst.portlist if pa.portname}
            for direction, port_name in dut_ports:
                if port_name not in connected:
                    → PORT_BINDING_MISMATCH (missing connection)
```

### Undriven / Unobserved check (AST-based)
Walk TB module items for:
- `vast.Reg` / `vast.Wire` declarations that match DUT input names
- `vast.NonblockingSubstitution` / `vast.BlockingSubstitution` that assign to those regs
- `vast.SystemCall` (`$display`, `$fdisplay`, `$monitor`) or `vast.IfStatement`
  conditions that reference DUT output names

Simpler heuristic: if a DUT input port name appears nowhere in the TB body text
after the instance declaration → flag as `UNDRIVEN_INPUT`.

### Sensitivity list check (SEQ only — when DUT has `posedge` in its source)
```python
for item in tb_module.items:
    if isinstance(item, vast.Always):
        sens_list = item.sens_list
        if sens_list:
            sigs = [s.sig.name for s in sens_list.list if s.sig]
            if not any("clk" in s.lower() or "clock" in s.lower() for s in sigs):
                → SENSITIVITY_LIST_ERROR
```

### $fdisplay check (SEQ only)
Walk TB for `vast.SystemCall` where `.syscall` in
`{"fdisplay","display","write","monitor"}`. Map the signal names in the args
back to DUT output ports. Any DUT output not covered → `MISSING_FDISPLAY`.

### Verible fallback
```python
import subprocess, json
result = subprocess.run(
    ["verible-verilog-syntax", "--export_json", "-", "--"],
    input=tb_verilog, capture_output=True, text=True, timeout=10
)
# parse result.stdout as JSON; extract syntax errors
```
If verible is not on PATH, catch FileNotFoundError and set parse_ok=False.

---

## Test Cases for `test_pyverilog_runner.py`

| Test | Input | Expected |
|---|---|---|
| `test_clean_tb_no_errors` | Correct half_adder TB | `report.is_clean() == True` |
| `test_missing_port_flagged` | TB with one port omitted from instance | `PORT_BINDING_MISMATCH` in port_errors |
| `test_wrong_portname_flagged` | TB swaps `sum` ↔ `cout` in port list | `PORT_BINDING_MISMATCH` in port_errors |
| `test_parse_ok_on_valid_verilog` | Any valid Verilog | `report.parse_ok == True` |
| `test_report_is_json_serialisable` | Any valid run | `json.dumps(report.to_dict())` does not raise |
