# Quickstart: Repair Loop

## Prerequisites

- Project deps installed; iverilog **v13** on PATH.
- `.env` provider key for live runs (optional).

## Validate offline (no tokens)

```bash
pytest tests/unit/test_repair_node.py tests/integration/test_repair_loop.py -q
```

Expected: all four ablation modes behave per their definition; oscillation → `oscillated`;
persistent errors → `exhausted_iters`; a scripted fix → `success`; `repair_iter` never
exceeds the max; no LangGraph deadlock on loop re-entry.

## Validate live (a run that actually repairs)

```bash
# full_adder-style: description-only, model may produce a testbench with wrong
# expected values → HYBRID mode repairs it against the generated DUT
python -m pipeline run --nl desc.txt --module full_adder --mode hybrid
```

Expected summary shows `Repair iterations : >= 1` and (ideally) `Status : SUCCESS`, with
the result JSON containing a `repair_history` listing each iteration's feedback source.

## Compare ablation modes on one module

```bash
for m in baseline compiler_only pyverilog_only hybrid; do
  python -m pipeline run --module <faulty_module> --mode $m --run-id abl-$m
done
```

Expected: `baseline` has `repair_iter=0`; `hybrid` repairs on any error; the two single-source
modes repair only on their own source.

## What "done" looks like

- `pytest -q` green offline (repair tests included).
- `final_status` takes each of `success`, `oscillated`, `exhausted_iters` in the relevant tests.
- A live run reports ≥1 repair iteration with a populated `repair_history`.
