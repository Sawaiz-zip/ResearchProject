"""T022 — configurable temperature (Constitution IV, v1.1.0)."""

import pytest

from pipeline import llm


def test_resolve_precedence_arg_wins(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "0.3")
    assert llm.resolve_temperature(0.9) == 0.9  # explicit arg beats env


def test_resolve_env_used_when_no_arg(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "0.42")
    assert llm.resolve_temperature() == 0.42


def test_resolve_default_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
    assert llm.resolve_temperature() == 0.7


def test_resolve_bad_env_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "not-a-number")
    assert llm.resolve_temperature() == 0.7


def test_llm_call_logs_temperature(monkeypatch):
    """llm_call must record the resolved temperature in the log entry."""
    captured = {}

    def fake_provider():
        return "anthropic"

    def fake_anthropic(model, prompt, max_tokens, max_retries, log, temperature):
        captured["temperature"] = temperature
        log["tokens_in"] = 1
        log["tokens_out"] = 1
        return "ok", log

    monkeypatch.setattr(llm, "_provider", fake_provider)
    monkeypatch.setattr(llm, "_call_anthropic", fake_anthropic)
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)

    text, log = llm.llm_call(
        node="classify", model="m", prompt="p", run_id="r", temperature=0.55
    )
    assert log["temperature"] == 0.55
    assert captured["temperature"] == 0.55
