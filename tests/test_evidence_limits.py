"""Count boundaries use the real parser, provider adapters and reasoning loop."""

import json

import httpx
import pytest
from test_reasoning import EVENT, assessment, source

from triage.broker import Record
from triage.config import Settings
from triage.enrichment import EnrichmentResult
from triage.reasoning import ReasonedEdit, reason
from triage.schema import Evidence
from triage.worker import process


def hunks(count):
    return tuple(Evidence(before=f"Old claim {i}.", after=f"New claim {i}.") for i in range(count))


def changes(indexes):
    return {
        "changes": [
            {
                "hunk": i,
                "kind": "meaning",
                "summary": "The claim changed.",
                **hunks(i + 1)[i].model_dump(),
            }
            for i in indexes
        ]
    }


def settings(backend):
    return Settings.from_env(
        {"LLM_BACKEND": backend, "OPENAI_API_KEY": "test-only-no-real-request"}
    )


def model_response(value, backend):
    message = {"role": "assistant", "content": json.dumps(value)}
    return httpx.Response(
        200,
        json={"message": message, "done": True, "done_reason": "stop"}
        if backend == "ollama"
        else {"choices": [{"message": message, "finish_reason": "stop"}]},
    )


@pytest.mark.parametrize("backend", ["ollama", "openai"])
@pytest.mark.parametrize("count", [0, 1, 8, 9, 20, 21])
def test_count_boundary_is_handled_before_model_calls(count, backend):
    calls = []
    body = "".join(
        '<tr><td class="diff-lineno">Line 1:</td><td class="diff-lineno">Line 1:</td></tr>'
        '<tr><td class="diff-marker"></td>'
        f'<td class="diff-deletedline">{item.before}</td>'
        '<td class="diff-marker"></td>'
        f'<td class="diff-addedline">{item.after}</td></tr>'
        for item in hunks(count)
    )

    def response(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "compare": {
                        "fromrevid": EVENT.old_revision_id,
                        "torevid": EVENT.revision_id,
                        "fromid": 42,
                        "toid": 42,
                        "fromns": 0,
                        "tons": 0,
                        "fromtitle": EVENT.title,
                        "totitle": EVENT.title,
                        "body": body,
                    }
                },
            )
        assert 1 <= count <= 8, "Unprocessable evidence must not incur model calls"
        calls.append(json.loads(request.content))
        return model_response(changes(range(count)) if len(calls) == 1 else assessment(), backend)

    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        result = process(
            Record("edits", 0, 0, EVENT.event_id.encode(), EVENT.model_dump_json().encode()),
            settings(backend),
            client,
            deadline=240,
            clock=lambda: 0,
        )
    assert isinstance(result, ReasonedEdit)
    assert result.analysis.event == EVENT
    assert result.enrichment.provenance.source_url == EVENT.source_url
    assert result.enrichment.evidence == hunks(min(count, 8))
    assert result.analysis.attempts == len(calls) == (2 if 1 <= count <= 8 else 0)
    assert result.analysis.content_truncated == result.enrichment.content_truncated == (count > 8)
    if 1 <= count <= 8:
        assert result.outcome == "assessed" and result.analysis.decision == "review"
        assert result.enrichment.status == "ready"
        assert result.analysis.evidence == hunks(count)
        assert {change.hunk for change in result.extraction.changes} == set(range(count))
    else:
        assert result.analysis.decision == "insufficient_evidence"
        assert result.analysis.confidence == 0 and result.extraction is None and not result.steps
        assert result.enrichment.status == ("evidence_limit" if count else "no_text_change")
        assert result.outcome == ("incomplete_source" if count else "no_change")
        assert result.enrichment.status in result.analysis.explanation or not count


@pytest.mark.parametrize("count", [9, 20])
def test_legacy_ready_evidence_is_bounded_without_inference_or_input_mutation(count):
    original = EnrichmentResult.model_validate({**source().model_dump(), "evidence": hunks(count)})
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("No model call for oversized input"))
    ) as client:
        result = reason(original, Settings(), client)
    assert len(original.evidence) == count and original.status == "ready"
    assert not original.content_truncated
    assert result.enrichment.evidence == hunks(8)
    assert result.enrichment.status == "evidence_limit"
    assert result.enrichment.provenance == original.provenance
    assert result.analysis.content_truncated and result.analysis.attempts == 0
    assert result.analysis.decision == "insufficient_evidence"
    assert result.outcome == "incomplete_source" and not result.steps


@pytest.mark.parametrize(
    "count,indexes",
    [(2, [0]), (2, [0, 0]), (2, [0, 2]), (8, [*range(8), 0])],
    ids=["missing", "duplicate-instead-of-missing", "out-of-range", "too-many"],
)
@pytest.mark.parametrize("repaired", [False, True])
def test_model_count_mismatches_require_complete_repair_or_abstention(count, indexes, repaired):
    original = EnrichmentResult.model_validate({**source().model_dump(), "evidence": hunks(count)})
    calls = []

    def response(request):
        body = json.loads(request.content)
        calls.append(json.loads(body["messages"][1]["content"]))
        value = changes(indexes)
        if repaired and len(calls) == 2:
            value = changes(range(count))
        elif repaired and len(calls) == 3:
            value = assessment()
        return model_response(value, "ollama")

    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        result = reason(original, Settings(), client)
    assert calls[0]["repair"] is False and calls[1]["repair"] is True
    assert all(call["hunks"] == [h.model_dump() for h in original.evidence] for call in calls)
    assert result.analysis.attempts == len(calls) == (3 if repaired else 2)
    assert result.steps[0].outcome == "invalid_output"
    if repaired:
        assert result.outcome == "assessed" and result.analysis.decision == "review"
        assert result.analysis.evidence == original.evidence
    else:
        assert result.outcome == "invalid_output"
        assert (
            result.analysis.decision == "insufficient_evidence" and result.analysis.confidence == 0
        )
        assert result.extraction is None and all(step.stage == "extract" for step in result.steps)
