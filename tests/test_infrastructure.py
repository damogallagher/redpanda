"""Real infrastructure behavior checks."""

import json

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
    }


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
