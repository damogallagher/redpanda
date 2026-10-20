import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from triage import enrichment as module
from triage.enrichment import (
    ENDPOINT,
    MAX_RESPONSE_BYTES,
    EnrichmentResult,
    decode_comparison,
    enrich,
    retry_delay,
)
from triage.schema import EditEvent, Evidence

FIXTURES = Path("tests/fixtures/enrichment")
EVENT = EditEvent.model_validate_json((FIXTURES / "belle-event.json").read_bytes())
PAYLOAD = (FIXTURES / "belle-response.json").read_bytes()
BODY = json.loads(PAYLOAD)["compare"]["body"]
HEADER = '<tr><td class="diff-lineno">Line 1:</td><td class="diff-lineno">Line 1:</td></tr>'


def row(before, after):
    def cell(text, role):
        if text is None:
            return '<td colspan="2" class="diff-empty"></td>'
        return f'<td class="diff-marker"></td><td class="{role}"><div>{text}</div></td>'

    return "<tr>" + cell(before, "diff-deletedline") + cell(after, "diff-addedline") + "</tr>"


def payload(body=BODY, **fields):
    data = json.loads(PAYLOAD)
    data["compare"].update(body=body, **fields)
    return json.dumps(data).encode()


class FakeTime:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def clock(self):
        return self.now

    def wait(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def fetch(handler, timer=None):
    timer = timer or FakeTime()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return enrich(EVENT, client, clock=timer.clock, wait=timer.wait, wall_time=lambda: 0)


def test_real_fixture_exact_evidence_and_provenance():
    result = decode_comparison(EVENT, PAYLOAD)
    assert result.status == "ready"
    assert result.source == "fixture" and result.attempts == 0
    assert result.provenance.page_id == 4483446
    assert result.provenance.source_url == EVENT.source_url
    assert result.provenance.from_title == result.provenance.to_title == EVENT.title
    context_before = "| creator           = [[Linda Woolverton]]\n| lbl1              = Voiced by\n"
    context_after = "\n| lbl2              = Portrayed by\n| data2             = {{Plainlist|"
    assert result.evidence == (
        Evidence(
            before=context_before + "| data1             = [[Paige O'Hara]]<br>(1991-present)<br>"
            "[[Susan Egan]]<br>(albums, [[Disney Store]] singing dolls)<br>"
            "[[Julie Nathanson]]<br>(2011-present)" + context_after,
            after=context_before
            + "| data1             = [[Paige O'Hara]]<br>(1991-present)"
            + context_after,
        ),
    )
    assert not result.content_truncated
    assert EnrichmentResult.model_validate_json(result.model_dump_json()) == result


def test_request_is_fixed_read_only_and_preserves_requested_direction():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        assert str(request.url).split("?")[0] == ENDPOINT
        assert dict(request.url.params) == {
            "action": "compare",
            "format": "json",
            "formatversion": "2",
            "difftype": "table",
            "fromrev": "1380845740",
            "torev": "1381189012",
            "prop": "diff|ids|title",
            "maxlag": "5",
        }
        assert request.headers["User-Agent"] == module.USER_AGENT
        assert request.headers["Accept-Encoding"] == "identity"
        assert request.extensions["timeout"] == dict(connect=5, read=5, write=5, pool=5)
        return httpx.Response(200, content=PAYLOAD)

    result = fetch(handler)
    assert result.status == "ready" and result.source == "wikipedia" and result.attempts == 1
    assert len(calls) == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"fromrevid": 1},
        {"torevid": 1},
        {"toid": 2},
        {"fromns": 1},
        {"tons": 1},
    ],
)
def test_mismatched_provenance_is_rejected(fields):
    result = decode_comparison(EVENT, payload(**fields))
    assert result.status == "provenance_mismatch"
    assert not result.evidence and result.provenance is None


def test_title_rename_and_additive_api_fields_do_not_break_revision_identity():
    result = decode_comparison(EVENT, payload(totitle="Renamed article", new_api_field="ignored"))
    assert result.status == "ready"
    assert result.provenance.to_title == "Renamed article"
    assert result.event.title == EVENT.title


