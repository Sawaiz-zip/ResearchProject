"""
T014 — run_sweep over 1 fixture × 2 modes, fully offline (fake_llm + mock_icarus).
Asserts each run writes a mode-tagged result and the aggregator groups by mode.
"""

import json
import os

from pipeline.config import AblationMode
from pipeline.eval.aggregate import aggregate
from pipeline.eval.harness import run_sweep

_MODES = [AblationMode.BASELINE, AblationMode.HYBRID]


def test_sweep_writes_mode_tagged_results(fake_llm, mock_icarus, tmp_path):
    results_dir = str(tmp_path)
    out = run_sweep(["half_adder"], _MODES, results_dir=results_dir)

    assert out["refused"] is False
    assert out["ran"] == 2

    files = [f for f in os.listdir(results_dir)
             if f.endswith(".json") and f != "summary.json"]
    assert len(files) == 2
    modes_seen = set()
    for f in files:
        rec = json.loads((tmp_path / f).read_text())
        assert rec["module_name"] == "half_adder"
        assert rec["mode"] in ("baseline", "hybrid")
        modes_seen.add(rec["mode"])
    assert modes_seen == {"baseline", "hybrid"}

    summary = aggregate(results_dir)
    assert set(summary.keys()) == {"baseline", "hybrid"}
    assert summary["baseline"]["n"] == 1
    assert summary["hybrid"]["n"] == 1
