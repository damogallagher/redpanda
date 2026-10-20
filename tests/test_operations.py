"""Operator safety: exact project ownership, profiles, budgets, and failure reporting."""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from triage import operations as op


@pytest.fixture
def commands(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in [".env", ".env.local", ".env.frontier"]:
        Path(name).write_text("PRIVATE ORIGINAL")
    config = {
        "name": "example",
        "services": {
            "model-check": {"environment": {"LLM_BASE_URL": "http://ollama:11434"}},
            "model-init": {"command": ["pull", "qwen2.5:7b"]},
            "ollama": {},
        },
        "volumes": {
            v: {"name": "example_" + v} for v in ["redpanda-data", "postgres-data", "ollama-data"]
        },
    }
    state = SimpleNamespace(
        config=config, calls=[], code=0, output=json.dumps({"passed": 9, "total": 9}), owned=True
    )

    def run(args, **kwargs):
        state.calls.append((args, kwargs))
        out = ""
        code = 0
        if "config" in args:
            out = json.dumps(config)
        elif args[:3] == ["docker", "volume", "ls"]:
            key = args[-1].split("=")[-1]
            out = (
                "example_" + key + "\n"
                if state.owned is True
                else ""
                if state.owned is False
                else state.owned
            )
        elif "triage-evaluate" in args:
            out, code = state.output, state.code
        return SimpleNamespace(stdout=out, returncode=code)

    monkeypatch.setattr(op, "run", run)
    return state


def test_environment_keeps_docker_connection_not_profile_overrides(monkeypatch):
    monkeypatch.setattr(
        os,
        "environ",
        {
            "DOCKER_HOST": "socket",
            "PATH": "path",
            "LLM_MODEL": "bad",
            "COMPOSE_FILE": "bad",
            "OPENAI_API_KEY": "secret",
            "SINK_GROUP_ID": "bad",
            "POSTGRES_PASSWORD": "secret",
            "OLLAMA_MODEL": "bad",
            "PGPASSWORD": "bad",
        },
    )
    assert op.environment() == {"DOCKER_HOST": "socket", "PATH": "path"}


@pytest.mark.parametrize(
    "code,allow,raises", [(0, False, False), (1, True, False), (1, False, True)]
)
def test_subprocess_contract(monkeypatch, code, allow, raises):
    def fake(args, **kw):
        assert kw["timeout"] == 2400 and kw["capture_output"] and not kw["check"]
        assert "shell" not in kw
        return subprocess.CompletedProcess(args, code, "secret", "secret")

    monkeypatch.setattr(subprocess, "run", fake)
    if raises:
        with pytest.raises(op.OperationError, match="Docker command failed"):
            op.run(["docker"], capture=True, allow_failure=allow)
    else:
        assert op.run(["docker"], capture=True, allow_failure=allow).returncode == code


@pytest.mark.parametrize(
    "command,delete",
    [
        ("clean-docker", False),
        ("clean-docker", True),
        ("clean-ollama", False),
        ("clean-ollama", True),
    ],
)
def test_cleanup_exact_ownership_and_retention(commands, command, delete):
    flag = "--delete-data" if command == "clean-docker" else "--delete-models"
    assert op.main([command, *([flag] if delete else [])]) == 0
    calls = [args for args, kw in commands.calls]
    assert any("down" in args and "--profile" in args and "--volumes" not in args for args in calls)
    removals = [args[3:] for args in calls if args[:3] == ["docker", "volume", "rm"]]
    expected = (
        ["example_ollama-data"]
        if command == "clean-ollama"
        else ["example_redpanda-data", "example_postgres-data"]
    )
    assert removals == ([expected] if delete else [])
    assert Path(".env").read_text() == "PRIVATE ORIGINAL"


@pytest.mark.parametrize("kind", ["external", "wrong-owner", "native", "missing"])
def test_cleanup_refuses_unsafe_or_missing_setup(commands, kind, capsys):
    if kind == "external":
        commands.config["volumes"]["ollama-data"]["external"] = True
    elif kind == "wrong-owner":
        commands.owned = "unrelated_volume\n"
    elif kind == "native":
        del commands.config["services"]["ollama"]
    else:
        Path(".env.local").unlink()
    assert op.main(["clean-ollama", "--delete-models"]) == 1
    assert not any("down" in args or "rm" in args for args, kw in commands.calls)
    assert "secret" not in capsys.readouterr().err


def test_cleanup_is_idempotent_when_volume_absent(commands):
    commands.owned = False
    assert op.main(["clean-docker", "--delete-data"]) == 0
    assert not any(args[:3] == ["docker", "volume", "rm"] for args, kw in commands.calls)


@pytest.mark.parametrize(
    "args",
    [
        ["test-local", "--delete-data"],
        ["clean-docker", "--delete-models"],
        ["clean-ollama", "--delete-data"],
    ],
)
def test_invalid_delete_flags(args):
    with pytest.raises(SystemExit) as exc:
        op.main(args)
    assert exc.value.code == 2


@pytest.mark.parametrize("mode", ["local", "frontier", "native"])
def test_model_only_no_worker_no_profile_switch(commands, mode, capsys):
    if mode == "frontier":
        commands.config["services"]["model-check"]["environment"] = {
            "LLM_BACKEND": "openai",
            "LLM_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_API_KEY": "secret",
        }
    elif mode == "native":
        commands.config["services"]["model-check"]["environment"]["LLM_BASE_URL"] = (
            "http://host.docker.internal:11434"
        )
    command = "test-frontier" if mode == "frontier" else "test-local"
    assert op.main([command]) == 0
    calls = [args for args, kw in commands.calls]
    assert not any("worker" in args or "connect" in args or "down" in args for args in calls)
    assert any("ollama" in args for args in calls) == (mode == "local")
    assert any("triage-evaluate" in args and "--no-deps" in args for args in calls)
    report = Path("reports/model-" + ("frontier" if mode == "frontier" else "local") + ".json")
    assert report.stat().st_mode & 0o777 == 0o600
    assert json.loads(report.read_text())["passed"] == 9
    assert Path(".env").read_text() == "PRIVATE ORIGINAL"
    assert "secret" not in capsys.readouterr().out
    report.chmod(0o644)
    assert op.main([command]) == 0
    assert report.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "issue", ["backend", "tag", "missing-init", "exit", "empty", "malformed", "failed"]
)
def test_failed_model_check_is_visible(commands, issue, capsys):
    if issue == "backend":
        commands.config["services"]["model-check"]["environment"] = {
            "LLM_BACKEND": "openai",
            "LLM_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_API_KEY": "secret",
        }
    elif issue == "tag":
        commands.config["services"]["model-init"]["command"] = ["pull", "wrong"]
    elif issue == "missing-init":
        del commands.config["services"]["model-init"]
    elif issue == "exit":
        commands.code = 2
    elif issue == "empty":
        commands.output = ""
    elif issue == "malformed":
        commands.output = "secret not json"
    else:
        commands.code = 1
        commands.output = json.dumps({"passed": 8, "total": 9})
    assert op.main(["test-local"]) == 1
    out = capsys.readouterr()
    assert "secret" not in out.out + out.err
    if issue == "failed":
        assert "FAIL: 8/9" in out.out


@pytest.mark.parametrize(
    "error", [OSError("secret"), KeyError("secret"), subprocess.TimeoutExpired("secret", 1)]
)
def test_system_errors_are_redacted(monkeypatch, error, capsys):
    def fail(*args):
        raise error

    monkeypatch.setattr(op, "manage", fail)
    assert op.main(["clean-docker"]) == 1
    assert "secret" not in capsys.readouterr().err.replace("No secret output", "")


@pytest.mark.parametrize("name", ["test-local", "test-frontier", "clean-docker", "clean-ollama"])
def test_shell_entry_points_resolve_checkout_and_forward_flags(tmp_path, name):
    import shutil

    root = Path(__file__).resolve().parents[1]
    repo = tmp_path / "checkout with spaces"
    shutil.copytree(root / "scripts", repo / "scripts")
    fake = tmp_path / "uv"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@"\nexit 17\n')
    fake.chmod(0o755)
    result = subprocess.run(
        [str(repo / "scripts" / f"{name}.sh"), "--help"],
        cwd=tmp_path,
        env={**os.environ, "UV": str(fake)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 17
    assert result.stdout.splitlines() == [
        str(repo),
        "run",
        "--frozen",
        "--no-editable",
        "triage-manage",
        name,
        "--help",
    ]
