"""Validated configuration. Never log settings or validation inputs."""

from collections.abc import Mapping
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    backend: Literal["ollama", "openai"] = "ollama"
    model: str = Field(default="qwen2.5:7b", min_length=1, max_length=200, pattern=r"^\S+$")
    base_url: str = Field(
        default="http://localhost:11434", max_length=2048, pattern=r"^https?://\S+$"
    )
    api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    timeout_seconds: float = Field(default=120, gt=0, le=300, allow_inf_nan=False)
    max_tokens: int = Field(default=1024, ge=16, le=8192)

    @model_validator(mode="after")
    def validate_provider(self) -> Self:
        url = urlsplit(self.base_url)
        _ = url.port  # urlsplit validates malformed/out-of-range ports when this is accessed.
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "LLM_BASE_URL must be an HTTP(S) URL without credentials/query/fragment"
            )
        if self.backend == "openai":
            if self.base_url.rstrip("/") != "https://api.openai.com/v1":
                raise ValueError("OpenAI backend requires https://api.openai.com/v1")
            if not self.api_key.get_secret_value().strip():
                raise ValueError("OpenAI backend requires OPENAI_API_KEY")
        return self

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Self:
        hosted = env.get("LLM_BACKEND", "ollama") == "openai"
        # Pydantic parses strings from the environment and rejects invalid values.
        return cls.model_validate(
            {
                "backend": env.get("LLM_BACKEND", "ollama"),
                "model": env.get("LLM_MODEL", "gpt-6.1-sol" if hosted else "qwen2.5:7b"),
                "base_url": env.get(
                    "LLM_BASE_URL",
                    "https://api.openai.com/v1" if hosted else "http://localhost:11434",
                ),
                "api_key": env.get("OPENAI_API_KEY", ""),
                "timeout_seconds": env.get("LLM_TIMEOUT_SECONDS", "120"),
                "max_tokens": env.get("LLM_MAX_TOKENS", "1024"),
            }
        )
