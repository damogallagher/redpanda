"""Real broker/worker boundary demo; Wikipedia and model HTTP are controlled."""

import json
from threading import Event

import httpx
from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic

from triage.broker import Broker, WorkerSettings
from triage.config import Settings
from triage.worker import run_worker

topic = "evidence-boundaries"
group = "evidence-boundaries-worker"
counts = (8, 9, 20, 21)
admin = AdminClient({"bootstrap.servers": "redpanda:9092"})
admin.create_topics([NewTopic(topic, 1, 1)])[topic].result(timeout=15)
producer = Producer({"bootstrap.servers": "redpanda:9092", "acks": "all"})
for count in counts:
    revision = 1000 + count
    producer.produce(
        topic,
        key=f"enwiki:{revision}".encode(),
        value=json.dumps(
            {
                "schema_version": 1,
                "wiki": "enwiki",
                "title": f"Synthetic {count}-hunk edit",
                "old_revision_id": revision - 1,
                "revision_id": revision,
                "occurred_at": "2026-10-21T10:00:00Z",
            }
        ).encode(),
    )
assert producer.flush(15) == 0
model_calls = []


def response(request):
    if request.method == "GET":
        revision = int(request.url.params["torev"])
        count = revision - 1000
        return httpx.Response(
            200,
            json={
                "compare": {
                    "fromrevid": revision - 1,
                    "torevid": revision,
                    "fromid": revision,
                    "toid": revision,
                    "fromns": 0,
                    "tons": 0,
                    "fromtitle": f"Synthetic {count}-hunk edit",
                    "totitle": f"Synthetic {count}-hunk edit",
                    "body": "".join(
                        '<tr><td class="diff-lineno">Line 1:</td>'
                        '<td class="diff-lineno">Line 1:</td></tr>'
                        '<tr><td class="diff-marker"></td>'
                        f'<td class="diff-deletedline">Old claim {i}.</td>'
                        '<td class="diff-marker"></td>'
                        f'<td class="diff-addedline">New claim {i}.</td></tr>'
                        for i in range(count)
                    ),
                }
            },
        )
    body = json.loads(request.content)
    data = json.loads(body["messages"][1]["content"])
    assert data["title"] == "Synthetic 8-hunk edit", "Oversized edits must not call the model"
    model_calls.append(data["title"])
    value = (
        {
            "changes": [
                {"hunk": i, "kind": "meaning", "summary": "Claim changed.", **item}
                for i, item in enumerate(data["hunks"])
            ]
        }
        if "Extract the changes" in body["messages"][0]["content"]
        else {"decision": "review", "confidence": 0.95, "explanation": "The claims changed."}
    )
    return httpx.Response(
        200,
        json={
            "message": {"role": "assistant", "content": json.dumps(value)},
            "done": True,
            "done_reason": "stop",
        },
    )


with httpx.Client(transport=httpx.MockTransport(response)) as client:
    assert run_worker(
        Broker(WorkerSettings(input_topic=topic, group_id=group, max_items=len(counts))),
        Settings(model="fixture-not-a-real-model"),
        client,
        Event(),
    ) == len(counts)
consumer = Consumer(
    {"bootstrap.servers": "redpanda:9092", "group.id": group, "enable.auto.commit": False}
)
try:
    offset = consumer.committed([TopicPartition(topic, 0)], timeout=10)[0].offset
finally:
    consumer.close()
assert offset == len(counts) and len(model_calls) == 2
print(json.dumps({"counts": counts, "committed_offset": offset, "model_calls": model_calls}))
