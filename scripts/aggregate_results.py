"""
Back-compat wrapper — re-aggregate whatever is already in results/ into summary.json.
The implementation lives in pipeline/eval/aggregate.py (importable + unit-tested).
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from pipeline.eval.aggregate import aggregate, print_summary_table


if __name__ == "__main__":
    summary = aggregate()
    print_summary_table(summary)
    print(json.dumps(summary, indent=2))
