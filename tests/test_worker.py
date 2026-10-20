import hashlib
import json
from threading import Event
from unittest.mock import Mock

import httpx
import pytest
from test_reasoning import EVENT, assessment, extraction, run, source

from triage import worker
from triage.broker import DeliveryError, Record, WorkerSettings
from triage.config import Settings
from triage.reasoning import ReasoningFailure, Step
from triage.worker import ProcessingError, process, run_worker, worker_settings

RECORD = Record("edits", 0, 7, EVENT.event_id.encode(), EVENT.model_dump_json().encode())


def test_worker_settings_are_explicit_and_unrelated_secrets_are_ignored():
    assert worker_settings({"OPENAI_API_KEY": "PRIVATE"}) == WorkerSettings()
    settings = worker_settings(
        {"KAFKA_BROKERS": "broker:9092", "KAFKA_GROUP_ID": "fixture", "WORKER_MAX_ITEMS": "0"}
    )
    assert (settings.brokers, settings.group_id, settings.max_items) == (
        "broker:9092",
        "fixture",
        0,
    )


@pytest.mark.parametrize(
    "value,key",
    [
        (None, None),
        (b"PRIVATE", None),
        (b"x" * 8193, b"key"),
        (EVENT.model_dump_json().encode(), b"wrong"),
    ],
)
def test_invalid_events_get_replay_metadata_without_raw_payload(value, key):
    record = Record("edits", 1, 8, key, value)
    with httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("no network"))) as client:
        result = process(record, Settings(), client, deadline=240)
    assert isinstance(result, ProcessingError)
    assert result.code == "invalid_event" and not result.steps
    assert result.source.model_dump() == {"topic": "edits", "partition": 1, "offset": 8}
    assert result.payload_sha256 == hashlib.sha256(value or b"").hexdigest()
    assert "PRIVATE" not in result.model_dump_json()


def test_process_enriches_then_reasons(monkeypatch):
    calls = []
    expected, _, _ = run([extraction(), assessment()])
    monkeypatch.setattr(
        worker, "enrich", lambda event, client, **kw: (calls.append("enrich"), source())[1]
    )
    monkeypatch.setattr(
        worker,
        "reason",
        lambda enriched, settings, client, **kw: (
            calls.append(("reason", enriched, kw["deadline"])),
            expected,
        )[1],
    )
    with httpx.Client() as client:
        assert process(RECORD, Settings(), client, deadline=240) == expected
    assert calls == ["enrich", ("reason", source(), 240)]


def test_enrichment_technical_failure_uses_error_topic_contract(monkeypatch):
    failed = source().model_copy(update={"status": "timeout", "provenance": None, "evidence": ()})
    monkeypatch.setattr(worker, "enrich", lambda *a, **kw: failed)
    with httpx.Client() as client:
        result = process(RECORD, Settings(), client, deadline=240)
    assert result.code == "enrichment_failed" and result.detail == "timeout"
    assert result.event == EVENT


def test_reasoning_failure_keeps_step_metadata(monkeypatch):
    monkeypatch.setattr(worker, "enrich", lambda *a, **kw: source())

    def fail(*args, **kwargs):
        raise ReasoningFailure("model_failed", (Step(stage="extract", outcome="model_error"),))

    monkeypatch.setattr(worker, "reason", fail)
    with httpx.Client() as client:
        result = process(RECORD, Settings(), client, deadline=240)
    assert result.code == "model_failed"
    assert len(result.steps) == 1 and result.steps[0].outcome == "model_error"


def broker_fixture(records, limit=1):
    return Mock(settings=WorkerSettings(max_items=limit), poll=Mock(side_effect=records))


@pytest.mark.parametrize("kind", ["result", "error"])
def test_publish_precedes_commit_and_logs_only_operational_metadata(monkeypatch, capsys, kind):
    result, _, _ = run([extraction(), assessment()])
    if kind == "error":
        with httpx.Client() as client:
            result = process(
                Record("edits", 0, 7, None, b"PRIVATE"), Settings(), client, deadline=240
            )
    broker = broker_fixture([None, RECORD])
    order = []
    monkeypatch.setattr(worker, "process", lambda *a, **kw: result)
    broker.publish.side_effect = lambda *a: order.append("publish")
    broker.commit.side_effect = lambda *a: order.append("commit")
    with httpx.Client() as client:
        assert run_worker(broker, Settings(), client, Event()) == 1
    assert order == ["publish", "commit"]
    topic, key, value = broker.publish.call_args.args
    assert topic == ("results" if kind == "result" else "processing-errors")
    assert (
        key
        == (f"{EVENT.event_id}:triage-v1" if kind == "result" else "edits:0:7:triage-v1").encode()
    )
    assert json.loads(value) == result.model_dump(mode="json")
    broker.commit.assert_called_once_with(RECORD)
    broker.close.assert_called_once()
    logs = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [log["event"] for log in logs] == [
        "worker_started",
        "record_committed",
        "worker_stopped",
    ]
    assert logs[1]["offset"] == 7 and "PRIVATE" not in json.dumps(logs)


@pytest.mark.parametrize("failure", ["publish", "commit"])
def test_failed_delivery_stops_before_later_records(monkeypatch, failure, capsys):
    result, _, _ = run([extraction(), assessment()])
    broker = broker_fixture([RECORD, RECORD], limit=0)
    getattr(broker, failure).side_effect = DeliveryError("failed")
    monkeypatch.setattr(worker, "process", lambda *a, **kw: result)
    with httpx.Client() as client, pytest.raises(DeliveryError):
        run_worker(broker, Settings(), client, Event())
    assert broker.poll.call_count == 1
    assert broker.commit.call_count == (0 if failure == "publish" else 1)
    broker.close.assert_called_once()
    assert "record_committed" not in capsys.readouterr().out


@pytest.mark.parametrize("when", ["before", "poll", "processing"])
def test_shutdown_leaves_unstarted_work_or_drains_current_item(monkeypatch, when):
    result, _, _ = run([extraction(), assessment()])
    stop = Event()
    broker = broker_fixture([RECORD], limit=0)
    if when == "before":
        stop.set()
    if when == "poll":
        broker.poll.side_effect = lambda: (stop.set(), RECORD)[1]

    def handle(*args, **kwargs):
        stop.set()
        return result

    monkeypatch.setattr(worker, "process", handle)
    with httpx.Client() as client:
        count = run_worker(broker, Settings(), client, stop)
    assert count == (1 if when == "processing" else 0)
    assert broker.commit.call_count == count
    broker.close.assert_called_once()


@pytest.mark.parametrize("failed", [False, True])
def test_service_handles_signals_and_restores_previous_handlers(monkeypatch, failed, capsys):
    registrations = []
    monkeypatch.setattr(
        worker.signal,
        "signal",
        lambda signum, handler: (registrations.append((signum, handler)), "old")[1],
    )
    monkeypatch.setattr(worker, "Broker", lambda _: object())

    def run_service(broker, settings, client, stop):
        assert not stop.is_set()
        registrations[0][1](2, None)
        assert stop.is_set()
        if failed:
            raise DeliveryError("broker publication failed")

    monkeypatch.setattr(worker, "run_worker", run_service)
    assert worker.serve(WorkerSettings(), Settings()) == (1 if failed else 0)
    assert [handler for _, handler in registrations[2:]] == ["old", "old"]
    if failed:
        assert json.loads(capsys.readouterr().out)["event"] == "worker_failed"
