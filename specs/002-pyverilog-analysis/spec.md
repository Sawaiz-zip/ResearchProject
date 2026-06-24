# Feature Specification: Pyverilog Static Analysis Layer

**Feature Branch**: `phase-2-pyverilog`

**Created**: 2026-06-24

**Status**: In Progress

**Depends on**: `specs/001-langgraph-pipeline/` (Phase 1 gate must pass — ✅ done)

**Research context**: S6.ReKI.1 — primary research contribution (RQ1, RQ2)

---

## Goal

Add a deterministic, pre-simulation analysis layer between testbench generation
and Icarus Verilog evaluation. Pyverilog parses the generated testbench + golden
DUT together and checks for structural errors without running any simulation.
The structured error report is then fed to an LLM (Sonnet) which translates it
into actionable fix instructions.

This is the feature that differentiates this project from AutoBench, which has
no pre-simulation checking at all.

---

## User Story 2 — Pyverilog Static Analysis & Error Reporting (P2)

After testbench generation, the system runs Pyverilog on the TB + golden DUT
pair and produces a structured error report:
`{error_type, affected_signal, line, suggested_fix, severity}`

covering:
- Port-binding mismatches (wrong port name in DUT instantiation)
- Missing port connections (DUT port not connected at all)
- Unobserved outputs (TB never checks a DUT output)
- Undriven inputs (TB never drives a DUT input)
- Sensitivity list errors (wrong clocking in SEQ always blocks)
- Missing `$fdisplay` for SEQ output signals

**Why P2**: Primary research contribution (RQ1, RQ2). Without it the project
is a reimplementation of AutoBench.

**Independent Test**: Feed a hand-crafted buggy testbench (wrong port name) into
`pyverilog_runner.run()` alone and assert the error report contains
`error_type: port_binding_mismatch`.

---

## Acceptance Scenarios

1. **Given** a testbench that swaps two DUT port names (e.g., connects `sum`
   to `cout` and vice versa), **When** `pyverilog_runner.run()` is called,
   **Then** `pyverilog_report.port_errors` is non-empty and contains
   `error_type="port_binding_mismatch"`.

2. **Given** a testbench that never drives one of the DUT inputs,
   **When** `pyverilog_runner.run()` is called,
   **Then** `pyverilog_report.dataflow_errors` contains `error_type="undriven_input"`.

3. **Given** a syntactically invalid TB that Pyverilog cannot parse,
   **When** `pyverilog_analysis_node` runs,
   **Then** Verible is tried as fallback; if Verible also fails,
   `pyverilog_report.parse_ok=False` and the node returns without crashing.

4. **Given** a fully correct testbench, **When** the node runs,
   **Then** `pyverilog_report.is_clean()` returns True and `error_report` is
   empty — the pipeline proceeds directly to evaluate without repair.

5. **Given** a non-empty `pyverilog_report`, **When** `error_reasoner_node`
   runs, **Then** it calls Sonnet with `error_reasoner.j2` and writes a
   `list[dict]` to `error_report` — each item has `error_type`, `affected_signal`,
   `line`, `suggested_fix`, `severity`.

---

## What Pyverilog Checks (Scope for Phase 2)

| Check | Method | Always / SEQ-only |
|---|---|---|
| Port binding — all DUT ports connected | AST: walk `Instance.portlist` | Always |
| Port binding — port names match DUT | AST: compare `PortArg.portname` vs DUT portlist | Always |
| Undriven inputs | AST: check DUT inputs appear in TB reg declarations + drive logic | Always |
| Unobserved outputs | AST: check DUT outputs appear in TB comparisons / prints | Always |
| Sensitivity list | AST: walk `Always.sens_list`, verify posedge clk present | SEQ only |
| `$fdisplay` presence | AST: walk for `SystemCall` with display-family name | SEQ only |

Dataflow analysis (VerilogDataflowAnalyzer) is attempted on the DUT only.
`FormatError` (async reset) is caught; analysis degrades gracefully to AST-only.

---

## Out of Scope for Phase 2

- Full repair loop (Phase 3)
- SEQ `$fdisplay` standardiser (Phase 3)
- Verible deep semantic analysis (only syntax check as fallback)
- Precision/recall measurement on full VerilogEval set (Phase 4)

---

## Functional Requirements (Phase 2 additions)

- **FR-P2-001**: `pyverilog_runner.run(tb, dut, module_name)` must return a
  `PyverilogReport` without raising for any valid Verilog input.
- **FR-P2-002**: If Pyverilog's AST parser raises, the node must try Verible;
  if Verible also fails, set `parse_ok=False` and return.
- **FR-P2-003**: `error_reasoner_node` must only call the LLM when
  `pyverilog_report` is non-empty (i.e., at least one error found). If the
  report is clean, skip the LLM call and set `error_report=[]`.
- **FR-P2-004**: All Pyverilog analysis is deterministic — zero LLM calls in
  `pyverilog_analysis_node`.
- **FR-P2-005**: `pyverilog_report` must be JSON-serialisable (`.to_dict()`).

---

## Success Criteria (Phase 2 gate)

- `pytest tests/unit/test_pyverilog_runner.py` — all tests pass
- Hand-crafted buggy TB with wrong port name → `error_report` non-empty
- Clean TB (half_adder passing TB from smoke test) → `error_report` empty
- Full pipeline smoke run on 5 CMB fixtures still passes at same or better rate
