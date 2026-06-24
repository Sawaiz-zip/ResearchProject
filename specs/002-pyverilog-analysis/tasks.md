---
description: "Phase 2 task list — Pyverilog static analysis layer"
---

# Tasks: Phase 2 — Pyverilog Static Analysis

**Branch**: `phase-2-pyverilog`
**Last updated**: 2026-06-24 (all tasks complete)
**Input**: [spec.md](./spec.md) + [plan.md](./plan.md)

---

## Phase 2 Tasks

### Tests (write first — TDD)

- [x] T101 [P] Write `tests/unit/test_pyverilog_runner.py`:
  - `test_clean_tb_no_errors` — correct half_adder TB → `report.is_clean()`
  - `test_missing_port_flagged` — TB omits one port → PORT_BINDING_MISMATCH
  - `test_wrong_portname_flagged` — TB swaps port names → PORT_BINDING_MISMATCH
  - `test_parse_ok_on_valid_verilog` — `report.parse_ok == True`
  - `test_report_is_json_serialisable` — `json.dumps(report.to_dict())` succeeds

### Core implementation

- [x] T102 Implement `pipeline/analysis/pyverilog_runner.run(tb, dut, module_name)`:
  - Step 1: write to temp files, parse both with `vparser.parse()` (stderr suppressed)
  - Step 2: find DUT + TB module definitions in AST; auto-detect DUT name if not provided
  - Step 3: extract DUT ports with `_extract_ports()` (handles Ioport + Port styles)
  - Step 4: `_check_port_bindings()` — flags missing ports + unknown port names (AST)
  - Step 5: `_check_driven_observed()` — undriven inputs (assignment heuristic), unobserved outputs (comparison/if/display heuristic)
  - Step 6: VerilogDataflowAnalyzer deferred (heuristics cover key cases; dataflow reserved for Phase 3 when repair context is richer)
  - Step 7: `_check_sensitivity_lists()` — if DUT is SEQ and TB has no posedge always-blocks → SENSITIVITY_LIST_ERROR
  - Step 8: `_check_fdisplay()` — for SEQ circuits, every DUT output must appear in a display call

- [x] T103 [P] Create `pipeline/analysis/verible_runner.py`:
  - `verible-verilog-syntax --export_json -` subprocess; gracefully returns `parse_ok=False` when not installed

- [x] T104 Replace stub in `pipeline/nodes/pyverilog_analysis.py`:
  - Calls pyverilog_runner.run(); falls back to verible_runner if parse_ok=False; writes pyverilog_report dict to state; zero LLM calls

- [x] T105 Replace stub in `pipeline/nodes/error_reasoner.py`:
  - Snapshots error_report → last_error_report; skips LLM if pyverilog_report is clean (saves tokens); otherwise calls Sonnet with error_reasoner.j2

### Gate

- [x] T106 `pytest tests/unit/test_pyverilog_runner.py` — **8/8 pass** (5 CMB + 3 SEQ tests); full suite 17/17
- [x] T107 `python -m pipeline run --module half_adder --mode hybrid` — **status=success, eval0=True, eval1=True, eval2=1.00** — pyverilog_report populated, error_reasoner correctly skips LLM (clean report, zero extra tokens)
- [x] T108 Buggy-TB test — wrong port name → `port_errors=[('port_binding_mismatch', 'wrong_output'), ('port_binding_mismatch', 'sum')]` — non-empty ✅

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
