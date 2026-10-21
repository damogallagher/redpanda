"""Extract, assess, optionally review; four calls maximum and no confident fallback."""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic, sleep
from typing import Annotated, Literal

import httpx
from pydantic import Field

from triage.config import Settings
from triage.enrichment import EnrichmentResult
from triage.limits import ITEM_DEADLINE_SECONDS, MAX_MODEL_CALLS, MAX_STAGE_ATTEMPTS, MAX_WIRE_HUNKS
from triage.llm import ModelError, complete
from triage.prompts import ANALYSIS_VERSION, ASSESS, EXTRACT, PROMPT_VERSION, REVIEW
from triage.schema import MAX_REASONING_HUNKS, AnalysisResult, Contract, Evidence

CONFIDENCE_THRESHOLD = 0.8
MAX_CALLS = MAX_MODEL_CALLS
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
    hunk: Annotated[int, Field(ge=0, le=MAX_WIRE_HUNKS - 1)]
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
    steps: Annotated[tuple[Step, ...], Field(max_length=MAX_CALLS)]
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
    deadline = start + ITEM_DEADLINE_SECONDS if deadline is None else deadline
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
    return _Reasoner(source, settings, client, start, deadline, clock, wait, record).run()


@dataclass
class _Reasoner:
    """State for one item only; all stages share the same call and deadline budgets."""

    source: EnrichmentResult
    settings: Settings
    client: httpx.Client
    start: float
    deadline: float
    clock: Callable[[], float]
    wait: Callable[[float], None]
    record: Callable[[CallRecord], None] | None
    steps: list[Step] = field(default_factory=list)
    extraction: Extraction | None = None

    @property
    def input_data(self) -> dict[str, object]:
        return {
            "title": self.source.event.title,
            "hunks": [item.model_dump() for item in self.source.evidence],
        }

    def finish(self, outcome: Outcome, assessment: Assessment | None = None) -> ReasonedEdit:
        if assessment is None:
            explanations = {
                "invalid_output": "Model output could not be validated within the call budget.",
                "low_confidence": "The bounded review did not resolve uncertainty.",
                "contradiction": "Extraction and assessments disagree; evidence is insufficient.",
                "incomplete_source": f"Source evidence is incomplete: {self.source.status}.",
                "no_change": "The API returned no textual difference between these revisions.",
            }
            assessment = Assessment(
                decision="insufficient_evidence",
                confidence=0.0,
                explanation=explanations[outcome],
            )
        evidence = (
            ()
            if self.extraction is None
            else tuple(
                Evidence(before=change.before, after=change.after)
                for change in self.extraction.changes
            )
        )
        analysis = AnalysisResult(
            event=self.source.event,
            analysis_version=ANALYSIS_VERSION,
            backend=self.settings.backend,
            model=self.settings.model,
            prompt_version=PROMPT_VERSION,
            **assessment.model_dump(),
            evidence=evidence,
            attempts=len(self.steps),
            latency_ms=int((self.clock() - self.start) * 1000),
            content_truncated=self.source.content_truncated,
        )
        return ReasonedEdit(
            analysis=analysis,
            enrichment=self.source,
            extraction=self.extraction,
            steps=tuple(self.steps),
            outcome=outcome,
        )

    def request(self, stage: Stage, instructions: str, user: str, attempt: int) -> str | None:
        try:
            raw = complete(
                self.settings,
                instructions,
                user,
                self.client,
                deadline=self.deadline,
                clock=self.clock,
            )
        except ModelError:
            self.steps.append(Step(stage=stage, outcome="model_error"))
            if self.record is not None:
                self.record(
                    CallRecord(
                        stage=stage, system_prompt=instructions, user_prompt=user, response=None
                    )
                )
            if self.clock() >= self.deadline:
                raise ReasoningFailure("deadline_exceeded", tuple(self.steps)) from None
            if attempt == MAX_STAGE_ATTEMPTS - 1 or len(self.steps) == MAX_CALLS:
                raise ReasoningFailure("model_failed", tuple(self.steps)) from None
            self.wait(max(0.0, min(1.0, self.deadline - self.clock())))
            return None
        if self.record is not None:
            self.record(
                CallRecord(stage=stage, system_prompt=instructions, user_prompt=user, response=raw)
            )
        return raw

    def call[T: Contract](
        self,
        stage: Stage,
        contract: type[T],
        system: str,
        extra: dict[str, object],
        validate: Callable[[T], None] | None = None,
    ) -> T | None:
        for attempt in range(MAX_STAGE_ATTEMPTS):
            if len(self.steps) >= MAX_CALLS:
                return None
            if self.clock() >= self.deadline:
                raise ReasoningFailure("deadline_exceeded", tuple(self.steps))
            user = json.dumps(
                {**self.input_data, **extra, "repair": attempt > 0}, ensure_ascii=False
            )
            instructions = system + "\nJSON schema: " + json.dumps(contract.model_json_schema())
            raw = self.request(stage, instructions, user, attempt)
            if raw is None:
                continue
            if self.clock() >= self.deadline:
                self.steps.append(Step(stage=stage, outcome="model_error"))
                raise ReasoningFailure("deadline_exceeded", tuple(self.steps))
            try:
                parsed = parse_output(raw, contract)
                if validate is not None:
                    validate(parsed)
            except ValueError:
                self.steps.append(Step(stage=stage, outcome="invalid_output"))
                continue
            self.steps.append(Step(stage=stage, outcome="valid"))
            return parsed
        return None

    def run(self) -> ReasonedEdit:
        if self.source.status != "ready":
            return self.finish(
                "no_change" if self.source.status == "no_text_change" else "incomplete_source"
            )
        self.extraction = self.call(
            "extract", Extraction, EXTRACT, {}, lambda value: validate_grounding(value, self.source)
        )
        if self.extraction is None:
            return self.finish("invalid_output")
        extra: dict[str, object] = {"extraction": self.extraction.model_dump(mode="json")}
        assessment = self.call("assess", Assessment, ASSESS, extra)
        if assessment is None:
            return self.finish("invalid_output")
        substantive = any(change.kind != "wording" for change in self.extraction.changes)
        conflict = assessment.decision == "routine" and substantive
        if assessment.decision == "insufficient_evidence":
            return self.finish("assessed", assessment)
        if assessment.confidence >= CONFIDENCE_THRESHOLD and not conflict:
            return self.finish("assessed", assessment)
        return self.review(assessment, substantive, extra)

    def review(
        self, assessment: Assessment, substantive: bool, extra: dict[str, object]
    ) -> ReasonedEdit:
        extra["first_assessment"] = assessment.model_dump(mode="json")
        reviewed = self.call("review", Assessment, REVIEW, extra)
        if reviewed is None:
            return self.finish("invalid_output")
        if reviewed.decision == "insufficient_evidence":
            return self.finish("reviewed", reviewed)
        if reviewed.confidence < CONFIDENCE_THRESHOLD:
            return self.finish("low_confidence")
        if reviewed.decision != assessment.decision or (
            reviewed.decision == "routine" and substantive
        ):
            return self.finish("contradiction")
        return self.finish("reviewed", reviewed)
