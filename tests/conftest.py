"""Disposable real infrastructure shared by integration tests."""

import os
import subprocess
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def compose():
    project = "triage-test-" + uuid.uuid4().hex[:10]
    base = [
        "docker",
        "compose",
        "--env-file",
        "/dev/null",
        "-f",
        "compose.infrastructure.yml",
        "-p",
        project,
    ]
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("LLM_", "INGEST_", "COMPOSE_"))
        and name not in {"OPENAI_API_KEY", "CONNECT_PORT"}
    }
    env["POSTGRES_PASSWORD"] = "test-only"
    env["CONNECT_PORT"] = "0"

    def run(*args, input=None, timeout=180, env_overrides=None):
        return subprocess.run(
            [*base, *args],
            cwd=ROOT,
            env={**env, **(env_overrides or {})},
            input=input,
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout,
        ).stdout

    try:
        run("up", "-d", "--wait", "--wait-timeout", "120", "redpanda", "postgres")
        yield run
    finally:
        # This unique project was created by this test; no shared/user volumes are removed.
        subprocess.run(
            [*base, "down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            timeout=120,
        )
