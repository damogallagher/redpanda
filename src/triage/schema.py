"""Versioned boundary contracts; strict validation rejects silent coercion."""

from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from triage.limits import MAX_MODEL_CALLS, MAX_TEXT_CHARS, MAX_WIRE_HUNKS
from triage.limits import MAX_REASONING_HUNKS as MAX_REASONING_HUNKS

Text = Annotated[str, Field(min_length=1, max_length=MAX_TEXT_CHARS, pattern=r"\S")]
Revision = Annotated[int, Field(gt=0, strict=True)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class EditEvent(Contract):
    schema_version: Literal[1] = 1
    wiki: Literal["enwiki"]
    title: Annotated[str, Field(min_length=1, max_length=512, pattern=r"\S")]
    old_revision_id: Revision
    revision_id: Revision
    occurred_at: AwareDatetime

    @model_validator(mode="after")
    def different_revisions(self) -> Self:
        if self.old_revision_id == self.revision_id:
            raise ValueError("old and new revisions must differ")
        return self

    @property
    def event_id(self) -> str:
        return f"{self.wiki}:{self.revision_id}"

    @property
    def source_url(self) -> str:
        return (
            f"https://en.wikipedia.org/w/index.php?diff={self.revision_id}"
            f"&oldid={self.old_revision_id}"
        )


class Evidence(Contract):
    before: Annotated[str, Field(max_length=MAX_TEXT_CHARS)]
    after: Annotated[str, Field(max_length=MAX_TEXT_CHARS)]

    @model_validator(mode="after")
    def changed_text(self) -> Self:
        if self.before == self.after:
            raise ValueError("evidence must contain a change")
        return self


class AnalysisResult(Contract):
    schema_version: Literal[1] = 1
    event: EditEvent
    analysis_version: Text
    backend: Literal["ollama", "openai"]
    model: Text
    prompt_version: Text
    decision: Literal["routine", "review", "insufficient_evidence"]
    confidence: Annotated[float, Field(ge=0, le=1)]
    explanation: Text
    evidence: Annotated[tuple[Evidence, ...], Field(max_length=MAX_WIRE_HUNKS)]
    attempts: Annotated[int, Field(ge=0, le=MAX_MODEL_CALLS)]
    latency_ms: Annotated[int, Field(ge=0)]
    content_truncated: bool

    @model_validator(mode="after")
    def require_evidence(self) -> Self:
        if self.decision != "insufficient_evidence" and not self.evidence:
            raise ValueError("a substantive decision requires evidence")
        if self.content_truncated and self.decision == "routine":
            raise ValueError("incomplete content cannot be classified as routine")
        return self
