import json
from pathlib import Path

import pytest

from triage import cli
from triage.llm import ModelError


@pytest.fixture(autouse=True)
def clean_model_env(monkeypatch):
    for name in list(cli.os.environ):
        if name.startswith("LLM_") or name == "OPENAI_API_KEY":
            monkeypatch.delenv(name)


def test_check_config_is_offline_and_never_prints_secrets(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-not-to-print")
    assert cli.main(["check-config"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {"status": "valid", "backend": "ollama", "model": "qwen2.5:7b"}
    assert not output.err
    assert "secret-not-to-print" not in output.out


def test_bad_configuration_is_actionable_but_sanitized(monkeypatch, capsys):
    monkeypatch.setenv("LLM_BACKEND", "secret-invalid-setting")
    assert cli.main(["check-config"]) == 2
    error = capsys.readouterr().err
    assert "Invalid model configuration" in error
    assert "secret-invalid-setting" not in error


def test_smoke_records_prompt_and_response(monkeypatch, capsys):
    def fake_complete(settings, system, user, client):
        assert system == cli.SMOKE_SYSTEM
        assert "possible association" in user
        return "The edit strengthens an uncertain association into a causal claim."

    monkeypatch.setattr(cli, "complete", fake_complete)
    assert cli.main(["smoke-model"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["elapsed_seconds"] >= 0
    assert result["response"].startswith("The edit")
    assert result["user_prompt"] == cli.SMOKE_USER


def test_model_failure_has_nonzero_exit(monkeypatch, capsys):
    def fail(*args):
        raise ModelError("model HTTP status 429")

    monkeypatch.setattr(cli, "complete", fail)
    assert cli.main(["smoke-model"]) == 1
    assert capsys.readouterr().err.strip() == "model HTTP status 429"


def test_export_schemas_is_idempotent_and_independent_of_model_config(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("LLM_BACKEND", "invalid")
    for _ in range(2):
        assert cli.main(["schemas", "--output", str(tmp_path)]) == 0
    for name in ("edit-event", "analysis-result"):
        assert json.loads((tmp_path / f"{name}.v1.json").read_text()) == json.loads(
            Path(f"schemas/{name}.v1.json").read_text()
        )
    assert "Exported schema v1" in capsys.readouterr().out


def test_missing_command_is_a_usage_error():
    with pytest.raises(SystemExit) as error:
        cli.main([])
    assert error.value.code == 2
