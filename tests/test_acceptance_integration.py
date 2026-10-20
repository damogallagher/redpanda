"""Real broker outage, process death, replay into SQL, and narrowly scoped cleanup."""

import json
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import monotonic

import httpx
import pytest
from test_ingestion import consume
from test_serving_integration import eventually, sql

from triage import operations

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("fault", ["crash", "outage"])
def test_interruption_replays_backlog_into_unique_rows(compose, tmp_path, fault):
    compose("build", "model-check", "api", timeout=300)
    compose("up", "-d", "--wait", "--wait-timeout", "120", "sink", "api")
    topic = "acceptance-" + uuid.uuid4().hex[:10]
    group = topic + "-worker"
    compose("exec", "-T", "redpanda", "rpk", "topic", "create", topic)
    revision = 60001 if fault == "crash" else 70001
    for index in range(2):
        event = {
            "schema_version": 1,
            "wiki": "enwiki",
            "title": "Recovery example",
            "old_revision_id": revision - 1,
            "revision_id": revision + index,
            "occurred_at": "2026-10-20T00:00:00Z",
        }
        compose(
            "exec",
            "-T",
            "redpanda",
            "rpk",
            "topic",
            "produce",
            topic,
            "--key",
            f"enwiki:{revision + index}",
            input=json.dumps(event) + "\n",
        )
    control = tmp_path / "control"
    control.mkdir(mode=0o777)
    control.chmod(0o777)
    args = [
        "run",
        "--rm",
        "--no-deps",
        "-v",
        f"{ROOT}/tests/fixtures/acceptance:/acceptance:ro",
        "-v",
        f"{control}:/control",
        "model-check",
        "python",
        "/acceptance/recovery.py",
    ]
    started = monotonic()
    if fault == "crash":
        with pytest.raises(subprocess.CalledProcessError) as failure:
            compose(*args, "crash", topic, group, timeout=120)
        assert failure.value.returncode == 17
    else:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(compose, *args, "outage", topic, group, timeout=150)
            try:
                eventually(lambda: (control / "ready").exists(), timeout=60)
                compose("stop", "redpanda")
                (control / "release").touch()
                with pytest.raises(subprocess.CalledProcessError) as failure:
                    future.result(timeout=80)
                assert "not acknowledged" in failure.value.stderr
            finally:
                (control / "release").touch()
                compose("up", "-d", "--wait", "--wait-timeout", "120", "redpanda")

    def offset():
        state = json.loads(
            compose("exec", "-T", "redpanda", "rpk", "group", "describe", group, "--format", "json")
        )
        partitions = state[0].get("partitions", [])
        return partitions[0]["current_offset"] if partitions else -1

    failed_offset = offset()
    assert failed_offset < 0
    recovered = compose(*args, "recover", topic, group, timeout=150)
    assert '"processed": 2' in recovered
    assert offset() == 2
    with httpx.Client(
        base_url="http://" + compose("port", "api", "8000").strip(), trust_env=False
    ) as client:
        for rev in [revision, revision + 1]:
            eventually(lambda rev=rev: client.get(f"/results/enwiki/{rev}").status_code == 200)
            detail = client.get(f"/results/enwiki/{rev}").json()
            assert detail["result"]["analysis"]["decision"] == "review"
    assert (
        sql(
            compose,
            f"SELECT count(*) FROM triage_results WHERE revision_id IN ({revision},{revision + 1})",
        )
        == "2"
    )
    records = [
        item
        for item in consume(compose, "results")
        if item["key"].startswith((f"enwiki:{revision}:", f"enwiki:{revision + 1}:"))
    ]
    assert len(records) == (3 if fault == "crash" else 2)
    evidence = {
        "fault": fault,
        "backlog_before": 2,
        "offset_after_fault": failed_offset,
        "offset_after_recovery": 2,
        "backlog_after": 0,
        "kafka_results": len(records),
        "logical_rows": 2,
        "seconds": round(monotonic() - started, 3),
        "model": "deterministic HTTP double; not inference capacity",
    }
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/acceptance-{fault}.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence))


def test_cleanup_preserves_other_projects_and_separates_weights_from_data(tmp_path, monkeypatch):
    project = "triage-cleanup-" + uuid.uuid4().hex[:10]
    keys = ["redpanda-data", "postgres-data", "ollama-data"]
    names = [project + "_" + key for key in keys]
    sentinel = project + "-other"

    def docker(*args):
        return subprocess.run(
            ["docker", *args], check=True, text=True, capture_output=True, timeout=30
        ).stdout

    def create(key, name, owner):
        docker(
            "volume",
            "create",
            "--label",
            f"com.docker.compose.project={owner}",
            "--label",
            f"com.docker.compose.volume={key}",
            name,
        )

    profile = f"COMPOSE_FILE={ROOT}/docker-compose.yml\nCOMPOSE_PROJECT_NAME={project}\n"
    for name in [".env", ".env.local"]:
        (tmp_path / name).write_text(profile)
    monkeypatch.chdir(tmp_path)
    try:
        for key, name in zip(keys, names, strict=True):
            create(key, name, project)
        create("ollama-data", sentinel, project + "-other")
        assert operations.main(["clean-docker"]) == 0
        for name in names:
            docker("volume", "inspect", name)
        assert operations.main(["clean-docker", "--delete-data"]) == 0
        remaining = docker("volume", "ls", "-q").splitlines()
        assert names[0] not in remaining and names[1] not in remaining
        assert names[2] in remaining and sentinel in remaining
        for key, name in zip(keys[:2], names[:2], strict=True):
            create(key, name, project)
        assert operations.main(["clean-ollama", "--delete-models"]) == 0
        remaining = docker("volume", "ls", "-q").splitlines()
        assert names[0] in remaining and names[1] in remaining
        assert names[2] not in remaining and sentinel in remaining
        assert (tmp_path / ".env").read_text() == profile
    finally:
        existing = docker("volume", "ls", "-q").splitlines()
        for name in [*names, sentinel]:
            if name in existing:
                docker("volume", "rm", name)
