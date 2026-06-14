#!/usr/bin/env bash
# Run the pipeline on the 5-module CMB smoke set.
# Phase 1 gate: Eval0 >= 80%, Eval1 >= 50% required before Phase 2 begins.
set -euo pipefail

MODULES=("alu_1bit" "mux2to1" "half_adder" "comparator_2bit" "priority_encoder")
MODE=${1:-hybrid}

echo "Running CMB smoke set (mode=$MODE) ..."
for module in "${MODULES[@]}"; do
    echo "  -> $module"
    python -m pipeline run --module "$module" --mode "$MODE"
done
echo "Done. Check results/ for per-run JSON files."
