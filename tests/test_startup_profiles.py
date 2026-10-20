"""Verify committed examples against real Compose and application settings."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from triage.config import Settings

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("mode", ["local", "frontier"])
def test_startup_profile_contract(mode):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COMPOSE_", "LLM_", "INGEST_"))
        and key not in {"OPENAI_API_KEY", "OLLAMA_MODEL", "POSTGRES_PASSWORD", "CONNECT_PORT"}
    }
    config = json.loads(
        subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                f".env.{mode}.example",
                "--profile",
                "tools",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
            timeout=20,
        ).stdout
    )
    services = config["services"]
    assert config["name"] == "redpanda"
    settings = services["model-check"]["environment"]
    assert {"redpanda", "postgres", "connect", "topics"} <= services.keys()
    if mode == "local":
        assert {"ollama", "model-init"} <= services.keys()
        assert settings["LLM_BACKEND"] == "ollama"
        assert settings["LLM_BASE_URL"] == "http://ollama:11434"
        assert settings["LLM_MODEL"] == services["model-init"]["command"][1]
        assert settings["OPENAI_API_KEY"] == ""
    else:
        assert not {"ollama", "model-init"} & services.keys()
        assert settings["LLM_BACKEND"] == "openai"
        assert settings["LLM_BASE_URL"] == "https://api.openai.com/v1"
        with pytest.raises(ValueError, match="requires OPENAI_API_KEY"):
            Settings.from_env(settings)
        settings["OPENAI_API_KEY"] = "test-only-not-a-real-key"
    Settings.from_env(settings)
