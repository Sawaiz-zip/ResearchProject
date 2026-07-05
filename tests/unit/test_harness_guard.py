"""T013 — batch-runner budget guard (offline; injected invoke, no API)."""

from pipeline.config import AblationMode
from pipeline.eval import harness
from pipeline.eval.harness import (
    estimate_runs, run_sweep, SAFE_THRESHOLD, _is_daily_rate_limit,
)

_MODES = [AblationMode.BASELINE, AblationMode.HYBRID]


class _FakeRateLimitError(Exception):
    pass


def test_is_daily_rate_limit_detection():
    daily = _FakeRateLimitError(
        "Error code: 429 - Rate limit reached ... tokens per day (TPD): Limit 100000"
    )
    per_min = _FakeRateLimitError(
        "Error code: 429 - Rate limit reached ... tokens per minute (TPM): Limit 6000"
    )
    assert _is_daily_rate_limit(daily) is True
    assert _is_daily_rate_limit(per_min) is False
    assert _is_daily_rate_limit(ValueError("some other error")) is False


def test_sweep_aborts_on_daily_rate_limit(tmp_path):
    calls = {"n": 0}

    def boom(state, config):
        calls["n"] += 1
        raise _FakeRateLimitError(
            "429 tokens per day (TPD): Limit 100000, Used 99999"
        )

    # 2 modules × 2 modes = 4 runs, but the daily limit should abort after the 1st.
    result = run_sweep(["half_adder", "mux2to1"], _MODES, opt_in=True,
                       results_dir=str(tmp_path), graph_invoke=boom)
    assert result["aborted"] is True
    assert result["reason"] == "daily_rate_limit"
    assert calls["n"] == 1          # stopped immediately, did not grind through the rest
    assert result["ran"] == 0


def test_estimate_runs():
    assert estimate_runs(["a", "b", "c"], _MODES) == 6
    assert estimate_runs(["a", "b", "c"], _MODES, limit=1) == 2


def test_refuses_over_threshold_without_opt_in(monkeypatch, tmp_path):
    calls = {"n": 0}

    def spy_invoke(state, config):
        calls["n"] += 1
        return state

    # A big selection: enough modules × 4 modes to exceed SAFE_THRESHOLD.
    modules = [f"m{i}" for i in range(SAFE_THRESHOLD + 4)]
    result = run_sweep(modules, harness.ALL_MODES, opt_in=False,
                       results_dir=str(tmp_path), graph_invoke=spy_invoke)
    assert result["refused"] is True
    assert result["ran"] == 0
    assert calls["n"] == 0                    # NOT a single run executed


def test_proceeds_with_opt_in(monkeypatch, tmp_path):
    calls = {"n": 0}

    def spy_invoke(state, config):
        calls["n"] += 1
        return state

    # Reuse a real module so load_module resolves; 1 module × 2 modes = 2 runs.
    result = run_sweep(["half_adder"], _MODES, opt_in=True,
                       results_dir=str(tmp_path), graph_invoke=spy_invoke)
    assert result["refused"] is False
    assert result["ran"] == 2
    assert calls["n"] == 2


def test_limit_bounds_the_sweep(tmp_path):
    calls = {"n": 0}

    def spy_invoke(state, config):
        calls["n"] += 1
        return state

    # 5 modules but limit=1 → 1 module × 2 modes = 2 runs, under threshold.
    result = run_sweep(["half_adder", "mux2to1", "alu_1bit", "comparator_2bit",
                        "priority_encoder"], _MODES, limit=1, opt_in=False,
                       results_dir=str(tmp_path), graph_invoke=spy_invoke)
    assert result["refused"] is False
    assert calls["n"] == 2
