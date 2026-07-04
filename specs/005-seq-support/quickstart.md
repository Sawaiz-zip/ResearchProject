# Quickstart: SEQ Support

## Prerequisites

- Project deps installed; iverilog **v13** on PATH.
- `.env` provider key for live runs (optional).

## Validate offline (no tokens)

```bash
pytest tests/unit/test_fdisplay_inserter.py tests/integration/test_seq_routing.py -q
```

Expected: standardiser inserts observation for missing outputs, is idempotent, no-ops when all
outputs are already observed, is fail-safe on garbage, and never emits a DUT. SEQ runs pass
through `standardise`; CMB runs do not; both complete without deadlock.

## Validate the CMB path is unaffected

```bash
pytest tests/integration/test_pipeline_flow_mocked.py -q   # existing CMB coverage still green
```

## Validate a sequential run (live)

```bash
python -m pipeline run --module dff --mode hybrid
```

Expected: classified `SEQ`, a clocked testbench generated, standardiser ensures outputs are
observed, run reaches an evaluation result. The summary shows `circuit_type SEQ`.

## Run the (few) live tests

```bash
pytest -m live -q     # includes the SEQ live test; skipped automatically without a key
```

## What "done" looks like

- `pytest -q` green offline (standardiser + routing tests included; CMB unchanged).
- A SEQ fixture runs end-to-end and reaches a result.
- Running the standardiser twice yields identical output.
