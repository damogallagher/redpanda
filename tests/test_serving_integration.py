"""Real Connect → Postgres → HTTP, including replay and an interrupted database."""

import hashlib
import json
from pathlib import Path
from time import monotonic, sleep

import httpx
import pytest
from test_ingestion import consume

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parent / "fixtures" / "serving"


def eventually(check, timeout=40):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        value = check()
        if value:
            return value
        sleep(0.2)
    raise AssertionError("Expected observable state was not reached within the timeout")


def sql(compose, statement):
    return compose(
        "exec", "-T", "postgres", "psql", "-U", "triage", "-d", "triage", "-Atc", statement
    ).strip()


def publish(compose, value, key=None):
    raw = value if isinstance(value, str) else json.dumps(value)
    if key is None:
        analysis = value["analysis"]
        key = f"enwiki:{analysis['event']['revision_id']}:{analysis['analysis_version']}"
    compose(
        "exec",
        "-T",
        "redpanda",
        "rpk",
        "topic",
        "produce",
        "results",
        "--key",
        key,
        input=raw + "\n",
    )


def committed(compose):
    data = json.loads(
        compose(
            "exec",
            "-T",
            "redpanda",
            "rpk",
            "group",
            "describe",
            "triage-store-v1",
            "--format",
            "json",
        )
    )
    return data[0]["partitions"][0]["current_offset"]


@pytest.fixture(scope="module")
def serving(compose):
    # Existing Phase 1 volume already exists before the explicit migration runs.
    original = sql(compose, "SELECT applied_at FROM schema_migrations WHERE version=1")
    compose("build", "api", "model-check", timeout=300)
    compose("up", "-d", "--wait", "--wait-timeout", "120", "sink", "api")
    address = "http://" + compose("port", "api", "8000").strip()
    with httpx.Client(base_url=address, timeout=10, trust_env=False) as client:
        assert client.get("/health/ready").status_code == 200
        assert sql(compose, "SELECT applied_at FROM schema_migrations WHERE version=1") == original
        yield client


def test_seed_replay_pagination_parameterization_and_migration(compose, serving):
    client = serving
    assert client.get("/results").json() == {"items": [], "next_before_id": None}
    seeds = [
        json.loads((FIXTURES / (name + ".jsonl")).read_text())
        for name in ["review", "routine", "insufficient_evidence"]
    ]
    for seed in seeds:
        publish(compose, seed)
    eventually(lambda: len(client.get("/results").json()["items"]) == 3)
    first = client.get("/results?limit=2").json()
    assert [r["revision_id"] for r in first["items"]] == [103, 102]
    second = client.get(
        "/results", params={"limit": 2, "before_id": first["next_before_id"]}
    ).json()
    assert [r["revision_id"] for r in second["items"]] == [101]
    assert second["next_before_id"] is None
    detail = client.get("/results/enwiki/101?analysis_version=demo-v1").json()
    assert detail["result"] == seeds[0]
    assert (
        len(client.get("/results?decision=routine&analysis_version=demo-v1").json()["items"]) == 1
    )
    assert (
        client.get(
            "/results", params={"analysis_version": "'; DROP TABLE triage_results; --"}
        ).json()["items"]
        == []
    )
    seeds[0]["analysis"]["explanation"] = (
        "'; DROP TABLE triage_results; -- <script>example</script>"
    )
    publish(compose, seeds[0])
    eventually(
        lambda: (
            client.get("/results/enwiki/101?analysis_version=demo-v1").json()["result"] == seeds[0]
        )
    )
    updated = client.get("/results/enwiki/101?analysis_version=demo-v1").json()
    assert updated["id"] == detail["id"] and updated["created_at"] == detail["created_at"]
    assert updated["updated_at"] >= detail["updated_at"]
    assert sql(compose, "SELECT count(*) FROM triage_results") == "3"
    eventually(lambda: committed(compose) == 4)
    # A new consumer replays all offsets, including older values of the same analysis.
    compose("up", "-d", "--no-deps", "sink", env_overrides={"SINK_GROUP_ID": "triage-store-replay"})
    eventually(
        lambda: (
            '"component":"redpanda"' in compose("logs", "--no-color", "sink")
            or client.get("/health/ready").status_code == 200
        )
    )

    # Use the group's committed offset to prove replay completed, not just an unchanged row.
    def replay_complete():
        data = json.loads(
            compose(
                "exec",
                "-T",
                "redpanda",
                "rpk",
                "group",
                "describe",
                "triage-store-replay",
                "--format",
                "json",
            )
        )
        return (
            data and data[0].get("partitions") and data[0]["partitions"][0]["current_offset"] == 4
        )

    eventually(replay_complete)
    assert client.get("/results/enwiki/101?analysis_version=demo-v1").json() == updated
    compose("up", "-d", "--no-deps", "sink")
    compose("run", "--rm", "db-migrate")
    assert sql(compose, "SELECT count(*) FROM schema_migrations WHERE version=2") == "1"
    assert sql(compose, "SELECT count(*) FROM triage_results") == "3"


