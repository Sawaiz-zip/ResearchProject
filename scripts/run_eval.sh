#!/usr/bin/env bash
# Full 156-module VerilogEval evaluation for a given ablation mode.
# Usage: ./scripts/run_eval.sh [baseline|compiler_only|pyverilog_only|hybrid]
set -euo pipefail

MODE=${1:-hybrid}
DATA_DIR="data/verilog_eval"

if [ ! -d "$DATA_DIR" ] || [ -z "$(ls -A $DATA_DIR)" ]; then
    echo "ERROR: $DATA_DIR is empty. Download VerilogEval dataset first."
    exit 1
fi

echo "Running full evaluation (mode=$MODE) ..."
for module_dir in "$DATA_DIR"/*/; do
    module=$(basename "$module_dir")
    python -m pipeline run --module "$module" --mode "$MODE" \
        --nl "$module_dir/description.txt" \
        --dut "$module_dir/dut.v"
done
echo "Evaluation complete. Aggregating results ..."
python scripts/aggregate_results.py
echo "Summary written to results/summary.json"
