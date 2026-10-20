import json

import httpx
import pytest

from triage.config import Settings
from triage.llm import MAX_INPUT_CHARACTERS, MAX_RESPONSE_BYTES, ModelError, complete

OLLAMA = {
    "message": {"role": "assistant", "content": "The claim changed."},
    "done": True,
    "done_reason": "stop",
}
OPENAI = {
    "choices": [
        {"message": {"role": "assistant", "content": "The claim changed."}, "finish_reason": "stop"}
    ]
}


def test_ollama_request_contract_and_no_credential_forwarding():
    def handler(request):
        assert str(request.url) == "http://localhost:11434/api/chat"
        assert request.method == "POST"
        assert "authorization" not in request.headers
        body = json.loads(request.content)
        assert body == {
            "model": "qwen2.5:7b",
            "stream": False,
            "think": False,
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
            "options": {"num_predict": 1024, "temperature": 0},
        }
        assert request.extensions["timeout"]["read"] == 120
        return httpx.Response(200, json=OLLAMA)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        settings = Settings.from_env({"OPENAI_API_KEY": "must-not-be-sent"})
        assert complete(settings, "system", "user", client) == "The claim changed."


def test_openai_request_contract_and_exactly_one_call():
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-only"
        body = json.loads(request.content)
        assert body["model"] == "gpt-6.1-sol"
        assert body["max_completion_tokens"] == 1024
        assert body["store"] is False
        assert "temperature" not in body
        return httpx.Response(200, json=OPENAI)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        settings = Settings.from_env({"LLM_BACKEND": "openai", "OPENAI_API_KEY": "test-only"})
        assert complete(settings, "system", "user", client) == "The claim changed."
    assert len(calls) == 1


@pytest.mark.parametrize("status", [301, 400, 401, 429, 500, 503])
def test_http_errors_are_sanitized_without_retry_or_redirect(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status, text="private error body", headers={"Location": "https://other"}
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ModelError, match=f"^model HTTP status {status}$"),
    ):
        complete(Settings(), "system", "user", client)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "error", [httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError]
)
def test_connection_errors_are_sanitized(error):
    def handler(request):
        raise error("private connection details")

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ModelError, match="^model connection or timeout failure$"),
    ):
        complete(Settings(), "system", "user", client)


@pytest.mark.parametrize(
    "payload",
    [
        b"not JSON",
        b"\xff",
        b"null",
        b"[]",
        b"{}",
        json.dumps({**OLLAMA, "done": False}).encode(),
        json.dumps({**OLLAMA, "done_reason": "length"}).encode(),
        json.dumps({**OLLAMA, "message": {"role": "assistant", "content": " "}}).encode(),
    ],
)
def test_invalid_or_incomplete_ollama_response_is_rejected(payload):
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload))
        ) as c,
        pytest.raises(ModelError, match="invalid, empty, or incomplete"),
    ):
        complete(Settings(), "system", "user", c)


@pytest.mark.parametrize(
    "choices",
    [
        [],
        OPENAI["choices"] * 2,
        [{"finish_reason": "length", "message": {"role": "assistant", "content": "partial"}}],
        [{"finish_reason": "stop", "message": {"role": "assistant", "content": None}}],
    ],
)
def test_incomplete_ambiguous_or_refused_hosted_response_is_rejected(choices):
    settings = Settings.from_env({"LLM_BACKEND": "openai", "OPENAI_API_KEY": "test-only"})
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": choices}))
        ) as client,
        pytest.raises(ModelError),
    ):
        complete(settings, "system", "user", client)


def test_oversized_input_never_makes_a_request():
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
        ) as c,
        pytest.raises(ModelError, match="input exceeds"),
    ):
        complete(Settings(), "s", "x" * MAX_INPUT_CHARACTERS, c)


def test_oversized_response_is_rejected():
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
            )
        ) as client,
        pytest.raises(ModelError, match="response exceeds"),
    ):
        complete(Settings(), "s", "u", client)
