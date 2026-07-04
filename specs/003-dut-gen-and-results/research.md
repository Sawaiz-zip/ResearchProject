# Phase 0 Research: DUT Generation, Temperature, Results

All Technical Context items were resolvable from the existing codebase; no external research needed. Decisions below resolve the design questions raised by the spec.

## D1 — Where does `gen_dut` sit and what feeds it?

- **Decision**: Insert `gen_dut` as a node between `classify` and `extract_spec`. It consumes `nl_description` + `circuit_type` and writes `dut_rtl`.
- **Rationale**: Classification needs only the description (FR-002) and must run first so the DUT generator knows whether to emit clocked logic. `extract_spec` and all later stages then read the generated DUT.
- **Alternatives considered**: Generating the DUT before classification — rejected because classification is cheaper (Haiku) and the DUT prompt benefits from knowing CMB/SEQ. Generating DUT inside `extract_spec` — rejected, violates one-node-one-responsibility (Principle I).

## D2 — How to keep golden DUT for evaluation without changing generation?

- **Decision**: `golden_dut` stays in state but becomes **optional** and is used **only** in `evaluate_node`. Generation reads `dut_rtl`. `evaluate_node` picks `golden_dut` if non-empty, else `dut_rtl`, and records the choice in `eval_dut_source` ("golden" | "generated").
- **Rationale**: Satisfies FR-006/007/008 and User Story 2 without branching the generation graph.
- **Alternatives considered**: A separate "benchmark graph" — rejected as duplicated control flow (Principle I, Workflow rule 5 "single config flag").

## D3 — Temperature configuration surface

- **Decision**: `llm_call(..., temperature: float | None = None)`. Resolution order: explicit arg → `LLM_TEMPERATURE` env → `0.7`. Resolved value passed to both Anthropic and OpenAI-compat calls and written into the log entry as `temperature`. A single helper `resolve_temperature()` centralises this.
- **Rationale**: Per-call override kept (a node could still request low temperature for JSON) while the default is non-zero and env-controlled (FR-009/010).
- **Alternatives considered**: Hardcoding 0.7 — rejected, not configurable. Per-node config in `PipelineConfig` only — kept as the default source but env override is needed for quick experiments without code edits.

## D4 — Robustness at temperature > 0

- **Decision**: Rely on existing tolerant helpers (`extract_json`, `extract_code_block`) plus the existing retry loop. Add: nodes that parse JSON already catch parse errors and fall back (classify → keyword scan, extract_spec → `{}`). Confirm every LLM-consuming node has a fallback; `gen_dut` falls back to returning raw text (Verilog is not JSON, so `extract_code_block` is the tolerant path).
- **Rationale**: FR-011. No new retry machinery required; the guarantee is "a malformed response never aborts the run".
- **Alternatives considered**: JSON schema-enforced decoding — not available across all free-tier providers; rejected for portability.

## D5 — Parsing simulator output into per-scenario results

- **Decision**: `parse_scenarios(sim_output)` splits on lines and matches the established markers `^PASS:\s*<name>` / `^FAIL:\s*<name>` (the same convention `gen_driver.j2` already enforces and `icarus.simulate_tb` keys on via `\bFAIL\s*:`). Returns `[{name, passed}]`. Debug lines that merely contain "fail" without the `PASS:`/`FAIL:` prefix are ignored (FR-013).
- **Rationale**: Reuses the existing, already-tested marker convention — no prompt changes needed.
- **Alternatives considered**: Structured JSON emission from the testbench — rejected, would require regenerating all driver prompts and risks compile issues.

## D6 — Console summary location

- **Decision**: New `pipeline/reporting.py` with `parse_scenarios()` and `print_run_summary(result: dict)`. Called from `__main__.py` after `graph.invoke`, reading the same dict written to `results/<run_id>.json`. Token totals summed from `llm_calls`.
- **Rationale**: Keeps `evaluate_node` focused on evaluation; presentation is separate. Summary and file share one source of truth.
- **Alternatives considered**: Printing inside `evaluate_node` — rejected, mixes presentation into a graph node and wouldn't run for CLI-level context (wall time, mode).

## D7 — Test isolation without spending tokens

- **Decision**: `tests/conftest.py` provides a `fake_llm` fixture that monkeypatches `pipeline.llm.llm_call` to return canned `(text, log)` tuples keyed by the `node` argument. All unit + flow tests use it → zero API calls (FR-016/017). Live tests marked `@pytest.mark.live` and guarded by `skipif` on missing key + registered marker in `pyproject.toml` (FR-018).
- **Rationale**: One fixture covers every node; keying by `node` lets one graph run traverse the whole pipeline deterministically.
- **Alternatives considered**: Recording/replaying real responses (VCR-style) — heavier, and canned responses are sufficient and clearer for a research codebase.

## D8 — iverilog version

- **Decision**: Stay on iverilog v13 (installed, current stable). No code change; `icarus.py` invokes `iverilog`/`vvp` from PATH with `-g2012`.
- **Rationale**: Homebrew ships only v13; no specific v13 bug identified. Confirmed with user.
