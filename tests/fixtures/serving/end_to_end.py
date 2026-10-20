"""Real worker with deterministic Wikipedia/model HTTP doubles; test-only mount."""

import json
from threading import Event

import httpx

from triage.broker import Broker, WorkerSettings
from triage.config import Settings
from triage.worker import run_worker

before = "An association was found."
after = "A causal relationship was proved."


def response(request):
    if request.method == "GET":
        revision = int(request.url.params["torev"])
        title = "Example article" if revision == 101 else "Second article"
        return httpx.Response(
            200,
            json={
                "compare": {
                    "fromrevid": int(request.url.params["fromrev"]),
                    "torevid": revision,
                    "fromid": revision,
                    "toid": revision,
                    "fromns": 0,
                    "tons": 0,
                    "fromtitle": title,
                    "totitle": title,
                    "body": '<tr><td class="diff-lineno">Line 1:</td>'
                    '<td class="diff-lineno">Line 1:</td></tr>'
                    '<tr><td class="diff-marker"></td>'
                    f'<td class="diff-deletedline"><div>{before}</div></td>'
                    '<td class="diff-marker"></td>'
                    f'<td class="diff-addedline"><div>{after}</div></td></tr>',
                }
            },
        )
    system = json.loads(request.content)["messages"][0]["content"]
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
        if "Extract the changes" in system
        else {
            "decision": "review",
            "confidence": 0.95,
            "explanation": "The causal claim is stronger without additional evidence.",
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


with httpx.Client(transport=httpx.MockTransport(response)) as client:
    assert (
        run_worker(
            Broker(WorkerSettings(group_id="phase5-e2e", max_items=2)),
            Settings(model="fixture-not-a-real-model"),
            client,
            Event(),
        )
        == 2
    )
