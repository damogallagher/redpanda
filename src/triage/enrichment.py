"""Bounded, read-only Wikipedia comparison; content is evidence, never instructions."""

from collections.abc import Callable
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from time import monotonic, sleep, time
from typing import Annotated, Literal, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from triage.diff import extract_evidence
from triage.limits import MAX_WIRE_HUNKS
from triage.schema import Contract, EditEvent, Evidence, Revision, Text

ENDPOINT = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "WikipediaEditTriage/0.1 (https://github.com/damogallagher/redpanda)"
MAX_RESPONSE_BYTES = 262_144
MAX_EVIDENCE_CHARS = 16_000
DEADLINE_SECONDS = 20.0
MAX_REQUEST_ATTEMPTS = 2
MAX_RETRY_SECONDS = 10
REQUEST_TIMEOUT_SECONDS = 5.0
Status = Literal[
    "ready",
    "no_text_change",
    "evidence_limit",
    "revision_unavailable",
    "rate_limited",
    "upstream_unavailable",
    "http_error",
    "timeout",
    "network_error",
    "invalid_response",
    "provenance_mismatch",
    "unsupported_diff",
    "response_too_large",
    "deadline_exceeded",
]


class Provenance(Contract):
    endpoint: Literal["https://en.wikipedia.org/w/api.php"] = "https://en.wikipedia.org/w/api.php"
    page_id: Revision
    from_title: Text
    to_title: Text
    source_url: Text


class EnrichmentResult(Contract):
    schema_version: Literal[1] = 1
    event: EditEvent
    source: Literal["wikipedia", "fixture"]
    status: Status
    attempts: Annotated[int, Field(ge=0, le=MAX_REQUEST_ATTEMPTS)]
    provenance: Provenance | None = None
    # Preserve v1 read compatibility; new parsing uses MAX_REASONING_HUNKS in diff.py.
    evidence: Annotated[tuple[Evidence, ...], Field(max_length=MAX_WIRE_HUNKS)] = ()
    content_truncated: bool = False

    @model_validator(mode="after")
    def consistent_outcome(self) -> Self:
        parsed = self.status in {"ready", "no_text_change", "evidence_limit"}
        if parsed != (self.provenance is not None):
            raise ValueError("parsed outcomes require provenance; failures must not claim it")
        if self.provenance and self.provenance.source_url != self.event.source_url:
            raise ValueError("provenance must identify the requested revisions")
        if self.status == "ready" and not self.evidence:
            raise ValueError("ready requires evidence")
        if self.status not in {"ready", "evidence_limit"} and self.evidence:
            raise ValueError("this outcome cannot contain evidence")
        if self.content_truncated != (self.status in {"evidence_limit", "response_too_large"}):
            raise ValueError("truncation must match the outcome")
        if sum(len(item.before) + len(item.after) for item in self.evidence) > MAX_EVIDENCE_CHARS:
            raise ValueError("evidence exceeds the total character budget")
        return self


class Comparison(BaseModel):
    """Ignore additive upstream fields, but never coerce IDs, titles, or diff text."""

    model_config = ConfigDict(extra="ignore", strict=True)
    fromid: Revision
    toid: Revision
    fromrevid: Revision
    torevid: Revision
    fromns: int
    tons: int
    fromtitle: Text
    totitle: Text
    body: str


