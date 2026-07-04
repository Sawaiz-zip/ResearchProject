# Quickstart: Evaluation Harness

## Prerequisites

- Project deps installed; iverilog v13; `.env` provider key for real sweeps.

## Validate offline (no tokens)

```bash
pytest tests/unit/test_aggregate.py tests/unit/test_harness_guard.py \
       tests/integration/test_harness_smoke_mocked.py -q
```

Expected: aggregation figures match hand-computed values on synthetic records; the runner
refuses an over-threshold sweep without opt-in and makes no API calls; a tiny mocked sweep
produces mode-tagged result records the aggregator groups correctly.

## See the budget guard (no tokens)

```bash
python scripts/run_eval.py --modules verilogeval:156        # prints estimate (624 runs) and REFUSES
python scripts/run_eval.py --modules verilogeval:156 --yes  # would proceed (don't, on free tier)
```

## Run the default small sweep (spends tokens — 20 runs)

```bash
python scripts/run_eval.py                # 5 CMB fixtures × 4 modes = 20 runs
# → writes results/<run_id>.json per run, then results/summary.json + a printed table
```

## Aggregate existing results only (no tokens)

```bash
python scripts/aggregate_results.py       # re-aggregates whatever is already in results/
```

## What "done" looks like

- Offline tests green; the guard blocks large sweeps without `--yes`.
- A default sweep produces `summary.json` with one entry per mode and a readable table showing
  Eval0/1/2 rates, mean repair/tokens/time, final-status distribution, and per-stage failure
  attribution.
- Every result record carries its `mode` and `module_name`.
