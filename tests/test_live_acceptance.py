"""Opt-in fresh checkout + empty volumes + actual Wikipedia/Ollama acceptance."""

import io
import json
import subprocess
import tarfile
import uuid
from pathlib import Path
from time import monotonic, sleep

import httpx
import pytest

from triage.operations import environment

pytestmark = [pytest.mark.integration, pytest.mark.live]
ROOT = Path(__file__).resolve().parents[1]


def test_fresh_local_bootstrap_and_live_edit(tmp_path):
    project = "triage-live-" + uuid.uuid4().hex[:10]
    checkout = tmp_path / "fresh-checkout"
    checkout.mkdir()
    archive = subprocess.run(
        ["git", "archive", "HEAD"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        files.extractall(checkout, filter="data")
    assert not list(checkout.glob(".env")) and not (checkout / ".venv").exists()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    env = {
        **environment(),
        "CONNECT_PORT": "0",
        "SINK_PORT": "0",
        "API_PORT": "0",
        "WORKER_MAX_ITEMS": "3",
        "INGEST_SAMPLE_ALL": "true",
    }
    # All other settings use the normal root Compose defaults. No private profile/key is copied.
    base = [
        "docker",
        "compose",
        "--env-file",
        "/dev/null",
        "-f",
        "docker-compose.yml",
        "-p",
        project,
    ]

    def compose(*args, timeout=180):
        return subprocess.run(
            [*base, *args],
            cwd=checkout,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        ).stdout

    started = monotonic()
    try:
        print(
            "Fresh local startup: downloading model weights if needed; allow up to 40 minutes.",
            flush=True,
        )
        compose("up", "--build", "-d", timeout=2400)
        boot_seconds = round(monotonic() - started, 3)
        compose("exec", "-T", "redpanda", "rpk", "topic", "list")
        # Seed a persisted synthetic result without extra model calls to prove the canned demo too.
        subprocess.run(
            ["./scripts/seed-results.sh"],
            cwd=checkout,
            env={**env, "COMPOSE_PROJECT_NAME": project, "COMPOSE_FILE": "docker-compose.yml"},
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        address = "http://" + compose("port", "api", "8000").strip()
        deadline = monotonic() + 900
        with httpx.Client(base_url=address, timeout=5, trust_env=False) as client:
            while True:
                result = client.get("/results", params={"analysis_version": "triage-v1"}).json()
                if result["items"]:
                    break
                assert monotonic() < deadline, (
                    "No live result arrived within 15 minutes; "
                    "inspect service health and upstream availability."
                )
                sleep(2)
            state = json.loads(compose("ps", "-a", "--format", "json", "worker"))
            while state["State"] != "exited":
                assert monotonic() < deadline, (
                    "Three-edit worker batch did not finish within 15 minutes."
                )
                sleep(2)
                state = json.loads(compose("ps", "-a", "--format", "json", "worker"))
            assert state["ExitCode"] == 0
            compose("stop", "connect")
            rows = client.get("/results", params={"analysis_version": "triage-v1"}).json()["items"]
            details = [
                client.get(
                    f"/results/enwiki/{row['revision_id']}?analysis_version=triage-v1"
                ).json()["result"]
                for row in rows
            ]
            assert details and any(len(r["steps"]) >= 2 for r in details)
            assert all(r["enrichment"]["source"] == "wikipedia" for r in details)
            assert (
                len(client.get("/results", params={"analysis_version": "demo-v1"}).json()["items"])
                == 3
            )
            assert client.get("/health/ready").status_code == 200
        lag = json.loads(
            compose(
                "exec",
                "-T",
                "redpanda",
                "rpk",
                "group",
                "describe",
                "triage-v1",
                "--format",
                "json",
            )
        )
        models = compose("exec", "-T", "ollama", "ollama", "list")
        report = {
            "commit": commit,
            "project": project,
            "boot_seconds": boot_seconds,
            "total_seconds": round(monotonic() - started, 3),
            "worker_limit": 3,
            "maximum_model_calls": 12,
            "sampling": "all eligible edits for a bounded observation; normal default is 1%",
            "rows": len(details),
            "results": [
                {
                    "event": r["analysis"]["event"],
                    "decision": r["analysis"]["decision"],
                    "attempts": r["analysis"]["attempts"],
                    "outcome": r["outcome"],
                    "steps": r["steps"],
                }
                for r in details
            ],
            "group": lag,
            "ollama_models": models,
            "seed_rows": 3,
            "limits": "One live run; no accuracy or sustainable throughput claim.",
        }
        (ROOT / "reports").mkdir(exist_ok=True)
        (ROOT / "reports/live-acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        compose("--profile", "tools", "down", "--volumes", "--remove-orphans", timeout=180)
        for resource in [["ps", "-aq"], ["volume", "ls", "-q"], ["network", "ls", "-q"]]:
            left = subprocess.run(
                ["docker", *resource, "--filter", f"label=com.docker.compose.project={project}"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            ).stdout.strip()
            assert not left, f"Test resources remain: {left}"
