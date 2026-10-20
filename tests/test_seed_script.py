"""Exercise the real demo script with a recording Docker boundary."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from triage.reasoning import ReasonedEdit

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("failure,expected_calls", [("", 5), ("up", 1), ("produce", 2)])
def test_demo_publishes_valid_keyed_fixtures_and_stops_on_errors(tmp_path, failure, expected_calls):
    commands = tmp_path / "calls.jsonl"
    binary = tmp_path / "docker"
    binary.write_text("""#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
stage = "produce" if "produce" in args else "port" if "port" in args else "up"
value = sys.stdin.read() if stage == "produce" else None
with open(os.environ["SEED_LOG"], "a") as stream:
    stream.write(json.dumps({"args": args, "stage": stage, "value": value}) + "\\n")
if stage == os.environ["SEED_FAIL"]:
    sys.exit(17)
if stage == "port":
    print("127.0.0.1:8888")
""")
    binary.chmod(0o755)
    completed = subprocess.run(
        [str(ROOT / "scripts/seed-results.sh")],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
            "SEED_LOG": str(commands),
            "SEED_FAIL": failure,
        },
        text=True,
        capture_output=True,
        timeout=10,
    )
    calls = [json.loads(line) for line in commands.read_text().splitlines()]
    assert len(calls) == expected_calls
    assert completed.returncode == (17 if failure else 0)
    assert calls[0]["args"][-2:] == ["sink", "api"]
    if not failure:
        assert "127.0.0.1:8888" in completed.stdout
        assert [call["stage"] for call in calls] == ["up", "produce", "produce", "produce", "port"]
        for call, decision, revision in zip(
            calls[1:4], ["review", "routine", "insufficient_evidence"], [101, 102, 103], strict=True
        ):
            result = ReasonedEdit.model_validate_json(call["value"])
            assert result.analysis.event.revision_id == revision
            assert result.analysis.analysis_version == "demo-v1"
            assert result.analysis.decision == decision
            assert call["args"][-2:] == ["--key", f"enwiki:{revision}:demo-v1"]
