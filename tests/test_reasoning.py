import json
from pathlib import Path

import httpx
import pytest

from triage.config import Settings
from triage.enrichment import EnrichmentResult, Provenance
from triage.reasoning import (
    Assessment,
    Extraction,
    ReasoningFailure,
    parse_output,
    reason,
    validate_grounding,
)
from triage.schema import EditEvent, Evidence

EVENT = EditEvent.model_validate_json(
    Path("tests/fixtures/enrichment/synthetic-event.json").read_bytes()
)
BEFORE = "The study found an association, without proving causation."
AFTER = "The study proved that the treatment causes recovery."


def source(before=BEFORE, after=AFTER):
    return EnrichmentResult(
        event=EVENT,
        source="fixture",
        status="ready",
        attempts=0,
        provenance=Provenance(
            page_id=42, from_title=EVENT.title, to_title=EVENT.title, source_url=EVENT.source_url
        ),
        evidence=(Evidence(before=before, after=after),),
    )


def extraction(kind="meaning", **changes):
    return {
        "changes": [
            {
                "hunk": 0,
                "kind": kind,
                "summary": "Strengthens an association to causation.",
                "before": BEFORE,
                "after": AFTER,
                **changes,
            }
        ]
    }


def assessment(decision="review", confidence=0.95):
    return {
        "decision": decision,
        "confidence": confidence,
        "explanation": "The edit strengthens the causal claim without adding support.",
    }


def run(outputs, **kwargs):
    calls = []
    records = []
    outputs = iter(outputs)

    def handler(request):
        calls.append(json.loads(request.content))
        value = next(outputs)
        if isinstance(value, Exception):
            raise value
        content = value if isinstance(value, str) else json.dumps(value)
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": content},
                "done": True,
                "done_reason": "stop",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = reason(
            source(),
            Settings(),
            client,
            clock=lambda: 0,
            wait=lambda _: None,
            record=records.append,
            **kwargs,
        )
    return result, calls, records


def test_two_steps_do_content_work_and_preserve_grounded_evidence():
    result, calls, records = run([extraction(), assessment()])
    assert result.outcome == "assessed" and result.analysis.decision == "review"
    assert result.analysis.attempts == 2 and result.analysis.latency_ms == 0
    assert result.analysis.prompt_version == "edit-triage-v2"
    assert result.analysis.analysis_version == "triage-v1"
    assert result.analysis.evidence == source().evidence
    assert [step.stage for step in result.steps] == ["extract", "assess"]
    assert all(step.outcome == "valid" for step in result.steps)
    first = json.loads(calls[0]["messages"][1]["content"])
    second = json.loads(calls[1]["messages"][1]["content"])
    assert first["hunks"] == [source().evidence[0].model_dump()]
    assert second["extraction"] == extraction()
    assert len(records) == 2 and records[0].response == json.dumps(extraction())
    assert "untrusted data" in records[0].system_prompt


@pytest.mark.parametrize(
    "outputs,outcome,decision,attempts",
    [
        ([extraction("wording"), assessment("routine")], "assessed", "routine", 2),
        (
            [extraction(), assessment("insufficient_evidence")],
            "assessed",
            "insufficient_evidence",
            2,
        ),
        ([extraction(), assessment(confidence=0.4), assessment()], "reviewed", "review", 3),
        (
            [extraction(), assessment(confidence=0.4), assessment(confidence=0.5)],
            "low_confidence",
            "insufficient_evidence",
            3,
        ),
        (
            [extraction(), assessment("routine"), assessment("routine")],
            "contradiction",
            "insufficient_evidence",
            3,
        ),
        (
            [extraction(), assessment("routine"), assessment()],
            "contradiction",
            "insufficient_evidence",
            3,
        ),
        (
            [extraction(), assessment(confidence=0.4), assessment("insufficient_evidence")],
            "reviewed",
            "insufficient_evidence",
            3,
        ),
        (["broken", "still broken"], "invalid_output", "insufficient_evidence", 2),
        (["broken", extraction(), assessment()], "assessed", "review", 3),
        ([extraction(), "broken", assessment()], "assessed", "review", 3),
        ([extraction(), "broken", "broken"], "invalid_output", "insufficient_evidence", 3),
        (
            [extraction(), assessment(confidence=0.4), "broken", assessment()],
            "reviewed",
            "review",
            4,
        ),
        (
            ["broken", extraction(), "broken", assessment(confidence=0.4)],
            "invalid_output",
            "insufficient_evidence",
            4,
        ),
        (
            ["broken", extraction(), assessment(confidence=0.4), "broken"],
            "invalid_output",
            "insufficient_evidence",
            4,
        ),
        ([httpx.ReadTimeout("PRIVATE"), extraction(), assessment()], "assessed", "review", 3),
    ],
)
def test_repairs_reviews_and_abstention_are_bounded(outputs, outcome, decision, attempts):
    result, calls, _ = run(outputs)
    assert result.outcome == outcome
    assert result.analysis.decision == decision
    assert result.analysis.attempts == len(calls) == len(result.steps) == attempts <= 4
    assert "PRIVATE" not in result.model_dump_json()
    if outcome in {"invalid_output", "low_confidence", "contradiction"}:
        assert result.analysis.confidence == 0
    if any(step.outcome == "invalid_output" for step in result.steps[:-1]):
        assert any(json.loads(call["messages"][1]["content"])["repair"] for call in calls[1:])


@pytest.mark.parametrize(
    "confidence,calls,outcome", [(0.8, 2, "assessed"), (0.7999, 3, "reviewed")]
)
def test_confidence_boundary(confidence, calls, outcome):
    result, requests, _ = run([extraction(), assessment(confidence=confidence), assessment()])
    assert len(requests) == calls and result.outcome == outcome


