"""Test-only fault injection around a real worker/broker; never installed in the image."""

import json
import os
import sys
from pathlib import Path
from threading import Event
from time import monotonic, sleep

import httpx

from triage.broker import Broker, WorkerSettings
from triage.config import Settings
from triage.worker import run_worker

mode, topic, group = sys.argv[1:]
before = "An association was found."
after = "A causal relationship was proved."


def response(request):
    if request.method == "GET":
        revision = int(request.url.params["torev"])
        return httpx.Response(
            200,
            json={
                "compare": {
                    "fromrevid": int(request.url.params["fromrev"]),
                    "torevid": revision,
                    "fromid": 42,
                    "toid": 42,
                    "fromns": 0,
                    "tons": 0,
                    "fromtitle": "Recovery example",
                    "totitle": "Recovery example",
                    "body": '<tr><td class="diff-lineno">Line 1:</td>'
                    '<td class="diff-lineno">Line 1:</td></tr>'
                    '<tr><td class="diff-marker"></td>'
                    f'<td class="diff-deletedline"><div>{before}</div></td>'
                    '<td class="diff-marker"></td>'
                    f'<td class="diff-addedline"><div>{after}</div></td></tr>',
                }
            },
        )
    extract = "Extract the changes" in json.loads(request.content)["messages"][0]["content"]
    value = (
        {
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
        if extract
        else {
            "decision": "review",
            "confidence": 0.95,
            "explanation": "A stronger causal claim needs review.",
        }
    )
    return httpx.Response(
        200,
        json={
            "message": {"role": "assistant", "content": json.dumps(value)},
            "done": True,
            "done_reason": "stop",
        },
    )


broker = Broker(
    WorkerSettings(input_topic=topic, group_id=group, max_items=2, delivery_timeout_seconds=2)
)
if mode == "crash":
    broker.commit = lambda record: os._exit(17)  # After real publication, before commit/close.
elif mode == "outage":
    publish = broker.publish

    def wait_for_outage(*args):
        Path("/control/ready").touch()
        deadline = monotonic() + 90
        while not Path("/control/release").exists():
            assert monotonic() < deadline, "Parent did not release fault barrier"
            sleep(0.1)
        publish(*args)

    broker.publish = wait_for_outage
with httpx.Client(transport=httpx.MockTransport(response)) as client:
    assert run_worker(broker, Settings(model="fixture-not-a-real-model"), client, Event()) == 2
