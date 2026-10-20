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
    for name in ("edit-event", "analysis-result", "enrichment-result"):
        assert json.loads((tmp_path / f"{name}.v1.json").read_text()) == json.loads(
            Path(f"schemas/{name}.v1.json").read_text()
        )
    assert "Exported schema v1" in capsys.readouterr().out


def test_missing_command_is_a_usage_error():
    with pytest.raises(SystemExit) as error:
        cli.main([])
    assert error.value.code == 2


FIXTURES = Path("tests/fixtures/enrichment")


def test_enrich_fixture_is_offline_and_independent_of_model_config(monkeypatch, capsys):
    monkeypatch.setenv("LLM_BACKEND", "invalid")
    monkeypatch.setattr(cli.httpx, "Client", lambda: pytest.fail("must remain offline"))
    assert (
        cli.main(
            [
                "enrich",
                "--event",
                str(FIXTURES / "belle-event.json"),
                "--fixture-response",
                str(FIXTURES / "belle-response.json"),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ready" and result["source"] == "fixture"
    assert result["attempts"] == 0
    assert "Susan Egan" in result["evidence"][0]["before"]
    assert "Susan Egan" not in result["evidence"][0]["after"]


def test_enrich_live_cli_uses_real_client_code_with_mock_transport(monkeypatch, capsys):
    client = cli.httpx.Client(
        transport=cli.httpx.MockTransport(
            lambda _: cli.httpx.Response(
                200, content=(FIXTURES / "belle-response.json").read_bytes()
            )
        )
    )
    monkeypatch.setattr(cli.httpx, "Client", lambda: client)
    assert cli.main(["enrich", "--event", str(FIXTURES / "belle-event.json")]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["source"] == "wikipedia" and result["attempts"] == 1
    assert client.is_closed


def test_enrich_unavailable_exits_nonzero_with_inspectable_json(capsys):
    assert (
        cli.main(
            [
                "enrich",
                "--event",
                str(FIXTURES / "belle-event.json"),
                "--fixture-response",
                str(FIXTURES / "missing-response.json"),
            ]
        )
        == 1
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "revision_unavailable" and not result["evidence"]


@pytest.mark.parametrize(
    "kind", ["missing-event", "bad-json", "oversized-event", "missing-fixture"]
)
def test_enrich_bad_files_are_bounded_and_sanitized(kind, tmp_path, capsys):
    event = tmp_path / "event.json"
    event.write_bytes((FIXTURES / "belle-event.json").read_bytes())
    fixture = FIXTURES / "belle-response.json"
    if kind == "missing-event":
        event.unlink()
    elif kind == "bad-json":
        event.write_text("PRIVATE")
    elif kind == "oversized-event":
        event.write_bytes(event.read_bytes().ljust(8193))
    else:
        fixture = tmp_path / "PRIVATE"
    assert cli.main(["enrich", "--event", str(event), "--fixture-response", str(fixture)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "check file paths and the event schema" in output.err
    assert "PRIVATE" not in output.err