@pytest.mark.parametrize(
    "status,truncated",
    [
        ("revision_unavailable", False),
        ("evidence_limit", True),
        ("no_text_change", False),
    ],
)
def test_unavailable_or_incomplete_source_never_calls_model(status, truncated):
    original = source()
    data = original.model_dump()
    data.update(status=status, evidence=(), content_truncated=truncated)
    if status == "revision_unavailable":
        data["provenance"] = None
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("unexpected model"))
    ) as client:
        result = reason(EnrichmentResult.model_validate(data), Settings(), client)
    assert result.analysis.decision == "insufficient_evidence"
    assert result.analysis.attempts == 0 and not result.steps
    assert result.analysis.content_truncated == truncated
    assert result.outcome == ("no_change" if status == "no_text_change" else "incomplete_source")


@pytest.mark.parametrize("wrapper", ["{}", "```json\n{}\n```", "```\n{}\n```", " \n{}\n "])
def test_single_json_object_or_exact_fence_parses_strings_with_braces(wrapper):
    data = assessment()
    data["explanation"] = 'A quoted {brace} and an escaped "quote" are data.'
    parsed = parse_output(wrapper.format(json.dumps(data)), Assessment)
    assert parsed.explanation == data["explanation"]


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[" * 15000 + "0" + "]" * 15000,
        "[]",
        "{}",
        "null",
        json.dumps(assessment()) * 2,
        "Prose: " + json.dumps(assessment()),
        json.dumps(assessment()) + "\nMore prose",
        '{"decision":"routine","decision":"review"}',
        json.dumps({**assessment(), "confidence": "0.9"}),
        json.dumps({**assessment(), "confidence": float("nan")}),
        json.dumps({**assessment(), "decision": " ROUTINE "}),
        json.dumps({**assessment(), "extra": "ignored?"}),
        '{"nested":{"x":1,"x":2}}',
    ],
)
def test_dirty_ambiguous_or_wrong_typed_output_requires_repair(raw):
    with pytest.raises(ValueError):
        parse_output(raw, Assessment)


@pytest.mark.parametrize(
    "changes",
    [
        {"hunk": 1},
        {"before": "invented quote"},
        {"after": "invented quote"},
        {"before": ""},
        {"after": ""},
        {"before": "The study", "after": "The study"},
    ],
)
def test_ungrounded_or_unchanged_excerpts_are_rejected(changes):
    value = parse_output(json.dumps(extraction(**changes)), Extraction)
    with pytest.raises(ValueError):
        validate_grounding(value, source())


@pytest.mark.parametrize("before,after", [("", AFTER), (BEFORE, "")])
def test_empty_side_is_allowed_only_for_actual_full_insertion_or_deletion(before, after):
    value = parse_output(json.dumps(extraction(before=before, after=after)), Extraction)
    validate_grounding(value, source(before, after))


def test_invented_evidence_is_repaired_before_assessment():
    result, calls, _ = run([extraction(before="invented"), extraction(), assessment()])
    assert result.analysis.decision == "review"
    assert result.steps[0].outcome == "invalid_output"
    assert json.loads(calls[1]["messages"][1]["content"])["repair"]


@pytest.mark.parametrize(
    "outputs,attempts",
    [
        ([httpx.ConnectError("PRIVATE"), httpx.ConnectError("PRIVATE")], 2),
        (["broken", extraction(), assessment(confidence=0.4), httpx.ReadTimeout("PRIVATE")], 4),
    ],
)
def test_repeated_transport_failure_is_a_technical_failure(outputs, attempts):
    with pytest.raises(ReasoningFailure) as raised:
        run(outputs)
    assert raised.value.code == "model_failed" and len(raised.value.steps) == attempts
    assert "PRIVATE" not in str(raised.value)


@pytest.mark.parametrize("kind", ["before", "during", "error", "retry"])
def test_deadline_exhaustion_is_explicit(kind):
    now = [0.0]
    calls = []

    def handler(request):
        calls.append(request)
        if kind != "retry":
            now[0] = 240
        if kind in {"error", "retry"}:
            raise httpx.ReadTimeout("PRIVATE")
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": json.dumps(extraction())},
                "done": True,
                "done_reason": "stop",
            },
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ReasoningFailure) as raised,
    ):
        reason(
            source(),
            Settings(),
            client,
            clock=lambda: now[0],
            deadline=-1 if kind == "before" else 240,
            wait=lambda _: now.__setitem__(0, 240),
        )
    assert raised.value.code == "deadline_exceeded"
    assert len(calls) == (0 if kind == "before" else 1)


def test_reasoning_checks_deadline_after_adapter_returns(monkeypatch):
    # A boundary adapter returning just after the deadline must not yield a result.
    from triage import reasoning

    now = [0]

    def late(*args, **kwargs):
        now[0] = 240
        return json.dumps(extraction())

    monkeypatch.setattr(reasoning, "complete", late)
    with httpx.Client() as client, pytest.raises(ReasoningFailure, match="deadline_exceeded"):
        reason(source(), Settings(), client, clock=lambda: now[0])


@pytest.mark.parametrize(
    "contract,raw",
    [
        (
            Assessment,
            json.dumps(assessment()).replace(
                '"decision": "review"', '"decision": "routine", "decision": "review"'
            ),
        ),
        (Extraction, json.dumps(extraction()).replace('"hunk": 0', '"hunk": 1, "hunk": 0')),
    ],
)
def test_duplicate_keys_in_otherwise_valid_model_output_are_rejected(contract, raw):
    # Without duplicate detection both documents satisfy their Pydantic contracts.
    with pytest.raises(ValueError, match="duplicate JSON key"):
        parse_output(raw, contract)
