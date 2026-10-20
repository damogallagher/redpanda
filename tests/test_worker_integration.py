"""Real Redpanda acknowledgements, replay, and SIGTERM; model/Wikipedia HTTP are doubled."""

import json
import subprocess
from pathlib import Path

import pytest

from triage.reasoning import ReasonedEdit
from triage.worker import ProcessingError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def worker_compose(compose):
    compose("build", "model-check", timeout=240)
    compose(
        "exec",
        "-T",
        "redpanda",
        "rpk",
        "cluster",
        "config",
        "set",
        "auto_create_topics_enabled",
        "false",
    )
    return compose


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "dirty",
        "low-confidence",
        "unresolved",
        "invalid",
        "timeout",
        "malformed",
        "result-replay",
        "error-replay",
        "commit-replay",
        "shutdown",
    ],
)
def test_worker_delivery(worker_compose, case):
    compose = worker_compose
    try:
        output = compose(
            "run",
            "--rm",
            "--no-deps",
            "-v",
            f"{Path('tests/fixtures/worker').resolve()}:/scenario:ro",
            "model-check",
            "python",
            "/scenario/scenario.py",
            case,
            timeout=90,
        )
    except subprocess.CalledProcessError as exc:
        pytest.fail(exc.stdout + exc.stderr)
    summary = json.loads(output.splitlines()[-1])
    for line in output.splitlines()[:-1]:
        log = json.loads(line)
        if log["event"] == "record_committed":
            assert log["output_topic"] == summary["output_topic"], output
    raw = compose(
        "exec",
        "-T",
        "redpanda",
        "rpk",
        "topic",
        "consume",
        summary["output_topic"],
        "--num",
        str(summary["output_count"]),
        "--format",
        "%k\t%v\n",
        timeout=20,
    )
    rows = [line.split("\t", 1) for line in raw.splitlines()]
    for key, payload in rows:
        if case in {"malformed", "error-replay", "timeout"}:
            result = ProcessingError.model_validate_json(payload)
            assert result.code == ("model_failed" if case == "timeout" else "invalid_event")
            assert key == f"{summary['input_topic']}:0:{result.source.offset}:triage-v1"
        else:
            result = ReasonedEdit.model_validate_json(payload)
            assert result.analysis.decision == (
                "insufficient_evidence" if case in {"unresolved", "invalid"} else "review"
            )
            assert key == f"{result.analysis.event.event_id}:triage-v1"
            assert result.analysis.attempts <= 4
            if case == "dirty":
                assert result.steps[0].outcome == "invalid_output"
            if case == "low-confidence":
                assert result.outcome == "reviewed"
    if case.endswith("replay"):
        assert summary["failure_offset"] == summary["initial_offset"] < 0
        assert summary["final_offset"] == 2
    if case == "commit-replay":
        assert rows[0][0] == rows[1][0]  # Duplicate is intentional under at-least-once delivery.
    if case == "shutdown":
        assert summary["final_offset"] == 1 and summary["calls"] == ["extract", "assess"]
    if case in {"malformed", "error-replay"}:
        assert not summary["calls"]
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/worker-{case}.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "records": [{"key": key, "value": json.loads(payload)} for key, payload in rows],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2))
    print(raw)