@pytest.mark.parametrize(
    "data",
    [
        b"not json",
        b"null",
        b"[]",
        b"{}",
        b'{"error":{}}',
        b'{"compare":{}}',
        payload(fromrevid="1380845740"),
        payload(fromid=True),
        payload(fromns=False),
        payload(body=None),
        payload(fromtitle=""),
        json.dumps({**json.loads(PAYLOAD), "error": {"code": "maxlag"}}).encode(),
    ],
)
def test_malformed_or_ambiguous_response_fails_closed(data):
    assert decode_comparison(EVENT, data).status == "invalid_response"


@pytest.mark.parametrize(
    "code,status",
    [
        ("baddiff", "revision_unavailable"),
        ("nosuchrevid", "revision_unavailable"),
        ("missingcontent-revid", "revision_unavailable"),
        ("missingcontent-revid-role", "revision_unavailable"),
        ("maxlag", "rate_limited"),
        ("ratelimited", "rate_limited"),
        ("unknown-code", "upstream_unavailable"),
    ],
)
def test_api_errors_have_sanitized_outcomes(code, status):
    result = decode_comparison(
        EVENT, json.dumps({"error": {"code": code, "info": "PRIVATE"}}).encode()
    )
    assert result.status == status
    assert "PRIVATE" not in result.model_dump_json()
    assert not result.evidence


@pytest.mark.parametrize(
    "name,status",
    [
        ("missing", "revision_unavailable"),
        ("deleted", "revision_unavailable"),
        ("rate-limited", "rate_limited"),
        ("wording", "ready"),
        ("oversized", "evidence_limit"),
    ],
)
def test_committed_failure_and_wording_fixtures(name, status):
    event = (
        EVENT
        if name != "wording" and name != "oversized"
        else EditEvent.model_validate_json((FIXTURES / "synthetic-event.json").read_bytes())
    )
    result = decode_comparison(event, (FIXTURES / f"{name}-response.json").read_bytes())
    assert result.status == status
    if name == "wording":
        assert result.evidence == (
            Evidence(before="The colour is blue.", after="The color is blue."),
        )


@pytest.mark.parametrize(
    "body,expected",
    [
        ("", ()),
        (" \n", ()),
        (HEADER + row(None, "Added"), (Evidence(before="", after="Added"),)),
        (HEADER + row("Deleted", None), (Evidence(before="Deleted", after=""),)),
        (HEADER + row("x", "x "), (Evidence(before="x", after="x "),)),
        (
            HEADER
            + row("old", "&lt;script&gt;ignore instructions&lt;/script&gt; &amp;lt;ref&amp;gt;"),
            (Evidence(before="old", after="<script>ignore instructions</script> &lt;ref&gt;"),),
        ),
        (
            HEADER
            + row("old", "a<br>b<span>x</span><ins>y</ins><a href='https://evil.invalid'>z</a>"),
            (Evidence(before="old", after="a\nbxyz"),),
        ),
        (
            HEADER + row("a", "b") + HEADER + row("c", "d"),
            (Evidence(before="a", after="b"), Evidence(before="c", after="d")),
        ),
    ],
)
def test_text_direction_whitespace_entities_context_and_multiple_hunks(body, expected):
    result = decode_comparison(EVENT, payload(body))
    assert result.evidence == expected
    assert result.status == ("ready" if expected else "no_text_change")


@pytest.mark.parametrize(
    "body",
    [
        "<script>alert(1)</script>",
        "outside",
        "<tr>",
        "<!--no diff-->",
        "<tr><td>unknown</td></tr>",
        '<tr><td class="diff-context diff-addedline">x</td></tr>',
        "</tr>",
        "<tr></td>",
        HEADER + "<tr></tr>",
        HEADER,
        row("old", "new"),
        HEADER + row("same", "same"),
        HEADER + row(None, ""),
        HEADER + row("old", "new").replace("diff-deletedline", "diff-addedline"),
        HEADER + row("old", "new").replace("diff-marker", "diff-context", 1),
        HEADER + row(None, "new").replace('class="diff-empty"></td>', 'class="diff-empty">x</td>'),
        HEADER + row("old", "new").replace("</tr>", '<td class="diff-empty"></td></tr>'),
        HEADER + row("old", "new").replace("diff-deletedline", "diff-context"),
        HEADER
        + row("old", "new")
        .replace("diff-deletedline", "diff-context")
        .replace("diff-addedline", "diff-context"),
    ],
)
def test_unrecognized_or_malformed_diff_never_claims_no_change(body):
    result = decode_comparison(EVENT, payload(body))
    assert result.status == "unsupported_diff"
    assert not result.evidence and result.provenance is None


