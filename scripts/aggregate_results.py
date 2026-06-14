"""
Aggregate per-run JSON files in results/ into a single summary.json.
Run after a full evaluation sweep.
"""

import json
import os
from collections import defaultdict


def aggregate(results_dir: str = "results") -> dict:
    runs = []
    for fname in os.listdir(results_dir):
        if not fname.endswith(".json") or fname == "summary.json":
            continue
        with open(os.path.join(results_dir, fname)) as f:
            runs.append(json.load(f))

    if not runs:
        print("No result files found.")
        return {}

    by_mode: dict[str, list] = defaultdict(list)
    for run in runs:
        mode = run.get("mode", "unknown")
        by_mode[mode].append(run)

    summary = {}
    for mode, mode_runs in by_mode.items():
        n = len(mode_runs)
        summary[mode] = {
            "n": n,
            "eval0_pass_rate": sum(r.get("eval0_pass", False) for r in mode_runs) / n,
            "eval1_pass_rate": sum(r.get("eval1_pass", False) for r in mode_runs) / n,
            "eval2_pass_rate": sum(r.get("eval2_pass_rate", 0) for r in mode_runs) / n,
            "mean_repair_iter": sum(r.get("repair_iter", 0) for r in mode_runs) / n,
            "mean_tokens_in":   sum(
                sum(c.get("tokens_in", 0) for c in r.get("llm_calls", []))
                for r in mode_runs
            ) / n,
            "mean_tokens_out": sum(
                sum(c.get("tokens_out", 0) for c in r.get("llm_calls", []))
                for r in mode_runs
            ) / n,
            "failure_stages": _count_field(mode_runs, "failure_stage"),
            "final_statuses": _count_field(mode_runs, "final_status"),
        }

    out_path = os.path.join(results_dir, "summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def _count_field(runs: list, field: str) -> dict:
    counts: dict = defaultdict(int)
    for r in runs:
        counts[str(r.get(field, "unknown"))] += 1
    return dict(counts)


if __name__ == "__main__":
    result = aggregate()
    print(json.dumps(result, indent=2))
