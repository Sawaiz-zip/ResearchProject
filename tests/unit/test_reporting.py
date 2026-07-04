"""T024 — reporting: parse_scenarios + print_run_summary."""

from pipeline.reporting import parse_scenarios, print_run_summary


def test_parse_counts_pass_and_fail():
    out = parse_scenarios("PASS: alpha\nFAIL: beta\nPASS: gamma\n")
    assert out == [
        {"name": "alpha", "passed": True},
        {"name": "beta", "passed": False},
        {"name": "gamma", "passed": True},
    ]


def test_parse_ignores_debug_lines():
    # 'the operation failed' must NOT be counted; only PASS:/FAIL: markers.
    out = parse_scenarios("the operation failed unexpectedly\nPASS: only_one\n")
    assert out == [{"name": "only_one", "passed": True}]


def test_parse_empty():
    assert parse_scenarios("") == []
    assert parse_scenarios(None) == []


def test_summary_renders_with_empty_data(capsys):
    result = {
        "run_id": "abc",
        "module_name": "m",
        "circuit_type": "CMB",
        "nl_description": "",
        "eval0_pass": False,
        "eval1_pass": False,
        "eval2_pass_rate": 0.0,
        "final_status": "failed_compile",
        "llm_calls": [],
        "scenario_results": [],
        "wall_clock_ms": 0,
    }
    print_run_summary(result)  # must not raise
    text = capsys.readouterr().out
    assert "0 / 0 scenarios passed" in text
    assert "FAILED_COMPILE" in text


def test_summary_lists_failing_scenarios(capsys):
    result = {
        "run_id": "abc", "module_name": "m", "circuit_type": "CMB",
        "nl_description": "adder", "eval0_pass": True, "eval1_pass": False,
        "eval2_pass_rate": 0.5, "final_status": "failed_eval1",
        "eval_dut_source": "generated",
        "scenario_results": [
            {"name": "zero", "passed": True},
            {"name": "both", "passed": False},
        ],
        "scenarios_passed": 1, "scenarios_total": 2,
        "tokens_in_total": 100, "tokens_out_total": 50,
        "llm_calls": [], "wall_clock_ms": 1234,
    }
    print_run_summary(result)
    text = capsys.readouterr().out
    assert "1 / 2 scenarios passed" in text
    assert "both" in text
    assert "150" in text  # total tokens