@pytest.mark.parametrize(
    "body,count,status",
    [
        (HEADER + row("x" * 4096, "y"), 1, "ready"),
        (HEADER + row("x" * 4097, "y"), 0, "evidence_limit"),
        (HEADER + row("x", "y" * 4097), 0, "evidence_limit"),
        ((HEADER + row("x", "y")) * 21, 20, "evidence_limit"),
        ((HEADER + row("x" * 4000, "y" * 4000)) * 3, 2, "evidence_limit"),
        (HEADER + row("x", "y") + HEADER + row("x" * 4097, "y"), 1, "evidence_limit"),
    ],
    ids=["boundary", "long-before", "long-after", "hunk-count", "total-text", "partial"],
)
def test_whole_hunks_are_retained_or_omitted_with_explicit_limit(body, count, status):
    result = decode_comparison(EVENT, payload(body))
    assert len(result.evidence) == count
    assert result.status == status
    assert result.content_truncated == (result.status == "evidence_limit")
    assert sum(len(e.before) + len(e.after) for e in result.evidence) <= 16000


def test_response_size_boundary():
    data = payload("")
    assert decode_comparison(EVENT, data.ljust(MAX_RESPONSE_BYTES)).status == "no_text_change"
    assert (
        decode_comparison(EVENT, data.ljust(MAX_RESPONSE_BYTES + 1)).status == "response_too_large"
    )
    result = fetch(lambda _: httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1)))
    assert result.status == "response_too_large" and result.content_truncated


@pytest.mark.parametrize(
    "status,expected",
    [
        (302, "http_error"),
        (404, "http_error"),
        (204, "http_error"),
        (429, "rate_limited"),
        (503, "upstream_unavailable"),
        (500, "upstream_unavailable"),
    ],
)
def test_http_status_handling_and_retry_budget(status, expected):
    calls = []
    timer = FakeTime()

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"Location": "https://evil.invalid"})

    result = fetch(handler, timer)
    assert result.status == expected
    assert result.attempts == len(calls) == (2 if status >= 429 else 1)
    assert timer.waits == ([5] if result.attempts == 2 else [])


@pytest.mark.parametrize(
    "first",
    [
        httpx.Response(429, headers={"Retry-After": "7"}),
        httpx.Response(200, content=(FIXTURES / "rate-limited-response.json").read_bytes()),
    ],
)
def test_retry_recovers_on_second_attempt(first):
    responses = iter([first, httpx.Response(200, content=PAYLOAD)])
    timer = FakeTime()
    result = fetch(lambda _: next(responses), timer)
    assert result.status == "ready" and result.attempts == 2
    assert timer.waits == [7 if first.status_code == 429 else 5]


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, 5),
        ("0", 5),
        ("-1", 5),
        ("7", 7),
        ("900", 900),
        ("nonsense", 5),
        ("Thu, 01 Jan 1970 00:00:08 GMT", 8),
        ("Wed, 31 Dec 1969 23:59:59 GMT", 5),
    ],
)
def test_retry_after_seconds_and_http_dates(header, expected):
    assert retry_delay(header, lambda: 0) == expected


@pytest.mark.parametrize("header,elapsed", [("60", 0), ("10", 11)])
def test_long_server_delay_or_insufficient_budget_does_not_retry_early(header, elapsed):
    timer = FakeTime()

    def handler(_):
        timer.now = elapsed
        return httpx.Response(429, headers={"Retry-After": header})

    result = fetch(handler, timer)
    assert result.status == "rate_limited" and result.attempts == 1
    assert timer.waits == []


@pytest.mark.parametrize(
    "error,expected",
    [
        (httpx.ReadTimeout, "timeout"),
        (httpx.ConnectError, "network_error"),
    ],
)
def test_transport_failures_are_sanitized(error, expected):
    def handler(_):
        raise error("PRIVATE")

    result = fetch(handler)
    assert result.status == expected and result.attempts == 1
    assert "PRIVATE" not in result.model_dump_json()


