"""Test-only process: real Kafka, HTTP boundary doubles; never shipped in the image."""

import json
import signal
import sys
import uuid
from threading import Event
from unittest.mock import patch

import httpx
from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic

from triage.broker import Broker, DeliveryError, WorkerSettings
from triage.config import Settings
from triage.worker import run_worker, serve

case = sys.argv[1]
prefix = "phase4-" + uuid.uuid4().hex[:10]
names = {name: f"{prefix}-{name}" for name in ("edits", "results", "errors")}
failed_delivery = case in {"result-replay", "error-replay", "commit-replay"}
poison = case in {"malformed", "error-replay"}
missing = (
    names["results"]
    if case == "result-replay"
    else names["errors"]
    if case == "error-replay"
    else None
)
admin = AdminClient({"bootstrap.servers": "redpanda:9092"})


def create(topics):
    for future in admin.create_topics([NewTopic(name, 1, 1) for name in topics]).values():
        future.result(timeout=15)


create([name for name in names.values() if name != missing])
event = {
    "schema_version": 1,
    "wiki": "enwiki",
    "title": "Synthetic delivery example",
    "old_revision_id": 100,
    "revision_id": 101,
    "occurred_at": "2026-10-20T10:00:00Z",
}
producer = Producer({"bootstrap.servers": "redpanda:9092", "acks": "all"})
count = 2 if failed_delivery or case == "shutdown" else 1
for index in range(count):
    value = b"malformed" if poison else json.dumps({**event, "revision_id": 101 + index}).encode()
    producer.produce(names["edits"], key=f"enwiki:{101 + index}".encode(), value=value)
assert producer.flush(15) == 0
before = "The study found an association, without proving causation."
after = "The study proved that the treatment causes recovery."
extraction = {
    "changes": [
        {
            "hunk": 0,
            "kind": "meaning",
            "summary": "Association becomes causation.",
            "before": before,
            "after": after,
        }
    ]
}
assessment = {
    "decision": "review",
    "confidence": 0.95,
    "explanation": "The causal claim is stronger without additional evidence.",
}
calls = []


def response(request):
    if request.method == "GET":
        return httpx.Response(
            200,
            json={
                "compare": {
                    "fromrevid": int(request.url.params["fromrev"]),
                    "torevid": int(request.url.params["torev"]),
                    "fromid": 42,
                    "toid": 42,
                    "fromns": 0,
                    "tons": 0,
                    "fromtitle": event["title"],
                    "totitle": event["title"],
                    "body": (
                        '<tr><td class="diff-lineno">Line 1:</td>'
                        '<td class="diff-lineno">Line 1:</td></tr>'
                        '<tr><td class="diff-marker"></td>'
                        f'<td class="diff-deletedline"><div>{before}</div></td>'
                        '<td class="diff-marker"></td>'
                        f'<td class="diff-addedline"><div>{after}</div></td></tr>'
                    ),
                }
            },
        )
    body = json.loads(request.content)
    system = body["messages"][0]["content"]
    stage = (
        "extract"
        if "Extract the changes" in system
        else "review"
        if "second assessment" in system
        else "assess"
    )
    calls.append(stage)
    if case == "shutdown" and len(calls) == 1:
        signal.raise_signal(signal.SIGTERM)
    if case == "timeout":
        raise httpx.ReadTimeout("synthetic model unavailable")
    value = extraction if stage == "extract" else assessment
    if (case == "dirty" and len(calls) == 1) or case == "invalid":
        value = "invalid JSON"
    elif (case in {"low-confidence", "unresolved"} and stage == "assess") or (
        case == "unresolved" and stage == "review"
    ):
        value = {**assessment, "confidence": 0.4}
    return httpx.Response(
        200,
        json={
            "message": {
                "role": "assistant",
                "content": value if isinstance(value, str) else json.dumps(value),
            },
            "done": True,
            "done_reason": "stop",
        },
    )


config = WorkerSettings(
    group_id=prefix,
    input_topic=names["edits"],
    results_topic=names["results"],
    errors_topic=names["errors"],
    max_items=count,
    delivery_timeout_seconds=2 if missing else 10,
)


def committed():
    consumer = Consumer(
        {"bootstrap.servers": "redpanda:9092", "group.id": prefix, "enable.auto.commit": False}
    )
    try:
        return consumer.committed([TopicPartition(names["edits"], 0)], timeout=10)[0].offset
    finally:
        consumer.close()


initial = committed()
assert initial < 0
with httpx.Client(transport=httpx.MockTransport(response)) as client:
    if case == "shutdown":
        with patch(
            "triage.worker.httpx.Client",
            return_value=httpx.Client(transport=httpx.MockTransport(response)),
        ):
            assert serve(config, Settings()) == 0
    elif failed_delivery:
        broker = Broker(config)
        if case == "commit-replay":

            def reject_commit(record):
                raise DeliveryError(
                    "injected offset-commit boundary failure after real publication"
                )

            broker.commit = reject_commit
        try:
            run_worker(broker, Settings(), client, Event())
        except DeliveryError:
            pass
        else:
            raise AssertionError("Expected delivery failure")
        after_failure = committed()
        assert after_failure == initial, (initial, after_failure)
        if missing:
            create([missing])
        run_worker(
            Broker(config.model_copy(update={"delivery_timeout_seconds": 10})),
            Settings(),
            client,
            Event(),
        )
    else:
        run_worker(Broker(config), Settings(), client, Event())
final = committed()
assert final == (1 if case == "shutdown" else count), final
print(
    json.dumps(
        {
            "case": case,
            "input_topic": names["edits"],
            "output_topic": names["errors"] if poison or case == "timeout" else names["results"],
            "group": prefix,
            "initial_offset": initial,
            "failure_offset": after_failure if failed_delivery else None,
            "final_offset": final,
            "calls": calls,
            "output_count": count + (1 if case == "commit-replay" else 0)
            if case != "shutdown"
            else 1,
        }
    )
)
