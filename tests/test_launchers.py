"""Exercise the real shell launchers with a recording Docker boundary."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def launcher(tmp_path):
    repo = tmp_path / "checkout with spaces"
    repo.mkdir()
    shutil.copytree(ROOT / "scripts", repo / "scripts")
    for mode in ("local", "frontier"):
        text = (ROOT / f".env.{mode}.example").read_text()
        (repo / f".env.{mode}").write_text(text)
    (repo / ".env").write_text("PREVIOUS=retain-until-validated\n")
    commands = tmp_path / "commands.jsonl"
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text(
        """#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
stage = next(s for s in ('config', 'run', 'down', 'up') if s in args)
profile = pathlib.Path(args[args.index('--env-file') + 1])
entry = {
    'args': args, 'stage': stage, 'cwd': os.getcwd(), 'profile': profile.read_text(),
    'inherited_overrides': [k for k in os.environ if k in {
        'LLM_BACKEND', 'OPENAI_API_KEY', 'COMPOSE_FILE', 'COMPOSE_PROJECT_NAME',
        'COMPOSE_PROFILES', 'POSTGRES_PASSWORD', 'INGEST_SAMPLE_ALL', 'OLLAMA_MODEL',
        'KAFKA_BROKERS', 'KAFKA_GROUP_ID', 'WORKER_MAX_ITEMS',
        'API_PORT', 'SINK_PORT', 'SINK_GROUP_ID', 'PGHOST', 'PGPORT', 'PGPASSWORD'}],
    'docker_host': os.environ.get('DOCKER_HOST'),
}
with open(os.environ['DOCKER_TEST_LOG'], 'a') as log:
    log.write(json.dumps(entry) + '\\n')
if os.environ.get('DOCKER_TEST_FAIL') == stage:
    print('Simulated Docker ' + stage + ' failure', file=sys.stderr)
    sys.exit(17)
