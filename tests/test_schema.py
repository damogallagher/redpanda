import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from triage.schema import AnalysisResult, EditEvent, Evidence

EVENT = {
    "wiki": "enwiki",
    "title": "Example",
    "old_revision_id": 100,
    "revision_id": 101,
    "occurred_at": "2026-10-20T10:00:00Z",
}
RESULT = {
    "event": EVENT,
    "analysis_version": "v1",
    "backend": "ollama",
    "model": "test:1",
    "prompt_version": "v1",
    "decision": "review",
    "confidence": 0.7,
    "explanation": "The revised sentence asserts causation.",
    "evidence": [{"before": "possible association", "after": "proved causation"}],
    "attempts": 2,
    "latency_ms": 100,
    "content_truncated": False,
}


def test_event_identity_provenance_and_json_roundtrip():
    event = EditEvent.model_validate_json(json.dumps(EVENT))
    assert event.event_id == "enwiki:101"
    assert event.source_url == "https://en.wikipedia.org/w/index.php?diff=101&oldid=100"
    assert event.schema_version == 1
    assert EditEvent.model_validate_json(event.model_dump_json()) == event


@pytest.mark.parametrize(
    "override",
    [
        {"schema_version": 2},
        {"wiki": "otherwiki"},
        {"title": ""},
        {"title": " "},
        {"revision_id": 0},
        {"revision_id": "101"},
        {"revision_id": True},
        {"old_revision_id": 101},
        {"old_revision_id": -1},
        {"occurred_at": "2026-10-20T10:00:00"},
        {"extra": "field"},
    ],
)
def test_event_rejects_invalid_records(override):
    with pytest.raises(ValidationError):
        EditEvent.model_validate_json(json.dumps({**EVENT, **override}))


def test_result_requires_evidence_and_preserves_complete_payload():
    result = AnalysisResult.model_validate_json(json.dumps(RESULT))
    assert result.decision == "review"
    assert result.evidence[0].after == "proved causation"
    assert result.event.revision_id == 101
    assert AnalysisResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "override",
    [
        {"decision": "good"},
        {"confidence": -0.01},
        {"confidence": 1.01},
        {"confidence": "0.7"},
        {"confidence": float("nan")},
        {"confidence": float("inf")},
        {"attempts": 0},
        {"attempts": 5},
        {"latency_ms": -1},
        {"explanation": " "},
        {"evidence": []},
        {"decision": "routine", "content_truncated": True},
        {"evidence": [{"before": "same", "after": "same"}]},
        {"unknown": "field"},
    ],
)
def test_result_rejects_unsafe_or_incompatible_values(override):
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate_json(json.dumps({**RESULT, **override}))


def test_abstention_and_partial_review_are_explicit():
    abstention = AnalysisResult.model_validate_json(
        json.dumps(
            {
                **RESULT,
                "decision": "insufficient_evidence",
                "evidence": [],
                "content_truncated": True,
            }
        )
    )
    assert not abstention.evidence
    review = AnalysisResult.model_validate_json(json.dumps({**RESULT, "content_truncated": True}))
    assert review.decision == "review"
    assert Evidence(before="", after="added").after == "added"
    assert Evidence(before="removed", after="").before == "removed"


@pytest.mark.parametrize(
    "name,model", [("edit-event", EditEvent), ("analysis-result", AnalysisResult)]
)
def test_committed_json_schema_matches_application_contract(name, model):
    assert json.loads(Path(f"schemas/{name}.v1.json").read_text()) == model.model_json_schema()