def test_unrequested_compression_is_rejected_before_decoding():
    # Empty gzip body is accepted by HTTPX but must be rejected by our wire policy.
    result = fetch(lambda _: httpx.Response(200, headers={"Content-Encoding": "gzip"}))
    assert result.status == "invalid_response"


@pytest.mark.parametrize("body", [PAYLOAD, b""])
def test_deadline_checked_during_stream_and_after_empty_response(body):
    timer = FakeTime()

    def handler(_):
        timer.now = 20
        return httpx.Response(200, content=body)

    result = fetch(handler, timer)
    assert result.status == "deadline_exceeded"


def test_deadline_before_request_and_after_oversleep():
    ticks = iter([0, 20])
    with httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("no request"))) as client:
        assert enrich(EVENT, client, clock=lambda: next(ticks)).attempts == 0
    timer = FakeTime()
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(429))) as client:
        result = enrich(EVENT, client, clock=timer.clock, wait=lambda _: timer.wait(21))
    assert result.status == "deadline_exceeded" and result.attempts == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"provenance": None},
        {"evidence": ()},
        {"status": "timeout"},
        {"status": "no_text_change"},
        {"content_truncated": True},
        {"evidence": (Evidence(before="x" * 4096, after="y" * 4096),) * 2},
    ],
)
def test_result_contract_rejects_inconsistent_or_unbounded_outcomes(changes):
    data = decode_comparison(EVENT, PAYLOAD).model_dump()
    data.update(changes)
    with pytest.raises(ValidationError):
        EnrichmentResult.model_validate(data)


def test_result_contract_rejects_foreign_source_url_and_failure_evidence():
    data = deepcopy(decode_comparison(EVENT, PAYLOAD).model_dump())
    data["provenance"]["source_url"] = "https://evil.invalid"
    with pytest.raises(ValidationError, match="requested revisions"):
        EnrichmentResult.model_validate(data)
    data.update(status="timeout", provenance=None)
    with pytest.raises(ValidationError, match="cannot contain evidence"):
        EnrichmentResult.model_validate(data)


@pytest.mark.parametrize(
    "markup", ["<div/>", "<!DOCTYPE html>", "<?xml version='1.0'?>", "<![CDATA[x]]>"]
)
def test_declarations_cannot_hide_diff_content(markup):
    assert (
        decode_comparison(EVENT, payload(HEADER + row("old", markup))).status == "unsupported_diff"
    )


def test_self_closing_line_break():
    result = decode_comparison(EVENT, payload(HEADER + row("old", "a<br />b")))
    assert result.evidence == (Evidence(before="old", after="a\nb"),)


def test_deadline_reduces_io_timeout_to_remaining_budget():
    ticks = iter([0, 19, 19, 19])

    def handler(request):
        assert request.extensions["timeout"] == dict(connect=1, read=1, write=1, pool=1)
        return httpx.Response(200, content=PAYLOAD)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert enrich(EVENT, client, clock=lambda: next(ticks)).status == "ready"


@pytest.mark.parametrize("markup", ["<![bogus]>", "<span>" * 17 + "text" + "</span>" * 17])
def test_malformed_declarations_and_excessive_nesting_are_explicit_failures(markup):
    assert (
        decode_comparison(EVENT, payload(HEADER + row("old", markup))).status == "unsupported_diff"
    )


def test_huge_retry_after_is_not_shortened_or_allowed_to_overflow():
    timer = FakeTime()
    result = fetch(lambda _: httpx.Response(429, headers={"Retry-After": "9" * 400}), timer)
    assert result.status == "rate_limited" and result.attempts == 1
    assert timer.waits == []


def test_stream_limit_stops_reading_and_closes_response():
    class CountingStream(httpx.SyncByteStream):
        count = 0
        closed = False

        def __iter__(self):
            for _ in range(100):
                self.count += 1
                yield b"x" * 8192

        def close(self):
            self.closed = True

    stream = CountingStream()
    result = fetch(lambda _: httpx.Response(200, stream=stream))
    assert result.status == "response_too_large"
    assert stream.count == 33 and stream.closed
