"""Extract, assess, optionally review; four calls maximum and no confident fallback."""

import json
import re
from collections.abc import Callable
from time import monotonic, sleep
from typing import Annotated, Literal

import httpx
from pydantic import Field

from triage.config import Settings
from triage.enrichment import EnrichmentResult
from triage.llm import ModelError, complete
from triage.prompts import ANALYSIS_VERSION, ASSESS, EXTRACT, PROMPT_VERSION, REVIEW
from triage.schema import MAX_REASONING_HUNKS, AnalysisResult, Contract, Evidence

CONFIDENCE_THRESHOLD = 0.8
MAX_CALLS = 4
Stage = Literal["extract", "assess", "review"]
Outcome = Literal[
    "assessed",
    "reviewed",
    "invalid_output",
    "low_confidence",
    "contradiction",
    "incomplete_source",
    "no_change",
]


class Change(Contract):
    hunk: Annotated[int, Field(ge=0, le=19)]
    kind: Literal["wording", "meaning", "evidence", "unclear"]
    summary: Annotated[str, Field(min_length=1, max_length=400, pattern=r"\S")]
    before: Annotated[str, Field(max_length=512)]
    after: Annotated[str, Field(max_length=512)]


class Extraction(Contract):
    changes: Annotated[tuple[Change, ...], Field(min_length=1, max_length=MAX_REASONING_HUNKS)]


class Assessment(Contract):
    decision: Literal["routine", "review", "insufficient_evidence"]
    confidence: Annotated[float, Field(ge=0, le=1)]
    explanation: Annotated[str, Field(min_length=1, max_length=1200, pattern=r"\S")]


class Step(Contract):
    stage: Stage
    outcome: Literal["valid", "invalid_output", "model_error"]


class ReasonedEdit(Contract):
    schema_version: Literal[1] = 1
    analysis: AnalysisResult
    enrichment: EnrichmentResult
    extraction: Extraction | None
    steps: Annotated[tuple[Step, ...], Field(max_length=4)]
    outcome: Outcome


class CallRecord(Contract):
    """Only explicitly requested development evaluations retain prompts/responses."""

    stage: Stage
    system_prompt: str
    user_prompt: str
    response: str | None


class ReasoningFailure(Exception):
    def __init__(
        self,
        code: Literal["model_failed", "deadline_exceeded"],
        steps: tuple[Step, ...],
    ) -> None:
        super().__init__(code)
        self.code = code
        self.steps = steps


def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_output[T: Contract](text: str, contract: type[T]) -> T:
    text = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # Pydantic alone accepts duplicate JSON keys. Reject them at every nesting level.
    try:
        json.loads(text, object_pairs_hook=unique_keys)
    except RecursionError:
        raise ValueError("model JSON nesting exceeds parser limit") from None
    return contract.model_validate_json(text)


def validate_grounding(extraction: Extraction, source: EnrichmentResult) -> None:
    if {change.hunk for change in extraction.changes} != set(range(len(source.evidence))):
        raise ValueError("extraction must cover every source hunk")
    for change in extraction.changes:
        hunk = source.evidence[change.hunk]
        for quote, text in ((change.before, hunk.before), (change.after, hunk.after)):
            if quote not in text or (not quote and text):
                raise ValueError("evidence must be an exact excerpt from the same hunk")
        Evidence(before=change.before, after=change.after)


