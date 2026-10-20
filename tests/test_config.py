import pytest
from pydantic import ValidationError

from triage.config import Settings


def test_local_defaults_and_explicit_overrides():
    settings = Settings.from_env({})
    assert (settings.backend, settings.model, settings.base_url) == (
        "ollama",
        "qwen2.5:7b",
        "http://localhost:11434",
    )
    configured = Settings.from_env(
        {
            "LLM_MODEL": "custom:tag",
            "LLM_TIMEOUT_SECONDS": "30",
            "LLM_MAX_TOKENS": "256",
            "LLM_BASE_URL": "http://ollama:11434",
        }
    )
    assert configured.model == "custom:tag"
    assert configured.timeout_seconds == 30
    assert configured.max_tokens == 256


def test_hosted_requires_key_and_has_explicit_defaults():
    with pytest.raises(ValidationError, match="requires OPENAI_API_KEY"):
        Settings.from_env({"LLM_BACKEND": "openai"})
    hosted = Settings.from_env({"LLM_BACKEND": "openai", "OPENAI_API_KEY": "test-only"})
    assert hosted.model == "gpt-6.1-sol"
    assert hosted.base_url == "https://api.openai.com/v1"
    assert "test-only" not in repr(hosted)
    assert "test-only" not in hosted.model_dump_json()


@pytest.mark.parametrize(
    "overrides",
    [
        {"LLM_BACKEND": "unknown"},
        {"LLM_MODEL": ""},
        {"LLM_MODEL": "a b"},
        {"LLM_TIMEOUT_SECONDS": "0"},
        {"LLM_TIMEOUT_SECONDS": "301"},
        {"LLM_TIMEOUT_SECONDS": "nan"},
        {"LLM_TIMEOUT_SECONDS": "inf"},
        {"LLM_MAX_TOKENS": "0"},
        {"LLM_MAX_TOKENS": "8193"},
        {"LLM_MAX_TOKENS": "no"},
        {"LLM_BASE_URL": "file:///tmp/model"},
        {"LLM_BASE_URL": "http:///path"},
        {"LLM_BASE_URL": "http://localhost:99999"},
        {"LLM_BASE_URL": "http://localhost:not-a-port"},
        {"LLM_BASE_URL": "http://localhost:11434\n"},
        {"LLM_BASE_URL": "http://user:password@localhost:11434"},
        {"LLM_BASE_URL": "http://localhost:11434?token=bad"},
        {"LLM_BASE_URL": "http://localhost:11434#fragment"},
        {"LLM_BACKEND": "openai", "LLM_BASE_URL": "http://api.openai.com/v1"},
        {"LLM_BACKEND": "openai", "LLM_BASE_URL": "https://other.example/v1"},
        {"LLM_BACKEND": "openai", "OPENAI_API_KEY": "   "},
    ],
)
def test_invalid_configuration_fails_closed(overrides):
    with pytest.raises(ValidationError):
        Settings.from_env({"OPENAI_API_KEY": "test-only", **overrides})


def test_settings_are_immutable_and_do_not_accept_misspelled_fields():
    with pytest.raises(ValidationError):
        Settings(extra_typo=True)
    with pytest.raises(ValidationError):
        Settings().model = "changed"
