"""Security regressions exercise observable boundaries, including failure paths."""

import json
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from test_evaluation import cases

from triage import evaluation, files, operations
from triage.api import create_app
from triage.config import Settings
from triage.enrichment import EnrichmentResult
from triage.limits import MAX_EVALUATION_BYTES
from triage.storage import Store


def test_private_atomic_report_replaces_symlink_without_touching_target(tmp_path):
    victim = tmp_path / "original.json"
    victim.write_text("PRIVATE ORIGINAL")
    report = tmp_path / "report.json"
    report.symlink_to(victim)
    files.write_private_json(report, {"prompt": "synthetic"})
    assert not report.is_symlink()
    assert victim.read_text() == "PRIVATE ORIGINAL"
    assert json.loads(report.read_text()) == {"prompt": "synthetic"}
    assert report.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".triage-*"))


@pytest.mark.parametrize("failure", ["encoding", "creation", "flush", "replace"])
def test_failed_report_preserves_previous_copy_and_removes_temporary_files(
    monkeypatch, tmp_path, failure
):
    report = tmp_path / "report.json"
    report.write_text("ORIGINAL")

    def fail(*args, **kwargs):
        raise OSError("synthetic disk error")

    if failure == "creation":
        monkeypatch.setattr(files.tempfile, "mkstemp", fail)
    elif failure == "flush":
        monkeypatch.setattr(files.os, "fsync", fail)
    elif failure == "replace":
        monkeypatch.setattr(files.os, "replace", fail)
    value = object() if failure == "encoding" else {"calls": []}
    with pytest.raises((OSError, TypeError)):
        files.write_private_json(report, value)
    assert report.read_text() == "ORIGINAL"
    assert not list(tmp_path.glob(".triage-*"))


def test_report_directory_and_replaced_report_are_private(tmp_path):
    report = tmp_path / "private" / "report.json"
    files.write_private_json(report, {"calls": []})
    assert report.parent.stat().st_mode & 0o777 == 0o700
    report.chmod(0o644)
    files.write_private_json(report, {"calls": ["replacement"]})
    assert report.stat().st_mode & 0o777 == 0o600
    assert json.loads(report.read_text())["calls"] == ["replacement"]


@pytest.mark.parametrize("argv", [[], ["sh", "-c", "echo unsafe"], ["docker; echo unsafe"]])
def test_operator_helper_rejects_non_docker_commands(monkeypatch, argv):
    run = Mock()
    monkeypatch.setattr(operations.subprocess, "run", run)
    with pytest.raises(operations.OperationError, match="Only Docker"):
        operations.run(argv)
    run.assert_not_called()


@pytest.mark.parametrize(
    "host", ["evil.example", "localhost.evil.example", "127.0.0.1.evil.example"]
)
def test_host_header_is_checked_before_storage(host):
    store = Mock(spec=Store)
    with TestClient(create_app(store), base_url="http://127.0.0.1") as client:
        response = client.get("/results", headers={"Host": host})
    assert response.status_code == 400
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert store.mock_calls == []


def test_evaluation_accepts_oversized_source_abstention_without_model_requests():
    original = cases()[0]
    source = EnrichmentResult.model_validate(
        {**original.source.model_dump(), "evidence": original.source.evidence * 9}
    )
    case = evaluation.Case(
        id="legacy-oversized",
        rubric="Capacity limitation must abstain without inference.",
        expected="insufficient_evidence",
        source=source,
    )

    def forbidden(request):
        pytest.fail("Oversized evidence must not reach the model")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        report = evaluation.evaluate([case], Settings(), client)
    assert report["passed"] == report["total"] == report["completed"] == 1
    assert report["cases"][0]["calls"] == []
    assert report["cases"][0]["output"]["enrichment"]["status"] == "evidence_limit"


@pytest.mark.parametrize("extra", [1, 1000])
def test_oversized_evaluation_is_rejected_before_inference(tmp_path, monkeypatch, capsys, extra):
    # Valid JSON prefix padded beyond the boundary must not hide an oversized file.
    payload = json.dumps([cases()[0].model_dump(mode="json")]).encode()
    path = tmp_path / "cases.json"
    path.write_bytes(payload + b" " * (MAX_EVALUATION_BYTES - len(payload) + extra))
    evaluate = Mock()
    monkeypatch.setattr(evaluation, "evaluate", evaluate)
    assert evaluation.main([str(path)]) == 2
    evaluate.assert_not_called()
    assert "Invalid evaluation" in capsys.readouterr().err