def test_invalid_records_are_quarantined_with_bounded_metadata(compose, serving):
    before = len(consume(compose, "sink-errors"))
    values = ['{"invalid":"secret fixture"}', '{"padding":"' + "x" * 262145 + '"}']
    for raw in values:
        publish(compose, raw, key="invalid")
    errors = eventually(
        lambda: items if len(items := consume(compose, "sink-errors")) == before + 2 else None
    )
    for error, raw in zip(errors[-2:], values, strict=True):
        data = json.loads(error["value"])
        assert data["reason"] == "invalid_result" and data["stage"] == "persistence"
        assert data["payload_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
        assert len(error["value"]) < 400
        assert "secret fixture" not in error["value"]
    assert sql(compose, "SELECT count(*) FROM triage_results") == "3"
    assert serving.get("/results?limit=101").status_code == 422


def test_database_outage_and_sink_restart_preserve_uncommitted_work(compose, serving):
    client = serving
    expected = len(consume(compose, "results"))
    eventually(lambda: committed(compose) == expected)
    error_count = len(consume(compose, "sink-errors"))
    compose("stop", "postgres")
    seed = json.loads((FIXTURES / "review.jsonl").read_text())
    seed["analysis"]["analysis_version"] = "recovery-v1"
    publish(compose, seed)
    assert client.get("/health/live").status_code == 200
    for path in ["/health/ready", "/results", "/results/enwiki/101?analysis_version=demo-v1"]:
        response = client.get(path)
        assert response.status_code == 503
        assert response.json() == {"error": "storage_unavailable"}
    eventually(lambda: "failed to connect" in compose("logs", "--no-color", "sink").lower())
    assert committed(compose) == expected
    compose("restart", "sink")
    assert committed(compose) == expected
    compose("up", "-d", "--wait", "--wait-timeout", "120", "postgres")
    eventually(
        lambda: client.get("/results/enwiki/101?analysis_version=recovery-v1").status_code == 200
    )
    eventually(lambda: committed(compose) == expected + 1)
    assert sql(compose, "SELECT count(*) FROM triage_results") == "4"
    assert len(consume(compose, "sink-errors")) == error_count
    evidence = {
        "database_outage": {
            "offset_before": expected,
            "offset_during": expected,
            "offset_after": expected + 1,
        },
        "logical_rows": 4,
        "detail": client.get("/results/enwiki/101?analysis_version=recovery-v1").json(),
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/serving-recovery.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        json.dumps(
            {
                "recovery": "passed",
                "pending_offset": expected,
                "delivered_offset": expected + 1,
                "logical_rows": 4,
            }
        )
    )


def test_fixture_source_to_results_api(compose, serving):
    compose("up", "-d", "--wait", "fixture-source")
    compose(
        "run",
        "--rm",
        "--no-deps",
        "-e",
        "INGEST_STREAM_URL=http://fixture-source:8080/phase-2.sse",
        "-e",
        "INGEST_RECONNECT=false",
        "-e",
        "INGEST_SAMPLE_ALL=true",
        "connect",
    )
    output = compose(
        "run",
        "--rm",
        "--no-deps",
        "-v",
        f"{FIXTURES.resolve()}:/fixtures:ro",
        "model-check",
        "python",
        "/fixtures/end_to_end.py",
        timeout=90,
    )
    assert '"processed": 2' in output
    deliveries = [json.loads(line) for line in output.splitlines() if '"record_committed"' in line]
    assert len(deliveries) == 2
    assert all(item["output_topic"] == "results" for item in deliveries), output
    from triage.prompts import ANALYSIS_VERSION

    eventually(
        lambda: (
            len(
                serving.get("/results", params={"analysis_version": ANALYSIS_VERSION}).json()[
                    "items"
                ]
            )
            == 2
        )
    )
    for revision, title in [(101, "Example article"), (201, "Second article")]:
        response = serving.get(f"/results/enwiki/{revision}?analysis_version={ANALYSIS_VERSION}")
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["analysis"]["decision"] == "review"
        assert result["analysis"]["event"]["title"] == title
        assert result["analysis"]["evidence"][0]["after"] == "A causal relationship was proved."
        assert result["analysis"]["attempts"] == 2
        assert result["steps"] == [
            {"stage": "extract", "outcome": "valid"},
            {"stage": "assess", "outcome": "valid"},
        ]
    assert consume(compose, "processing-errors") == []
    print(
        json.dumps(
            {
                "end_to_end": "passed",
                "source": "SSE fixture",
                "worker": "real",
                "http_model_boundaries": "deterministic doubles",
                "results": 2,
            }
        )
    )
