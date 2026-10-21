"""Real infrastructure behavior checks."""

import json
import subprocess
from time import monotonic, sleep

import pytest

pytestmark = pytest.mark.integration


def test_hosted_stack_has_no_local_inference_service(compose):
    services = set(compose("--profile", "tools", "config", "--services").splitlines())
    assert services == {
        "redpanda",
        "postgres",
        "topics",
        "connect",
        "fixture-source",
        "model-check",
        "worker",
        "db-migrate",
        "sink",
        "api",
    }


def test_topics_initialize_twice_and_records_roundtrip(compose):
    for _ in range(2):
        compose("run", "--rm", "topics")
    topics = json.loads(
        compose("exec", "-T", "redpanda", "rpk", "topic", "list", "--format", "json")
    )
    assert {t["name"] for t in topics} == {
        "edits",
        "results",
        "ingest-errors",
        "processing-errors",
        "sink-errors",
    }
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


def test_one_shot_helpers_complete_without_persistent_volumes(compose):
    compose("up", "-d", "topics", "db-migrate")
    containers = {
        service: compose("ps", "-aq", service).strip() for service in ["topics", "db-migrate"]
    }
    deadline = monotonic() + 30
    for service, container in containers.items():
        while True:
            state = json.loads(
                subprocess.run(
                    ["docker", "inspect", container],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                ).stdout
            )[0]
            if state["State"]["Status"] == "exited":
                break
            assert monotonic() < deadline, f"{service} did not finish"
            sleep(0.2)
        assert state["State"]["ExitCode"] == 0
        assert not any(mount["Type"] == "volume" for mount in state["Mounts"]), (
            f"{service} creates unused persistent storage that ordinary shutdown leaves behind"
        )
