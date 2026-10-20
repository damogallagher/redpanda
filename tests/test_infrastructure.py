"""Real infrastructure tests; each run owns and cleans up its own volumes."""

import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
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
        if not name.startswith("LLM_") and name != "OPENAI_API_KEY"
    }
    env["POSTGRES_PASSWORD"] = "test-only"

    def run(*args, input=None, timeout=180):
        return subprocess.run(
            [*base, *args],
            cwd=ROOT,
            env=env,
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


def test_hosted_stack_has_no_local_inference_service(compose):
    services = set(compose("--profile", "tools", "config", "--services").splitlines())
    assert services == {"redpanda", "postgres", "topics", "model-check"}


def test_topics_initialize_twice_and_records_roundtrip(compose):
    for _ in range(2):
        compose("run", "--rm", "topics")
    topics = json.loads(
        compose("exec", "-T", "redpanda", "rpk", "topic", "list", "--format", "json")
    )
    assert {t["name"] for t in topics} == {"edits", "results", "ingest-errors", "processing-errors"}
    assert all(t["partitions"] == 1 and t["replicas"] == 1 for t in topics)
    compose(
        "exec",
        "-T",
        "redpanda",
        "rpk",
        "topic",
        "produce",
        "edits",
        input='{"fixture":"phase-1"}\n',
    )
    output = compose(
        "exec",
        "-T",
        "redpanda",
        "rpk",
        "topic",
        "consume",
        "edits",
        "--num",
        "1",
        "--format",
        "%v",
        timeout=20,
    )
    assert json.loads(output) == {"fixture": "phase-1"}


def test_database_schema_initialization_is_idempotent_and_persistent(compose):
    for _ in range(2):
        compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "triage",
            "-d",
            "triage",
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            "/docker-entrypoint-initdb.d/001-foundation.sql",
        )
    compose("restart", "postgres")
    compose("up", "-d", "--wait", "--wait-timeout", "120", "postgres")
    count = compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "triage",
        "-d",
        "triage",
        "-Atc",
        "SELECT count(*) FROM schema_migrations WHERE version = 1",
    )
    assert count.strip() == "1"
