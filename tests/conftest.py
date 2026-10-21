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
        if not name.startswith(
            ("LLM_", "INGEST_", "COMPOSE_", "KAFKA_", "WORKER_", "SINK_", "PG", "TRIAGE_")
        )
        and name not in {"OPENAI_API_KEY", "CONNECT_PORT", "API_PORT"}
    }
    env["POSTGRES_PASSWORD"] = "test-only:p@ss/word"
    env["CONNECT_PORT"] = "0"
    env["API_PORT"] = "0"
    env["SINK_PORT"] = "0"

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
        # Compose down ignores inactive profiles, even with --remove-orphans.
        run("--profile", "tools", "down", "--volumes", "--remove-orphans", timeout=120)
        for command in (["ps", "-aq"], ["volume", "ls", "-q"], ["network", "ls", "-q"]):
            remaining = subprocess.run(
                ["docker", *command, "--filter", f"label=com.docker.compose.project={project}"],
                cwd=ROOT,
                env=env,
                text=True,
                check=True,
                capture_output=True,
                timeout=20,
            ).stdout.strip()
            assert not remaining, f"Test-owned resources remain after cleanup: {remaining}"
