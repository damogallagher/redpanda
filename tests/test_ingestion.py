"""Run the actual HTTP scanner, processors, and output against a real broker."""

import hashlib
import json
from pathlib import Path

import pytest

from triage.schema import EditEvent

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parent / "fixtures" / "ingestion"


def consume(compose, topic):
    """Read the complete current topic, so unexpected extra records fail assertions."""
    output = compose(
        "exec",
        "-T",
        "redpanda",
        "rpk",
        "topic",
        "consume",
        topic,
        "--offset",
        ":end",
        "--format",
        "json",
        "--pretty-print=false",
        timeout=20,
    )
    return [json.loads(line) for line in output.splitlines()]


def test_http_fixture_projection_routing_and_replay(compose):
    compose("run", "--rm", "topics")
    compose("up", "-d", "--wait", "fixture-source")
    expected_edits = json.loads((FIXTURES / "expected-edits.json").read_text())
    expected_errors = []
    # Replay is intentionally allowed: stable keys let later phases deduplicate.
    for index, filename in enumerate(["phase-2.sse", "phase-2.sse", "phase-2-crlf.sse"], 1):
        compose(
            "run",
            "--rm",
            "--no-deps",
            "-e",
            "INGEST_STREAM_URL=http://fixture-source:8080/" + filename,
            "-e",
            "INGEST_RECONNECT=false",
            "-e",
            "INGEST_SAMPLE_ALL=true",
            "-e",
            "INGEST_SOURCE=fixture",
            "connect",
        )
        expected_error = json.loads((FIXTURES / "expected-error.json").read_text())
        raw = (FIXTURES / filename).read_bytes()
        invalid = raw[raw.rfind(b"event: message") :]
        expected_error["payload_sha256"] = hashlib.sha256(invalid).hexdigest()
        expected_errors.append(expected_error)

        edits = consume(compose, "edits")
        assert [json.loads(r["value"]) for r in edits] == expected_edits * index
        assert [r["key"] for r in edits] == ["enwiki:101", "enwiki:201"] * index
        for record in edits:
            EditEvent.model_validate_json(record["value"])
            headers = {h["key"]: h["value"] for h in record["headers"]}
            assert headers == {
                "source": "fixture",
                "source_id": "fixture-1" if record["key"] == "enwiki:101" else "fixture-2",
                "ingest_version": "1",
            }
        errors = consume(compose, "ingest-errors")
        assert [json.loads(r["value"]) for r in errors] == expected_errors
        assert [r["key"] for r in errors] == [
            "ingest:" + error["payload_sha256"] for error in expected_errors
        ]


@pytest.mark.parametrize("filename", ["incomplete.sse", "garbage.sse", "oversized.sse"])
def test_invalid_http_frames_never_reach_edits(compose, filename):
    compose("run", "--rm", "topics")
    compose("up", "-d", "--wait", "fixture-source")
    before_edits = consume(compose, "edits")
    before_errors = consume(compose, "ingest-errors")
    compose(
        "run",
        "--rm",
        "--no-deps",
        "-e",
        "INGEST_STREAM_URL=http://fixture-source:8080/" + filename,
        "-e",
        "INGEST_RECONNECT=false",
        "-e",
        "INGEST_SAMPLE_ALL=true",
        "-e",
        "INGEST_SOURCE=fixture",
        "connect",
    )
    assert consume(compose, "edits") == before_edits
    errors = consume(compose, "ingest-errors")
    assert errors[:-1] == before_errors
    raw = (FIXTURES / filename).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert errors[-1]["key"] == "ingest:" + digest
    assert json.loads(errors[-1]["value"]) == {
        "schema_version": 1,
        "stage": "ingestion",
        "reason": "invalid_record",
        "source": "fixture",
        "source_id": "" if filename == "garbage.sse" else "fixture-1",
        "payload_sha256": digest,
    }