"""
    )
    docker.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(binary) + os.pathsep + os.environ["PATH"],
        "DOCKER_TEST_LOG": str(commands),
        "DOCKER_HOST": "test-docker-connection",
        "LLM_BACKEND": "unwanted-host-backend",
        "OPENAI_API_KEY": "test-only-inherited-secret",
        "COMPOSE_FILE": "wrong.yml",
        "COMPOSE_PROJECT_NAME": "wrong-project",
        "COMPOSE_PROFILES": "tools",
        "POSTGRES_PASSWORD": "wrong-password",
        "INGEST_SAMPLE_ALL": "true",
        "OLLAMA_MODEL": "wrong-model",
        "KAFKA_BROKERS": "wrong-broker:9092",
        "KAFKA_GROUP_ID": "wrong-group",
        "WORKER_MAX_ITEMS": "0",
        "API_PORT": "9999",
        "SINK_PORT": "9998",
        "SINK_GROUP_ID": "wrong-group",
        "PGHOST": "wrong-db",
        "PGPORT": "9997",
        "PGPASSWORD": "wrong-password",
    }

    def run(mode="local", *, failure="", args=()):
        completed = subprocess.run(
            [str(repo / "scripts" / f"start-{mode}.sh"), *args],
            cwd=tmp_path,  # Must resolve paths from the script, not the caller's cwd.
            env={**env, "DOCKER_TEST_FAIL": failure},
            text=True,
            capture_output=True,
            timeout=10,
        )
        calls = (
            [json.loads(line) for line in commands.read_text().splitlines()]
            if commands.exists()
            else []
        )
        return completed, calls

    return repo, run


@pytest.mark.parametrize("mode", ["local", "frontier"])
def test_selects_profile_replaces_env_and_retains_volumes(launcher, mode):
    repo, run = launcher
    selected = (repo / f".env.{mode}").read_bytes()
    result, calls = run(mode)
    assert result.returncode == 0, result.stderr
    assert [call["stage"] for call in calls] == ["config", "run", "down", "up"]
    assert calls[1]["args"][-7:] == [
        "run",
        "--build",
        "--rm",
        "--no-deps",
        "model-check",
        "triage",
        "check-config",
    ]
    assert calls[2]["profile"] == "PREVIOUS=retain-until-validated\n"
    assert calls[2]["args"][-4:] == ["--profile", "tools", "down", "--remove-orphans"]
    assert calls[3]["args"][-4:] == ["up", "--build", "-d", "--remove-orphans"]
    assert (repo / ".env").read_bytes() == selected
    assert (repo / ".env").stat().st_mode & 0o777 == 0o600
    assert (repo / f".env.{mode}").read_bytes() == selected
    assert all(not call["inherited_overrides"] for call in calls)
    assert all(call["docker_host"] == "test-docker-connection" for call in calls)
    assert all(call["cwd"] == str(repo) for call in calls)
    assert all("--volumes" not in call["args"] for call in calls)
    assert "test-only-inherited-secret" not in result.stdout + result.stderr
    assert "model-init" in result.stdout if mode == "local" else "model-init" not in result.stdout
    assert not list(repo.glob(".env.switch.*"))


def test_first_start_needs_no_existing_env(launcher):
    repo, run = launcher
    (repo / ".env").unlink()
    result, calls = run()
    assert result.returncode == 0
    assert [call["stage"] for call in calls] == ["config", "run", "up"]
    assert (repo / ".env").read_bytes() == (repo / ".env.local").read_bytes()


def test_missing_profile_leaves_active_config_untouched(launcher):
    repo, run = launcher
    (repo / ".env.frontier").unlink()
    result, calls = run("frontier")
    assert result.returncode != 0
    assert "Copy .env.frontier.example" in result.stderr
    assert calls == []
    assert (repo / ".env").read_text() == "PREVIOUS=retain-until-validated\n"


@pytest.mark.parametrize("stage", ["config", "run", "down"])
def test_preflight_or_shutdown_failure_retains_active_config(launcher, stage):
    repo, run = launcher
    result, calls = run(failure=stage)
    assert result.returncode == 17
    assert calls[-1]["stage"] == stage
    assert (repo / ".env").read_text() == "PREVIOUS=retain-until-validated\n"
    assert not list(repo.glob(".env.switch.*"))
    assert "Started" not in result.stdout


def test_startup_failure_keeps_selected_config_for_retry(launcher):
    repo, run = launcher
    result, calls = run("frontier", failure="up")
    assert result.returncode == 17
    assert calls[-1]["stage"] == "up"
    assert (repo / ".env").read_bytes() == (repo / ".env.frontier").read_bytes()
    assert not list(repo.glob(".env.switch.*"))
    assert "Started" not in result.stdout


def test_concurrent_switch_is_rejected_without_removing_other_lock(launcher):
    repo, run = launcher
    (repo / ".env.switch.lock").mkdir()
    result, calls = run()
    assert result.returncode != 0
    assert "Another startup" in result.stderr
    assert calls == []
    assert (repo / ".env.switch.lock").is_dir()
    assert (repo / ".env").read_text() == "PREVIOUS=retain-until-validated\n"


def test_env_content_is_not_executed_as_shell(launcher):
    repo, run = launcher
    marker = repo / "must-not-exist"
    with (repo / ".env.local").open("a") as stream:
        stream.write(f'UNTRUSTED=$(touch "{marker}")\n')
    result, _ = run()
    assert result.returncode == 0
    assert not marker.exists()


def test_extra_arguments_are_rejected(launcher):
    _, run = launcher
    result, calls = run(args=("--volumes",))
    assert result.returncode == 2
    assert "Usage:" in result.stderr
    assert calls == []


@pytest.mark.parametrize("args", [[], ["unknown"]])
def test_shared_entry_point_requires_a_known_mode(args):
    result = subprocess.run(
        [str(ROOT / "scripts/start.sh"), *args], text=True, capture_output=True, timeout=5
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr or "Unknown mode" in result.stderr