class APIError(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    code: str


class APIResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    compare: Comparison | None = None
    error: APIError | None = None


def api_error_status(code: str) -> Status:
    if code in {"baddiff", "nosuchrevid", "missingcontent-revid", "missingcontent-revid-role"}:
        return "revision_unavailable"
    if code in {"maxlag", "ratelimited"}:
        return "rate_limited"
    return "upstream_unavailable"


def decode_comparison(
    event: EditEvent,
    payload: bytes,
    *,
    source: Literal["wikipedia", "fixture"] = "fixture",
    attempts: int = 0,
) -> EnrichmentResult:
    """The live path and offline inspection use the same validation and extraction."""

    def outcome(status: Status, **kwargs: object) -> EnrichmentResult:
        return EnrichmentResult.model_validate(
            {
                "event": event,
                "source": source,
                "attempts": attempts,
                "status": status,
                "content_truncated": status in {"evidence_limit", "response_too_large"},
                **kwargs,
            }
        )

    if len(payload) > MAX_RESPONSE_BYTES:
        return outcome("response_too_large")
    try:
        response = APIResponse.model_validate_json(payload)
    except ValidationError:
        return outcome("invalid_response")
    if response.error is not None:
        if response.compare is not None:
            return outcome("invalid_response")
        return outcome(api_error_status(response.error.code))
    data = response.compare
    if data is None:
        return outcome("invalid_response")
    if (data.fromrevid, data.torevid, data.fromid, data.fromns, data.tons) != (
        event.old_revision_id,
        event.revision_id,
        data.toid,
        0,
        0,
    ):
        return outcome("provenance_mismatch")
    provenance = Provenance(
        page_id=data.toid,
        from_title=data.fromtitle,
        to_title=data.totitle,
        source_url=event.source_url,
    )
    try:
        evidence, truncated = extract_evidence(data.body, MAX_EVIDENCE_CHARS)
    except (ValueError, AssertionError):
        # HTMLParser raises AssertionError for malformed marked declarations.
        return outcome("unsupported_diff")
    status: Status = "evidence_limit" if truncated else "ready" if evidence else "no_text_change"
    return outcome(status, provenance=provenance, evidence=evidence)


def retry_delay(header: str | None, wall_time: Callable[[], float]) -> float:
    """Never shorten a valid server delay. A long delay ends this item without retry."""
    try:
        seconds: float = int(header) if header is not None else 5.0
    except ValueError:
        try:
            seconds = parsedate_to_datetime(str(header)).timestamp() - wall_time()
        except (ValueError, TypeError, OverflowError):
            seconds = 5.0
    return max(5.0, seconds)


def read_comparison(
    event: EditEvent,
    response: httpx.Response,
    attempts: int,
    deadline: float,
    clock: Callable[[], float],
) -> EnrichmentResult:
    def failure(status: Status) -> EnrichmentResult:
        return EnrichmentResult(
            event=event,
            source="wikipedia",
            status=status,
            attempts=attempts,
            content_truncated=status == "response_too_large",
        )

    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return failure("rate_limited")
    if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return failure("upstream_unavailable")
    if response.status_code != HTTPStatus.OK:
        return failure("http_error")
    if response.headers.get("Content-Encoding", "identity") != "identity":
        return failure("invalid_response")
    payload = bytearray()
    for chunk in response.iter_bytes():
        if clock() >= deadline:
            return failure("deadline_exceeded")
        if len(payload) + len(chunk) > MAX_RESPONSE_BYTES:
            return failure("response_too_large")
        payload.extend(chunk)
    return decode_comparison(event, bytes(payload), source="wikipedia", attempts=attempts)


def enrich(
    event: EditEvent,
    client: httpx.Client,
    *,
    clock: Callable[[], float] = monotonic,
    wait: Callable[[float], None] = sleep,
    wall_time: Callable[[], float] = time,
) -> EnrichmentResult:
    """At most two serial requests, with bounded streaming and cooperative deadline checks."""
    deadline = clock() + DEADLINE_SECONDS
    attempts = 0
    params = {
        "action": "compare",
        "format": "json",
        "formatversion": "2",
        "difftype": "table",
        "fromrev": str(event.old_revision_id),
        "torev": str(event.revision_id),
        "prop": "diff|ids|title",
        "maxlag": "5",
    }

    def failure(status: Status) -> EnrichmentResult:
        return EnrichmentResult(
            event=event,
            source="wikipedia",
            status=status,
            attempts=attempts,
            content_truncated=status == "response_too_large",
        )

    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            return failure("deadline_exceeded")
        attempts += 1
        try:
            with client.stream(
                "GET",
                ENDPOINT,
                params=params,
                follow_redirects=False,
                timeout=httpx.Timeout(min(REQUEST_TIMEOUT_SECONDS, remaining)),
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
            ) as response:
                delay = retry_delay(response.headers.get("Retry-After"), wall_time)
                result = read_comparison(event, response, attempts, deadline, clock)
        except httpx.TimeoutException:
            return failure("timeout")
        except httpx.HTTPError:
            return failure("network_error")
        if clock() >= deadline:
            return failure("deadline_exceeded")
        if result.status not in {"rate_limited", "upstream_unavailable"}:
            return result
        if (
            attempts == MAX_REQUEST_ATTEMPTS
            or delay > MAX_RETRY_SECONDS
            or clock() + delay >= deadline
        ):
            return result
        wait(delay)
