"""One bounded call to the selected provider. Retry policy belongs to the worker."""

import json
from collections.abc import Callable
from time import monotonic
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from triage.config import Settings

MAX_RESPONSE_BYTES = 65_536
MAX_INPUT_CHARACTERS = 32_000


class ModelError(Exception):
    """Sanitized failure; never contains response bodies or credentials."""


class Message(BaseModel):
    model_config = ConfigDict(strict=True)
    role: Literal["assistant"]
    content: Annotated[str, Field(min_length=1, max_length=32_000, pattern=r"\S")]


class OllamaResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    message: Message
    done: Literal[True]
    done_reason: Literal["stop"]


class Choice(BaseModel):
    message: Message
    finish_reason: Literal["stop"]


class OpenAIResponse(BaseModel):
    choices: Annotated[list[Choice], Field(min_length=1, max_length=1)]


def complete(
    settings: Settings,
    system: str,
    user: str,
    client: httpx.Client,
    *,
    deadline: float | None = None,
    clock: Callable[[], float] = monotonic,
) -> str:
    """Return complete text or raise ModelError; never retry or switch providers."""
    if len(system) + len(user) > MAX_INPUT_CHARACTERS:
        raise ModelError("model input exceeds character limit")
    now = clock()
    deadline = now + settings.timeout_seconds if deadline is None else deadline
    remaining = deadline - now
    if remaining <= 0:
        raise ModelError("model deadline exceeded")
    timeout = min(settings.timeout_seconds, remaining)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    body: dict[str, object] = {"model": settings.model, "messages": messages, "stream": False}
    headers: dict[str, str] = {"Accept-Encoding": "identity"}
    if settings.backend == "ollama":
        path = "/api/chat"
        body.update(think=False, options={"num_predict": settings.max_tokens, "temperature": 0})
    else:
        path = "/chat/completions"
        headers["Authorization"] = f"Bearer {settings.api_key.get_secret_value()}"
        body.update(max_completion_tokens=settings.max_tokens, store=False)
    try:
        with client.stream(
            "POST",
            settings.base_url.rstrip("/") + path,
            json=body,
            headers=headers,
            follow_redirects=False,
            timeout=httpx.Timeout(timeout, connect=min(5.0, timeout)),
        ) as response:
            response.raise_for_status()
            if response.headers.get("Content-Encoding", "identity") != "identity":
                raise ModelError("model returned unexpected compression")
            data = bytearray()
            for chunk in response.iter_bytes():
                if clock() >= deadline:
                    raise ModelError("model deadline exceeded")
                if len(data) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise ModelError("model response exceeds byte limit")
                data.extend(chunk)
        if clock() >= deadline:
            raise ModelError("model deadline exceeded")
        payload = json.loads(data)
        if settings.backend == "ollama":
            return OllamaResponse.model_validate(payload).message.content
        return OpenAIResponse.model_validate(payload).choices[0].message.content
    except httpx.HTTPStatusError as exc:
        raise ModelError(f"model HTTP status {exc.response.status_code}") from None
    except httpx.HTTPError:
        raise ModelError("model connection or timeout failure") from None
    except (ValueError, ValidationError, RecursionError):
        raise ModelError("model returned invalid, empty, or incomplete output") from None
