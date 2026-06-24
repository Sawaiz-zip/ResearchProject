---
description: "Phase 2 task list — Pyverilog static analysis layer"
---

# Tasks: Phase 2 — Pyverilog Static Analysis

**Branch**: `phase-2-pyverilog`
**Last updated**: 2026-06-24
**Input**: [spec.md](./spec.md) + [plan.md](./plan.md)

---

## Phase 2 Tasks

### Tests (write first — TDD)

- [ ] T101 [P] Write `tests/unit/test_pyverilog_runner.py`:
  - `test_clean_tb_no_errors` — correct half_adder TB → `report.is_clean()`
  - `test_missing_port_flagged` — TB omits one port → PORT_BINDING_MISMATCH
  - `test_wrong_portname_flagged` — TB swaps port names → PORT_BINDING_MISMATCH
  - `test_parse_ok_on_valid_verilog` — `report.parse_ok == True`
  - `test_report_is_json_serialisable` — `json.dumps(report.to_dict())` succeeds

### Core implementation

- [ ] T102 Implement `pipeline/analysis/pyverilog_runner.run(tb, dut, module_name)`:
  - Step 1: write to temp files, parse both with `vparser.parse()`
  - Step 2: find DUT + TB module definitions in AST
  - Step 3: extract DUT ports with `_extract_ports()`
  - Step 4: walk TB for `vast.InstanceList` → `vast.Instance` → `vast.PortArg`; flag missing/misnamed ports
  - Step 5: heuristic undriven/unobserved check (signal name appears in TB body)
  - Step 6: try `VerilogDataflowAnalyzer` on DUT; catch `FormatError`
  - Step 7: sensitivity list check if DUT contains `posedge`
  - Step 8: `$fdisplay` check for SEQ circuits
  - Return populated `PyverilogReport`

- [ ] T103 [P] Create `pipeline/analysis/verible_runner.py`:
  - Run `verible-verilog-syntax --export_json - --` as subprocess
  - Return partial `PyverilogReport(parse_ok=True/False, parser_used="verible")`
  - If verible not on PATH → return `PyverilogReport(parse_ok=False, parser_used="none")`

- [ ] T104 Replace stub in `pipeline/nodes/pyverilog_analysis.py`:
  - Call `pyverilog_runner.run(driver_rtl, golden_dut, module_name)`
  - On `NotImplementedError`/`Exception` from runner → try `verible_runner`
  - Write `pyverilog_report` dict to state

- [ ] T105 Replace stub in `pipeline/nodes/error_reasoner.py`:
  - Copy `error_report → last_error_report` (oscillation detection setup)
  - If `pyverilog_report` is clean (no errors) → set `error_report: []`, skip LLM call
  - Otherwise: render `error_reasoner.j2`, call Sonnet, parse JSON array
  - Write `error_report` list to state

### Gate

- [ ] T106 Run `pytest tests/unit/test_pyverilog_runner.py` — all 5 tests pass
- [ ] T107 Run `python -m pipeline run --module half_adder --mode hybrid` — still `success`
- [ ] T108 Run buggy-TB manual test: create TB with wrong port name, confirm `error_report` non-empty

---

## Dependencies

- T101 can be written immediately (uses fixture files from Phase 1)
- T102 must come before T104
- T103 is independent of T102 (parallel)
- T104 depends on T102 + T103
- T105 depends on T104 (needs `pyverilog_report` to be populated)
- T106–T108 depend on T102–T105

## Notes

- `[P]` = can run in parallel
- Pyverilog LALR warning ("183 shift/reduce conflicts") is normal — suppress with `--quiet` flag or accept it
- Verible is optional — if not installed, `parse_ok=False` is a valid degraded state
- Do NOT add LLM calls to `pyverilog_analysis_node` — it must remain deterministic