def reason(
    source: EnrichmentResult,
    settings: Settings,
    client: httpx.Client,
    *,
    deadline: float | None = None,
    clock: Callable[[], float] = monotonic,
    wait: Callable[[float], None] = sleep,
    record: Callable[[CallRecord], None] | None = None,
) -> ReasonedEdit:
    start = clock()
    deadline = start + 240 if deadline is None else deadline
    steps: list[Step] = []
    extraction: Extraction | None = None
    # Old v1 inputs can contain 20 hunks. Preserve read compatibility, but never
    # spend model calls on an impossible extraction or classify a partial edit.
    if len(source.evidence) > MAX_REASONING_HUNKS:
        source = EnrichmentResult.model_validate(
            {
                **source.model_dump(),
                "evidence": source.evidence[:MAX_REASONING_HUNKS],
                "status": "evidence_limit",
                "content_truncated": True,
            }
        )
    input_data = {
        "title": source.event.title,
        "hunks": [item.model_dump() for item in source.evidence],
    }

    def finish(outcome: Outcome, assessment: Assessment | None = None) -> ReasonedEdit:
        if assessment is None:
            explanations = {
                "invalid_output": "Model output could not be validated within the call budget.",
                "low_confidence": "The bounded review did not resolve uncertainty.",
                "contradiction": "Extraction and assessments disagree; evidence is insufficient.",
                "incomplete_source": f"Source evidence is incomplete: {source.status}.",
                "no_change": "The API returned no textual difference between these revisions.",
            }
            assessment = Assessment(
                decision="insufficient_evidence",
                confidence=0.0,
                explanation=explanations[outcome],
            )
        evidence = (
            ()
            if extraction is None
            else tuple(
                Evidence(before=change.before, after=change.after) for change in extraction.changes
            )
        )
        analysis = AnalysisResult(
            event=source.event,
            analysis_version=ANALYSIS_VERSION,
            backend=settings.backend,
            model=settings.model,
            prompt_version=PROMPT_VERSION,
            **assessment.model_dump(),
            evidence=evidence,
            attempts=len(steps),
            latency_ms=int((clock() - start) * 1000),
            content_truncated=source.content_truncated,
        )
        return ReasonedEdit(
            analysis=analysis,
            enrichment=source,
            extraction=extraction,
            steps=tuple(steps),
            outcome=outcome,
        )

    def call[T: Contract](
        stage: Stage,
        contract: type[T],
        system: str,
        extra: dict[str, object],
        validate: Callable[[T], None] | None = None,
    ) -> T | None:
        for attempt in range(2):
            if len(steps) >= MAX_CALLS:
                return None
            if clock() >= deadline:
                raise ReasoningFailure("deadline_exceeded", tuple(steps))
            user = json.dumps({**input_data, **extra, "repair": attempt > 0}, ensure_ascii=False)
            instructions = system + "\nJSON schema: " + json.dumps(contract.model_json_schema())
            try:
                raw = complete(settings, instructions, user, client, deadline=deadline, clock=clock)
            except ModelError:
                steps.append(Step(stage=stage, outcome="model_error"))
                if record is not None:
                    record(
                        CallRecord(
                            stage=stage, system_prompt=instructions, user_prompt=user, response=None
                        )
                    )
                if clock() >= deadline:
                    raise ReasoningFailure("deadline_exceeded", tuple(steps)) from None
                if attempt == 1 or len(steps) == MAX_CALLS:
                    raise ReasoningFailure("model_failed", tuple(steps)) from None
                wait(max(0.0, min(1.0, deadline - clock())))
                continue
            if record is not None:
                record(
                    CallRecord(
                        stage=stage, system_prompt=instructions, user_prompt=user, response=raw
                    )
                )
            if clock() >= deadline:
                steps.append(Step(stage=stage, outcome="model_error"))
                raise ReasoningFailure("deadline_exceeded", tuple(steps))
            try:
                parsed = parse_output(raw, contract)
                if validate is not None:
                    validate(parsed)
            except ValueError:
                steps.append(Step(stage=stage, outcome="invalid_output"))
                continue
            steps.append(Step(stage=stage, outcome="valid"))
            return parsed
        return None

    if source.status != "ready":
        return finish("no_change" if source.status == "no_text_change" else "incomplete_source")
    extraction = call(
        "extract", Extraction, EXTRACT, {}, lambda value: validate_grounding(value, source)
    )
    if extraction is None:
        return finish("invalid_output")
    extra: dict[str, object] = {"extraction": extraction.model_dump(mode="json")}
    assessment = call("assess", Assessment, ASSESS, extra)
    if assessment is None:
        return finish("invalid_output")
    substantive = any(change.kind != "wording" for change in extraction.changes)
    conflict = assessment.decision == "routine" and substantive
    if assessment.decision == "insufficient_evidence":
        return finish("assessed", assessment)
    if assessment.confidence >= CONFIDENCE_THRESHOLD and not conflict:
        return finish("assessed", assessment)
    extra["first_assessment"] = assessment.model_dump(mode="json")
    reviewed = call("review", Assessment, REVIEW, extra)
    if reviewed is None:
        return finish("invalid_output")
    if reviewed.decision == "insufficient_evidence":
        return finish("reviewed", reviewed)
    if reviewed.confidence < CONFIDENCE_THRESHOLD:
        return finish("low_confidence")
    if reviewed.decision != assessment.decision or (reviewed.decision == "routine" and substantive):
        return finish("contradiction")
    return finish("reviewed", reviewed)
