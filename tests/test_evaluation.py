"""Acceptance scoring must fail honestly without exposing provider/config secrets."""

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from triage import evaluation as ev
from triage.config import Settings
from triage.reasoning import CallRecord, ReasoningFailure

CASES = Path(__file__).parent / "fixtures/acceptance/cases.json"


def cases():
    return ev.CASES.validate_json(CASES.read_bytes())


def fake_reason(source, settings, client, *, record):
    case = next(c for c in cases() if c.source == source)
    count = 2 if source.status == "ready" else 0
    for stage in ["extract", "assess"][:count]:
        record(
            CallRecord(
                stage=stage, system_prompt="synthetic", user_prompt="synthetic", response="{}"
            )
        )
    return SimpleNamespace(
        analysis=SimpleNamespace(decision=case.expected, attempts=count),
        model_dump=lambda **kw: {"decision": case.expected},
    )


def test_complete_report_and_cli(monkeypatch, capsys):
    monkeypatch.setattr(ev, "reason", fake_reason)
    monkeypatch.setattr(ev.Settings, "from_env", lambda env: Settings())
    assert ev.main([str(CASES)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["passed"] == report["total"] == report["completed"] == 9
    assert sum(len(c["calls"]) for c in report["cases"]) == 14
    assert all("rubric" in c for c in report["cases"])


@pytest.mark.parametrize("failure", ["label", "count", "attempts", "empty-calls"])
def test_incorrect_model_result_fails(monkeypatch, failure):
    def incorrect(source, settings, client, *, record):
        result = fake_reason(source, settings, client, record=record)
        if failure == "label":
            result.analysis.decision = "review"
        elif failure == "attempts":
            result.analysis.attempts = 4
        return result

    monkeypatch.setattr(ev, "reason", incorrect)
    selected = cases()[:1]
    if failure == "count":

        def no_calls(source, settings, client, *, record):
            return fake_reason(source, settings, client, record=lambda c: None)

        monkeypatch.setattr(ev, "reason", no_calls)
    if failure == "empty-calls":
        selected = cases()[-1:]

        def extra_call(source, settings, client, *, record):
            record(CallRecord(stage="extract", system_prompt="x", user_prompt="x", response="x"))
            return fake_reason(source, settings, client, record=record)

        monkeypatch.setattr(ev, "reason", extra_call)
    with httpx.Client() as client:
        assert ev.evaluate(selected, Settings(), client)["passed"] == 0


def test_provider_failure_stops_and_preserves_failed_trace(monkeypatch, capsys):
    def unavailable(*args, record):
        record(CallRecord(stage="extract", system_prompt="x", user_prompt="x", response=None))
        raise ReasoningFailure("model_failed", ())

    monkeypatch.setattr(ev, "reason", unavailable)
    monkeypatch.setattr(ev.Settings, "from_env", lambda env: Settings())
    assert ev.main([str(CASES)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["completed"] == 1 and report["passed"] == 0 and report["total"] == 9
    assert report["cases"][0]["output"]["error"] == "model_failed"


@pytest.mark.parametrize(
    "payload",
    [None, "[]", "{invalid secret", "[" + CASES.read_text()[1:-2] + "," + CASES.read_text()[1:]],
)
def test_invalid_manifest(monkeypatch, tmp_path, capsys, payload):
    path = tmp_path / "cases.json"
    if payload is not None:
        path.write_text(payload)
    assert ev.main([str(path)]) == 2
    assert "secret" not in capsys.readouterr().err


def test_invalid_profile(monkeypatch, capsys):
    monkeypatch.setattr(
        ev.Settings,
        "from_env",
        lambda env: Settings(backend="openai", base_url="https://api.openai.com/v1"),
    )
    assert ev.main([str(CASES)]) == 2
    assert "Invalid evaluation" in capsys.readouterr().err
