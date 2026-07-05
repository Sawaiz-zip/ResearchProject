"""T012 — aggregator on synthetic result records (offline, no API)."""

import json
import os

import pytest

from pipeline.eval.aggregate import aggregate


def _write(d, name, rec, mtime=None):
    path = os.path.join(d, name)
    with open(path, "w") as f:
        json.dump(rec, f)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _rec(module, mode, **over):
    r = {
        "run_id": module + "_" + mode, "module_name": module, "mode": mode,
        "eval0_pass": True, "eval1_pass": True, "eval2_pass_rate": 1.0,
        "repair_iter": 0, "tokens_in_total": 100, "tokens_out_total": 50,
        "wall_clock_ms": 1000, "scenarios_passed": 5, "scenarios_total": 5,
        "final_status": "success", "failure_stage": None,
    }
    r.update(over)
    return r


def test_per_mode_figures(tmp_path):
    d = str(tmp_path)
    _write(d, "a.json", _rec("A", "baseline", eval1_pass=False, eval2_pass_rate=0.0,
                             tokens_in_total=100, tokens_out_total=50, wall_clock_ms=1000,
                             scenarios_passed=3, final_status="failed_eval1",
                             failure_stage="evaluate"))
    _write(d, "b.json", _rec("B", "baseline", tokens_in_total=200, tokens_out_total=80,
                             wall_clock_ms=2000))
    _write(d, "c.json", _rec("A", "hybrid", repair_iter=2, tokens_in_total=300,
                             tokens_out_total=120, wall_clock_ms=5000))

    s = aggregate(d)
    base = s["baseline"]
    assert base["n"] == 2
    assert base["eval0_pass_rate"] == 1.0
    assert base["eval1_pass_rate"] == 0.5
    assert base["eval2_pass_rate"] == 0.5
    assert base["mean_tokens_in"] == 150
    assert base["mean_tokens_out"] == 65
    assert base["mean_wall_clock_ms"] == 1500
    assert base["mean_scenarios_passed"] == 4
    assert base["final_statuses"]["failed_eval1"]["count"] == 1
    assert base["final_statuses"]["success"]["count"] == 1
    # failure-stage fractions per mode sum to 1.0
    assert abs(sum(v["fraction"] for v in base["failure_stages"].values()) - 1.0) < 1e-9
    assert base["failure_stages"]["evaluate"]["fraction"] == 0.5
    assert base["failure_stages"]["none"]["fraction"] == 0.5   # null → "none"

    hyb = s["hybrid"]
    assert hyb["n"] == 1
    assert hyb["mean_repair_iter"] == 2.0
    assert hyb["failure_stages"]["none"]["fraction"] == 1.0


def test_empty_dir_graceful(tmp_path):
    assert aggregate(str(tmp_path)) == {}


def test_malformed_record_skipped(tmp_path):
    d = str(tmp_path)
    _write(d, "good.json", _rec("A", "hybrid"))
    with open(os.path.join(d, "bad.json"), "w") as f:
        f.write("this is not json {{{")
    s = aggregate(d)
    assert s["hybrid"]["n"] == 1   # bad file skipped, not counted


def test_dedup_newest_wins(tmp_path):
    d = str(tmp_path)
    # Two records for the same (A, hybrid); newer file has eval1_pass=False.
    _write(d, "old.json", _rec("A", "hybrid", eval1_pass=True), mtime=1000)
    _write(d, "new.json", _rec("A", "hybrid", eval1_pass=False), mtime=2000)
    s = aggregate(d)
    assert s["hybrid"]["n"] == 1                  # de-duplicated
    assert s["hybrid"]["eval1_pass_rate"] == 0.0  # newest (False) won
